from __future__ import annotations

import argparse
import asyncio
import sys


def run_client() -> None:
    parser = argparse.ArgumentParser(description="Local TTS client")
    parser.add_argument(
        "--server",
        default="ws://localhost:8880",
        help="Server WebSocket URL (default: ws://localhost:8880)",
    )
    parser.add_argument(
        "--voice",
        default="af_heart",
        help="Voice ID (default: af_heart)",
    )
    parser.add_argument(
        "--model",
        default="kokoro",
        help="Model ID: kokoro or pocket (default: kokoro)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Speech speed multiplier (default: 1.0)",
    )
    parser.add_argument(
        "-t", "--text",
        help="Text to synthesize (non-interactive mode)",
    )
    args = parser.parse_args()

    from .repl import run_once, run_repl

    if args.text:
        asyncio.run(run_once(args.server, args.voice, args.model, args.speed, args.text))
    else:
        asyncio.run(run_repl(args.server, args.voice, args.model, args.speed))
