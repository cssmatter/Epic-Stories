#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bollywood Reel Generator
========================
Downloads YouTube audio + transcript, uses NVIDIA LLM to pick the best
2-3 Reel clips with per-line lyrics + SD3 image prompts, generates
styled 9:16 background images in RDR2 Zoological Compendium style,
and renders Instagram-ready Reels.

Usage:
  python youtube_mp3_transcript.py --url "Tum Hi Ho"
  python youtube_mp3_transcript.py --url "https://youtu.be/Vyi0vQ-HTrM?si=evtxrxzr9w9TDHbV" --skip-video
  python youtube_mp3_transcript.py --url "..." --skip-ai
"""

# ── Windows UTF-8 fix ────────────────────────────────────────────────────────
import sys
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    else:
        import os
        os.environ["PYTHONIOENCODING"] = "utf-8"

import argparse
import base64
import hashlib
import json
import logging
import os
import random
import re
import subprocess
import tempfile
import textwrap
import time
import unicodedata
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from PIL import features as pil_features
from youtube_transcript_api import YouTubeTranscriptApi

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

HAS_LIBRAQM = False
try:
    HAS_LIBRAQM = pil_features.check("raqm")
except Exception:
    HAS_LIBRAQM = False

HAS_SKIA_HB = False
try:
    import skia
    import uharfbuzz as hb
    HAS_SKIA_HB = True
except ImportError:
    HAS_SKIA_HB = False

# ── API Config ───────────────────────────────────────────────────────────────
# Keys are read from environment variables first; fallback to hardcoded values.
# Set env vars to avoid exposing keys in code:
#   set NVIDIA_API_KEY=nvapi-xxx        (Windows)
#   export NVIDIA_API_KEY=nvapi-xxx     (Linux/Mac)
NVIDIA_API_KEY = os.environ.get(
    "NVIDIA_API_KEY",
    "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",
)
NVIDIA_IMAGE_API_KEY = os.environ.get(
    "NVIDIA_IMAGE_API_KEY",
    "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",
)
NVIDIA_IMAGE_INVOKE_URL = os.environ.get(
    "NVIDIA_IMAGE_INVOKE_URL",
    "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-3-medium",
)
NVIDIA_LLM_URL   = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_LLM_MODEL = "openai/gpt-oss-120b"

# ── Video dimensions ─────────────────────────────────────────────────────────
REEL_WIDTH  = 1080
REEL_HEIGHT = 1920

# ── SD3 Negative Prompt ──────────────────────────────────────────────────────
SD3_NEGATIVE_PROMPT = (
    "blurry, low quality, watermark, text overlay, signature, logo, "
    "extra limbs, deformed hands, mutated fingers, western features, "
    "caucasian face, ugly, bad anatomy, disfigured, jpeg artifacts, "
    "photorealistic, 3D render, CGI, modern photography, color photograph, "
    "nsfw, nudity, multiple people, crowd, group"
)

# ── RDR2 Zoological Style — Parchment Mood Palettes ──────────────────────────
# Aged cream/parchment background tones matching the RDR2 compendium aesthetic
MOOD_PALETTES = {
    "romantic":   [(245, 235, 210), (210, 180, 140), (160, 110, 80)],
    "sad":        [(220, 225, 230), (170, 185, 200), (100, 120, 150)],
    "energetic":  [(248, 238, 200), (220, 170,  80), (160,  90,  30)],
    "devotional": [(250, 240, 200), (220, 190, 100), (180, 130,  40)],
    "retro":      [(240, 228, 196), (190, 160, 110), (130,  95,  55)],
    "longing":    [(235, 228, 218), (180, 160, 140), (110,  85,  75)],
    "happy":      [(245, 240, 210), (200, 185, 130), (140, 120,  70)],
    "default":    [(242, 233, 205), (200, 175, 130), (140, 100,  60)],
}

# ── System Prompt ─────────────────────────────────────────────────────────────
REEL_PROMPT = """You are an expert Bollywood Instagram Reels editor and Stable Diffusion 3 prompt engineer.

I will give you a song transcript with timestamps in [MM:SS] format.

YOUR TASKS:
1. I WANT YOU TO GO THROW ALL SONG CONTEXT FIRST.
2. Pick the 2-3 BEST clips for Instagram Reels
3. Generate one master image_style for the entire song
4. MAKE SURE EVERY SCENE AND SUBJECT SHOULD BE LIKED ORIGINAL SONG.
5. CHECK WHAT IS IN ORIGINAL SONG AND MAKE SURE TO INCLUDE THAT IN IMAGE PROMPT.
6. GIVE ME ORIGINAL SONG CONTEXT IN IMAGE PROMPT.

══════════════════════════════════════════
CLIP SELECTION RULES
══════════════════════════════════════════
- Pick the 2-3 BEST clips for Instagram Reels
- Each clip MUST be 30–90 seconds long
- For each clip, include the most impactful lyric lines with their exact timestamps
- Calculate duration_seconds = end_time minus start_time in seconds
- Skip lines that are ONLY: [संगीत], [Music], [Applause], [Instrumental]
- Prioritize: hook, chorus, emotionally impactful, catchy, or viral-worthy moments

══════════════════════════════════════════
IMAGE STYLE — RDR2 ZOOLOGICAL COMPENDIUM
══════════════════════════════════════════
ALL images MUST follow this exact visual style (like Red Dead Redemption 2 wildlife cards):

MASTER STYLE (apply to every image):
- Fine ink crosshatching and stippling technique
- Subtle watercolor wash over etching
- Aged cream/parchment paper background
- Small watercolor vignette environment at subject's feet (ground/floor/petals)
- Muted warm earthy palette: sepia, amber, ochre, olive
- Soft faded atmospheric background
- Museum natural history plate aesthetic
- NO photorealism, NO modern rendering, NO color photography
- IMAGE PROMPTS MUST BE IN ENGLISH: Translate the meaning of Hindi lyrics into a descriptive English scene.
- DO NOT SKIP LINES: Every timestamped line in a clip MUST have its own unique image_prompt.


SD3 PROMPT STRUCTURE for each line:
line-specific subject and scene description,
fine ink crosshatching, watercolor wash, 
natural history plate aesthetic, highly detailed etching, 8K, no text, no watermark

══════════════════════════════════════════
COLOR THEME — Match song mood
══════════════════════════════════════════
Pick a CREATIVE deep background color and a contrasting light text color.
Examples by mood:
- Sad/Melancholy: deep navy #0D1B2A, slate blue text #A8C6E2
- Romantic/Love: wine red #2A0A1B, rose gold text #E8C5B7
- Devotional: deep saffron #2E1A00, warm gold text #F0D68A
- Nostalgic: deep purple #1A0A2E, lavender text #D5C8E8
- Energetic/Happy: deep teal #0A2A2A, bright cyan text #7EECD5
- Longing: charcoal green #0D1F0D, soft sage text #B8D4B8
RULES: Background MUST be dark (luminance < 0.15). Text MUST be light (luminance > 0.5).

