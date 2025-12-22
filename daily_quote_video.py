
import json
import random
import os
import textwrap
from PIL import Image, ImageDraw, ImageFont
import math
import subprocess
import imageio_ffmpeg
# from moviepy import ImageClip, VideoFileClip, AudioFileClip, CompositeVideoClip, ColorClip, concatenate_videoclips (Unused for now)


import youtube_uploader

def get_random_quote(json_file_path):
    """Reads a random quote from the JSON file."""
    with open(json_file_path, 'r', encoding='utf-8') as f:
        quotes = json.load(f)
    if not quotes:
        return None
    return random.choice(quotes)

def create_quote_image(quote_data, output_image_path="temp_quote_image.png"):
    """Creates an image with the quote text centered on a transparent background."""
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
        if system == "Windows":
            header_font_path = "C:\\Windows\\Fonts\\times.ttf"
        else:  # Linux/Ubuntu (GitHub Actions)
            header_font_path = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
        header_font = ImageFont.truetype(header_font_path, 30)
    except IOError:
        print(f"Warning: Could not load font from {header_font_path}, using default")
        header_font = ImageFont.load_default()
    
    # Opacity 0.2 (approx 51/255)
    header_color = (255, 255, 255, 51) 
    
    # Position: Top Center (y=70)
    draw.text((width/2, 70), header_text, font=header_font, fill=header_color, anchor="ma")
    
    # Font setup for quote and author
    try:
        if system == "Windows":
            font_path = "C:\\Windows\\Fonts\\times.ttf"
        else:  # Linux/Ubuntu (GitHub Actions)
            font_path = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
        font_size = 50  # Consistent font size for 720p
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        print(f"Warning: Could not load font from {font_path}, using default")
        # If font loading fails, use a larger default size
        font = ImageFont.load_default()
        font_size = 50  # Keep size consistent even with default font
    
    quote_text = f'"{quote_data["quote"]}"'
    author_text = f"- {quote_data['author']} -"
    
    # Text wrapping
    char_width_approx = font_size * 0.5 
    max_chars_per_line = int((width - 140) / char_width_approx)
    
    wrapped_quote = textwrap.fill(quote_text, width=max_chars_per_line)
    
    # Calculate text positions
    quote_bbox = draw.textbbox((0, 0), wrapped_quote, font=font)
    quote_h = quote_bbox[3] - quote_bbox[1]
    
    author_gap = 100
    author_bbox = draw.textbbox((0, 0), author_text, font=font)
    author_h = author_bbox[3] - author_bbox[1]
    
    total_text_height = quote_h + author_gap + author_h
    current_y = (height - total_text_height) // 2
    
    # Draw Quote
    draw.multiline_text((width/2, current_y), wrapped_quote, font=font, fill=text_color, anchor="ma", align="center")
    
    # Draw Author
    current_y += quote_h + author_gap
    draw.text((width/2, current_y), author_text, font=font, fill=text_color, anchor="ma")
    
    img.save(output_image_path, "PNG")
    return output_image_path
import subprocess
import imageio_ffmpeg

# ... imports ...

