#!/usr/bin/env python3
"""
Extract lyrics with timestamps from audio using Whisper
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import timedelta

try:
    from faster_whisper import WhisperModel
except ImportError:
    print("Error: faster-whisper is not installed.")
    print("Please install it using: pip install faster-whisper")
    sys.exit(1)


def format_timestamp(seconds):
    """Convert seconds to MM:SS.ms format"""
    td = timedelta(seconds=seconds)
    minutes = int(td.total_seconds() // 60)
    secs = td.total_seconds() % 60
    return f"{minutes:02d}:{secs:06.3f}"


def sanitize_text(text):
    """Clean up transcribed text"""
    # Remove excessive whitespace
    text = ' '.join(text.split())
    # Keep original punctuation
    return text.strip()


def extract_lyrics_to_json(mp3_path, output_json_path=None, model_size="base"):
    """
    Transcribe audio and extract sentence-level timestamps

    Args:
        mp3_path: Path to the MP3 file
        output_json_path: Optional output path for JSON
        model_size: Whisper model size (tiny, base, small, medium, large-v3)

    Returns:
        dict: Lyrics data with title, artist, duration, and sentence-level timestamps
    """
    mp3_path = Path(mp3_path)

    if not mp3_path.exists():
        print(f"Error: File not found: {mp3_path}")
        sys.exit(1)

    # Derive title and artist from filename
    filename = mp3_path.stem
    # Typical format: "Awarapan Banjarapan - KK (Lyrics)"
    if " - " in filename:
        title, rest = filename.split(" - ", 1)
        artist = rest.split("(")[0].strip()
    else:
        title = filename
        artist = "Unknown"

    # Use simple ASCII markers to avoid Windows console encoding issues
    print(f"[+] Processing: {mp3_path.name}")
    print(f"   Title: {title}")
    print(f"   Artist: {artist}")
    print(f"   Loading Whisper model ({model_size})...")

    # Load Whisper model
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    print(f"   Transcribing audio (this may take a while)...")

    # Transcribe with word-level timestamps
    segments, info = model.transcribe(
        str(mp3_path),
        beam_size=5,
        vad_filter=True,
        word_timestamps=True,
    )

    duration = info.duration
    print(f"   Audio duration: {format_timestamp(duration)}")
    print(f"   Language detected: {info.language}")

    # Collect all words with timestamps
    all_words = []
    word_count = 0

    for segment in segments:
        for word in segment.words:
            all_words.append({
                "word": word.word,
                "start": round(word.start, 3),
                "end": round(word.end, 3)
            })
            word_count += 1

    print(f"   Extracted {word_count} words")

    # Group words into sentences based on punctuation and natural pauses
    sentences = []
    current_sentence_words = []
    sentence_index = 0

    for i, word in enumerate(all_words):
        current_sentence_words.append(word)

        # Check if this word ends a sentence (has sentence-ending punctuation)
        word_text = word['word'] if isinstance(word, dict) else word.word
        is_sentence_end = word_text and word_text[-1] in ['.', '!', '?', '।', '॥']

        # Check for long pause after this word (> 1 second) indicating sentence break
        next_word = all_words[i + 1] if i + 1 < len(all_words) else None
        if next_word:
            next_word_end = next_word['end'] if isinstance(next_word, dict) else next_word.end
            current_word_end = word['end'] if isinstance(word, dict) else word.end
            long_pause = (next_word['start'] if isinstance(next_word, dict) else next_word.start) - current_word_end > 1.0
        else:
            long_pause = False

        # Also force break if we've accumulated many words (max 10) without punctuation
        max_words_reached = len(current_sentence_words) >= 10

        if is_sentence_end or long_pause or max_words_reached or i == len(all_words) - 1:
            if current_sentence_words:
                # Create sentence entry
                sentence_words = []
                sentence_text_parts = []
                for w in current_sentence_words:
                    if isinstance(w, dict):
                        sentence_words.append(w)
                        sentence_text_parts.append(w['word'])
                    else:
                        sentence_words.append({'word': w.word, 'start': w.start, 'end': w.end})
                        sentence_text_parts.append(w.word)

                sentence_text = ' '.join(sentence_text_parts).strip()
                sentence_start = sentence_words[0]['start']
                sentence_end = sentence_words[-1]['end']

                sentences.append({
                    "sentence": sentence_text,
                    "start": sentence_start,
                    "end": sentence_end,
                    "words": sentence_words
                })
            current_sentence_words = []
            sentence_index += 1

    print(f"   Grouped into {len(sentences)} sentences")

    # Build result
    result = {
        "title": title,
        "artist": artist,
        "duration": round(duration, 3),
        "audio_file": str(mp3_path),
        "language": info.language,
        "lyrics": sentences  # Sentence-level data instead of word-level
    }

    # Save to JSON
    if output_json_path is None:
        output_json_path = mp3_path.with_suffix('.lyrics.json')

    output_json_path = Path(output_json_path)
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Lyrics extracted successfully!")
    print(f"   Saved to: {output_json_path}")
    # Don't print word preview on Windows to avoid encoding errors, rely on JSON

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Extract lyrics with timestamps from MP3 using Whisper'
    )
    parser.add_argument(
        'mp3_file',
        help='Path to the MP3 file'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output JSON file path (default: same as MP3 with .lyrics.json)'
    )
    parser.add_argument(
        '-m', '--model',
        default='base',
        choices=['tiny', 'base', 'small', 'medium', 'large-v3'],
        help='Whisper model size (default: base)'
    )

    args = parser.parse_args()

    extract_lyrics_to_json(args.mp3_file, args.output, args.model)


if __name__ == "__main__":
    main()
