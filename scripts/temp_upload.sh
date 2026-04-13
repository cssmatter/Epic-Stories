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
        URL=$(echo "$RESPONSE" | grep -E '^https://' | head -n 1)
        
        if [[ $URL == https://* ]]; then
            # Save release tag for cleanup
            RELEASE_TAG=$(echo "$RESPONSE" | grep "RELEASE_TAG=" | sed 's/RELEASE_TAG=//')
            if [ -n "$RELEASE_TAG" ]; then
                echo "$RELEASE_TAG" > /tmp/github_release_tag.txt
            fi
            echo "$URL"
            exit 0
        else
            log "GitHub Releases failed or not available."
            log "Response from github_release_upload.sh:"
            log "$RESPONSE"
        fi
    fi
else
    log "Skipping GitHub Releases (GITHUB_TOKEN not set)."
fi

# --- Try Catbox.moe ---
log "Trying Catbox.moe..."
RESPONSE=$(curl -sL -F "reqtype=fileupload" -F "fileToUpload=@$FILE_PATH" https://catbox.moe/user/api.php)
if [[ $RESPONSE == http* ]]; then
    echo "$RESPONSE"
    exit 0
fi
log "Catbox failed."

# --- Try 0x0.st (Reliable) ---
log "Trying 0x0.st..."
RESPONSE=$(curl -sL -F "file=@$FILE_PATH" https://0x0.st)
if [[ $RESPONSE == http* ]]; then
    echo "$RESPONSE"
    exit 0
fi
log "0x0.st failed."

# --- Try Pixeldrain (Reliable) ---
log "Trying Pixeldrain.com..."
RESPONSE=$(curl -sL -F "file=@$FILE_PATH" https://pixeldrain.com/api/file/)
# Response: {"id":"XXXX","success":true}
ID=$(echo "$RESPONSE" | grep -o '"id":"[^"]*"' | cut -d'"' -f4 | head -n 1)
if [ -n "$ID" ]; then
    echo "https://pixeldrain.com/api/file/$ID"
    exit 0
fi
log "Pixeldrain failed."

# --- Try Uguu.se (Reliable direct links) ---
log "Trying Uguu.se..."
# Response: {"success":true,"files":[{"url":"https:\/\/h.uguu.se\/xxx.mp4"}]}
RESPONSE=$(curl -sL -F "files[]=@$FILE_PATH" https://uguu.se/upload.php)
LINK=$(echo "$RESPONSE" | grep -o 'https:\\/\\/[^"]*' | sed 's/\\//g' | head -n 1)
if [[ $LINK == https://* ]]; then
    echo "$LINK"
    exit 0
fi
log "Uguu.se failed."


# --- Try Transfer.sh ---
log "Trying Transfer.sh..."
# curl --upload-file ./hello.txt https://transfer.sh/hello.txt
RESPONSE=$(curl -sL --upload-file "$FILE_PATH" "https://transfer.sh/$(basename $FILE_PATH)")
if [[ $RESPONSE == http* ]]; then
    echo "$RESPONSE"
    exit 0
fi
log "Transfer.sh failed."

# --- Try Bashupload.com ---
log "Trying Bashupload.com..."
RESPONSE=$(curl -sL --upload-file "$FILE_PATH" "https://bashupload.com/$(basename $FILE_PATH)")
LINK=$(echo "$RESPONSE" | grep -o 'https://bashupload.com/[^ ]*' | head -n 1)
if [[ $LINK == http* ]]; then
    echo "$LINK"
    exit 0
fi
log "Bashupload failed."

# --- Try Oshi.at ---
log "Trying Oshi.at..."
RESPONSE=$(curl -sL -F "f=@$FILE_PATH" https://oshi.at)
LINK=$(echo "$RESPONSE" | grep -o 'https://oshi.at/[a-zA-Z0-9]\{3,\}' | head -n 1)
if [[ $LINK == http* ]]; then
    echo "$LINK"
    exit 0
fi
log "Oshi.at failed."

log "Error: All hosting providers failed. Please check the logs above for details."
exit 1
