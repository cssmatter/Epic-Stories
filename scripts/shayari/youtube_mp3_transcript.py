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

OUTPUT JSON FORMAT:
{
  "background_color": "#hex",
  "text_color": "#hex",
  "youtube_title": "Catchy Title",
  "youtube_description": "Description with #hashtags",
  "clips": [
    {
      "clip_number": 1,
      "start_time": "MM:SS",
      "end_time": "MM:SS",
      "visual_description": "prompt for SD3",
      "lines": [
        {"time": "MM:SS", "text": "lyric line"}
      ]
    }
  ]
}
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
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.error(f"FFmpeg [{label}] FAILED:\n{result.stderr[-2000:]}")
        return False
    return True

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
                "player_client": ["android_vr", "web"],
                "player_skip": ["mweb", "web_embedded", "android"]
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
    
    # Sort files by modified time to guarantee we grab the one that just finished downloading
    mp3_files = sorted(output_dir.glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not mp3_files: raise FileNotFoundError("MP3 download failed.")
    return str(mp3_files[0]), info.get("id", ""), info.get("title", "Unknown")

def fetch_transcript(video_id: str, title: str, output_dir: Path) -> tuple:
    try:
        data = None
        
        # Strategy 1: New Instance-based API (YouTubeTranscriptApi().fetch)
        try:
            log.info("Trying instance-based fetch...")
            data = YouTubeTranscriptApi().fetch(video_id, languages=['hi', 'en'])
        except (TypeError, AttributeError, Exception) as e:
            # Strategy 2: Modern Static API (YouTubeTranscriptApi.list_transcripts)
            if hasattr(YouTubeTranscriptApi, 'list_transcripts'):
                log.info("Trying list_transcripts static method...")
                try:
                    t_list = YouTubeTranscriptApi.list_transcripts(video_id)
                    try: t_obj = t_list.find_transcript(['hi', 'en'])
                    except: t_obj = t_list.find_generated_transcript(['hi', 'en'])
                    data = t_obj.fetch()
                except Exception: pass
            
            # Strategy 3: Legacy Static API (YouTubeTranscriptApi.get_transcript)
            if not data and hasattr(YouTubeTranscriptApi, 'get_transcript'):
                log.info("Trying get_transcript static method...")
                try:
                    data = YouTubeTranscriptApi.get_transcript(video_id, languages=['hi', 'en'])
                except Exception: pass
        
        if not data:
            raise RuntimeError("All transcript retrieval strategies failed.")
            
        lines = []
        for e in data:
            # Handle both dictionary (Standard/Legacy) and Object (New v0.6.3+) formats
            if isinstance(e, dict):
                start = e.get('start', 0)
                text = e.get('text', '')
            else:
                start = getattr(e, 'start', 0)
                text = getattr(e, 'text', '')
            lines.append(f"[{seconds_to_mmss(start)}] {text}")

        txt_path = output_dir / f"{safe_filename(title)}.txt"
        with open(txt_path, "w", encoding="utf-8") as f: f.write("\n".join(lines))
        return "\n".join(lines), str(txt_path)
    except Exception as e:
        log.error(f"Transcript failed: {e}")
        return None, None

def _repair_json(text: str) -> str:
    """Extracts JSON from markdown code blocks or cleans up common AI noise."""
    if not text: return "{}"
    # Remove markdown code blocks
    text = re.sub(r"```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```\s*", "", text)
    # Extract outer-most braces
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match: return match.group(1)
    return text.strip()

def generate_background(prompt: str, output_path: Path) -> bool:
    """Generates a 1080x1920 background image using SD3."""
    key = os.environ.get("NVIDIA_API_KEY") # Use same key as LLM
    if not key:
        log.error("NVIDIA_API_KEY missing for image generation.")
        return False
        
    headers = {
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }
    
    payload = {
        "prompt": prompt,
        "negative_prompt": SD3_NEGATIVE_PROMPT,
        "aspect_ratio": "9:16",
        "mode": "text-to-image",
        "model": "stabilityai/stable-diffusion-3-medium"
    }

    try:
        log.info(f"Generating Background SD3: {prompt[:50]}...")
        # Use a retry loop for the image API as it can be flaky
        for attempt in range(3):
            response = requests.post(NVIDIA_IMAGE_INVOKE_URL, headers=headers, json=payload)
            if response.status_code == 202:
                # Handle async if needed (poll), but SD3 medium usually returns 200 or 202 with polling
                # Actually NVIDIA SD3 on integrate API usually returns 200 with base64
                pass
            
            if response.status_code == 200:
                data = response.json()
                if "artifacts" in data:
                    import base64
                    image_b64 = data["artifacts"][0]["base64"]
                    with open(output_path, "wb") as f:
                        f.write(base64.b64decode(image_b64))
                    return True
                elif "image" in data: # Newer NVIDIA API format
                    import base64
                    with open(output_path, "wb") as f:
                        f.write(base64.b64decode(data["image"]))
                    return True
            
            log.warning(f"Image API Attempt {attempt+1} failed: {response.status_code}")
            time.sleep(2)
            
        return False
    except Exception as e:
        log.error(f"Image generation error: {e}")
        return False

def get_ai_reel_suggestions(transcript_text: str, title: str):
    if not NVIDIA_API_KEY:
        log.error("NVIDIA_API_KEY is missing! Set it before running locally.")
        return None
    try:
        log.info(f"Requesting AI suggestions for: {title}")
        resp = requests.post(NVIDIA_LLM_URL, headers={"Authorization": f"Bearer {NVIDIA_API_KEY}"}, json={
            "model": NVIDIA_LLM_MODEL, "messages": [
                {"role": "system", "content": REEL_PROMPT},
                {"role": "user", "content": f"Song: {title}\nTranscript:\n{transcript_text}"}
            ]
        }, timeout=120)
        
        if resp.status_code != 200:
            log.error(f"NVIDIA API Error ({resp.status_code}): {resp.text}")
            resp.raise_for_status()
            
        json_resp = resp.json()
        choices = json_resp.get("choices", [])
        if not choices:
            log.error(f"NVIDIA API returned NO choices. Full response: {json_resp}")
            return None
            
        content = choices[0].get("message", {}).get("content", "")
        if not content:
            log.error("AI returned empty content.")
            return None
            
        repaired = _repair_json(content)
        return json.loads(repaired)
    except Exception as e:
        log.error(f"AI failed: {e}")
        return None

# ── Font Loader ──────────────────────────────────────────────────────────────
def resolve_font_path(text: str = "") -> Path | None:
    # Samanya.ttf is a legacy ASCII-mapped font. We MUST use a standard Unicode Hindi font
    script_dir = Path(__file__).parent
    candidates = [
        script_dir / "fonts" / "TiroDevanagariHindi-Regular.ttf",
        Path("C:/Windows/Fonts/Nirmala.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf")
    ]
    for p in candidates:
        if p.exists():
            return p
            
    # Fallback search if Nirmala.ttc wasn't in C:/Windows/Fonts
    for p in Path("C:/Windows/Fonts").glob("Nirmala*.ttc"):
        return p
        
    log.warning("Could not find suitable standard Hindi font!")
    return None

def load_font(size: int, text: str = "") -> ImageFont.FreeTypeFont:
    fp = resolve_font_path(text)
    if fp: return ImageFont.truetype(str(fp), size)
    return ImageFont.load_default()

# ── Render Logic ─────────────────────────────────────────────────────────────
def render_skia_hindi_text(canvas, text, font_path, font_size, max_width, start_y, color_hex):
    """
    Renders Hindi text with proper shaping using HarfBuzz and Skia.
    Ported from working daily_shayari_video.py
    """
    rgba = _hex_to_rgb(color_hex) + (255,)
    sk_color = skia.ColorSetARGB(rgba[3], rgba[0], rgba[1], rgba[2])
    
    with open(font_path, "rb") as f:
        font_data = f.read()
    face = hb.Face(font_data)
    hb_font = hb.Font(face)
    hb_font.scale = (font_size * 64, font_size * 64)
    
    sk_typeface = skia.Typeface.MakeFromFile(str(font_path))
    sk_font = skia.Font(sk_typeface, font_size)
    sk_paint = skia.Paint(Color=sk_color, AntiAlias=True)
    sk_paint.setStyle(skia.Paint.kStrokeAndFill_Style)
    sk_paint.setStrokeWidth(0.8) # Slight bolding for premium look
    
    lines = []
    words = text.split(' ')
    current_line_words = []
    
    for word in words:
        test_line = ' '.join(current_line_words + [word])
        test_buf = hb.Buffer()
        test_buf.add_str(test_line)
        test_buf.guess_segment_properties()
        hb.shape(hb_font, test_buf, {})
        width = sum(p.x_advance for p in test_buf.glyph_positions) / 64.0
        
        if width <= max_width:
            current_line_words.append(word)
        else:
            lines.append(' '.join(current_line_words))
            current_line_words = [word]
    lines.append(' '.join(current_line_words))
    
    curr_y = start_y
    line_height = font_size * 1.4
    
    for line in lines:
        buf = hb.Buffer()
        buf.add_str(line)
        buf.guess_segment_properties()
        hb.shape(hb_font, buf, {})
        
        glyphs = [info.codepoint for info in buf.glyph_infos]
        positions = []
        
        line_width = sum(p.x_advance for p in buf.glyph_positions) / 64.0
        curr_x = (REEL_WIDTH - line_width) / 2
        
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

def overlay_lyrics(img_path: Path, text: str, text_color: str = "#FFFFFF"):
    """Render lyrics onto a frame using PIL (Pillow) – the simplest, most reliable approach."""
    text = _clean_lyric_text(text)
    if not text: return
    
    img = Image.open(str(img_path)).convert("RGBA")
    draw = ImageDraw.Draw(img)
    
    font = load_font(130, text)
    wrapped = textwrap.fill(text, width=15)
    
    # CORRECT bounding box centering:
    # textbbox returns (left, top, right, bottom) relative to draw origin (0,0).
    # 'top' is NOT 0 – it's the ascender offset (e.g. 105). We must subtract it.
    # x_center = (W - (right - left)) / 2 - left
    # y_center = (H - (bottom - top)) / 2 - top
    bbox = draw.textbbox((0, 0), wrapped, font=font)
    x = (REEL_WIDTH  - (bbox[2] - bbox[0])) // 2 - bbox[0]
    y = (REEL_HEIGHT - (bbox[3] - bbox[1])) // 2 - bbox[1]
    
    # Black stroke for readability on any background, then coloured text on top
    for dx, dy in [(-2,-2),(2,-2),(-2,2),(2,2),(0,3),(0,-3),(3,0),(-3,0)]:
        draw.text((x+dx, y+dy), wrapped, font=font, fill="#000000", align="center")
    draw.text((x, y), wrapped, font=font, fill=text_color, align="center")
    
    img.convert("RGB").save(str(img_path), "JPEG")

def render_reel_video(clip_data, audio_path, song_folder, clip_num, bg_color="#000000", text_color="#FFFFFF"):
    # Resilient key access for start/end times
    s_raw = clip_data.get("start_time") or clip_data.get("start") or clip_data.get("startTime", "00:00")
    e_raw = clip_data.get("end_time") or clip_data.get("end") or clip_data.get("endTime", "00:30")
    
    start = mmss_to_seconds(s_raw)
    end = mmss_to_seconds(e_raw)
    dur = end - start
    
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"reel{clip_num}_"))
    
    # ── Background Generation (DISABLED as requested) ────────────────────────
    has_bg = False
    # bg_image_path = tmp_dir / "bg.png"
    # visual_prompt = clip_data.get("visual_description")
    # if visual_prompt:
    #     has_bg = generate_background(visual_prompt, bg_image_path)
    
    frame_paths = []
    durations = []
    lines = clip_data.get("lines", [])
    
    font_path = resolve_font_path("")
    if not font_path:
        log.error("No font found! Cannot render frames.")
        return None
    
    for i, line in enumerate(lines):
        p = tmp_dir / f"f{i:03d}.jpg"
        raw_text = _clean_lyric_text(line.get("text", ""))
        
        # === Bulletproof Composite: Skia (Text) -> PIL (Background + Save) ===
        # 1. Provide a PIL Background
        rgb = _hex_to_rgb(bg_color)
        bg_img = Image.new("RGB", (REEL_WIDTH, REEL_HEIGHT), rgb)
        
        # 2. Skia Transparent Surface for Text
        surface = skia.Surface(REEL_WIDTH, REEL_HEIGHT)
        canvas = surface.getCanvas()
        canvas.clear(skia.ColorTRANSPARENT)
        
        # 3. Render Hindi text using HarfBuzz shaping
        if raw_text:
            font_size = 100
            line_height = font_size * 1.4
            words = raw_text.split()
            
            with open(str(font_path), "rb") as f_data:
                face = hb.Face(f_data.read())
            hb_font_obj = hb.Font(face)
            hb_font_obj.scale = (font_size * 64, font_size * 64)
            
            test_lines = []
            cur_words = []
            max_w = REEL_WIDTH - 100
            for w in words:
                test = ' '.join(cur_words + [w])
                buf = hb.Buffer()
                buf.add_str(test)
                buf.guess_segment_properties()
                hb.shape(hb_font_obj, buf, {})
                tw = sum(pos.x_advance for pos in buf.glyph_positions) / 64.0
                if tw <= max_w:
                    cur_words.append(w)
                else:
                    test_lines.append(' '.join(cur_words))
                    cur_words = [w]
            test_lines.append(' '.join(cur_words))
            
            total_h = len(test_lines) * line_height
            start_y = (REEL_HEIGHT - total_h) / 2 + font_size
            
            render_skia_hindi_text(canvas, raw_text, font_path, font_size, max_w, start_y, text_color)
        
        # 4. Composite in PIL
        sk_image = surface.makeImageSnapshot()
        # Explicitly read bytes as BGRA (Skia's internal layout on Windows) to prevent pixel corruption
        text_layer = Image.frombytes("RGBA", (REEL_WIDTH, REEL_HEIGHT), sk_image.tobytes(), "raw", "BGRA")
        
        bg_img.paste(text_layer, (0, 0), text_layer)
        bg_img.save(str(p), "JPEG", quality=95)
        
        frame_paths.append(p)
        
        # Timing
        if i < len(lines) - 1:
            durations.append(max(mmss_to_seconds(lines[i+1]["time"]) - mmss_to_seconds(line["time"]), 1.5))
        else:
            durations.append(max(end - mmss_to_seconds(line["time"]), 1.5))

    concat_txt = tmp_dir / "concat.txt"
    # IMPORTANT: Use absolute paths in concat.txt so FFmpeg finds frames
    # regardless of the current working directory.
    with open(concat_txt, "w") as f:
        for p, d in zip(frame_paths, durations):
            # Forward slashes prevent FFmpeg path parsing issues on Windows
            safe_p = str(p.resolve()).replace("\\", "/")
            f.write(f"file '{safe_p}'\nduration {d:.3f}\n")
        # FFmpeg concat requires the last file to be specified again without a duration
        # (or just a short duration) to hold the last frame. We'll hold it for 1.5s
        safe_last = str(frame_paths[-1].resolve()).replace("\\", "/")
        f.write(f"file '{safe_last}'\n")

    safe_audio = tmp_dir / "audio.mp3"
    shutil.copy2(audio_path, safe_audio)

    
    out_video = song_folder / f"reel_{clip_num}.mp4"
    safe_out = tmp_dir / "out.mp4"
    
    log.info(f"Running FFmpeg for reel_{clip_num} | dur={dur:.1f}s | frames={len(frame_paths)}")
    
    ok = run_ffmpeg(
        # Video: image concat
        "-f", "concat", "-safe", "0", "-i", str(concat_txt),
        # Audio: trim to clip window
        "-ss", str(start), "-t", str(dur), "-i", str(safe_audio),
        # Encoding
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-t", str(dur),
        str(safe_out),
        label=f"reel_{clip_num}"
    )
    
    if ok and safe_out.exists():
        shutil.move(safe_out, out_video)
        log.info(f"Reel saved: {out_video}")
    else:
        log.error(f"FFmpeg failed for reel_{clip_num}. Check errors above.")
    try:
        shutil.rmtree(tmp_dir)
    except Exception:
        pass
    return str(out_video) if out_video.exists() else None

