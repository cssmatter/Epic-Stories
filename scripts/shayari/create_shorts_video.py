import os
import json
import argparse
from pathlib import Path
from moviepy import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, ImageClip, ColorClip

# Reconfigure stdout for Windows console
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def create_shorts_video(json_path: str, mp3_path: str, output_path: str, background_image: str = None):
    # Load lyrics data
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    lyrics = data['lyrics_with_timestamps']
    audio = AudioFileClip(mp3_path)
    duration = audio.duration
    
    # Video settings (YouTube Shorts: 1080x1920)
    width, height = 1080, 1920
    fps = 24
    
    # Create background
    if background_image and os.path.exists(background_image):
        bg_clip = ImageClip(background_image).with_duration(duration).resized(height=height)
        # Center crop to 1080 width if wider
        if bg_clip.w > width:
            bg_clip = bg_clip.cropped(x_center=bg_clip.w/2, width=width)
    else:
        bg_clip = ColorClip(size=(width, height), color=(10, 10, 15)).with_duration(duration)

    clips = [bg_clip]
    
    # Add text clips
    for i, item in enumerate(lyrics):
        start_time = item['timestamp_seconds']
        end_time = item['end_timestamp_seconds']
        text = item['line']
        
        # Ensure end_time doesn't exceed audio duration
        if end_time > duration:
            end_time = duration
            
        if start_time >= duration:
            break

        # Calculate duration for this clip
        clip_duration = end_time - start_time
        if clip_duration <= 0:
            continue
            
        # Create text clip
        # Using a standard font to avoid issues, sizing it for 1080 width
        txt_clip = (TextClip(
                        text=text,
                        font_size=70,
                        color='white',
                        font="Arial-Bold", # common on Windows
                        text_align='center',
                        method='caption',
                        size=(width * 0.8, None)
                    )
                    .with_start(start_time)
                    .with_duration(clip_duration)
                    .with_position(('center', 'center'))
                    .with_effects([
                        lambda clip: clip.with_fadein(0.5).with_fadeout(0.5)
                    ]))
        
        clips.append(txt_clip)

    # Combine everything
    video = CompositeVideoClip(clips, size=(width, height))
    video = video.with_audio(audio)
    
    # Write output
    print(f"🚀 Rendering video to {output_path}...")
    video.write_videofile(output_path, fps=fps, codec='libx264', audio_codec='aac', threads=4)
    print(f"✅ Video saved successfully: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Generate a YouTube Short video from lyrics JSON and MP3.")
    parser.add_argument("--json", required=True, help="Path to the lyrics JSON file")
    parser.add_argument("--mp3", required=True, help="Path to the MP3 audio file")
    parser.add_argument("--output", default="output/short_video.mp4", help="Path to the output MP4 file")
    parser.add_argument("--background", help="Path to a background image")
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    create_shorts_video(args.json, args.mp3, args.output, args.background)

if __name__ == "__main__":
    main()
