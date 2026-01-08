import os
import pickle
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

# Fix path to access root for client_secrets if needed, though usually in root
# Assume script is run from root or we find client_secrets in root
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CLIENT_SECRETS_FILE = os.path.join(ROOT_DIR, "client_secrets.json")
TOKEN_FILE = os.path.join(ROOT_DIR, "token_devotional.pickle")

SCOPES = ['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.force-ssl']

def authenticate_youtube():
    if not os.path.exists(CLIENT_SECRETS_FILE):
        print(f"Error: {CLIENT_SECRETS_FILE} not found. Please ensure it exists in the project root.")
        return

    print("Starting authentication for NEW Devotional Channel...")
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    creds = flow.run_local_server(port=0, prompt='consent')

    with open(TOKEN_FILE, 'wb') as token:
        pickle.dump(creds, token)
    
    print(f"\nSUCCESS! Token saved to: {TOKEN_FILE}")
    print("Next Steps:")
    print("1. Encode this file to Base64 (using a tool or script).")
    print("2. Add it to GitHub Secrets as 'DEVOTIONAL_TOKEN_PICKLE_BASE64'.")

if __name__ == "__main__":
    authenticate_youtube()
