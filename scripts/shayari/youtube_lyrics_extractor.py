#!/usr/bin/env python3
"""
YouTube → MP3 → Lyrics JSON with Timestamps  (Multilingual)
=============================================================
Supports ALL languages Whisper knows — auto-detected by default:
  English, Hindi (हिन्दी), Marathi (मराठी), Spanish (Español),
  French, Arabic, Japanese, Korean, Tamil, Telugu, Punjabi,
  Bengali, Gujarati, Urdu, Portuguese, German, Italian, and 99 more.

Uses:
  - yt-dlp        : download YouTube audio (free, no API key)
  - openai-whisper: local multilingual speech-to-text (free, runs offline)
  - ffmpeg        : audio conversion (free)

Install dependencies:
    pip install yt-dlp openai-whisper
    # Also install ffmpeg:
    # Ubuntu/Debian: sudo apt install ffmpeg
    # macOS:         brew install ffmpeg
    # Windows:       https://ffmpeg.org/download.html

Language codes (use with --language flag):
    en=English, hi=Hindi, mr=Marathi, es=Spanish, fr=French,
    ar=Arabic, ja=Japanese, ko=Korean, ta=Tamil, te=Telugu,
    pa=Punjabi, bn=Bengali, gu=Gujarati, ur=Urdu, pt=Portuguese,
    de=German, it=Italian, ru=Russian, zh=Chinese, nl=Dutch
    (Full list: https://github.com/openai/whisper#available-models-and-languages)
"""

import os
import re
import sys
import json
import argparse
import subprocess
from pathlib import Path

# Fix Windows console encoding for emoji/Unicode characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ──────────────────────────────────────────────
# 1. Download YouTube video as MP3
# ──────────────────────────────────────────────

def download_audio(youtube_url: str, output_dir: str = ".", cookies_from_browser: str | None = "chrome") -> str:
    """
    Download audio from a YouTube URL and save as MP3.
    Returns the path to the saved MP3 file.
    """
    try:
        import yt_dlp
    except ImportError:
        print("❌ yt-dlp not installed. Run: pip install yt-dlp")
        sys.exit(1)

    output_template = os.path.join(output_dir, "%(title)s.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": False,
        "no_warnings": False,
    }

    # Use browser cookies to bypass YouTube sign-in / bot detection
    if cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = (cookies_from_browser,)

    # Initialize mp3_path
    mp3_path = ""

    # 1. Get Info first to know the title and check if MP3 exists
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            title = info.get("title", "audio")
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
            mp3_path = os.path.join(output_dir, f"{safe_title}.mp3")

            if os.path.exists(mp3_path):
                print(f"[OK] MP3 already exists: {mp3_path}")
                return mp3_path
    except Exception as e:
        print(f"(!) Warning: Could not get info or check for existing file: {e}")
        # If info extraction fails, proceed to download attempt without pre-check
        pass

    # 2. Download if not found or if info extraction failed
    if not os.path.exists(mp3_path): # Re-check in case mp3_path was set but file not found
        print(f"\n[INFO] Downloading audio: {youtube_url}")
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 1. Get Info
                info = ydl.extract_info(youtube_url, download=False)
                title = info.get("title", "audio")

                # Use yt-dlp's own filename logic
                base_path = ydl.prepare_filename(info)
                mp3_path = str(Path(base_path).with_suffix(".mp3"))

                # 2. Check if this specific MP3 exists
                if os.path.exists(mp3_path):
                    print(f"[OK] MP3 already exists: {mp3_path}")
                    return mp3_path

                # 3. Download if not
                print(f"\n[INFO] Downloading audio: {title}")
                ydl.download([youtube_url])

                # Final check of the path
                if not os.path.exists(mp3_path):
                    # Fallback: look for ANY .mp3 in output_dir that was just created
                    mp3_files = sorted(Path(output_dir).glob("*.mp3"), key=os.path.getmtime, reverse=True)
                    if mp3_files:
                        mp3_path = str(mp3_files[0])

        except Exception as e:
            print(f"(!) Warning: Task failed: {e}")
            # Try once more with a broad search
            mp3_files = sorted(Path(output_dir).glob("*.mp3"), key=os.path.getmtime, reverse=True)
            if not mp3_files:
                raise e
            mp3_path = str(mp3_files[0])

    print(f"[OK] MP3 ready: {mp3_path}")
    return mp3_path


# ──────────────────────────────────────────────
# 2. Transcribe MP3 with Whisper (local, free)
# ──────────────────────────────────────────────

