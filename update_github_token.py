import base64
import os
import sys

# Default token file
token_file = 'token.pickle'

# Check for command line argument
if len(sys.argv) > 1:
    arg = sys.argv[1]
    
    # Alias mapping to match reset_youtube_auth.py
    alias_map = {
        'shayari': 'token_shayari.pickle',
        'god': 'token_godisgreatest.pickle',
        'viral': 'token_viral_courses.pickle',
        'hidden': 'token_hidden_offers.pickle',
        'devotional': 'token_devotional.pickle',
        'quote': 'token.pickle'
    }
    
    if arg in alias_map:
        token_file = alias_map[arg]
    else:
        token_file = arg
        if not token_file.endswith('.pickle'):
            token_file += '.pickle'
        if not os.path.exists(token_file) and not token_file.startswith('token_'):
            token_file = f"token_{token_file}"

# Read the token file
if not os.path.exists(token_file):
    print(f"ERROR: {token_file} not found!")
    print(f"Please ensure you've ran the authentication for this channel first.")
    exit(1)

with open(token_file, 'rb') as f:
    token_data = f.read()

# Encode to base64
encoded = base64.b64encode(token_data).decode('utf-8')

# Save to a file for easy copying
output_file = f"{token_file.replace('.pickle', '')}_base64.txt"
with open(output_file, 'w') as f:
    f.write(encoded)

print(f"SUCCESS: {token_file} successfully encoded!")
print("\n" + "="*70)
print("INSTRUCTIONS: Update your GitHub Secret")
print("="*70)

# Map token to secret names
secret_map = {
    'token_shayari.pickle': 'SHAYARI_TOKEN_PICKLE_BASE64',
    'token.pickle': 'TOKEN_PICKLE_BASE64',
    'token_godisgreatest.pickle': 'GODISGREATEST_TOKEN_PICKLE_BASE64',
    'token_hidden_offers.pickle': 'HIDDEN_OFFERS_TOKEN_PICKLE_BASE64',
    'token_viral_courses.pickle': 'VIRAL_COURSES_TOKEN_PICKLE_BASE64',
    'token_devotional.pickle': 'DEVOTIONAL_TOKEN_PICKLE_BASE64'
}
secret_name = secret_map.get(os.path.basename(token_file), 'TOKEN_PICKLE_BASE64')

print(f"\n1. Go to your GitHub repository")
print("2. Navigate to: Settings -> Secrets and variables -> Actions")
print(f"3. Find the secret named: {secret_name}")
print("4. Click 'Update' and paste the content from your clipboard (or {output_file})")
print(f"\nThe encoded token has been saved to: {output_file}")
print("="*70)
print("\nYou can also copy it directly from below:")
print("-" * 70)
print(encoded)
print("-" * 70)

