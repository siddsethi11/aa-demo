#!/usr/bin/env python3
"""
Kong Audio Routing Demo — Hindi → English via OpenAI Whisper

Flow:
  Step 1: POST /audio/speech        → Kong → OpenAI TTS-1    (text → Hindi MP3)
  Step 2: POST /audio/translations  → Kong → OpenAI Whisper  (Hindi MP3 → English)

Both calls go through Kong. Kong injects the OpenAI auth header; the client
only needs the Kong API key.

Usage:
  python demo.py                              # full demo with built-in Hindi sample
  python demo.py --text "आज बहुत गर्मी है।"  # custom Hindi text
  python demo.py --translate-file audio.mp3   # translate an existing audio file
"""

import argparse
import os
import sys
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Config — override via environment variables
# ---------------------------------------------------------------------------
KONG_URL = os.getenv("KONG_URL", "http://localhost:8000").rstrip("/")
API_KEY  = os.getenv("AUDIO_DEMO_API_KEY", "audio-demo-key")

AUDIO_ROUTE_SPEECH       = f"{KONG_URL}/audio/speech"
AUDIO_ROUTE_TRANSLATION  = f"{KONG_URL}/audio/translations"

DEFAULT_OUTPUT = Path(__file__).parent / "sample_hindi.mp3"

# A small set of Hindi sentences to choose from in the default demo run
SAMPLE_SENTENCES = [
    "यद्यपि आज की आधुनिक और भागदौड़ भरी जिंदगी में विज्ञान ने हमें अनेक प्रकार की सुख-सुविधाएं और तकनीकी साधन प्रदान किए हैं, फिर भी मानसिक शांति और आंतरिक संतोष पाने के लिए मनुष्य को अंततः प्रकृति की शरण में ही जाना पड़ता है।",        # Hello, how can I help you?
    "आज का मौसम बहुत अच्छा है।",                       # Today's weather is very good.
    "कृपया मुझे बताएं कि यह कैसे काम करता है।",        # Please tell me how this works.
    "मुझे एक रिपोर्ट तैयार करनी है।",                   # I need to prepare a report.
]

HEADERS = {"apikey": API_KEY}


# ---------------------------------------------------------------------------
# Step 1: Text → Hindi speech via Kong → OpenAI TTS-1
# ---------------------------------------------------------------------------
def generate_hindi_audio(text: str, output_path: Path) -> None:
    """
    Calls Kong /audio/speech which proxies to OpenAI TTS-1.
    Kong injects the OpenAI Authorization header; client sends only 'apikey'.
    """
    print(f"\n[STEP 1] Generating Hindi speech via Kong → OpenAI TTS-1")
    print(f"  Route : POST {AUDIO_ROUTE_SPEECH}")
    print(f"  Text  : {text}")

    try:
        response = httpx.post(
            AUDIO_ROUTE_SPEECH,
            headers={**HEADERS, "Content-Type": "application/json"},
            json={
                "model": "tts-1",
                "input": text,
                "voice": "alloy",           # alloy | echo | fable | onyx | nova | shimmer
                "response_format": "mp3",
            },
            timeout=60.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        print(f"\n  ERROR {exc.response.status_code}: {exc.response.text}")
        sys.exit(1)
    except httpx.ConnectError:
        print(f"\n  ERROR: Could not connect to Kong at {KONG_URL}")
        print("  Make sure the demo stack is running and KONG_URL is correct.")
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)
    print(f"  Saved : {output_path}  ({len(response.content):,} bytes)")


# ---------------------------------------------------------------------------
# Step 2: Hindi audio → English translation via Kong → OpenAI Whisper-1
# ---------------------------------------------------------------------------
def translate_audio_to_english(audio_path: Path) -> str:
    """
    Calls Kong /audio/translations which proxies to OpenAI Whisper-1.
    Whisper detects the source language and translates directly to English.
    """
    print(f"\n[STEP 2] Translating audio via Kong → OpenAI Whisper-1")
    print(f"  Route : POST {AUDIO_ROUTE_TRANSLATION}")
    print(f"  File  : {audio_path}  ({audio_path.stat().st_size:,} bytes)")

    try:
        with open(audio_path, "rb") as audio_file:
            response = httpx.post(
                AUDIO_ROUTE_TRANSLATION,
                headers=HEADERS,
                files={"file": (audio_path.name, audio_file, "audio/mpeg")},
                data={"model": "whisper-1"},
                timeout=120.0,
            )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        print(f"\n  ERROR {exc.response.status_code}: {exc.response.text}")
        sys.exit(1)
    except httpx.ConnectError:
        print(f"\n  ERROR: Could not connect to Kong at {KONG_URL}")
        sys.exit(1)

    result = response.json()
    return result.get("text", "").strip()


# ---------------------------------------------------------------------------
# Full end-to-end demo
# ---------------------------------------------------------------------------
def run_full_demo(hindi_text: str) -> None:
    _banner()
    generate_hindi_audio(hindi_text, DEFAULT_OUTPUT)
    english = translate_audio_to_english(DEFAULT_OUTPUT)
    _result(hindi_text, english)


def run_translate_only(audio_file: str) -> None:
    path = Path(audio_file)
    if not path.exists():
        print(f"ERROR: File not found: {audio_file}")
        sys.exit(1)
    _banner(tts=False)
    english = translate_audio_to_english(path)
    _result(None, english)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _banner(tts: bool = True) -> None:
    print()
    print("=" * 60)
    print("Kong Audio Routing Demo: Hindi → English via Whisper")
    print("=" * 60)
    print(f"  Kong URL  : {KONG_URL}")
    if tts:
        print(f"  TTS route : {AUDIO_ROUTE_SPEECH}")
        print(f"               └─► OpenAI TTS-1  (text → Hindi audio)")
    print(f"  Whis route: {AUDIO_ROUTE_TRANSLATION}")
    print(f"               └─► OpenAI Whisper-1 (audio → English)")


def _result(hindi: str | None, english: str) -> None:
    print()
    print("[RESULT]")
    if hindi:
        print(f"  Hindi input   : {hindi}")
    print(f"  English output: {english}")
    print()
    print("Done. All calls were routed through Kong.")
    print("Check Grafana/Loki for the request logs.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Hindi → English audio translation demo via Kong Gateway",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--text",
        default=SAMPLE_SENTENCES[0],
        help="Hindi text to synthesise and translate (default: built-in sample)",
    )
    parser.add_argument(
        "--translate-file",
        metavar="AUDIO_FILE",
        help="Translate an existing audio file; skip the TTS step",
    )
    args = parser.parse_args()

    if args.translate_file:
        run_translate_only(args.translate_file)
    else:
        run_full_demo(args.text)
