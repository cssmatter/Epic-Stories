
from TTS.api import TTS
import os

# Initialize XTTS v2
print("Initializing XTTS v2...")
# This will download the model if not present, which might be large.
try:
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
    
    TEXT = "तुम्हें केवल कर्म करने का अधिकार है, उसके फल की चिंता नहीं करनी चाहिए।"
    OUTPUT_FILE = "test_xtts_hindi.wav"
    
    # We need a speaker reference for XTTS. 
    # Usually we can use a sample from the dataset or provide a wav file.
    # For testing, let's see if we can use a built-in speaker.
    # XTTS requires speaker_wav or speaker (for built-in speakers).
    
    # Let's list available speakers if possible
    print("Available speakers:", tts.speakers)
    
    # If speakers are available, use the first one for testing
    if tts.speakers:
        speaker = tts.speakers[0]
        print(f"Using speaker: {speaker}")
        tts.tts_to_file(text=TEXT, speaker=speaker, language="hi", file_path=OUTPUT_FILE)
        print(f"XTTS voiceover saved to {OUTPUT_FILE}")
    else:
        # If no built-in speakers, we might need a reference wav.
        # But usually xtts_v2 comes with some.
        print("No built-in speakers found. XTTS might need a reference wav.")

except Exception as e:
    print(f"Error initializing or running XTTS: {e}")
