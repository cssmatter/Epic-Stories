# Epic Stories Video Generator

This directory contains the automated video generation system for Epic Stories.

## Overview

The system generates YouTube videos from `story.json` data with:
- AI-generated images (Stable Diffusion) for each scene
- Male "wise man" voiceover narration (gTTS with slow speech)
- Burned-in subtitles for accessibility
- Automated scene composition and video generation

## Files

- `config.py` - Configuration settings (paths, video settings, TTS, subtitles)
- `image_generator.py` - Generates images from text prompts using Stable Diffusion
- `tts_generator.py` - Creates voiceover audio using gTTS
- `subtitle_generator.py` - Burns subtitles into video
- `epic_stories_video_generator.py` - Main script that orchestrates everything
- `requirements.txt` - Python dependencies

## Installation

1. Install basic dependencies:
```powershell
pip install gtts Pillow imageio-ffmpeg
```

2. (Optional) Install Stable Diffusion for local image generation:
```powershell
pip install diffusers transformers accelerate torch torchvision
```

**Note**: Stable Diffusion requires ~10GB of disk space and works best with a GPU. Without it, the system will generate placeholder images.

## Usage

Run the video generator:

```powershell
cd c:\git\youtube-automation\Epic-Stories-All-youtube-automation-shorts
python scripts\epicstories\epic_stories_video_generator.py
```

The script will:
1. Load story data from `data/epicstories/story.json`
2. Generate intro with story title
3. For each scene:
   - Generate image from `image_prompt`
   - Create voiceover from `text`
   - Burn subtitles into video
4. Concatenate all scenes into final video
5. Output to `output/epicstories/epic_story.mp4`

## Output

- Final video: `output/epicstories/epic_story.mp4`
- Temporary files: `output/epicstories/temp/` (auto-generated, can be deleted)
- Cached images: `output/epicstories/temp/image_cache/`
- Cached TTS: `output/epicstories/temp/tts_cache/`

## Configuration

Edit `config.py` to customize:
- Video resolution and FPS
- Subtitle font size, color, position
- TTS language and speed
- Stable Diffusion model and settings
- Scene durations

## Testing Individual Components

Test image generation:
```powershell
python scripts\epicstories\image_generator.py
```

Test TTS:
```powershell
python scripts\epicstories\tts_generator.py
```

Test subtitles:
```powershell
python scripts\epicstories\subtitle_generator.py
```
