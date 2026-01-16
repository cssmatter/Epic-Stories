
import json
import random
import os
import textwrap
from PIL import Image, ImageDraw, ImageFont
import math
import subprocess
import imageio_ffmpeg
# from moviepy import ImageClip, VideoFileClip, AudioFileClip, CompositeVideoClip, ColorClip, concatenate_videoclips (Unused for now)




# Path helpers for reorganized structure
import sys
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)

import youtube_uploader

def get_data_path(filename):
    return os.path.join(ROOT_DIR, "data", "epicstories", filename)

def get_asset_path(filename):
    return os.path.join(ROOT_DIR, "assets", "epicstories", filename)

def get_output_path(filename):
    return os.path.join(ROOT_DIR, filename)

def get_random_moment(json_file_path):
    """Reads a random moment from the JSON file."""
    with open(json_file_path, 'r', encoding='utf-8') as f:
        moments = json.load(f)
    if not moments:
        return None
    return random.choice(moments)

def create_moment_image(moment_data, output_image_path="temp_moment_image.png"):
    """Creates an image with the moment text centered on a transparent background."""
    # Settings
    width, height = 720, 1280  # YouTube Shorts / Vertical HD (720p to save memory)
    # Transparent background for overlay
    background_color = (0, 0, 0, 0) 
    text_color = (255, 255, 255, 255) # White with full opacity
    
    # Create background
    img = Image.new('RGBA', (width, height), color=background_color)
    draw = ImageDraw.Draw(img)
    
    # Header Text
    header_text = "All Time Epic Stories"
    
    # Cross-platform font setup
    import platform
    system = platform.system()
    
    try:
        # Use our premium Caveat font
        header_font_path = os.path.join(ROOT_DIR, "fonts", "Caveat-Bold.ttf")
        header_font = ImageFont.truetype(header_font_path, 40) # Slightly larger for Caveat
    except IOError:
        print(f"Warning: Could not load font from {header_font_path}, using default")
        header_font = ImageFont.load_default()
    
    # Opacity 0.2 (approx 51/255)
    header_color = (255, 255, 255, 51) 
    
    # Position: Top Center (y=70)
    draw.text((width/2, 70), header_text, font=header_font, fill=header_color, anchor="ma")
    
    # Font setup for moment and author (question)
    try:
        font_path = os.path.join(ROOT_DIR, "fonts", "Caveat-Bold.ttf")
        font_size = 75  # Handwriting fonts need to be much larger for readability
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        print(f"Warning: Could not load font from {font_path}, using default")
        # If font loading fails, use a larger default size
        font = ImageFont.load_default()
        font_size = 50  # Keep size consistent even with default font
    
    moment_text = f'"{moment_data["quote"]}"'
    author_text = f"- {moment_data['author']} -"
    
    # Text wrapping
    char_width_approx = font_size * 0.5 
    max_chars_per_line = int((width - 140) / char_width_approx)
    
    wrapped_moment = textwrap.fill(moment_text, width=max_chars_per_line)
    
    # Calculate text positions
    moment_bbox = draw.textbbox((0, 0), wrapped_moment, font=font)
    moment_h = moment_bbox[3] - moment_bbox[1]
    
    author_gap = 100
    author_bbox = draw.textbbox((0, 0), author_text, font=font)
    author_h = author_bbox[3] - author_bbox[1]
    
    total_text_height = moment_h + author_gap + author_h
    current_y = (height - total_text_height) // 2
    
    # Draw Moment
    draw.multiline_text((width/2, current_y), wrapped_moment, font=font, fill=text_color, anchor="ma", align="center")
    
    # Draw Author/Question
    current_y += moment_h + author_gap
    draw.text((width/2, current_y), author_text, font=font, fill=text_color, anchor="ma")
    
    img.save(output_image_path, "PNG")
    return output_image_path

