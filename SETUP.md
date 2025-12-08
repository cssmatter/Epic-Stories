# YouTube Quote Video Automation - Setup Guide

## Overview

This GitHub Actions workflow automatically generates and uploads quote videos to YouTube every hour.

## Prerequisites

- Private GitHub repository
- YouTube channel with API access
- GitHub Personal Access Token (PAT)
- Media files: `light-effect.mp4`, `background-music.mp3`, `daily_quote_background_final.mp4`

## Setup Instructions

### 1. Prepare Your Repository

Ensure these files are in your repository:
- `daily_quote_video.py` - Main script
- `youtube_uploader.py` - YouTube upload module
- `quotes.json` - Quote database
- `requirements.txt` - Python dependencies
- `.github/workflows/upload-quote-video.yml` - Workflow file
- Media files (light-effect.mp4, background-music.mp3, daily_quote_background_final.mp4)

### 2. Configure GitHub Secrets

Go to your repository → Settings → Secrets and variables → Actions → New repository secret

Add the following secrets:

#### `PAT_TOKEN`
Your GitHub Personal Access Token: `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`

#### `CLIENT_SECRETS_JSON`
Copy the entire content of your `client_secrets.json` file:
```json
{
  "installed": {
    "client_id": "...",
    "project_id": "...",
    ...
  }
}
```

#### `TOKEN_PICKLE_BASE64`
Base64-encode your `token.pickle` file:

**On Windows (PowerShell):**
```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("token.pickle"))
```

**On Linux/Mac:**
```bash
base64 -w 0 token.pickle
```

Copy the output and add it as the secret value.

### 3. Commit Media Files

Make sure these files are committed to your repository:
```bash
git add light-effect.mp4 background-music.mp3 daily_quote_background_final.mp4
git commit -m "Add media files for video generation"
git push
```

### 4. Push Workflow Files

```bash
git add .github/workflows/upload-quote-video.yml requirements.txt .gitignore
git commit -m "Add GitHub Actions workflow for automated uploads"
git push
```

### 5. Enable GitHub Actions

1. Go to your repository → Actions tab
2. If prompted, enable GitHub Actions for your repository
3. You should see the "Upload Quote Video to YouTube" workflow

### 6. Test the Workflow

**Manual Trigger:**
1. Go to Actions → Upload Quote Video to YouTube
2. Click "Run workflow" → "Run workflow"
3. Monitor the workflow execution
4. Check for errors in the logs

**Automatic Schedule:**
- The workflow runs automatically every hour at minute 0 (e.g., 1:00, 2:00, 3:00)
- First scheduled run will be at the next hour mark

## Monitoring

### Check Workflow Status
- Go to Actions tab to see workflow runs
- Green checkmark = Success
- Red X = Failed (check logs)

### Verify Uploads
- Check your YouTube channel for new videos
- Videos are uploaded as "private" by default
- Check the "Daily Status Shorts" playlist

### Monitor Quotes
- After each successful upload, `quotes.json` is automatically updated
- The published quote is removed from the file
- When all quotes are exhausted, the workflow stops gracefully

## Troubleshooting

### Workflow Fails with "No quotes remaining"
- Add more quotes to `quotes.json`
- Commit and push the changes

### Authentication Errors
- Verify `CLIENT_SECRETS_JSON` secret is correct
- Verify `TOKEN_PICKLE_BASE64` secret is correct
- Token may have expired - regenerate locally and update secret

### Media File Not Found
- Ensure all media files are committed to the repository
- Check file names match exactly (case-sensitive)

### Git Push Fails
- Verify `PAT_TOKEN` has repo write permissions
- Check token hasn't expired

## Important Notes

⚠️ **Security**: Never commit `client_secrets.json` or `token.pickle` directly to the repository. They are listed in `.gitignore`.

⚠️ **YouTube Quotas**: YouTube has daily upload limits (typically 50-100 videos/day). With hourly uploads, you'll upload 24 videos/day.

⚠️ **Quote Management**: You have 20 quotes. At 1 per hour, they'll last ~20 hours. Add more quotes regularly.

⚠️ **GitHub Actions Minutes**: Private repositories get 2,000 free minutes/month. Each workflow run takes ~2-3 minutes. Monitor your usage.

## Customization

### Change Schedule
Edit `.github/workflows/upload-quote-video.yml`:
```yaml
schedule:
  - cron: '0 * * * *'  # Every hour
  # - cron: '0 */6 * * *'  # Every 6 hours
  # - cron: '0 9 * * *'  # Daily at 9 AM UTC
```

### Change Video Privacy
Edit `youtube_uploader.py` line 66:
```python
'privacyStatus': 'public',  # or 'unlisted', 'private'
```

## Support

If you encounter issues:
1. Check workflow logs in Actions tab
2. Verify all secrets are set correctly
3. Test the script locally first: `python daily_quote_video.py`
