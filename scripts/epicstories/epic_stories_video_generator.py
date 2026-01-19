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

# Parse arguments early to determine which config to use
parser = argparse.ArgumentParser(description='Generate Epic Stories videos')
parser.add_argument('--test', action='store_true', help='Run in test mode with lower resolution for faster processing')
args, unknown = parser.parse_known_args()

# Import appropriate config based on test mode
if args.test:
    import config_test as config
    print("*** TEST MODE: Using reduced resolution (1080p, 30fps) for faster processing ***")
else:
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

            # Pass full tags list (uploader now handles sanitization)
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
        imageid = thumbnail_data.get('imageid', '')
        thumbnail_prompt = thumbnail_data.get('image_prompt', '')
        
        bg_image_path = None
        self.thumbnail_source_path_to_delete = None
        
        # Priority 1: Use Local Thumbnail (search in Assets first, then Temp)
        if imageid:
            search_dirs = [
                os.path.join(config.ASSETS_DIR, "thumbnails"),
                os.path.join(config.TEMP_DIR, "thumbnails")
            ]
            
            print(f"  Searching for thumbnail matching ID: {imageid}...")
            
            for thumbnails_dir in search_dirs:
                if not os.path.exists(thumbnails_dir):
                    continue
                    
                print(f"    Checking {thumbnails_dir}...")
                for f in os.listdir(thumbnails_dir):
                    if f.startswith(imageid):
                        potential_path = os.path.join(thumbnails_dir, f)
                        try:
                            valid_img = Image.open(potential_path)
                            valid_img.verify()
                            bg_image_path = potential_path
                            self.thumbnail_source_path_to_delete = bg_image_path
                            print(f"  ✓ Found source thumbnail: {bg_image_path}")
                            break
                        except:
                            continue
                if bg_image_path:
                    break
            
            if not bg_image_path:
                print(f"  Info: No local thumbnail found for ID {imageid} (checked {len(search_dirs)} locations). Falling back to generation.")

        # Priority 2: Fallback to AI Generation
        if not bg_image_path:
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
        
        # Handle case where channel_intro is just a string name
        if isinstance(intro_data, str):
            bg_prompt = '' # Use default intro image
            overlay_texts = [intro_data]
            vo_text = f"Welcome to {intro_data}."
            if story_data.get('title') or story_data.get('video_title'):
                vo_text += f" Today's story: {story_data.get('title') or story_data.get('video_title')}"
        else:
            bg_prompt = intro_data.get('background_image_notext', '')
            overlay_texts = intro_data.get('overlay_text', [])
            vo_text = intro_data.get('voice_over_text', f"Welcome to All Time Epic Stories. Today's story: {story_data.get('video_title')}")
        # SIMPLIFIED INTRO: Use Thumbnail Only + Voiceover (No Text, No AI Gen)
        # We rely on 'intro_image.png' which creates_thumbnail_image saved earlier
        
        intro_img_path = os.path.join(config.TEMP_DIR, "intro_image.png")
        if not os.path.exists(intro_img_path):
             print("  Warning: intro_image.png not found, trying to use thumbnail...")
             # Fallback logic if needed, but intro_image.png should exist
        
        # Load image for processing (e.g. Watermark)
        from PIL import Image
        try:
            img = Image.open(intro_img_path).convert('RGB')
        except Exception as e:
            print(f"  Error loading intro image: {e}")
            return None

        # (Text Overlay Logic Removed at User Request)
        
        intro_path = os.path.join(config.TEMP_DIR, "scene_000_intro.mp4")
        
        # Step 1: Generate Voiceover
        print(f"  Generating intro voiceover...")
        audio_path, _ = self.tts_gen.generate_speech(vo_text)
        audio_duration = self.tts_gen.get_audio_duration(audio_path) if audio_path else 5.0
            
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
        
        # [NEW] Add 1s padding to ensure voiceover completes fully
        process_duration = audio_duration + config.SCENE_PADDING
        num_frames = int(process_duration * fps)
        
        # Render at high resolution for supersampling (smooth zoom)
        # For 4K (3840), 1.1x = 4224 (approx 12M pixels per frame)
        # For 1080p (1920), 1.25x = 2400
        zoom_mult = 1.1 if config.WIDTH >= 3840 else 1.25
        render_w = int(config.WIDTH * zoom_mult)
        if render_w > 4800: render_w = 4800 # Sane cap for 4K+
        render_h = int(config.HEIGHT * (render_w / config.WIDTH))
        
        # Ensure even dimensions
        if render_w % 2 != 0: render_w += 1
        if render_h % 2 != 0: render_h += 1
        
        # CRITICAL FIX: Since we use -loop 1 on input, we MUST use d=1 in zoompan
        # Otherwise it duplicates frames (d*{num_frames}) causing massive output files and hangs.
        # [ADD] fps={fps} ensures input stream matches output density before zoompan.
        # [ADD] setpts=N/FRAME_RATE/TB ensures flawlessly monotonic timestamps.
        filter_complex = (
            f"fps={fps},"
            f"scale={render_w}:{render_h}:force_original_aspect_ratio=decrease,pad={render_w}:{render_h}:(ow-iw)/2:(oh-ih)/2:black,"
            f"zoompan=z='1.0+0.05*on/{num_frames}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={render_w}x{render_h}:fps={fps},"
            f"setpts=N/FRAME_RATE/TB,"
            f"scale={config.WIDTH}:{config.HEIGHT}:flags=lanczos"
        )
        
        intro_base = intro_path.replace('.mp4', '_base.mp4')
        # Use -loop 1 to treat image as a stream for zoompan
        cmd = [
            FFMPEG_EXE, "-y", 
            "-loglevel", "error", # Prevent log buffer hangs
            "-threads", "1", 
            "-loop", "1", 
            "-t", str(process_duration), 
            "-i", intro_img_path, 
            "-vf", filter_complex, 
            "-c:v", config.CODEC, 
            "-preset", "ultrafast", # Use fastest for intermediate
            "-pix_fmt", "yuv420p", 
            "-r", str(fps), 
            intro_base
        ]
        
        # Use binary capture for robustness
        result = subprocess.run(cmd, capture_output=True)
        
        if result.returncode != 0:
            print(f"  Error creating intro base video")
            try:
                print(f"  FFmpeg Error: {result.stderr.decode('utf-8', errors='replace')[:500]}")
            except: pass
            return None
        
        if audio_path:
            # Combine base and audio. We REMOVE -shortest to allow the padding to play.
            cmd = [
                FFMPEG_EXE, "-y", 
                "-loglevel", "error",
                "-threads", "1", 
                "-i", intro_base, 
                "-i", audio_path, 
                "-c:v", "copy", 
                "-c:a", "aac", 
                intro_path
            ]
            subprocess.run(cmd, capture_output=True)
            if os.path.exists(intro_base): 
                try: os.remove(intro_base)
                except: pass
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
        
        # Step 3: Scene Setup (Intermediates & Zoom)
        base_video = scene_path.replace('.mp4', '_base.mp4')
        direction = "in" if scene_number % 2 != 0 else "out"
        fps = config.FPS
        process_duration = scene_duration + config.SCENE_PADDING
        num_frames = int(process_duration * fps)
        
        if direction == "in":
            zoom_expr = f"1.0+0.15*on/{num_frames}"
        else:
            zoom_expr = f"1.15-0.15*on/{num_frames}"
            
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
            
        zoom_mult = 1.1 if config.WIDTH >= 3840 else 1.25
        render_w = int(config.WIDTH * zoom_mult)
        if render_w > 4800: render_w = 4800 
        render_h = int(config.HEIGHT * (render_w / config.WIDTH))
        if render_w % 2 != 0: render_w += 1
        if render_h % 2 != 0: render_h += 1
        
        # CRITICAL FIX: Since we use -loop 1 on input, we MUST use d=1 in zoompan
        # Otherwise it duplicates frames (d*{num_frames}) causing massive output files and hangs.
        # [ADD] fps={fps} ensures input stream matches output density before zoompan.
        # [ADD] setpts=N/FRAME_RATE/TB ensures flawlessly monotonic timestamps for subtitle/sync.
        filter_complex = (
            f"fps={fps},"
            f"scale={render_w}:{render_h}:force_original_aspect_ratio=decrease,"
            f"pad={render_w}:{render_h}:(ow-iw)/2:(oh-ih)/2:black,"
            f"zoompan=z='{zoom_expr}':d=1:x='{x_expr}':y='{y_expr}':s={render_w}x{render_h}:fps={fps},"
            f"setpts=N/FRAME_RATE/TB,"
            f"scale={config.WIDTH}:{config.HEIGHT}:flags=lanczos"
        )
        
        # Step 4: Add subtitles (WORD-SYNCED SRT)
        # We generate the SRT first so we can include it in the single-pass render
        sub_filter = None
        if word_timings:
            print(f"  Preparing word-synced subtitles...")
            srt_path = scene_path.replace('.mp4', '.srt')
            self.subtitle_gen.create_word_synced_srt(word_timings, srt_path)
            sub_filter = self.subtitle_gen.get_subtitles_filter(srt_path)
        
        # Build filter chain for single-pass render
        final_vf = filter_complex
        if sub_filter:
            final_vf += f",{sub_filter}"
            
        print(f"  Rendering base video with zoom and subtitles...")
        cmd = [
            FFMPEG_EXE, "-y",
            "-loglevel", "error", # Prevent buffer fill hangs
            "-threads", "1", # High res processing is memory intensive
            "-loop", "1", "-t", str(process_duration), 
            "-i", image_path,
            "-vf", final_vf,
            "-c:v", config.CODEC,
            "-preset", "ultrafast", # Optimization: use fast preset for the intermediate scene
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            base_video
        ]
        
        # Use binary capture for robustness
        result = subprocess.run(cmd, capture_output=True)
        
        if result.returncode != 0:
            print(f"  Error creating base video for scene {scene_number}")
            try:
                err_text = result.stderr.decode('utf-8', errors='replace')
                print(f"  FFmpeg Error: {err_text[:800]}")
            except:
                print("  FFmpeg Error: (Could not decode output)")
            return None
        
        # Cleanup SRT (if it was created)
        srt_path = scene_path.replace('.mp4', '.srt')
        if os.path.exists(srt_path):
            try: os.remove(srt_path)
            except: pass

        # Skip Step 4 (already integrated) and keep video_with_subs pointer
        video_with_subs = base_video
        
        # Step 5: Add voiceover audio
        # Combine video (with subs) and audio
        if audio_path:
            # Check if we have video_with_subs (might be base_video)
            input_video = video_with_subs if os.path.exists(video_with_subs) else base_video
            
            print(f"  Adding voiceover...")
            cmd = [
                FFMPEG_EXE, "-y",
                "-loglevel", "error",
                "-threads", "1",
                "-i", input_video,
                "-i", audio_path,
                "-c:v", "copy", # Video already encoded in Base or Subs step
                "-c:a", "aac",
                scene_path
            ]
            subprocess.run(cmd, capture_output=True)
        else:
            # Fallback if no audio
            input_video = video_with_subs if os.path.exists(video_with_subs) else base_video
            if os.path.exists(input_video):
                # Copy to scene_path
                import shutil
                shutil.copy(input_video, scene_path)
        
        # Cleanup temp files
        if os.path.exists(base_video) and base_video != scene_path: 
            try: os.remove(base_video)
            except: pass

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
            "-loglevel", "error",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            temp_video
        ]
        
        subprocess.run(cmd, capture_output=True)
        
        # FINAL PASS: Combine Overlays, Logo, and Background Music into ONE encoding step
        # This is a massive optimization: 1 encode instead of 3.
        
        print(f"Starting final render (Overlays + Logo + Music)...")
        
        # Prepare inputs
        inputs = ["-i", temp_video] # Input 0
        filter_parts = []
        
        current_v = "[0:v]"
        current_a = "[0:a]"
        
        input_idx = 1
        
        # 1. & 2. Overlays
        if os.path.exists(config.OVERLAY_VIDEO_PATH) and os.path.exists(config.CLOUDS_VIDEO_PATH):
            inputs.extend(["-stream_loop", "-1", "-i", config.OVERLAY_VIDEO_PATH]) # Input 1
            inputs.extend(["-stream_loop", "-1", "-i", config.CLOUDS_VIDEO_PATH])  # Input 2
            
            filter_parts.append(f"[{input_idx}:v]scale={config.WIDTH}:{config.HEIGHT},format=rgba,colorchannelmixer=aa={config.OVERLAY_OPACITY}[ov1]")
            filter_parts.append(f"[{input_idx+1}:v]scale={config.WIDTH}:{config.HEIGHT},format=rgba,colorchannelmixer=aa={config.CLOUDS_OPACITY}[ov2]")
            filter_parts.append(f"{current_v}[ov1]overlay=0:0:shortest=1[tmp_v1]")
            filter_parts.append(f"[tmp_v1][ov2]overlay=0:0:shortest=1[tmp_v2]")
            current_v = "[tmp_v2]"
            input_idx += 2
            
        # 3. Logo
        if os.path.exists(config.LOGO_PATH):
            inputs.extend(["-loop", "1", "-i", config.LOGO_PATH]) # Input N
            filter_parts.append(f"[{input_idx}:v]scale={config.LOGO_WIDTH}:-1[logo_scaled]")
            filter_parts.append(f"{current_v}[logo_scaled]overlay=W-w-{config.LOGO_PADDING}:{config.LOGO_PADDING}:shortest=1[tmp_v3]")
            current_v = "[tmp_v3]"
            input_idx += 1
            
        # 4. Music
        if os.path.exists(config.BACKGROUND_MUSIC_PATH):
            inputs.extend(["-i", config.BACKGROUND_MUSIC_PATH]) # Input N
            # amix: input 0:a is voiceover, input N:a is music
            filter_parts.append(f"{current_a}volume=1.0[vo];[{input_idx}:a]volume={config.MUSIC_VOLUME}[bgm];[vo][bgm]amix=inputs=2:duration=first[a_final]")
            current_a = "[a_final]"
            input_idx += 1
        
        # Assemble command
        # Using [v] and [a] as intermediate labels for clarity and parsing safety
        filter_str = " ; ".join(filter_parts)
        
        cmd = [FFMPEG_EXE, "-y", "-loglevel", "error", "-threads", "1"] + inputs + [
            "-filter_complex", filter_str,
            "-map", current_v,
            "-map", current_a,
            "-c:v", config.CODEC,
            "-preset", config.PRESET,
            "-crf", str(config.CRF),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            output_path
        ]
        
        print(f"  Executing: {' '.join(cmd)}")
        
        # Run final render
        result = subprocess.run(cmd, capture_output=True)
        
        if result.returncode != 0:
            print(f"✗ Final render failed!")
            try:
                err = result.stderr.decode('utf-8', errors='replace')
                # Log both start (config issues) and end (processing issues)
                print(f"  FFmpeg Error (Start):\n{err[:800]}")
                print(f"  FFmpeg Error (Tail):\n{err[-800:]}")
            except: pass
            # Fallback: Just return the temp video if production fails
            # (better than nothing, though it will lack effects)
            if os.path.exists(temp_video):
                os.replace(temp_video, output_path)
                return output_path
            return None

        # Success - Cleanup temp
        if os.path.exists(temp_video): 
            try: os.remove(temp_video)
            except: pass
        if os.path.exists(concat_file): 
            try: os.remove(concat_file)
            except: pass
        
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
        
        # DEBUG: Log the description that will be used
        metadata = story.get('youtube_metadata_for_better_seo', {})
        desc_preview = metadata.get('description', story.get('video_description', 'No description found - Using Default'))
        print(f"  PROCESSING STORY INDEX 0: {story_title}")
        print(f"  DESCRIPTION PREVIEW: {desc_preview[:100]}...")

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
            if test_mode and scene_counter > 5:
                print("  Test Mode: Stopping after 5 scenes to save time.")
                break
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
                if test_mode and scene_counter > 2:
                    break
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
                    video_id = self.publish_to_youtube(story, final_video, thumbnail_path)
                    
                    if video_id:
                        # Remove analyzed story from data ONLY if upload succeeded
                        self.remove_story_from_data()
                        
                        # Cleanup source thumbnail if it was a temp file from thumbnails directory
                        if hasattr(self, 'thumbnail_source_path_to_delete') and self.thumbnail_source_path_to_delete:
                            if os.path.exists(self.thumbnail_source_path_to_delete):
                                try:
                                    os.remove(self.thumbnail_source_path_to_delete)
                                    print(f"✓ Removed used thumbnail source: {self.thumbnail_source_path_to_delete}")
                                except Exception as e:
                                    print(f"Warning: Failed to remove thumbnail source: {e}")
                    else:
                        print("✗ YouTube upload failed. STORY NOT REMOVED FROM QUEUE for retry.")
                        return None
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
