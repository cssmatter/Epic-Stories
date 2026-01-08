import os
import sys
import json
import requests
import datetime
import time

# Add root to python path to import youtube_uploader
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT_DIR)

import youtube_uploader

# Configuration
DATA_FILE = os.path.join(ROOT_DIR, "data", "DevotionalHindiQuotes", "data.json")
VIDEO_FILE = os.path.join(ROOT_DIR, "devotional_hindi_quote.mp4")
BACKGROUND_IMAGE = os.path.join(ROOT_DIR, "assets", "devotional_hindi", "current_bg.png")
TOKEN_FILE_YOUTUBE = os.path.join(ROOT_DIR, "token_devotional.pickle")

# Instagram Token (Ideally from env var for security, but hardcoded as per prompt for now or env var in CI)
INSTAGRAM_ACCESS_TOKEN = os.environ.get("BHAKTIDAILY_INSTAGRAM_TOKEN", "EAAc4XxpI2FYBQTJcczyPV64UM2mPrDTbQYMR2HwQ8YfRk2pI3nxY6bzvQKswiZAECUJSInGhFDrYy63YEZBu6fupnjKAZB8TDCDgFas9JuUAc2nuqYrObNOsIpckTKpamsMTU32KLHnIHSE0tqCgAvTG5nbOUTZBrT6FJq5N1y3YheYMCSp4ZASBp2Qh8ohdIbAZDZD")
INSTAGRAM_USER_ID = "me" # Or specific Page ID if "me" doesn't work with this token type, usually it's Page ID

def load_first_quote():
    if not os.path.exists(DATA_FILE):
        print("Data file not found.")
        return None
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not data:
        print("Data file is empty.")
        return None
    return data[0]

def remove_processed_quote():
    """Removes the first item (Index 0) from data.json."""
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if data:
        removed = data.pop(0)
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n[CLEANUP] Removed processed quote '{removed.get('verse_number')}' from data.json.")
    
    # Remove assets
    if os.path.exists(BACKGROUND_IMAGE):
        os.remove(BACKGROUND_IMAGE)
        print("[CLEANUP] Removed background image.")
    # We might want to keep the video for debug, or delete it? 
    # Usually in CI we delete, but locally maybe keep. 
    # Let's keep the video file for now or delete if in CI.
    if os.environ.get("GITHUB_ACTIONS") and os.path.exists(VIDEO_FILE):
        os.remove(VIDEO_FILE)
        print("[CLEANUP] Removed video file.")

def generate_social_metadata(quote_data):
    hook = quote_data.get("hook_text", "")
    verse = quote_data.get("verse_number", "")
    quote_sans = quote_data.get("quote_hindi_sansrikt", "")
    meaning = quote_data.get("meaning_simple_hindi", "")
    cta = quote_data.get("cta", "")
    channel = quote_data.get("channel_name", "") # unused in text body if purely handle
    category = quote_data.get("category", "Bhagavad Gita")
    
    # Title
    # User Request: category + verse_number + hook_text
    title = f"{category} | {verse} | {hook} #Shorts"
    
    # Ensure it fits 100 char limit
    if len(title) > 100:
        # Try removing category length if too long
        title = f"{verse} | {hook} #Shorts"
        
    # Hashtags
    hashtags = "#Hinduism #BhagavadGita #Krishna #Motivation #Spiritual #DailyWisdom #Shorts #HInduQuotes #SanatanaDharma"
    
    # Description / Caption
    description = f"""{hook}

{quote_sans}

{meaning}

{cta}

{hashtags}
"""
    return title, description, category

# --- Instagram Logic ---

