"""The Risers router: one policy image, two models.

Port 8000 (the platform's) is this front. It starts v3 (MolmoBot-Img, our best MolmoSpaces model) on port 8001 and
passes every connection through to it. v3 logs the task of each new session (`ROUTER_TASK '...'`). The first task
decides the run, once:
  - a MolmoSpaces wording (route_rule.is_molmospaces): v3 stays for the whole run;
  - any other wording (RoboLab, the real robot): the front refuses new sessions with 503 (the client retries a
    cold server up to its connect deadline, 900 s), waits until the sessions open on v3 end, stops v3, starts
    FLUX 3 Action (1 step, fast timing + retry) on port 8002 and passes everything to FLUX from then on.
It never switches back. If FLUX does not start, v3 comes back so the run goes on.
While no model answers, a keepalive gets 503 before the first start and 200 {"alive_seconds": null} during the
switch, so the platform waits instead of failing the run.
Standard library only.
"""
import ast
import asyncio
import os
import re
import signal
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from route_rule import is_molmospaces  # noqa: E402

FRONT_PORT, V3_PORT, FLUX_PORT = 8000, 8001, 8002
KEEPALIVE = '/api/v1/keepalive'
WAIT_SESSIONS_S = 900  # the longest the switch waits for the sessions on v3 to end
START_LIMIT_S = 1500  # the longest a model may take to answer its first keepalive

V3_ENV = {
    'PYTHONPATH': ':'.join(f'/v3/positronic/{p}' for p in ('', 'client', 'wire', 'model_server', 'vocabulary', 'evals'))
    + ':/opt/molmobot',
    'VIRTUAL_ENV': '/v3/positronic/.venv',
    'UV_PROJECT_ENVIRONMENT': '/v3/positronic/.venv',
    'HF_HOME': '/opt/hf',
    'PYTORCH_CUDA_ALLOC_CONF': 'expandable_segments:True',
}
V3_CMD = [
    '/v3/positronic/.venv/bin/python', '-m', 'positronic.vendors.molmobot.server', 'droid_half_overlap',
    '--model.checkpoint_dir=/opt/molmobot/MolmoBot-Img-DROID', '--model.camera=left',
    '--pipeline.horizon_sec=0.7667', '--model.num_flow_steps=3', '--model.still_calls=3',
    '--model.reword_tasks=True', '--model.split_tasks=True', '--model.miss_deeper_m=0.02',
    f'--websocket.served_address.port={V3_PORT}',
]
FLUX_CMD = [
    '/positronic/.venv/bin/python', '-m', 'positronic.vendors.flux3_v3rules.server', 'droid_retry_1step',
    '--model.model.flux_python=/opt/flux-action/.venv/bin/python',
    f'--model.model.checkpoint={os.environ.get("FLUX_POLICY_REPO", "")}',
    f'--model.model.revision={os.environ.get("FLUX_POLICY_REVISION", "")}',
    f'--model.model.subfolder={os.environ.get("FLUX_POLICY_SUBFOLDER", "")}',
    '--model.model.text_encode=cpu',
    f'--websocket.served_address.port={FLUX_PORT}',
]
TASK_LINE = re.compile(r"ROUTER_TASK (?P<task>'.*'|\".*\")\s*$")


def say(msg: str) -> None:
    print(f'{time.strftime("%H:%M:%S")} [router] {msg}', flush=True)


