
import os
import sys
import json
import argparse
import subprocess
import shutil
import requests
import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

# Add script directory to path to import local config/modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from tts_generator import TTSGenerator

try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except:
    FFMPEG_EXE = "ffmpeg"

class BookSummaryVideoGenerator:
    def __init__(self):
        self.tts_gen = TTSGenerator()
        # Override TTS voice if needed from config
        self.tts_gen.voice = config.TTS_VOICE
        
        self.font = None
        self.bold_font = None
        
    def setup_fonts(self):
        """Load fonts"""
        # Try to load fonts from config or system
        try:
            self.font = ImageFont.truetype("arial.ttf", config.BODY_FONT_SIZE)
            self.bold_font = ImageFont.truetype("arialbd.ttf", config.BODY_FONT_SIZE)
            self.title_font = ImageFont.truetype("arialbd.ttf", config.TITLE_FONT_SIZE)
            self.author_font = ImageFont.truetype("arial.ttf", config.AUTHOR_FONT_SIZE)
            self.chapter_font = ImageFont.truetype("arialbd.ttf", config.CHAPTER_TITLE_FONT_SIZE)
        except:
             # Fallback to default if custom fonts fail
            self.font = ImageFont.load_default()
            self.bold_font = ImageFont.load_default()
            self.title_font = ImageFont.load_default()
            self.author_font = ImageFont.load_default()
            self.chapter_font = ImageFont.load_default()
            print("Warning: Could not load requested fonts, using defaults.")

    def download_image(self, url, save_path):
        """Download image from URL"""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return save_path
        except Exception as e:
            print(f"Error downloading image {url}: {e}")
            return None

    def get_dominant_color(self, image_path):
        """Get dominant color from image"""
        try:
            img = Image.open(image_path).convert('RGB')
            img = img.resize((1, 1), resample=0)
            dominant_color = img.getpixel((0, 0))
            return dominant_color
        except Exception as e:
            print(f"Error getting dominant color: {e}")
            return (50, 50, 50) # Dark gray default

    def get_invert_color(self, color):
        """Get inverted color (black or white) for best contrast"""
        # Calculate luminance
        r, g, b = color
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        if luminance > 0.5:
            return (0, 0, 0) # Black text for light background
        else:
            return (255, 255, 255) # White text for dark background

    def create_background(self, width, height, color):
        """Create a solid color background"""
        return Image.new('RGB', (width, height), color)

    def wrap_text(self, text, font, max_width, draw):
        """Wrap text based on pixel width"""
        lines = []
        words = text.split()
        
        if not words:
            return []
            
        current_line = words[0]
        
        for word in words[1:]:
            test_line = current_line + " " + word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            w = bbox[2] - bbox[0]
            
            if w <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        
        lines.append(current_line)
        return lines

    def generate_layout_frame(self, cover_path, book_title, book_author, chapter_title, 
                            segment_text, full_text, bg_color, text_color, 
                            width, height, is_short=False):
        """
        Generate a single video frame.
        Normal: Split layout with text.
        Shorts: Cover only, centered, 30% padding.
        """
        img = Image.new('RGB', (width, height), bg_color)
        draw = ImageDraw.Draw(img)
        
        if is_short:
            # --- SHORTS LAYOUT (Cover Only) ---
            padding = config.SHORTS_PADDING  # Use fixed padding for shorts
            
            # Available area for cover
            cover_area_w = width - (padding * 2)
            cover_area_h = height - (padding * 2)
            
            if cover_path and os.path.exists(cover_path):
                try:
                    cover = Image.open(cover_path).convert('RGBA')
                    # Resize to fit within the padded area, keeping aspect ratio
                    cover.thumbnail((cover_area_w, cover_area_h), Image.LANCZOS)
                    
                    # Center within padded area
                    cover_x = padding + (cover_area_w - cover.width) // 2
                    cover_y = padding + (cover_area_h - cover.height) // 2
                    
                    img.paste(cover, (cover_x, cover_y), cover)
                except Exception as e:
                    print(f"Error drawing cover: {e}")
            
            return img

        # --- NORMAL LAYOUT ---
        padding = config.PADDING
        gap = config.GAP
        half_width = width // 2
        
        # ... (rest of normal layout logic) ...
        
        # --- LEFT SIDE: Book Cover ---
        cover_area_w = half_width - (padding * 2)
        cover_area_h = height - (padding * 2)
        
        if cover_path and os.path.exists(cover_path):
            try:
                cover = Image.open(cover_path).convert('RGBA')
                cover.thumbnail((cover_area_w, cover_area_h), Image.LANCZOS)
                # Center within the padded left area
                cover_x = padding + (cover_area_w - cover.width) // 2
                cover_y = padding + (cover_area_h - cover.height) // 2
                img.paste(cover, (cover_x, cover_y), cover)
            except Exception as e:
                print(f"Error drawing cover: {e}")
        
        # --- RIGHT SIDE ---
        right_start_x = half_width + gap
        right_max_width = (width - padding) - right_start_x
        current_y = padding
        
        # 1. Title & Author
        title_lines = self.wrap_text(book_title, self.title_font, right_max_width, draw)
        for line in title_lines:
            bbox = draw.textbbox((right_start_x, current_y), line, font=self.title_font)
            text_h = bbox[3] - bbox[1]
            draw.text((right_start_x, current_y), line, font=self.title_font, fill=text_color)
            current_y += text_h + 10
            
        current_y += 30 
        author_bbox = draw.textbbox((right_start_x, current_y), book_author, font=self.author_font)
        author_h = author_bbox[3] - author_bbox[1]
        draw.text((right_start_x, current_y), book_author, font=self.author_font, fill=text_color)
        current_y += author_h + 40 
        
        # 2. Key Content (Chapter & Lyrics)
        current_y += 30  # Top margin before chapter title
        chapter_lines = self.wrap_text(chapter_title, self.chapter_font, right_max_width, draw)
        for line in chapter_lines:
             bbox = draw.textbbox((right_start_x, current_y), line, font=self.chapter_font)
             text_h = bbox[3] - bbox[1]
             draw.text((right_start_x, current_y), line, font=self.chapter_font, fill=text_color)
             current_y += text_h + 15
        
        current_y += 40
        
        # Lyrics Text Display
        lines = self.wrap_text(segment_text, self.font, right_max_width, draw)
        for line in lines:
            bbox = draw.textbbox((right_start_x, current_y), line, font=self.font)
            text_h = bbox[3] - bbox[1]
            # Apply opacity from config
            alpha = config.LYRICS_ACTIVE_OPACITY
            fill_color = (*text_color, alpha)
            draw.text((right_start_x, current_y), line, font=self.font, fill=fill_color)
            current_y += text_h + 25
            
        # 3. Footer / CTA (Bottom)
        cta_text = "Check description to order this book."
        bbox = draw.textbbox((0, 0), cta_text, font=self.author_font)
        cta_h = bbox[3] - bbox[1]
        cta_x = right_start_x
        cta_y = height - padding - cta_h
        draw.text((cta_x, cta_y), cta_text, font=self.author_font, fill=text_color)
        
        return img

    def create_video_segment(self, segment_text, audio_path, cover_path, book_title, book_author, chapter_title, bg_color, text_color, output_path, width, height, is_short=False):
        """
        Create a video segment.
        """
        # Generate image
        img = self.generate_layout_frame(cover_path, book_title, book_author, chapter_title, 
                                       segment_text, "", bg_color, text_color, width, height, is_short=is_short)
        
        img_path = output_path.replace(".mp4", ".png")
        img.save(img_path)
        
        # Get audio duration
        duration = self.tts_gen.get_audio_duration(audio_path)
        
        # Ensure even dimensions
        if width % 2 != 0: width -= 1
        if height % 2 != 0: height -= 1
        
        # Escape font path for FFmpeg (Windows path issue)
        # font_path = config.MARQUEE_FONT_PATH.replace("\\", "/").replace(":", "\\\\:")
        
        cmd = [
            FFMPEG_EXE, "-y",
            "-threads", "1",
            "-loop", "1",
            "-i", img_path,
            "-i", audio_path,
            "-c:v", config.CODEC,
            "-preset", "ultrafast",
            "-t", str(duration),
            "-pix_fmt", "yuv420p"
        ]
        
        # Filter Chain
        filters = [f"scale={width}:{height}"]
        
        # Marquee is helpful for channel branding.
        # Use relative path for FFmpeg on Windows to avoid drive letter colon issues
        escaped_font_path = "fonts/arial.ttf"
        
        # Marquee text filter with background box for visibility
        drawtext_filter = f"drawtext=fontfile='{escaped_font_path}':text='{config.MARQUEE_TEXT}':fontcolor=white:fontsize={config.MARQUEE_FONT_SIZE}:box=1:boxcolor=black@0.5:x=w-mod(t*100\,w+tw):y={config.MARQUEE_TOP_PADDING}"
        filters.append(drawtext_filter)
        
        cmd.extend(["-vf", ",".join(filters), "-shortest", output_path])
        
        subprocess.run(cmd, check=True)
        
        # Cleanup image
        if os.path.exists(img_path):
            os.remove(img_path)
            
        return output_path

    def process_story(self, story_data, test_mode=False, shorts_mode=False):
        """Process a single story"""
        # --- MAP DATA FIELDS ---
        yt = story_data.get('youtube_metadata', {})
        st = story_data.get('screentext', {})
        
        display_title = st.get('original_title', yt.get('title', 'Untitled'))
        display_author = st.get('author', yt.get('author', 'Unknown Author'))
        cover_url = yt.get('cover_image', yt.get('cover_image_url', ''))
        
        print(f"Processing: {display_title} by {display_author} (Shorts: {shorts_mode})")
        
        if not cover_url:
            print("Warning: No cover image URL found!")
        
        # 1. Download Cover
        cover_path = os.path.join(config.TEMP_DIR, "cover.jpg")
        print(f"Downloading cover from {cover_url}...")
        self.download_image(cover_url, cover_path)
        
        # 2. Determine Colors
        bg_color = self.get_dominant_color(cover_path)
        text_color = self.get_invert_color(bg_color)
        print(f"Colors - BG: {bg_color}, Text: {text_color}")
        
        # Dimensions
        if shorts_mode:
            width = config.SHORTS_WIDTH
            height = config.SHORTS_HEIGHT
        else:
            width = config.TEST_WIDTH if test_mode else config.WIDTH
            height = config.TEST_HEIGHT if test_mode else config.HEIGHT
        
        self.setup_fonts()
        
        segments = [] 
        cumulative_time = 0
        chapter_timestamps = []
        
        # 3. Intro
        # "read only first chapter" implication -> Skip intro?
        # Usually shorts need a hook. The "welcome_hook" in intro is good.
        # I will SKIP intro if shorts_mode is True, based on strict reading of "read ONLY first chapter".
        
        if not shorts_mode:
            intro_data = story_data.get('channel_intro', {})
            welcome_hook = intro_data.get('welcome_hook', '')
            intro_line = intro_data.get('intro_line', '')
            
            # Audio reads both
            spoken_intro_text = f"{welcome_hook} {intro_line}"
            # Display only reads welcome_hook
            display_intro_text = welcome_hook
            
            if spoken_intro_text.strip():
                print("Creating Intro...")
                audio_path, _ = self.tts_gen.generate_speech(spoken_intro_text)
                if audio_path:
                    duration = self.tts_gen.get_audio_duration(audio_path)
                    chapter_timestamps.append({
                        "time": cumulative_time,
                        "label": "Introduction"
                    })
                    
                    out_path = os.path.join(config.TEMP_DIR, "intro.mp4")
                    self.create_video_segment(display_intro_text, audio_path, cover_path, display_title, display_author, "Introduction", bg_color, text_color, out_path, width, height, is_short=shorts_mode)
                    segments.append(out_path)
                    cumulative_time += duration
        
        # 4. Chapters
        chapters = story_data.get('chapters', [])
        for i, chapter in enumerate(chapters):
            if test_mode and i >= config.TEST_SCENE_LIMIT:
                break
                
            # Shorts Mode: Only Chapter 1 (index 0)
            if shorts_mode and i > 0:
                print("Shorts mode: Skipping subsequent chapters.")
                break
                
            c_number = chapter.get('chapter_number', str(i+1))
            c_name = chapter.get('chapter_title', '')
            c_title = f"Chapter {c_number}: {c_name}"
            
            # Support both 'summary' and 'chapter_summary' keys
            c_summary = chapter.get('chapter_summary', chapter.get('summary', ''))
            
            print(f"Processing {c_title}...")
            
            # Record chapter start
            chapter_timestamps.append({
                "time": cumulative_time,
                "label": c_name if c_name else f"Chapter {c_number}"
            })
            
            # Split summary into sentences for "Lyrics Style" sync
            sentences = [s.strip() + "." for s in c_summary.split(".") if s.strip()]
            
            for j, sentence in enumerate(sentences):
                # Generate audio first to get duration (and file)
                audio_path, _ = self.tts_gen.generate_speech(sentence)
                if not audio_path: continue
                
                duration = self.tts_gen.get_audio_duration(audio_path)
                out_path = os.path.join(config.TEMP_DIR, f"ch{i}_s{j}.mp4")
                self.create_video_segment(sentence, audio_path, cover_path, display_title, display_author, c_title, bg_color, text_color, out_path, width, height, is_short=shorts_mode)
                segments.append(out_path)
                cumulative_time += duration
        
        # 5. Outro (Shorts Only)
        if shorts_mode:
            print("Creating Shorts Outro...")
            outro_text = config.SHORTS_OUTRO_TEXT
            audio_path, _ = self.tts_gen.generate_speech(outro_text)
            if audio_path:
                out_path = os.path.join(config.TEMP_DIR, "outro.mp4")
                # Outro also uses "Cover Only" layout (is_short=True)
                self.create_video_segment(outro_text, audio_path, cover_path, display_title, display_author, "Outro", bg_color, text_color, out_path, width, height, is_short=True)
                segments.append(out_path)

        # 6. Concatenate
        print(f"Concatenating {len(segments)} segments...")
        concat_list_path = os.path.join(config.TEMP_DIR, "concat.txt")
        with open(concat_list_path, 'w', encoding='utf-8') as f:
            for s in segments:
                f.write(f"file '{s.replace(os.sep, '/')}'\n")
        
        filename_suffix = "_short" if shorts_mode else ""
        final_output = os.path.join(config.OUTPUT_DIR, f"{display_title.replace(' ', '_')}{filename_suffix}.mp4")
        
        cmd = [
            FFMPEG_EXE, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy",
            final_output
        ]
        subprocess.run(cmd, check=True)
        print(f"Video generated: {final_output}")
        
        # Save timestamps for Long video
        if not shorts_mode:
            ts_path = os.path.join(config.OUTPUT_DIR, "timestamps.json")
            with open(ts_path, 'w', encoding='utf-8') as f:
                json.dump(chapter_timestamps, f, indent=4)
            print(f"Timestamps saved to {ts_path}")
        
        # Cleanup Temp Directory
        print("Cleaning up temporary files...")
        for filename in os.listdir(config.TEMP_DIR):
            file_path = os.path.join(config.TEMP_DIR, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path) and filename != "tts_cache": 
                     shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
                
        return final_output

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Run in test mode")
    # --short flag is no longer needed as we generate both, but keeping it as valid arg to avoid breaking potential scripts
    parser.add_argument("--short", action="store_true", help="Deprecated: Script now generates both formats by default") 
    args = parser.parse_args()
    
    with open(config.DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    generator = BookSummaryVideoGenerator()
    
    if data:
        story = data[0]
        
        # 1. Generate Standard Video
        print("=== GENERATING STANDARD VIDEO ===")
        generator.process_story(story, test_mode=args.test, shorts_mode=False)
        
        print("\n\n")
        
        # 2. Generate YouTube Short
        print("=== GENERATING YOUTUBE SHORT ===")
        generator.process_story(story, test_mode=args.test, shorts_mode=True)

if __name__ == "__main__":
    main()
