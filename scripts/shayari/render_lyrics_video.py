#!/usr/bin/env python3
"""
Lyrics Video Renderer
Extracts lyrics and renders a synchronized video with embedded audio
"""

import os
import re
import sys
import json
import argparse
import subprocess
import base64
from pathlib import Path

# Import our extraction module
sys.path.insert(0, str(Path(__file__).parent))
from extract_lyrics import extract_lyrics_to_json


def create_props_json(lyrics_data: dict, mp3_path: Path, remotion_root: Path) -> Path:
    """
    Create Remotion props JSON file with base64-embedded audio

    Returns:
        Path to the props file
    """
    # Read MP3 and encode as base64
    print(f"   Embedding audio as base64 (this may take a moment)...")
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

    # Create props temp directory
    props_dir = remotion_root / "props-temp"
    props_dir.mkdir(parents=True, exist_ok=True)

    # Write props file
    props_file = props_dir / "lyrics-props.json"
    with open(props_file, 'w', encoding='utf-8') as f:
        json.dump(props, f, ensure_ascii=False, indent=2)

    print(f"[OK] Props file created: {props_file}")
    return props_file


def render_video(props_file: Path, output_path: Path, remotion_root: Path):
    """
    Execute Remotion render command with audio
    """
    print(f"\n>> Rendering video with audio...")

    # Build remotion render command using local binary
    if sys.platform == "win32":
        remotion_bin = remotion_root / "node_modules" / ".bin" / "remotion.cmd"
    else:
        remotion_bin = remotion_root / "node_modules" / ".bin" / "remotion"

    # Check if binary exists, fallback to npx
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
    print(f"   Working directory: {remotion_root}")

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

        if result.stderr:
            print("STDERR:", result.stderr)

        if result.returncode != 0:
            print(f"\n[ERROR] Render failed with exit code {result.returncode}")
            sys.exit(1)
        else:
            print(f"\n[OK] Video rendered successfully!")
            print(f"   Output: {output_path}")

    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Render failed: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("\n[ERROR] npx or remotion not found.")
        print("   Make sure node_modules are installed in remotion-shayari.")
        sys.exit(1)


def cleanup_files(*files: Path):
    """Remove temporary files"""
    for f in files:
        try:
            if f.exists():
                f.unlink()
                print(f"[CLEAN] {f}")
        except Exception as e:
            print(f"[WARN] Could not clean up {f}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Render lyrics video from MP3 using Remotion'
    )
    parser.add_argument(
        '--mp3',
        required=True,
        help='Path to the MP3 file'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output video file path (default: remotion-shayari/out/lyrics-<songname>.mp4)'
    )
    parser.add_argument(
        '--keep-props',
        action='store_true',
        help='Keep the props file (for debugging)'
    )

    args = parser.parse_args()

    # Resolve paths
    mp3_path = Path(args.mp3).resolve()
    script_dir = Path(__file__).parent.resolve()
    remotion_root = script_dir.parent.parent / "remotion-shayari"

    if not mp3_path.exists():
        print(f"Error: MP3 file not found: {mp3_path}")
        sys.exit(1)

    if not remotion_root.exists():
        print(f"Error: Remotion project not found: {remotion_root}")
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = Path(args.output).resolve()
    else:
        output_dir = remotion_root / "out"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"lyrics-{mp3_path.stem}.mp4"

    print("=" * 60)
    print("LYRICS VIDEO RENDERER")
    print("=" * 60)
    print(f"MP3 File: {mp3_path.name}")
    print(f"Output:  {output_path}")
    print(f"Remotion: {remotion_root}")
    print("=" * 60)

    # Step 1: Extract lyrics
    print("\n[STEP 1/3] Extracting lyrics from audio...")
    lyrics_json_path = mp3_path.with_suffix('.lyrics.json')
    lyrics_data = extract_lyrics_to_json(
        mp3_path,
        output_json_path=lyrics_json_path,
        model_size="base"
    )

    # Step 2: Create props with embedded audio
    print("\n[STEP 2/3] Creating Remotion props (with embedded audio)...")
    props_file = create_props_json(lyrics_data, mp3_path, remotion_root)

    # Step 3: Render video
    try:
        render_video(props_file, output_path, remotion_root)
    finally:
        # Cleanup props file (unless keep-props)
        if not args.keep_props:
            print("\n[STEP 3/3] Cleaning up temporary files...")
            cleanup_files(props_file)
        else:
            print("\n[STEP 3/3] Keeping props file (--keep-props)")

    print("\n[DONE] All done!")
    print(f"   Video: {output_path}")
    print(f"   Lyrics JSON: {lyrics_json_path}")


if __name__ == "__main__":
    main()