══════════════════════════════════════════
OUTPUT — respond ONLY with valid JSON, no markdown, no explanation
══════════════════════════════════════════
{
  "youtube_title": "SEO title with song name, singer, film (under 100 chars)",
  "youtube_description": "A poetic emotional summary of the song (MAX 2 lines/300 chars) + singer/composer credits + 15 hashtags. Use escaped \\n sequences ONLY.",
  "background_color": "#hex dark background color matching song mood",
  "text_color": "#hex light text color with high contrast against background",
  "image_style": "",
  "style_preset": "",
  "clips": [
    {
      "clip_number": 1,
      "start_time": "MM:SS",
      "end_time": "MM:SS",
      "duration_seconds": 0,
      "reason": "Why this clip is emotionally or virally strong (1–2 sentences)",
      "lines": [
        {
          "time": "",
          "text": "",
          "emotion": "",
          "image_prompt": ""
        }
      ]
    }
  ]
}
"""

STAGE_TAG_RE = re.compile(r"\[.*?\]", re.IGNORECASE)
DEVANAGARI_CONJUNCT_RE = re.compile(r"([\u0915-\u0939\u0958-\u095f])\u094d([\u0915-\u0939\u0958-\u095f])")

# ── Color Utilities ──────────────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert '#RRGGBB' to (R, G, B) tuple."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return (0, 0, 0)  # fallback black
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


def _luminance(r: int, g: int, b: int) -> float:
    """WCAG relative luminance."""
    def _lin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def _contrast_ratio(rgb1: tuple, rgb2: tuple) -> float:
    """WCAG contrast ratio between two RGB tuples."""
    l1 = _luminance(*rgb1)
    l2 = _luminance(*rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _ensure_contrast(bg_hex: str, text_hex: str) -> tuple:
    """Ensure bg/text have >= 4.5:1 contrast. Auto-correct if not."""
    bg_rgb = _hex_to_rgb(bg_hex)
    text_rgb = _hex_to_rgb(text_hex)
    ratio = _contrast_ratio(bg_rgb, text_rgb)
    if ratio >= 4.5:
        return bg_hex, text_hex
    # Auto-correct: if bg is dark, force text to white; else force text to black
    if _luminance(*bg_rgb) < 0.5:
        return bg_hex, "#FFFFFF"
    else:
        return bg_hex, "#000000"


DEFAULT_BG_COLOR = "#000000"
DEFAULT_TEXT_COLOR = "#FFFFFF"


# ════════════════════════════════════════════════════════════════════════════
# UTILITIES
# ════════════════════════════════════════════════════════════════════════════

def _clean_lyric_text(text: str) -> str:
    """Remove inline non-lyric stage tags and normalize spacing."""
    if not text:
        return ""
    # Use NFC normalization first to prevent character splitting
    text = unicodedata.normalize("NFC", text.strip())
    text = STAGE_TAG_RE.sub(" ", text)
    text = re.sub(r"\s{2,}", " ", text)
    # Preservation: Keep punctuation like !, ?, etc. as per user request for "exact match"
    return text.strip()


def _needs_strict_conjunct_rendering(text: str) -> bool:
    """Identify if the text contains complex characters (like i-matras or halants) that require advanced shaping."""
    if not text: return False
    # \u093f is the 'i-matra' (ri, ji, etc.)
    # \u094d is the halant (conjuncts)
    return bool(text) and ("\u094d" in text or "\u093f" in text or "ि" in text or "ख्म" in text or "ज़ख्म" in text or "जख्म" in text)


def _shape_lyric_text_for_rendering(text: str) -> str:
    """Hint renderers to keep Devanagari half-forms/conjuncts stable and fix glyph order."""
    if not text: return ""
    # NFC normalization is critical for complex scripts like Hindi to stay as single units
    text = unicodedata.normalize("NFC", text.strip())
    if _needs_strict_conjunct_rendering(text):
        text = DEVANAGARI_CONJUNCT_RE.sub(
            lambda m: f"{m.group(1)}\u094d\u200d{m.group(2)}",
            text,
        )
    return text

def _repair_json(raw: str) -> str:
    """Robust JSON repair: handles unescaped newlines, trailing commas, and truncation."""
    if not raw:
        return ""
    
    # Remove potential markdown fences if they still exist
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$",          "", raw, flags=re.MULTILINE)
    raw = raw.strip()

    # 1. Handle literal newlines inside strings
    out = []
    in_string = False
    escaped = False
    stack = []

    for i, ch in enumerate(raw):
        if escaped:
            out.append(ch)
            escaped = False
            continue
        if ch == "\\":
            out.append(ch)
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            out.append(ch)
            continue
        
        if in_string:
            if ch == "\n":
                out.append("\\n")
            elif ch == "\r":
                pass
            else:
                out.append(ch)
        else:
            if ch == '{': stack.append('}')
            elif ch == '[': stack.append(']')
            elif ch == '}':
                if stack and stack[-1] == '}': stack.pop()
            elif ch == ']':
                if stack and stack[-1] == ']': stack.pop()
            out.append(ch)

    # 2. Close open string if truncated
    if in_string:
        out.append('"')
    
    # 3. Close open objects/arrays in reverse order
    while stack:
        out.append(stack.pop())
    
    repaired = "".join(out)

    # 4. Final safety: remove trailing commas before closing braces/brackets
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    
    # 5. Remove dangling keys (keys without values) at the end of truncated strings
    # This matches: "key": followed by optional whitespace and a closing brace/bracket
    repaired = re.sub(r'[,{]\s*"[^"]+"\s*:\s*([}\]])', r"\1", repaired)
    # This matches: "key": at the absolute end of the string
    repaired = re.sub(r'[,{]\s*"[^"]+"\s*:\s*$', "", repaired.strip())
    
    return repaired


def _escape_unescaped_newlines_in_json_strings(raw: str) -> str:
    """Legacy wrapper for _repair_json logic."""
    return _repair_json(raw)


def _parse_timestamped_transcript(transcript_text: str) -> list:
    """Parse `[MM:SS] lyric` transcript lines into structured entries."""
    entries = []
    for raw_line in transcript_text.splitlines():
        match = re.match(r"^\[(\d{2}:\d{2}(?::\d{2})?)\]\s*(.+?)\s*$", raw_line.strip())
        if not match:
            continue
        time_str, text = match.groups()
        text = _clean_lyric_text(text)
        if not text:
            continue
        entries.append({
            "time": time_str,
            "text": text,
            "seconds": mmss_to_seconds(time_str),
        })
    return entries


def _build_line_fallback_prompt(text: str, emotion: str = "default") -> str:
    """Create a unique image prompt when the LLM omits one for a transcript line."""
    cleaned_text = _clean_lyric_text(text)
    emotion_hint = (emotion or "default").strip()
    return (
        f"A scene showing {emotion_hint} emotion inspired by the song context of '{cleaned_text}', "
        "fine ink crosshatching, watercolor wash, natural history plate aesthetic, "
        "highly detailed etching, 8K, no text, no watermark"
    )


def _hydrate_clip_lines_from_transcript(clips: list, transcript_entries: list) -> None:
    """Force each clip to include every transcript line between start and end."""
    for clip in clips:
        start_sec = mmss_to_seconds(clip["start_time"])
        end_sec = mmss_to_seconds(clip["end_time"])
        existing_lines = clip.get("lines", [])

        existing_by_time = {
            line.get("time"): line for line in existing_lines if line.get("time")
        }
        fallback_emotion = clip.get("style_preset", "default")
        if existing_lines:
            fallback_emotion = existing_lines[0].get("emotion", fallback_emotion)

        hydrated = []
        for entry in transcript_entries:
            if start_sec <= entry["seconds"] <= end_sec:
                original = existing_by_time.get(entry["time"], {})
                emotion = original.get("emotion", fallback_emotion or "default")
                cleaned_text = _clean_lyric_text(original.get("text", entry["text"]))
                if not cleaned_text:
                    continue
                hydrated.append({
                    "time": entry["time"],
                    "text": cleaned_text,
                    "emotion": emotion,
                    "image_prompt": original.get("image_prompt", _build_line_fallback_prompt(cleaned_text, emotion)),
                })

        if hydrated:
            clip["lines"] = hydrated

def seconds_to_mmss(seconds: float) -> str:
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02d}:{s:02d}"


def mmss_to_seconds(mmss: str) -> float:
    parts = mmss.strip().split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return int(parts[0]) * 60 + int(parts[1])


def safe_filename(name: str, max_len: int = 50) -> str:
    """Strip illegal chars and truncate for Windows MAX_PATH safety."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()[:max_len].strip()


