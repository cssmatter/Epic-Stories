#!/usr/bin/env python3
"""
One-command lyrics video creator
Just provide a song name - it will download and render automatically!
"""

import os
import sys
import json
import argparse
import subprocess
import base64
from pathlib import Path

# Import our modules
sys.path.insert(0, str(Path(__file__).parent))
from extract_lyrics import extract_lyrics_to_json
from download_youtube_song import download_song as download_youtube_song


def create_props_json(lyrics_data: dict) -> Path:
    """Create Remotion props JSON file with embedded audio"""
    # Read the MP3 file and encode as base64
    mp3_path = Path(lyrics_data["audio_file"])
    print(f"   Embedding audio as base64...")

    with open(mp3_path, 'rb') as f:
        audio_bytes = f.read()
    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
    audio_data_url = f"data:audio/mpeg;base64,{audio_b64}"

    props = {
        "audioUrl": audio_data_url,
        "lyrics": lyrics_data["lyrics"],
        "title": lyrics_data["title"],
        "artist": lyrics_data["artist"],
        "backgroundColor": "#0a0a0a",
    }

    # Get remotion root
    script_dir = Path(__file__).parent.resolve()
    remotion_root = script_dir.parent.parent / "remotion-shayari"

    # Create props temp directory
    props_dir = remotion_root / "props-temp"
    props_dir.mkdir(parents=True, exist_ok=True)

    # Write props file
    safe_title = "".join(c for c in lyrics_data["title"][:30] if c.isalnum() or c in (' ', '-', '_')).rstrip()
    props_file = props_dir / f"lyrics-props-{safe_title}.json"
    with open(props_file, 'w', encoding='utf-8') as f:
        json.dump(props, f, ensure_ascii=False, indent=2)

    print(f"[OK] Props file created")
    return props_file


def render_video(props_file: Path, output_path: Path, remotion_root: Path):
    """Execute Remotion render command"""
    print(f"\n>> Rendering video...")

    # Build command
    if sys.platform == "win32":
        remotion_bin = remotion_root / "node_modules" / ".bin" / "remotion.cmd"
    else:
        remotion_bin = remotion_root / "node_modules" / ".bin" / "remotion"

    if not remotion_bin.exists():
        print(f"   [WARN] Local remotion binary not found, falling back to npx")
        cmd = [
            "npx", "remotion", "render",
            "src/index.tsx",
            "LyricsVideo",
            str(output_path),
            f"--props={props_file}"
        ]
    else:
        cmd = [
            str(remotion_bin),
            "render",
            "src/index.tsx",
            "LyricsVideo",
            str(output_path),
            f"--props={props_file}"
        ]

    print(f"   Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            cwd=remotion_root,
            capture_output=True,
            text=True,
            shell=False,
        )

        if result.stdout:
            print(result.stdout)

        if result.stderr and "Rendered" in result.stderr:
            # Show progress in realtime
            print(result.stderr)
        elif result.stderr:
            print("STDERR:", result.stderr)

        if result.returncode != 0:
            print(f"\n[ERROR] Render failed with exit code {result.returncode}")
            return False
        else:
            print(f"\n[OK] Video rendered successfully!")
            return True

    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Render failed: {e}")
        return False
    except FileNotFoundError:
        print("\n[ERROR] npx or remotion not found.")
        return False


def cleanup_temp_files(props_file: Path):
    """Remove temporary props file"""
    try:
        if props_file.exists():
            props_file.unlink()
            print(f"[CLEAN] Cleaned up: {props_file}")
    except Exception as e:
        print(f"[WARN] Could not clean up {props_file}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Create lyrics video from a song name (download + render)'
    )
    parser.add_argument(
        'song_name',
        help='Song name to download and convert (e.g., "Shape of You Ed Sheeran")'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output video file path (default: remotion-shayari/out/lyrics-<song>.mp4)'
    )
    parser.add_argument(
        '--keep-props',
        action='store_true',
        help='Keep props file for debugging'
    )

    args = parser.parse_args()

    script_dir = Path(__file__).parent.resolve()
    remotion_root = script_dir.parent.parent / "remotion-shayari"
    mp3_dir = script_dir.parent.parent / "mp3"  # Project root mp3 folder

    # Check remotion exists
    if not remotion_root.exists():
        print(f"Error: Remotion project not found: {remotion_root}")
        sys.exit(1)

    # Create mp3 directory if needed
    mp3_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(" LYRIC VIDEO CREATOR - ALL IN ONE")
    print("=" * 70)
    print(f"Song Name: {args.song_name}")
    print(f"MP3 Dir:   {mp3_dir}")
    print(f"Output:    {args.output or 'auto'}")
    print("=" * 70)

    # STEP 1: Download the song
    print("\n[STEP 1/4] Downloading song from YouTube...")
    try:
        mp3_filename = download_youtube_song(args.song_name, output_dir=str(mp3_dir))
        if not mp3_filename:
            print("[ERROR] Download failed")
            sys.exit(1)
        mp3_path = mp3_dir / mp3_filename
        print(f"[OK] Downloaded: {mp3_path}")
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        sys.exit(1)

    # STEP 2: Extract lyrics
    print("\n[STEP 2/4] Extracting lyrics with Whisper AI...")
    try:
        lyrics_json_path = mp3_path.with_suffix('.lyrics.json')
        lyrics_data = extract_lyrics_to_json(
            mp3_path,
            output_json_path=lyrics_json_path,
            model_size="base"
        )
        print(f"[OK] Lyrics extracted ({len(lyrics_data['lyrics'])} sentences)")
    except Exception as e:
        print(f"[ERROR] Lyrics extraction failed: {e}")
        sys.exit(1)

    # STEP 3: Create props
    print("\n[STEP 3/4] Preparing Remotion props...")
    try:
        props_file = create_props_json(lyrics_data)
    except Exception as e:
        print(f"[ERROR] Failed to create props: {e}")
        sys.exit(1)

    # STEP 4: Determine output path
    if args.output:
        output_path = Path(args.output).resolve()
    else:
        output_dir = remotion_root / "out"
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_name = "".join(c for c in args.song_name[:50] if c.isalnum() or c in (' ', '-', '_')).rstrip()
        output_path = output_dir / f"lyrics-{safe_name}.mp4"

    # STEP 5: Render video
    print("\n[STEP 4/4] Rendering video (this takes 2-5 minutes)...")
    success = render_video(props_file, output_path, remotion_root)

    # Cleanup
    if success and not args.keep_props:
        cleanup_temp_files(props_file)

    if success:
        print("\n" + "=" * 70)
        print("[SUCCESS] All done!")
        print(f"Video: {output_path}")
        print(f"Size:  {output_path.stat().st_size // (1024*1024)} MB")
        print("=" * 70)
    else:
        print("\n[ERROR] Video rendering failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
