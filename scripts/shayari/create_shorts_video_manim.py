#!/usr/bin/env python3
"""
Manim YouTube Shorts Generator
Generates a 9:16 video with synced lyrics and fade effects.
"""

import json
import argparse
import os
import sys
from pathlib import Path
from manim import *

# Fix Windows console encoding for emoji/Unicode characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

class LyricsScene(Scene):
    def construct(self):
        # Access parameters passed via personal settings or command line
        json_path = self.json_path
        mp3_path = self.mp3_path
        
        # Load Lyrics
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        lyrics = data.get("lyrics_with_timestamps", [])
        
        # Add Audio - Disabled in Manim to avoid MemoryError, will mux with ffmpeg later
        # self.add_sound(mp3_path)
        
        # Track current time in the scene
        current_time = 0
        
        import textwrap
        
        for item in lyrics:
            start_s = item["timestamp_seconds"]
            end_s = item["end_timestamp_seconds"]
            line_text = item["line"].strip()
            
            if not line_text:
                continue
                
            duration = end_s - start_s
            
            # Wait until start time
            if start_s > current_time:
                self.wait(start_s - current_time)
                current_time = start_s
            
            # Wrap text (max ~20 chars per line for vertical shorts)
            wrapped_text = "\n".join(textwrap.wrap(line_text, width=22))
            
            # Create Text Mobject with larger font
            text_mob = Text(
                wrapped_text, 
                font="Sans-Serif", 
                font_size=65, # Larger for mobile
                line_spacing=1.2,
                color=WHITE
            )
            
            # Final safety scale if still too wide
            if text_mob.width > config.frame_width * 0.85:
                text_mob.scale_to_fit_width(config.frame_width * 0.85)
                
            text_mob.move_to(ORIGIN)
            
            # Fade In
            fade_in_time = min(0.5, duration / 4)
            self.play(FadeIn(text_mob), run_time=fade_in_time)
            
            # Wait
            wait_time = max(0, duration - (fade_in_time * 2))
            self.wait(wait_time)
            
            # Fade Out
            self.play(FadeOut(text_mob), run_time=fade_in_time)
            
            current_time = end_s

def main():
    parser = argparse.ArgumentParser(description="Generate YouTube Short with Manim")
    parser.add_argument("--json", required=True, help="Path to lyrics JSON")
    parser.add_argument("--mp3", required=True, help="Path to audio MP3")
    parser.add_argument("--output", default="output/short_video.mp4", help="Output video path")
    parser.add_argument("--quality", default="l", choices=["l", "m", "h", "p", "k"], help="Render quality")
    
    args = parser.parse_args()
    
    # Manim Configuration for 9:16 Short
    # Base aspect ratio is 9:16
    aspect_ratio = 9 / 16
    
    # Map quality to pixels (keeping 9:16)
    quality_map = {
        "l": (360, 640),   # 360p equivalent height
        "m": (720, 1280),  # 720p
        "h": (1080, 1920), # 1080p
        "p": (1440, 2560), # 1440p
        "k": (2160, 3840), # 4k
    }
    
    res_w, res_h = quality_map.get(args.quality, (360, 640))
    fps = 15 if args.quality != "l" else 10
    
    # Set quality first (this sets defaults)
    if args.quality == "l":
        config.quality = "low_quality"
    elif args.quality == "m":
        config.quality = "medium_quality"
    elif args.quality == "h":
        config.quality = "high_quality"
        
    # Override defaults for 9:16 and custom resolution
    config.pixel_height = res_h
    config.pixel_width = res_w
    config.frame_height = 16.0
    config.frame_width = 9.0
    config.frame_rate = fps
    config.background_color = "#000000"
    config.output_file = Path(args.output).stem
    
    # Inject paths into the Scene class
    LyricsScene.json_path = args.json
    LyricsScene.mp3_path = args.mp3
    
    # Run Manim
    print(f"[INFO] Rendering Short at {res_w}x{res_h} quality '{args.quality}'...")
    scene = LyricsScene()
    scene.render()
    
    # Final Muxing with ffmpeg
    video_stem = Path(args.output).stem
    # Manim might name it SceneName or output_file
    possible_names = [f"{config.output_file}.mp4", f"{video_stem}.mp4", "LyricsScene.mp4"]
    possible_dirs = [f"{res_h}p{fps}", f"{res_h}p60", f"{res_h}p15", "1080p60", "480p15"]
    
    final_video_path = None
    for d in possible_dirs:
        for name in possible_names:
            test_path = Path("media") / "videos" / d / name
            if test_path.exists():
                final_video_path = test_path
                break
        if final_video_path:
            break
    
    if final_video_path.exists():
        output_file = Path(args.output)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"[Mux] Muxing audio with ffmpeg: {args.mp3} + {final_video_path} -> {args.output}")
        mux_cmd = [
            "ffmpeg", "-y",
            "-i", str(final_video_path),
            "-i", str(args.mp3),
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            str(args.output)
        ]
        
        import subprocess
        try:
            subprocess.run(mux_cmd, check=True)
            print(f"[OK] Final video saved to: {args.output}")
        except subprocess.CalledProcessError as e:
            print(f"(!) Muxing failed: {e}")
            # Move the video anyway as a fallback
            import shutil
            shutil.copy(final_video_path, args.output)
            print(f"(!) Saved video without audio to: {args.output}")
    else:
        print(f"[Error] Could not find rendered video at {final_video_path}")

if __name__ == "__main__":
    main()
