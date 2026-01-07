
import json
import random
import os
import skia
import uharfbuzz as hb
import math
import subprocess
import imageio_ffmpeg
import platform
import sys
import shutil
from TTS.api import TTS
import time
import requests
import urllib.parse

# Force utf-8 output for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Helper to get paths relative to repo root
def get_root_path(rel_path):
    return os.path.join(parent_dir, rel_path)

# Helper to get data paths
def get_data_path(filename):
    return os.path.join(parent_dir, "data", "DevotionalHindiQuotes", filename)

# Helper to get asset paths
def get_asset_path(filename):
    # Ensure directory exists
    path = os.path.join(parent_dir, "assets", "devotional_hindi")
    if not os.path.exists(path):
        os.makedirs(path)
    return os.path.join(path, filename)

# Helper to get output paths
def get_output_path(filename):
    return os.path.join(parent_dir, filename)

def get_data(json_file_path):
    """Reads data from the JSON file."""
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def render_hindi_text(canvas, text, font_path, font_size, max_width, start_y, color, align="center"):
    """
    Renders Hindi text with proper shaping using HarfBuzz and Skia.
    Supports multi-line wrapping and adds a black shadow for readability.
    """
    with open(font_path, "rb") as f:
        font_data = f.read()
    face = hb.Face(font_data)
    hb_font = hb.Font(face)
    hb_font.scale = (font_size * 64, font_size * 64)
    
    sk_typeface = skia.Typeface.MakeFromFile(font_path)
    sk_font = skia.Font(sk_typeface, font_size)
    
    # Shadow Paint (Black, slightly blurred or just offset)
    shadow_paint = skia.Paint(Color=skia.ColorBLACK, AntiAlias=True)
    shadow_paint.setStyle(skia.Paint.kStrokeAndFill_Style)
    shadow_paint.setStrokeWidth(1.0) # Thicker for shadow
    
    # Main Paint
    sk_paint = skia.Paint(Color=color, AntiAlias=True)
    # Make font slightly bolder
    sk_paint.setStyle(skia.Paint.kStrokeAndFill_Style)
    sk_paint.setStrokeWidth(0.6)
    
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
            if current_line_words:
                lines.append(' '.join(current_line_words))
                current_line_words = [word]
            else:
                lines.append(word)
                current_line_words = []
    if current_line_words:
        lines.append(' '.join(current_line_words))
    
    curr_y = start_y
    line_height = font_size * 1.5
    
    total_h = len(lines) * line_height
    
    rendered_line_data = []
    
    for line in lines:
        buf = hb.Buffer()
        buf.add_str(line)
        buf.guess_segment_properties()
        hb.shape(hb_font, buf, {})
        
        glyphs = [info.codepoint for info in buf.glyph_infos]
        positions = []
        shadow_positions = []
        
        line_width = sum(p.x_advance for p in buf.glyph_positions) / 64.0
        
        if align == "center":
            base_x = (canvas.getBaseLayerSize().width() - line_width) / 2
        else:
            base_x = (canvas.getBaseLayerSize().width() - max_width) / 2
            
        curr_x = base_x
        for p in buf.glyph_positions:
            off_x = p.x_offset / 64.0
            off_y = p.y_offset / 64.0
            
            # Shadow offset (2px right, 2px down)
            shadow_positions.append(skia.Point(curr_x + off_x + 2, curr_y - off_y + 2))
            positions.append(skia.Point(curr_x + off_x, curr_y - off_y))
            curr_x += p.x_advance / 64.0
            
        builder_shadow = skia.TextBlobBuilder()
        builder_shadow.allocRunPos(sk_font, glyphs, shadow_positions)
        blob_shadow = builder_shadow.make()
        
        builder_main = skia.TextBlobBuilder()
        builder_main.allocRunPos(sk_font, glyphs, positions)
        blob_main = builder_main.make()
        
        rendered_line_data.append((blob_shadow, blob_main, curr_y))
        
        curr_y += line_height
        
    for blob_shadow, blob_main, y in rendered_line_data:
        canvas.drawTextBlob(blob_shadow, 0, 0, shadow_paint)
        canvas.drawTextBlob(blob_main, 0, 0, sk_paint)
        
    return total_h