def create_video(quote_data, image_path, output_video_path="daily_quote_video.mp4", duration=20):
    """Creates a video with background, music, and overlaid image using FFMPEG directly."""
    
    # Assets
    bg_video_path = "daily_quote_background_final.mp4"
    bg_music_path = "background-music.mp3"
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
    inputs.extend(["-i", bg_video_path])
    
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
    filter_complex = "[0:v]scale=720:1280,setsar=1[bg];[bg][1:v]overlay[v_final]"
    
    # Assemble Command
    cmd = [ffmpeg_exe, "-y", "-threads", "1"] + inputs
    
    cmd.extend(["-filter_complex", filter_complex])
    cmd.extend(["-map", "[v_final]"])
    if map_audio:
        cmd.extend(map_audio)
        
    cmd.extend(["-t", str(duration), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", output_video_path])
    
    print(f"Running FFMPEG: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)



def generate_metadata(quote_data):
    """Generates YouTube title, description, and keywords."""
    author = quote_data['author']
    quote = quote_data['quote']
    
    # Title: Author Quote (e.g., "Epictetus Quote")
    title = f"{author} Quote"
        
    # Keywords / Hashtags
    words = [w.strip(".,!?;:\"") for w in quote.split() if len(w) > 3]
    words.append(author)
    words.extend(["shorts", "motivation", "wisdom", "stoic", "philosophy", "dailyquote", "inspiration"])
    
    keywords = ",".join(list(set(words))[:30])
    
    hashtags = " ".join([f"#{w.replace(' ', '')}" for w in words[:15]])
    
    description = f"""{quote}

- {author}

{hashtags}

#shorts #motivation #inspiration #stoicism #reels #reel #trending
"""
    # Save metadata for Instagram
    metadata = {
        "title": title,
        "description": description.strip(),
        "keywords": keywords,
        "hashtags": hashtags
    }
    with open("instagram_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)
        
    return title, description, keywords

def remove_quote_from_json(json_file_path, quote_to_remove):
    """Removes a specific quote from the JSON file after it's been published."""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            quotes = json.load(f)
        
        # Filter out the published quote
        updated_quotes = [q for q in quotes if q['quote'] != quote_to_remove['quote'] or q['author'] != quote_to_remove['author']]
        
        # Save the updated list back to the file
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(updated_quotes, f, indent=4, ensure_ascii=False)
        
        print(f"Quote removed from {json_file_path}. Remaining quotes: {len(updated_quotes)}")
        return True
    except Exception as e:
        print(f"Error removing quote from JSON: {e}")
        return False

def main():
    json_path = "quotes.json"
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        return

    print("Selecting quote...")
    quote = get_random_quote(json_path)
    if not quote:
        print("No quotes available. All quotes have been published!")
        print("Please add more quotes to quotes.json to continue.")
        return
    print(f"Selected: {quote['quote'][:30]}...")

    print("Creating image...")
    image_path = create_quote_image(quote)
    
    print("Creating video...")
    video_output = "daily_quote_video.mp4"
    create_video(quote, image_path, video_output)
    
    print("Video created successfully.")
    
    # Metadata
    title, description, keywords = generate_metadata(quote)
    
    print("\n--- YouTube Metadata ---")
    print(f"Title: {title}")
    print(f"Description:\n{description}")
    print(f"Keywords: {keywords}")
    print("------------------------\n")
    
    # Upload to YouTube (Optional based on flag or user intent? 
    # Original script performed upload. I'll keep it but comment it out or put it at end, 
    # but the user didn't explicitly asking to STOP uploading, just to ADD features.
    # However, uploading automatically might be risky if they just want to test generation.
    # I will perform the upload if youtube_uploader module is present and configured, 
    # matching previous behavior but perhaps confirming first? 
    # The previous script did `youtube_uploader.upload_video`. I will keep it.)
    
    # Upload to YouTube
    print("Starting YouTube Upload...")
    # Playlist ID: Daily Status Shorts
    playlist_id = "PLzBjRj37QV5Ap8LhjV7O7Rl2W6xFWZI4W"
    
    video_id = youtube_uploader.upload_video(video_output, title, description, category_id="27", keywords=keywords)
    
    if video_id:
        print("Adding to playlist...")
        try:
            youtube_uploader.add_video_to_playlist(video_id, playlist_id)
            print("Successfully added to playlist.")
            
            # Remove the published quote from JSON
            print("Removing published quote from JSON...")
            remove_quote_from_json(json_path, quote)
            
        except Exception as e:
            print(f"Failed to add to playlist: {e}")
    else:
        print("Upload failed, skipping playlist addition.")

    if os.path.exists(image_path):
        os.remove(image_path)

if __name__ == "__main__":
    main()
