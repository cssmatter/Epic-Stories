import os
import sys
import json
import subprocess

# Add root to python path to import youtube_uploader
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT_DIR)

import youtube_uploader

# Configuration
DATA_FILE = os.path.join(ROOT_DIR, "data", "BookSummariesChannel", "data.json")
OUTPUT_DIR = os.path.join(ROOT_DIR, "output", "book_summaries")
TOKEN_FILE_YOUTUBE = os.path.join(ROOT_DIR, "token_book_summaries.pickle")

def load_book_data():
    """Load the first book from data.json"""
    if not os.path.exists(DATA_FILE):
        print("Data file not found.")
        return None
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not data:
        print("Data file is empty.")
        return None
    return data[0]

def get_video_duration(video_path):
    """Get video duration using ffprobe"""
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception as e:
        print(f"Error getting video duration: {e}")
        return 0

def format_timestamp(seconds):
    """Convert seconds to MM:SS or HH:MM:SS format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

def generate_long_video_metadata(book_data, video_path):
    """Generate metadata for the long-form video"""
    yt_meta = book_data.get('youtube_metadata', {})
    chapters = book_data.get('chapters', [])
    intro = book_data.get('channel_intro', {})
    
    # Title
    title = yt_meta.get('title', 'Book Summary')
    
    # Description
    affiliate_link = yt_meta.get('affiliate_link', '')
    short_desc = yt_meta.get('short_description', '')
    tags = yt_meta.get('tags', [])
    
    # Build description
    description_parts = []
    
    # Title + Affiliate Link
    if affiliate_link:
        description_parts.append(f"{title}")
        description_parts.append(f"Get the book: {affiliate_link}")
    else:
        description_parts.append(f"{title}")
    
    description_parts.append("")
    
    # Short description
    if short_desc:
        description_parts.append(short_desc)
        description_parts.append("")
    
    # Timestamps
    ts_file = os.path.join(OUTPUT_DIR, "timestamps.json")
    if os.path.exists(ts_file):
        try:
            with open(ts_file, 'r', encoding='utf-8') as f:
                timestamps = json.load(f)
            
            if timestamps:
                description_parts.append("TIMESTAMPS:")
                for ts in timestamps:
                    formatted_time = format_timestamp(ts.get('time', 0))
                    label = ts.get('label', 'Chapter')
                    description_parts.append(f"{formatted_time} {label}")
                description_parts.append("")
        except Exception as e:
            print(f"[WARNING] Error reading timestamps: {e}")
            # Fallback
            description_parts.append("TIMESTAMPS:")
            description_parts.append("00:00 Introduction")
            description_parts.append("")
    else:
        # Fallback
        description_parts.append("TIMESTAMPS:")
        description_parts.append("00:00 Introduction")
        description_parts.append("")
    
    # Tags as hashtags
    if tags:
        tag_line = " ".join([f"#{tag.replace(' ', '')}" for tag in tags[:10]])  # First 10 tags
        description_parts.append(tag_line)
    
    description_parts.append("")
    description_parts.append("#books #book")
    
    description = "\n".join(description_parts)
    
    # Keywords
    keywords = ",".join(tags[:15]) if tags else ""
    
    return title, description, keywords

def generate_short_video_metadata(book_data):
    """Generate metadata for the short-form video"""
    screentext = book_data.get('screentext', {})
    
    # Title
    title = screentext.get('original_title', 'Book Summary Short')
    
    # Description
    original_title = screentext.get('original_title', '')
    author = screentext.get('author', '')
    
    description_parts = []
    if original_title and author:
        description_parts.append(f"{original_title} by {author}")
    elif original_title:
        description_parts.append(original_title)
    
    description_parts.append("")
    description_parts.append("#shorts #trending #book")
    
    description = "\n".join(description_parts)
    
    return title, description

def upload_long_video(book_data):
    """Upload the long-form video to YouTube"""
    print("\n=== UPLOADING LONG VIDEO ===")
    
    yt_meta = book_data.get('youtube_metadata', {})
    screentext = book_data.get('screentext', {})
    
    # Find the video file
    title_slug = screentext.get('original_title', 'book').replace(' ', '_')
    video_path = os.path.join(OUTPUT_DIR, f"{title_slug}.mp4")
    
    # Try alternative naming
    if not os.path.exists(video_path):
        # Look for any .mp4 file that's not a short
        for file in os.listdir(OUTPUT_DIR):
            if file.endswith('.mp4') and '_short' not in file:
                video_path = os.path.join(OUTPUT_DIR, file)
                break
    
    if not os.path.exists(video_path):
        print(f"Video file not found: {video_path}")
        return False
    
    print(f"Video file: {video_path}")
    
    # Generate metadata
    title, description, keywords = generate_long_video_metadata(book_data, video_path)
    
    print(f"Title: {title}")
    print(f"Description preview: {description[:200]}...")
    
    # Upload to YouTube
    thumbnail_id = book_data.get('screentext', {}).get('thumbnail_id')
    thumbnail_path = None
    if thumbnail_id:
        test_path = os.path.join(ROOT_DIR, "assets", "book_summaries", "thumb", f"{thumbnail_id}.jpg")
        if os.path.exists(test_path):
            thumbnail_path = test_path
            print(f"Thumbnail found: {thumbnail_path}")

    video_id = youtube_uploader.upload_video(
        video_path,
        title,
        description,
        category_id="27",  # Education category
        keywords=keywords,
        token_file=TOKEN_FILE_YOUTUBE,
        thumbnail=thumbnail_path,
        privacy_status="public"  # Set to public for launch
    )
    
    if video_id:
        print(f"[SUCCESS] Long video uploaded! Video ID: {video_id}")
        print(f"   URL: https://www.youtube.com/watch?v={video_id}")
        
        # Add to playlist based on category
        category = yt_meta.get('category', 'Book Summaries')
        print(f"Managing playlist: {category}")
        try:
            playlist_id = youtube_uploader.get_or_create_playlist(category, token_file=TOKEN_FILE_YOUTUBE)
            if playlist_id:
                youtube_uploader.add_video_to_playlist(video_id, playlist_id, token_file=TOKEN_FILE_YOUTUBE)
                print(f"[SUCCESS] Added to playlist: {category}")
        except Exception as e:
            print(f"[WARNING] Playlist management failed: {e}")
        
        return True
    else:
        print("[FAILED] Long video upload failed")
        return False

def upload_short_video(book_data):
    """Upload the short-form video to YouTube"""
    print("\n=== UPLOADING SHORT VIDEO ===")
    
    screentext = book_data.get('screentext', {})
    
    # Find the short video file
    title_slug = screentext.get('original_title', 'book').replace(' ', '_')
    video_path = os.path.join(OUTPUT_DIR, f"{title_slug}_short.mp4")
    
    # Try alternative naming
    if not os.path.exists(video_path):
        # Look for any .mp4 file with 'short' in the name
        for file in os.listdir(OUTPUT_DIR):
            if file.endswith('.mp4') and 'short' in file:
                video_path = os.path.join(OUTPUT_DIR, file)
                break
    
    if not os.path.exists(video_path):
        print(f"Short video file not found: {video_path}")
        return False
    
    print(f"Video file: {video_path}")
    
    # Generate metadata
    title, description = generate_short_video_metadata(book_data)
    
    print(f"Title: {title}")
    print(f"Description: {description}")
    
    # Upload to YouTube
    video_id = youtube_uploader.upload_video(
        video_path,
        title,
        description,
        category_id="27",  # Education category
        keywords="shorts,book,summary",
        token_file=TOKEN_FILE_YOUTUBE,
        privacy_status="public"  # Set to public for launch
    )
    
    if video_id:
        print(f"[SUCCESS] Short video uploaded! Video ID: {video_id}")
        print(f"   URL: https://www.youtube.com/shorts/{video_id}")
        return True
    else:
        print("[FAILED] Short video upload failed")
        return False

def main():
    # Load book data
    book_data = load_book_data()
    if not book_data:
        print("No book data found. Exiting.")
        return
    
    # Upload both videos
    long_success = upload_long_video(book_data)
    short_success = upload_short_video(book_data)
    
    if long_success and short_success:
        print("\n[SUCCESS] Both videos uploaded successfully!")
        print("   Videos are set to PRIVATE. Review them in YouTube Studio before publishing.")
        
        # --- POST-UPLOAD CLEANUP ---
        screentext = book_data.get('screentext', {})
        title_slug = screentext.get('original_title', 'book').replace(' ', '_')
        long_video_path = os.path.join(OUTPUT_DIR, f"{title_slug}.mp4")
        short_video_path = os.path.join(OUTPUT_DIR, f"{title_slug}_short.mp4")

        # 1. Cleanup timestamps file
        ts_file = os.path.join(OUTPUT_DIR, "timestamps.json")
        if os.path.exists(ts_file):
            os.remove(ts_file)
            print(f"Temporary file {ts_file} deleted.")

        # 2. Delete Final Video Files
        # Use find logic if slug naming failed
        if not os.path.exists(long_video_path):
             for file in os.listdir(OUTPUT_DIR):
                if file.endswith('.mp4') and '_short' not in file:
                    long_video_path = os.path.join(OUTPUT_DIR, file)
                    break
        
        if os.path.exists(long_video_path):
            os.remove(long_video_path)
            print(f"Long video deleted: {long_video_path}")
        
        if not os.path.exists(short_video_path):
            for file in os.listdir(OUTPUT_DIR):
                if file.endswith('.mp4') and '_short' in file:
                    short_video_path = os.path.join(OUTPUT_DIR, file)
                    break

        if os.path.exists(short_video_path):
            os.remove(short_video_path)
            print(f"Short video deleted: {short_video_path}")

        # 3. Delete Thumbnail
        thumbnail_id = book_data.get('screentext', {}).get('thumbnail_id')
        if thumbnail_id:
            thumb_path = os.path.join(ROOT_DIR, "assets", "book_summaries", "thumb", f"{thumbnail_id}.jpg")
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
                print(f"Thumbnail deleted: {thumb_path}")

        # 3. Remove first object from data.json
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                current_data = json.load(f)
            
            if current_data:
                print(f"Removing processed book: {current_data[0].get('screentext', {}).get('original_title')}")
                current_data.pop(0)
                
                with open(DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(current_data, f, indent=4)
                print(f"Updated data.json (remaining items: {len(current_data)})")
        except Exception as e:
            print(f"[ERROR] Failed to update data.json: {e}")

    elif long_success or short_success:
        print("\n[WARNING] Partial success - one video uploaded. Cleanup skipped to allow manual retry.")
    else:
        print("\n[FAILED] Upload failed for both videos")

if __name__ == "__main__":
    main()
