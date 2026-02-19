# local-tts

Local TTS server with an [ElevenLabs](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-as-stream)-compatible API. Runs entirely on your machine using [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M), [Pocket TTS](https://huggingface.co/kyutai-labs/pocketlm-tts-pretrained-600M), and [KittenTTS](https://github.com/KittenML/KittenTTS) models.

## Features

- ElevenLabs-compatible HTTP and WebSocket streaming APIs
- Three TTS engines loaded simultaneously: Kokoro (82M params), Pocket TTS (600M params), and KittenTTS (15M-80M params)
- 24 kHz 16-bit signed PCM audio output
- Models downloaded and cached automatically on first run
- Built-in CLI client with interactive REPL and one-shot modes

## Requirements

- Python >= 3.10, < 3.13
- [uv](https://docs.astral.sh/uv/) package manager

## Installation

```bash
# Clone the repository
git clone https://github.com/saghul/local-tts.git
cd local-tts

# Install dependencies (uv will create a virtual environment automatically)
uv sync
```

On first server startup, model weights are downloaded from Hugging Face Hub and cached
in `~/.cache/huggingface/hub/`. Subsequent startups only perform a quick validation
request — the models are **not** re-downloaded.

## Quick start

Start the server:

```bash
uv run local-tts server
```

In another terminal, run the client:

```bash
# Interactive REPL — type text and press Enter to synthesize,
# use /interrupt to stop playback, /quit to exit
uv run local-tts client

# One-shot mode
uv run local-tts client -t "Hello, world!"
```

## Usage

### Server

```
uv run local-tts server [--host HOST] [--port PORT] [--kitten-model-size SIZE]
                        [--no-preload] [--disable-kokoro] [--disable-pocket] [--disable-kitten]
```

| Option | Default | Description |
|---|---|---|
| `--host` | `0.0.0.0` | Bind address |
| `--port` | `8880` | Bind port |
| `--kitten-model-size` | `micro` | KittenTTS model size: `mini`, `micro`, `nano`, or `nano-int8` |
| `--no-preload` | | Skip preloading models at startup (lazy-load on first request instead) |
| `--disable-kokoro` | | Disable the Kokoro engine |
| `--disable-pocket` | | Disable the Pocket TTS engine |
| `--disable-kitten` | | Disable the KittenTTS engine |

By default all models are preloaded at startup, so the first request is served without
delay. Use `--no-preload` to skip this and load models lazily on first use. Disabled
engines are not registered at all — any API request targeting a disabled engine will
return an error.

**KittenTTS model sizes**

| Size | Parameters | File Size | HuggingFace model |
|---|---|---|---|
| `mini` | 80M | 80 MB | `KittenML/kitten-tts-mini-0.8` |
| `micro` | 40M | 41 MB | `KittenML/kitten-tts-micro-0.8` |
| `nano` | 15M | 56 MB | `KittenML/kitten-tts-nano-0.8` |
| `nano-int8` | 15M | 19 MB | `KittenML/kitten-tts-nano-0.8-int8` |

### Client

```
uv run local-tts client [--server URL] [--voice VOICE_ID] [--model MODEL_ID] [--speed SPEED] [-t TEXT]
```

| Option | Default | Description |
|---|---|---|
| `--server` | `http://localhost:8880` | Server URL |
| `--voice` | `af_heart` | Voice ID (see [Voices](#voices)) |
| `--model` | `kokoro` | Model ID: `kokoro`, `pocket`, or `kitten` |
| `--speed` | `1.0` | Speech speed multiplier (0.25 - 4.0) |
| `-t, --text` | | Text to synthesize (skip REPL) |

When launched without `-t`, the client starts an interactive REPL. Type any text and
press Enter to synthesize and play it through the default audio output device.

#### REPL commands

| Command | Description |
|---|---|
| `/quit` | Exit the REPL |
| `/interrupt` | Stop current playback immediately |

## API reference

All endpoints follow the [ElevenLabs API](https://elevenlabs.io/docs/api-reference) conventions.

Audio is returned as **raw PCM**: 24 kHz, 16-bit signed integer, mono, little-endian.

### `POST /v1/text-to-speech/{voice_id}/stream`

Synthesize text and stream audio back as raw PCM bytes.

**Path parameters**

| Parameter | Type | Description |
|---|---|---|
| `voice_id` | string | Voice identifier (see [Voices](#voices)) |

**Query parameters**

| Parameter | Default | Description |
|---|---|---|
| `output_format` | `pcm_24000` | Output format (only `pcm_24000` supported) |

**Request body** (`application/json`)

```json
{
  "text": "Hello, world!",
  "model_id": "kokoro",
  "voice_settings": {
    "speed": 1.0
  }
}
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `text` | string | yes | | Text to synthesize |
| `model_id` | string | no | `kokoro` | Engine to use: `kokoro`, `pocket`, or `kitten` |
| `voice_settings` | object | no | | Optional voice settings |
| `voice_settings.speed` | float | no | `1.0` | Speed multiplier (0.25 - 4.0) |

**Response**

- Content-Type: `audio/pcm;rate=24000;encoding=signed-int;bits=16`
- Body: streaming raw PCM bytes

**Example with curl**

```bash
curl -X POST http://localhost:8880/v1/text-to-speech/af_heart/stream \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, world!", "model_id": "kokoro"}' \
  --output audio.pcm
```

Play the resulting file (requires ffplay/sox):

```bash
ffplay -f s16le -ar 24000 -ac 1 audio.pcm
# or
play -t raw -r 24000 -b 16 -e signed -c 1 audio.pcm
```

### `WS /v1/text-to-speech/{voice_id}/stream-input`

WebSocket endpoint for streaming text input and receiving audio output. Follows the
ElevenLabs [input streaming](https://elevenlabs.io/docs/api-reference/text-to-speech/websockets) protocol.

**Connection URL**

```
ws://localhost:8880/v1/text-to-speech/{voice_id}/stream-input?model_id=kokoro
```

**Query parameters**

| Parameter | Default | Description |
|---|---|---|
| `model_id` | `kokoro` | Engine to use: `kokoro`, `pocket`, or `kitten` |
| `output_format` | `pcm_24000` | Output format (only `pcm_24000` supported) |

**Protocol**

1. **BOS (Beginning of Stream)** -- send a message with a single space as text to start a new synthesis session:
   ```json
   {"text": " ", "voice_settings": {"speed": 1.0}}
   ```

2. **Text messages** -- send text chunks:
   ```json
   {"text": "Hello, ", "try_trigger_generation": true}
   ```
   Set `"flush": true` to force immediate generation of accumulated text.

3. **EOS (End of Stream)** -- send an empty string to finalize:
   ```json
   {"text": ""}
   ```

**Server responses**

Audio chunks are sent as JSON with base64-encoded PCM:

```json
{"audio": "base64-encoded-pcm-bytes", "isFinal": false}
```

The final message after EOS processing:

```json
{"audio": "", "isFinal": true}
```

### `GET /v1/voices`

List available voices for a given model.

**Query parameters**

| Parameter | Default | Description |
|---|---|---|
| `model_id` | `kokoro` | Engine to query |

**Response** (`application/json`)

```json
[
  {
    "voice_id": "af_heart",
    "name": "Heart",
    "category": "female"
  }
]
```

### `GET /v1/models`

List available TTS models.

**Response** (`application/json`)

```json
[
  {"model_id": "kokoro", "name": "Kokoro"},
  {"model_id": "pocket", "name": "Pocket"},
  {"model_id": "kitten", "name": "Kitten"}
]
```

## Voices

### Kokoro voices

#### American English

| Voice ID | Name | Gender |
|---|---|---|
| `af_heart` | Heart | female |
| `af_alloy` | Alloy | female |
| `af_aoede` | Aoede | female |
| `af_bella` | Bella | female |
| `af_jessica` | Jessica | female |
| `af_kore` | Kore | female |
| `af_nicole` | Nicole | female |
| `af_nova` | Nova | female |
| `af_river` | River | female |
| `af_sarah` | Sarah | female |
| `af_sky` | Sky | female |
| `am_adam` | Adam | male |
| `am_echo` | Echo | male |
| `am_eric` | Eric | male |
| `am_fenrir` | Fenrir | male |
| `am_liam` | Liam | male |
| `am_michael` | Michael | male |
| `am_onyx` | Onyx | male |
| `am_puck` | Puck | male |
| `am_santa` | Santa | male |

#### British English

| Voice ID | Name | Gender |
|---|---|---|
| `bf_alice` | Alice | female |
| `bf_emma` | Emma | female |
| `bf_isabella` | Isabella | female |
| `bf_lily` | Lily | female |
| `bm_daniel` | Daniel | male |
| `bm_fable` | Fable | male |
| `bm_george` | George | male |
| `bm_lewis` | Lewis | male |

### Pocket TTS voices

| Voice ID | Name | Gender |
|---|---|---|
| `alba` | Alba | female |
| `fantine` | Fantine | female |
| `cosette` | Cosette | female |
| `eponine` | Eponine | female |
| `azelma` | Azelma | female |
| `marius` | Marius | male |
| `javert` | Javert | male |
| `jean` | Jean | male |

### KittenTTS voices

| Voice ID | Name | Gender |
|---|---|---|
| `bella` | Bella | female |
| `jasper` | Jasper | male |
| `luna` | Luna | female |
| `bruno` | Bruno | male |
| `rosie` | Rosie | female |
| `hugo` | Hugo | male |
| `kiki` | Kiki | female |
| `leo` | Leo | male |

## Audio format

All audio is output as **raw PCM** with the following parameters:

| Property | Value |
|---|---|
| Sample rate | 24,000 Hz |
| Bit depth | 16-bit |
| Encoding | Signed integer |
| Channels | Mono |
| Byte order | Little-endian |

## Development

```bash
# Install dev dependencies
uv sync --group dev

# Run tests
uv run pytest tests/ -v
```

## TODO

### Kokoro: additional language support

Kokoro currently only runs with English (`lang_code='a'` for American, `'b'` for British).
Supporting other languages requires additional dependencies:

| Language | Lang code | Extra dependency |
|---|---|---|
| Japanese | `j` | `misaki[ja]` (Python package) |
| Mandarin Chinese | `z` | `misaki[zh]` (Python package) |
| Spanish | `e` | `espeak-ng` (system package) |
| French | `f` | `espeak-ng` (system package) |
| Hindi | `h` | `espeak-ng` (system package) |
| Italian | `i` | `espeak-ng` (system package) |
| Brazilian Portuguese | `p` | `espeak-ng` (system package) |

The `misaki` extras could be added as optional dependencies in `pyproject.toml`.
`espeak-ng` is a system-level package (e.g. `brew install espeak-ng` on macOS)
and would need to be documented as a prerequisite.
