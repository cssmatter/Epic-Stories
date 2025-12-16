import base64
import os

# Read the token.pickle file
if not os.path.exists('token.pickle'):
    print("ERROR: token.pickle not found!")
    print("Please run 'python daily_quote_video.py' first to generate the token.")
    exit(1)

with open('token.pickle', 'rb') as f:
    token_data = f.read()

# Encode to base64
encoded = base64.b64encode(token_data).decode('utf-8')

# Save to a file for easy copying
with open('token_base64.txt', 'w') as f:
    f.write(encoded)

print("SUCCESS: Token successfully encoded!")
print("\n" + "="*70)
print("INSTRUCTIONS: Update your GitHub Secret")
print("="*70)
print("\n1. Go to your GitHub repository")
print("2. Navigate to: Settings -> Secrets and variables -> Actions")
print("3. Find the secret named: TOKEN_PICKLE_BASE64")
print("4. Click 'Update' and paste the content from 'token_base64.txt'")
print("\nThe encoded token has been saved to: token_base64.txt")
print("="*70)
print("\nYou can also copy it directly from below:")
print("-"*70)
print(encoded)
print("-"*70)