def run_ffmpeg(*args, label: str = "ffmpeg") -> bool:
    """Run an ffmpeg command; return True on success with diagnostic logging."""
    cmd = ["ffmpeg", "-y"] + [str(a) for a in args]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if result.returncode != 0:
        err = result.stderr.decode(errors='replace')
        # Log the last few lines of the FFmpeg error for context
        short_err = "\n".join(err.splitlines()[-5:])
        log.warning(f"[{label}] FFmpeg failed (RC {result.returncode}): {short_err}")
        # Log full command only on failure to avoid clutter
        log.debug(f"[{label}] Command: {' '.join(cmd)}")
    return result.returncode == 0


# ════════════════════════════════════════════════════════════════════════════
# DOWNLOAD
# ════════════════════════════════════════════════════════════════════════════

def download_audio(url: str, output_dir: Path) -> tuple:
    """
    Download best audio as MP3.
    Returns (mp3_path, video_id, title).
    """
    import yt_dlp

    url = url.strip()
    if not url.startswith("http") and not url.startswith("www."):
        log.info(f"Searching YouTube for: {url}")
        url = f"ytsearch1:{url}"
    elif not url.startswith("http"):
        url = "https://" + url

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / "%(title).50s.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {"youtube": {"skip": ["dash", "hls"]}},
        "socket_timeout": 30,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if "entries" in info:
            info = info["entries"][0]

    mp3_files = list(output_dir.glob("*.mp3"))
    if not mp3_files:
        raise FileNotFoundError("No MP3 found after download.")

    return str(mp3_files[0]), info.get("id", ""), info.get("title", "Unknown")


# ════════════════════════════════════════════════════════════════════════════
# TRANSCRIPT
# ════════════════════════════════════════════════════════════════════════════

def fetch_transcript(video_id: str, title: str, output_dir: Path) -> tuple:
    """
    Fetch transcript via YouTubeTranscriptApi.
    Supports cookies.txt for bypassing IP blocks with version compatibility.
    """
    log.info(f"Fetching transcript for: {title}")
    
    # ── Cookie Support ──
    cookie_file = Path(__file__).resolve().parent / "cookies.txt"
    cookie_path = str(cookie_file) if cookie_file.exists() else None
    if cookie_path:
        log.info(f"  [AUTH] Using cookies from: {cookie_file.name}")

    try:
        transcript = None
        # Try both class-level (new) and instance-level (old) list_transcripts
        try:
            # 1. Try modern list_transcripts (supports cookies)
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id, cookies=cookie_path)
            # Prioritize Hindi, then English
            try:
                transcript_obj = transcript_list.find_transcript(['hi'])
            except:
                try:
                    transcript_obj = transcript_list.find_generated_transcript(['hi'])
                except:
                    transcript_obj = transcript_list.find_transcript(['en'])
            
            transcript = transcript_obj.fetch()
        except Exception:
            # 2. Try simpler module-level fetch (instance-based)
            try:
                api = YouTubeTranscriptApi()
                # Newer versions of the instance also support cookies in different ways
                transcript = api.fetch(video_id, languages=['hi', 'en'])
            except Exception:
                # 3. Final resort: direct fetch (may fail if old version)
                if hasattr(YouTubeTranscriptApi, 'get_transcript'):
                    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['hi', 'en'], cookies=cookie_path)
                else:
                    raise RuntimeError("No compatible transcript fetch method found in YouTubeTranscriptApi library.")

        if not transcript:
            raise ValueError("No transcript data returned.")

        txt_path = output_dir / f"{safe_filename(title)}.txt"
        lines = []
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"Title: {title}\nYouTube ID: {video_id}\n{'='*40}\n\n")
            for entry in transcript:
                # Handle both object-style (new) and dict-style (old) entries
                start_t = entry['start'] if isinstance(entry, dict) else entry.start
                text_t  = entry['text']  if isinstance(entry, dict) else entry.text
                ts   = seconds_to_mmss(start_t)
                line = f"[{ts}] {text_t}"
                f.write(line + "\n")
                lines.append(line)

        log.info(f"Transcript saved → {txt_path.name} ({len(lines)} lines)")
        return "\n".join(lines), str(txt_path)

    except Exception as e:
        log.error(f"Transcript fetch failed: {e}")
        if "IP" in str(e) or "blocked" in str(e).lower() or "Blocked" in str(e):
             log.error("💡 TIP: YouTube is blocking your IP. Please export 'cookies.txt' to the script folder to bypass.")
        return None, None


# ════════════════════════════════════════════════════════════════════════════
# AI REEL SELECTION
# ════════════════════════════════════════════════════════════════════════════

def get_ai_reel_suggestions(transcript_text: str, title: str):
    """Call NVIDIA LLM and return parsed reel JSON."""
    if not NVIDIA_API_KEY or NVIDIA_API_KEY.startswith("YOUR_"):
        log.error("NVIDIA_API_KEY is not set.")
        return None
    log.info("Asking NVIDIA LLM for best Reel clips...")

    user_msg = f"Song: {title}\n\nTranscript:\n{transcript_text}"
    raw = ""
    max_attempts = 3
    timeout_seconds = 900

    try:
        for attempt in range(1, max_attempts + 1):
            try:
                resp = requests.post(
                    NVIDIA_LLM_URL,
                    headers={
                        "Authorization": f"Bearer {NVIDIA_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": NVIDIA_LLM_MODEL,
                        "temperature": 0.25,
                        "top_p": 0.85,
                        "max_tokens": 8192,
                        "messages": [
                            {"role": "system", "content": REEL_PROMPT},
                            {"role": "user", "content": user_msg},
                        ],
                    },
                    timeout=timeout_seconds,
                )
                resp.raise_for_status()
                raw = resp.json()["choices"][0]["message"]["content"].strip()
                break
            except requests.exceptions.Timeout as e:
                if attempt == max_attempts:
                    raise e
                wait_seconds = attempt * 10
                log.warning(
                    f"NVIDIA LLM timed out on attempt {attempt}/{max_attempts}; "
                    f"retrying in {wait_seconds}s..."
                )
                time.sleep(wait_seconds)
            except requests.exceptions.RequestException as e:
                if attempt == max_attempts:
                    raise e
                wait_seconds = attempt * 5
                log.warning(
                    f"NVIDIA LLM request failed on attempt {attempt}/{max_attempts}: {e}; "
                    f"retrying in {wait_seconds}s..."
                )
                time.sleep(wait_seconds)

        # Strip markdown fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"\s*```$",          "", raw, flags=re.MULTILINE)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Attempt a standard repair first
            repaired = _repair_json(raw)
            try:
                data = json.loads(repaired)
                log.info("  [FIX] JSON repaired successfully.")
            except json.JSONDecodeError as e2:
                # If still failing, try to find the last valid clip if it was truncated
                log.warning(f"  [FIX] Basic JSON repair failed: {e2}")
                raise e2

        transcript_entries = _parse_timestamped_transcript(transcript_text)
        _hydrate_clip_lines_from_transcript(data.get("clips", []), transcript_entries)
        for clip in data.get("clips", []):
            cleaned_lines = []
            for line in clip.get("lines", []):
                cleaned_text = _clean_lyric_text(line.get("text", ""))
                if not cleaned_text:
                    continue
                line["text"] = cleaned_text
                cleaned_lines.append(line)
            clip["lines"] = cleaned_lines

        # --- Duration Filter: Strictly 30-90s ---
        valid_clips = []
        for clip in data.get("clips", []):
            try:
                s_t = mmss_to_seconds(clip["start_time"])
                e_t = mmss_to_seconds(clip["end_time"])
                dur = round(e_t - s_t, 1)
                clip["duration_seconds"] = dur
                if 30 <= dur <= 90:
                    valid_clips.append(clip)
            except Exception:
                continue
        data["clips"] = valid_clips

        log.info(
            f"AI returned {len(data.get('clips', []))} clips | "
            f"preset: {data.get('style_preset', '?')} | "
            f"style: {data.get('image_style', '')[:60]}"
        )
        return data

    except json.JSONDecodeError as e:
        log.error(f"JSON parse error: {e}\nRaw (first 500):\n{raw[:500]}")
        return None
    except Exception as e:
        log.error(f"AI suggestion failed: {e}")
        return None


