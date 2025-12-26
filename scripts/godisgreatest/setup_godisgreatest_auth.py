
import os
import sys

# Add root directory to path to import youtube_uploader
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)

import youtube_uploader

def main():
    print("--- God Is Greatest YouTube Authentication Setup ---")
    print("This script will open a browser to authenticate the new YouTube channel.")
    print("Ensure you log in with the 'God Is Greatest' channel account.")
    
    token_file = os.path.join(ROOT_DIR, 'token_godisgreatest.pickle')
    
    try:
        # Trigger authentication and save to specific file
        service = youtube_uploader.get_authenticated_service(token_file=token_file)
        print(f"\nSUCCESS! Authentication complete.")
        print(f"Token saved to: {token_file}")
    except Exception as e:
        print(f"\nFAILED: {e}")

if __name__ == "__main__":
    main()
