
import json
import random
import os
import skia
import uharfbuzz as hb
import math
import subprocess
import imageio_ffmpeg
import platform
import sys

# Add parent directory to sys.path to import youtube_uploader
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

import youtube_uploader

# Helper to get paths relative to repo root
def get_root_path(rel_path):
    return os.path.join(parent_dir, rel_path)

# Helper to get paths relative to this script
def get_local_path(rel_path):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), rel_path)

def get_random_shayari(json_file_path):
    """Reads a random shayari from the JSON file."""
    with open(json_file_path, 'r', encoding='utf-8') as f:
        shayaris = json.load(f)
    if not shayaris:
        return None
    return random.choice(shayaris)

def render_hindi_text(canvas, text, font_path, font_size, max_width, start_y, color):
    """
    Renders Hindi text with proper shaping using HarfBuzz and Skia.
    Supports multi-line wrapping.
    """
    with open(font_path, "rb") as f:
        font_data = f.read()
    face = hb.Face(font_data)
    hb_font = hb.Font(face)
    hb_font.scale = (font_size * 64, font_size * 64)
    
    sk_typeface = skia.Typeface.MakeFromFile(font_path)
    sk_font = skia.Font(sk_typeface, font_size)
    sk_paint = skia.Paint(Color=color, AntiAlias=True)
    
    lines = []
    words = text.split(' ')
    current_line_words = []
    
    for word in words:
        test_line = ' '.join(current_line_words + [word])
        # Shape test line to get width
        test_buf = hb.Buffer()
        test_buf.add_str(test_line)
        test_buf.guess_segment_properties()
        hb.shape(hb_font, test_buf, {})
        
        width = sum(p.x_advance for p in test_buf.glyph_positions) / 64.0
        
        if width <= max_width:
            current_line_words.append(word)
        else:
            lines.append(' '.join(current_line_words))
            current_line_words = [word]
    lines.append(' '.join(current_line_words))
    
    curr_y = start_y
    line_height = font_size * 1.4
    
    total_h = len(lines) * line_height
    
    rendered_line_data = [] # (blob, x, y)
    
    for line in lines:
        buf = hb.Buffer()
        buf.add_str(line)
        buf.guess_segment_properties()
        hb.shape(hb_font, buf, {})
        
        glyphs = [info.codepoint for info in buf.glyph_infos]
        positions = []
        
        line_width = sum(p.x_advance for p in buf.glyph_positions) / 64.0
        curr_x = (canvas.getBaseLayerSize().width() - line_width) / 2
        
        for p in buf.glyph_positions:
            off_x = p.x_offset / 64.0
            off_y = p.y_offset / 64.0
            positions.append(skia.Point(curr_x + off_x, curr_y - off_y))
            curr_x += p.x_advance / 64.0
            
        builder = skia.TextBlobBuilder()
        builder.allocRunPos(sk_font, glyphs, positions)
        blob = builder.make()
        rendered_line_data.append((blob, curr_y))
        
        curr_y += line_height
        
    for blob, y in rendered_line_data:
        canvas.drawTextBlob(blob, 0, 0, sk_paint)
        
    return total_h

def create_shayari_image(shayari_data, output_image_path=None):
    """Creates an image with the shayari text centered using Skia."""
    if output_image_path is None:
        output_image_path = get_local_path("temp_shayari_image.png")
    width, height = 720, 1280
    surface = skia.Surface(width, height)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorTRANSPARENT)
    
    font_path = get_root_path(os.path.join("fonts", "TiroDevanagariHindi-Regular.ttf"))
    if not os.path.exists(font_path):
        # Fallback for Windows if bundled not found (unlikely)
        font_path = "C:\\Windows\\Fonts\\Nirmala.ttc"
        
    # Header
    header_paint = skia.Paint(Color=skia.Color(255, 255, 255, 51), AntiAlias=True)
    header_font = skia.Font(skia.Typeface.MakeFromName("Arial"), 25)
    header_blob = skia.TextBlob.MakeFromText("https://www.youtube.com/@Hindi-Shayari-हिंदी-शायरी", header_font)
    canvas.drawTextBlob(header_blob, (width - header_blob.bounds().width())/2, 70, header_paint)
    
    # Shayari and Author
    quote_text = shayari_data["quote"]
    author_text = f"- {shayari_data['author']} -"
    
    # We'll calculate the middle and center vertically
    # First, a dry run or just estimate
    line_height = 45 * 1.4
    lines_estimate = len(quote_text) / 25 # Rough
    total_h_estimate = lines_estimate * line_height + 100 + line_height
    
    start_y = (height - total_h_estimate) / 2
    
    # Render Quote
    actual_h = render_hindi_text(canvas, quote_text, font_path, 45, width - 100, start_y, skia.ColorWHITE)
    
    # Render Author
    author_y = start_y + actual_h + 80
    render_hindi_text(canvas, author_text, font_path, 40, width - 100, author_y, skia.ColorWHITE)
    
    image = surface.makeImageSnapshot()
    image.save(output_image_path, skia.kPNG)
    return output_image_path

