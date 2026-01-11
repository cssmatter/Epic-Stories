import subprocess
import json
import os
import sys
import time

# Get root dir
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

DATA_FILE = os.path.join(ROOT_DIR, "data", "viralCourses", "data.json")
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts", "viralCourses")

def get_remaining_count():
    if not os.path.exists(DATA_FILE):
        return 0
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return len(data)
    except:
        return 0

def run_step(script_name):
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    print(f"Running {script_name}...")
    result = subprocess.run([sys.executable, script_path], check=False)
    return result.returncode == 0

def main():
    print("=== Viral Courses Batch Processor ===")
    
    while True:
        count = get_remaining_count()
        if count == 0:
            print("No more data in data.json. Finished.")
            break
        
        print(f"\n--- Processing Video (Items remaining: {count}) ---")
        
        # 1. Generate Video
        if not run_step("viral_courses_fast.py"):
            print("Video generation failed. Stopping.")
            break
            
        # 2. Generate Thumbnail
        if not run_step("generate_thumbnail.py"):
            print("Thumbnail generation failed. Skipping to next? No, stopping for safety.")
            break
            
        # 3. Upload and Cleanup
        # This script removes the first item from data.json and deletes the video file on success
        if not run_step("upload_viral_course.py"):
            print("Upload failed. Stopping batch to avoid re-generating same video.")
            break
            
        print("\nSuccess! Moving to next item in 5 seconds...")
        time.sleep(5)

if __name__ == "__main__":
    main()
