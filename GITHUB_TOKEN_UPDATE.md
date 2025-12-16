# Fixing GitHub Actions Authentication Issues

## Problem
When the YouTube OAuth token expires in GitHub Actions, the workflow fails because it tries to open a browser in a headless environment.

## Solution
The code has been updated to detect CI environments and provide clear error messages instead of attempting browser-based authentication.

## How to Update the Token

When you see an error in GitHub Actions about expired tokens, follow these steps:

### Step 1: Authenticate Locally
Run the script on your local machine to refresh the token:
```bash
python daily_quote_video.py
```

This will open a browser window for you to authenticate with Google. Complete the authentication process.

### Step 2: Encode the Token
After successful authentication, run the helper script:
```bash
python update_github_token.py
```

This will:
- Read your `token.pickle` file
- Encode it to base64
- Save it to `token_base64.txt`
- Display the encoded token in the console

### Step 3: Update GitHub Secret
1. Go to your GitHub repository
2. Navigate to: **Settings → Secrets and variables → Actions**
3. Find the secret named: `TOKEN_PICKLE_BASE64`
4. Click **Update**
5. Paste the content from `token_base64.txt` (or copy from the console output)
6. Click **Update secret**

### Step 4: Verify
Trigger the GitHub Actions workflow manually or wait for the next scheduled run. The workflow should now complete successfully.

## Token Expiration
Google OAuth tokens typically expire after several months. You'll need to repeat this process whenever the token expires.

## Security Notes
- Never commit `token.pickle` or `token_base64.txt` to your repository
- These files are already in `.gitignore`
- The `client_secrets.json` should also remain private
- GitHub Secrets are encrypted and safe to use
