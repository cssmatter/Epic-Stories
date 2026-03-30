import sys
import os
from pathlib import Path

# Add the script dir to path
sys.path.append(os.getcwd())

import youtube_mp3_transcript as yt

def create_sample():
    text = "वो बारिश का पानी"
    img_path = Path("sample_hindi_fix.jpg")
    
    # Ensure background
    yt.generate_background("monsoon rain paper boat", "RDR2 Zoological Compendium", img_path)
    
    # Overlay with our best renderer
    yt.overlay_lyrics(img_path, text, "serene")
    
    print(f"Sample created: {img_path.absolute()}")

if __name__ == "__main__":
    create_sample()
