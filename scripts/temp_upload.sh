#!/bin/bash

# Script to upload a file to temporary hosting with fallbacks
# Usage: ./temp_upload.sh <file_path>

FILE_PATH=$1

if [ ! -f "$FILE_PATH" ]; then
    echo "Error: File $FILE_PATH not found." >&2
    exit 1
fi

log() {
    echo "$1" >&2
}

log "Attempting to upload $FILE_PATH to temporary hosts..."

# --- Try GitHub Releases (Most reliable in CI/CD) ---
if [ -n "$GITHUB_TOKEN" ]; then
    log "Trying GitHub Releases..."
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    if [ -f "$SCRIPT_DIR/github_release_upload.sh" ]; then
        chmod +x "$SCRIPT_DIR/github_release_upload.sh"
        RESPONSE=$("$SCRIPT_DIR/github_release_upload.sh" "$FILE_PATH" "$GITHUB_TOKEN" 2>&1)
        
        # Extract the URL (first line) and release info (stderr)
        URL=$(echo "$RESPONSE" | grep -E '^https://' | head -1)
        
        if [[ $URL == https://* ]]; then
            # Save release tag for cleanup
            RELEASE_TAG=$(echo "$RESPONSE" | grep "RELEASE_TAG=" | sed 's/RELEASE_TAG=//')
            if [ -n "$RELEASE_TAG" ]; then
                echo "$RELEASE_TAG" > /tmp/github_release_tag.txt
            fi
            echo "$URL"
            exit 0
        fi
    fi
    log "GitHub Releases failed or not available."
else
    log "Skipping GitHub Releases (GITHUB_TOKEN not set)."
fi

# --- Try Catbox.moe ---
log "Trying Catbox.moe..."
RESPONSE=$(curl -s -F "reqtype=fileupload" -F "fileToUpload=@$FILE_PATH" https://catbox.moe/user/api.php)
if [[ $RESPONSE == http* ]]; then
    echo "$RESPONSE"
    exit 0
fi
log "Catbox failed."

# --- Try File.io (Very reliable) ---
log "Trying File.io..."
RESPONSE=$(curl -s -F "file=@$FILE_PATH" https://file.io)
# Response: {"success":true,"link":"https://file.io/XXXX",...}
LINK=$(echo "$RESPONSE" | grep -o 'https://file.io/[a-zA-Z0-9]*')
if [[ $LINK == http* ]]; then
    echo "$LINK"
    exit 0
fi
log "File.io failed."

# --- Try Transfer.sh ---
log "Trying Transfer.sh..."
# curl --upload-file ./hello.txt https://transfer.sh/hello.txt
RESPONSE=$(curl -s --upload-file "$FILE_PATH" "https://transfer.sh/$(basename $FILE_PATH)")
if [[ $RESPONSE == http* ]]; then
    echo "$RESPONSE"
    exit 0
fi
log "Transfer.sh failed."

# --- Try Bashupload.com ---
log "Trying Bashupload.com..."
RESPONSE=$(curl -s --upload-file "$FILE_PATH" "https://bashupload.com/$(basename $FILE_PATH)")
LINK=$(echo "$RESPONSE" | grep -o 'https://bashupload.com/[^ ]*')
if [[ $LINK == http* ]]; then
    echo "$LINK"
    exit 0
fi
log "Bashupload failed."

# --- Try Oshi.at ---
log "Trying Oshi.at..."
RESPONSE=$(curl -s -F "f=@$FILE_PATH" https://oshi.at)
LINK=$(echo "$RESPONSE" | grep -o 'https://oshi.at/[a-zA-Z0-9]*')
if [[ $LINK == http* ]]; then
    echo "$LINK"
    exit 0
fi
log "Oshi.at failed."

log "Error: All hosting providers failed."
exit 1
