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

# Add parent directory for youtube_uploader
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
try:
    from youtube_uploader import upload_video, get_authenticated_service
except ImportError:
    # Fallback to current dir or path
    import youtube_uploader
    upload_video = youtube_uploader.upload_video
    get_authenticated_service = youtube_uploader.get_authenticated_service

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
        
        return data

    def remove_story_from_data(self):
        """Remove the first story from the JSON file after successful processing"""
        if not os.path.exists(config.DATA_FILE):
            return
            
        with open(config.DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if isinstance(data, list) and len(data) > 0:
            data.pop(0)
            with open(config.DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            print("✓ Removed processed story from story.json")

    def publish_to_youtube(self, story_data, video_path, thumbnail_path=None):
        """Publish the generated video to YouTube using SEO metadata"""
        metadata = story_data.get('youtube_metadata_for_better_seo', {})
        if not metadata:
            print("  Warning: No YouTube SEO metadata found. Using story defaults.")
            title = story_data.get('video_title', 'Epic Story')
            description = "Emotional Mastery and Wisdom from Epic Stories."
            tags = "motivation,wisdom,story"
        else:
            title = metadata.get('video_title', story_data.get('video_title', 'Epic Story'))
            description = metadata.get('description', '')
            tags_list = metadata.get('50_tags', [])
            hashtags = metadata.get('10_hashtags', [])
            
            # Format description with tags and hashtags specifically as requested
            full_description = f"{description}\n\n"
            full_description += "tags: " + ", ".join(tags_list) + "\n\n"
            full_description += "hashtags: " + " ".join(hashtags)

            tags = ",".join(tags_list)

        print(f"\nPublishing to YouTube: {title}")
        try:
            # Check which channel we are uploading to for CI debugging
            yt_service = get_authenticated_service()
            channel_info = yt_service.channels().list(part="snippet", mine=True).execute()
            if channel_info.get("items"):
                channel_name = channel_info["items"][0]["snippet"]["title"]
                print(f"  Uploading to Channel: {channel_name}")
            
            video_id = upload_video(
                file_path=video_path,
                title=title,
                description=full_description if 'full_description' in locals() else description,
                keywords=tags,
                thumbnail=thumbnail_path,
                privacy_status='private'
            )
            if video_id:
                print(f"✓ Video published successfully! ID: {video_id}")
                return video_id
        except Exception as e:
            print(f"✗ Failed to publish to YouTube: {e}")
        return None
    
    def create_thumbnail_image(self, story_data):
        """
        Generate a standalone high-quality thumbnail image for manual upload.
        """
        print("\n" + "="*40)
        print("GENERATING STANDALONE THUMBNAIL")
        print("="*40)
        
        from PIL import Image
        
        thumbnail_data = story_data.get('youtube_thumbnail', {})
        thumbnail_prompt = thumbnail_data.get('image_prompt', '')
        
        # Prepend global style if not already present
        if hasattr(self, 'global_style') and self.global_style and self.global_style not in thumbnail_prompt:
            thumbnail_prompt = self.global_style + " " + thumbnail_prompt
        
        if not thumbnail_prompt:
            print("  Warning: No thumbnail prompt found. Skipping thumbnail generation.")
            return None
            
        print(f"  Generating AI Thumbnail (Lucid-Origin)...")
        bg_image_path = self.image_gen.generate_image(thumbnail_prompt, "thumbnail", is_thumbnail=True)
        
        if bg_image_path and os.path.exists(bg_image_path):
            img = Image.open(bg_image_path).convert('RGB')
            if img.size != (config.WIDTH, config.HEIGHT):
                img = img.resize((config.WIDTH, config.HEIGHT), Image.LANCZOS)
            
            # Add Logo to Thumbnail
            if os.path.exists(config.LOGO_PATH):
                try:
                    logo = Image.open(config.LOGO_PATH).convert('RGBA')
                    aspect_ratio = logo.height / logo.width
                    logo_h = int(config.LOGO_WIDTH * aspect_ratio)
                    logo = logo.resize((config.LOGO_WIDTH, logo_h), Image.LANCZOS)
                    img.paste(logo, (config.WIDTH - config.LOGO_WIDTH - config.LOGO_PADDING, config.LOGO_PADDING), logo if logo.mode == 'RGBA' else None)
                except: pass
            
            final_path = os.path.join(config.OUTPUT_DIR, "thumbnail.png")
            img.save(final_path)
            
            # Save a YouTube-optimized version (JPEG under 2MB)
            yt_thumbnail_path = os.path.join(config.OUTPUT_DIR, "thumbnail_optimized.jpg")
            quality = 95
            img.save(yt_thumbnail_path, "JPEG", quality=quality, optimize=True)
            
            # Iteratively reduce quality if still over 2MB
            while os.path.getsize(yt_thumbnail_path) > 2 * 1024 * 1024 and quality > 40:
                quality -= 5
                img.save(yt_thumbnail_path, "JPEG", quality=quality, optimize=True)
            
            print(f"✓ Standalone thumbnail saved to: {final_path}")
            print(f"✓ YouTube optimized thumbnail: {yt_thumbnail_path} ({os.path.getsize(yt_thumbnail_path)/1024/1024:.2f} MB)")
            
            # Save as intro_image.png so create_intro_scene uses it as background
            intro_image_path = os.path.join(config.TEMP_DIR, "intro_image.png")
            img.save(intro_image_path)
            
            print(f"✓ Created intro_image.png for video background.")
            return final_path
        return None

    def create_intro_scene(self, story_data):
        """
        Create a high-impact channel intro scene using channel_intro data.
        """
        print("\n" + "="*40)
        print("CREATING CHANNEL INTRO SCENE")
        print("="*40)
        
        intro_data = story_data.get('channel_intro', {})
        bg_prompt = intro_data.get('background_image_notext', '')
        
        # Prepend global style if not already present
        if hasattr(self, 'global_style') and self.global_style and self.global_style not in bg_prompt:
            bg_prompt = self.global_style + " " + bg_prompt
            
        overlay_texts = intro_data.get('overlay_text', [])
        vo_text = intro_data.get('voice_over_text', f"Welcome to All Time Epic Stories. Today's story: {story_data.get('video_title')}")
        
        intro_path = os.path.join(config.TEMP_DIR, "scene_000_intro.mp4")
        
        # Step 1: Generate Voiceover
        print(f"  Generating intro voiceover...")
        audio_path, _ = self.tts_gen.generate_speech(vo_text)
        audio_duration = self.tts_gen.get_audio_duration(audio_path) if audio_path else 5.0
            
        # Step 2: Fetch/Generate Background
        from PIL import Image, ImageDraw, ImageFont
        
        if bg_prompt:
            print(f"  Generating intro background from channel_intro prompt...")
            bg_path = self.image_gen.generate_image(bg_prompt, "intro_bg")
            img = Image.open(bg_path).convert('RGB') if bg_path else Image.new('RGB', (config.WIDTH, config.HEIGHT), color='#0f0f1e')
        else:
            img = Image.new('RGB', (config.WIDTH, config.HEIGHT), color='#0f0f1e')
            
        if img.size != (config.WIDTH, config.HEIGHT):
            img = img.resize((config.WIDTH, config.HEIGHT), Image.LANCZOS)
        
        # Step 3: Add Centered Overlay Text
        if overlay_texts:
            print(f"  Adding centered overlay text...")
            draw = ImageDraw.Draw(img)
            
            def get_font(size):
                try: return ImageFont.truetype("arialbd.ttf", size)
                except: return ImageFont.load_default()
            
            target_width = int(config.WIDTH * 0.8)
            current_font_size = 140
            while current_font_size > 40:
                font = get_font(current_font_size)
                if all((draw.textbbox((0, 0), line, font=font)[2] - draw.textbbox((0, 0), line, font=font)[0]) <= target_width for line in overlay_texts):
                    break
                current_font_size -= 5
            
            font = get_font(current_font_size)
            line_h = int(current_font_size * 1.3)
            y = (config.HEIGHT - (len(overlay_texts) * line_h)) // 2
            
            for line in overlay_texts:
                bbox = draw.textbbox((0, 0), line, font=font)
                w = bbox[2] - bbox[0]
                x = (config.WIDTH - w) // 2
                
                # Shadow
                off = max(2, current_font_size // 25)
                for dx, dy in [(-off,-off), (-off,off), (off,-off), (off,off)]:
                    draw.text((x+dx, y+dy), line, fill='black', font=font)
                
                draw.text((x, y), line, fill='white', font=font)
                y += line_h

        # Step 4: Watermark
        if os.path.exists(config.LOGO_PATH):
            try:
                logo = Image.open(config.LOGO_PATH).convert('RGBA')
                logo_h = int(config.LOGO_WIDTH * (logo.height / logo.width))
                logo = logo.resize((config.LOGO_WIDTH, logo_h), Image.LANCZOS)
                img.paste(logo, (config.WIDTH - config.LOGO_WIDTH - config.LOGO_PADDING, config.LOGO_PADDING), logo if logo.mode == 'RGBA' else None)
            except: pass
        
        intro_img_path = os.path.join(config.TEMP_DIR, "intro_frame.png")
        img.save(intro_img_path)
        
        # Step 5: Render with Zoom
        fps = config.FPS
        num_frames = int(audio_duration * fps)
        render_w, render_h = 4096, 2304
        filter_complex = (
            f"scale={render_w}:{render_h}:force_original_aspect_ratio=decrease,pad={render_w}:{render_h}:(ow-iw)/2:(oh-ih)/2:black,"
            f"zoompan=z='1.0+0.05*on/{num_frames}':d={num_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={render_w}x{render_h}:fps={fps},"
            f"scale=1920:1080:flags=lanczos"
        )
        
        intro_base = intro_path.replace('.mp4', '_base.mp4')
        cmd = [FFMPEG_EXE, "-y", "-i", intro_img_path, "-vf", filter_complex, "-c:v", config.CODEC, "-preset", config.PRESET, "-pix_fmt", "yuv420p", "-r", str(fps), intro_base]
        subprocess.run(cmd, capture_output=True)
        
        if audio_path:
            cmd = [FFMPEG_EXE, "-y", "-i", intro_base, "-i", audio_path, "-c:v", "copy", "-c:a", "aac", "-shortest", intro_path]
            subprocess.run(cmd, capture_output=True)
            return intro_path
        return intro_base
        
        if audio_path:
            return intro_path
        
        return intro_base
    
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
        
        # Prepend global style if not already present
        if hasattr(self, 'global_style') and self.global_style and self.global_style not in image_prompt:
            image_prompt = self.global_style + " " + image_prompt
        
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
        # Padding ensures video is longer than audio to prevent clipping
        process_duration = scene_duration + 0.5
        num_frames = int(process_duration * fps)
        
        # Use frame-index based expressions ('on') to avoid cumulative float errors (jitter)
        if direction == "in":
            # Zoom IN: 1.0 to 1.15
            zoom_expr = f"1.0+0.15*on/{num_frames}"
        else:
            # Zoom OUT: 1.15 to 1.0
            zoom_expr = f"1.15-0.15*on/{num_frames}"
            
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
            
        # 4K+ Supersampling for ultra-smooth zoom (minimizes jitter)
        # We use a single input frame and d={num_frames} for better stability
        render_w, render_h = 4096, 2304
        
        filter_complex = (
            f"scale={render_w}:{render_h}:force_original_aspect_ratio=decrease,"
            f"pad={render_w}:{render_h}:(ow-iw)/2:(oh-ih)/2:black,"
            f"zoompan=z='{zoom_expr}':d={num_frames}:x='{x_expr}':y='{y_expr}':s={render_w}x{render_h}:fps={fps},"
            f"scale=1920:1080:flags=lanczos"
        )
        
        # Sub-pixel movement simulation: 4K+ -> 1080p
        cmd = [
            FFMPEG_EXE, "-y",
            "-threads", "1", # High res processing is memory intensive
            "-i", image_path,
            "-vf", filter_complex,
            "-c:v", config.CODEC,
            "-preset", "ultrafast", # Optimization: use fast preset for the intermediate scene
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            base_video
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"  Error creating base video for scene {scene_number}")
            print(f"  Command: {' '.join(cmd)}")
            print(f"  FFmpeg Error: {result.stderr}")
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
                "-threads", "2",
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
        
        # Add logo watermark
        video_with_logo = temp_video.replace('.mp4', '_logo.mp4')
        if os.path.exists(config.LOGO_PATH):
            print(f"Adding channel logo watermark...")
            
            # Apply logo overlay in top-right with padding
            # [0:v] is main, [1:v] is logo. loop 1 for logo image.
            cmd = [
                FFMPEG_EXE, "-y",
                "-threads", "2",
                "-i", temp_video,
                "-loop", "1", "-i", config.LOGO_PATH,
                "-filter_complex", 
                f"[1:v]scale={config.LOGO_WIDTH}:-1[logo];[0:v][logo]overlay=W-w-{config.LOGO_PADDING}:{config.LOGO_PADDING}:shortest=1",
                "-c:v", config.CODEC,
                "-preset", config.PRESET,
                "-crf", str(config.CRF),
                "-c:a", "copy",
                video_with_logo
            ]
            subprocess.run(cmd, capture_output=True)
            
            # Replace temp_video with logo version
            if os.path.exists(video_with_logo):
                os.remove(temp_video)
                os.rename(video_with_logo, temp_video)
        else:
            print(f"Warning: Logo not found at {config.LOGO_PATH}, skipping...")
        
        # Add background music
        if os.path.exists(config.BACKGROUND_MUSIC_PATH):
            print(f"Adding background music: {os.path.basename(config.BACKGROUND_MUSIC_PATH)}")
            
            # Mux voiceover and background music
            # [0:a] is voiceover, [1:a] is background music
            # amix filter mixes them. volume adjustments: voiceover 1.0, background music low
            cmd = [
                FFMPEG_EXE, "-y",
                "-threads", "2",
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
    
    def clean_cache(self):
        """Clean all cache directories"""
        import shutil
        
        cache_dirs = [
            config.IMAGE_CACHE_DIR,
            config.TTS_CACHE_DIR
        ]
        
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                try:
                    shutil.rmtree(cache_dir)
                    print(f"✓ Cleaned cache: {cache_dir}")
                except Exception as e:
                    print(f"Warning: Could not clean {cache_dir}: {e}")
        
        # Recreate cache directories
        os.makedirs(config.IMAGE_CACHE_DIR, exist_ok=True)
        os.makedirs(config.TTS_CACHE_DIR, exist_ok=True)
        
        # Also clean scene fragment files in temp dir
        for file in os.listdir(config.TEMP_DIR):
            if file.startswith("scene_") or file.endswith(".mp4") or file.endswith(".png"):
                try:
                    os.remove(os.path.join(config.TEMP_DIR, file))
                except:
                    pass
    
    def generate_video(self, test_mode=False):
        """Main method to generate the complete video"""
        print("=" * 60)
        print("Epic Stories Video Generator (Male Voice & AI Visuals)")
        print("=" * 60)
        
        # Clean cache at start for fresh generation
        print("\nCleaning cache for fresh start...")
        self.clean_cache()
        
        # Load story data
        print("\nLoading story data...")
        story_list = self.load_story_data()
        
        if not isinstance(story_list, list) or len(story_list) == 0:
            print("✗ No stories found in story.json")
            return None
            
        # Process ONLY the first story (index 0)
        print("✓ Targeting story at index 0")
        story = story_list[0]
        
        story_title = story.get('video_title', 'Untitled Story')
        scenes = story.get('scenes', [])
        
        print(f"Story: {story_title}")
        print(f"Scenes: {len(scenes)}")
        
        # Store global image style (support both old and new keys)
        self.global_style = story.get('image_style_for_all_images') or story.get('image_style_for_all_images_generate', '')
        if self.global_style:
            print(f"Using global image style: {self.global_style}")
        
        # Step 0: Create Standalone Thumbnail Image
        self.create_thumbnail_image(story)
        
        # Step 1: Create intro
        intro_path = self.create_intro_scene(story)
        if intro_path:
            self.scene_videos.append(intro_path)
        
        # Step 2: Create main story scenes
        scene_counter = 1
        for scene in scenes:
            scene_path = self.create_scene_video(scene, scene_counter)
            if scene_path:
                self.scene_videos.append(scene_path)
            scene_counter += 1
        
        # Step 3: Create video outro scenes
        outro_data = story.get('video_outro', {})
        outro_scenes = outro_data.get('outro_scenes', [])
        if outro_scenes:
            print(f"\nCreating {len(outro_scenes)} outro scenes...")
            for scene in outro_scenes:
                scene_path = self.create_scene_video(scene, scene_counter)
                if scene_path:
                    self.scene_videos.append(scene_path)
                scene_counter += 1
        
        if self.scene_videos:
            final_output = os.path.join(config.OUTPUT_DIR, "epic_story.mp4")
            # Use the optimized JPEG for publishing (<2MB)
            thumbnail_path = os.path.join(config.OUTPUT_DIR, "thumbnail_optimized.jpg")
            # Fallback for old/other systems
            if not os.path.exists(thumbnail_path):
                thumbnail_path = os.path.join(config.OUTPUT_DIR, "thumbnail.png")
                
            final_video = self.concatenate_scenes(self.scene_videos, final_output)
            
            if final_video:
                if not test_mode:
                    # Step 5: Publish to YouTube
                    self.publish_to_youtube(story, final_video, thumbnail_path)
                    
                    # Remove analyzed story from data
                    self.remove_story_from_data()
                else:
                    print("\n[TEST MODE] Skipping YouTube upload and story removal.")

                # Clean cache after successful generation
                print("\nCleaning cache after completion...")
                self.clean_cache()
                print("\n" + "="*60)
                print(f"SUCCESS! Video generated: {final_video}")
                print("="*60)
                return final_video
        
        print("\n✗ Failed to generate video")
        return None


def main():
    print("Starting Main Execution...")
    parser = argparse.ArgumentParser(description='Generate Epic Stories videos')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    args = parser.parse_args()
    
    try:
        generator = EpicStoriesVideoGenerator()
        video_path = generator.generate_video(test_mode=args.test)
        
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