def create_quote_overlay(quote_data, output_image_path):
    """Creates an image with the quote text using Skia."""
    width, height = 720, 1280
    surface = skia.Surface(width, height)
    canvas = surface.getCanvas()
    
    # Transparent background
    canvas.clear(skia.ColorTRANSPARENT)
    
    font_path = get_root_path(os.path.join("fonts", "TiroDevanagariHindi-Regular.ttf"))
    if not os.path.exists(font_path):
        font_path = "C:\\Windows\\Fonts\\Nirmala.ttc"
        
    hook_text = quote_data.get("hook_text", "")
    quote_text = quote_data.get("quote_hindi_sansrikt", "")
    
    # Handle both meaning key variations robustly
    meaning_text = quote_data.get("meaning_meaning_simple_hindi", quote_data.get("meaning_simple_hindi", ""))
    
    # 1. Hook Text (Top)
    hook_y = 150
    render_hindi_text(canvas, hook_text, font_path, 42, width - 100, hook_y, skia.ColorWHITE)
    
    # 2. Main Quote (Middle)
    quote_font_size = 55
    lines_estimate = (len(quote_text) / 20) + 1
    quote_total_h_est = lines_estimate * quote_font_size * 1.5
    
    quote_start_y = (height - quote_total_h_est) / 2 - 50 
    
    actual_quote_h = render_hindi_text(canvas, quote_text, font_path, quote_font_size, width - 120, quote_start_y, skia.Color(255, 215, 0)) # Gold Color
    
    # 3. Meaning (Below Quote)
    meaning_font_size = 38
    meaning_y = quote_start_y + actual_quote_h + 80
    render_hindi_text(canvas, meaning_text, font_path, meaning_font_size, width - 150, meaning_y, skia.ColorWHITE)
    
    image = surface.makeImageSnapshot()
    image.save(output_image_path, skia.kPNG)
    return output_image_path

# Initialize TTS globally to avoid reloading for every quote
print("Loading Coqui TTS XTTS v2 model... (Might take a moment)")
tts_engine = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)

def clean_text_for_tts(text):
    """Sanitizes text for TTS, removing characters that trigger expansion errors (like decimals in Hindi)."""
    import re
    if not text:
        return ""
    # Remove verse refs like "|| 1.2" or "|| 1.1-1.3"
    text = re.sub(r"\|\|\s*[\d\.\-]+", "", text)
    # Remove the standard Hindi punctuation pipes
    text = text.replace("|", "").replace("॥", "").replace("।", " ")
    # If any decimals remain (like 1.1), replace dot with space
    text = re.sub(r"(\d)\.(\d)", r"\1 \2", text)
    # Remove special chars that might cause issues
    text = re.sub(r"[^\w\s\u0900-\u097F]", " ", text)
    return " ".join(text.split())

