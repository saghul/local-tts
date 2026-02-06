from __future__ import annotations

import asyncio
import sys

from .player import AudioPlayer
from .ws import TTSWebSocketClient


async def run_repl(server_url: str, voice_id: str, model_id: str, speed: float) -> None:
    client = TTSWebSocketClient(server_url, voice_id, model_id)
    player = AudioPlayer()

    print(f"Connecting to {server_url}...")
    await client.connect()
    print(f"Connected. Model: {model_id}, Voice: {voice_id}")
    print("Type text and press Enter to synthesize.")
    print("Commands: /quit  /interrupt\n")

    loop = asyncio.get_running_loop()
    input_queue: asyncio.Queue[str | None] = asyncio.Queue()

    async def _read_input_loop() -> None:
        """Read user input in a thread and put it on the queue."""
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
                # No active synthesis at the prompt, nothing to interrupt
                continue
            if not text.strip():
                continue

            # Synthesize and play audio, listening for /interrupt concurrently
            await _synthesize_with_interrupt(client, player, text, speed, input_queue)

    except KeyboardInterrupt:
        print()
    finally:
        input_task.cancel()
        await client.close()


async def _synthesize_with_interrupt(
    client: TTSWebSocketClient,
    player: AudioPlayer,
    text: str,
    speed: float,
    input_queue: asyncio.Queue[str | None],
) -> None:
    """Run synthesis while monitoring input_queue for /interrupt."""
    player.start()

    async def _do_synth() -> None:
        async for chunk in client.synthesize(text, speed=speed):
            player.play_chunk(chunk)
        player.drain()

    synth_task = asyncio.create_task(_do_synth())

    # Monitor for /interrupt while synthesis is running
    while not synth_task.done():
        # Wait for either synthesis to finish or new input
        input_wait = asyncio.create_task(input_queue.get())
        done, _ = await asyncio.wait(
            {synth_task, input_wait},
            return_when=asyncio.FIRST_COMPLETED,
        )

        if input_wait in done:
            cmd = input_wait.result()
            if cmd is not None and cmd.strip().lower() == "/interrupt":
                synth_task.cancel()
                try:
                    await synth_task
                except asyncio.CancelledError:
                    pass
                player.interrupt()
                print("Interrupted.")
                return
            elif cmd is not None and cmd.strip().lower() == "/quit":
                synth_task.cancel()
                try:
                    await synth_task
                except asyncio.CancelledError:
                    pass
                player.interrupt()
                # Put /quit back so the main loop sees it
                await input_queue.put(cmd)
                return
            # Ignore other input during synthesis
        else:
            input_wait.cancel()

    # Synthesis finished normally
    try:
        await synth_task
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
    finally:
        player.stop()


def _read_input() -> str:
    return input("> ")


async def run_once(server_url: str, voice_id: str, model_id: str, speed: float, text: str) -> None:
    client = TTSWebSocketClient(server_url, voice_id, model_id)
    player = AudioPlayer()

    await client.connect()
    player.start()
    try:
        async for chunk in client.synthesize(text, speed=speed):
            player.play_chunk(chunk)
        player.drain()
    finally:
        player.stop()
        await client.close()
