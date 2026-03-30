import unicodedata
import subprocess
from pathlib import Path

def test_rendering():
    text = "बारिश"
    # Try different normalizations
    nfc = unicodedata.normalize("NFC", text)
    
    print(f"Original: {list(text)}")
    print(f"NFC:      {list(nfc)}")
    
    # Simple check: Does it render correctly with FFmpeg?
    # We will create a small ASS file and render it to a black frame.
    
    font_path = Path(r"C:\git\youtube-automation\Epic-Stories-All-youtube-automation-shorts\fonts\TiroDevanagariHindi-Regular.ttf")
    out_img = Path("test_hindi.jpg")
    
    ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Tiro Devanagari Hindi,100,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,30,30,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,{nfc}
"""
    with open("test.ass", "w", encoding="utf-8") as f:
        f.write(ass_content)
        
    # Create black background
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1080x1920", "-frames:v", "1", "bg.jpg"])
    
    # Render
    vf = f"subtitles=test.ass:fontsdir='{str(font_path.parent)}'"
    cmd = ["ffmpeg", "-y", "-i", "bg.jpg", "-vf", vf, "-frames:v", "1", str(out_img)]
    subprocess.run(cmd)
    print(f"Done. Check {out_img}")

if __name__ == "__main__":
    test_rendering()
