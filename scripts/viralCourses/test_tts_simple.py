
from TTS.api import TTS
import os

print("Initializing TTS...")
try:
    # Try a faster model for testing first, or checks if the big one works
    # usage: tts = TTS(model_name="tts_models/en/ljspeech/glow-tts", progress_bar=True, gpu=False)
    # But user wants consistency. Let's try the one from the script.
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
    
    print("TTS initialized. Generating audio...")
    tts.tts_to_file(text="This is a test of the emergency broadcast system.", file_path="test_tts_output.wav", speaker="Damien Black", language="en")
    print("Audio generated: test_tts_output.wav")
except Exception as e:
    print(f"TTS Error: {e}")
