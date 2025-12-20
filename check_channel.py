
import youtube_uploader

def check_current_channel(token_file='token.pickle'):
    try:
        youtube = youtube_uploader.get_authenticated_service(token_file=token_file)
        request = youtube.channels().list(
            part="snippet,contentDetails,statistics",
            mine=True
        )
        response = request.execute()
        
        if 'items' in response and len(response['items']) > 0:
            channel = response['items'][0]
            print(f"Authenticated Channel Name: {channel['snippet']['title']}")
            print(f"Authenticated Channel ID: {channel['id']}")
            print(f"Custom URL (if any): {channel['snippet'].get('customUrl', 'N/A')}")
        else:
            print("No channel found for these credentials.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'shayari':
        print("Checking SHAYARI channel...")
        check_current_channel(token_file='shayari/token_shayari.pickle')
    else:
        print("Checking STORIES channel...")
        check_current_channel()
