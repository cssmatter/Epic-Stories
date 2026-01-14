#!/bin/bash

# Script to upload a file to GitHub Releases and return the public URL
# Usage: ./github_release_upload.sh <file_path> <github_token>

FILE_PATH=$1
GITHUB_TOKEN=$2

if [ ! -f "$FILE_PATH" ]; then
    echo "Error: File $FILE_PATH not found." >&2
    exit 1
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_TOKEN is required." >&2
    exit 1
fi

# Get repository info from git
REPO_OWNER=$(git config --get remote.origin.url | sed -n 's/.*github.com[:/]\([^/]*\)\/.*/\1/p')
REPO_NAME=$(git config --get remote.origin.url | sed -n 's/.*github.com[:/][^/]*\/\([^.]*\).*/\1/p')

if [ -z "$REPO_OWNER" ] || [ -z "$REPO_NAME" ]; then
    echo "Error: Could not determine repository owner and name." >&2
    exit 1
fi

# Generate unique release tag
TIMESTAMP=$(date +%s)
RELEASE_TAG="temp-video-$TIMESTAMP"
FILE_NAME=$(basename "$FILE_PATH")

log() {
    echo "$1" >&2
}

log "Creating temporary release: $RELEASE_TAG"

# Create a temporary release
CREATE_RESPONSE=$(curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/releases" \
  -d "{
    \"tag_name\": \"$RELEASE_TAG\",
    \"name\": \"Temporary Video Upload\",
    \"body\": \"Temporary release for Instagram video upload. Will be deleted automatically.\",
    \"draft\": false,
    \"prerelease\": true
  }")

# Extract release ID and upload URL
RELEASE_ID=$(echo "$CREATE_RESPONSE" | grep -o '"id": [0-9]*' | head -1 | grep -o '[0-9]*')
UPLOAD_URL=$(echo "$CREATE_RESPONSE" | grep -o '"upload_url": "[^"]*"' | sed 's/"upload_url": "\([^{]*\).*/\1/')

if [ -z "$RELEASE_ID" ] || [ -z "$UPLOAD_URL" ]; then
    log "Error: Failed to create release."
    log "Response: $CREATE_RESPONSE"
    exit 1
fi

log "Release created with ID: $RELEASE_ID"
log "Uploading asset: $FILE_NAME"

# Upload the file as a release asset
UPLOAD_RESPONSE=$(curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: video/mp4" \
  --data-binary "@$FILE_PATH" \
  "${UPLOAD_URL}?name=${FILE_NAME}")

# Extract the browser download URL
DOWNLOAD_URL=$(echo "$UPLOAD_RESPONSE" | grep -o '"browser_download_url": "[^"]*"' | sed 's/"browser_download_url": "\([^"]*\)"/\1/')

if [ -z "$DOWNLOAD_URL" ]; then
    log "Error: Failed to upload asset."
    log "Response: $UPLOAD_RESPONSE"
    
    # Cleanup: Delete the release
    curl -s -X DELETE \
      -H "Authorization: token $GITHUB_TOKEN" \
      "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/releases/$RELEASE_ID" >/dev/null
    
    exit 1
fi

log "Asset uploaded successfully"
log "Download URL: $DOWNLOAD_URL"

# Output the download URL and release ID (for cleanup later)
echo "$DOWNLOAD_URL"
echo "RELEASE_ID=$RELEASE_ID" >&2
echo "RELEASE_TAG=$RELEASE_TAG" >&2

exit 0
