import os
import sys

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import youtube_uploader
import base64

TOKEN_FILE = 'token_hidden_offers.pickle'

def authenticate():
    print("--- HiddenOffersDaily Authentication ---")
    print("This script will open a browser window for you to log into the CORRECT YouTube channel.")
    print(f"Generating: {TOKEN_FILE}")
    
    try:
        # This will trigger the flow and save to token_hidden_offers.pickle
        service = youtube_uploader.get_authenticated_service(token_file=TOKEN_FILE)
        
        # Verify channel
        channel = service.channels().list(part='snippet', mine=True).execute()
        if 'items' in channel:
            title = channel['items'][0]['snippet']['title']
            print(f"\nSuccessfully authenticated for channel: {title}")
            
            # Generate Base64 for the user
            with open(TOKEN_FILE, 'rb') as f:
                b64_token = base64.b64encode(f.read()).decode('utf-8')
            
            print("\n--- GITHUB SECRETS DETAILS ---")
            print("1. Go to your GitHub Repository -> Settings -> Secrets and variables -> Actions")
            print(f"2. Update/Add 'TOKEN_HIDDEN_OFFERS_BASE64' with the following string (Copy everything below):\n")
            print(b64_token)
            print("\n------------------------------")
            
        else:
            print("No channel found for this account.")
            
    except Exception as e:
        print(f"Error during authentication: {e}")

if __name__ == "__main__":
    authenticate()
