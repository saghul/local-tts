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
    input_queue: asyncio.Queue[str | None] = asyncio.Queue()

    async def _read_input_loop() -> None:
        while True:
            try:
                text = await loop.run_in_executor(None, _read_input)
                await input_queue.put(text)
            except EOFError:
                await input_queue.put(None)
                break

    input_task = asyncio.create_task(_read_input_loop())

    try:
        while True:
            text = await input_queue.get()
            if text is None:
                break

            cmd = text.strip().lower()
            if cmd == "/quit":
                break
            if cmd == "/interrupt":
                continue
            if not text.strip():
                continue

            await _synthesize_with_interrupt(client, player, text, speed, input_queue)

    except KeyboardInterrupt:
        print()
    finally:
        input_task.cancel()


async def _synthesize_with_interrupt(
    client: TTSHTTPClient,
    player: AudioPlayer,
    text: str,
    speed: float,
    input_queue: asyncio.Queue[str | None],
) -> None:
    player.start()
    loop = asyncio.get_running_loop()

    def _stream_to_player() -> None:
        try:
            for chunk in client.synthesize(text, speed=speed):
                player.play_chunk(chunk)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)

    synth_task = asyncio.ensure_future(loop.run_in_executor(None, _stream_to_player))

    while not synth_task.done():
        input_wait = asyncio.create_task(input_queue.get())
        done, _ = await asyncio.wait(
            {synth_task, input_wait},
            return_when=asyncio.FIRST_COMPLETED,
        )

        if input_wait in done:
            cmd = input_wait.result()
            if cmd is not None and cmd.strip().lower() == "/interrupt":
                synth_task.cancel()
                player.interrupt()
                print("Interrupted.")
                return
            elif cmd is not None and cmd.strip().lower() == "/quit":
                synth_task.cancel()
                player.interrupt()
                await input_queue.put(cmd)
                return
        else:
            input_wait.cancel()

    try:
        await synth_task
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)

    player.stop()


def _read_input() -> str:
    return input("> ")


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
