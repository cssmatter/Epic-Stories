#!/usr/bin/env python3
"""
Master Orchestrator for YouTube Shorts Generation.
Usage: python automate_shorts.py "Song Name or URL"
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path

# Fix Windows console encoding for emoji/Unicode characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def run_step(command, description):
    print(f"\n[STEP] {description}")
    print(f"[CMD] {' '.join(command)}")
    try:
        # Capture output for better debugging on failure
        result = subprocess.run(
            command, 
            check=True, 
            encoding="utf-8", 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            errors="replace"
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Error during {description}:")
        print(e.output)
        return False

def find_latest_files(output_dir, query_hint):
    """Find the most recent .json and .mp3 in the output directory that match keywords."""
    files = list(Path(output_dir).glob("*"))
    if not files:
        return None, None
    
    # Get keywords from query (ignore small words)
    hint_str = str(query_hint or "")
    keywords = [k.lower() for k in hint_str.split() if len(k) > 2]
    
    def score_file(f):
        # Score based on keyword match + recency
        score = 0
        name = f.name.lower()
        for k in keywords:
            if k in name:
                score += 10
        # Add a tiny bit for recency (within last 10 mins)
        mtime = os.path.getmtime(f)
        if (time.time() - mtime) < 600:
            score += 5
        return score

    json_files = sorted([f for f in files if f.suffix == ".json"], key=score_file, reverse=True)
    mp3_files = sorted([f for f in files if f.suffix == ".mp3"], key=score_file, reverse=True)
    
    if not json_files or not mp3_files:
        return None, None
    
    return str(json_files[0]), str(mp3_files[0])

def main():
    parser = argparse.ArgumentParser(description="Automate YouTube Shorts Generation")
    parser.add_argument("query", nargs="?", help="Song name or YouTube URL")
    parser.add_argument("--url", help="Explicit YouTube URL")
    parser.add_argument("--model", default="base", help="Whisper model (base, medium, etc.)")
    parser.add_argument("--quality", default="l", help="Video quality (l, m, h)")
    parser.add_argument("--output-dir", default="output", help="Directory for assets")
    parser.add_argument("--cookies", default="none", help="Cookie source (chrome, brave, none)")
    
    args = parser.parse_args()
    
    if not args.query and not args.url:
        parser.print_help()
        sys.exit(1)
        
    # Step 1: Extract Lyrics and Download MP3
    query_or_url = args.url or args.query
    raw_query = query_or_url
    if not query_or_url.startswith("http"):
        query_or_url = f"ytsearch1:{query_or_url}"
        
    extractor_cmd = [
        sys.executable, "youtube_lyrics_extractor.py",
        query_or_url,
        "--model", args.model,
        "--output-dir", args.output_dir,
        "--cookies-from-browser", args.cookies
    ]
    
    if not run_step(extractor_cmd, "Extracting Lyrics and Downloading MP3"):
        sys.exit(1)
    
    # Step 2: Detection
    json_path, mp3_path = find_latest_files(args.output_dir, args.query)
    if not json_path or not mp3_path:
        print("❌ Could not find the generated JSON or MP3 files.")
        sys.exit(1)
        
    print(f"🔍 Detected Assets:")
    print(f"   JSON: {json_path}")
    print(f"   MP3:  {mp3_path}")
    
    # Step 3: Render Video
    video_output = Path(args.output_dir) / f"{Path(json_path).stem}_short.mp4"
    render_cmd = [
        sys.executable, "create_shorts_video_manim.py",
        "--json", json_path,
        "--mp3", mp3_path,
        "--output", str(video_output),
        "--quality", args.quality
    ]
    
    if not run_step(render_cmd, "Rendering Manim Video"):
        sys.exit(1)
        
    print(f"\n[DONE] SUCCESS! Your YouTube Short is ready at:")
    print(f"[FILE] {video_output}")

if __name__ == "__main__":
    main()
