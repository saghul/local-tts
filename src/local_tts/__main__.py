from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="local-tts",
        description="Local TTS server with ElevenLabs-compatible API",
    )
    sub = parser.add_subparsers(dest="command")

    # Server
    sp = sub.add_parser("server", help="Start the TTS server")
    sp.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    sp.add_argument("--port", type=int, default=8880, help="Bind port (default: 8880)")

    # Client
    cp = sub.add_parser("client", help="Start the TTS client")
    cp.add_argument("--server", default="ws://localhost:8880", help="Server URL")
    cp.add_argument("--voice", default="af_heart", help="Voice ID")
    cp.add_argument("--model", default="kokoro", help="Model ID")
    cp.add_argument("--speed", type=float, default=1.0, help="Speech speed")
    cp.add_argument("-t", "--text", help="Text to synthesize (non-interactive)")

    args = parser.parse_args()

    if args.command == "server":
        from .server.main import run_server
        run_server(host=args.host, port=args.port)

    elif args.command == "client":
        import asyncio
        from .client.repl import run_once, run_repl

        if args.text:
            asyncio.run(run_once(args.server, args.voice, args.model, args.speed, args.text))
        else:
            asyncio.run(run_repl(args.server, args.voice, args.model, args.speed))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
