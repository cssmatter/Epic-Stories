#!/usr/bin/env python3
"""
Quick test video generator with English lyrics (30 seconds)
"""

import json
import argparse
from pathlib import Path

def create_test_lyrics(duration_seconds=30, words_per_second=3):
    """Generate simple English test lyrics"""
    sample_words = [
        "Hello", "World", "Testing", "One", "Two", "Three",
        "Four", "Five", "Six", "Seven", "Eight", "Nine",
        "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
        "This", "is", "a", "test", "lyrics", "video",
        "Remotion", "animation", "word", "by", "word", "fade"
    ]

    lyrics = []
    time_step = 1.0 / words_per_second  # seconds per word

    for i in range(int(duration_seconds * words_per_second)):
        word_idx = i % len(sample_words)
        start_time = i * time_step
        end_time = start_time + time_step

        lyrics.append({
            "word": sample_words[word_idx],
            "start": round(start_time, 3),
            "end": round(end_time, 3)
        })

    return lyrics


def create_test_props(output_props_path: Path):
    """Create a test props file for Remotion"""
    lyrics = create_test_lyrics(duration_seconds=30)

    props = {
        "audioUrl": "",  # No audio for test
        "lyrics": lyrics,
        "title": "Test Song",
        "artist": "Test Artist",
        "backgroundColor": "#0a0a0a"
    }

    with open(output_props_path, 'w', encoding='utf-8') as f:
        json.dump(props, f, ensure_ascii=False, indent=2)

    print(f"[OK] Test props created: {output_props_path}")
    print(f"   Generated {len(lyrics)} words over 30 seconds")
    return props


def render_test_video():
    """Render a 30-second test video"""
    import subprocess
    import sys

    script_dir = Path(__file__).parent.resolve()
    remotion_root = script_dir.parent.parent / "remotion-shayari"

    if not remotion_root.exists():
        print(f"Error: Remotion project not found: {remotion_root}")
        return False

    # Create props file
    props_dir = remotion_root / "props-temp"
    props_dir.mkdir(parents=True, exist_ok=True)
    props_file = props_dir / "test-props.json"

    create_test_props(props_file)

    # Output path
    output_dir = remotion_root / "out"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "test-lyrics-30sec.mp4"

    print("\n[RENDERING] Test video (30 seconds)...")

    # Build command
    if sys.platform == "win32":
        remotion_bin = remotion_root / "node_modules" / ".bin" / "remotion.cmd"
    else:
        remotion_bin = remotion_root / "node_modules" / ".bin" / "remotion"

    if not remotion_bin.exists():
        cmd = ["npx", "remotion", "render", "src/index.tsx", "LyricsVideo", str(output_path), f"--props={props_file}"]
    else:
        cmd = [str(remotion_bin), "render", "src/index.tsx", "LyricsVideo", str(output_path), f"--props={props_file}"]

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
        if result.stderr:
            print("STDERR:", result.stderr)

        if result.returncode == 0:
            print(f"\n[SUCCESS] Test video created!")
            print(f"   Output: {output_path}")
            print(f"   Duration: 30 seconds")

            # Cleanup
            props_file.unlink()
            print(f"[CLEAN] Removed {props_file}")

            return True
        else:
            print(f"[ERROR] Render failed with exit code {result.returncode}")
            return False

    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Create a 30-second test video with English lyrics'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output video file path (default: remotion-shayari/out/test-lyrics-30sec.mp4)'
    )

    args = parser.parse_args()
    render_test_video()


if __name__ == "__main__":
    main()
