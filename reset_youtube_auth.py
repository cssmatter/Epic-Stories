import os
import sys
import youtube_uploader

# Force utf-8 output for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Older python versions might not have reconfigure
        pass

def reset_and_reauth(token_file='token.pickle', channel_name='All Time Epic Stories'):
    if os.path.exists(token_file):
        print(f"Removing old authentication token: {token_file}")
        os.remove(token_file)
    else:
        print(f"No existing token found for {token_file}.")
    
    print(f"\nStarting NEW authentication flow for: {channel_name}")
    print("IMPORTANT: When the browser opens, please select the Google Account that owns the channel:")
    print(f"'{channel_name}'")
    print("-" * 60)
    
    try:
        # Trigger the auth flow
        youtube_uploader.get_authenticated_service(token_file=token_file)
        print(f"\nSUCCESS: Successfully authenticated with {channel_name}.")
        print(f"You can verify by running 'python check_channel.py' (make sure to update it to take the token file)")
    except Exception as e:
        print(f"\nError during authentication: {e}")

if __name__ == "__main__":
    import sys
    channel_map = {
        'shayari': ('token_shayari.pickle', 'Hindi Shayari हिंदी शायरी'),
        'god': ('token_godisgreatest.pickle', 'God Is Greatest'),
        'viral': ('token_viral_courses.pickle', 'Viral Courses'),
        'hidden': ('token_hidden_offers.pickle', 'Hidden Offers'),
        'devotional': ('token_devotional.pickle', 'Devotional hindi quote'),
        'quote': ('token.pickle', 'All Time Epic Stories')
    }
    
    if len(sys.argv) > 1 and sys.argv[1] in channel_map:
        token, name = channel_map[sys.argv[1]]
        reset_and_reauth(token_file=token, channel_name=name)
    elif len(sys.argv) > 1:
        # Try direct filename
        reset_and_reauth(token_file=sys.argv[1])
    else:
        reset_and_reauth()
