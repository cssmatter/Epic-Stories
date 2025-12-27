import json
import os
import requests
from PIL import Image, ImageDraw, ImageFont
import textwrap
import subprocess
import imageio_ffmpeg
import random
import datetime
from gtts import gTTS

# Path helpers
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_FILE = os.path.join(ROOT_DIR, "data", "HiddenOffersDaily", "products.json")
OUTPUT_VIDEO = os.path.join(ROOT_DIR, "hidden_offers_daily_video.mp4")
BG_MUSIC = os.path.join(ROOT_DIR, "assets", "epicstories", "background-music.mp3")

# Font setup
def get_font(size):
    import platform
    system = platform.system()
    try:
        if system == "Windows":
            font_path = "C:\\Windows\\Fonts\\arialbd.ttf" # Bold Arial
        else:
            font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        return ImageFont.truetype(font_path, size)
    except IOError:
        return ImageFont.load_default()

def download_image(url, save_path):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Error downloading image {url}: {e}")
        return False

def create_product_slide(product, index, output_image_path):
    """Creates a 16:9 slide for a product: Left image, Right detailed info."""
    width, height = 1280, 720
    
    # Create background (Modern Navy Gradient)
    bg_color = (15, 23, 42, 255) # Slate 900
    img = Image.new('RGBA', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Download and process product image
    temp_img_path = f"temp_prod_{index}.jpg"
    if download_image(product['image_url'], temp_img_path):
        try:
            prod_img = Image.open(temp_img_path).convert("RGBA")
            # Resize image to fit left half
            max_w, max_h = 550, 600
            prod_img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
            
            img_x = (width // 4) - (prod_img.width // 2)
            img_y = (height // 2) - (prod_img.height // 2)
            
            # Subtle card background for image
            card_padding = 20
            draw.rounded_rectangle(
                [img_x - card_padding, img_y - card_padding, img_x + prod_img.width + card_padding, img_y + prod_img.height + card_padding],
                radius=15, fill=(255, 255, 255, 20)
            )
            
            img.paste(prod_img, (img_x, img_y), prod_img)
        except Exception as e:
            print(f"Error processing image: {e}")
        finally:
            if os.path.exists(temp_img_path):
                os.remove(temp_img_path)
    
    # Text on Right Half
    content_x = width // 2 + 40
    current_y = 60
    text_width_max = 580
    
    # 1. Category Badge
    category_text = product.get('category', 'DEAL').upper()
    cat_font = get_font(20)
    cat_bbox = draw.textbbox((0, 0), category_text, font=cat_font)
    cat_w = cat_bbox[2] - cat_bbox[0]
    draw.rounded_rectangle([content_x, current_y, content_x + cat_w + 20, current_y + 30], radius=5, fill=(56, 189, 248, 255)) # Sky 400
    draw.text((content_x + 10, current_y + 3), category_text, font=cat_font, fill=(255, 255, 255, 255))
    current_y += 50

    # 2. Title
    title_font = get_font(38)
    wrapped_title = textwrap.fill(product['title'], width=35)
    draw.multiline_text((content_x, current_y), wrapped_title, font=title_font, fill=(255, 255, 255, 255), spacing=10)
    title_bbox = draw.multiline_textbbox((content_x, current_y), wrapped_title, font=title_font)
    current_y = title_bbox[3] + 30

    # 3. Prime & Price Row
    price_font = get_font(55)
    draw.text((content_x, current_y), product['price'], font=price_font, fill=(52, 211, 153, 255)) # Emerald 400
    
    if product.get('is_prime'):
        prime_x = content_x + draw.textbbox((0, 0), product['price'], font=price_font)[2] + 20
        # Draw Prime Badge
        draw.rounded_rectangle([prime_x, current_y + 15, prime_x + 80, current_y + 45], radius=5, fill=(0, 168, 225, 255))
        draw.text((prime_x + 10, current_y + 18), "PRIME", font=get_font(20), fill=(255, 255, 255, 255))
    
    current_y += 70

    # 4. Savings
    if product.get('savings') and product.get('savings') != "0":
        savings_text = f"SAVE {product['savings']} ({product['savings_percentage']}%)"
        draw.text((content_x, current_y), savings_text, font=get_font(28), fill=(251, 113, 133, 255)) # Rose 400
        current_y += 50

    # 5. Description (Bullet points)
    desc_font = get_font(22)
    desc_text = product.get('description', '')
    if desc_text:
        current_y += 10
        wrapped_desc = textwrap.fill(desc_text, width=50)
        # Limit to reasonable height
        draw.multiline_text((content_x, current_y), wrapped_desc[:400] + "...", font=desc_font, fill=(200, 200, 200, 255), spacing=8)

    # 6. CTA at bottom
    draw.text((content_x, height - 70), "Link in Description", font=get_font(24), fill=(148, 163, 184, 255)) # Slate 400
    
    img.save(output_image_path, "PNG")

from mutagen.mp3 import MP3

def get_audio_duration(file_path):
    """Gets duration of an audio file using mutagen."""
    try:
        audio = MP3(file_path)
        return float(audio.info.length)
    except Exception as e:
        print(f"Error getting duration with mutagen: {e}")
        return 6.0

def generate_voiceover(product, output_path):
    """Generates a detailed voiceover script and converts to MP3."""
    clean_title = product['title'].split('(')[0].strip() # Remove extra brackets
    category = product.get('category', 'featured').lower()
    price = product['price']
    savings = product.get('savings', 'a significant amount')
    
    # Handle prime text
    prime_text = "This item is Prime eligible with free delivery" if product.get('is_prime') else "Check the link for delivery options"
    
    # Cleanup description (replace \n with space)
    description_summary = product.get('description', '').replace('\n', ' ').strip()
    if not description_summary:
        description_summary = "Check out the full details in the link below"

    # Custom Script from User
    script = f"Today's featured deal: {clean_title}. "
    script += f"From the {category} category, this product is currently available for only {price}, saving you {savings} off the regular price. "
    script += f"{prime_text}. "
    script += f"{description_summary}. "
    script += "If you've been thinking about getting one, now's a great time — deals like this don't last long. "
    script += "Hit the link in the description before the price goes back up."
    
    print(f"Voiceover script: {script}")
    tts = gTTS(text=script, lang='en')
    tts.save(output_path)
    return output_path

def create_video(products):
    if not products:
        print("No products to generate video.")
        return
    
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    
    # Process ONLY the first product as requested
    product = products[0]
    print(f"Creating slide for: {product['title']}")
    
    image_path = "temp_final_slide.png"
    audio_path = "temp_voiceover.mp3"
    create_product_slide(product, 0, image_path)
    
    # Generate Voiceover
    generate_voiceover(product, audio_path)
    audio_duration = get_audio_duration(audio_path)
    video_duration = max(audio_duration + 1.0, 6.0) # Add a small buffer

    # FFMPEG Command for Video + Voiceover + Background Music
    # [1:a] volume=1.0[v_audio]; [2:a] volume=0.1[bg_audio]; [v_audio][bg_audio] amix=inputs=2:duration=first[a_final]
    
    inputs = [
        "-loop", "1", "-t", str(video_duration), "-i", image_path, # Input 0: Image
        "-i", audio_path # Input 1: Voiceover
    ]
    
    has_bg_music = os.path.exists(BG_MUSIC)
    if has_bg_music:
        inputs.extend(["-stream_loop", "-1", "-i", BG_MUSIC]) # Input 2: BG Music
        filter_complex = "[1:a]volume=1.5[v_audio];[2:a]volume=0.15[bg_audio];[v_audio][bg_audio]amix=inputs=2:duration=first[a_final]"
        map_audio = ["-map", "[a_final]"]
    else:
        filter_complex = "[1:a]volume=1.5[a_final]"
        map_audio = ["-map", "[a_final]"]

    cmd = [
        ffmpeg_exe, "-y"
    ] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "0:v",
    ] + map_audio + [
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-c:a", "aac",
        "-shortest",
        OUTPUT_VIDEO
    ]
    
    print(f"Running FFMPEG (Duration: {video_duration}s)...")
    subprocess.run(cmd, check=True)
    
    # Cleanup
    for p in [image_path, audio_path]:
        if os.path.exists(p):
            os.remove(p)
    
    print(f"Video created: {OUTPUT_VIDEO}")

import youtube_uploader

def remove_product_from_json(product_to_remove):
    """Removes a specific product from products.json after successful upload."""
    if not os.path.exists(DATA_FILE):
        return
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            products = json.load(f)
        
        # Filter out the one we just processed (using URL as unique ID)
        remaining = [p for p in products if p['url'] != product_to_remove['url']]
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(remaining, f, indent=4)
        print(f"Product removed. Remaining in queue: {len(remaining)}")
    except Exception as e:
        print(f"Error removing product from JSON: {e}")

def main():
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found. Run fetch script first.")
        return
        
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    if not products:
        print("No products found in data file.")
        return
        
    # Take the first product from the queue
    product = products[0]
    
    # 1. Generate Video
    create_video(products)
    
    # 2. Generate Metadata
    # Title: Product Name - Offer
    offer_text = product.get('savings', 'Featured Deal')
    video_title = f"{product['title'][:70]} - {offer_text}"
    
    # Description: Link \n\n Product Name \n\n Description \n\n Disclosure & Date
    description_cleaned = product.get('description', '').replace('\n', ' ').strip()
    current_date = datetime.datetime.now().strftime("%d/%m/%y")
    disclosure_text = "Disclosures: As an Amazon Associate, I earn from qualifying purchases."
    
    video_description = (
        f"{product['url']}\n\n"
        f"{product['title']}\n\n"
        f"{description_cleaned}\n\n"
        f"{disclosure_text}\n\n"
        f"offer date: {current_date}"
    )
    
    # 3. Upload to YouTube
    print(f"Uploading to YouTube: {video_title}")
    # HiddenOffersDaily Playlist (to be verified by user or updated later)
    # Using a placeholder or the default channel
    try:
        video_id = youtube_uploader.upload_video(
            file_path=OUTPUT_VIDEO,
            title=video_title,
            description=video_description,
            category_id="22", # People & Blogs or 27 for Education
            keywords="Amazon, Deals, Shopping",
            token_file='token_hidden_offers.pickle'
        )
        
        if video_id:
            print(f"Success! Video ID: {video_id}")
            # 4. Remove from JSON
            remove_product_from_json(product)
        else:
            print("Upload failed.")
            
    except Exception as e:
        print(f"YouTube Upload Error: {e}")

if __name__ == "__main__":
    main()