def transcribe_audio(
    mp3_path: str,
    model_name: str = "base",
    language: str | None = None,
) -> tuple[list[dict], str]:
    """
    Transcribe an MP3 using OpenAI Whisper (runs locally, 100% free).

    Supports 99+ languages — auto-detected when language=None.
    Pass an ISO-639-1 code (e.g. 'hi', 'mr', 'es') to force a language.

    Returns:
        segments : list of { "start", "end", "text" }
        detected_language : the language code Whisper detected/used
    """
    try:
        import whisper
    except ImportError:
        print("❌ openai-whisper not installed. Run: pip install openai-whisper")
        sys.exit(1)

    # For non-English languages, 'medium' or 'large' gives much better results.
    # Warn the user if they're using tiny/base with a forced non-English language.
    if language and language != "en" and model_name in ("tiny", "base"):
        print(
            f"⚠️  Tip: For non-English languages ('{language}'), "
            "accuracy improves significantly with --model small/medium/large."
        )

    print(f"\n[INFO] Loading Whisper model '{model_name}'...")
    model = whisper.load_model(model_name)

    transcribe_kwargs = {
        "task": "transcribe",
        "verbose": False,
    }

    if language:
        transcribe_kwargs["language"] = language
        print(f"[Language] Forced: {language}")
    else:
        print("[Language] Auto-detect")

    print(f"[Whisper] Transcribing: {mp3_path}")
    result = model.transcribe(mp3_path, **transcribe_kwargs)

    detected_language = result.get("language", language or "unknown")
    print(f"[OK] Detected language: {detected_language}")

    segments = []
    for seg in result.get("segments", []):
        segments.append(
            {
                "start": round(seg["start"], 2),
                "end": round(seg["end"], 2),
                "text": seg["text"].strip(),
            }
        )

    print(f"[OK] Transcription complete — {len(segments)} segments found.")
    return segments, detected_language


# ──────────────────────────────────────────────
# 3. Build lyrics JSON
# ──────────────────────────────────────────────

def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS.ms format, e.g. 01:23.45"""
    minutes = int(seconds // 60)
    secs = seconds - minutes * 60
    return f"{minutes:02d}:{secs:05.2f}"


def build_lyrics_json(
    segments: list[dict],
    title: str = "Unknown Song",
    language: str = "unknown",
) -> dict:
    """
    Build the final lyrics JSON structure with language metadata.
    """
    lyrics_lines = []
    for seg in segments:
        lyrics_lines.append(
            {
                "timestamp": format_timestamp(seg["start"]),
                "timestamp_seconds": seg["start"],
                "end_timestamp": format_timestamp(seg["end"]),
                "end_timestamp_seconds": seg["end"],
                "line": seg["text"],
            }
        )

    # Also build a plain lyrics string (like the example in the prompt)
    plain_lyrics = "\n".join(seg["text"] for seg in segments)

    return {
        "title": title,
        "language": language,
        "lyrics_with_timestamps": lyrics_lines,
        "plain_lyrics": plain_lyrics,
    }


# ──────────────────────────────────────────────
# 4. Main pipeline
# ──────────────────────────────────────────────

def process_youtube_url(
    youtube_url: str,
    output_dir: str = ".",
    whisper_model: str = "base",
    language: str | None = None,
    keep_mp3: bool = True,
    cookies_from_browser: str | None = "chrome",
) -> str:
    """
    Full pipeline: YouTube URL → MP3 → transcription → lyrics JSON.
    Returns path to the saved JSON file.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Download
    mp3_path = download_audio(youtube_url, output_dir, cookies_from_browser=cookies_from_browser)

    # Step 2: Transcribe (auto-detect or forced language)
    segments, detected_language = transcribe_audio(
        mp3_path, model_name=whisper_model, language=language
    )

    # Step 3: Build JSON
    title = Path(mp3_path).stem
    lyrics_data = build_lyrics_json(segments, title=title, language=detected_language)

    # Step 4: Save JSON
    json_path = os.path.join(output_dir, f"{title}_lyrics.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(lyrics_data, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Lyrics JSON saved: {json_path}")
    print(f"[Language] In JSON : {detected_language}")

    if not keep_mp3:
        os.remove(mp3_path)
        print(f"[-] MP3 deleted: {mp3_path}")

    # Preview
    print("\n── Preview (first 5 lines) ──────────────────────────")
    for line in lyrics_data["lyrics_with_timestamps"][:5]:
        print(f"  [{line['timestamp']}]  {line['line']}")
    print("─────────────────────────────────────────────────────\n")

    return json_path


# ──────────────────────────────────────────────
# 5. CLI entry point
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Download a YouTube video as MP3 and extract lyrics with timestamps."
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="YouTube video URL (omit to use the hard-coded demo URL)",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="output",
        help="Directory to save MP3 and JSON files (default: ./output)",
    )
    parser.add_argument(
        "--model", "-m",
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: base). Larger = more accurate but slower.",
    )
    parser.add_argument(
        "--language", "-l",
        default=None,
        metavar="LANG_CODE",
        help=(
            "Force a language (ISO 639-1 code). "
            "Default: auto-detect. "
            "Examples: en, hi, mr, es, fr, ar, ja, ko, ta, te, bn, gu, ur, pt, de, it, ru, zh"
        ),
    )
    parser.add_argument(
        "--delete-mp3",
        action="store_true",
        help="Delete the MP3 after transcription (keeps JSON only)",
    )
    parser.add_argument(
        "--cookies-from-browser", "-c",
        default="chrome",
        metavar="BROWSER",
        help=(
            "Browser to extract cookies from (default: chrome). "
            "Options: chrome, firefox, edge, safari, opera, brave. "
            "Use 'none' to disable."
        ),
    )
    args = parser.parse_args()

    # Demo URL if none provided
    url = args.url or "https://www.youtube.com/watch?v=7wtfhZwyrcc"  # Believer – Imagine Dragons

    # Parse cookies browser option
    cookies_browser = args.cookies_from_browser
    if cookies_browser and cookies_browser.lower() == "none":
        cookies_browser = None

    process_youtube_url(
        youtube_url=url,
        output_dir=args.output_dir,
        whisper_model=args.model,
        language=args.language,
        keep_mp3=not args.delete_mp3,
        cookies_from_browser=cookies_browser,
    )


if __name__ == "__main__":
    main()