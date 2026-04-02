#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bollywood Reel Generator (Ghazal Edition)
========================================
High-quality automated Reel generation with Skia/HarfBuzz shaping,
NVIDIA AI clip selection, and SD3 background generation.
Includes a robust retry loop for daily automation.
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
import shutil
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
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
NVIDIA_IMAGE_API_KEY = os.environ.get("NVIDIA_IMAGE_API_KEY", "")
NVIDIA_IMAGE_INVOKE_URL = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-3-medium"
NVIDIA_LLM_URL   = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_LLM_MODEL = "openai/gpt-oss-120b"

REEL_WIDTH  = 1080
REEL_HEIGHT = 1920

SD3_NEGATIVE_PROMPT = (
    "blurry, low quality, watermark, text overlay, signature, logo, "
    "extra limbs, deformed hands, mutated fingers, western features, "
    "caucasian face, ugly, bad anatomy, disfigured, jpeg artifacts, "
    "photorealistic, 3D render, CGI, modern photography, color photograph"
)

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

REEL_PROMPT = """You are an expert Bollywood Instagram Reels editor and Stable Diffusion 3 prompt engineer.
I will give you a song transcript with timestamps in [MM:SS] format.

TASKS:
1. Pick the 2-3 BEST clips for Instagram Reels (30-90s each)
2. Generate hex background_color (dark) and text_color (light)
3. Use RED DEAD REDEMPTION 2 zoological compendium style prompts.

OUTPUT JSON ONLY.
"""

STAGE_TAG_RE = re.compile(r"\[.*?\]", re.IGNORECASE)
DEVANAGARI_CONJUNCT_RE = re.compile(r"([\u0915-\u0939\u0958-\u095f])\u094d([\u0915-\u0939\u0958-\u095f])")

# ── Color Utilities ──────────────────────────────────────────────────────────
def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    if len(h) != 6: return (0, 0, 0)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _luminance(r: int, g: int, b: int) -> float:
    def _lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)

def _contrast_ratio(rgb1: tuple, rgb2: tuple) -> float:
    l1, l2 = _luminance(*rgb1), _luminance(*rgb2)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)

def _ensure_contrast(bg_hex: str, text_hex: str) -> tuple:
    bg_rgb, text_rgb = _hex_to_rgb(bg_hex), _hex_to_rgb(text_hex)
    if _contrast_ratio(bg_rgb, text_rgb) >= 4.5: return bg_hex, text_hex
    return bg_hex, ("#FFFFFF" if _luminance(*bg_rgb) < 0.5 else "#000000")

DEFAULT_BG_COLOR = "#000000"
DEFAULT_TEXT_COLOR = "#FFFFFF"

# ── Utilities ────────────────────────────────────────────────────────────────
def _clean_lyric_text(text: str) -> str:
    if not text: return ""
    text = unicodedata.normalize("NFC", text.strip())
    text = STAGE_TAG_RE.sub(" ", text)
    return re.sub(r"\s{2,}", " ", text).strip()

def _needs_strict_conjunct_rendering(text: str) -> bool:
    return any(c in text for c in ["\u094d", "\u093f", "ि"])

def _repair_json(raw: str) -> str:
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
    return re.sub(r",\s*([}\]])", r"\1", raw.strip())

def seconds_to_mmss(seconds: float) -> str:
    return f"{int(seconds)//60:02d}:{int(seconds)%60:02d}"

def mmss_to_seconds(mmss: str) -> float:
    parts = mmss.strip().split(":")
    if len(parts) == 3: return int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
    return int(parts[0])*60 + int(parts[1])

def safe_filename(name: str, max_len: int = 50) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()[:max_len].strip()

def run_ffmpeg(*args, label: str = "ffmpeg") -> bool:
    cmd = ["ffmpeg", "-y"] + [str(a) for a in args]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return result.returncode == 0

