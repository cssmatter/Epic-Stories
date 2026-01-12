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

log "Error: All 5 hosting providers failed."
exit 1
