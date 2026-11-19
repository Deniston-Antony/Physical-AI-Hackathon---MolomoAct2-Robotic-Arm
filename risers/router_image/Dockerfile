# The Risers router image: v3 (MolmoBot-Img, MolmoSpaces) and FLUX 3 Action (1 step, fast timing + retry, RoboLab and
# anything else) in one image. front.py on port 8000 starts v3 and switches to FLUX when the first task is not a
# MolmoSpaces wording. Only one model is on the GPU at a time.
FROM docker.io/denistonantony/molmobot-img-droid:v3-jpeg-rl2 AS v3

# v3 reads the float32 checkpoint into a bfloat16 model (policy.py: model.to(bfloat16), then load_state_dict).
# Storing the checkpoint in bfloat16 gives the same weights and halves the file (20 GB -> 10 GB).
FROM v3 AS v3bf16
RUN mkdir -p /out && tar -C /opt -cf - --exclude=molmobot/MolmoBot-Img-DROID/model.pt molmobot | tar -C /out -xf - \
 && /positronic/.venv/bin/python -c "import torch; \
s = torch.load('/opt/molmobot/MolmoBot-Img-DROID/model.pt', map_location='cpu', weights_only=True, mmap=True); \
torch.save({k: (v.to(torch.bfloat16) if v.is_floating_point() else v) for k, v in s.items()}, \
'/out/molmobot/MolmoBot-Img-DROID/model.pt')"

FROM docker.io/positro/flux3-action@sha256:af8ebf7933b9cd6c15bd34d0c5a12bdfbbbd02b43f10857393b3db33ec57cccc
# Python 3.13 for v3 beside the image's own Python 3.12.
COPY --from=v3 /usr/local/bin/python3.13 /usr/local/bin/python3.13
COPY --from=v3 /usr/local/lib/python3.13 /usr/local/lib/python3.13
COPY --from=v3 /usr/local/lib/libpython3.13.so.1.0 /usr/local/lib/libpython3.13.so.1.0
RUN ldconfig
COPY --from=v3 /positronic /v3/positronic
COPY --from=v3 /opt/hf /opt/hf
COPY --from=v3bf16 /out/molmobot /opt/molmobot
COPY v3_patch/policy.py /v3/positronic/positronic/vendors/molmobot/policy.py
COPY code_flux3v3 /positronic/positronic/vendors/flux3_v3rules
COPY route_rule.py front.py /router/
RUN /v3/positronic/.venv/bin/python -c "import sys; print(sys.version)" \
 && grep -rl '/positronic' /v3/positronic/.venv/lib/python3.13/site-packages/*.pth 2>/dev/null || true
ENTRYPOINT ["/usr/local/bin/python3.12", "/router/front.py"]
