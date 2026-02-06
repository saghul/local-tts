from __future__ import annotations

import asyncio
import sys

from .http import TTSHTTPClient
from .player import AudioPlayer


async def run_repl(server_url: str, voice_id: str, model_id: str, speed: float) -> None:
    client = TTSHTTPClient(server_url, voice_id, model_id)
    player = AudioPlayer()

    print(f"Server: {server_url}")
    print(f"Model: {model_id}, Voice: {voice_id}")
    print("Type text and press Enter to synthesize.")
    print("Commands: /quit  /interrupt\n")

    loop = asyncio.get_running_loop()
    stdin_reader = asyncio.StreamReader()
    transport, _ = await loop.connect_read_pipe(
        lambda: asyncio.StreamReaderProtocol(stdin_reader), sys.stdin
    )

    pending_read: asyncio.Task[bytes] | None = None

    try:
        while True:
            if pending_read is None:
                sys.stdout.write("> ")
                sys.stdout.flush()
                pending_read = asyncio.ensure_future(stdin_reader.readline())

            line = await pending_read
            pending_read = None

            if not line:  # EOF
                break

            text = line.decode().rstrip("\n")
            cmd = text.strip().lower()
            if cmd == "/quit":
                break
            if cmd == "/interrupt":
                continue
            if not text.strip():
                continue

            quit_requested, pending_read = await _synthesize_with_interrupt(
                client, player, text, speed, stdin_reader
            )
            if quit_requested:
                break

    except KeyboardInterrupt:
        print()
    finally:
        if pending_read is not None and not pending_read.done():
            pending_read.cancel()
        transport.close()


async def _synthesize_with_interrupt(
    client: TTSHTTPClient,
    player: AudioPlayer,
    text: str,
    speed: float,
    stdin_reader: asyncio.StreamReader,
) -> tuple[bool, asyncio.Task[bytes] | None]:
    """Run synthesis with interrupt support.

    Returns (quit_requested, pending_readline_task).
    """
    player.start()
    loop = asyncio.get_running_loop()

    def _stream_to_player() -> None:
        try:
            for chunk in client.synthesize(text, speed=speed):
                player.play_chunk(chunk)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)

    synth_task = asyncio.ensure_future(loop.run_in_executor(None, _stream_to_player))
    pending_read: asyncio.Task[bytes] | None = None

    while not synth_task.done():
        if pending_read is None:
            sys.stdout.write("> ")
            sys.stdout.flush()
            pending_read = asyncio.ensure_future(stdin_reader.readline())

        done, _ = await asyncio.wait(
            {synth_task, pending_read},
            return_when=asyncio.FIRST_COMPLETED,
        )

        if pending_read in done:
            line = pending_read.result()
            pending_read = None
            if not line:  # EOF
                synth_task.cancel()
                player.interrupt()
                return True, None
            cmd = line.decode().rstrip("\n").strip().lower()
            if cmd == "/interrupt":
                synth_task.cancel()
                player.interrupt()
                print("Interrupted.")
                return False, None
            if cmd == "/quit":
                synth_task.cancel()
                player.interrupt()
                return True, None
            # Other input during synthesis is ignored

    try:
        await synth_task
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)

    player.stop()
    return False, pending_read


async def run_once(server_url: str, voice_id: str, model_id: str, speed: float, text: str) -> None:
    client = TTSHTTPClient(server_url, voice_id, model_id)
    player = AudioPlayer()

    player.start()
    try:
        for chunk in client.synthesize(text, speed=speed):
            player.play_chunk(chunk)
        player.drain()
    finally:
        player.stop()
