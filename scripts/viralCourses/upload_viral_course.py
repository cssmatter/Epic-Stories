import os
import sys
import json

# Add root to python path to import youtube_uploader
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT_DIR)

import youtube_uploader

# Configuration
DATA_FILE = os.path.join(ROOT_DIR, "data", "viralCourses", "data.json")
VIDEO_FILE = os.path.join(ROOT_DIR, "output", "viralCourses", "viral_course_video_fast.mp4")
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

def generate_metadata(asset_data):
    meta = asset_data["video_assets"]["youtube_metadata"]
    
    title = meta.get("youtubetitle", "Viral Course Video")
    
    # Description Construction
    course_link = meta.get("courselink", "")
    desc_main = meta.get("description", "")
    hashtags = " ".join(meta.get("hashtags", []))
    keywords = ", ".join(meta.get("keywords", []))
    google_search = meta.get("mostsearchedongoogle", "")
    
    # Tags
    tags_str_raw = meta.get("tags", "")
    tags = [t.strip() for t in tags_str_raw.split(",")]
    # Add keywords to tags too usually
    if keywords:
        tags.extend([k.strip() for k in keywords.split(",")])
        
    # Deduplicate tags and limit
    tags = list(set([t for t in tags if t]))[:40] # Youtube limit ~500 chars total usually
    
    # Extra Titles
    titles = asset_data["video_assets"].get("titles", [])
    titles_str = "\n".join(titles)

    description = f"""Full Course Link:
{course_link}

{desc_main}

Alternative Titles:
{titles_str}

Related Queries:
{google_search}

Keywords:
{keywords}

Tags:
{tags_str_raw}

{hashtags}
"""
    
    return title, description, tags, meta.get("category", "27") # 27 is Education

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

    # 3. Generate Metadata
    title, description, tags, category_id = generate_metadata(data)
    
    print(f"Title: {title}")
    print(f"Description Preview:\n{description[:100]}...")
    print(f"Tags: {tags}")
    
    # 4. Upload
    # Since this is a new channel, this will likely trigger the auth flow on first run
    video_id = youtube_uploader.upload_video(
        VIDEO_FILE, 
        title, 
        description, 
        category_id="27", # Education
        keywords=",".join(tags),
        token_file=TOKEN_FILE_YOUTUBE
    )
    
    if video_id:
        print(f"Upload Success! Video ID: {video_id}")
        
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
            
            # Also delete thumbnail if exists
            thumb_file = os.path.join(ROOT_DIR, "output", "viralCourses", "thumbnail.png")
            if os.path.exists(thumb_file):
                os.remove(thumb_file)
                print(f"Deleted thumbnail file: {thumb_file}")
                
        except Exception as e:
            print(f"Error cleaning up files: {e}")

    else:
        print("Upload Failed.")

if __name__ == "__main__":
    upload_viral_video()