class Router:
    def __init__(self) -> None:
        self.state = 'starting'  # starting -> v3 -> (switching -> flux) ; 'down' when a model died
        self.port = V3_PORT
        self.proc: asyncio.subprocess.Process | None = None
        self.decided = False
        self.sessions = 0  # websocket sessions open on the current model

    # --- models -------------------------------------------------------------------------------------------
    async def start(self, which: str) -> bool:
        cmd, env, port = (V3_CMD, V3_ENV, V3_PORT) if which == 'v3' else (FLUX_CMD, {}, FLUX_PORT)
        # python -m puts the working folder first on the path: v3 must start in its own code, not FLUX's /positronic.
        cwd = '/v3/positronic' if which == 'v3' else '/positronic'
        cwd = cwd if os.path.isdir(cwd) else None
        say(f'starting {which} on port {port}')
        t0 = time.monotonic()
        self.proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=cwd, env={**os.environ, **env}, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        asyncio.create_task(self.read_log(self.proc, which))
        while time.monotonic() - t0 < START_LIMIT_S:
            if self.proc.returncode is not None:
                say(f'{which} exited with {self.proc.returncode} before it was ready')
                return False
            if await keepalive_ok(port):
                say(f'{which} ready after {time.monotonic() - t0:.0f} s')
                self.port = port
                return True
            await asyncio.sleep(2)
        say(f'{which} not ready after {START_LIMIT_S} s')
        await self.stop()
        return False

    async def stop(self) -> None:
        p = self.proc
        if p is None or p.returncode is not None:
            return
        p.terminate()
        try:
            await asyncio.wait_for(p.wait(), 60)
        except asyncio.TimeoutError:
            p.kill()
            await p.wait()
        say(f'model process stopped ({p.returncode})')

    async def read_log(self, proc: asyncio.subprocess.Process, which: str) -> None:
        assert proc.stdout is not None
        async for raw in proc.stdout:
            line = raw.decode(errors='replace').rstrip()
            print(f'[{which}] {line}', flush=True)
            m = TASK_LINE.search(line)
            if m and which == 'v3' and not self.decided:
                try:
                    task = ast.literal_eval(m.group('task'))
                except (ValueError, SyntaxError):
                    continue
                if not str(task).strip():
                    continue  # v3's warm-up call at startup has no task
                self.decided = True
                # ROUTER_TEST_SWITCH=1 (cloud test only, never in the image's settings) switches on any first task.
                if is_molmospaces(task) and os.environ.get('ROUTER_TEST_SWITCH') != '1':
                    say(f'first task {task!r} is a MolmoSpaces wording: v3 for the whole run')
                else:
                    say(f'first task {task!r} is not a MolmoSpaces wording: switch to FLUX')
                    self.state = 'switching'
                    asyncio.create_task(self.switch())
        rc = await proc.wait()
        if proc is self.proc and self.state in ('v3', 'flux'):
            say(f'{which} died ({rc}); starting it again')
            self.state = 'down'
            asyncio.create_task(self.restart(which))

    async def restart(self, which: str) -> None:
        if await self.start(which):
            self.state = which

    async def switch(self) -> None:
        t0 = time.monotonic()
        while self.sessions > 0 and time.monotonic() - t0 < WAIT_SESSIONS_S:
            await asyncio.sleep(0.5)
        say(f'{self.sessions} sessions still open after {time.monotonic() - t0:.0f} s; stop v3')
        await self.stop()
        if await self.start('flux'):
            self.state = 'flux'
            say('FLUX serves the rest of the run')
        else:
            say('FLUX did not start: v3 comes back')
            if await self.start('v3'):
                self.state = 'v3'

    # --- connections --------------------------------------------------------------------------------------
    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            head = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), 30)
        except (asyncio.TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError, ConnectionError):
            writer.close()
            return
        first = head.split(b'\r\n', 1)[0].decode(errors='replace').split()
        path = first[1] if len(first) > 1 else ''
        is_session = b'upgrade: websocket' in head.lower()
        ready = self.state in ('v3', 'flux')
        if not ready:
            if path.startswith(KEEPALIVE) and self.state in ('switching', 'down'):
                await reply(writer, 200, b'{"alive_seconds": null}', 'application/json')
            else:
                await reply(writer, 503, b'', 'text/plain')
            return
        try:
            br, bw = await asyncio.open_connection('127.0.0.1', self.port)
        except OSError:
            await reply(writer, 503, b'', 'text/plain')
            return
        if is_session:
            self.sessions += 1
        try:
            bw.write(head)
            await bw.drain()
            await asyncio.gather(pipe(reader, bw), pipe(br, writer))
        finally:
            if is_session:
                self.sessions -= 1
            for w in (bw, writer):
                w.close()


async def pipe(src: asyncio.StreamReader, dst: asyncio.StreamWriter) -> None:
    try:
        while data := await src.read(1 << 16):
            dst.write(data)
            await dst.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        try:
            dst.write_eof()
        except (OSError, RuntimeError):
            pass


async def reply(writer: asyncio.StreamWriter, code: int, body: bytes, ctype: str) -> None:
    text = {200: 'OK', 503: 'Service Unavailable'}[code]
    writer.write(
        f'HTTP/1.1 {code} {text}\r\nContent-Type: {ctype}\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n'
        .encode() + body
    )
    try:
        await writer.drain()
    finally:
        writer.close()


async def keepalive_ok(port: int) -> bool:
    try:
        r, w = await asyncio.wait_for(asyncio.open_connection('127.0.0.1', port), 3)
    except (OSError, asyncio.TimeoutError):
        return False
    try:
        token = os.environ.get('AUTH_TOKEN')
        auth = f'Authorization: Bearer {token}\r\n' if token else ''
        w.write(f'POST {KEEPALIVE} HTTP/1.1\r\nHost: localhost\r\n{auth}Content-Length: 0\r\nConnection: close\r\n\r\n'.encode())
        await w.drain()
        status = await asyncio.wait_for(r.readline(), 5)
        return b' 200 ' in status
    except (OSError, asyncio.TimeoutError):
        return False
    finally:
        w.close()


async def main() -> None:
    router = Router()
    server = await asyncio.start_server(router.handle, '0.0.0.0', FRONT_PORT)
    say(f'front on port {FRONT_PORT}')
    loop = asyncio.get_running_loop()
    stop = asyncio.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    if await router.start('v3'):
        router.state = 'v3'
    else:
        say('v3 did not start; trying FLUX')
        router.decided = True
        if await router.start('flux'):
            router.state = 'flux'
    async with server:
        await stop.wait()
    await router.stop()


if __name__ == '__main__':
    asyncio.run(main())
