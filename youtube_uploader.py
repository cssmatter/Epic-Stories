
import os
import pickle
import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Scopes needed for uploading and playlist management
SCOPES = ['https://www.googleapis.com/auth/youtube']

def get_authenticated_service(token_file='token.pickle'):
    """
    Authenticate with YouTube using OAuth 2.0.
    Requires 'client_secrets.json' to be present in the directory.
    """
    creds = None
    is_ci = os.getenv('CI') or os.getenv('GITHUB_ACTIONS')
    
    # Check if we have valid saved credentials
    if os.path.exists(token_file):
        print("Loading saved credentials...")
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
            
    # If no valid credentials, log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Refreshing access token...")
                creds.refresh(Request())
            except RefreshError as e:
                print(f"Token refresh failed: {e}")
                print("Token has been revoked or expired. Deleting token and re-authenticating...")
                # Delete the invalid token file
                if os.path.exists(token_file):
                    os.remove(token_file)
                # Trigger new authentication flow
                creds = None
        
        if not creds:
            if is_ci:
                # Map token filenames to their corresponding secret names in GitHub
                secret_map = {
                    'token_shayari.pickle': 'SHAYARI_TOKEN_PICKLE_BASE64',
                    'token.pickle': 'TOKEN_PICKLE_BASE64',
                    'token_godisgreatest.pickle': 'GOD_TOKEN_PICKLE_BASE64',
                    'token_hidden_offers.pickle': 'HIDDEN_OFFERS_TOKEN_PICKLE_BASE64'
                }
                secret_name = secret_map.get(token_file, 'TOKEN_PICKLE_BASE64')
                
                # Determine refresh script
                refresh_script = ".\\auth_and_get_token.ps1" if "shayari" in token_file else "python update_github_token.py"
                if "god" in token_file:
                    refresh_script = "python scripts/godisgreatest/daily_god_message_video.py" # Local run triggers auth
                
                raise RuntimeError(
                    f"\n{'='*70}\n"
                    f"TOKEN EXPIRED OR MISSING IN CI ENVIRONMENT\n"
                    f"{'='*70}\n"
                    f"The YouTube token ({token_file}) is missing or could not be refreshed.\n"
                    f"In a CI/GitHub Actions environment, we cannot open a browser for re-authentication.\n\n"
                    f"TO FIX THIS:\n"
                    f"1. Run the appropriate script locally to refresh the token:\n"
                    f"   - {refresh_script}\n"
                    f"2. Complete the browser authentication.\n"
                    f"3. Copy the BASE64 string from the output.\n"
                    f"4. Update the '{secret_name}' secret in GitHub repository settings.\n"
                    f"{'='*70}\n"
                )

            print("Starting new authentication flow...")
            client_secrets_file = 'client_secrets.json'
            if not os.path.exists(client_secrets_file):
                raise FileNotFoundError(f"Could not find {client_secrets_file}. You provided an API Key, but uploads require an OAuth 2.0 Client ID JSON file.")
                
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secrets_file, SCOPES)
            # Use access_type='offline' to get a refresh token
            # Use prompt='consent' to force the consent screen and ensure we get a new refresh token
            creds = flow.run_local_server(
                port=0, 
                access_type='offline',
                prompt='consent'
            )
            
        # Save the credentials for the next run (only if not in CI, as secrets are immutable)
        if not is_ci:
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
            
    return build('youtube', 'v3', credentials=creds)

def upload_video(file_path, title, description, category_id="22", keywords="quote,motivation", token_file='token.pickle'):
    """
    Uploads a video to YouTube.
    """
    if not os.path.exists(file_path):
        print(f"Error: Video file not found: {file_path}")
        return None

    youtube = get_authenticated_service(token_file=token_file)

    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': keywords.split(','),
            'categoryId': category_id
        },
        'status': {
            'privacyStatus': 'public', # Public so videos are immediately visible
            'selfDeclaredMadeForKids': False,
        }
    }

    print(f"Uploading {file_path}...")
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    
    request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%")

    print(f"Upload Complete! Video ID: {response['id']}")
    print(f"Link: https://youtu.be/{response['id']}")
    return response['id']

def add_video_to_playlist(video_id, playlist_id, token_file='token.pickle'):
    """
    Adds a video to a specific playlist.
    """
    youtube = get_authenticated_service(token_file=token_file)
    
    print(f"Adding video {video_id} to playlist {playlist_id}...")
    request = youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id
                }
            }
        }
    )
    try:
        response = request.execute()
        print(f"Video added to playlist: {response['snippet']['title']}")
    except UnicodeEncodeError:
        print(f"Video added to playlist successfully (Title contains non-printable characters).")
    except Exception as e:
        print(f"Error adding to playlist: {e}")

def get_or_create_playlist(title, token_file='token.pickle'):
    """
    Finds a playlist by title or creates it if it doesn't exist.
    """
    youtube = get_authenticated_service(token_file=token_file)
    
    # 1. Search for existing playlist
    request = youtube.playlists().list(
        part="snippet,contentDetails",
        mine=True,
        maxResults=50
    )
    
    while request:
        response = request.execute()
        for item in response.get('items', []):
            if item['snippet']['title'] == title:
                print(f"Found existing playlist: {title} (ID: {item['id']})")
                return item['id']
        
        request = youtube.playlists().list_next(request, response)

    # 2. Create new playlist if not found
    print(f"Playlist '{title}' not found. Creating new playlist...")
    request = youtube.playlists().insert(
        part="snippet,status",
        body={
          "snippet": {
            "title": title,
            "description": f"Collection of Shayari by {title}.",
            "defaultLanguage": "hi"
          },
          "status": {
            "privacyStatus": "public"
          }
        }
    )
    response = request.execute()
    print(f"Created new playlist: {title} (ID: {response['id']})")
    return response['id']

if __name__ == "__main__":
    # Test run
    # upload_video("daily_quote_video.mp4", "Test Quote Video", "Generated by Python")
    print("This module is intended to be imported.")
