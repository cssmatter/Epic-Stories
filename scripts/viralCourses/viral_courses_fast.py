import json
import os
import sys
import time
import math
import skia
import numpy as np
import subprocess
import argparse
import gc
from gtts import gTTS
import imageio_ffmpeg

# Force utf-8 output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

print("Starting FAST Viral Course Video Generator...", flush=True)

# --- CONSTANTS ---
WIDTH = 1920
HEIGHT = 1080
FPS = 24
BG_COLOR = skia.ColorWHITE
TEXT_COLOR = skia.ColorBLACK
GREEN_HIGHLIGHT = skia.Color(144, 238, 144)
FONT_NAME = "Arial"

# Get executables
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
# Try to guess ffprobe path (usually next to ffmpeg)
FFPROBE_EXE = FFMPEG_EXE.replace("ffmpeg.exe", "ffprobe.exe") if "ffmpeg.exe" in FFMPEG_EXE else "ffprobe"

# --- PATHS ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_FILE = os.path.join(REPO_ROOT, "data", "viralCourses", "data.json")
OUTPUT_DIR = os.path.join(REPO_ROOT, "output", "viralCourses")
TEMP_DIR = os.path.join(OUTPUT_DIR, "temp_fast")
ASSETS_DIR = os.path.join(REPO_ROOT, "assets", "fonts")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# --- SKIA CACHING ---
_TYPEFACE_CACHE = {}
_FONT_CACHE = {}
_SHARED_SURFACE = None
_SHARED_BUFFER = None
_BG_IMAGE_CACHE = None

def get_font(size=40):
    global _TYPEFACE_CACHE, _FONT_CACHE
    font_key = f"Inter-Bold_{size}"
    if font_key in _FONT_CACHE:
        return _FONT_CACHE[font_key]
        
    if "Inter-Bold" not in _TYPEFACE_CACHE:
        font_path = os.path.join(ASSETS_DIR, "Inter-Bold.ttf")
        if os.path.exists(font_path):
             _TYPEFACE_CACHE["Inter-Bold"] = skia.Typeface.MakeFromFile(font_path)
        else:
             _TYPEFACE_CACHE["Inter-Bold"] = skia.Typeface.MakeFromName("Arial", skia.FontStyle.Bold())
             
    font = skia.Font(_TYPEFACE_CACHE["Inter-Bold"], size)
    _FONT_CACHE[font_key] = font
    return font

def get_shared_surface():
    global _SHARED_SURFACE, _SHARED_BUFFER
    if _SHARED_SURFACE is None:
        _SHARED_SURFACE = skia.Surface(WIDTH, HEIGHT)
        # Pre-allocate a buffer for pixels (1920x1080x4)
        import numpy as np
        _SHARED_BUFFER = np.zeros((HEIGHT, WIDTH, 4), dtype=np.uint8)
    return _SHARED_SURFACE

def get_shared_buffer():
    global _SHARED_BUFFER
    if _SHARED_BUFFER is None:
        get_shared_surface()
    return _SHARED_BUFFER

def get_bg_image():
    global _BG_IMAGE_CACHE
    if _BG_IMAGE_CACHE: return _BG_IMAGE_CACHE
    
    bg_path = os.path.join(ASSETS_DIR, "..", "viralCourses", "bg.jpg")
    if os.path.exists(bg_path):
        try:
            # Use skia.Image.open() to load the image
            image = skia.Image.open(bg_path)
            if image:
                _BG_IMAGE_CACHE = image
                return image
        except Exception as e:
            print(f"Error loading BG Image: {e}")
    return None

def wrap_text(text, font, max_width):
    if not text: return []
    words = text.split(' ')
    lines = []
    current_line = []
    for word in words:
        test_line = ' '.join(current_line + [word])
        width = font.measureText(test_line)
        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []
    if current_line:
        lines.append(' '.join(current_line))
    return lines

