from __future__ import annotations

import argparse
import sys

DEFAULT_VOICES = {
    "kokoro": "af_heart",
    "pocket": "alba",
    "kitten": "bella",
}


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
    sp.add_argument(
        "--kitten-model-size",
        default="micro",
        choices=["mini", "micro", "nano", "nano-int8"],
        help="KittenTTS model size (default: micro)",
    )

    # Client
    cp = sub.add_parser(
        "client",
        help="Start the TTS client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "supported models:\n"
            "  kokoro   Kokoro TTS (82M params, English)\n"
            "           Voices: af_heart (default), af_alloy, af_bella,\n"
            "           af_jessica, af_nova, af_river, af_sarah, af_sky,\n"
            "           am_adam, am_echo, am_eric, am_michael, am_puck, ...\n"
            "  pocket   Pocket TTS (600M params, English)\n"
            "           Voices: alba (default), fantine, cosette, eponine,\n"
            "           azelma, marius, javert, jean\n"
            "  kitten   KittenTTS (15M-80M params, English)\n"
            "           Voices: bella (default), jasper, luna, bruno,\n"
            "           rosie, hugo, kiki, leo\n"
            "\n"
            "use GET /v1/voices?model_id=MODEL for the full voice list"
        ),
    )
    cp.add_argument("--server", default="http://localhost:8880", help="Server URL")
    cp.add_argument("--voice", default=None, help="Voice ID (default: per-model)")
    cp.add_argument("--model", default="kokoro", choices=DEFAULT_VOICES, help="Model ID (default: kokoro)")
    cp.add_argument("--speed", type=float, default=1.0, help="Speech speed (default: 1.0)")
    cp.add_argument("-t", "--text", help="Text to synthesize (non-interactive)")

    args = parser.parse_args()

    if args.command == "server":
        from .engines.base import KittenOptions, ModelOptions
        from .server.main import run_server

        model_options = ModelOptions(
            kitten=KittenOptions(model_size=args.kitten_model_size),
        )
        run_server(host=args.host, port=args.port, model_options=model_options)

    elif args.command == "client":
        import asyncio
        from .client.repl import run_once, run_repl

        voice = args.voice or DEFAULT_VOICES.get(args.model, "af_heart")

        if args.text:
            asyncio.run(run_once(args.server, voice, args.model, args.speed, args.text))
        else:
            asyncio.run(run_repl(args.server, voice, args.model, args.speed))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
