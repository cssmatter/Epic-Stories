
import os
import sys
from PIL import Image
from youtube_uploader import get_authenticated_service
from googleapiclient.http import MediaFileUpload

# Target video and paths
video_id = "cODAgW0N5nM"
source_thumb = os.path.abspath("output/epicstories/thumbnail.png")
optimized_thumb = os.path.abspath("output/epicstories/thumbnail_90sec_optimized.jpg")

def compress_and_upload():
    if not os.path.exists(source_thumb):
        print(f"Error: Source thumbnail not found: {source_thumb}")
        return

    # 1. Compress
    print(f"Compressing {source_thumb}...")
    img = Image.open(source_thumb)
    quality = 95
    img.save(optimized_thumb, "JPEG", quality=quality, optimize=True)
    
    while os.path.getsize(optimized_thumb) > 2 * 1024 * 1024 and quality > 40:
        quality -= 5
        img.save(optimized_thumb, "JPEG", quality=quality, optimize=True)
    
    size_mb = os.path.getsize(optimized_thumb) / (1024 * 1024)
    print(f"Optimized thumbnail size: {size_mb:.2f} MB")

    # 2. Upload
    print(f"Uploading optimized thumbnail to video {video_id}...")
    try:
        youtube = get_authenticated_service()
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(optimized_thumb)
        ).execute()
        print("SUCCESS! Thumbnail has been updated on YouTube.")
    except Exception as e:
        print(f"FAILED to upload thumbnail: {e}")

if __name__ == "__main__":
    compress_and_upload()
