import os
import sys
import json

# Force UTF-8 encoding for stdout to handle emojis
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add root to python path to import youtube_uploader
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT_DIR)

import youtube_uploader

# Configuration
DATA_FILE = os.path.join(ROOT_DIR, "data", "viralCourses", "data.json")
VIDEO_FILE = os.path.join(ROOT_DIR, "output", "viralCourses", "viral_course_video_fast.mp4")
THUMBNAIL_FILE = os.path.join(ROOT_DIR, "output", "viralCourses", "thumbnail.png")
TOKEN_FILE_YOUTUBE = os.path.join(ROOT_DIR, "token_viral_courses.pickle")

def load_data():
    if not os.path.exists(DATA_FILE):
        print(f"Data file not found: {DATA_FILE}")
        return None
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not data:
        print("Data file is empty.")
        return None
    return data[0]

def generate_metadata(asset_data, timestamps=None):
    meta = asset_data["video_assets"]["youtube_metadata"]
    asset_titles = asset_data["video_assets"].get("titles", [])
    
    # Get title
    title = meta.get("youtubetitle", "Viral Course Video")
    # Truncate to 100 chars
    if len(title) > 100:
        title = title[:97] + "..."

    # Extract course title
    course_title = asset_titles[0] if asset_titles else None
    course_link = meta.get("courselink", "")
    desc_main = meta.get("description", "")
    hashtags = " ".join(meta.get("hashtags", []))
    keywords = meta.get("keywords", [])
    keywords_str = ", ".join(keywords) if isinstance(keywords, list) else keywords
    google_search = meta.get("mostsearchedongoogle", "")
    
    # Tags
    tags_str_raw = meta.get("tags", "")
    tags = [t.strip() for t in tags_str_raw.split(",")]
    if keywords:
        if isinstance(keywords, list):
            tags.extend([str(k).strip() for k in keywords])
        else:
            tags.extend([k.strip() for k in keywords.split(",")])
            
    # Deduplicate tags and limit
    tags = list(set([t for t in tags if t]))[:40]
    
    # Alternative titles string for description
    titles_str = "\n".join([f"• {t}" for t in asset_titles if t])

    # Build clean description
    description_parts = []
    
    # Course link (first)
    if course_link:
        description_parts.append(f"📚 Practice Exam Questions and Answers: {course_link}")
        description_parts.append("")
    
    # Main description
    if desc_main:
        description_parts.append(desc_main)
        description_parts.append("")
    
    # Timestamps
    if timestamps:
        description_parts.append("\n".join(timestamps))
        description_parts.append("")
    
    # Alternative titles
    if titles_str:
        description_parts.append("📌 Related Topics:")
        description_parts.append(titles_str)
        description_parts.append("")
    
    # Search queries
    if google_search:
        description_parts.append(f"🔍 {google_search}")
        description_parts.append("")
    
    # Hashtags at the end
    if hashtags:
        description_parts.append(hashtags)
    
    description = "\n".join(description_parts)
    
    # Handle description limit (5000 chars total, user wants 4600 limit with truncation)
    if len(description) > 4600:
        description = description[:4597] + "..."
    
    return title, description, tags, meta.get("category", "27"), course_title

def upload_viral_video():
    print("\n--- Starting Viral Course YouTube Upload ---")
    
    # 1. Check Video
    if not os.path.exists(VIDEO_FILE):
        print(f"Error: Video file not found at {VIDEO_FILE}")
        print("Please run viral_courses_fast.py first.")
        return

    # 2. Load Data
    data = load_data()
    if not data: return

    # 3. Load Timestamps
    timestamps = []
    timestamps_file = os.path.join(ROOT_DIR, "output", "viralCourses", "timestamps.json")
    if os.path.exists(timestamps_file):
        try:
            with open(timestamps_file, 'r', encoding='utf-8') as f:
                timestamps = json.load(f)
            print(f"Loaded {len(timestamps)} timestamps.")
        except Exception as e:
            print(f"Error loading timestamps: {e}")

    # 4. Generate Metadata
    title, description, tags, category_id, course_title = generate_metadata(data, timestamps)
    
    print(f"Title: {title}")
    print(f"Description Preview:\n{description[:100]}...")
    print(f"Tags: {tags}")

    # 4. Upload
    video_id = youtube_uploader.upload_video(
        VIDEO_FILE, 
        title, 
        description, 
        category_id="27", # Education
        keywords=",".join(tags),
        token_file=TOKEN_FILE_YOUTUBE,
        thumbnail=THUMBNAIL_FILE,
        course_title=course_title
    )
    
    if video_id:
        video_url = f"https://youtu.be/{video_id}"
        print(f"Upload Success! Video ID: {video_id}")
        
        # --- Community Post Helper ---
        print("\n" + "="*50)
        print("📢 COMMUNITY POST TEMPLATE (Copy & Paste)")
        print("="*50)
        print(f"New Course Video is LIVE! 🎓\n")
        print(f"📺 {title}\n")
        print(f"Watch the full video here 👇")
        print(f"{video_url}\n")
        print(f"Please like and subscribe for more free courses! 📚")
        print("="*50 + "\n")
        

        
        # 5. Cleanup Data
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                full_data = json.load(f)
            
            if len(full_data) > 0:
                removed_item = full_data.pop(0)
                print(f"Removed uploaded item: {removed_item.get('video_assets', {}).get('youtube_metadata', {}).get('youtubetitle', 'Unknown Title')}")
                
                with open(DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(full_data, f, indent=4)
                print("Updated data.json")
        except Exception as e:
            print(f"Error updating data.json: {e}")

        # 6. Delete Video File
        try:
            if os.path.exists(VIDEO_FILE):
                os.remove(VIDEO_FILE)
                print(f"Deleted video file: {VIDEO_FILE}")
            
            
            # Delete thumbnail
            if os.path.exists(THUMBNAIL_FILE):
                os.remove(THUMBNAIL_FILE)
                print(f"Deleted thumbnail: {THUMBNAIL_FILE}")
                
            # Delete timestamps
            timestamps_file = os.path.join(ROOT_DIR, "output", "viralCourses", "timestamps.json")
            if os.path.exists(timestamps_file):
                os.remove(timestamps_file)
                print(f"Deleted timestamps file: {timestamps_file}")
                
        except Exception as e:
            print(f"Error cleaning up files: {e}")

    else:
        print("Upload Failed.")

if __name__ == "__main__":
    upload_viral_video()
