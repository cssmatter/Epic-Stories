
import json
import random
import os
import textwrap
from PIL import Image, ImageDraw, ImageFont
import subprocess
import imageio_ffmpeg
import sys
import time

# Path helpers for reorganized structure
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)

import youtube_uploader
from instagram_graph_uploader import InstagramGraphUploader

def get_data_path(filename):
    return os.path.join(ROOT_DIR, "data", "godisgreatest", filename)

def get_asset_path(filename):
    # Reusing epicstories assets as requested/implied
    return os.path.join(ROOT_DIR, "assets", "epicstories", filename)

def get_output_path(filename):
    return os.path.join(ROOT_DIR, filename)

def get_random_entry(json_file_path):
    """Reads a random entry from the JSON file."""
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not data:
        return None
    return random.choice(data)

def create_message_image(entry_data, output_image_path="temp_god_message_image.png"):
    """Creates an image with the quote text and CTA centered on a transparent background."""
    width, height = 720, 1280
    background_color = (19, 20, 45, 180) # Dark Navy/Blackish Blue
    text_color = (255, 255, 255, 255) # White
    
    img = Image.new('RGBA', (width, height), color=background_color)
    draw = ImageDraw.Draw(img)
    
    # Header Text
    header_text = "God Is Greatest"
    
    import platform
    system = platform.system()
    
    try:
        if system == "Windows":
            font_path = "C:\\Windows\\Fonts\\times.ttf"
        else:
            font_path = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
        
        header_font = ImageFont.truetype(font_path, 35)
        quote_font = ImageFont.truetype(font_path, 55)
        cta_font = ImageFont.truetype(font_path, 45)
    except IOError:
        print("Warning: Could not load font, using default")
        header_font = ImageFont.load_default()
        quote_font = ImageFont.load_default()
        cta_font = ImageFont.load_default()
    
    # Header: Top Center
    header_color = (255, 255, 255, 80) # Slightly more visible than 0.2
    draw.text((width/2, 100), header_text, font=header_font, fill=header_color, anchor="ma")
    
    quote_text = entry_data["quote_text"]
    cta_text = entry_data["cta"]
    
    # Wrap Quote
    max_chars_quote = 25
    wrapped_quote = textwrap.fill(quote_text, width=max_chars_quote)
    
    # Wrap CTA if long
    max_chars_cta = 30
    wrapped_cta = textwrap.fill(cta_text, width=max_chars_cta)
    
    # Calculate positions
    # Quote in the middle
    draw.multiline_text((width/2, height/2 - 50), wrapped_quote, font=quote_font, fill=text_color, anchor="mm", align="center", spacing=20)
    
    # CTA below quote
    draw.multiline_text((width/2, height/2 + 200), wrapped_cta, font=cta_font, fill=(255, 215, 0, 255), anchor="mm", align="center", spacing=15) # Gold color for CTA
    
    img.save(output_image_path, "PNG")
    return output_image_path

def create_video(image_path, output_video_path="daily_god_message_video.mp4", duration=12):
    """Creates a video with background, music, and overlaid image."""
    bg_video_path = get_asset_path("daily_quote_background_final.mp4")
    bg_music_path = get_asset_path("background-music.mp3")
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    
    if not os.path.exists(bg_video_path):
        print(f"Error: {bg_video_path} not found.")
        return False

    has_music = os.path.exists(bg_music_path)
    
    inputs = ["-i", bg_video_path, "-i", image_path]
    if has_music:
        inputs.extend(["-stream_loop", "-1", "-i", bg_music_path])
        map_audio = ["-map", "2:a"]
    else:
        map_audio = []
        
    filter_complex = "[0:v]scale=720:1280,setsar=1[bg];[bg][1:v]overlay[v_final]"
    
    cmd = [ffmpeg_exe, "-y", "-threads", "1"] + inputs
    cmd.extend(["-filter_complex", filter_complex])
    cmd.extend(["-map", "[v_final]"])
    if map_audio:
        cmd.extend(map_audio)
        
    cmd.extend(["-t", str(duration), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", output_video_path])
    
    subprocess.run(cmd, check=True)
    return True

def generate_metadata(entry_data):
    quote = entry_data["quote_text"]
    
    # Original hashtags + JSON hashtags
    original_hashtags = ["#GodIsGreatest", "#Faith", "#Shorts", "#Christianity", "#God", "#Hope", "#Prayer"]
    json_hashtags = entry_data.get("hashtags", [])
    all_hashtags = list(set(original_hashtags + json_hashtags))
    hashtags_str = " ".join(all_hashtags)
    
    # Original keywords + JSON keywords
    original_keywords = ["God", "Jesus", "Faith", "Devotional", "Shorts", "Motivation"]
    json_keywords = entry_data.get("seo_keywords", [])
    all_keywords = list(set(original_keywords + json_keywords))
    keywords_str = ",".join(all_keywords)
    
    description = f"{entry_data['description']}\n\n{hashtags_str}\n\n#shorts #trending #godmessage"
    title = f"{quote[:50]}..." if len(quote) > 50 else quote
    
    # Save metadata for Instagram
    metadata = {
        "title": title,
        "description": description.strip(),
        "keywords": keywords_str,
        "hashtags": hashtags_str
    }
    metadata_path = os.path.join(ROOT_DIR, "godisgreatest_metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)
        
    return title, description, keywords_str

def remove_entry_from_json(json_file_path, entry_to_remove):
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        updated_data = [e for e in data if e['quote_text'] != entry_to_remove['quote_text']]
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(updated_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error updating JSON: {e}")
        return False

def main():
    json_path = get_data_path("data.json")
    token_file = os.path.join(ROOT_DIR, 'token_godisgreatest.pickle')
    
    # 1. Get Entry
    entry = get_random_entry(json_path)
    if not entry:
        print("No entries available.")
        return

    # 2. Create Video
    print("Generating video...")
    image_path = create_message_image(entry)
    video_output = get_output_path("daily_god_message_video.mp4")
    if not create_video(image_path, video_output):
        return

    # 3. Metadata
    title, description, keywords = generate_metadata(entry)
    playlist_name = entry.get("playlist", "God Is Greatest")

    # 4. Upload to YouTube
    print("Uploading to YouTube...")
    video_id = youtube_uploader.upload_video(video_output, title, description, category_id="27", keywords=keywords, token_file=token_file)
    
    if video_id:
        playlist_id = youtube_uploader.get_or_create_playlist(playlist_name, token_file=token_file)
        youtube_uploader.add_video_to_playlist(video_id, playlist_id, token_file=token_file)
        remove_entry_from_json(json_path, entry)
        print("YouTube Upload Success!")
    
    # 5. Instagram Note
    print("\nNote: Instagram upload is handled by the GitHub Actions workflow using instagram_graph_uploader.py.")
    
    if os.path.exists(image_path):
        os.remove(image_path)

if __name__ == "__main__":
    main()
