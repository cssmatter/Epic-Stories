import sys

with open('scripts/shayari/youtube_lyrics_extractor.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace 1: signature of download_audio
text = text.replace(
    'def download_audio(youtube_url: str, output_dir: str = ".", cookies_from_browser: str | None = "chrome") -> str:',
    'def download_audio(youtube_url: str, output_dir: str = ".", cookies_from_browser: str | None = "chrome") -> tuple[str, dict]:'
)

# Replace 2: initialize info
text = text.replace(
    '    mp3_path = ""',
    '    mp3_path = ""\n    info = {}'
)

# Replace 3: returns in download_audio
text = text.replace('return mp3_path', 'return mp3_path, info')

# Replace 4: Add fetch_exact_lyrics function after download_audio
new_func = '''
def fetch_exact_lyrics(info: dict, fallback_title: str) -> tuple[list[dict], str] | tuple[None, None]:
    if not syncedlyrics:
        return None, None
        
    track = info.get("track")
    artist = info.get("artist")
    
    if track and artist:
        query = f"{track} {artist}"
    else:
        query = info.get("title") or fallback_title
        
    print(f"\\n[INFO] Searching exact synced lyrics for: {query}")
    try:
        lrc = syncedlyrics.search(query)
    except Exception as e:
        print(f"(!) syncedlyrics error: {e}")
        return None, None
        
    if not lrc:
        print("[-] No exact LRC lyrics found.")
        return None, None
        
    print("[+] Exact LRC lyrics found!")
    
    # Parse LRC
    lines = lrc.strip().split("\\n")
    segments = []
    import re
    pattern = re.compile(r"^\\[(\\d{2}):(\\d{2}\\.\\d+)\\](.*)")
    
    for line in lines:
        match = pattern.match(line)
        if match:
            m, s, txt = match.groups()
            mm = int(m)
            ss = float(s)
            start_time = mm * 60 + ss
            txt = txt.strip()
            if txt:
                segments.append({"start": round(start_time, 2), "text": txt})
                
    if not segments:
        return None, None
        
    # Calculate end times
    for i in range(len(segments)):
        if i < len(segments) - 1:
            segments[i]["end"] = segments[i+1]["start"]
        else:
            segments[i]["end"] = round(segments[i]["start"] + 5.0, 2)
            
    # Detect language
    plain = "\\n".join(s["text"] for s in segments)
    try:
        detected_lang = lang_detect(plain)
    except:
        detected_lang = "unknown"
        
    print(f"[OK] Parsed {len(segments)} segments. Detected language: {detected_lang}")
    return segments, detected_lang
'''
text = text.replace('# 2. Transcribe MP3 with Whisper (local, free)', new_func + '\n# 2. Transcribe MP3 with Whisper (local, free)')

# Replace 5: process_youtube_url modifications
old_process = '''    # Step 1: Download
    mp3_path = download_audio(youtube_url, output_dir, cookies_from_browser=cookies_from_browser)

    # Step 2: Transcribe (auto-detect or forced language)
    segments, detected_language = transcribe_audio(
        mp3_path, model_name=whisper_model, language=language
    )'''

new_process = '''    # Step 1: Download
    mp3_path, info = download_audio(youtube_url, output_dir, cookies_from_browser=cookies_from_browser)

    # Step 2: Fetch Exact Lyrics or Transcribe
    title = Path(mp3_path).stem
    segments, detected_language = fetch_exact_lyrics(info, title)
    
    if not segments:
        # Fallback to Whisper
        print("[INFO] Falling back to Whisper transcription...")
        segments, detected_language = transcribe_audio(
            mp3_path, model_name=whisper_model, language=language
        )
    elif language:
        # Override detected language if user specifically forced one
        detected_language = language'''

text = text.replace(old_process, new_process)

with open('scripts/shayari/youtube_lyrics_extractor.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Patched successfully")
