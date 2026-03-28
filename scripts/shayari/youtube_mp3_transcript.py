#!/usr/bin/env python3
"""
YouTube MP3 & Transcript Downloader + AI Reel Video Generator
==============================================================
Downloads audio + transcript, uses NVIDIA AI to suggest the best
2-3 Reel clips with per-line lyrics + image prompts, generates
styled background images, and renders Instagram-ready 9:16 videos.

Usage:
  python youtube_mp3_transcript.py --url "song name"
  python youtube_mp3_transcript.py --url "https://youtu.be/Qhwafoo7Pnc?si=K2q-vA4a0H5C5W5z" --skip-ai
"""

import argparse
import json
import math
import os
import re
import subprocess
import hashlib
from pathlib import Path
from youtube_transcript_api import YouTubeTranscriptApi

NVIDIA_API_KEY = os.environ.get(
    "NVIDIA_API_KEY",
    "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"
)

# Gemini API Key for image generation
GEMINI_API_KEY = os.environ.get(
    "GEMINI_API_KEY",
    os.environ.get("GOOGLE_API_KEY", "AIzaSyDNtugK2Xw7YIW4njN-Y1DeZs0Oq268icQ")
)

REEL_PROMPT = """You are an expert music video editor for Instagram Reels.

I will give you a song transcript with timestamps in [MM:SS] format.
Your job: pick the 2-3 BEST clips for Instagram Reels.

Rules:
- Each clip MUST be between 30 and 90 seconds long.
- Avoid segments that are only "[संगीत]", "[Music]", "[Applause]" or instrumental.
- Pick the most emotionally impactful, catchy, or viral-worthy parts.
- For each clip, provide EVERY lyric line with its timestamp.
- Generate ONE consistent image style description for the entire song (e.g. "oil painting on canvas").
- For each lyric line, generate a specific image prompt that matches the lyrics but uses the same art style.

Respond ONLY with valid JSON. No markdown fences, no explanation.
Format:
{
  "image_style": "consistent style description for all images in this song",
  "clips": [
    {
      "clip_number": 1,
      "start_time": "MM:SS",
      "end_time": "MM:SS",
      "reason": "Why this clip is great",
      "lines": [
        {
          "time": "MM:SS",
          "text": "exact lyric line",
          "image_prompt": "specific scene description matching this line, using the song's image style"
        }
      ]
    }
  ]
}
"""

def seconds_to_mmss(seconds: float) -> str:
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02d}:{s:02d}"

def mmss_to_seconds(mmss: str) -> float:
    parts = mmss.strip().split(":")
    return int(parts[0]) * 60 + int(parts[1])

# ── Download ─────────────────────────────────────────────────────────────────

def download_audio_and_get_id(url: str, output_dir: str):
    import yt_dlp
    url = url.strip()
    if not (url.startswith("http") or url.startswith("www.")):
        print(f"🔍 Searching for: {url}...")
        url = f"ytsearch1:{url}"
    elif not url.startswith("http"):
        url = "https://" + url

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_dir, "%(title).50s.%(ext)s"),
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
        "quiet": True, "no_warnings": True,
        "javascript_runtime": "node", # Use Node.js for JS extraction
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if "entries" in info: info = info["entries"][0]
        return str(list(Path(output_dir).glob("*.mp3"))[0]), info.get("id"), info.get("title", "Unknown")

# ── Transcript ───────────────────────────────────────────────────────────────

def save_transcript(video_id, title, output_dir):
    print(f"📝 Fetching transcript for: {title}...")
    try:
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id, languages=['hi', 'en'])

        clean_title = re.sub(r'[\\/*?:"<>|]', '', title).strip()[:50].strip()
        txt_path = Path(output_dir) / f"{clean_title}.txt"

        lines = []
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"Title: {title}\n")
            f.write(f"YouTube ID: {video_id}\n")
            f.write("="*40 + "\n\n")
            for entry in transcript:
                time_str = seconds_to_mmss(entry.start)
                line = f"[{time_str}] {entry.text}"
                f.write(line + "\n")
                lines.append(line)

        print(f"✅ Transcript saved: {txt_path.name}")
        return "\n".join(lines), str(txt_path)
    except Exception as e:
        print(f"❌ Could not fetch transcript: {e}")
        return None, None

