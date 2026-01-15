"""
Epic Stories Video Generator
Main script to generate YouTube videos from story.json data
"""
import json
import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add script directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from image_generator import ImageGenerator
from tts_generator import TTSGenerator
from subtitle_generator import SubtitleGenerator

try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except:
    FFMPEG_EXE = "ffmpeg"

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')


class EpicStoriesVideoGenerator:
    def __init__(self):
        self.image_gen = ImageGenerator()
        self.tts_gen = TTSGenerator()
        self.subtitle_gen = SubtitleGenerator()
        self.scene_videos = []
    
    def load_story_data(self):
        """Load story data from JSON file"""
        if not os.path.exists(config.DATA_FILE):
            raise FileNotFoundError(f"Story data file not found: {config.DATA_FILE}")
        
        with open(config.DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Expecting array with story object
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        else:
            return data
    
    def create_intro_scene(self, story_title):
        """
        Create intro scene with story title
        
        Args:
            story_title: Title of the story
            
        Returns:
            Path to intro video file
        """
        print(f"Creating intro scene for: {story_title}")
        
        intro_path = os.path.join(config.TEMP_DIR, "scene_000_intro.mp4")
        
        # Generate intro voiceover
        intro_text = f"Welcome. Today's story: {story_title}"
        audio_path, _ = self.tts_gen.generate_speech(intro_text)
        
        if not audio_path:
            print("Warning: No audio generated for intro")
            audio_duration = config.INTRO_DURATION
        else:
            audio_duration = self.tts_gen.get_audio_duration(audio_path)
        
        # Create intro image with title
        from PIL import Image, ImageDraw, ImageFont
        
        img = Image.new('RGB', (config.WIDTH, config.HEIGHT), color='#0f0f1e')
        draw = ImageDraw.Draw(img)
        
        # Draw gradient background
        for y in range(config.HEIGHT):
            shade = int(15 + (y / config.HEIGHT) * 40)
            draw.line([(0, y), (config.WIDTH, y)], fill=(shade, shade, shade + 15))
        
        # Draw title
        try:
            title_font = ImageFont.truetype("arial.ttf", 80)
        except:
            title_font = ImageFont.load_default()
        
        # Word wrap title
        words = story_title.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=title_font)
            if bbox[2] - bbox[0] <= config.WIDTH - 200:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Draw lines centered
        total_height = len(lines) * 100
        y_start = (config.HEIGHT - total_height) // 2
        
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=title_font)
            line_width = bbox[2] - bbox[0]
            x = (config.WIDTH - line_width) // 2
            y = y_start + i * 100
            
            # Draw shadow
            draw.text((x + 3, y + 3), line, fill='black', font=title_font)
            # Draw text
            draw.text((x, y), line, fill='white', font=title_font)
        
        # Save intro image
        intro_img_path = os.path.join(config.TEMP_DIR, "intro_image.png")
        img.save(intro_img_path)
        
        # Create video from image
        cmd = [
            FFMPEG_EXE, "-y",
            "-loop", "1",
            "-i", intro_img_path,
            "-t", str(audio_duration),
            "-vf", f"scale={config.WIDTH}:{config.HEIGHT}",
            "-c:v", config.CODEC,
            "-crf", str(config.CRF),
            "-pix_fmt", "yuv420p",
            intro_path
        ]
        
        subprocess.run(cmd, capture_output=True)
        
        # Add audio if available
        if audio_path:
            intro_with_audio = intro_path.replace('.mp4', '_audio.mp4')
            cmd = [
                FFMPEG_EXE, "-y",
                "-i", intro_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                intro_with_audio
            ]
            subprocess.run(cmd, capture_output=True)
            
            # Replace original
            if os.path.exists(intro_with_audio):
                os.replace(intro_with_audio, intro_path)
        
        print(f"✓ Intro scene created: {intro_path}")
        return intro_path
    
    def create_scene_video(self, scene_data, scene_number):
        """
        Create video for a single scene
        
        Args:
            scene_data: Scene dictionary with text and image_prompt
            scene_number: Scene number for labeling
            
        Returns:
            Path to scene video file
        """
        print(f"\nCreating scene {scene_number}...")
        
        text = scene_data.get('text', '')
        image_prompt = scene_data.get('image_prompt', '')
        
        scene_path = os.path.join(config.TEMP_DIR, f"scene_{scene_number:03d}.mp4")
        
        # Step 1: Generate image from prompt
        print(f"  Generating image...")
        image_path = self.image_gen.generate_image(image_prompt, scene_number)
        
        # Step 2: Generate voiceover and word timings
        print(f"  Generating voiceover & word timings...")
        audio_path, word_timings = self.tts_gen.generate_speech(text)
        
        if not audio_path:
            print("  Warning: No audio generated")
            scene_duration = 5.0
        else:
            scene_duration = self.tts_gen.get_audio_duration(audio_path)
        
        # Step 3: Create video from image as background
        print(f"  Creating video (duration: {scene_duration:.2f}s)...")
        
        # Create base video from image - Scale and crop to fit 1920x1080
        # Create base video from image with Ken Burns effect
        base_video = scene_path.replace('.mp4', '_base.mp4')
        
        # Determine zoom direction (Odd=In, Even=Out)
        direction = "in" if scene_number % 2 != 0 else "out"
        
        # Calculate parameters for smooth zoom
        fps = config.FPS
        num_frames = int(scene_duration * fps)
        step = 0.15 / num_frames  # 15% zoom over duration
        
        if direction == "in":
            # Zoom IN: Start at 1.0, increase
            zoom_expr = f"min(zoom+{step},1.15)"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"
        else:
            # Zoom OUT: Start at 1.15, decrease
            zoom_expr = f"if(eq(on,1),1.15,max(1.0,zoom-{step}))"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"
            
        # 4K Supersampling Filter Chain (Smooths jitter)
        filter_complex = (
            f"scale=1920:1080:force_original_aspect_ratio=increase,"
            f"crop=1920:1080,"
            f"zoompan=z='{zoom_expr}':d={num_frames}:x='{x_expr}':y='{y_expr}':s=3840x2160:fps={fps},"
            f"scale=1920:1080"
        )
        
        cmd = [
            FFMPEG_EXE, "-y",
            "-loop", "1",
            "-i", image_path,
            "-t", str(scene_duration),
            "-vf", filter_complex,
            "-c:v", config.CODEC,
            "-crf", str(config.CRF),
            "-pix_fmt", "yuv420p",
            base_video
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"  Error creating base video: {result.stderr}")
            return None
        
        # Step 4: Add subtitles (WORD-SYNCED SRT)
        video_with_subs = base_video.replace('_base.mp4', '_subs.mp4')
        
        if word_timings:
            print(f"  Adding word-synced subtitles...")
            srt_path = scene_path.replace('.mp4', '.srt')
            self.subtitle_gen.create_word_synced_srt(word_timings, srt_path)
            self.subtitle_gen.burn_subtitles_srt(base_video, srt_path, video_with_subs)
            
            # Cleanup SRT
            if os.path.exists(srt_path):
                os.remove(srt_path)
        else:
            print(f"  Warning: No word timings, skipping subtitles")
            if os.path.exists(base_video):
                os.replace(base_video, video_with_subs)
        
        # Step 5: Add voiceover audio
        if audio_path and os.path.exists(video_with_subs):
            print(f"  Adding voiceover...")
            cmd = [
                FFMPEG_EXE, "-y",
                "-i", video_with_subs,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                scene_path
            ]
            subprocess.run(cmd, capture_output=True)
        else:
            if os.path.exists(video_with_subs):
                os.replace(video_with_subs, scene_path)
        
        # Cleanup temp files
        if os.path.exists(base_video): os.remove(base_video)
        if os.path.exists(video_with_subs): os.remove(video_with_subs)
        
        if os.path.exists(scene_path):
            print(f"✓ Scene {scene_number} created: {scene_path}")
            return scene_path
        else:
            print(f"✗ Failed to create scene {scene_number}")
            return None
    
    def concatenate_scenes(self, scene_paths, output_path):
        """
        Concatenate all scene videos and add background music
        """
        print(f"\nConcatenating {len(scene_paths)} scenes...")
        
        # Create concat file
        concat_file = os.path.join(config.TEMP_DIR, "concat_list.txt")
        with open(concat_file, 'w', encoding='utf-8') as f:
            for path in scene_paths:
                safe_path = path.replace('\\', '/').replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")
        
        # Temp video before adding music
        temp_video = output_path.replace('.mp4', '_temp.mp4')
        
        # Concatenate videos
        cmd = [
            FFMPEG_EXE, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            temp_video
        ]
        
        subprocess.run(cmd, capture_output=True)
        
        # Add overlay video with opacity
        video_with_overlay = temp_video.replace('.mp4', '_overlay.mp4')
        if os.path.exists(config.OVERLAY_VIDEO_PATH):
            print(f"Adding overlay video with {config.OVERLAY_OPACITY} opacity...")
            
            # Apply overlay with opacity using filter_complex
            # [0:v] is main video, [1:v] is overlay
            # scale overlay to match main video size, set opacity, then overlay
            cmd = [
                FFMPEG_EXE, "-y",
                "-i", temp_video,
                "-stream_loop", "-1",  # Loop overlay video
                "-i", config.OVERLAY_VIDEO_PATH,
                "-filter_complex", 
                f"[1:v]scale={config.WIDTH}:{config.HEIGHT},format=rgba,colorchannelmixer=aa={config.OVERLAY_OPACITY}[ovr];[0:v][ovr]overlay=0:0:shortest=1",
                "-c:v", config.CODEC,
                "-crf", str(config.CRF),
                "-c:a", "copy",
                video_with_overlay
            ]
            subprocess.run(cmd, capture_output=True)
            
            # Replace temp_video with overlay version
            if os.path.exists(video_with_overlay):
                os.remove(temp_video)
                os.rename(video_with_overlay, temp_video)
        else:
            print("Warning: Overlay video not found, skipping...")
        
        # Add background music
        if os.path.exists(config.BACKGROUND_MUSIC_PATH):
            print(f"Adding background music: {os.path.basename(config.BACKGROUND_MUSIC_PATH)}")
            
            # Mux voiceover and background music
            # [0:a] is voiceover, [1:a] is background music
            # amix filter mixes them. volume adjustments: voiceover 1.0, background music low
            cmd = [
                FFMPEG_EXE, "-y",
                "-i", temp_video,
                "-i", config.BACKGROUND_MUSIC_PATH,
                "-filter_complex", f"[0:a]volume=1.0[v];[1:a]volume={config.MUSIC_VOLUME}[m];[v][m]amix=inputs=2:duration=first",
                "-c:v", "copy",
                "-c:a", "aac",
                output_path
            ]
            subprocess.run(cmd, capture_output=True)
        else:
            print("Warning: Background music not found, skipping...")
            if os.path.exists(temp_video):
                os.replace(temp_video, output_path)
        
        # Cleanup
        if os.path.exists(temp_video): os.remove(temp_video)
        if os.path.exists(concat_file): os.remove(concat_file)
        
        return output_path
    
    def generate_video(self):
        """Main method to generate the complete video"""
        print("=" * 60)
        print("Epic Stories Video Generator (Male Voice & AI Visuals)")
        print("=" * 60)
        
        # Load story data
        print("\nLoading story data...")
        story = self.load_story_data()
        
        story_title = story.get('video_title', 'Untitled Story')
        scenes = story.get('scenes', [])
        
        print(f"Story: {story_title}")
        print(f"Scenes: {len(scenes)}")
        
        # Create intro
        intro_path = self.create_intro_scene(story_title)
        if intro_path:
            self.scene_videos.append(intro_path)
        
        # Create scene videos
        for scene in scenes:
            scene_number = scene.get('scene_number', len(self.scene_videos))
            scene_path = self.create_scene_video(scene, scene_number)
            
            if scene_path:
                self.scene_videos.append(scene_path)
        
        # Concatenate all scenes
        if self.scene_videos:
            final_output = os.path.join(config.OUTPUT_DIR, "epic_story.mp4")
            final_video = self.concatenate_scenes(self.scene_videos, final_output)
            
            if final_video:
                print("\n" + "=" * 60)
                print(f"SUCCESS! Video generated: {final_video}")
                print("=" * 60)
                return final_video
        
        print("\n✗ Failed to generate video")
        return None


def main():
    parser = argparse.ArgumentParser(description='Generate Epic Stories videos')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    args = parser.parse_args()
    
    try:
        generator = EpicStoriesVideoGenerator()
        video_path = generator.generate_video()
        
        if video_path:
            print(f"\n✓ Video ready: {video_path}")
            return 0
        else:
            print("\n✗ Video generation failed")
            return 1
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
