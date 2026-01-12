#!/bin/bash

# Script to upload a file to temporary hosting with fallbacks
# Usage: ./temp_upload.sh <file_path>

FILE_PATH=$1

if [ ! -f "$FILE_PATH" ]; then
    echo "Error: File $FILE_PATH not found."
    exit 1
fi

echo "Attempting to upload $FILE_PATH to temporary hosts..."

# --- Try Catbox.moe ---
echo "Trying Catbox.moe..."
VIDEO_URL=$(curl -s -F "reqtype=fileupload" -F "fileToUpload=@$FILE_PATH" https://catbox.moe/user/api.php)

if [[ $VIDEO_URL == http* ]]; then
    echo "$VIDEO_URL"
    exit 0
fi
echo "Catbox failed. Response: $VIDEO_URL"

# --- Try Bashupload.com ---
echo "Trying Bashupload.com..."
# Bashupload returns the URL in the response body directly
VIDEO_URL=$(curl -s --upload-file "$FILE_PATH" "https://bashupload.com/$(basename $FILE_PATH)")

if [[ $VIDEO_URL == http* ]]; then
    # Bashupload sometimes adds extra text, extract just the URL
    VIDEO_URL=$(echo "$VIDEO_URL" | grep -o 'https://bashupload.com/[^ ]*')
    echo "$VIDEO_URL"
    exit 0
fi
echo "Bashupload failed."

# --- Try Oshi.at ---
echo "Trying Oshi.at..."
# Oshi returns a multi-line response, the URL is on its own line
VIDEO_URL=$(curl -s -F "f=@$FILE_PATH" https://oshi.at | grep -o 'https://oshi.at/[a-zA-Z0-9]*')

if [[ $VIDEO_URL == http* ]]; then
    echo "$VIDEO_URL"
    exit 0
fi
echo "Oshi.at failed."

echo "Error: All hosting providers failed."
exit 1
