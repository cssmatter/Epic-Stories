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

# --- SKIA HELPERS ---
def get_font(size=40):
    font_path = os.path.join(ASSETS_DIR, "Inter-Bold.ttf")
    if os.path.exists(font_path):
         typeface = skia.Typeface.MakeFromFile(font_path)
    else:
         typeface = skia.Typeface.MakeFromName("Arial", skia.FontStyle.Bold())
    return skia.Font(typeface, size)

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
    surface = skia.Surface(WIDTH, HEIGHT)
    canvas = surface.getCanvas()
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

    image = surface.makeImageSnapshot()
    arr = image.toarray(colorType=skia.kRGBA_8888_ColorType).tobytes()
    # Explicitly clear/delete to help GC
    del image
    del canvas
    del surface
    return arr

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

import os

# --- TTS HELPERS ---
def generate_tts_cached_offline(text, filename_seed):
    """
    Generate TTS using gTTS, save to temp.
    """
    if not text or not text.strip(): return None, 0.0

    clean_seed = "".join(x for x in filename_seed if x.isalnum())[:20]
    fname = f"{clean_seed}_{hash(text)}.mp3" 
    path = os.path.join(TEMP_DIR, fname)
    
    if os.path.exists(path):
        return path, get_audio_duration(path)
    
    try:
        tts = gTTS(text=text, lang='en')
        tts.save(path)
        
        if os.path.exists(path):
             return path, get_audio_duration(path)
        return None, 0.0
    except Exception as e:
        print(f"  TTS Error: {e}")
        return None, 0.0


# ...

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
    
    print("Opening FFmpeg pipe...", flush=True)
    process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

    # 3. Processing Loop
    audio_segments = []
    total_audio_time = 0.0
    total_frames_written = 0
    
    def process_segment(
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
            dur = duration_override
            
        final_dur = max(dur, duration_override if duration_override else 0)
        
        # Add to audio list
        if audio_path:
            audio_segments.append(audio_path)
            if final_dur > dur:
                silence_gap = final_dur - dur
                if silence_gap > 0.1:
                    s_path = create_silence(silence_gap)
                    audio_segments.append(s_path)
        
        # B. Video Rendering
        nonlocal total_audio_time, total_frames_written
        
        start_audio_time = total_audio_time
        total_audio_time += final_dur
        
        target_total_frames = int(total_audio_time * FPS)
        num_frames = target_total_frames - total_frames_written
        
        if num_frames <= 0: return

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
                try:
                    process.stdin.write(frame_bytes)
                    total_frames_written += 1
                except BrokenPipeError:
                    break

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
                try:
                    process.stdin.write(frame_bytes)
                    total_frames_written += 1
                except BrokenPipeError: break

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
                try:
                    process.stdin.write(frame_bytes)
                    total_frames_written += 1
                except BrokenPipeError: break
        
        elif mode == "timer":
             for f_idx in range(num_frames):
                t = f_idx / FPS
                remaining = math.ceil(timer_seconds - t) if timer_seconds else 0
                frame_bytes = render_frame_bytes(
                    text_content, 
                    progress=1.0, 
                    subtext_list=subtext_list,
                    visible_subtext_count=len(subtext_list) if subtext_list else 0,
                    title=title,
                    timer_val=max(1, remaining),
                    footer_text=footer_str
                )
                try: 
                    process.stdin.write(frame_bytes)
                    total_frames_written += 1
                except BrokenPipeError: break

        # Flush and GC
        if total_frames_written % 100 == 0:
            process.stdin.flush()
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

    # --- DEFINING THE SEQUENCE ---
    print("Generating Sequence...", flush=True)

    # Intro
    process_segment(intro["hook"], intro["hook"], mode="typing_main", title="Did You Know?")
    process_segment(meta["youtubetitle"], f"In this video, we will cover {meta['youtubetitle']}", mode="static", title="Topic")
    desc_short = meta["description"].split('.')[0] + "."
    process_segment(desc_short, desc_short, mode="static", title="Description")
    process_segment(intro["summary"], intro["summary"], mode="typing_main", title="Summary")
    process_segment(intro["cta_intro"], intro["cta_intro"], mode="typing_main", title="Get Ready")

    # MCQs
    for i, mcq in enumerate(mcqs):
        print(f"  MCQ {i+1}/{len(mcqs)}", flush=True)
        q_text = mcq["question"]
        q_title = f"Question {i+1} : {mcq['difficulty']}"
        opts_list = [f"{k}: {v}" for k, v in mcq["options"].items()]
        
        # 1. Question (Typing)
        process_segment(q_text, q_text, mode="typing_main", title=q_title)
        
        # 2. Options (Typing Sequence)
        opts_audio = ". ".join([f"Option {k}, {v}" for k, v in mcq["options"].items()])
        process_segment(q_text, opts_audio, mode="typing_options", subtext_list=opts_list, title=q_title)
        
        # 3. Timer (5s static silence/visual)
        process_segment(q_text, None, mode="timer", duration_override=5, timer_seconds=5, subtext_list=opts_list, title=q_title)
        
        # 4. Reaction Pause (1.0s highlight, but SILENCE)
        ans_key = mcq["answer"]
        process_segment(q_text, None, mode="static", subtext_list=opts_list, highlight_option=ans_key, title=q_title, duration_override=1.0)
        
        # 5. Reveal Voiceover ("The correct answer is...")
        process_segment(q_text, f"The correct answer is {ans_key}", mode="static", subtext_list=opts_list, highlight_option=ans_key, title=q_title, duration_override=2.0)
        
        # 6. Breather (0.5s silence before explanation)
        process_segment(q_text, None, mode="static", subtext_list=opts_list, highlight_option=ans_key, title=q_title, duration_override=0.5)

        # 7. Explanation
        exp_text = mcq["detailedexplanation"]
        process_segment(exp_text, exp_text, mode="typing_main", title="Detailed Explanation")
        process_segment(exp_text, None, mode="static", duration_override=2, title="Detailed Explanation") # Brief Pause

    # Outro
    process_segment(outro["closing"], outro["closing"], mode="typing_main", title="Conclusion")
    process_segment(outro["cta_final"], outro["cta_final"], mode="typing_main", title="Subscribe")
    process_segment(outro["cta_final"], footer_str, mode="static", title="Subscribe")

    # --- CLEANUP ---
    print("Closing Video Pipe...", flush=True)
    process.stdin.close()
    process.wait()
    
    # --- AUDIO MERGE ---
    print("Concatenating Audio...", flush=True)
    concat_list_path = os.path.join(TEMP_DIR, "concat.txt")
    with open(concat_list_path, "w", encoding='utf-8') as f:
        for p in audio_segments:
            # ffmpeg concat demuxer formats
            safe_p = p.replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{safe_p}'\n")
    
    final_audio_path = os.path.join(TEMP_DIR, "full_audio.wav")
    subprocess.run([
        FFMPEG_EXE, "-y", "-f", "concat", "-safe", "0", 
        "-i", concat_list_path, "-c:a", "pcm_s16le", final_audio_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # --- FINAL MUX ---
    print("Muxing Final Video...", flush=True)
    final_output = os.path.join(OUTPUT_DIR, "viral_course_video_fast.mp4")
    subprocess.run([
        FFMPEG_EXE, "-y", 
        "-i", output_video_path,
        "-i", final_audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        final_output
    ]) # stdout hidden? 

    elapsed = time.time() - start_time
    print(f"DONE! Total time: {elapsed:.2f}s")
    print(f"Output: {final_output}")

if __name__ == "__main__":
    main()