def upload_to_instagram(video_path, caption):
    """
    Uploads video to Instagram by first hosting on catbox.moe, then using Graph API.
    """
    print("\n--- Starting Instagram Upload ---")
    if not os.path.exists(video_path):
        print("Video file not found for Instagram.")
        return False
        
    try:
        # Step 1: Upload to temporary public host (catbox.moe)
        print("Uploading to temporary host for public URL...")
        files = {'fileToUpload': open(video_path, 'rb')}
        data = {'reqtype': 'fileupload'}
        
        response = requests.post('https://catbox.moe/user/api.php', files=files, data=data, timeout=120)
        video_url = response.text.strip()
        
        if not video_url.startswith('http'):
            print(f"Error: Failed to get public URL. Response: {video_url}")
            return False
            
        print(f"Public Video URL: {video_url}")
        
        # Step 2: Use Instagram Graph API
        sys.path.insert(0, ROOT_DIR)
        from instagram_graph_uploader import InstagramGraphUploader
        
        # Get Instagram Business ID from env (different from "me")
        instagram_id = os.environ.get("IG_BUSINESS_ID", INSTAGRAM_USER_ID)
        
        uploader = InstagramGraphUploader(INSTAGRAM_ACCESS_TOKEN, instagram_id)
        success = uploader.upload_reel(video_url, caption)
        
        if success:
            print("Instagram upload successful!")
            return True
        else:
            print("Instagram upload failed.")
            return False
            
    except Exception as e:
        print(f"Error uploading to Instagram: {e}")
        import traceback
        traceback.print_exc()
        return False

def upload_to_facebook(video_path, caption):
    """
    Uploads video to Facebook Reels (or Video) using binary upload.
    This works from local/CI without needing a public URL hosting!
    """
    print("\n--- Starting Facebook Reel Upload ---")
    if not os.path.exists(video_path):
        print("Video file not found for Facebook.")
        return False
        
    url = f"https://graph-video.facebook.com/v18.0/{INSTAGRAM_USER_ID}/videos"
    
    payload = {
        'access_token': INSTAGRAM_ACCESS_TOKEN,
        'description': caption,
        # 'is_reel': 'true', # Optional, often auto-detected or treated as video
    }
    
    # Binary upload
    files = {
        'source': open(video_path, 'rb')
    }
    
    try:
        print("Uploading binary to Facebook Graph API...")
        response = requests.post(url, data=payload, files=files, timeout=120)
        
        if response.status_code == 200:
            print(f"Facebook Upload Success! ID: {response.json().get('id')}")
            return True
        else:
            print(f"Facebook Upload Failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error uploading to Facebook: {e}")
        return False
    finally:
        files['source'].close()

def upload_to_youtube(video_path, quote_data):
    print("\n--- Starting YouTube Upload ---")
    if not os.path.exists(video_path):
        print("Video file not found.")
        return

    title, description, category = generate_social_metadata(quote_data)
    
    print(f"Title: {title}")
    
    # Authenticate (Logic in youtube_uploader uses token.pickle)
    # We need to ensure youtube_uploader uses OUR token file
    
    # Upload
    video_id = youtube_uploader.upload_video(video_path, title, description, category_id="27", keywords="bhakti,krishna,gita", token_file=TOKEN_FILE_YOUTUBE)
    
    if video_id:
        print(f"Uploaded to YouTube: {video_id}")
        
        # Playlist Management
        playlist_name = category.split("-")[0].strip() # e.g. "Srimad Bhagavad Gita" from "Category - Sub"
        if not playlist_name:
            playlist_name = "Devotional Wisdom"
            
        print(f"Managing Playlist: {playlist_name}")
        playlist_id = youtube_uploader.get_or_create_playlist(playlist_name, token_file=TOKEN_FILE_YOUTUBE)
        if playlist_id:
            youtube_uploader.add_video_to_playlist(video_id, playlist_id, token_file=TOKEN_FILE_YOUTUBE)
        
        return True
    return False

def main():
    # 1. Load Data
    quote_data = load_first_quote()
    if not quote_data:
        print("No quote data found. Exiting.")
        return

    # 2. Upload YouTube
    success_yt = upload_to_youtube(VIDEO_FILE, quote_data)
    
    # 3. Upload Instagram & Facebook
    _, caption, _ = generate_social_metadata(quote_data)
    
    # Instagram (Using catbox.moe hosting + Graph API)
    success_ig = upload_to_instagram(VIDEO_FILE, caption)
    
    # Facebook Reel (Uses same token)
    success_fb = upload_to_facebook(VIDEO_FILE, caption)
    
    # 4. Cleanup (Only if at least one upload succeeds)
    if success_yt or success_fb or success_ig:
        remove_processed_quote()
    else:
        print("Uploads failed. Skipping cleanup to preserve data.")

if __name__ == "__main__":
    main()