def download_ai_background(prompt, output_path):
    """Downloads a fresh AI-generated background from Pollinations.ai with retries."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Use a random seed for each attempt to bypass 530/cache issues
            seed = random.randint(1, 100000)
            encoded_prompt = urllib.parse.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=720&height=1280&nologo=true&enhance=true&seed={seed}"
            
            print(f"Acquiring fresh AI background (Attempt {attempt+1}/{max_retries})...")
            response = requests.get(url, timeout=40)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                print(f"Fresh AI background saved to: {output_path}")
                return output_path
            else:
                print(f"Attempt {attempt+1} failed with status {response.status_code}. Retrying...")
                time.sleep(2) # Small backoff
        except Exception as e:
            print(f"Error during attempt {attempt+1}: {e}")
            time.sleep(2)
            
    print("[ERROR] Failed to acquire AI background after all retries.")
    return None

def get_audio_duration(file_path):
    """Returns the duration of an audio file in seconds using ffmpeg."""
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        # ffmpeg outputs info to stderr
        cmd = [ffmpeg_exe, "-i", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        import re
        match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
        if match:
            hours, minutes, seconds = match.groups()
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        return 20.0
    except:
        return 20.0

def generate_meditative_voiceover(quote_data, output_path):
    """Generates a sequential meditative Hindi voiceover with hook, quote, and meaning."""
    hook = quote_data.get('hook_text', '').strip()
    quote = quote_data.get('quote_hindi_sansrikt', '').strip()
    
    # Handle double "meaning" key typo from user edit, fallback to standard key
    meaning = quote_data.get('meaning_meaning_simple_hindi', quote_data.get('meaning_simple_hindi', '')).strip()
    
    segments = []
    temp_files = []
    
    # helper to generate segment
    def add_segment(text, label):
        if text:
            clean_text = clean_text_for_tts(text)
            if not clean_text:
                return
            path = get_output_path(f"temp_{label}.wav")
            print(f"Generating segment for {label} (Cleaned: {clean_text[:40]}...)...")
            tts_engine.tts_to_file(
                text=clean_text,
                speaker="Kumar Dahl",
                language="hi",
                file_path=path
            )
            segments.append(path)
            temp_files.append(path)

    # 1. Quote
    add_segment(quote, "quote")
    
    # 2. Meaning
    add_segment(meaning, "meaning")
    
    if not segments:
        print("Error: No text found for voiceover segments.")
        return None

    # Generate silence segment (3 seconds) - Inter-segment pause
    pause_path = get_output_path("temp_pause.wav")
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([
        ffmpeg_exe, "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", 
        "-t", "3", "-ar", "24000", pause_path
    ], capture_output=True)
    temp_files.append(pause_path)

    # Generate silence segment (2 seconds) - Start Delay
    start_delay_path = get_output_path("temp_start_delay.wav")
    subprocess.run([
        ffmpeg_exe, "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", 
        "-t", "2", "-ar", "24000", start_delay_path
    ], capture_output=True)
    temp_files.append(start_delay_path)

    # Concatenate with pauses
    # Flow: [2s Delay] -> Quote -> [3s Pause] -> Meaning
    concat_list = []
    
    # Always add start delay
    concat_list.append(start_delay_path)
    
    if len(segments) > 0:
        concat_list.append(segments[0]) # Quote
    if len(segments) > 1:
        concat_list.append(pause_path)
        concat_list.append(segments[1]) # Meaning

    # Create concat list for ffmpeg
    list_file_path = get_output_path("concat_list.txt")
    with open(list_file_path, "w", encoding="utf-8") as f:
        for p in concat_list:
            abs_p = os.path.abspath(p).replace("\\", "/")
            f.write(f"file '{abs_p}'\n")
    temp_files.append(list_file_path)

    print("Concatenating voiceover segments...")
    concat_result = subprocess.run([
        ffmpeg_exe, "-y", "-f", "concat", "-safe", "0", "-i", list_file_path, 
        "-c:a", "libmp3lame", "-q:a", "2", output_path
    ], capture_output=True, text=True)
    
    if concat_result.returncode != 0:
        print("Error during audio concatenation:")
        print(concat_result.stderr)
        return None

    # Cleanup segments
    for f in temp_files:
        if os.path.exists(f):
            os.remove(f)

    return output_path

def create_video(quote_data, bg_img_path, overlay_img_path, output_video_path, duration=20):
    """Combines background and overlay into a video with generated voiceover."""
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    
    # Voiceover path (generated previously in the flow or here)
    voiceover_path = get_output_path("temp_voiceover.mp3")
    
    # PASS 1: Generate Silent Video
    temp_silent_video = get_output_path("temp_silent.mp4")
    
    inputs_v = [
        "-loop", "1", "-t", str(duration), "-i", bg_img_path,
        "-loop", "1", "-t", str(duration), "-i", overlay_img_path,
        "-f", "lavfi", "-t", str(duration), "-i", "color=c=black:s=720x1280"
    ]
    
    filter_complex = (
        "[0:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,format=yuva420p,colorchannelmixer=aa=0.5[img_low_op];"
        "[2:v][img_low_op]overlay=format=auto[bg_layered];"
        "[bg_layered][1:v]overlay=format=auto[v_final]"
    )
    
    # Using even more aggressive low-memory settings for Pass 1
    cmd_v = [ffmpeg_exe, "-y", "-threads", "1"] + inputs_v
    cmd_v.extend(["-filter_complex", filter_complex])
    cmd_v.extend(["-map", "[v_final]"])
    cmd_v.extend([
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "28", # Lower quality = less memory
        "-pix_fmt", "yuv420p",
        temp_silent_video
    ])
    
    print(f"Pass 1: Creating silent video...")
    subprocess.run(cmd_v, check=True, capture_output=True, text=True)
    
    # PASS 2: Add Voiceover + Background Music
    print(f"Pass 2: Adding voiceover and background music (50%)...")
    bg_music_path = get_root_path(os.path.join("assets", "epicstories", "background-music.mp3"))
    
    # Check if music exists, fallback to only voiceover if not
    if os.path.exists(bg_music_path):
        cmd_a = [
            ffmpeg_exe, "-y",
            "-i", temp_silent_video,
            "-i", voiceover_path,
            "-i", bg_music_path,
            "-filter_complex", "[1:a]volume=1.0[v]; [2:a]volume=0.25[bg]; [v][bg]amix=inputs=2:duration=longest[a]",
            "-map", "0:v",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            output_video_path
        ]
    else:
        print("Warning: Background music NOT found. Generating with voiceover only.")
        cmd_a = [
            ffmpeg_exe, "-y",
            "-i", temp_silent_video,
            "-i", voiceover_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v",
            "-map", "1:a",
            "-shortest",
            output_video_path
        ]
    
    result = subprocess.run(cmd_a, capture_output=True, text=True)
    
    # Cleanup temp video
    if os.path.exists(temp_silent_video):
        os.remove(temp_silent_video)

    if result.returncode != 0:
        print(f"FFMPEG Pass 2 failed with code {result.returncode}")
        print(result.stderr)
        raise subprocess.CalledProcessError(result.returncode, cmd_a, result.stdout, result.stderr)

def create_quote_videos(limit=None):
    """Processes quotes and creates videos."""
    json_path = get_data_path("data.json")
    if not os.path.exists(json_path):
        print(f"Data file not found at {json_path}")
        return
        
    all_data = get_data(json_path)
    if not all_data:
        print("No data found in JSON.")
        return
    
    if len(all_data) < 1:
        print("Error: No data found in JSON.")
        return

    # Reverted to processing the FIRST one (Index 0)
    quote = all_data[0]
    print(f"\n--- Processing First Quote (Index 0): {quote.get('hook_text', 'No Hook')} (Verse {quote.get('verse_number', 'N/A')}) ---")
    
    # 5 Second Wait as requested
    print("Waiting 5 seconds before starting...")
    time.sleep(5)
    
    # --- AUTOMATED AI BACKGROUND ACQUISITION ---
    bg_path = get_asset_path("current_bg.png")
    prompt = quote.get('background_theme_detailed_prompt', 'A serene meditative background, ancient India, spiritual atmosphere, 4k.')
    
    if not download_ai_background(prompt, bg_path):
        print("\n[ERROR] Could not acquire a fresh AI background.")
        return

    overlay_path = get_output_path("temp_overlay.png")
    create_quote_overlay(quote, overlay_path)
    
    output_video = get_output_path("devotional_hindi_quote.mp4")
    voiceover_path = get_output_path("temp_voiceover.mp3")
    
    try:
        # Generate meditative voiceover (Full narration)
        print(f"Generating expanded meditative voiceover...")
        generate_meditative_voiceover(quote, voiceover_path)
        
        # Smart Sync logic: 10 second buffer as requested
        audio_duration = get_audio_duration(voiceover_path)
        print(f"Total audio duration: {audio_duration:.2f}s")
        
        # Min 20s, but always add 10s buffer to audio
        video_duration = max(20, int(audio_duration + 10))
        print(f"Setting smart video duration (Audio + 10s): {video_duration}s")
        
        create_video(quote, bg_path, overlay_path, output_video, duration=video_duration)
        print(f"Video generated successfully: {output_video}")
        
        # SUCCESS! Now remove the processed quote (Index 0) from JSON
        all_data.pop(0)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print(f"Successfully removed processed quote (Index 0) from {os.path.basename(json_path)}")
        
        # ALSO remove the background image as per user request
        if os.path.exists(bg_path):
            os.remove(bg_path)
            print(f"Deleted background image {os.path.basename(bg_path)} for a fresh start next time.")
        
    except Exception as e:
        import traceback
        print(f"Error during video generation: {e}")
        traceback.print_exc()
    finally:
        # Cleanup
        if os.path.exists(overlay_path):
            os.remove(overlay_path)

def main():
    # In this flow, --limit is less relevant but we'll call create_quote_videos
    create_quote_videos()

if __name__ == "__main__":
    main()