# ── AI Reel Selection ────────────────────────────────────────────────────────

def get_ai_reel_suggestions(transcript_text, title):
    import requests as req

    print(f"\n🤖 Asking NVIDIA AI for best Reel clips...")

    user_msg = f"Song: {title}\n\nTranscript:\n{transcript_text}"

    try:
        resp = req.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {NVIDIA_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "meta/llama-3.3-70b-instruct",
                "temperature": 0.3,
                "max_tokens": 4096,
                "messages": [
                    {"role": "system", "content": REEL_PROMPT},
                    {"role": "user", "content": user_msg}
                ]
            },
            timeout=120,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"^```\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        data = json.loads(raw)
        clips = data.get("clips", [])
        style = data.get("image_style", "cinematic moody gradient")
        print(f"✅ AI suggested {len(clips)} clips with style: {style}")
        return data
    except Exception as e:
        print(f"❌ AI suggestion failed: {e}")
        return None

# ── Image Generation ──────────────────────────────────────────────────────────

def generate_background(image_prompt, style, output_path, width=1080, height=1920):
    """Generate background using Gemini 2.5 Flash Image, fallback to gradient."""
    from google import genai
    from google.genai import types
    from PIL import Image

    import time
    max_retries = 3
    retry_delay = 5

    try:
        print(f"      🎨 Generating AI image via Gemini 2.5 Flash: {image_prompt[:40]}...")
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # We append the style and format requirements to the prompt
        full_prompt = f"{image_prompt}, {style}, cinematic, 8k resolution, 9:16 aspect ratio"
        
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash-image",
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        candidate_count=1,
                        image_config=types.ImageConfig(aspect_ratio="9:16")
                    )
                )
                
                # Process and save the generated image
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        # The SDK provides a helper to save the image directly
                        img_data = part.as_image()
                        img_data.save(str(output_path))
                        
                        # Resize image to target 1080x1920
                        with Image.open(output_path) as img:
                            img = img.resize((width, height), Image.Resampling.LANCZOS)
                            img.save(str(output_path), quality=95)
                        
                        print(f"      ✅ Gemini Image saved successfully!")
                        return str(output_path)
                    elif part.text:
                        print(f"      ⚠️ Model Message: {part.text}")
                
                print(f"      ⚠️ No image data returned from Gemini.")
                break # Exit retry loop if we got a response but no image

            except Exception as e:
                if "429" in str(e) or "RetryInfo" in str(e) or "500" in str(e):
                    print(f"      ⚠️ Gemini API busy (attempt {attempt+1}/{max_retries}), retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2 # Exponential backoff
                else:
                    raise e

    except Exception as e:
        print(f"      ⚠️ Gemini API failed after retries ({e}).")

    print(f"      Gradient fallback for: {output_path.name}")
    # Fallback to local Pillow Gradient
    from PIL import ImageDraw, ImageFilter
    import random
    import hashlib

    seed = int(hashlib.md5(style.encode()).hexdigest()[:8], 16)
    random.seed(seed)

    palettes = [
        [(10, 10, 40), (80, 20, 120), (180, 40, 100)],
        [(5, 15, 30), (20, 60, 100), (40, 150, 180)],
        [(20, 5, 5), (100, 20, 20), (200, 80, 40)],
        [(5, 20, 15), (20, 80, 60), (40, 180, 120)],
        [(15, 10, 30), (60, 30, 90), (140, 60, 200)],
        [(10, 10, 10), (40, 40, 50), (80, 80, 100)],
        [(20, 10, 5), (100, 50, 20), (220, 140, 40)],
        [(5, 5, 25), (30, 30, 80), (100, 80, 180)],
    ]
    palette = random.choice(palettes)

    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    c1, c2, c3 = palette
    for y in range(height):
        ratio = y / height
        if ratio < 0.5:
            r2 = ratio * 2
            r = int(c1[0] + (c2[0] - c1[0]) * r2)
            g = int(c1[1] + (c2[1] - c1[1]) * r2)
            b = int(c1[2] + (c2[2] - c1[2]) * r2)
        else:
            r2 = (ratio - 0.5) * 2
            r = int(c2[0] + (c3[0] - c2[0]) * r2)
            g = int(c2[1] + (c3[1] - c2[1]) * r2)
            b = int(c2[2] + (c3[2] - c2[2]) * r2)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    vignette = Image.new("L", (width, height), 255)
    vdraw = ImageDraw.Draw(vignette)
    for i in range(40):
        opacity = int(255 * (1 - i / 40))
        vdraw.rectangle([i, i, width - i, height - i], outline=opacity)
    vignette = vignette.filter(ImageFilter.GaussianBlur(80))
    img = Image.composite(img, Image.new("RGB", (width, height), (0, 0, 0)), vignette)

    img.save(str(output_path), quality=95)
    return str(output_path)

# ── Video Rendering ──────────────────────────────────────────────────────────

def render_reel_video(clip_data, audio_path, style, song_folder, clip_num):
    """Render a single Reel video with synced lyrics on styled backgrounds."""
    from PIL import Image, ImageDraw, ImageFont
    import textwrap

    lines = clip_data.get("lines", [])
    start_sec = mmss_to_seconds(clip_data["start_time"])
    end_sec = mmss_to_seconds(clip_data["end_time"])
    duration = end_sec - start_sec

    reel_dir = song_folder / f"reel_{clip_num}"
    reel_dir.mkdir(parents=True, exist_ok=True)

    # Generate one background per line
    frame_paths = []
    frame_durations = []

    for i, line in enumerate(lines):
        img_path = reel_dir / f"frame_{i:03d}.jpg"
        prompt = line.get("image_prompt", "abstract gradient")
        generate_background(prompt, style, img_path)

        # Overlay text on the image
        img = Image.open(str(img_path))
        
        # Try to load a Devanagari-supporting font for Hindi/Marathi text
        text = line.get("text", "")
        # Use a much larger font size for 1080x1920 video
        font_size = 80  
        font = None
        
        # Build paths to the custom fonts found in the repository
        repo_root = Path(__file__).resolve().parent.parent.parent
        custom_fonts = [
            str(repo_root / "fonts" / "PlaypenSansDeva.ttf"),
            str(Path(__file__).resolve().parent / "Samanya.ttf"),
            str(repo_root / "fonts" / "TiroDevanagariHindi-Regular.ttf"),
            str(repo_root / "fonts" / "TiroDevanagariHindi-Italic.ttf"),
            str(repo_root / "fonts" / "Caveat-Bold.ttf"),
            "C:/Windows/Fonts/Nirmala.ttf", 
            "C:/Windows/Fonts/mangal.ttf", 
            "C:/Windows/Fonts/segoeui.ttf"
        ]
        
        for font_name in custom_fonts:
            try:
                font = ImageFont.truetype(font_name, font_size)
                # Success!
                break
            except:
                continue
        
        if font is None:
            # Fallback to default, but try to scale it up if possible
            font = ImageFont.load_default()
            print(f"      ⚠️ Warning: Failed to load any custom fonts. Using default.")

        # Wrap text for vertical layout
        wrapped = textwrap.fill(text, width=18)
        
        # Calculate text position (centered in lower third for Reels style)
        draw = ImageDraw.Draw(img)
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align="center")
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        
        x = (1080 - tw) // 2
        y = 1400  # Position in lower part of the screen
        
        # Draw a strong drop shadow for readability since we removed the box
        for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2), (0, 3)]:
            draw.multiline_text((x + dx, y + dy), wrapped, fill=(0, 0, 0, 220), font=font, align="center")

        # Draw main text (white)
        draw.multiline_text((x, y), wrapped, fill=(255, 255, 255), font=font, align="center")

        img.save(str(img_path), quality=95)
        frame_paths.append(str(img_path))

        # Calculate duration: time from this line to next line
        if i < len(lines) - 1:
            this_t = mmss_to_seconds(line["time"])
            next_t = mmss_to_seconds(lines[i + 1]["time"])
            frame_durations.append(max(next_t - this_t, 1.0))
        else:
            this_t = mmss_to_seconds(line["time"])
            frame_durations.append(max(end_sec - this_t, 1.0))

    # Create FFmpeg concat file with absolute paths
    concat_path = reel_dir / "concat.txt"
    with open(str(concat_path), "w", encoding="utf-8") as f:
        for fp, dur in zip(frame_paths, frame_durations):
            abs_fp = str(Path(fp).resolve()).replace("\\", "/")
            f.write(f"file '{abs_fp}'\n")
            f.write(f"duration {dur:.2f}\n")
        # Repeat last frame (FFmpeg concat demuxer requirement)
        if frame_paths:
            last_abs = str(Path(frame_paths[-1]).resolve()).replace("\\", "/")
            f.write(f"file '{last_abs}'\n")

    # Trim audio
    audio_clip = reel_dir / "audio_clip.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(start_sec), "-t", str(duration),
        "-i", audio_path, "-acodec", "copy", str(audio_clip)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Render final video
    output_video = song_folder / f"reel_{clip_num}.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_path),
        "-i", str(audio_clip),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-pix_fmt", "yuv420p",
        str(output_video)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Also save the trimmed audio as standalone MP3
    reel_mp3 = song_folder / f"reel_{clip_num}.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(start_sec), "-t", str(duration),
        "-i", audio_path, "-acodec", "copy", str(reel_mp3)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print(f"  🎬 Reel {clip_num} video: {output_video.name}")
    return str(output_video)

