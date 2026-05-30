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
from urllib.parse import quote
import pollinations_gen
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
NVIDIA_LLM_MODEL = "meta/llama-3.3-70b-instruct"

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
- Include EVERY lyric line with its exact timestamp (do not skip any line)
- Calculate duration_seconds = end_time minus start_time in seconds
- Each clip MUST be 30–90 seconds long
- Skip lines that are ONLY: [संगीत], [Music], [Applause], [Instrumental]
- Prioritize: hook, chorus, emotionally impactful, catchy, or viral-worthy moments
- Include EVERY lyric line with its exact timestamp (do not skip any line)
- Calculate duration_seconds = end_time minus start_time in seconds 

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


SD3 PROMPT STRUCTURE for each line:
line-specific subject and scene description,
fine ink crosshatching, watercolor wash, 
natural history plate aesthetic, highly detailed etching, 8K, no text, no watermark

══════════════════════════════════════════
OUTPUT — respond ONLY with valid JSON, no markdown, no explanation
══════════════════════════════════════════
{
  "youtube_title": "SEO title with song name, singer, film (under 100 chars)",
  "youtube_description": "Full lyrics with timestamps + singer/composer credits + 25 relevant Hindi and English hashtags. If you need line breaks, use escaped \\n sequences only, never raw newlines inside JSON strings.",
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

STAGE_TAG_RE = re.compile(r"\[\s*(?:music|applause|instrumental|संगीत)\s*\]", re.IGNORECASE)
DEVANAGARI_CONJUNCT_RE = re.compile(r"([\u0915-\u0939\u0958-\u095f])\u094d([\u0915-\u0939\u0958-\u095f])")


# ════════════════════════════════════════════════════════════════════════════
# UTILITIES
# ════════════════════════════════════════════════════════════════════════════

def _clean_lyric_text(text: str) -> str:
    """Remove inline non-lyric stage tags and normalize spacing."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text.strip())
    text = STAGE_TAG_RE.sub(" ", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip()


def _needs_strict_conjunct_rendering(text: str) -> bool:
    return bool(text) and ("\u094d" in text or "ख्म" in text or "ज़ख्म" in text or "जख्म" in text)


def _shape_lyric_text_for_rendering(text: str) -> str:
    """Hint renderers to keep Devanagari half-forms/conjuncts stable."""
    if not _needs_strict_conjunct_rendering(text):
        return text
    return DEVANAGARI_CONJUNCT_RE.sub(
        lambda m: f"{m.group(1)}\u094d\u200d{m.group(2)}",
        text,
    )

def _escape_unescaped_newlines_in_json_strings(raw: str) -> str:
    """Escape literal newlines that appear inside JSON string values."""
    out = []
    in_string = False
    escaped = False

    for ch in raw:
        if escaped:
            out.append(ch)
            escaped = False
            continue

        if ch == "\\":
            out.append(ch)
            escaped = True
            continue

        if ch == '"':
            out.append(ch)
            in_string = not in_string
            continue

        if in_string and ch == "\n":
            out.append("\\n")
            continue

        if in_string and ch == "\r":
            continue

        out.append(ch)

    return "".join(out)


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
        f"inspired by the lyric '{cleaned_text}', "
        f"showing {emotion_hint} emotion, expressive pose, symbolic scene from the song context"
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
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name).strip()[:max_len]
    return cleaned.rstrip(". ")


def run_ffmpeg(*args, label: str = "ffmpeg") -> bool:
    """Run an ffmpeg command; return True on success."""
    cmd = ["ffmpeg", "-y"] + list(args)
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if result.returncode != 0:
        log.warning(f"[{label}] stderr: {result.stderr[-300:].decode(errors='replace')}")
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
    Returns (transcript_text, txt_path).
    """
    log.info(f"Fetching transcript for: {title}")
    try:
        api = YouTubeTranscriptApi()
        transcript = None
        for lang_pref in [["hi"], ["en"], ["hi", "en"]]:
            try:
                transcript = api.fetch(video_id, languages=lang_pref)
                break
            except Exception:
                continue
        if transcript is None:
            transcript = api.fetch(video_id)

        txt_path = output_dir / f"{safe_filename(title)}.txt"
        lines = []
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"Title: {title}\nYouTube ID: {video_id}\n{'='*40}\n\n")
            for entry in transcript:
                ts   = seconds_to_mmss(entry.start)
                line = f"[{ts}] {entry.text}"
                f.write(line + "\n")
                lines.append(line)

        log.info(f"Transcript saved → {txt_path.name} ({len(lines)} lines)")
        return "\n".join(lines), str(txt_path)

    except Exception as e:
        log.error(f"Transcript fetch failed: {e}")
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
    timeout_seconds = 300

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
            raw = _escape_unescaped_newlines_in_json_strings(raw)
            data = json.loads(raw)

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

        # Fix duration_seconds
        for clip in data.get("clips", []):
            try:
                s = mmss_to_seconds(clip["start_time"])
                e = mmss_to_seconds(clip["end_time"])
                clip["duration_seconds"] = round(e - s, 1)
            except Exception:
                pass

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
def generate_background_pollinations(
    image_prompt: str,
    style: str,
    output_path: Path,
    mood: str = "default",
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
    use_nvidia_only: bool = False,
    skip_pollinations: bool = False,
) -> str:
    """New entry: try Pollinations first (free), then SD3 (paid), fallback to parchment gradient."""
    output_path = Path(output_path)
    
    # 1. Option: Skip Pollinations or Force NVIDIA
    if not use_nvidia_only and not skip_pollinations:
        try:
            return pollinations_gen.generate_with_pollinations(
                image_prompt, style, output_path, width, height,
                _crop_fill_resize, _build_sd3_prompt
            )
        except Exception as e:
            log.warning(f"  [WARN] Pollinations generation failed: {e}")

    # 2. Try NVIDIA SD3 (Paid / Secondary)
    try:
        if NVIDIA_IMAGE_API_KEY and not NVIDIA_IMAGE_API_KEY.startswith("YOUR_"):
            return generate_with_nvidia(image_prompt, style, output_path, width, height)
    except Exception as e:
        log.warning(f"  [WARN] NVIDIA SD3 failed: {e}")

    # 3. Fallback to Parchment Gradient
    return _parchment_gradient_fallback(style, output_path, mood, width, height)




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
) -> str:
    """Main entry: try SD3, fallback to parchment gradient."""
    output_path = Path(output_path)
    try:
        return generate_with_nvidia(image_prompt, style, output_path, width, height)
    except Exception as e:
        log.warning(f"  [WARN] SD3 failed → parchment fallback. Reason: {e}")
    return _parchment_gradient_fallback(style, output_path, mood, width, height)


