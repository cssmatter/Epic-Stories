"""
Test Configuration for Epic Stories video generation
Lower resolution and faster settings for local testing
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

# --- VIDEO SETTINGS (TEST - 1080p for faster processing) ---
WIDTH = 1920
HEIGHT = 1080
FPS = 30  # Reduced from 60 for faster encoding
CODEC = "libx264"
CRF = 28  # Higher CRF = lower quality but faster encoding (was 23)
PRESET = "ultrafast"  # Fastest encoding preset (was "medium")

# --- TTS SETTINGS ---
TTS_LANGUAGE = "en"
TTS_VOICE = "en-US-GuyNeural"
TTS_SLOW = True  # Slow speech for "wise man" effect
TTS_CACHE_DIR = os.path.join(TEMP_DIR, "tts_cache")
os.makedirs(TTS_CACHE_DIR, exist_ok=True)

# --- SUBTITLE SETTINGS (Scaled for 1080p) ---
SUBTITLE_FONT = "Caveat"
SUBTITLE_FONT_SIZE = 11  # Scaled down from 22 for 1080p
SUBTITLE_COLOR = "&H00FFFFFF"  # BGR order for libass (White)
SUBTITLE_BG_COLOR = "black@0.6"
SUBTITLE_POSITION_Y = HEIGHT - 20  # Scaled down from 40
SUBTITLE_MAX_WIDTH = WIDTH - 200  # Scaled down from 400

# --- IMAGE GENERATION SETTINGS ---
IMAGE_CACHE_DIR = os.path.join(TEMP_DIR, "image_cache")
os.makedirs(IMAGE_CACHE_DIR, exist_ok=True)

# Cloudflare Image Generation Settings
CLOUDFLARE_WORKER_URL = "https://imagegeneration.cssmatter.workers.dev/"
CLOUDFLARE_THUMBNAIL_WORKER_URL = CLOUDFLARE_WORKER_URL
# Supports environment variable for CI/GitHub Actions
CLOUDFLARE_AUTH_TOKEN = os.getenv("CLOUDFLARE_AUTH_TOKEN", "Bearer shivaay143$manish")

# OpenAI Settings for Thumbnails
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")

# Image Generation Dimensions (1080p for testing)
GEN_WIDTH = 1920 
GEN_HEIGHT = 1080

# --- SCENE SETTINGS ---
INTRO_DURATION = 5.0  # Seconds to show intro
SCENE_PADDING = 1.0  # Pause between scenes
FADE_DURATION = 0.5  # Fade transition duration

# --- OVERLAY VIDEOS ---
OVERLAY_VIDEO_PATH = os.path.join(ASSETS_DIR, "overlay.mp4")
CLOUDS_VIDEO_PATH = os.path.join(ASSETS_DIR, "clouds.mp4")
OVERLAY_OPACITY = 0.10  # Opacity for overlay.mp4
CLOUDS_OPACITY = 0.02  # Opacity for clouds.mp4

# --- BACKGROUND MUSIC ---
BACKGROUND_MUSIC_PATH = os.path.join(ASSETS_DIR, "story-bg.mp3")
MUSIC_VOLUME = 0.20  # Background music volume (0.0 to 1.0)

# --- BRANDING (Scaled for 1080p) ---
LOGO_PATH = os.path.join(ASSETS_DIR, "channels_profile.jpg")
LOGO_WIDTH = 50  # Scaled down from 100 for 1080p
LOGO_PADDING = 20  # Scaled down from 40 for 1080p
