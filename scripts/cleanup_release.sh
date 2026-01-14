#!/bin/bash

# Script to cleanup a GitHub Release
# Usage: ./cleanup_release.sh <release_tag> <github_token>

RELEASE_TAG=$1
GITHUB_TOKEN=$2

if [ -z "$RELEASE_TAG" ]; then
    echo "Error: RELEASE_TAG is required." >&2
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

log() {
    echo "$1" >&2
}

log "Deleting release with tag: $RELEASE_TAG"

# Get release by tag
RELEASE_INFO=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/releases/tags/$RELEASE_TAG")

RELEASE_ID=$(echo "$RELEASE_INFO" | grep -o '"id": [0-9]*' | head -1 | grep -o '[0-9]*')

if [ -z "$RELEASE_ID" ]; then
    log "Warning: Release not found or already deleted."
    exit 0
fi

# Delete the release
DELETE_RESPONSE=$(curl -s -w "%{http_code}" -X DELETE \
  -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/releases/$RELEASE_ID")

if [[ "$DELETE_RESPONSE" == "204" ]]; then
    log "Release deleted successfully"
    
    # Also delete the tag
    curl -s -X DELETE \
      -H "Authorization: token $GITHUB_TOKEN" \
      "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/git/refs/tags/$RELEASE_TAG" >/dev/null
    
    log "Tag deleted successfully"
else
    log "Warning: Failed to delete release. HTTP code: $DELETE_RESPONSE"
fi

exit 0