# ── Processing ───────────────────────────────────────────────────────────────
def download_audio(url: str, output_dir: Path, cookies: str = None, proxy: str = None) -> tuple:
    import yt_dlp
    url = url.strip()
    if not (url.startswith("http") or url.startswith("www.")): url = f"ytsearch1:{url}"
    # Modern High-Reputation User-Agents
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ]
    
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / "%(title).50s.%(ext)s"),
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
        "quiet": True,
        "nocheckcertificate": True,
        "cookiefile": cookies,
        "proxy": proxy,
        "user_agent": random.choice(USER_AGENTS),
        "extractor_args": {
            "youtube": {
                "player_client": ["web", "mweb"]
            }
        }
    }
    
    if cookies:
        log.info(f"Applying cookies from {cookies}...")
    
    # Add a small random jitter to avoid 429 rate limiting
    time.sleep(random.uniform(3, 7))

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if "entries" in info: info = info["entries"][0]
    mp3_files = list(output_dir.glob("*.mp3"))
    if not mp3_files: raise FileNotFoundError("MP3 download failed.")
    return str(mp3_files[0]), info.get("id", ""), info.get("title", "Unknown")

def fetch_transcript(video_id: str, title: str, output_dir: Path) -> tuple:
    try:
        t_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try: t_obj = t_list.find_transcript(['hi'])
        except: t_obj = t_list.find_generated_transcript(['hi'])
        data = t_obj.fetch()
        lines = [f"[{seconds_to_mmss(e['start'])}] {e['text']}" for e in data]
        txt_path = output_dir / f"{safe_filename(title)}.txt"
        with open(txt_path, "w", encoding="utf-8") as f: f.write("\n".join(lines))
        return "\n".join(lines), str(txt_path)
    except Exception as e:
        log.error(f"Transcript failed: {e}")
        return None, None

def get_ai_reel_suggestions(transcript_text: str, title: str):
    if not NVIDIA_API_KEY: return None
    try:
        resp = requests.post(NVIDIA_LLM_URL, headers={"Authorization": f"Bearer {NVIDIA_API_KEY}"}, json={
            "model": NVIDIA_LLM_MODEL, "messages": [
                {"role": "system", "content": REEL_PROMPT},
                {"role": "user", "content": f"Song: {title}\nTranscript:\n{transcript_text}"}
            ]
        }, timeout=120)
        resp.raise_for_status()
        return json.loads(_repair_json(resp.json()["choices"][0]["message"]["content"]))
    except Exception as e:
        log.error(f"AI failed: {e}")
        return None

# ── Font Loader ──────────────────────────────────────────────────────────────
def resolve_font_path(text: str = "") -> Path | None:
    candidates = [
        Path("C:/Windows/Fonts/Nirmala.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"),
        Path("/usr/share/fonts/truetype/indic/Nirmala.ttf")
    ]
    for c in candidates:
        if c.exists(): return c
    return None

def load_font(size: int, text: str = "") -> ImageFont.FreeTypeFont:
    fp = resolve_font_path(text)
    if fp: return ImageFont.truetype(str(fp), size)
    return ImageFont.load_default()

