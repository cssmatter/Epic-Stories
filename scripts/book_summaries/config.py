"""
Configuration file for Book Summary Video Generator
"""
import os

# --- PATHS ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_FILE = os.path.join(REPO_ROOT, "data", "BookSummariesChannel", "data.json")
OUTPUT_DIR = os.path.join(REPO_ROOT, "output", "book_summaries")
TEMP_DIR = os.path.join(OUTPUT_DIR, "temp")
ASSETS_DIR = os.path.join(REPO_ROOT, "assets", "book_summaries")
FONTS_DIR = os.path.join(REPO_ROOT, "fonts")

# Create directories
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

# --- VIDEO SETTINGS ---
WIDTH = 1920
HEIGHT = 1080
FPS = 30
CODEC = "libx264"
CRF = 23
PRESET = "medium"

# --- TEST MODE SETTINGS ---
TEST_WIDTH = 1280
TEST_HEIGHT = 720
TEST_SCENE_LIMIT = 2

# --- LAYOUT SETTINGS ---
PADDING = 100  # Padding around the main container (standard video)
SHORTS_PADDING = 70  # Padding for shorts video
GAP = 40       # Gap between book cover and text
CORNER_RADIUS = 20

# --- TEXT SETTINGS ---
TITLE_FONT_SIZE = 60
AUTHOR_FONT_SIZE = 45
CHAPTER_TITLE_FONT_SIZE = 50
BODY_FONT_SIZE = 45
FONT_FAMILY = "arial.ttf" # Fallback, ideally use Inter or Roboto if available
BOLD_FONT_FAMILY = "arialbd.ttf"
LYRICS_ACTIVE_OPACITY = 255 # Fully Opaque
LYRICS_INACTIVE_OPACITY = 127 # ~50% Opacity

# --- MARQUEE SETTINGS ---
MARQUEE_TEXT = "Subscribe to @BookSummariesChannel"
MARQUEE_FONT_SIZE = 30
MARQUEE_TOP_PADDING = 60
MARQUEE_FONT_PATH = os.path.join(FONTS_DIR, "arial.ttf")

# --- SHORTS SETTINGS ---
SHORTS_WIDTH = 720
SHORTS_HEIGHT = 1280
SHORTS_PADDING_PERCENT = 0.20 # 30% Padding
SHORTS_OUTRO_TEXT = "Check out our 'Book Summaries Channel' for full book summary."

# --- TTS SETTINGS ---
TTS_VOICE = "en-US-AndrewNeural" # Good narrator voice
TTS_RATE = "+0%"
TTS_CACHE_DIR = os.path.join(TEMP_DIR, "tts_cache")
os.makedirs(TTS_CACHE_DIR, exist_ok=True)