# ── Main with Meta Export ────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="YouTube URL or search query")
    parser.add_argument("--auto", action="store_true", help="Pull from ghazal_songs.json")
    parser.add_argument("--cookies", help="Path to cookies.txt")
    parser.add_argument("--proxy", help="Proxy URL")
    parser.add_argument("--output", default="downloads")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    def process_url(target_url):
        log.info(f"Resolving video for: {target_url}")
        # 1. Resolve exact Video ID and Title first
        audio_p, vid_id, title = download_audio(target_url, output_dir, cookies=args.cookies, proxy=args.proxy)
        
        song_folder = output_dir / safe_filename(title)
        song_folder.mkdir(parents=True, exist_ok=True)
        
        # 2. Use the exact same ID for transcript
        transcript, _ = fetch_transcript(vid_id, title, song_folder)
        if not transcript:
            log.warning(f"No transcript found for {vid_id} ({title}). Cannot generate synced reels.")
            return False # Non-fatal failure
            
        ai_data = get_ai_reel_suggestions(transcript, title)
        if not ai_data:
            log.warning(f"AI failed to generate suggestions for {title}.")
            return False
            
        bg_c, txt_c = _ensure_contrast(ai_data.get("background_color", "#000000"), ai_data.get("text_color", "#FFFFFF"))
        
        for clip in ai_data.get("clips", []):
            clip_num = clip.get("clip_number", 1)
            # Pass original vid_id to ensure we are cutting the right audio
            vid_path = render_reel_video(clip, audio_p, song_folder, clip_num, bg_color=bg_c, text_color=txt_c)
            
            if vid_path:
                base_desc = ai_data.get("youtube_description", "")
                
                # Clean up the transcript (remove [00:03], [संगीत], and empty lines)
                clean_transcript = "\n".join(
                    line for line in (STAGE_TAG_RE.sub("", t).strip() for t in transcript.split("\n"))
                    if line
                )
                
                full_desc = f"{base_desc}\n\nPoetry:\n{clean_transcript}"
                if len(full_desc) > 4800: full_desc = full_desc[:4800] + "..."
                
                # Also strip bracketed tags from keywords (and split correctly)
                base_keywords = ai_data.get("youtube_description", "").split("#")[1:]
                clean_keywords = [STAGE_TAG_RE.sub("", k).strip() for k in base_keywords]
                
                upload_meta = {
                    "title": ai_data.get("youtube_title", title),
                    "description": full_desc,
                    "video_path": str(vid_path),
                    "keywords": [k for k in clean_keywords if k]
                }
                meta_path = song_folder / f"upload_metadata_{clip_num}.json"
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(upload_meta, f, ensure_ascii=False, indent=2)
                log.info(f"Saved Metadata: {meta_path.name}")
        return True

    if args.auto:
        json_path = Path("data/shayari/ghazal_songs.json")
        if not json_path.exists():
            log.info("No ghazal_songs.json found.")
            sys.exit(0)
            
        with open(json_path, "r", encoding="utf-8") as f:
            songs = json.load(f)
            
        while songs:
            url = songs[0]  # Peek the first song
            log.info(f"\n--- Processing Auto Queue: {url} ({len(songs)} remaining) ---")
            try:
                success = process_url(url)
                
                # We pop it regardless of success/fail to keep the queue moving
                # (unless it was a network error, but for missing transcripts we skip)
                songs.pop(0)
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(songs, f, indent=2, ensure_ascii=False)
                
                if not success:
                    log.warning(f"Skipped {url} due to processing issues. Moving to next.")
                
                if songs:
                    log.info("Pausing for 10 seconds before next song...")
                    time.sleep(10)
            except Exception as e:
                log.error(f"Critical failure on {url}: {e}")
                # For critical errors (lost auth, etc.), we stop. 
                # For per-song errors, process_url already returns False.
                sys.exit(1)
    else:
        if not args.url:
            log.error("Must provide --url if not using --auto")
            sys.exit(1)
            
        try:
            process_url(args.url)
        except Exception as e:
            log.error(f"Failed to process {args.url}: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