# ── Save JSON + Suggestions ─────────────────────────────────────────────────

def save_suggestions(ai_data, song_folder, title):
    clean_title = re.sub(r'[\\/*?:"<>|]', '', title).strip()[:50].strip()

    # Save full JSON
    json_path = song_folder / "reel_data.json"
    with open(str(json_path), "w", encoding="utf-8") as f:
        json.dump(ai_data, f, indent=2, ensure_ascii=False)

    # Save human-readable suggestions
    txt_path = song_folder / "reel_suggestions.txt"
    with open(str(txt_path), "w", encoding="utf-8") as f:
        f.write(f"AI Reel Suggestions for: {title}\n")
        f.write(f"Image Style: {ai_data.get('image_style', 'N/A')}\n")
        f.write("=" * 40 + "\n\n")

        for clip in ai_data.get("clips", []):
            num = clip.get("clip_number", "?")
            start = clip.get("start_time", "?")
            end = clip.get("end_time", "?")
            reason = clip.get("reason", "")
            f.write(f"Reel {num}: [{start}] → [{end}]\n")
            f.write(f"  Reason: {reason}\n")
            for line in clip.get("lines", []):
                f.write(f"  [{line['time']}] {line['text']}\n")
                f.write(f"           🎨 {line.get('image_prompt', '')}\n")
            f.write("\n")

    print(f"📄 Saved: {json_path.name}, {txt_path.name}")

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", "-u", required=True, help="YouTube URL or Song Name")
    parser.add_argument("--output", "-o", default="downloads", help="Output directory")
    parser.add_argument("--skip-ai", action="store_true", help="Skip AI reel suggestions")
    parser.add_argument("--skip-video", action="store_true", help="Skip video rendering (only JSON + MP3)")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Resolve title
        import yt_dlp
        search_query = args.url
        if not (search_query.startswith("http") or search_query.startswith("www.")):
            search_query = f"ytsearch1:{search_query}"

        with yt_dlp.YoutubeDL({"quiet": True, "javascript_runtime": "node"}) as ydl:
            info = ydl.extract_info(search_query, download=False)
            if "entries" in info: info = info["entries"][0]
            title = info.get("title", "Unknown")

        # Create song folder (truncate to avoid Windows MAX_PATH limit)
        clean_title = re.sub(r'[\\/*?:"<>|]', '', title).strip()[:50].strip()
        song_folder = output_dir / clean_title
        song_folder.mkdir(parents=True, exist_ok=True)

        # Download
        audio_path, video_id, final_title = download_audio_and_get_id(args.url, str(song_folder))
        print(f"🎵 Audio downloaded: {Path(audio_path).name}")

        # Transcript
        transcript_text, txt_path = save_transcript(video_id, final_title, song_folder)

        # AI Reel Selection + Video
        if transcript_text and not args.skip_ai:
            ai_data = get_ai_reel_suggestions(transcript_text, final_title)
            if ai_data:
                save_suggestions(ai_data, song_folder, final_title)
                style = ai_data.get("image_style", "cinematic moody")

                if not args.skip_video:
                    for clip in ai_data.get("clips", []):
                        num = clip.get("clip_number", 1)
                        render_reel_video(clip, audio_path, style, song_folder, num)

        print(f"\n✨ Done! Files are in: {song_folder}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
