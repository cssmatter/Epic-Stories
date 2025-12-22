import requests
import sys
import os

def find_instagram_id(access_token):
    """
    Finds the Instagram Business Account ID linked to the Facebook Pages
    managed by the user of the provided access token.
    """
    base_url = "https://graph.facebook.com/v18.0"
    
    # 1. Get the list of Facebook Pages managed by the user
    try:
        pages_url = f"{base_url}/me/accounts?access_token={access_token}"
        response = requests.get(pages_url).json()
        
        if 'error' in response:
            print(f"Error fetching pages: {response['error']['message']}")
            return

        pages = response.get('data', [])
        if not pages:
            print("No Facebook Pages found linked to this account.")
            return

        print(f"Found {len(pages)} Facebook Page(s). Searching for linked Instagram accounts...")

        for page in pages:
            page_id = page['id']
            page_name = page['name']
            
            # 2. For each page, check if there is an Instagram Business Account linked
            ig_url = f"{base_url}/{page_id}?fields=instagram_business_account&access_token={access_token}"
            ig_response = requests.get(ig_url).json()
            
            if 'instagram_business_account' in ig_response:
                ig_id = ig_response['instagram_business_account']['id']
                print(f"\nSUCCESS!")
                safe_name = page_name.encode('ascii', 'ignore').decode('ascii')
                print(f"Facebook Page: {safe_name} (ID: {page_id})")
                print(f"Instagram Business Account ID: {ig_id}")
                print("\nUse this ID as your IG_BUSINESS_ID secret in GitHub.")
                return
            else:
                print(f" - Page '{page_name}' has no linked Instagram Business Account.")

        print("\nCould not find any Instagram Business Account linked to your Facebook Pages.")
        print("Ensure your Instagram account is a 'Business' or 'Creator' account and linked to a Facebook Page.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    if not token and len(sys.argv) > 1:
        token = sys.argv[1]
    
    if not token:
        print("Usage: python find_ig_id.py <YOUR_FACEBOOK_ACCESS_TOKEN>")
        print("Or set the environment variable FACEBOOK_ACCESS_TOKEN")
        sys.exit(1)
        
    find_instagram_id(token)
