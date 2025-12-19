import os
import time
import json
from pathlib import Path
from instagrapi import Client
from instagrapi.exceptions import LoginRequired

class InstagramUploader:
    def __init__(self, username, password, session_file="session.json"):
        self.username = username
        self.password = password
        self.session_file = Path(session_file)
        self.client = Client()

    def login(self):
        """Log in using session file or credentials."""
        print(f"Attempting login for {self.username}...")
        
        if self.session_file.exists():
            try:
                self.client.load_settings(self.session_file)
                self.client.login(self.username, self.password)
                print("Successfully logged in using session file.")
            except Exception as e:
                print(f"Session login failed: {e}. Trying fresh login...")
                self._fresh_login()
        else:
            self._fresh_login()

    def _fresh_login(self):
        """Perform a fresh login and save settings."""
        self.client.login(self.username, self.password)
        self.client.dump_settings(self.session_file)
        print("Successfully logged in and saved session settings.")

    def upload_reel(self, video_path, caption="", thumbnail_path=None):
        """Upload a video as a Reel."""
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        print(f"Uploading Reel: {video_path.name}...")
        try:
            media = self.client.clip_upload(
                video_path,
                caption=caption,
                thumbnail=thumbnail_path
            )
            print(f"Successfully uploaded Reel! Media ID: {media.pk}")
            return media
        except Exception as e:
            print(f"Error during Reel upload: {e}")
            raise

if __name__ == "__main__":
    # Get credentials from environment variables
    USERNAME = os.getenv("INSTAGRAM_USERNAME")
    PASSWORD = os.getenv("INSTAGRAM_PASSWORD")
    
    # Example usage for testing or integration
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python instagram_uploader.py <video_path> [caption]")
        sys.exit(1)
        
    video_path = sys.argv[1]
    caption = sys.argv[2] if len(sys.argv) > 2 else "New Reel! #automation"

    if not USERNAME or not PASSWORD:
        print("Error: INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD environment variables are required.")
        sys.exit(1)

    uploader = InstagramUploader(USERNAME, PASSWORD)
    try:
        uploader.login()
        uploader.upload_reel(video_path, caption)
    except Exception as e:
        print(f"Automation failed: {e}")
        sys.exit(1)