# ════════════════════════════════════════════════════════════════════════════
# FONT LOADER
# ════════════════════════════════════════════════════════════════════════════

def _font_candidates(kind: str = "lyrics", strict_conjunct: bool = False) -> list:
    script_dir = Path(__file__).resolve().parent
    repo_root  = script_dir.parent.parent
    if sys.platform == "win32":
        if strict_conjunct:
            lyric_candidates = [
                Path("C:/Windows/Fonts/mangal.ttf"),
                Path("C:/Windows/Fonts/Nirmala.ttf"),
                script_dir / "Samanya.ttf",
                repo_root / "fonts" / "TiroDevanagariHindi-Regular.ttf",
                repo_root / "fonts" / "PlaypenSansDeva.ttf",
                Path("C:/Windows/Fonts/segoeui.ttf"),
                Path("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"),
                Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
                Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
                repo_root / "fonts" / "Caveat-Bold.ttf",
            ]
        else:
            lyric_candidates = [
                Path("C:/Windows/Fonts/Nirmala.ttf"),
                Path("C:/Windows/Fonts/mangal.ttf"),
                script_dir / "Samanya.ttf",
                repo_root / "fonts" / "TiroDevanagariHindi-Regular.ttf",
                repo_root / "fonts" / "PlaypenSansDeva.ttf",
                Path("C:/Windows/Fonts/segoeui.ttf"),
                Path("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"),
                Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
                Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
                repo_root / "fonts" / "Caveat-Bold.ttf",
            ]
    else:
        if strict_conjunct:
            lyric_candidates = [
                script_dir / "Samanya.ttf",
                repo_root / "fonts" / "TiroDevanagariHindi-Regular.ttf",
                Path("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"),
                repo_root / "fonts" / "PlaypenSansDeva.ttf",
                Path("C:/Windows/Fonts/mangal.ttf"),
                Path("C:/Windows/Fonts/Nirmala.ttf"),
                Path("C:/Windows/Fonts/segoeui.ttf"),
                Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
                Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
                repo_root / "fonts" / "Caveat-Bold.ttf",
            ]
        else:
            lyric_candidates = [
                repo_root / "fonts" / "TiroDevanagariHindi-Regular.ttf",
                script_dir / "Samanya.ttf",
                Path("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"),
                repo_root / "fonts" / "PlaypenSansDeva.ttf",
                Path("C:/Windows/Fonts/Nirmala.ttf"),
                Path("C:/Windows/Fonts/mangal.ttf"),
                Path("C:/Windows/Fonts/segoeui.ttf"),
                Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
                Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
                repo_root / "fonts" / "Caveat-Bold.ttf",
            ]
    if kind == "lyrics":
        return lyric_candidates
    return lyric_candidates


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


