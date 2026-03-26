#!/usr/bin/env python3
"""
YouTube Song Downloader
Downloads songs from YouTube as MP3 files
"""

import os
import sys
import re
import argparse
from pathlib import Path

# Check if yt-dlp is installed
try:
    import yt_dlp
except ImportError:
    print("Error: yt-dlp is not installed.")
    print("Please install it using: pip install yt-dlp")
    sys.exit(1)


def sanitize_filename(filename):
    """Remove invalid characters from filenames"""
    # Remove or replace invalid characters for Windows/Mac/Linux
    invalid_chars = r'[<>:"/\\|?*\x00-\x1F]'
    filename = re.sub(invalid_chars, '_', filename)
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    return filename[:200] if len(filename) > 200 else filename


def download_song(song_name, output_dir="mp3"):
    """
    Download a song from YouTube as MP3

    Args:
        song_name: Name of the song to search and download
        output_dir: Directory to save the MP3 file
    """
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Searching for: {song_name}")

    # yt-dlp options for audio-only download
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': str(output_path / '%(title)s.%(ext)s'),
        'quiet': False,
        'no_warnings': False,
        'extractaudio': True,
        'audioformat': 'mp3',
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'default_search': 'ytsearch',
        'noprogress': False,
        'progress': True,
    }

    try:
        # Search and download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Search for the song
            search_query = f"ytsearch:{song_name} official audio"
            info = ydl.extract_info(search_query, download=True)

            if 'entries' in info:
                # Get the first result from search
                video_info = info['entries'][0]
                filename = ydl.prepare_filename(video_info)

                # Rename to .mp3 if needed
                if filename.endswith('.webm') or filename.endswith('.m4a'):
                    new_filename = filename.rsplit('.', 1)[0] + '.mp3'
                    if os.path.exists(filename):
                        # Overwrite existing mp3 if present
                        os.replace(filename, new_filename)
                        filename = new_filename

                print(f"\n[OK] Download completed!")
                print(f"  Saved to: {filename}")
                print(f"  Title: {video_info.get('title', 'Unknown')}")
                print(f"  Duration: {video_info.get('duration', 0)} seconds")
                print(f"  Channel: {video_info.get('uploader', 'Unknown')}")

                return filename
            else:
                print("Error: No search results found")
                return None

    except Exception as e:
        print(f"Error downloading song: {str(e)}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Download songs from YouTube as MP3'
    )
    parser.add_argument(
        'song_name',
        nargs='?',
        help='Name of the song to download'
    )
    parser.add_argument(
        '-o', '--output',
        default='mp3',
        help='Output directory (default: mp3)'
    )

    args = parser.parse_args()

    # If no song name provided, prompt user
    if not args.song_name:
        args.song_name = input("Enter song name: ").strip()

    if not args.song_name:
        print("Error: No song name provided")
        sys.exit(1)

    # Download the song
    download_song(args.song_name, args.output)


if __name__ == "__main__":
    main()
