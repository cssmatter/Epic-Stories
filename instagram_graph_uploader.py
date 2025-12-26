import requests
import time
import os
import sys

class InstagramGraphUploader:
    def __init__(self, access_token, instagram_account_id):
        self.access_token = access_token
        self.instagram_account_id = instagram_account_id
        self.base_url = f"https://graph.facebook.com/v18.0/{self.instagram_account_id}"

    def upload_reel(self, video_url, caption=""):
        """
        Uploads an Instagram Reel using the 3-step Graph API process.
        """
        print(f"Starting official Reel upload for: {video_url}")
        
        # Step 1: Create Media Container
        container_id = self._create_container(video_url, caption)
        if not container_id:
            return False

        # Step 2: Poll for status until Ready
        if not self._wait_for_container(container_id):
            return False

        # Step 3: Publish Media
        media_id = self._publish_container(container_id)
        if media_id:
            print(f"✅ Successfully published Reel! Media ID: {media_id}")
            return True
        return False

    def _create_container(self, video_url, caption):
        print("Step 1: Creating media container...")
        url = f"{self.base_url}/media"
        payload = {
            'media_type': 'REELS',
            'video_url': video_url,
            'caption': caption,
            'access_token': self.access_token
        }
        response = requests.post(url, data=payload).json()
        
        if 'id' in response:
            print(f"Container created. ID: {response['id']}")
            return response['id']
        else:
            print(f"Error creating container: {response}")
            return None

    def _wait_for_container(self, container_id):
        print("Step 2: Waiting for container to be ready (processing)...")
        url = f"https://graph.facebook.com/v18.0/{container_id}"
        params = {
            'fields': 'status_code,status',
            'access_token': self.access_token
        }
        
        max_retries = 30  # Wait up to 5 minutes (10s * 30)
        for i in range(max_retries):
            response = requests.get(url, params=params).json()
            status = response.get('status_code')
            
            if status == 'FINISHED':
                print("Container is ready!")
                return True
            elif status == 'ERROR':
                print(f"Error during processing: {response}")
                return False
            else:
                print(f"Status: {status}... waiting 10s (Attempt {i+1}/{max_retries})")
                time.sleep(10)
        
        print("Timed out waiting for container processing.")
        return False

    def _publish_container(self, container_id):
        print("Step 3: Publishing media...")
        url = f"{self.base_url}/media_publish"
        payload = {
            'creation_id': container_id,
            'access_token': self.access_token
        }
        response = requests.post(url, data=payload).json()
        
        if 'id' in response:
            return response['id']
        else:
            print(f"Error publishing: {response}")
            return None

if __name__ == "__main__":
    import json
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload a Reel to Instagram.")
    parser.add_argument("video_url", nargs="?", help="URL of the video to upload")
    parser.add_argument("caption", nargs="?", help="Caption for the Reel")
    parser.add_argument("--metadata", help="Path to JSON metadata file")
    
    args = parser.parse_args()
    
    # Credentials from environment variables
    TOKEN = os.getenv("IG_ACCESS_TOKEN")
    ACCOUNT_ID = os.getenv("IG_BUSINESS_ID")
    
    video_url = args.video_url
    caption = args.caption
    metadata_file = args.metadata or "instagram_metadata.json"

    # If no caption provided, try to load from metadata file
    if caption is None:
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    caption = metadata.get("description", "")
                print(f"Loaded caption from {metadata_file}")
            except Exception as e:
                print(f"Error loading metadata file: {e}")
                caption = ""
        else:
            if args.metadata: # Only warn if user explicitly provided a path that doesn't exist
                print(f"Warning: Metadata file {metadata_file} not found.")
            caption = ""

    if not video_url:
        print("Error: VIDEO_URL is required.")
        sys.exit(1)

    if not TOKEN or not ACCOUNT_ID:
        print("Error: IG_ACCESS_TOKEN and IG_BUSINESS_ID environment variables are required.")
        sys.exit(1)

    uploader = InstagramGraphUploader(TOKEN, ACCOUNT_ID)
    success = uploader.upload_reel(video_url, caption)
    
    if not success:
        sys.exit(1)