def _wrap_lyric_text(text: str, width: int = 22) -> str:
    return textwrap.fill(
        text,
        width=width,
        break_long_words=False,
        break_on_hyphens=False,
    )


def _lyric_layout(text: str, font_size: int, width: int, height: int) -> dict:
    wrapped = _wrap_lyric_text(text)
    line_count = wrapped.count("\n") + 1
    line_height = font_size + 12
    pad_x = 56
    pad_y = 32
    pill_h = line_count * line_height + pad_y * 2 + 12
    pill_y = max(60, height - 280 - pill_h)
    return {
        "wrapped": wrapped,
        "pad_x": pad_x,
        "pad_y": pad_y,
        "box_x": 30,
        "box_w": width - 60,
        "box_y": pill_y,
        "box_h": pill_h,
        "text_y": pill_y + pad_y + 8,
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

def _overlay_lyrics_pil(img_path: Path, text: str, emotion: str = "default") -> None:
    """Fallback lyric renderer using Pillow when FFmpeg text shaping is unavailable."""
    # Emotion → accent color (sepia/ink tones for parchment aesthetic)
    EMOTION_COLORS = {
        "romantic":   (160,  60,  80),   # Deep rose-sepia
        "sad":        ( 60,  80, 130),   # Slate blue-ink
        "happy":      ( 80, 130,  60),   # Olive green
        "energetic":  (180, 110,  20),   # Burnt amber
        "devotional": (160, 110,  20),   # Gold ochre
        "longing":    (110,  70, 120),   # Muted purple
        "default":    ( 80,  55,  30),   # Dark sepia ink
    }
    accent     = EMOTION_COLORS.get(emotion, EMOTION_COLORS["default"])
    ink_color  = (30, 20, 10)            # Dark sepia ink for text (like RDR2 labels)
    pill_fill  = (242, 233, 205, 200)    # Parchment cream semi-transparent

    # ── Open image ───────────────────────────────────────────────────────
    img  = Image.open(str(img_path)).convert("RGBA")
    W, H = img.size
    text = _shape_lyric_text_for_rendering(unicodedata.normalize("NFC", text.strip()))

    font_size = 68
    font      = load_font(font_size, text=text)
    text_kwargs = {"font": font, "align": "center"}
    if HAS_LIBRAQM:
        text_kwargs["language"] = "hi"

    # ── Wrap and measure text ─────────────────────────────────────────────
    layout   = _lyric_layout(text, font_size, W, H)
    wrapped  = layout["wrapped"]
    measure  = ImageDraw.Draw(Image.new("RGBA", (1, 1)))   # throwaway for bbox only
    bbox     = measure.multiline_textbbox((0, 0), wrapped, **text_kwargs)
    tw       = bbox[2] - bbox[0]
    th       = bbox[3] - bbox[1]

    # ── Pill geometry ─────────────────────────────────────────────────────
    pad_x   = layout["pad_x"]
    pad_y   = layout["pad_y"]
    pill_w  = min(tw + pad_x * 2, W - 60)    # never wider than screen
    pill_h  = th + pad_y * 2 + 12            # +12 for accent line space
    pill_x  = (W - pill_w) // 2
    pill_y  = layout["box_y"]

    # Clamp pill_y to never go off-screen
    pill_y  = max(60, pill_y)

    # ── Draw pill overlay (on separate RGBA layer) ────────────────────────
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov      = ImageDraw.Draw(overlay)
    radius  = 28

    # Parchment background pill
    ov.rounded_rectangle(
        [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
        radius=radius,
        fill=pill_fill,
    )
    # Accent top bar (emotion color — like RDR2 category color strip)
    ov.rounded_rectangle(
        [pill_x, pill_y, pill_x + pill_w, pill_y + 8],
        radius=radius,
        fill=(*accent, 240),
    )
    # Subtle border (dark sepia ink)
    ov.rounded_rectangle(
        [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
        radius=radius,
        outline=(*ink_color, 120),
        width=2,
    )

    # ── Alpha composite pill onto image ──────────────────────────────────
    # IMPORTANT: img_composited is a NEW image — must draw text on THIS, not on img
    img_composited = Image.alpha_composite(img, overlay)

    # ── Draw text on the COMPOSITED image ────────────────────────────────
    # This is the fix for the missing text bug:
    # Previously text was drawn on `img` before composite, then lost.
    draw   = ImageDraw.Draw(img_composited)
    text_x = pill_x + pad_x
    text_y = pill_y + pad_y + 8            # +8 to clear accent bar

    # Center text horizontally inside pill
    text_x = pill_x + (pill_w - tw) // 2

    # Drop shadow (sepia tone)
    for dx, dy in [(-2, 2), (2, 2), (0, 3), (0, -1)]:
        draw.multiline_text(
            (text_x + dx, text_y + dy),
            wrapped,
            fill=(*ink_color, 100),
            **text_kwargs,
        )

    # Main text — dark sepia ink (RDR2 label style)
    draw.multiline_text(
        (text_x, text_y),
        wrapped,
        fill=(*ink_color, 255),
        **text_kwargs,
    )

    # ── Save ─────────────────────────────────────────────────────────────
    img_composited.convert("RGB").save(str(img_path), "JPEG", quality=95, optimize=True)


def _overlay_lyrics_windows_native(img_path: Path, text: str, emotion: str = "default") -> bool:
    """Use Windows GDI+ text shaping for better Hindi ligatures."""
    if sys.platform != "win32":
        return False

    emotion_colors = {
        "romantic":   (160,  60,  80),
        "sad":        ( 60,  80, 130),
        "happy":      ( 80, 130,  60),
        "energetic":  (180, 110,  20),
        "devotional": (160, 110,  20),
        "longing":    (110,  70, 120),
        "default":    ( 80,  55,  30),
    }
    accent = emotion_colors.get(emotion, emotion_colors["default"])
    ink_color = (30, 20, 10)
    pill_fill = (242, 233, 205, 200)

    text = _shape_lyric_text_for_rendering(text)
    font_path = resolve_font_path("lyrics", text=text)
    if not font_path:
        return False

    img = Image.open(str(img_path)).convert("RGBA")
    width, height = img.size
    font_size = 68
    layout = _lyric_layout(text, font_size, width, height)

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ov = ImageDraw.Draw(overlay)
    radius = 28
    ov.rounded_rectangle(
        [layout["box_x"], layout["box_y"], layout["box_x"] + layout["box_w"], layout["box_y"] + layout["box_h"]],
        radius=radius,
        fill=pill_fill,
    )
    ov.rounded_rectangle(
        [layout["box_x"], layout["box_y"], layout["box_x"] + layout["box_w"], layout["box_y"] + 8],
        radius=radius,
        fill=(*accent, 240),
    )
    ov.rounded_rectangle(
        [layout["box_x"], layout["box_y"], layout["box_x"] + layout["box_w"], layout["box_y"] + layout["box_h"]],
        radius=radius,
        outline=(*ink_color, 120),
        width=2,
    )
    img_composited = Image.alpha_composite(img, overlay)
    temp_output = img_path.with_name(f"{img_path.stem}_lyric_tmp{img_path.suffix}")
    img_composited.convert("RGB").save(str(temp_output), "JPEG", quality=95, optimize=True)

    family_override = os.environ.get("LYRIC_FONT_FAMILY") if os.environ.get("LYRIC_FONT_PATH") else None
    font_family = family_override or _font_family_name(font_path)

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tf:
        tf.write(layout["wrapped"])
        text_file = Path(tf.name)

    ps_script = f"""
Add-Type -AssemblyName System.Drawing
$imagePath = [System.IO.Path]::GetFullPath("{str(temp_output)}")
$textPath  = [System.IO.Path]::GetFullPath("{str(text_file)}")
$fontPath  = [System.IO.Path]::GetFullPath("{str(font_path)}")
$text      = Get-Content -LiteralPath $textPath -Raw -Encoding UTF8
$source    = [System.Drawing.Image]::FromFile($imagePath)
$bitmap    = New-Object System.Drawing.Bitmap($source.Width, $source.Height, [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
$graphics  = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
$graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
$graphics.Clear([System.Drawing.Color]::White)
$graphics.DrawImage($source, 0, 0, $source.Width, $source.Height)
$source.Dispose()
$fontCollection = New-Object System.Drawing.Text.PrivateFontCollection
$fontCollection.AddFontFile($fontPath)
if ($fontCollection.Families.Length -gt 0) {{
    $fontFamily = $fontCollection.Families[0]
}} else {{
    $fontFamily = New-Object System.Drawing.FontFamily("{font_family}")
}}
$font = New-Object System.Drawing.Font($fontFamily, {font_size}, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
$format = New-Object System.Drawing.StringFormat
$format.Alignment = [System.Drawing.StringAlignment]::Center
$format.LineAlignment = [System.Drawing.StringAlignment]::Near
$format.FormatFlags = [System.Drawing.StringFormatFlags]::LineLimit
$format.Trimming = [System.Drawing.StringTrimming]::Word
$shadowBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(100, {ink_color[0]}, {ink_color[1]}, {ink_color[2]}))
$textBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, {ink_color[0]}, {ink_color[1]}, {ink_color[2]}))
$shadowRect = New-Object System.Drawing.RectangleF({layout["box_x"] + 2}, {layout["text_y"] + 2}, {layout["box_w"]}, {layout["box_h"]})
$textRect = New-Object System.Drawing.RectangleF({layout["box_x"]}, {layout["text_y"]}, {layout["box_w"]}, {layout["box_h"]})
$graphics.DrawString($text, $font, $shadowBrush, $shadowRect, $format)
$graphics.DrawString($text, $font, $textBrush, $textRect, $format)
$codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object {{ $_.MimeType -eq "image/jpeg" }} | Select-Object -First 1
$params = New-Object System.Drawing.Imaging.EncoderParameters(1)
$params.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, 95L)
$bitmap.Save($imagePath, $codec, $params)
$params.Dispose()
$shadowBrush.Dispose()
$textBrush.Dispose()
$font.Dispose()
$graphics.Dispose()
$bitmap.Dispose()
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    try:
        text_file.unlink(missing_ok=True)
    except Exception:
        pass

    if result.returncode == 0 and temp_output.exists():
        temp_output.replace(img_path)
        log.info(f"[overlay_lyrics] Windows native renderer OK with {font_family} ({font_path.name})")
        return True

    if temp_output.exists():
        temp_output.unlink(missing_ok=True)
    log.warning(f"[overlay_lyrics] Windows native renderer failed: {result.stderr[-300:].decode(errors='replace')}")
    return False


def _overlay_lyrics_ffmpeg_ass(img_path: Path, text: str, emotion: str = "default") -> bool:
    """Use ASS subtitles via libass for stronger complex-script shaping."""
    emotion_colors = {
        "romantic": "A03C50",
        "sad": "3C5082",
        "happy": "50823C",
        "energetic": "B46E14",
        "devotional": "A06E14",
        "longing": "6E4678",
        "default": "50371E",
    }

    text = _shape_lyric_text_for_rendering(text)
    font_path = resolve_font_path("lyrics", text=text)
    if not font_path:
        return False

    img = Image.open(str(img_path)).convert("RGBA")
    width, height = img.size
    font_size = 68
    layout = _lyric_layout(text, font_size, width, height)
    accent = emotion_colors.get(emotion, emotion_colors["default"])
    family_override = os.environ.get("LYRIC_FONT_FAMILY") if os.environ.get("LYRIC_FONT_PATH") else None
    font_family = family_override or _font_family_name(font_path)

    temp_output = img_path.with_name(f"{img_path.stem}_lyric_tmp{img_path.suffix}")
    box_x = layout["box_x"]
    box_w = layout["box_w"]
    box_y = layout["box_y"]
    box_h = layout["box_h"]
    text_y = layout["text_y"]

    with tempfile.NamedTemporaryFile("w", suffix=".ass", delete=False, encoding="utf-8") as tf:
        ass_file = Path(tf.name)
        tf.write(
            "[Script Info]\n"
            "ScriptType: v4.00+\n"
            f"PlayResX: {width}\n"
            f"PlayResY: {height}\n"
            "ScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
            "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Lyrics,{font_family},{font_size},&H001E140A,&H001E140A,&H64F2E9CD,&H00F2E9CD,"
            "0,0,0,0,100,100,0,0,1,18,0,2,30,30,180,1\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            f"Dialogue: 0,0:00:00.00,0:00:05.00,Lyrics,,0,0,0,,"
            f"{{\\bord2\\shad0\\1c&H1E140A&\\3c&H1E140A&\\4c&HF2E9CD&\\alpha&H00&"
            f"\\pos({width // 2},{text_y + font_size})}}{_ass_escape_text(layout['wrapped'])}\n"
        )

    vf = (
        f"drawbox=x={box_x}:y={box_y}:w={box_w}:h={box_h}:color=0xF2E9CD@0.82:t=fill,"
        f"drawbox=x={box_x}:y={box_y}:w={box_w}:h=8:color=0x{accent}@0.94:t=fill,"
        f"drawbox=x={box_x}:y={box_y}:w={box_w}:h={box_h}:color=0x1E140A@0.47:t=2,"
        f"subtitles='{_ffmpeg_escape_filter_value(str(ass_file.resolve()))}':fontsdir='{_ffmpeg_escape_filter_value(str(font_path.parent.resolve()))}'"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(img_path),
        "-vf", vf,
        "-frames:v", "1",
        str(temp_output),
    ]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    try:
        ass_file.unlink(missing_ok=True)
    except Exception:
        pass

    if result.returncode == 0 and temp_output.exists():
        temp_output.replace(img_path)
        log.info(f"[overlay_lyrics] ASS renderer OK with {font_family} ({font_path.name})")
        return True

    if temp_output.exists():
        temp_output.unlink(missing_ok=True)
    log.warning(f"[overlay_lyrics] ASS subtitles shaping failed: {result.stderr[-300:].decode(errors='replace')}")
    return False


def _overlay_lyrics_ffmpeg_drawtext(img_path: Path, text: str, emotion: str = "default") -> bool:
    """Use ffmpeg drawtext with shaping when available."""
    emotion_colors = {
        "romantic": "A03C50",
        "sad": "3C5082",
        "happy": "50823C",
        "energetic": "B46E14",
        "devotional": "A06E14",
        "longing": "6E4678",
        "default": "50371E",
    }

    text = _shape_lyric_text_for_rendering(text)
    font_path = resolve_font_path("lyrics", text=text)
    if not font_path:
        return False

    img = Image.open(str(img_path)).convert("RGBA")
    width, height = img.size
    font_size = 68
    layout = _lyric_layout(text, font_size, width, height)
    accent = emotion_colors.get(emotion, emotion_colors["default"])

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tf:
        tf.write(layout["wrapped"])
        text_file = Path(tf.name)

    temp_output = img_path.with_name(f"{img_path.stem}_lyric_tmp{img_path.suffix}")
    font_arg = _ffmpeg_escape_path(font_path)
    text_arg = _ffmpeg_escape_path(text_file)
    box_x = layout["box_x"]
    box_w = layout["box_w"]
    box_y = layout["box_y"]
    box_h = layout["box_h"]
    text_y = layout["text_y"]

    vf = (
        f"drawbox=x={box_x}:y={box_y}:w={box_w}:h={box_h}:color=0xF2E9CD@0.82:t=fill,"
        f"drawbox=x={box_x}:y={box_y}:w={box_w}:h=8:color=0x{accent}@0.94:t=fill,"
        f"drawbox=x={box_x}:y={box_y}:w={box_w}:h={box_h}:color=0x1E140A@0.47:t=2,"
        f"drawtext=fontfile='{font_arg}':textfile='{text_arg}':fontcolor=0x1E140A@0.35:fontsize={font_size}:"
        f"line_spacing=8:text_shaping=1:x=(w-text_w)/2+2:y={text_y}+2,"
        f"drawtext=fontfile='{font_arg}':textfile='{text_arg}':fontcolor=0x1E140A:fontsize={font_size}:"
        f"line_spacing=8:text_shaping=1:x=(w-text_w)/2:y={text_y}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(img_path),
        "-vf", vf,
        "-frames:v", "1",
        str(temp_output),
    ]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    try:
        text_file.unlink(missing_ok=True)
    except Exception:
        pass

    if result.returncode == 0 and temp_output.exists():
        temp_output.replace(img_path)
        log.info(f"[overlay_lyrics] drawtext renderer OK with {font_path.name}")
        return True

    if temp_output.exists():
        temp_output.unlink(missing_ok=True)
    log.warning(f"[overlay_lyrics] FFmpeg drawtext shaping failed: {result.stderr[-300:].decode(errors='replace')}")
    return False


def overlay_lyrics(img_path: Path, text: str, emotion: str = "default") -> None:
    """Render lyric text with strongest available shaping backend."""
    text = _clean_lyric_text(text)
    if not text:
        log.info("[overlay_lyrics] Skipping empty lyric after stage-tag cleanup.")
        return

    if sys.platform == "win32" and _needs_strict_conjunct_rendering(text):
        if _overlay_lyrics_windows_native(img_path, text, emotion):
            return
    if _overlay_lyrics_ffmpeg_ass(img_path, text, emotion):
        return
    if _overlay_lyrics_ffmpeg_drawtext(img_path, text, emotion):
        return
    if _overlay_lyrics_windows_native(img_path, text, emotion):
        return
    log.warning("[overlay_lyrics] Falling back to Pillow renderer; complex Hindi ligatures may differ from source text.")
    _overlay_lyrics_pil(img_path, text, emotion)


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
    use_nvidia_only: bool = False,
    skip_pollinations: bool = False,
) -> str:
    """Render one Instagram Reel MP4 with synced lyric frames."""
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

        # 1. Generate background (Pollinations-first, then SD3 fallback)
        generate_background_pollinations(
            prompt, style, img_path, mood=emotion, 
            use_nvidia_only=use_nvidia_only, 
            skip_pollinations=skip_pollinations
        )

        # 2. Overlay lyrics (text drawn correctly after composite)
        overlay_lyrics(img_path, text, emotion)

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
    concat_path = reel_dir / "concat.txt"
    with open(str(concat_path), "w", encoding="utf-8") as f:
        for fp, dur in zip(frame_paths, frame_durations):
            abs_fp = str(Path(fp).resolve()).replace("\\", "/")
            f.write(f"file '{abs_fp}'\n")
            f.write(f"duration {dur:.3f}\n")
        if frame_paths:
            last = str(Path(frame_paths[-1]).resolve()).replace("\\", "/")
            f.write(f"file '{last}'\n")      # FFmpeg concat demuxer requirement

    # ── Trim audio ───────────────────────────────────────────────────────
    audio_clip = reel_dir / "audio_clip.mp3"
    run_ffmpeg(
        "-ss", str(start_sec), "-t", str(duration),
        "-i", audio_path, "-acodec", "copy", str(audio_clip),
        label="audio_trim",
    )

    # ── Render video ─────────────────────────────────────────────────────
    output_video = song_folder / f"reel_{clip_num}.mp4"
    run_ffmpeg(
        "-f", "concat", "-safe", "0", "-i", str(concat_path),
        "-i", str(audio_clip),
        "-vf", (
            f"scale={REEL_WIDTH}:{REEL_HEIGHT}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={REEL_WIDTH}:{REEL_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
            "format=yuv420p"
        ),
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        str(output_video),
        label=f"render_reel_{clip_num}",
    )

    # ── Standalone MP3 clip ──────────────────────────────────────────────
    reel_mp3 = song_folder / f"reel_{clip_num}.mp3"
    run_ffmpeg(
        "-ss", str(start_sec), "-t", str(duration),
        "-i", audio_path, "-acodec", "copy", str(reel_mp3),
        label="reel_mp3",
    )

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
    parser.add_argument("--url",        "-u", required=True, help="YouTube URL or song name")
    parser.add_argument("--output",     "-o", default="downloads", help="Output directory")
    parser.add_argument("--skip-ai",    action="store_true", help="Skip AI reel suggestions")
    parser.add_argument("--skip-video", action="store_true", help="Skip video rendering")
    parser.add_argument("--use-nvidia", action="store_true", help="Force NVIDIA SD3 as primary")
    parser.add_argument("--skip-pollinations", action="store_true", help="Skip Pollinations AI")
    args = parser.parse_args()

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
                
                if not args.skip_video:
                    style = ai_data.get("image_style", "")
                    for clip in ai_data.get("clips", []):
                        render_reel_video(
                            clip, audio_path, style, song_folder, 
                            clip["clip_number"], 
                            use_nvidia_only=args.use_nvidia,
                            skip_pollinations=args.skip_pollinations
                        )
                style = ai_data.get("image_style", (
                    "watercolor wash, aged parchment background"
                    "muted sepia-amber palette, natural history plate aesthetic"
                ))
                mood = ai_data.get("style_preset", "default")

                if not args.skip_video:
                    for clip in ai_data.get("clips", []):
                        render_reel_video(
                            clip_data   = clip,
                            audio_path  = audio_path,
                            style       = style,
                            song_folder = song_folder,
                            clip_num    = clip.get("clip_number", 1),
                            mood        = mood,
                        )
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