def create_video(moment_data, image_path, output_video_path="daily_moments_video.mp4", duration=10):
    """Creates a video with background, music, and overlaid image using FFMPEG directly."""
    
    # Assets
    bg_video_path = get_asset_path("light-effect.mp4")
    bg_music_path = get_asset_path("background-music.mp3")
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    
    # Check assets
    if not os.path.exists(bg_video_path):
        print(f"Error: {bg_video_path} not found.")
        return # Cannot proceed without background

    if not os.path.exists(bg_music_path):
        print(f"Warning: {bg_music_path} not found.")
        has_music = False
    else:
        has_music = True
        
    print("Building FFMPEG command...")
    
    # Inputs
    inputs = []
    
    # Input 0: Pre-processed Background Video (already 20s, dark)
    inputs.extend(["-stream_loop", "-1", "-i", bg_video_path])
    
    # Input 1: Text Image
    inputs.extend(["-i", image_path])
    
    # Input 2: Audio
    if has_music:
        inputs.extend(["-stream_loop", "-1", "-i", bg_music_path])
        map_audio = ["-map", "2:a"]
    else:
        map_audio = []
        
    # Filter Complex: Scale BG to 720x1280, then Overlay
    # [0:v]scale=720:1280,setsar=1[bg];[bg][1:v]overlay[v_final]
    filter_complex = "[0:v]scale=720:1280,setsar=1,format=yuv420p[bg];[bg][1:v]overlay[v_final]"
    
    # Assemble Command
    cmd = [ffmpeg_exe, "-y", "-threads", "1"] + inputs
    
    cmd.extend(["-filter_complex", filter_complex])
    cmd.extend(["-map", "[v_final]"])
    if map_audio:
        cmd.extend(map_audio)
        
    cmd.extend(["-t", str(duration), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", output_video_path])
    
    print(f"Running FFMPEG: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

def generate_metadata(moment_data):
    """Generates YouTube title, description, and keywords."""
    author = moment_data['author']
    quote = moment_data['quote']
    category = moment_data.get('category', 'Story Moments')
    
    # Title: Category - Question/Author
    title = f"{category} - {author}"
    if len(title) > 100:
        title = title[:97] + "..."
        
    # Keywords / Hashtags
    words = [w.strip(".,!?;:\"") for w in quote.split() if len(w) > 3]
    words.append(author)
    words.append(category)
    words.extend(["shorts", "moments", "story", "emotional", "life", "inspiration", "dailyvideo"])
    
    keywords = ",".join(list(set(words))[:30])
    
    hashtags = " ".join([f"#{w.replace(' ', '')}" for w in words[:15]])
    
    description = f"""{quote}

- {author}

Category: {category}

{hashtags}

#shorts #moments #story #emotional #life #{category.replace(' ', '')} #reels #reel #trending
"""
    # Save metadata for Instagram
    metadata = {
        "title": title,
        "description": description.strip(),
        "keywords": keywords,
        "hashtags": hashtags
    }
    with open(get_output_path("instagram_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)
        
    return title, description, keywords

def remove_moment_from_json(json_file_path, moment_to_remove):
    """Removes a specific moment from the JSON file after it's been published."""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            moments = json.load(f)
        
        # Filter out the published moment
        updated_moments = [m for m in moments if m['quote'] != moment_to_remove['quote'] or m['author'] != moment_to_remove['author']]
        
        # Save the updated list back to the file
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(updated_moments, f, indent=4, ensure_ascii=False)
        
        print(f"Moment removed from {json_file_path}. Remaining moments: {len(updated_moments)}")
        return True
    except Exception as e:
        print(f"Error removing moment from JSON: {e}")
        return False

def main():
    json_path = get_data_path("moments.json")
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        return

    print("Selecting moment...")
    moment = get_random_moment(json_path)
    if not moment:
        print("No moments available. All moments have been published!")
        print("Please add more moments to moments.json to continue.")
        return
    print(f"Selected: {moment['quote'][:30]}...")

    print("Creating image...")
    image_path = create_moment_image(moment)
    
    print("Creating video...")
    video_output = get_output_path("daily_moments_video.mp4")
    create_video(moment, image_path, video_output)
    
    print("Video created successfully.")
    
    # Metadata
    title, description, keywords = generate_metadata(moment)
    
    print("\n--- YouTube Metadata ---")
    print(f"Title: {title}")
    print(f"Description:\n{description}")
    print(f"Keywords: {keywords}")
    print("------------------------\n")
    
    # Upload to YouTube
    print("Starting YouTube Upload...")
    # Playlist ID for moments
    playlist_id = "PLzBjRj37QV5DDKAG_U6bMuWh4ULkYqJGu"
    
    video_id = youtube_uploader.upload_video(video_output, title, description, category_id="27", keywords=keywords)
    
    if video_id:
        print("Adding to playlist...")
        try:
            youtube_uploader.add_video_to_playlist(video_id, playlist_id)
            print("Successfully added to playlist.")
            
            # Remove the published moment from JSON
            print("Removing published moment from JSON...")
            remove_moment_from_json(json_path, moment)
            
        except Exception as e:
            print(f"Failed to add to playlist: {e}")
    else:
        print("Upload failed, skipping playlist addition.")

    if os.path.exists(image_path):
        os.remove(image_path)

if __name__ == "__main__":
    main()
