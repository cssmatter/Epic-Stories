import os
import time
import json
import base64
from pathlib import Path
from instagrapi import Client
from instagrapi.exceptions import LoginRequired

class InstagramUploader:
    def __init__(self, username, password, session_file="session.json", session_base64=None):
        self.username = username
        self.password = password
        self.session_file = Path(session_file)
        self.client = Client()
        
        # Add challenge handler for interactive login (for local setup)
        self.client.challenge_code_handler = self._challenge_code_handler
        
        # If base64 session is provided, write it to the session file
        if session_base64:
            try:
                print("Decoding session from environment variable...")
                session_data = base64.b64decode(session_base64).decode('utf-8')
                with open(self.session_file, "w") as f:
                    f.write(session_data)
                print(f"Session decoded and saved to {self.session_file}")
            except Exception as e:
                print(f"Failed to decode SESSION_BASE64: {e}")

    def login(self, session_id=None):
        """Log in using session_id (primary), session file, or credentials."""
        if session_id:
            try:
                print("Attempting login via session_id...")
                # Extract user_id from session_id if possible (it's the first part before %3A)
                if "%3A" in session_id:
                    uid = session_id.split("%3A")[0]
                    self.client.set_settings({"uuids": {"phone_id": uid, "uuid": uid, "client_ad_id": uid, "device_id": uid}})
                
                self.client.login_by_sessionid(session_id)
                
                # VERIFY: Using a non-GraphQL method first
                print("Validating session via timeline feed...")
                self.client.get_timeline_feed()
                print("Session is valid for timeline feed.")
                
                # Optional: Try to get username for logging (may fail with KeyError: 'data')
                try:
                    user_info = self.client.user_info(self.client.user_id)
                    print(f"Logged in as {user_info.username}")
                except Exception:
                    print(f"Logged in successfully (User ID: {self.client.user_id})")
                
                print("Waiting 3 seconds for session stabilization...")
                time.sleep(3)
                
                self.client.dump_settings(self.session_file)
                return
            except Exception as e:
                print(f"SessionID login or validation failed: {e}")
                print("This session might be restricted or expired.")

        if not self.username or not self.password:
             if not session_id:
                raise ValueError("INSTAGRAM_USERNAME or INSTAGRAM_PASSWORD is empty or None")

        print(f"Attempting login for '{self.username}'...")
        
        # 1. Try loading from session file
        if self.session_file.exists():
            try:
                print(f"Loading session from {self.session_file}...")
                self.client.load_settings(self.session_file)
                # Check if session is still valid
                self.client.get_timeline_feed() 
                print("Session is valid. Logged in successfully.")
                return
            except Exception as e:
                print(f"Session invalid or expired: {e}. Cleaning up and trying fresh login...")
                if self.session_file.exists():
                    self.session_file.unlink()

        # 2. Fresh login if session failed or doesn't exist
        self._fresh_login()

    def _fresh_login(self):
        """Perform a fresh login with a random delay to avoid some 429s."""
        try:
            print("Performing fresh login...")
            # Adding a small delay before login
            time.sleep(2) 
            self.client.login(self.username, self.password)
            self.client.dump_settings(self.session_file)
            print("Successfully logged in and saved new session settings.")
        except Exception as e:
            if "int() argument must be a string" in str(e):
                print("Detected specific 'NoneType' error during login. This usually means Instagram blocked the IP or returned a 429.")
                print("Check if your account requires 2FA or has a 'Help Us Confirm You Own This Account' prompt.")
            raise e

    def _challenge_code_handler(self, username, choice):
        """Handle challenges by asking the user to enter the code in the terminal."""
        print(f"Challenge required for {username}!")
        print(f"Instagram sent a code via {choice}. Check your email or phone.")
        code = input("Enter the verification code: ")
        return code

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
    SESSION_ID = os.getenv("INSTAGRAM_SESSION_ID")
    SESSION_B64 = os.getenv("INSTAGRAM_SESSION_BASE64")
    
    # Example usage for testing or integration
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python instagram_uploader.py <video_path> [caption]")
        sys.exit(1)
        
    video_path = sys.argv[1]
    caption = sys.argv[2] if len(sys.argv) > 2 else "New Reel! #automation"

    if not USERNAME or not PASSWORD:
        if not SESSION_ID:
            print("Error: INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD (or INSTAGRAM_SESSION_ID) are required.")
            sys.exit(1)

    uploader = InstagramUploader(USERNAME, PASSWORD, session_base64=SESSION_B64)
    try:
        uploader.login(session_id=SESSION_ID)
        uploader.upload_reel(video_path, caption)
    except Exception as e:
        print(f"Automation failed: {e}")
        sys.exit(1)