def render_frame_bytes(
    main_text, 
    progress=1.0, 
    subtext_list=None, 
    visible_subtext_count=None, 
    highlight_option=None, 
    title="",
    timer_val=None,
    footer_text=""
):
    """
    Renders a frame using Skia and returns raw RGBA bytes.
    """
    surface = get_shared_surface()
    canvas = surface.getCanvas()
    
    # Draw Background
    bg_img = get_bg_image()
    if bg_img:
        # Scale to fill
        rect = skia.Rect.MakeWH(WIDTH, HEIGHT)
        canvas.drawImageRect(bg_img, rect)
    else:
        canvas.clear(BG_COLOR)
    
    margin_x = 100
    margin_y = 100
    max_width = WIDTH - (2 * margin_x)
    
    # 1. Title
    if title:
        title_font = get_font(50)
        title_paint = skia.Paint(Color=skia.ColorBLACK, AntiAlias=True)
        canvas.drawSimpleText(title, margin_x, margin_y, title_font, title_paint)
        margin_y += 100

    # 2. Main Text
    main_font = get_font(60)
    paint = skia.Paint(Color=TEXT_COLOR, AntiAlias=True)
    
    if main_text:
        visible_char_count = int(len(main_text) * progress)
        visible_text = main_text[:visible_char_count]
        lines = wrap_text(visible_text, main_font, max_width)
        for line in lines:
            canvas.drawSimpleText(line, margin_x, margin_y, main_font, paint)
            margin_y += 80
        margin_y += 40 

    # 3. Subtext (Options)
    if subtext_list:
        option_font = get_font(50)
        count_to_show = len(subtext_list)
        if visible_subtext_count is not None:
            count_to_show = visible_subtext_count
            
        for i in range(count_to_show):
            opt = subtext_list[i]
            opt_bg_paint = None
            if highlight_option is not None:
                prefix = opt.split(':')[0].strip()
                if str(highlight_option) == prefix:
                     opt_bg_paint = skia.Paint(Color=GREEN_HIGHLIGHT, AntiAlias=True)
            
            if opt_bg_paint:
                rect = skia.Rect.MakeXYWH(margin_x - 20, margin_y - 50, max_width + 40, 70)
                canvas.drawRoundRect(rect, 15, 15, opt_bg_paint)

            opt_lines = wrap_text(opt, option_font, max_width)
            for line in opt_lines:
                canvas.drawSimpleText(line, margin_x, margin_y, option_font, paint)
                margin_y += 70
            margin_y += 20

    # 4. Timer
    if timer_val is not None:
        timer_font = get_font(150)
        timer_text = str(timer_val)
        t_width = timer_font.measureText(timer_text)
        
        center_x = WIDTH - 150
        center_y = HEIGHT - 200
        radius = 120
        
        circle_paint = skia.Paint(Color=skia.ColorRED, AntiAlias=True)
        circle_paint.setStyle(skia.Paint.kStroke_Style)
        circle_paint.setStrokeWidth(10)
        canvas.drawCircle(center_x, center_y, radius, circle_paint)
        
        text_paint = skia.Paint(Color=skia.ColorRED, AntiAlias=True)
        canvas.drawSimpleText(timer_text, center_x - (t_width/2), center_y + 50, timer_font, text_paint)

    # 5. Footer
    if footer_text:
        f_font = get_font(30)
        f_paint = skia.Paint(Color=skia.ColorGRAY, AntiAlias=True)
        f_width = f_font.measureText(footer_text)
        canvas.drawSimpleText(footer_text, (WIDTH - f_width)/2, HEIGHT - 50, f_font, f_paint)

    info = skia.ImageInfo.Make(WIDTH, HEIGHT, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType)
    buffer = get_shared_buffer()
    surface.readPixels(info, buffer)
    return buffer

def generate_thumbnail(mcq, meta, intro):
    """Generates a thumbnail image and saves it to disk."""
    print("Generating Thumbnail...", flush=True)
    thumb_path = os.path.join(OUTPUT_DIR, "thumbnail.png")
    
    # Render a frame for thumbnail
    # We can use the Title + Hook
    # Or just the main Title
    
    surface = get_shared_surface()
    canvas = surface.getCanvas()
    
    # 1. Draw BG
    bg_img = get_bg_image()
    if bg_img:
        rect = skia.Rect.MakeWH(WIDTH, HEIGHT)
        canvas.drawImageRect(bg_img, rect)
    else:
        canvas.clear(BG_COLOR)
        
    # 2. Draw Big Title
    title_text = meta.get("youtubetitle", "Viral Course")
    
    # Split title if too long
    t_font = get_font(100)
    t_paint = skia.Paint(Color=skia.ColorBLACK, AntiAlias=True)
    
    margin_x = 100
    margin_y = 300
    max_w = WIDTH - 200
    
    lines = wrap_text(title_text, t_font, max_w)
    
    # Center vertically by calculating total height
    total_height = len(lines) * 120
    start_y = (HEIGHT - total_height) / 2 + 100
    
    for line in lines:
        # Center horizontally
        w = t_font.measureText(line)
        x = (WIDTH - w) / 2
        canvas.drawSimpleText(line, x, start_y, t_font, t_paint)
        start_y += 120

    # Save
    image = surface.makeImageSnapshot()
    image.save(thumb_path, skia.kPNG)
    print(f"Thumbnail saved to: {thumb_path}")


