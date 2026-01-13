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
THUMBNAIL_1 = os.path.join(ROOT_DIR, "output", "viralCourses", "thumbnail_1.png")
THUMBNAIL_2 = os.path.join(ROOT_DIR, "output", "viralCourses", "thumbnail_2.png")
THUMBNAIL_3 = os.path.join(ROOT_DIR, "output", "viralCourses", "thumbnail_3.png")
AB_TEST_METADATA = os.path.join(ROOT_DIR, "output", "viralCourses", "ab_test_metadata.json")
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
    asset_titles = asset_data["video_assets"].get("titles", [])
    
    # --- A/B TESTING TITLES ---
    # Option 1: youtubetitle (Main)
    title_1 = meta.get("youtubetitle", "Viral Course Video")
    
    # Option 2: titles[0] (Alternative 1)
    title_2 = asset_titles[0] if len(asset_titles) > 0 else title_1
    
    # Option 3: titles[1] (Alternative 2)
    title_3 = asset_titles[1] if len(asset_titles) > 1 else title_1
    
    # Truncate all titles to 100 chars
    title_1 = (title_1[:97] + "...") if len(title_1) > 100 else title_1
    title_2 = (title_2[:97] + "...") if len(title_2) > 100 else title_2
    title_3 = (title_3[:97] + "...") if len(title_3) > 100 else title_3

    # --- RESTORE DESCRIPTION & TAGS LOGIC ---
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
        description_parts.append(f"📚 Full Course: {course_link}")
        description_parts.append("")
    
    # Main description
    if desc_main:
        description_parts.append(desc_main)
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
    
    return (title_1, title_2, title_3), description, tags, meta.get("category", "27"), course_title

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
    titles, description, tags, category_id, course_title = generate_metadata(data)
    title_main = titles[0]
    
    print(f"Title (Main): {title_main}")
    print(f"Description Preview:\n{description[:100]}...")
    print(f"Tags: {tags}")
    
    # 4. Save A/B Test Metadata for user reference
    ab_testing_data = {
        "title_variations": titles,
        "thumbnail_variations": [THUMBNAIL_1, THUMBNAIL_2, THUMBNAIL_3],
        "video_file": VIDEO_FILE
    }
    with open(AB_TEST_METADATA, "w", encoding='utf-8') as f:
        json.dump(ab_testing_data, f, indent=4)
    print(f"✓ Saved A/B testing metadata to {AB_TEST_METADATA}")

    # 5. Upload (Using Main Variation)
    video_id = youtube_uploader.upload_video(
        VIDEO_FILE, 
        title_main, 
        description, 
        category_id="27", # Education
        keywords=",".join(tags),
        token_file=TOKEN_FILE_YOUTUBE,
        thumbnail=THUMBNAIL_1,
        course_title=course_title
    )
    
    if video_id:
        print(f"Upload Success! Video ID: {video_id}")
        print("Please note: You can manually set up A/B testing in YouTube Studio using the variations saved in ab_test_metadata.json")
        
        # 6. Cleanup Data
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
            
            
            # Delete all thumbnail variations
            for t in [THUMBNAIL_1, THUMBNAIL_2, THUMBNAIL_3]:
                if os.path.exists(t):
                    os.remove(t)
                    print(f"Deleted thumbnail: {t}")
            
            # Delete A/B metadata
            if os.path.exists(AB_TEST_METADATA):
                os.remove(AB_TEST_METADATA)
                
        except Exception as e:
            print(f"Error cleaning up files: {e}")

    else:
        print("Upload Failed.")

if __name__ == "__main__":
    upload_viral_video()
