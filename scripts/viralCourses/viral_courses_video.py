
import json
import os
import sys
import time
import math
import skia
import numpy as np
import subprocess
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import VideoClip, ImageClip, TextClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.audio.AudioClip import AudioArrayClip
from moviepy.video.compositing.CompositeVideoClip import concatenate_videoclips, CompositeVideoClip
from gtts import gTTS
import imageio_ffmpeg

# Force utf-8 output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

print("Starting Viral Course Video Generator (Optimized)...", flush=True)

WIDTH = 1920
HEIGHT = 1080
BG_COLOR = skia.ColorWHITE
TEXT_COLOR = skia.ColorBLACK
GREEN_HIGHLIGHT = skia.Color(144, 238, 144) 
FONT_NAME = "Arial" 

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_FILE = os.path.join(REPO_ROOT, "data", "viralCourses", "data.json")
OUTPUT_DIR = os.path.join(REPO_ROOT, "output", "viralCourses")
TEMP_DIR = os.path.join(OUTPUT_DIR, "temp")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

def get_font(size=40):
    font_path = os.path.join(REPO_ROOT, "assets", "fonts", "Inter-Bold.ttf")
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

def render_frame_skia(
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
    Renders a complex frame with title, main text (typing), options (typing/highlight), timer, and footer.
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
        # Center or Left?
        canvas.drawSimpleText(title, margin_x, margin_y, title_font, title_paint)
        margin_y += 100

    # 2. Main Text (Question/Description)
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
                # Check for "A", "B" etc.
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

    # 5. Footer (Persistent)
    if footer_text:
        f_font = get_font(30)
        f_paint = skia.Paint(Color=skia.ColorGRAY, AntiAlias=True)
        f_width = f_font.measureText(footer_text)
        # Bottom center
        canvas.drawSimpleText(footer_text, (WIDTH - f_width)/2, HEIGHT - 50, f_font, f_paint)

    image = surface.makeImageSnapshot()
    # Use RGBA 8888 to ensure valid channel data, then strip alpha to simple RGB
    # This prevents stride/alpha interpretation issues in MoviePy
    array = image.toarray(colorType=skia.kRGBA_8888_ColorType)
    return array[:, :, :3]

def generate_voiceover(text, filename):
    path = os.path.join(TEMP_DIR, filename)
    if os.path.exists(path):
        return path
    
    print(f"Generating TTS for: {text[:30]}...", flush=True)
    safe_text = text.replace('"', '').replace("'", "")
    if not safe_text.strip(): return None
    
    try:
        tts = gTTS(safe_text, lang='en')
        tts.save(path)
        return path
    except Exception as e:
        print(f"Error generating TTS for '{text[:20]}': {e}")
        return None

def create_base_clip(
    main_text, 
    title="", 
    subtext_list=None, 
    audio_text=None,
    mode="static",
    duration_override=None,
    highlight_option=None,
    timer_seconds=None,
    footer_text=""
):
    """
    Generic clip creator for all states.
    """
    
    # 1. Audio & Duration
    audio_clip = None
    voice_duration = 0
    
    if audio_text:
        fname = f"{hash(audio_text)}.wav"
        apath = generate_voiceover(audio_text, fname)
        if apath:
            # Load with lazy loading logic or just AudioFileClip
            audio_clip = AudioFileClip(apath)
            voice_duration = audio_clip.duration

    final_duration = voice_duration
    if duration_override:
        final_duration = max(voice_duration, duration_override)
    
    # 2. Frame Generator
    def make_frame(t):
        progress = 1.0
        visible_opts_count = len(subtext_list) if subtext_list else 0
        current_timer = None
        
        if mode == "typing_main":
            progress = min(1.0, t / (voice_duration * 0.95)) if voice_duration > 0 else 1.0
            
        elif mode == "typing_options":
            if subtext_list and voice_duration > 0:
                item_dur = voice_duration / len(subtext_list)
                visible_opts_count = min(len(subtext_list), int(t / item_dur) + 1)
        
        elif mode == "timer":
            if timer_seconds:
                remaining = math.ceil(timer_seconds - t)
                current_timer = max(1, remaining)

        return render_frame_skia(
            main_text, 
            progress=progress, 
            subtext_list=subtext_list, 
            visible_subtext_count=visible_opts_count, 
            highlight_option=highlight_option, 
            title=title,
            timer_val=current_timer,
            footer_text=footer_text
        )

    clip = VideoClip(make_frame, duration=final_duration)
    if audio_clip:
        clip = clip.with_audio(audio_clip)
    
    # Crucial: Close audio clip handles eventually? Python GC handles it usually.
    return clip

def main():
    print("Execution starting...", flush=True)
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print("Data loaded.", flush=True)
        
    final_clips = []
    
    assets = data[0]["video_assets"]
    intro = assets["intro_script"]
    meta = assets["youtube_metadata"]
    mcqs = data[0]["mcq_data"]
    outro = data[0]["outro_script"]

    footer_str = intro.get("checkfullexamlinkindescription", "Check full exam link in description")

    # --- INTRO SEQUENCE ---
    print("Processing Intro...", flush=True)
    
    final_clips.append(create_base_clip(
        intro["hook"], 
        title="Did You Know?", 
        audio_text=intro["hook"], 
        mode="typing_main",
        footer_text=footer_str
    ))
    
    final_clips.append(create_base_clip(
        meta["youtubetitle"], 
        title="Topic", 
        audio_text=f"In this video, we will cover {meta['youtubetitle']}", 
        mode="static",
        footer_text=footer_str
    ))
    
    desc_short = meta["description"].split('.')[0] + "."
    final_clips.append(create_base_clip(
        desc_short, 
        title="Description", 
        audio_text=desc_short, 
        mode="static",
        footer_text=footer_str
    ))

    final_clips.append(create_base_clip(
        intro["summary"], 
        title="Summary", 
        audio_text=intro["summary"], 
        mode="typing_main",
        footer_text=footer_str
    ))
    
    final_clips.append(create_base_clip(
        intro["cta_intro"], 
        title="Get Ready", 
        audio_text=intro["cta_intro"], 
        mode="typing_main",
        footer_text=footer_str
    ))

    # --- MCQ SEQUENCE ---
    for i, mcq in enumerate(mcqs):
        print(f"Processing MCQ {i+1}/{len(mcqs)}...", flush=True)
        
        q_text = mcq["question"]
        q_title = f"Question {i+1} : {mcq['difficulty']}"
        opts_list = [f"{k}: {v}" for k, v in mcq["options"].items()]
        
        # 1. Question
        final_clips.append(create_base_clip(
            q_text,
            title=q_title,
            audio_text=q_text,
            mode="typing_main",
            footer_text=footer_str
        ))
        
        # 2. Options
        opts_audio = ". ".join([f"Option {k}, {v}" for k, v in mcq["options"].items()])
        final_clips.append(create_base_clip(
            q_text,
            subtext_list=opts_list,
            title=q_title,
            audio_text=opts_audio,
            mode="typing_options",
            footer_text=footer_str
        ))
        
        # 3. Timer
        final_clips.append(create_base_clip(
            q_text,
            subtext_list=opts_list,
            title=q_title,
            mode="timer",
            duration_override=5,
            timer_seconds=5,
            footer_text=footer_str
        ))
        
        # 4. Answer Reveal
        ans_key = mcq["answer"]
        final_clips.append(create_base_clip(
            q_text,
            subtext_list=opts_list,
            title=q_title,
            highlight_option=ans_key,
            audio_text=f"The correct answer is {ans_key}",
            mode="static",
            duration_override=3,
            footer_text=footer_str
        ))
        
        # 5. Explanation
        exp_text = mcq["detailedexplanation"]
        final_clips.append(create_base_clip(
            exp_text,
            title="Detailed Explanation",
            audio_text=exp_text,
            mode="typing_main",
            footer_text=footer_str
        ))
        final_clips.append(create_base_clip(
            exp_text,
            title="Detailed Explanation",
            mode="static",
            duration_override=3,
            footer_text=footer_str
        ))

    # --- OUTRO SEQUENCE ---
    print("Processing Outro...", flush=True)
    
    final_clips.append(create_base_clip(
        outro["closing"],
        title="Conclusion",
        audio_text=outro["closing"],
        mode="typing_main",
        footer_text=footer_str
    ))
    
    final_clips.append(create_base_clip(
        outro["cta_final"],
        title="Subscribe",
        audio_text=outro["cta_final"],
        mode="typing_main",
        footer_text=footer_str
    ))
    
    final_clips.append(create_base_clip(
        outro["cta_final"],
        title="Subscribe",
        audio_text=footer_str, 
        mode="static",
        footer_text=footer_str
    ))

    # --- COMPOSITION (CHAIN) ---
    print(f"Concatenating {len(final_clips)} clips (method='chain')...", flush=True)
    # Using method="chain" which concatenates sequentially, reducing memory usage
    final_video = concatenate_videoclips(final_clips, method="chain")
    
    output_filename = os.path.join(OUTPUT_DIR, "viral_course_video_refined.mp4")
    
    # Use 2 threads to balance speed and memory
    final_video.write_videofile(
        output_filename, 
        fps=24, 
        codec='libx264', 
        audio_codec='aac',
        threads=2,
        preset='medium',
        ffmpeg_params=['-crf', '28']
    )
    print(f"Done! Video saved to {output_filename}", flush=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FATAL ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
