import os
import json
import glob
import shutil
from datetime import datetime, timedelta, timezone
import youtube_uploader

def bulk_upload_scheduled(directory="downloads", interval_hours=24):
    """
    Scans directory for metadata, uploads first immediately, 
    and schedules subsequent ones at 24-hour intervals.
    """
    # 1. Find all metadata files
    meta_files = sorted(glob.glob(os.path.join(directory, "upload_metadata_*.json")))
    
    if not meta_files:
        print(f"No metadata files found in {directory}.")
        return

    print(f"Found {len(meta_files)} videos to upload/schedule.")
    
    # Ensure published directory exists
    published_dir = os.path.join(directory, "published")
    os.makedirs(published_dir, exist_ok=True)

    # 2. Process each file
    base_time = datetime.now(timezone.utc)
    
    for i, meta_file in enumerate(meta_files):
        print(f"\n--- Processing {i+1}/{len(meta_files)}: {os.path.basename(meta_file)} ---")
        
        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            
            # Calculate schedule time (None for the first one = immediate)
            publish_at = None
            if i > 0:
                scheduled_dt = base_time + timedelta(hours=interval_hours * i)
                # YouTube API requires ISO 8601 format: YYYY-MM-DDThh:mm:ss.sZ
                publish_at = scheduled_dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            
            # Perform upload
            video_id = youtube_uploader.upload_video(
                file_path=meta['video_path'],
                title=meta['title'],
                description=meta['description'],
                keywords=meta.get('keywords', 'ghazal,shayari'),
                token_file='token_shayari.pickle',
                publish_at=publish_at
            )
            
            if video_id:
                print(f"Successfully uploaded/scheduled: {video_id}")
                
                # Move to published folder
                shutil.move(meta_file, os.path.join(published_dir, os.path.basename(meta_file)))
                if os.path.exists(meta['video_path']):
                    shutil.move(meta['video_path'], os.path.join(published_dir, os.path.basename(meta['video_path'])))
                
                # If there's an image path, move it too
                img_path = meta.get('image_path')
                if img_path and os.path.exists(img_path):
                    shutil.move(img_path, os.path.join(published_dir, os.path.basename(img_path)))
            
        except Exception as e:
            print(f"Error processing {meta_file}: {e}")
            continue

if __name__ == "__main__":
    bulk_upload_scheduled()