# ── Render Logic ─────────────────────────────────────────────────────────────
def overlay_lyrics(img_path: Path, text: str, text_color: str = "#FFFFFF"):
    text = _clean_lyric_text(text)
    if not text: return
    img = Image.open(str(img_path)).convert("RGBA")
    draw = ImageDraw.Draw(img)
    font = load_font(70, text)
    wrapped = textwrap.fill(text, width=20)
    bbox = draw.textbbox((0, 0), wrapped, font=font)
    draw.text(((REEL_WIDTH-(bbox[2]-bbox[0]))//2, (REEL_HEIGHT-(bbox[3]-bbox[1]))//2), wrapped, fill=text_color, font=font, align="center")
    img.convert("RGB").save(str(img_path), "JPEG")

def render_reel_video(clip_data, audio_path, song_folder, clip_num, bg_color="#000000", text_color="#FFFFFF"):
    start = mmss_to_seconds(clip_data["start_time"])
    end = mmss_to_seconds(clip_data["end_time"])
    dur = end - start
    
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"reel{clip_num}_"))
    
    frame_paths = []
    durations = []
    lines = clip_data.get("lines", [])
    for i, line in enumerate(lines):
        p = tmp_dir / f"f{i:03d}.jpg"
        rgb = _hex_to_rgb(bg_color)
        Image.new("RGB", (REEL_WIDTH, REEL_HEIGHT), rgb).save(p, "JPEG")
        overlay_lyrics(p, line["text"], text_color=text_color)
        frame_paths.append(p)
        
        # Timing
        if i < len(lines) - 1:
            durations.append(max(mmss_to_seconds(lines[i+1]["time"]) - mmss_to_seconds(line["time"]), 1.5))
        else:
            durations.append(max(end - mmss_to_seconds(line["time"]), 1.5))

    concat_txt = tmp_dir / "concat.txt"
    with open(concat_txt, "w") as f:
        for p, d in zip(frame_paths, durations):
            f.write(f"file '{p.name}'\nduration {d:.3f}\n")
        f.write(f"file '{frame_paths[-1].name}'\n")

    safe_audio = tmp_dir / "audio.mp3"
    shutil.copy2(audio_path, safe_audio)
    
    out_video = song_folder / f"reel_{clip_num}.mp4"
    safe_out = tmp_dir / "out.mp4"
    
    run_ffmpeg("-f", "concat", "-safe", "0", "-i", str(concat_txt), "-ss", str(start), "-t", str(dur), "-i", str(safe_audio), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest", str(safe_out))
    
    if safe_out.exists(): shutil.move(safe_out, out_video)
    shutil.rmtree(tmp_dir)
    return str(out_video)

# ── Main with Meta Export ────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="YouTube URL or search query")
    parser.add_argument("--auto", action="store_true", help="Pull from ghazal_songs.json")
    parser.add_argument("--cookies", help="Path to cookies.txt")
    parser.add_argument("--proxy", help="Proxy URL")
    parser.add_argument("--output", default="downloads")
    args = parser.parse_args()

    max_attempts = 5 if args.auto else 1
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    success = False

    for attempt in range(max_attempts):
        url = args.url
        try:
            if args.auto:
                json_path = Path("data/shayari/ghazal_songs.json")
                if not json_path.exists(): return
                with open(json_path, "r", encoding="utf-8") as f: songs = json.load(f)
                if not songs: return
                url = songs.pop(0)
                with open(json_path, "w", encoding="utf-8") as f: json.dump(songs, f, indent=2, ensure_ascii=False)
                log.info(f"\n--- Attempt {attempt+1}/{max_attempts}: {url} ---")

            audio_p, vid_id, title = download_audio(url, output_dir, cookies=args.cookies, proxy=args.proxy)
            song_folder = output_dir / safe_filename(title)
            song_folder.mkdir(parents=True, exist_ok=True)
            
            transcript, _ = fetch_transcript(vid_id, title, song_folder)
            if not transcript: raise ValueError("No transcript")
            
            ai_data = get_ai_reel_suggestions(transcript, title)
            if not ai_data: raise ValueError("AI failed")
            
            bg_c, txt_c = _ensure_contrast(ai_data.get("background_color", "#000000"), ai_data.get("text_color", "#FFFFFF"))
            
            for clip in ai_data.get("clips", []):
                clip_num = clip.get("clip_number", 1)
                vid_path = render_reel_video(clip, audio_p, song_folder, clip_num, bg_color=bg_c, text_color=txt_c)
                
                if vid_path:
                    base_desc = ai_data.get("youtube_description", "")
                    full_desc = f"{base_desc}\n\nPoetry:\n{transcript}"
                    if len(full_desc) > 4800: full_desc = full_desc[:4800] + "..."
                    
                    upload_meta = {
                        "title": ai_data.get("youtube_title", title),
                        "description": full_desc,
                        "video_path": str(vid_path),
                        "keywords": ai_data.get("youtube_description", "").split("#")[1:]
                    }
                    meta_path = output_dir / f"upload_metadata_{clip_num}.json"
                    with open(meta_path, "w", encoding="utf-8") as f:
                        json.dump(upload_meta, f, ensure_ascii=False, indent=2)
                    log.info(f"Saved Metadata: {meta_path.name}")
            
            success = True
            break
        except Exception as e:
            log.warning(f"Attempt failed: {e}")
            if not args.auto: sys.exit(1)

    if not success: sys.exit(1)

if __name__ == "__main__":
    main()
