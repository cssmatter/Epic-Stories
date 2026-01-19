"""
TTS Generator for Epic Stories
Uses edge-tts with word-timing estimation from sentence boundaries
"""
import os
import hashlib
import asyncio
import subprocess
import json
import re
import config
import edge_tts

def get_ffmpeg_exe():
    # Prefer system ffmpeg if available
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return "ffmpeg"
    except:
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except:
            return "ffmpeg"

FFMPEG_EXE = get_ffmpeg_exe()


class TTSGenerator:
    def __init__(self):
        self.cache_dir = config.TTS_CACHE_DIR
        self.voice = "en-US-GuyNeural"
        
    def _get_cache_path(self, text):
        """Generate cache file path from text"""
        text_hash = hashlib.md5(f"{self.voice}_{text}".encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{text_hash}.mp3")
    
    def _get_json_path(self, text):
        """Generate path for timing data JSON"""
        text_hash = hashlib.md5(f"{self.voice}_{text}".encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{text_hash}.json")
    
    def _estimate_word_timings(self, sentence_text, start_time, duration):
        """
        Estimate word timings by linearly distributing duration based on word length
        """
        words = sentence_text.split()
        if not words:
            return []
            
        total_chars = sum(len(w) for w in words)
        word_timings = []
        current_time = start_time
        
        for word in words:
            word_len_ratio = len(word) / total_chars
            word_duration = duration * word_len_ratio
            
            word_timings.append({
                "word": word,
                "start": round(current_time, 3),
                "end": round(current_time + word_duration, 3)
            })
            current_time += word_duration
            
        return word_timings

    async def _amain(self, text, audio_path, json_path):
        communicate = edge_tts.Communicate(text, self.voice, rate="-10%")
        all_word_timings = []
        
        with open(audio_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "SentenceBoundary":
                    s_text = chunk["text"]
                    s_mid_start = chunk["offset"] / 10**7
                    s_mid_dur = chunk["duration"] / 10**7
                    words = self._estimate_word_timings(s_text, s_mid_start, s_mid_dur)
                    all_word_timings.extend(words)
                elif chunk["type"] == "WordBoundary":
                    all_word_timings.append({
                        "word": chunk["text"],
                        "start": chunk["offset"] / 10**7,
                        "end": (chunk["offset"] + chunk["duration"]) / 10**7
                    })
        
        unique_timings = []
        last_start = -1
        for t in sorted(all_word_timings, key=lambda x: x['start']):
            if abs(t['start'] - last_start) > 0.001:
                unique_timings.append(t)
                last_start = t['start']
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(unique_timings, f, indent=2)
        
        return unique_timings

    def generate_speech(self, text):
        if not text or not text.strip():
            return None, []
        
        audio_path = self._get_cache_path(text)
        json_path = self._get_json_path(text)
        
        if os.path.exists(audio_path) and os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data:
                        return audio_path, data
            except:
                pass
        
        try:
            print(f"Generating TTS & Timings: {text[:30]}...")
            
            # Using new loop to avoid conflicting with existing one if any
            word_timings = asyncio.run(self._amain(text, audio_path, json_path))
            return audio_path, word_timings
            
        except Exception as e:
            print(f"Error in generate_speech: {e}")
            return None, []

    def get_audio_duration(self, audio_path):
        if not os.path.exists(audio_path):
            return 0.0
        try:
            # Try ffprobe
            try:
                ffprobe_exe = FFMPEG_EXE.replace("ffmpeg", "ffprobe")
                cmd = [
                    ffprobe_exe, "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    audio_path
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    return float(result.stdout.strip())
            except:
                pass
            
            # Fallback to ffmpeg
            cmd = [FFMPEG_EXE, "-i", audio_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            match = re.search(r"Duration:\s(\d+):(\d+):(\d+\.\d+)", result.stderr)
            if match:
                h, m, s = match.groups()
                return int(h) * 3600 + int(m) * 60 + float(s)
                
        except Exception as e:
            print(f"Error getting duration: {e}")
        return 0.0


if __name__ == "__main__":
    generator = TTSGenerator()
    test_text = "The path of discipline is the journey of the soul."
    audio, timings = generator.generate_speech(test_text)
    print(f"Generated {len(timings)} word timings.")
    if timings:
        print(f"Duration from probe: {generator.get_audio_duration(audio)}s")
