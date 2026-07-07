# Kong Audio Routing Demo — Hindi → English via OpenAI Whisper

This mini-demo shows Kong routing **audio requests** to OpenAI models:

| Kong Route               | Plugin              | route_type                    | Model       | Purpose                     |
|--------------------------|---------------------|-------------------------------|-------------|-----------------------------||
| `POST /audio/speech`     | ai-proxy-advanced   | `audio/v1/audio/speech`       | `tts-1`     | Text → Hindi speech (MP3)   |
| `POST /audio/translations` | ai-proxy-advanced | `audio/v1/audio/translations` | `whisper-1` | Audio → English translation |

Kong sits in the middle of **both** calls — providing auth injection, key-auth enforcement, and logging for every audio hop.

---

## Architecture

```
You / UI
   │
   │  POST /audio/speech       (Hindi text → MP3)
   ▼
Kong Gateway  ──── key-auth ────► OpenAI TTS-1
   │                              (generates Hindi speech)
   │
   │  POST /audio/translations  (Hindi MP3 → English text)
   ▼
Kong Gateway  ──── key-auth ────► OpenAI Whisper-1
                                  (translates to English)
```

Kong injects the OpenAI `Authorization` header via `request-transformer` — the client only needs the Kong API key.

---

## Prerequisites

- Kong demo stack running (`docker compose up` from the `aa-demo` root)
- The `kong_audio.yaml` applied to Kong (see step 3 below)
- Python 3.10+

---

## Setup Steps

### 1. Install Python dependencies

```bash
cd audio
pip install -r requirements.txt
```

### 2. Set environment variables

```bash
export KONG_URL=http://localhost:8000
export AUDIO_DEMO_API_KEY=audio-demo-key     # matches the consumer in kong_audio.yaml
export DECK_OPENAI_API_KEY=sk-...            # your OpenAI key (used by deck sync)
```

### 3. Apply the Kong audio routes

```bash
# from aa-demo root — Kong Enterprise workspace
deck gateway apply audio/kong_audio.yaml \
  -w "$KONG_WORKSPACE" \
  --headers "Kong-Admin-Token:$KONG_ADMIN_TOKEN" \
  --kong-addr "$KONG_ADMIN_ADDR"
```

### 4. Run the end-to-end demo

```bash
# Full demo: generates Hindi audio through Kong TTS, then translates through Kong Whisper
python audio/demo.py

# Use a custom Hindi sentence
python audio/demo.py --text "मुझे अंग्रेजी में अनुवाद करें।"

# Translate an existing audio file directly (skips TTS step)
python audio/demo.py --translate-file my_hindi_audio.mp3
```

---

## What you will see

```
============================================================
Kong Audio Routing Demo: Hindi → English via Whisper
============================================================
  Kong URL:    http://localhost:8000
  TTS Route:   http://localhost:8000/audio/speech        → OpenAI TTS-1
  Whisper Route: http://localhost:8000/audio/translations → OpenAI Whisper-1

[STEP 1] Generating Hindi audio via Kong → OpenAI TTS...
  Text: नमस्ते, मैं आपकी कैसे मदद कर सकता हूँ?
  Saved to: audio/sample_hindi.mp3

[STEP 2] Translating audio via Kong → OpenAI Whisper...
  Audio file: audio/sample_hindi.mp3

[RESULT]
  Hindi input:    नमस्ते, मैं आपकी कैसे मदद कर सकता हूँ?
  English output: Hello, how can I help you?

Done. Both calls were routed through Kong.
```

---

## What Kong is demonstrating here

| Concern                | How Kong handles it                                      |
|------------------------|----------------------------------------------------------|
| **Auth isolation**     | Client sends only `apikey`; `ai-proxy-advanced` injects `Authorization` from `DECK_OPENAI_API_KEY` |
| **Route governance**   | Only POST to `/audio/speech` and `/audio/translations`   |
| **Observability**      | Requests logged to Loki like any other Kong service      |
| **Model abstraction**  | You could swap `whisper-1` for any other model in config |

---

## Sample Hindi sentences included in demo.py

| Hindi                                              | English                                   |
|----------------------------------------------------|-------------------------------------------|
| नमस्ते, मैं आपकी कैसे मदद कर सकता हूँ?           | Hello, how can I help you?                |
| आज का मौसम बहुत अच्छा है।                         | Today's weather is very good.             |
| कृपया मुझे बताएं कि यह कैसे काम करता है।          | Please tell me how this works.            |
| मुझे एक रिपोर्ट तैयार करनी है।                    | I need to prepare a report.               |
