"""
Configuration file for Epic Stories video generation
"""
import os

# --- PATHS ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_FILE = os.path.join(REPO_ROOT, "data", "epicstories", "story.json")
OUTPUT_DIR = os.path.join(REPO_ROOT, "output", "epicstories")
TEMP_DIR = os.path.join(OUTPUT_DIR, "temp")
ASSETS_DIR = os.path.join(REPO_ROOT, "assets", "epicstories")
FONTS_DIR = os.path.join(REPO_ROOT, "fonts")

# Create directories
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

# --- VIDEO SETTINGS ---
WIDTH = 3840
HEIGHT = 2160
FPS = 60
CODEC = "libx264"
CRF = 23  # Quality (lower = better, 18-28 recommended)
PRESET = "medium"  # Encoding speed (ultrafast, fast, medium, slow)

# --- TTS SETTINGS ---
TTS_LANGUAGE = "en"
TTS_VOICE = "en-US-GuyNeural"
TTS_SLOW = True  # Slow speech for "wise man" effect
TTS_CACHE_DIR = os.path.join(TEMP_DIR, "tts_cache")
os.makedirs(TTS_CACHE_DIR, exist_ok=True)

# --- SUBTITLE SETTINGS ---
SUBTITLE_FONT = "Caveat"
SUBTITLE_FONT_SIZE = 22  # Scaled for 4K (approx 2.2x of 1080p size)
SUBTITLE_COLOR = "&H00FFFFFF"  # BGR order for libass (White)
SUBTITLE_BG_COLOR = "black@0.6"
SUBTITLE_POSITION_Y = HEIGHT - 40  # Moved closer to the bottom
SUBTITLE_MAX_WIDTH = WIDTH - 400  # Max width for text wrapping

# --- IMAGE GENERATION SETTINGS ---
IMAGE_CACHE_DIR = os.path.join(TEMP_DIR, "image_cache")
os.makedirs(IMAGE_CACHE_DIR, exist_ok=True)

# Cloudflare Image Generation Settings
CLOUDFLARE_WORKER_URL = "https://imagegeneration.cssmatter.workers.dev/"
CLOUDFLARE_THUMBNAIL_WORKER_URL = "https://thumbnailgenerator.cssmatter.workers.dev/"
# Supports environment variable for CI/GitHub Actions
CLOUDFLARE_AUTH_TOKEN = os.getenv("CLOUDFLARE_AUTH_TOKEN", "Bearer shivaay143$manish")

# Image Generation Dimensions (Requested 16:9)
# Note: The worker likely handles dimensions or we emphasize in prompt
GEN_WIDTH = 1920 
GEN_HEIGHT = 1080

# --- SCENE SETTINGS ---
INTRO_DURATION = 5.0  # Seconds to show intro
SCENE_PADDING = 1.0  # Pause between scenes
FADE_DURATION = 0.5  # Fade transition duration

# --- OVERLAY VIDEO ---
OVERLAY_VIDEO_PATH = os.path.join(ASSETS_DIR, "overlay.mp4")
OVERLAY_OPACITY = 0.10  # Overlay opacity (0.0 to 1.0)

# --- BACKGROUND MUSIC ---
BACKGROUND_MUSIC_PATH = os.path.join(ASSETS_DIR, "story-bg.mp3")
MUSIC_VOLUME = 0.20  # Background music volume (0.0 to 1.0)

# --- BRANDING ---
LOGO_PATH = os.path.join(ASSETS_DIR, "channels_profile.jpg")
LOGO_WIDTH = 100  # Scaled for 4K
LOGO_PADDING = 40 # Scaled for 4K
