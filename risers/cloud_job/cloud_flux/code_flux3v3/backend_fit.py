"""BFL's server for FLUX 3 Action, as `flux3_action/backend.py` runs it, inside the GPU memory of a competition run.

The text encoder stays on the CPU. With `--text-encode gpu` it visits the GPU to encode an instruction that is not
cached yet, as BFL's offload does. With `--text-encode cpu` it encodes on the CPU and never visits the GPU.
`--slice-mib` caps the GPU memory of this process at that slice, less the CUDA context: PyTorch then refuses an
allocation over the cap with an out-of-memory error. The DiT is packed for inference in place: each source weight
is freed when its block is packed. BFL's own packing keeps every source weight until the end, which needs about
9 GB more. The script logs the GPU memory as lines that start with `FIT:`.
It runs in BFL's own environment, so it imports nothing from positronic.
"""

import argparse
import gc

import torch
from flux_action import policy as flux_policy
from flux_action.models.transformer import JointSingleSeq
from flux_action.models.transformer_inf_bf16 import BF16InferenceDiT
from flux_action.policy import FluxActionPolicy
from flux_action.serving import robolab

# Room for the growth of the CUDA context after the cap is set: kernels load when they first run.
_CONTEXT_GROWTH_MIB = 512


def _mib(value: int) -> str:
    return f'{value / 2**20:.0f} MiB'


def _log(what: str) -> None:
    free, total = torch.cuda.mem_get_info()
    print(
        f'FIT: {what}: device used {_mib(total - free)}, allocated {_mib(torch.cuda.memory_allocated())}, '
        f'reserved {_mib(torch.cuda.memory_reserved())}, peak reserved {_mib(torch.cuda.max_memory_reserved())}',
        flush=True,
    )


def _patch_contexts(text_encode: str) -> None:
    """Log the memory after each instruction encode; with `cpu`, encode on the CPU, where the encoder waits."""
    contexts = FluxActionPolicy._contexts

    def patched(self, *args, **kwargs):
        offload = self._offload_text_encoder
        if text_encode == 'cpu':
            self._offload_text_encoder = False
        try:
            out = contexts(self, *args, **kwargs)
        finally:
            self._offload_text_encoder = offload
        _log('after an instruction encode')
        return out

    FluxActionPolicy._contexts = patched


def _then_free(pack):
    def packed_and_freed() -> None:
        pack()
        torch.cuda.empty_cache()

    return packed_and_freed


def _patch_prepare_inference() -> None:
    """`FluxActionPolicy.prepare_inference`, with the BF16 DiT packed in place."""
    published = FluxActionPolicy.prepare_inference

    def prepare_inference(self, *, compile: bool = True) -> bool:
        if not isinstance(self.dit, JointSingleSeq):
            return published(self, compile=compile)
        self.config.single_frame_encode = True
        if not flux_policy._released_inference_config(self.config) or self.device.type != 'cuda':
            return False
        weights = dict(self.dit.state_dict())
        assert len({t.device for t in weights.values()}) == 1, 'weights need one device'
        assert {t.dtype for t in weights.values()} == {torch.bfloat16}, 'expected BF16 weights'
        self.dit = None
        gc.collect()
        with torch.device('meta'):
            dit = BF16InferenceDiT()
        dit.load_state_dict(weights, strict=True, assign=True)
        weights.clear()
        for module in dit.modules():
            if hasattr(module, 'pack_input_projection'):
                module.pack_input_projection = _then_free(module.pack_input_projection)
        dit._pack_for_inference()
        dit.eval()
        self.dit = dit
        self.reset()
        _log('after the DiT packing')
        self.dit.validate_runtime_device()
        if compile and self.dit._compiled_hot is None:
            self.dit.compile_static()
            self.dit.compile_hot()
        if compile:
            self.video_vae.module.compile_encoder()
        self._inference_prepared = True
        _log('after the compile')
        return True

    FluxActionPolicy.prepare_inference = prepare_inference


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Serve FLUX 3 Action's DROID policy in a GPU memory slice.")
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--revision')
    parser.add_argument('--subfolder')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=9000)
    parser.add_argument('--slice-mib', type=int, default=0, help='the GPU memory of the slice; 0 sets no cap')
    parser.add_argument('--text-encode', choices=('gpu', 'cpu'), default='gpu')
    args = parser.parse_args(argv)

    first_graph = torch.cuda.CUDAGraph()
    with torch.cuda.graph(first_graph):
        torch.zeros(1, device='cuda')
    if args.slice_mib:
        free, total = torch.cuda.mem_get_info()
        context = (total - free) - torch.cuda.memory_reserved()
        cap = args.slice_mib * 2**20 - context - _CONTEXT_GROWTH_MIB * 2**20
        torch.cuda.set_per_process_memory_fraction(cap / total)
        print(f'FIT: slice {args.slice_mib} MiB, CUDA context {_mib(context)}, PyTorch cap {_mib(cap)}', flush=True)
    print(f'FIT: text encode on the {args.text_encode}, {torch.get_num_threads()} CPU threads', flush=True)
    _patch_contexts(args.text_encode)
    _patch_prepare_inference()

    policy = robolab.load_serving_policy(
        args.checkpoint,
        revision=args.revision,
        subfolder=args.subfolder,
        device='cuda',
        dtype='bfloat16',
        offload_text_encoder=True,
    )
    policy.set_text_encoder_offload(True)
    torch.cuda.empty_cache()
    _log('after the load and the warm-up')
    torch.cuda.reset_peak_memory_stats()
    metadata = {
        'checkpoint': args.checkpoint,
        'revision': args.revision,
        'subfolder': args.subfolder,
        'serving_setup': policy.serving_setup,
        'slice_mib': args.slice_mib,
        'text_encode': args.text_encode,
    }
    robolab.serve(robolab.RoboLabPolicy(policy), host=args.host, port=args.port, metadata=metadata)


if __name__ == '__main__':
    main()
