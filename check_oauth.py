"""
Helper script to show the exact OAuth redirect URI being used.
Run this to see what URI you need to add to Google Cloud Console.
"""
import sys
sys.path.insert(0, '.')

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/youtube']

print("=" * 60)
print("OAUTH REDIRECT URI HELPER")
print("=" * 60)

try:
    flow = InstalledAppFlow.from_client_secrets_file(
        'client_secrets.json', SCOPES)
    
    # This will show the redirect URI
    print("\nThe script will try to use a redirect URI like:")
    print("  http://localhost:<RANDOM_PORT>/")
    print("\nTo fix the error, go to Google Cloud Console:")
    print("  https://console.cloud.google.com/apis/credentials")
    print("\nAnd add BOTH of these to 'Authorized redirect URIs':")
    print("  1. http://localhost:8080/")
    print("  2. http://localhost/")
    print("\nAlternatively, download a 'Desktop app' type OAuth client")
    print("instead of 'Web application' type.")
    print("=" * 60)
    
except Exception as e:
    print(f"\nError: {e}")