# --- AUDIO HELPERS ---
def get_audio_duration(file_path):
    """
    Get exact audio duration using ffprobe.
    """
    cmd = [
        FFPROBE_EXE, 
        "-v", "error", 
        "-show_entries", "format=duration", 
        "-of", "default=noprint_wrappers=1:nokey=1", 
        file_path
    ]
    
    try:
        if os.path.exists(FFPROBE_EXE) or "ffprobe" in FFPROBE_EXE:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return float(result.stdout.strip())
    except:
        pass
    
    # Fallback to ffmpeg -i
    try:
        cmd_ffmpeg = [FFMPEG_EXE, "-i", file_path]
        result = subprocess.run(cmd_ffmpeg, capture_output=True, text=True)
        # Parse "Duration: 00:00:05.12,"
        import re
        match = re.search(r"Duration:\s+(\d+):(\d+):(\d+\.\d+)", result.stderr)
        if match:
            h, m, s = match.groups()
            return int(h) * 3600 + int(m) * 60 + float(s)
    except Exception as e:
        print(f"  Duration Error: {e}")
        
    return 0.0

from gtts import gTTS # Added this import as it's used in the new code

# --- TTS HELPERS ---
def generate_tts_cached_offline(text, filename_seed):
    """
    Generate TTS using gTTS, convert to WAV to ensure no padding/drift.
    """
    if not text or not text.strip(): return None, 0.0

    clean_seed = "".join(x for x in filename_seed if x.isalnum())[:20]
    fname_wav = f"{clean_seed}_{hash(text)}.wav"
    path_wav = os.path.join(TEMP_DIR, fname_wav)
    
    if os.path.exists(path_wav):
        return path_wav, get_audio_duration(path_wav)

    # Temporary mp3 path
    path_mp3 = os.path.join(TEMP_DIR, f"temp_{hash(text)}.mp3")
    
    try:
        tts = gTTS(text=text, lang='en')
        tts.save(path_mp3)
        
        # Convert to standard WAV 24kHz mono
        subprocess.run([
            FFMPEG_EXE, "-y", "-i", path_mp3, 
            "-ar", "24000", "-ac", "1", path_wav
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if os.path.exists(path_mp3):
            os.remove(path_mp3)

        if os.path.exists(path_wav):
             return path_wav, get_audio_duration(path_wav)
    except Exception as e:
        print(f"  gTTS Error: {e}")
        
    return None, 0.0

def create_silence(duration_sec):
    if duration_sec <= 0: return None
    
    fname = f"silence_{duration_sec}s.wav"
    path = os.path.join(TEMP_DIR, fname)
    if os.path.exists(path):
        return path
    
    cmd = [
        FFMPEG_EXE, "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", 
        "-t", str(duration_sec), "-c:a", "pcm_s16le", path
    ]
    subprocess.run(cmd, capture_output=True, text=True)
    return path



    # --- PRE-COMPUTE AUDIO (SEQUENTIAL) ---
    print("Pre-generating TTS Audio (Offline/Sequential)...", flush=True)
    
    tts_tasks = []
    tts_tasks.append(intro["hook"])
    tts_tasks.append(intro["summary"])
    tts_tasks.append(intro["cta_intro"])
    
    for mcq in mcqs:
        tts_tasks.append(mcq["question"])
        opts_audio = ". ".join([f"Option {k}, {v}" for k, v in mcq["options"].items()])
        tts_tasks.append(opts_audio)
        tts_tasks.append(mcq["detailedexplanation"])
        
    tts_tasks.append(outro["closing"])
    tts_tasks.append(outro["cta_final"])
    
    # Deduplicate
    tts_tasks = list(set([t for t in tts_tasks if t]))
    
    # Run sequentially (pyttsx3 is fast enough)
    count = 0
    for text in tts_tasks:
        generate_tts_cached_offline(text, str(hash(text)))
        count += 1
        if count % 10 == 0: print(f"  Generated {count}/{len(tts_tasks)}", flush=True)
            
    print("TTS Generation Complete.", flush=True)

def create_silence(duration_sec):
    """Create a silence audio file using ffmpeg."""
    fname = f"silence_{duration_sec}s.wav"
    path = os.path.join(TEMP_DIR, fname)
    if os.path.exists(path):
        return path
    
    cmd = [
        FFMPEG_EXE, "-y", "-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono", 
        "-t", str(duration_sec), "-c:a", "pcm_s16le", path
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error creating silence: {res.stderr}", flush=True)
    return path

# --- PIPELINE ---
def main():
    start_time = time.time()
    
    # 1. Load Data
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Limit number of MCQs to process")
    args = parser.parse_args()

    if not os.path.exists(DATA_FILE):
        print(f"Data file not found: {DATA_FILE}")
        return

    # Cleanup any legacy .mp3 files as requested
    print("Cleaning up legacy .mp3 files...", flush=True)
    for f in os.listdir(TEMP_DIR):
        if f.endswith(".mp3"):
            try:
                os.remove(os.path.join(TEMP_DIR, f))
            except:
                pass

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    assets = data[0]["video_assets"]
    intro = assets["intro_script"]
    meta = assets["youtube_metadata"]
    mcqs = data[0]["mcq_data"]
    print(f"Loaded {len(mcqs)} MCQs from the first object.")

    if args.limit:
        print(f"Limiting to first {args.limit} MCQs for testing.")
        mcqs = mcqs[:args.limit]
    
    # Use fallback if missing
    outro = data[0].get("outro_script", {
        "closing": "Thanks for watching!", 
        "cta_final": "Subscribe for more!", 
        "next_steps": "Check description."
    })

    footer_str = intro.get("checkfullexamlinkindescription", "Check full exam link in description")

    footer_str = intro.get("checkfullexamlinkindescription", "Check full exam link in description")
    output_video_path = os.path.join(TEMP_DIR, "raw_video.mp4")

    # -c:v libx264 -preset medium -crf 28 -pix_fmt yuv420p
    ffmpeg_cmd = [
        FFMPEG_EXE, "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "rgba",
        "-r", str(FPS),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "28",
        "-pix_fmt", "yuv420p",
        output_video_path
    ]
    
    print("Starting Clip-Based Render...", flush=True)
    
    # 3. Processing Helper
    
    # Stateless Processor
    def process_segment(
        pipe,
        local_audio_list,
        frames_tracker,
        text_content, 
        voice_text, 
        mode="static", 
        duration_override=None,
        subtext_list=None,
        title="",
        highlight_option=None,
        timer_seconds=None
    ):
        # A. Audio
        audio_path = None
        dur = 0.0
        if voice_text:
            audio_path, dur = generate_tts_cached_offline(voice_text, str(hash(voice_text)))
        elif duration_override:
            # Create silence if no voice but duration needed
            audio_path = create_silence(duration_override)
            # Get ACTUAL duration of the silence file to avoid drift
            dur = get_audio_duration(audio_path) if audio_path and os.path.exists(audio_path) else duration_override
            
        # Add to audio list
        segment_added_dur = 0.0
        
        if audio_path:
            # 1. Main audio
            real_main_dur = get_audio_duration(audio_path)
            local_audio_list.append(audio_path)
            segment_added_dur += real_main_dur
            
            # 2. Silence gap if needed
            # We want total time to match final_dur (theoretical target)
            # But we must track what we ACTUALLY add.
            current_total_theoretical = max(dur, duration_override if duration_override else 0)
            
            # If the theoretically desired duration is longer than what we have, add silence
            if current_total_theoretical > real_main_dur:
                silence_gap = current_total_theoretical - real_main_dur
                if silence_gap > 0.1:
                    s_path = create_silence(silence_gap)
                    real_s_dur = get_audio_duration(s_path)
                    local_audio_list.append(s_path)
                    segment_added_dur += real_s_dur

        # B. Video Rendering
        # frames_tracker is [current_total_frames]
        
        # --- QUANTIZED SYNC FIX ---
        # Instead of accumulating exact audio time and hoping it aligns with frames,
        # we FORCE the audio segment to be exactly N frames long.
        
        # 1. Calculate how many frames this segment *needs* to be
        if segment_added_dur > 0:
            target_dur = segment_added_dur
        else:
            target_dur = duration_override if duration_override else 0.0
            
        # 2. Calculate integer frames (ceil to ensuring covering audio)
        num_frames = math.ceil(target_dur * FPS)
        
        # 3. Calculate the aligned duration required for these frames
        aligned_dur = num_frames / FPS
        
        # 4. Calculate missing padding
        padding_needed = aligned_dur - target_dur
        
        # 5. Add micro-silence if needed
        # (Only if we have actual audio to pad, or if we are purely duration based)
        if padding_needed > 0.001:
             # Create tiny silence
             pad_path = create_silence(padding_needed)
             if pad_path:
                 local_audio_list.append(pad_path)
                 target_dur += padding_needed
                 
        # 6. Update Total Time (it is now exactly aligned)
        # We don't track total_audio_time globally anymore per segment in clip-mode
        pass 
        
        # If no audio was added (e.g. error), fall back to theoretical
        if num_frames <= 0 and duration_override:
              num_frames = int(duration_override * FPS)
              
        # Log sync status
        try:
            with open(os.path.join(OUTPUT_DIR, "sync_log.txt"), "a") as log:
                log.write(f"Segment: {title} | Mode: {mode}\n")
                log.write(f"  Target Frames: {num_frames} \n")
        except: pass

        # Helper to write frame safely with RETRY
        def write_frame_safe(p, data):
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    p.stdin.write(data)
                    frames_tracker[0] += 1
                    return True
                except (BrokenPipeError, OSError) as e:
                    if attempt < max_retries - 1:
                        time.sleep(0.01) # Short wait before retry
                    else:
                        print(f"  Frame Write Failed: {e}", flush=True)
                        return False
            return False

        # Static Mode Optimization
        if mode == "static":
            # Render ONCE
            frame_bytes = render_frame_bytes(
                text_content, 
                progress=1.0, 
                subtext_list=subtext_list, 
                visible_subtext_count=len(subtext_list) if subtext_list else 0,
                highlight_option=highlight_option,
                title=title,
                footer_text=footer_str
            )
            for _ in range(num_frames):
                if not write_frame_safe(pipe, frame_bytes): break

        elif mode == "typing_main":
            # Render Dynamic
            for f_idx in range(num_frames):
                # Use absolute time since start of THIS segment to determine progress
                t = f_idx / FPS
                progress = min(1.0, t / (dur * 0.95)) if dur > 0 else 1.0
                frame_bytes = render_frame_bytes(
                    text_content, 
                    progress=progress, 
                    subtext_list=subtext_list,
                    visible_subtext_count=len(subtext_list) if subtext_list else 0,
                    title=title,
                    footer_text=footer_str
                )
                if not write_frame_safe(pipe, frame_bytes): break

        elif mode == "typing_options":
             for f_idx in range(num_frames):
                t = f_idx / FPS
                # Calc visible items
                visible_count = len(subtext_list) if subtext_list else 0
                if subtext_list and dur > 0:
                    item_dur = dur / len(subtext_list)
                    visible_count = min(len(subtext_list), int(t / item_dur) + 1)
                
                frame_bytes = render_frame_bytes(
                    text_content, 
                    progress=1.0, 
                    subtext_list=subtext_list,
                    visible_subtext_count=visible_count,
                    title=title,
                    footer_text=footer_str
                )
                if not write_frame_safe(pipe, frame_bytes): break
        
        elif mode == "timer":
             last_timer_val = -1
             for f_idx in range(num_frames):
                t = f_idx / FPS
                remaining = math.ceil(timer_seconds - t) if timer_seconds else 0
                remaining = max(1, remaining)
                
                # Only re-render if value changed
                if remaining != last_timer_val:
                    frame_bytes = render_frame_bytes(
                        text_content, 
                        progress=1.0, 
                        subtext_list=subtext_list,
                        visible_subtext_count=len(subtext_list) if subtext_list else 0,
                        title=title,
                        timer_val=remaining,
                        footer_text=footer_str
                    )
                    last_timer_val = remaining
                    
                if not write_frame_safe(pipe, frame_bytes): break

        # Flush and GC
        pipe.stdin.flush()
        gc.collect()

    # --- PRE-COMPUTE AUDIO (SEQUENTIAL) ---
    print("Pre-generating TTS Audio (Offline/Sequential)...", flush=True)
    
    tts_tasks = []
    tts_tasks.append(intro["hook"])
    tts_tasks.append(intro["summary"])
    tts_tasks.append(intro["cta_intro"])
    
    for mcq in mcqs:
        tts_tasks.append(mcq["question"])
        opts_audio = ". ".join([f"Option {k}, {v}" for k, v in mcq["options"].items()])
        tts_tasks.append(opts_audio)
        tts_tasks.append(mcq["detailedexplanation"])
        
    tts_tasks.append(outro["closing"])
    tts_tasks.append(outro["cta_final"])
    
    # Deduplicate
    tts_tasks = list(set([t for t in tts_tasks if t]))
    
    # Run sequentially (pyttsx3 is fast enough)
    count = 0
    for text in tts_tasks:
        generate_tts_cached_offline(text, str(hash(text)))
        count += 1
        if count % 10 == 0: print(f"  Generated {count}/{len(tts_tasks)}", flush=True)
            
    print("TTS Generation Complete.", flush=True)

    # --- THUMBNAIL GENERATION ---
    generate_thumbnail(mcqs[0] if mcqs else None, meta, intro)

    # --- DEFINING THE SEQUENCE ---
    # --- SCENE DEFINITION ---
    # We will generate independent VIDEO CLIPS for:
    # 1. Intro
    # 2. Each MCQ (independent clip)
    # 3. Outro
    # Then concat them all. This GUARANTEES sync resetting.

    scene_clips = []

    def render_scene(scene_name, render_func):
        """Helper to render a self-contained video clip"""
        print(f"Rendering Clip: {scene_name} ...", flush=True)
        
        vid_path = os.path.join(TEMP_DIR, f"{scene_name}.mp4")
        if os.path.exists(vid_path): os.remove(vid_path)
        
        # Temp raw video
        raw_vid = os.path.join(TEMP_DIR, f"{scene_name}_raw.mp4") # container to hold raw h264 stream
        
        # Audio accumulator for this scene
        scene_audio_list = []
        
        # Start FFmpeg pipe for this scene
        # Note: We output raw stream to pipe, but we need to mux it with audio later.
        # It's easier if we pipe to a file or pipe to a subprocess that muxes?
        # Simpler: Pipe to raw h264 file, then mux with audio.
        
        cmd = [
            FFMPEG_EXE, '-y',
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f'{WIDTH}x{HEIGHT}',
            '-pix_fmt', 'rgba',
            '-r', str(FPS),
            '-i', '-',
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-qp', '18',
            raw_vid
        ]
        
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        
        # Audio accumulator for this scene
        scene_audio_list = []
        frames_tracker = [0] # Mutable counter for this scene
        
        # Run rendering logic
        try:
            render_func(proc, scene_audio_list, frames_tracker)
        except Exception as e:
            print(f"Error rendering {scene_name}: {e}")
            proc.kill()
            raise e
            
        proc.stdin.close()
        proc.wait()
        
        # Concatenate Audio for this scene
        scene_wav = os.path.join(TEMP_DIR, f"{scene_name}.wav")
        if not scene_audio_list:
            # Create 1s silence if no audio (edge case)
            scene_audio_list.append(create_silence(1.0))
            
        concat_txt = os.path.join(TEMP_DIR, f"{scene_name}_concat.txt")
        with open(concat_txt, "w", encoding='utf-8') as f:
            for p in scene_audio_list:
                safe_p = p.replace("\\", "/").replace("'", "'\\''")
                f.write(f"file '{safe_p}'\n")
                
        subprocess.run([
            FFMPEG_EXE, "-y", "-f", "concat", "-safe", "0", 
            "-i", concat_txt, "-c:a", "pcm_s16le", scene_wav
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Mux Scene
        subprocess.run([
            FFMPEG_EXE, "-y", 
            "-i", raw_vid, "-i", scene_wav,
            "-c:v", "copy", "-c:a", "aac",
            vid_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Cleanup raw
        if os.path.exists(raw_vid): os.remove(raw_vid)
        if os.path.exists(scene_wav): os.remove(scene_wav)
        if os.path.exists(concat_txt): os.remove(concat_txt)
        
        return vid_path

    # --- 1. INTRO SCENE ---
    def render_intro(pipe, aud_list, ft):
        process_segment(pipe, aud_list, ft, intro["hook"], intro["hook"], mode="typing_main", title="Did You Know?")
        process_segment(pipe, aud_list, ft, meta["youtubetitle"], f"In this video, we will cover {meta['youtubetitle']}", mode="static", title="Topic")
        desc_short = meta["description"].split('.')[0] + "."
        process_segment(pipe, aud_list, ft, desc_short, desc_short, mode="static", title="Description")
        process_segment(pipe, aud_list, ft, intro["summary"], intro["summary"], mode="typing_main", title="Summary")
        process_segment(pipe, aud_list, ft, intro["cta_intro"], intro["cta_intro"], mode="typing_main", title="Get Ready")

    intro_path = render_scene("scene_000_intro", render_intro)
    scene_clips.append(intro_path)

    # --- 2. MCQs SCENES ---
    for i, mcq in enumerate(mcqs):
        idx = i + 1
        
        def render_mcq(pipe, aud_list, ft):
            # Safety reset implicit in new clip
            q_text = mcq["question"]
            q_title = f"Question {idx} : {mcq['difficulty']}"
            opts_list = [f"{k}: {v}" for k, v in mcq["options"].items()]
            
            # Question
            process_segment(pipe, aud_list, ft, q_text, q_text, mode="typing_main", title=q_title)
            
            # Options
            opts_audio = ". ".join([f"Option {k}, {v}" for k, v in mcq["options"].items()])
            process_segment(pipe, aud_list, ft, q_text, opts_audio, mode="typing_options", subtext_list=opts_list, title=q_title)
            
            # Timer
            process_segment(pipe, aud_list, ft, q_text, None, mode="timer", duration_override=5, timer_seconds=5, subtext_list=opts_list, title=q_title)
            
            # Reveal Stats & Voiceover
            ans_key = mcq["answer"]
            # Reaction Pause
            process_segment(pipe, aud_list, ft, q_text, None, mode="static", subtext_list=opts_list, highlight_option=ans_key, title=q_title, duration_override=1.0)
            # Voiceover
            process_segment(pipe, aud_list, ft, q_text, f"The correct answer is {ans_key}", mode="static", subtext_list=opts_list, highlight_option=ans_key, title=q_title, duration_override=2.0)
            # Breather
            process_segment(pipe, aud_list, ft, q_text, None, mode="static", subtext_list=opts_list, highlight_option=ans_key, title=q_title, duration_override=0.5)
            
            # Explanation
            exp_text = mcq["detailedexplanation"]
            process_segment(pipe, aud_list, ft, exp_text, exp_text, mode="typing_main", title="Detailed Explanation")
            process_segment(pipe, aud_list, ft, exp_text, None, mode="static", duration_override=2, title="Detailed Explanation")

        clip_path = render_scene(f"scene_{idx:03d}_mcq", render_mcq)
        scene_clips.append(clip_path)

    # --- 3. OUTRO SCENE ---
    def render_outro(pipe, aud_list, ft):
        process_segment(pipe, aud_list, ft, outro["closing"], outro["closing"], mode="typing_main", title="Conclusion")
        process_segment(pipe, aud_list, ft, outro["cta_final"], outro["cta_final"], mode="typing_main", title="Subscribe")
        process_segment(pipe, aud_list, ft, outro["cta_final"], footer_str, mode="static", title="Subscribe")
        
    outro_path = render_scene("scene_999_outro", render_outro)
    scene_clips.append(outro_path)

    # --- FINAL CONCATENATION ---
    print("Concatenating All Scenes...", flush=True)
    final_list_txt = os.path.join(TEMP_DIR, "final_scenes.txt")
    with open(final_list_txt, "w", encoding='utf-8') as f:
        for p in scene_clips:
            safe_p = p.replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{safe_p}'\n")

    final_output = os.path.join(OUTPUT_DIR, "viral_course_video_fast.mp4")
    subprocess.run([
        FFMPEG_EXE, "-y", "-f", "concat", "-safe", "0", 
        "-i", final_list_txt, "-c", "copy", final_output
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    elapsed = time.time() - start_time
    print(f"DONE! Total time: {elapsed:.2f}s")
    print(f"Output: {final_output}")
    
    # --- CLEANUP TEMP FILES ---
    print("Cleaning up temporary files...", flush=True)
    try:
        import shutil
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)
            os.makedirs(TEMP_DIR, exist_ok=True)
            print("Temporary files cleaned.", flush=True)
    except Exception as e:
        print(f"Error cleaning temp files: {e}", flush=True)

if __name__ == "__main__":
    main()
