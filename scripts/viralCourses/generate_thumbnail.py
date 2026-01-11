import os
import sys
import json
import skia
import textwrap

# Add root to python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT_DIR)

# Config
DATA_FILE = os.path.join(ROOT_DIR, "data", "viralCourses", "data.json")
BG_FILE = os.path.join(ROOT_DIR, "assets", "viralCourses", "thumbnail_bg.png")
OUTPUT_FILE = os.path.join(ROOT_DIR, "output", "viralCourses", "thumbnail.png")
FONT_PATH = os.path.join(ROOT_DIR, "fonts", "Montserrat-Bold.ttf")

WIDTH = 1280
HEIGHT = 720

def load_title():
    if not os.path.exists(DATA_FILE): return "Title Not Found"
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not data: return "Title Not Found"
    return data[0]["video_assets"]["youtube_metadata"].get("youtubetitle", "Viral Video Title")

def get_typeface():
    if os.path.exists(FONT_PATH):
        return skia.Typeface.MakeFromFile(FONT_PATH)
    return skia.Typeface('Arial', skia.FontStyle.Bold())

def create_thumbnail():
    print("Generating Thumbnail...")
    
    # 1. Surface
    surface = skia.Surface(WIDTH, HEIGHT)
    canvas = surface.getCanvas()
    
    # 2. Draw Black Background
    canvas.clear(skia.ColorBLACK)
    
    # 3. Draw Background Image (Opacity 0.3)
    if os.path.exists(BG_FILE):
        bg_image = skia.Image.open(BG_FILE)
        # Resize if needed? Skia drawImageRect handles resizing
        paint = skia.Paint()
        paint.setAlphaf(0.3) # 0.3 Opacity
        
        src_rect = skia.Rect.MakeWH(bg_image.width(), bg_image.height())
        dst_rect = skia.Rect.MakeWH(WIDTH, HEIGHT)
        
        canvas.saveLayer(None, paint)
        canvas.drawImageRect(bg_image, src_rect, dst_rect)
        canvas.restore()
    else:
        print("Background image not found, using plain black.")

    # 4. Draw Title
    title_text = load_title()
    print(f"Title: {title_text}")
    
    typeface = get_typeface()
    font = skia.Font(typeface, 80) # Size 80
    
    # Wrap text
    # Simple wrapping logic
    words = title_text.split()
    lines = []
    current_line = []
    
    # Measure width
    max_w = WIDTH - 100 # Padding 50px sides
    
    for word in words:
        current_line.append(word)
        test_line = " ".join(current_line)
        if font.measureText(test_line) > max_w:
            # Pop last word
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(" ".join(current_line))
        
    # Draw Lines Centered
    paint_text = skia.Paint(Color=skia.ColorWHITE, AntiAlias=True)
    
    # Calculate vertical center
    line_height = 90
    total_text_height = len(lines) * line_height
    start_y = (HEIGHT - total_text_height) / 2 + line_height/2 + 20 # Adjustment for baseline
    
    for i, line in enumerate(lines):
        w = font.measureText(line)
        x = (WIDTH - w) / 2
        y = start_y + (i * line_height)
        canvas.drawSimpleText(line, x, y, font, paint_text)

    # 5. Save
    image = surface.makeImageSnapshot()
    image.save(OUTPUT_FILE, skia.kPNG)
    print(f"Thumbnail saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    create_thumbnail()