# ════════════════════════════════════════════════════════════════════════════
# IMAGE GENERATION
# ════════════════════════════════════════════════════════════════════════════

def _build_sd3_prompt(image_prompt: str, style: str) -> str:
    """Merge line prompt + master style into final SD3 prompt."""
    base = image_prompt.strip().rstrip(".")
    sty  = style.strip().rstrip(".")
    return (
        f"{base}. {sty}. "
        "Highly detailed, 8K resolution, fine engraving detail, sharp etching lines, "
        "no text, no watermark, no modern elements."
    )


def _extract_b64(response_body: dict) -> str:
    """Handle multiple NVIDIA API response schemas."""
    candidates = [
        response_body.get("image"),
        (response_body.get("artifacts") or [{}])[0].get("base64"),
        (response_body.get("data")      or [{}])[0].get("b64_json"),
        (response_body.get("data")      or [{}])[0].get("base64"),
    ]
    for c in candidates:
        if c:
            return c
    raise ValueError(f"No image data in NVIDIA response: {list(response_body.keys())}")


def _crop_fill_resize(img: Image.Image, width: int, height: int) -> Image.Image:
    """Smart crop-to-fill: no stretching, no black bars."""
    target_ratio = width / height
    img_ratio    = img.width / img.height

    if img_ratio > target_ratio:
        new_w = int(img.height * target_ratio)
        left  = (img.width - new_w) // 2
        img   = img.crop((left, 0, left + new_w, img.height))
    elif img_ratio < target_ratio:
        new_h = int(img.width / target_ratio)
        top   = (img.height - new_h) // 2
        img   = img.crop((0, top, img.width, top + new_h))

    return img.resize((width, height), Image.Resampling.LANCZOS)


def generate_with_nvidia(
    image_prompt: str,
    style: str,
    output_path: Path,
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
) -> str:
    """Generate image via NVIDIA SD3 endpoint and save as JPEG."""
    if not NVIDIA_IMAGE_API_KEY or NVIDIA_IMAGE_API_KEY.startswith("YOUR_"):
        raise RuntimeError("NVIDIA_IMAGE_API_KEY is not set.")

    full_prompt = _build_sd3_prompt(image_prompt, style)
    prompt_seed = int(hashlib.md5(full_prompt.encode("utf-8")).hexdigest()[:8], 16)
    log.info(f"  [SD3] {image_prompt[:70]}...")

    headers = {
        "Authorization": f"Bearer {NVIDIA_IMAGE_API_KEY}",
        "Accept":        "application/json",
        "Content-Type":  "application/json",
    }
    payload = {
        "prompt":          full_prompt,
        "negative_prompt": SD3_NEGATIVE_PROMPT,
        "cfg_scale":       7,
        "aspect_ratio":    "9:16",
        "seed":            prompt_seed,
        "steps":           40,
        "output_format":   "jpeg",
    }

    try:
        resp = requests.post(
            NVIDIA_IMAGE_INVOKE_URL, headers=headers, json=payload, timeout=120
        )
        resp.raise_for_status()
    except requests.HTTPError as e:
        raise RuntimeError(
            f"NVIDIA SD3 HTTP {resp.status_code}: {resp.text[:400]}"
        ) from e

    image_b64 = _extract_b64(resp.json())
    img       = Image.open(BytesIO(base64.b64decode(image_b64))).convert("RGB")
    img       = _crop_fill_resize(img, width, height)
    img.save(str(output_path), "JPEG", quality=95, optimize=True)
    log.info(f"  [SD3] Saved → {output_path.name}")
    return str(output_path)
# [POLLINATIONS DELETED]