def create_video(shayari_data, image_path, output_video_path="daily_shayari_video.mp4", duration=20):
    """Creates a video with background, music, and overlaid image using FFMPEG directly."""
    bg_video_path = get_root_path("light-effect.mp4")
    bg_music_path = get_root_path("background-music.mp3")
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    
    if not os.path.exists(bg_video_path):
        bg_video_path = get_root_path("daily_quote_background_final.mp4")
    
    if not os.path.exists(bg_video_path):
        print(f"Error: Background video not found.")
        return

    has_music = os.path.exists(bg_music_path)
        
    inputs = ["-stream_loop", "-1", "-i", bg_video_path]
    inputs.extend(["-i", image_path])
    
    if has_music:
        inputs.extend(["-stream_loop", "-1", "-i", bg_music_path])
        map_audio = ["-map", "2:a"]
    else:
        map_audio = []
        
    filter_complex = "[0:v]scale=720:1280,setsar=1,format=yuv420p[bg];[bg][1:v]overlay[v_final]"
    
    cmd = [ffmpeg_exe, "-y", "-threads", "1"] + inputs
    cmd.extend(["-filter_complex", filter_complex])
    cmd.extend(["-map", "[v_final]"])
    if map_audio:
        cmd.extend(map_audio)
        
    cmd.extend(["-t", str(duration), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", output_video_path])
    
    subprocess.run(cmd, check=True)

def generate_metadata(shayari_data):
    """Generates YouTube title, description, and keywords."""
    author = shayari_data['author']
    auth_en = shayari_data.get('authnameinenglish', '')
    quote = shayari_data['quote']
    quote_hinglish = shayari_data.get('quoteinhinglish', '')
    
    # Include English name in title if available
    if auth_en:
        title = f"Hindi Shayari - {author} ({auth_en}) | Romantic & Sad Status"
    else:
        title = f"Hindi Shayari - {author} | Romantic & Sad Status"
        
    if len(title) > 100:
        title = title[:97] + "..."
        
    words = ["hindi", "shayari", "status", "love", "sad", "poetry", "ghazal", "shorts", "reels"]
    words.append(author)
    if auth_en:
        words.append(auth_en)
    
    keywords = ",".join(list(set(words))[:30])
    hashtags = "#hindi #shayari #shorts #poetry #status #love #sad"
    
    author_display = f"{author} ({auth_en})" if auth_en else author
    
    description = f"""{quote}
    
{quote_hinglish if quote_hinglish else ""}

- {author_display}

Enjoy this beautiful Hindi Shayari. Subscribe for more daily Shayari status!

{hashtags}
"""
    return title, description, keywords

def remove_from_json(json_file_path, item_to_remove):
    """Removes a specific item from the JSON file after it's been published."""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
        
        updated_items = [i for i in items if i['quote'] != item_to_remove['quote']]
        
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(updated_items, f, indent=4, ensure_ascii=False)
        
        print(f"Item removed. Remaining: {len(updated_items)}")
        return True
    except Exception as e:
        print(f"Error removing from JSON: {e}")
        return False

def main():
    json_path = get_local_path("shayari.json")
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        return

    print("Selecting Shayari...")
    shayari = get_random_shayari(json_path)
    if not shayari:
        print("No shayaris available.")
        return
        
    print("Creating image with Hybrid Rendering...")
    image_path = create_shayari_image(shayari)
    
    print("Creating video...")
    video_output = get_local_path("daily_shayari_video.mp4")
    create_video(shayari, image_path, video_output)
    
    title, description, keywords = generate_metadata(shayari)
    
    print("Starting YouTube Upload...")
    playlist_id = "PL--T8UlYPeg5nqewlcIQ0xR-OVGijhSM0"
    token_path = get_local_path('token_shayari.pickle')
    
    video_id = youtube_uploader.upload_video(video_output, title, description, category_id="22", keywords=keywords, token_file=token_path)
    
    if video_id:
        print("Adding to playlist...")
        try:
            youtube_uploader.add_video_to_playlist(video_id, playlist_id, token_file=token_path)
            print("Successfully added to playlist.")
            remove_from_json(json_path, shayari)
        except Exception as e:
            print(f"Failed to add to playlist: {e}")
    else:
        print("Upload failed.")

    if os.path.exists(image_path):
        os.remove(image_path)

if __name__ == "__main__":
    main()