def _parchment_gradient_fallback(
    style: str,
    output_path: Path,
    mood: str = "default",
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
) -> str:
    """
    RDR2-style aged parchment gradient fallback.
    Uses warm cream/sepia tones matching the zoological compendium aesthetic.
    """
    style_lower = style.lower()
    detected    = next((k for k in MOOD_PALETTES if k in style_lower), "default")
    palette     = MOOD_PALETTES.get(mood if mood in MOOD_PALETTES else detected,
                                    MOOD_PALETTES["default"])

    seed = int(hashlib.md5(style.encode()).hexdigest()[:8], 16)
    random.seed(seed)
    c1, c2, c3 = palette

    img  = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # Vertical gradient: light top → darker bottom (parchment look)
    for y in range(height):
        t = y / height
        if t < 0.5:
            blend = t * 2
            color = tuple(int(c1[i] + (c2[i] - c1[i]) * blend) for i in range(3))
        else:
            blend = (t - 0.5) * 2
            color = tuple(int(c2[i] + (c3[i] - c2[i]) * blend) for i in range(3))
        draw.line([(0, y), (width, y)], fill=color)

    # Add subtle paper texture noise
    random.seed(seed + 1)
    for _ in range(width * height // 8):
        px = random.randint(0, width - 1)
        py = random.randint(0, height - 1)
        noise = random.randint(-8, 8)
        current = img.getpixel((px, py))
        noisy = tuple(max(0, min(255, c + noise)) for c in current)
        img.putpixel((px, py), noisy)

    # Soft vignette (darker edges, lighter center — parchment style)
    vig   = Image.new("L", (width, height), 220)
    vdraw = ImageDraw.Draw(vig)
    steps = 100
    for i in range(steps):
        opacity = int(220 * (i / steps) ** 1.5)
        vdraw.rectangle([i, i, width - i, height - i], outline=opacity)
    vig = vig.filter(ImageFilter.GaussianBlur(150))

    dark = Image.new("RGB", (width, height), (c3[0] - 20, c3[1] - 20, c3[2] - 20))
    img  = Image.composite(dark, img, vig)
    img.save(str(output_path), "JPEG", quality=92, optimize=True)
    log.info(f"  [FALLBACK] Parchment gradient → {output_path.name}")
    return str(output_path)


def generate_background(
    image_prompt: str,
    style: str,
    output_path: Path,
    mood: str = "default",
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
    bg_color: str = DEFAULT_BG_COLOR,
) -> str:
    """Return a solid color background matching the AI-chosen song mood."""
    output_path = Path(output_path)
    rgb = _hex_to_rgb(bg_color)
    img = Image.new("RGB", (width, height), rgb)
    img.save(str(output_path), "JPEG", quality=90, optimize=True)
    log.info(f"  [STYLE] Solid {bg_color} background → {output_path.name}")
    return str(output_path)


# ════════════════════════════════════════════════════════════════════════════
# FONT LOADER
# ════════════════════════════════════════════════════════════════════════════

def _font_candidates(kind: str = "lyrics", strict_conjunct: bool = False) -> list:
    """Search for the best available Hindi/Devanagari fonts across OSes."""
    script_dir = Path(__file__).resolve().parent
    repo_root  = script_dir.parent.parent
    
    # 1. Bundled repo fonts (High Priority for consistency in GitHub Actions)
    repo_fonts = [
        repo_root / "fonts" / "Nirmala.ttf",
        repo_root / "fonts" / "TiroDevanagariHindi-Regular.ttf",
        repo_root / "fonts" / "PlaypenSansDeva.ttf",
        script_dir / "Samanya.ttf",
        repo_root / "fonts" / "Caveat-Bold.ttf",
    ]

    # 2. OS-specific system fonts
    os_fonts = []
    if sys.platform == "win32":
        os_fonts = [
            Path("C:/Windows/Fonts/Nirmala.ttf"),
            Path("C:/Windows/Fonts/NirmalaB.ttf"),
            Path("C:/Windows/Fonts/mangal.ttf"),
            Path("C:/Windows/Fonts/mangalb.ttf"),
            Path("C:/Windows/Fonts/segoeui.ttf"),
        ]
    else:
        # Standard Ubuntu/GitHub Actions font paths
        os_fonts = [
            Path("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"),
            Path("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"),
            Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        ]

    # Combine: prioritze repo fonts first, then OS fonts
    return [f for f in (repo_fonts + os_fonts) if f.exists()]


def _font_family_name(font_path: Path) -> str:
    family_map = {
        "TiroDevanagariHindi-Regular.ttf": "Tiro Devanagari Hindi",
        "TiroDevanagariHindi-Italic.ttf": "Tiro Devanagari Hindi",
        "PlaypenSansDeva.ttf": "Playpen Sans Deva",
        "Samanya.ttf": "Samanya",
        "Nirmala.ttf": "Nirmala UI",
        "mangal.ttf": "Mangal",
        "segoeui.ttf": "Segoe UI",
    }
    return family_map.get(font_path.name, font_path.stem)


def _wrap_lyric_text(text: str, width: int = 18) -> str:
    return textwrap.fill(
        text,
        width=width,
        break_long_words=False,
        break_on_hyphens=False,
    )


def _lyric_layout(text: str, font_size: int, width: int, height: int) -> dict:
    wrapped = _wrap_lyric_text(text)
    line_count = len(wrapped.splitlines())
    line_height = font_size + 28
    pad_x = 60
    pad_y = 60
    pill_h = line_count * line_height + pad_y * 1.5
    pill_y = (height - pill_h) // 2   # Center text vertically on screen
    return {
        "wrapped": wrapped,
        "pad_x": pad_x,
        "pad_y": pad_y,
        "box_x": 30,
        "box_w": width - 60,
        "box_y": pill_y,
        "box_h": pill_h,
        "text_y": pill_y + pad_y,
    }


def resolve_font_path(kind: str = "lyrics", text: str | None = None) -> Path | None:
    env_override = os.environ.get("LYRIC_FONT_PATH") if kind == "lyrics" else None
    if env_override:
        candidate = Path(env_override)
        if candidate.exists():
            return candidate
        log.warning(f"LYRIC_FONT_PATH not found: {candidate}")

    strict_conjunct = kind == "lyrics" and _needs_strict_conjunct_rendering(text or "")
    for fp in _font_candidates(kind, strict_conjunct=strict_conjunct):
        if fp.exists():
            return fp
    return None


def _ffmpeg_escape_path(path: Path) -> str:
    value = str(path.resolve()).replace("\\", "/")
    value = value.replace(":", "\\:")
    value = value.replace("'", r"\'")
    return value


def _ffmpeg_escape_filter_value(value: str) -> str:
    value = value.replace("\\", "\\\\")
    value = value.replace(":", r"\:")
    value = value.replace("'", r"\'")
    value = value.replace(",", r"\,")
    return value


def _ass_escape_text(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", r"\N")

def load_font(size: int, text: str = "") -> ImageFont.FreeTypeFont:
    """Try multiple font paths; return best available for Hindi/Devanagari."""
    layout_engine = None
    if HAS_LIBRAQM and hasattr(ImageFont, "Layout") and hasattr(ImageFont.Layout, "RAQM"):
        layout_engine = ImageFont.Layout.RAQM
    else:
        log.warning("libraqm is not available; Hindi shaping may be imperfect.")
    preferred = resolve_font_path("lyrics", text=text)
    candidates = []
    if preferred is not None:
        candidates.append(preferred)
    strict_conjunct = _needs_strict_conjunct_rendering(text)
    candidates.extend(
        fp for fp in _font_candidates("lyrics", strict_conjunct=strict_conjunct)
        if fp not in candidates
    )

    for fp in candidates:
        try:
            kwargs = {"size": size}
            if layout_engine is not None:
                kwargs["layout_engine"] = layout_engine
            font = ImageFont.truetype(str(fp), **kwargs)
            suffix = " [strict conjunct mode]" if strict_conjunct else ""
            log.info(f"  [FONT] Loaded: {fp.name}{suffix}")
            return font
        except Exception:
            continue

    log.warning("No truetype font found — using PIL default (tiny, Hindi may not render)")
    return ImageFont.load_default()


# ════════════════════════════════════════════════════════════════════════════
# LYRIC OVERLAY
# ════════════════════════════════════════════════════════════════════════════

def _overlay_lyrics_skia_hb(img_path: Path, text: str, emotion: str = "default", text_color: str = DEFAULT_TEXT_COLOR) -> bool:
    """High-quality Hindi rendering using Skia and HarfBuzz."""
    if not HAS_SKIA_HB:
        return False
    
    text = _shape_lyric_text_for_rendering(text)
    font_path = resolve_font_path("lyrics", text=text)
    if not font_path or not font_path.exists():
        return False

    # 1. Create Skia surface from existing image
    with open(font_path, "rb") as f:
        font_data = f.read()
    
    face = hb.Face(font_data)
    hb_font = hb.Font(face)
    font_size = 72
    hb_font.scale = (font_size * 64, font_size * 64)
    
    sk_typeface = skia.Typeface.MakeFromFile(str(font_path))
    sk_font = skia.Font(sk_typeface, font_size)
    # Use AI-chosen text color
    tc = _hex_to_rgb(text_color)
    sk_color = skia.Color(tc[0], tc[1], tc[2])
    sk_paint = skia.Paint(Color=sk_color, AntiAlias=True)
    
    # Optional: subtle boldness
    sk_paint.setStyle(skia.Paint.kStrokeAndFill_Style)
    sk_paint.setStrokeWidth(0.5)

    img = Image.open(str(img_path)).convert("RGBA")
    width, height = img.size
    surface = skia.Surface(width, height)
    canvas = surface.getCanvas()
    
    # Draw background first
    sk_img = skia.Image.frombytes(img.tobytes(), img.size, skia.kRGBA_8888_ColorType)
    canvas.drawImage(sk_img, 0, 0)

    # 2. Shape and render text
    lines = _wrap_lyric_text(text).splitlines()
    line_height = font_size * 1.3
    total_h = len(lines) * line_height
    curr_y = (height - total_h) / 2 + (font_size * 0.8)  # Adjust for baseline

    for line in lines:
        buf = hb.Buffer()
        buf.add_str(line)
        buf.guess_segment_properties()
        hb.shape(hb_font, buf, {})
        
        glyphs = [info.codepoint for info in buf.glyph_infos]
        line_width = sum(p.x_advance for p in buf.glyph_positions) / 64.0
        curr_x = (width - line_width) / 2
        
        positions = []
        for p in buf.glyph_positions:
            off_x = p.x_offset / 64.0
            off_y = p.y_offset / 64.0
            positions.append(skia.Point(curr_x + off_x, curr_y - off_y))
            curr_x += p.x_advance / 64.0
            
        builder = skia.TextBlobBuilder()
        builder.allocRunPos(sk_font, glyphs, positions)
        blob = builder.make()
        canvas.drawTextBlob(blob, 0, 0, sk_paint)
        curr_y += line_height

    # 3. Save result — encode in-memory, then save through PIL
    #    (Skia's save() silently fails on Windows Unicode paths)
    snapshot = surface.makeImageSnapshot()
    encoded = snapshot.encodeToData(skia.kJPEG, 95)
    if encoded:
        pil_out = Image.open(BytesIO(bytes(encoded)))
        pil_out.convert("RGB").save(str(img_path), "JPEG", quality=95, optimize=True)
    else:
        log.warning("[overlay_lyrics] Skia encode failed, falling back")
        return False
    log.info(f"[overlay_lyrics] Skia+HarfBuzz renderer OK (Fixed 'ri')")
    return True


def _overlay_lyrics_windows_native(img_path: Path, text: str, emotion: str = "default") -> bool:
    """Use Windows GDI+ text shaping for White-on-Black aesthetic (Revised lifecycle)."""
    if sys.platform != "win32":
        return False
    
    text = _shape_lyric_text_for_rendering(text)
    font_path = resolve_font_path("lyrics", text=text)
    if not font_path:
        return False

    img = Image.open(str(img_path)).convert("RGB")
    width, height = img.size
    font_size = 72
    layout = _lyric_layout(text, font_size, width, height)
    font_family = _font_family_name(font_path)

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tf:
        tf.write(layout["wrapped"])
        text_file = Path(tf.name)

    ps_script = f"""
Add-Type -AssemblyName System.Drawing
$imagePath = [System.IO.Path]::GetFullPath("{str(img_path)}")
$textPath  = [System.IO.Path]::GetFullPath("{str(text_file)}")
$fontPath  = [System.IO.Path]::GetFullPath("{str(font_path)}")
$text      = Get-Content -LiteralPath $textPath -Raw -Encoding UTF8
$source    = [System.Drawing.Image]::FromFile($imagePath)
$bitmap    = New-Object System.Drawing.Bitmap($source.Width, $source.Height, [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
$graphics  = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
$graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
$graphics.Clear([System.Drawing.Color]::Black)
$graphics.DrawImage($source, 0, 0, $source.Width, $source.Height)
$source.Dispose()
$fontCollection = New-Object System.Drawing.Text.PrivateFontCollection
$fontCollection.AddFontFile($fontPath)
$fontFamily = if ($fontCollection.Families.Length -gt 0) {{ $fontCollection.Families[0] }} else {{ New-Object System.Drawing.FontFamily("{font_family}") }}
$font = New-Object System.Drawing.Font($fontFamily, {font_size}, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
$format = New-Object System.Drawing.StringFormat
$format.Alignment = [System.Drawing.StringAlignment]::Center
$format.LineAlignment = [System.Drawing.StringAlignment]::Center
$format.FormatFlags = [System.Drawing.StringFormatFlags]::NoFontFallback -bor [System.Drawing.StringFormatFlags]::DisplayFormatControl
$textBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)
$textRect = New-Object System.Drawing.RectangleF(0, 0, $source.Width, $source.Height)
$graphics.DrawString($text, $font, $textBrush, $textRect, $format)
$codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object {{ $_.MimeType -eq "image/jpeg" }} | Select-Object -First 1
$params = New-Object System.Drawing.Imaging.EncoderParameters(1)
$params.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, 95L)
$bitmap.Save($imagePath, $codec, $params)
$bitmap.Dispose()
$graphics.Dispose()
"""
    result = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try: text_file.unlink(missing_ok=True)
    except Exception: pass

    if result.returncode == 0:
        log.info(f"[overlay_lyrics] Windows native OK (B/W Style)")
        return True
    return False


def _overlay_lyrics_ffmpeg_ass(img_path: Path, text: str, emotion: str = "default") -> bool:
    """Use ASS subtitles for high-quality Hindi shaping with White-on-Black style."""
    text = _shape_lyric_text_for_rendering(text)
    font_path = resolve_font_path("lyrics", text=text)
    if not font_path: return False

    width, height = REEL_WIDTH, REEL_HEIGHT
    font_size = 72
    layout = _lyric_layout(text, font_size, width, height)
    font_family = _font_family_name(font_path)
    temp_output = img_path.with_name(f"{img_path.stem}_lyric_tmp{img_path.suffix}")
    
    with tempfile.NamedTemporaryFile("w", suffix=".ass", delete=False, encoding="utf-8") as tf:
        ass_file = Path(tf.name)
        tf.write(
            "[Script Info]\nScriptType: v4.00+\n"
            f"PlayResX: {width}\nPlayResY: {height}\n"
            "ScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
            "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Lyrics,{font_family},{font_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,"
            "0,0,0,0,100,100,0,0,1,1,0,5,30,30,0,1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            f"Dialogue: 0,0:00:00.00,0:00:05.00,Lyrics,,0,0,0,,"
            f"{{\\bord1\\shad0\\1c&HFFFFFF&\\3c&H000000&\\pos({width // 2},{height // 2})}}"
            f"{_ass_escape_text(layout['wrapped'])}\n"
        )

    vf = f"subtitles='{_ffmpeg_escape_filter_value(str(ass_file.resolve()))}':fontsdir='{_ffmpeg_escape_filter_value(str(font_path.parent.resolve()))}'"
    cmd = ["ffmpeg", "-y", "-i", str(img_path), "-vf", vf, "-frames:v", "1", str(temp_output)]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try: ass_file.unlink(missing_ok=True)
    except Exception: pass

    if result.returncode == 0 and temp_output.exists():
        temp_output.replace(img_path)
        log.info(f"[overlay_lyrics] ASS renderer OK (B/W Style)")
        return True
    return False


def _overlay_lyrics_ffmpeg_drawtext(img_path: Path, text: str, emotion: str = "default") -> bool:
    """Use FFmpeg drawtext for White-on-Black aesthetic (secondary fallback)."""
    text = _shape_lyric_text_for_rendering(text)
    font_path = resolve_font_path("lyrics", text=text)
    if not font_path: return False

    width, height = REEL_WIDTH, REEL_HEIGHT
    font_size = 72
    layout = _lyric_layout(text, font_size, width, height)
    temp_output = img_path.with_name(f"{img_path.stem}_lyric_tmp{img_path.suffix}")
    
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tf:
        tf.write(layout["wrapped"])
        text_file = Path(tf.name)

    font_arg = _ffmpeg_escape_path(font_path)
    text_arg = _ffmpeg_escape_path(text_file)

    vf = (
        f"drawtext=fontfile='{font_arg}':textfile='{text_arg}':fontcolor=white:fontsize={font_size}:"
        f"line_spacing=12:text_shaping=1:x=(w-text_w)/2:y=(h-text_h)/2"
    )

    cmd = ["ffmpeg", "-y", "-i", str(img_path), "-vf", vf, "-frames:v", "1", str(temp_output)]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try: text_file.unlink(missing_ok=True)
    except Exception: pass

    if result.returncode == 0 and temp_output.exists():
        temp_output.replace(img_path)
        log.info(f"[overlay_lyrics] drawtext renderer OK (B/W Style)")
        return True
    return False


def overlay_lyrics(img_path: Path, text: str, emotion: str = "default", text_color: str = DEFAULT_TEXT_COLOR) -> None:
    """Render lyric text with strongest available shaping backend."""
    text = _clean_lyric_text(text)
    if not text:
        log.info("[overlay_lyrics] Skipping empty lyric after stage-tag cleanup.")
        return

    # 1. High-quality: Skia + HarfBuzz
    if HAS_SKIA_HB:
        if _overlay_lyrics_skia_hb(img_path, text, emotion, text_color=text_color):
            return

    # 2. Fallbacks (use white text for non-Skia renderers)
    if sys.platform == "win32" and _needs_strict_conjunct_rendering(text):
        if _overlay_lyrics_windows_native(img_path, text, emotion):
            return
    if _overlay_lyrics_ffmpeg_ass(img_path, text, emotion):
        return
    if sys.platform == "win32" and _overlay_lyrics_windows_native(img_path, text, emotion):
        return
    if _overlay_lyrics_ffmpeg_drawtext(img_path, text, emotion):
        return
    log.warning("[overlay_lyrics] Falling back to Pillow renderer.")
    _overlay_lyrics_pil(img_path, text, emotion)


YT_HANDLE = "@Hindi-Shayari-हिंदी-शायरी"

# Possible watermark positions: (x_align, y_align)
_WATERMARK_POSITIONS = [
    ("left",   "top"),
    ("right",  "top"),
    ("left",   "bottom"),
    ("right",  "bottom"),
    ("center", "top"),
    ("center", "bottom"),
    ("left",   "middle"),
    ("right",  "middle"),
]


def add_watermark(img_path: Path, position_seed: int = 0, text_color: str = DEFAULT_TEXT_COLOR) -> None:
    """Add a subtle YouTube handle watermark at 20% opacity. Position varies per reel."""
    random.seed(position_seed)
    x_align, y_align = random.choice(_WATERMARK_POSITIONS)

    img = Image.open(str(img_path)).convert("RGBA")
    W, H = img.size

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_size = 22
    font = load_font(font_size, text=YT_HANDLE)
    bbox = draw.textbbox((0, 0), YT_HANDLE, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    margin = 30
    if x_align == "left":    x = margin
    elif x_align == "right": x = W - tw - margin
    else:                    x = (W - tw) // 2

    if y_align == "top":      y = margin
    elif y_align == "bottom": y = H - th - margin
    else:                     y = (H - th) // 2

    # Use text color at 20% opacity
    tc = _hex_to_rgb(text_color)
    watermark_color = (tc[0], tc[1], tc[2], 51)
    draw.text((x, y), YT_HANDLE, fill=watermark_color, font=font)

    img = Image.alpha_composite(img, overlay)
    img.convert("RGB").save(str(img_path), "JPEG", quality=95, optimize=True)


# ════════════════════════════════════════════════════════════════════════════
# VIDEO RENDERING
# ════════════════════════════════════════════════════════════════════════════

def render_reel_video(
    clip_data:   dict,
    audio_path:  str,
    style:       str,
    song_folder: Path,
    clip_num:    int,
    mood:        str = "default",
    bg_color:    str = DEFAULT_BG_COLOR,
    text_color:  str = DEFAULT_TEXT_COLOR,
) -> str:
    """Render one Instagram Reel MP4 with synced lyric frames, crossfades, and audio fade-out."""
    lines     = clip_data.get("lines", [])
    start_sec = mmss_to_seconds(clip_data["start_time"])
    end_sec   = mmss_to_seconds(clip_data["end_time"])
    duration  = end_sec - start_sec

    if not lines:
        log.warning(f"Clip {clip_num} has no lines — skipping.")
        return ""

    reel_dir = song_folder / f"reel_{clip_num}"
    reel_dir.mkdir(parents=True, exist_ok=True)

    frame_paths     = []
    frame_durations = []

    log.info(
        f"\n── Clip {clip_num}: {clip_data['start_time']} → "
        f"{clip_data['end_time']} ({duration:.0f}s) ──"
    )

    for i, line in enumerate(lines):
        img_path = reel_dir / f"frame_{i:03d}.jpg"
        prompt   = line.get("image_prompt", "")
        emotion  = line.get("emotion", "default")
        text     = line.get("text", "")

        log.info(f"  Frame {i+1}/{len(lines)} | {emotion} | {text[:45]}")

        # 1. Generate background with AI-chosen color
        generate_background(prompt, style, img_path, mood=emotion, bg_color=bg_color)

        # 2. Overlay lyrics with AI-chosen text color
        overlay_lyrics(img_path, text, emotion, text_color=text_color)

        # 3. Add subtle YouTube handle watermark (position per reel)
        add_watermark(img_path, position_seed=clip_num, text_color=text_color)

        # 4. Brief pause for OS file-handle stability (Windows fix)
        time.sleep(0.5)

        frame_paths.append(str(img_path))

        # 3. Frame duration = time to next line
        if i < len(lines) - 1:
            this_t = mmss_to_seconds(line["time"])
            next_t = mmss_to_seconds(lines[i + 1]["time"])
            frame_durations.append(max(next_t - this_t, 1.5))
        else:
            this_t = mmss_to_seconds(line["time"])
            frame_durations.append(max(end_sec - this_t, 1.5))

    # ── FFmpeg concat file ───────────────────────────────────────────────
    # Use RELATIVE filenames (just 'frame_000.jpg') to avoid Unicode path issues
    # on Windows. FFmpeg will resolve them relative to the concat file location.
    concat_path = reel_dir / "concat.txt"
    with open(str(concat_path), "w", encoding="utf-8") as f:
        for fp, dur in zip(frame_paths, frame_durations):
            fname = Path(fp).name  # Just 'frame_000.jpg'
            f.write(f"file '{fname}'\n")
            f.write(f"duration {dur:.3f}\n")
        if frame_paths:
            last_fname = Path(frame_paths[-1]).name
            f.write(f"file '{last_fname}'\n")      # FFmpeg concat demuxer requirement

    # ── ALL FFmpeg work in a temp ASCII directory ──────────────────────
    # Windows FFmpeg can't handle Unicode paths. We do ALL intermediate
    # work in a temp dir with pure-ASCII names, then move results back.
    import shutil
    tmp_work = Path(tempfile.mkdtemp(prefix=f"reel{clip_num}_"))
    log.info(f"  [TEMP] Working dir: {tmp_work}")

    # Copy source audio to safe path
    safe_audio = tmp_work / "source.mp3"
    try:
        shutil.copy2(str(audio_path), str(safe_audio))
    except Exception as e:
        log.error(f"Could not copy audio: {e}")
        return False

    # Copy concat file and all frames to temp dir
    safe_concat = tmp_work / "concat.txt"
    shutil.copy2(str(concat_path), str(safe_concat))
    for fp in frame_paths:
        shutil.copy2(fp, str(tmp_work / Path(fp).name))

    # ── Trim audio ───────────────────────────────────────────────────────
    # We explicitly re-encode to MP3 here instead of using '-acodec copy'.
    # Copying streams from yt-dlp MP3s often results in broken headers 
    # and "Invalid data found" errors on subsequent ffmpeg passes.
    safe_audio_clip = tmp_work / "audio_clip.mp3"
    run_ffmpeg(
        "-ss", str(start_sec), "-t", str(duration),
        "-i", str(safe_audio), "-c:a", "libmp3lame", "-q:a", "2",
        str(safe_audio_clip),
        label="audio_trim",
    )

    # ── Render video with audio fade-out ─────────────────────────────────
    safe_output = tmp_work / "output.mp4"
    af_filter = f"afade=t=out:st={max(duration - 1.5, 0):.1f}:d=1.5"
    if not run_ffmpeg(
        "-f", "concat", "-safe", "0", "-i", str(safe_concat),
        "-i", str(safe_audio_clip),
        "-vf", (
            f"scale={REEL_WIDTH}:{REEL_HEIGHT}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={REEL_WIDTH}:{REEL_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
            "format=yuv420p"
        ),
        "-af", af_filter,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        str(safe_output),
        label=f"render_reel_{clip_num}",
    ):
        log.error(f"[render_reel_{clip_num}] Rendering FAILED!")
        shutil.rmtree(str(tmp_work), ignore_errors=True)
        return False

    # ── Move results back to final Unicode paths ─────────────────────────
    output_video = song_folder / f"reel_{clip_num}.mp4"
    try:
        shutil.move(str(safe_output), str(output_video))
    except Exception:
        output_video = safe_output

    # Standalone MP3 clip
    reel_mp3 = song_folder / f"reel_{clip_num}.mp3"
    if safe_audio_clip.exists():
        try:
            shutil.copy2(str(safe_audio_clip), str(reel_mp3))
        except Exception:
            pass

    # Cleanup temp dir
    shutil.rmtree(str(tmp_work), ignore_errors=True)

    log.info(f"✅ Reel {clip_num} → {output_video.name}")
    return str(output_video)


# ════════════════════════════════════════════════════════════════════════════
# SAVE SUGGESTIONS
# ════════════════════════════════════════════════════════════════════════════

def save_suggestions(ai_data: dict, song_folder: Path, title: str) -> None:
    """Save reel_data.json + youtube_metadata.txt + reel_suggestions.txt"""
    json_path = song_folder / "reel_data.json"
    with open(str(json_path), "w", encoding="utf-8") as f:
        json.dump(ai_data, f, indent=2, ensure_ascii=False)

    yt_path = song_folder / "youtube_metadata.txt"
    with open(str(yt_path), "w", encoding="utf-8") as f:
        f.write(f"TITLE:\n{ai_data.get('youtube_title', '')}\n\n")
        f.write(f"DESCRIPTION:\n{ai_data.get('youtube_description', '')}\n")

    txt_path = song_folder / "reel_suggestions.txt"
    with open(str(txt_path), "w", encoding="utf-8") as f:
        f.write(f"Reel Suggestions: {title}\n")
        f.write(f"Style Preset : {ai_data.get('style_preset', 'N/A')}\n")
        f.write(f"Image Style  : {ai_data.get('image_style', 'N/A')}\n")
        f.write("=" * 50 + "\n\n")
        for clip in ai_data.get("clips", []):
            f.write(
                f"Reel {clip.get('clip_number')}: "
                f"[{clip.get('start_time')}] → [{clip.get('end_time')}] "
                f"({clip.get('duration_seconds', '?')}s)\n"
            )
            f.write(f"  Reason: {clip.get('reason', '')}\n\n")
            for line in clip.get("lines", []):
                f.write(f"  [{line['time']}] {line['text']}\n")
                f.write(f"    Emotion : {line.get('emotion', '')}\n")
                f.write(f"    Prompt  : {line.get('image_prompt', '')}\n\n")

    log.info(f"Saved: {json_path.name} | {txt_path.name} | {yt_path.name}")


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Bollywood Reel Generator")
    parser.add_argument("--url",        "-u", required=False, help="YouTube URL or song name")
    parser.add_argument("--auto",       action="store_true", help="Automatically pick first song from ghazal_songs.json")
    parser.add_argument("--output",     "-o", default="downloads", help="Output directory")
    parser.add_argument("--skip-ai",    action="store_true", help="Skip AI reel suggestions")
    parser.add_argument("--skip-video", action="store_true", help="Skip video rendering")
    args = parser.parse_args()

    if not args.url and not args.auto:
        parser.error("You must provide either --url or --auto")

    if args.auto:
        repo_root = Path(__file__).resolve().parent.parent.parent
        json_path = repo_root / "data" / "shayari" / "ghazal_songs.json"
        if not json_path.exists():
            log.error(f"Cannot find {json_path}")
            return
        with open(json_path, "r", encoding="utf-8") as f:
            songs = json.load(f)
        if not songs:
            log.error("No songs left in ghazal_songs.json")
            return
        query = songs.pop(0)
        args.url = query
        # Save updated list back
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(songs, f, indent=2, ensure_ascii=False)
        log.info(f"[AUTO MODE] Picked '{query}'. {len(songs)} remaining.")


    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        import yt_dlp

        query = args.url.strip()
        if not query.startswith("http") and not query.startswith("www."):
            query = f"ytsearch1:{query}"

        log.info("Resolving video info...")
        ydl_opts_resolve = {
            "quiet":          True,
            "no_warnings":    True,
            "extractor_args": {"youtube": {"skip": ["dash", "hls"]}},
            "socket_timeout": 30,
        }
        with yt_dlp.YoutubeDL(ydl_opts_resolve) as ydl:
            info = ydl.extract_info(query, download=False)
            if "entries" in info:
                info = info["entries"][0]
            title = info.get("title", "Unknown")

        log.info(f"Song: {title}")

        song_folder = output_dir / safe_filename(title)
        song_folder.mkdir(parents=True, exist_ok=True)

        audio_path, video_id, final_title = download_audio(args.url, song_folder)
        log.info(f"Audio: {Path(audio_path).name}")

        transcript_text, txt_path = fetch_transcript(video_id, final_title, song_folder)

        if transcript_text and not args.skip_ai:
            ai_data = get_ai_reel_suggestions(transcript_text, final_title)

            if ai_data:
                save_suggestions(ai_data, song_folder, final_title)
                style = ai_data.get("image_style", (
                    "watercolor wash, aged parchment background"
                    "muted sepia-amber palette, natural history plate aesthetic"
                ))
                mood = ai_data.get("style_preset", "default")

                if not args.skip_video:
                    # Extract AI color theme with contrast safety
                    raw_bg = ai_data.get("background_color", DEFAULT_BG_COLOR)
                    raw_text = ai_data.get("text_color", DEFAULT_TEXT_COLOR)
                    bg_color, text_color = _ensure_contrast(raw_bg, raw_text)
                    log.info(f"  [COLOR] Background: {bg_color} | Text: {text_color}")

                    for clip in ai_data.get("clips", []):
                        clip_num = clip.get("clip_number", 1)
                        vid_path = render_reel_video(
                            clip_data   = clip,
                            audio_path  = audio_path,
                            style       = style,
                            song_folder = song_folder,
                            clip_num    = clip_num,
                            mood        = mood,
                            bg_color    = bg_color,
                            text_color  = text_color,
                        )
                        
                        # Export Metadata for Github Actions Uploader
                        if vid_path:
                            # Append full lyrics to the AI suggested description
                            base_desc = ai_data.get("youtube_description", "")
                            full_desc = f"{base_desc}\n\nLyrics / Poetry:\n{transcript_text}"
                            if len(full_desc) > 4800: # YouTube description max is 5000
                                full_desc = full_desc[:4800] + "..."
                                
                            upload_meta = {
                                "title": ai_data.get("youtube_title", final_title),
                                "description": full_desc,
                                "video_path": str(vid_path),
                                "keywords": ai_data.get("youtube_description", "").split("#")[1:] # Extract hashtags heuristically
                            }
                            meta_path = output_dir / f"upload_metadata_{clip_num}.json"
                            with open(meta_path, "w", encoding="utf-8") as f:
                                json.dump(upload_meta, f, ensure_ascii=False, indent=2)
                            log.info(f"Saved {meta_path.name}")

        elif args.skip_ai:
            log.info("AI skipped (--skip-ai flag)")
        else:
            log.error("No transcript available — cannot generate reels.")

        log.info(f"\n✨ Done! Output folder: {song_folder}")

    except KeyboardInterrupt:
        log.info("Cancelled by user.")
    except Exception as e:
        log.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
