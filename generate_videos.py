import json
import os
from gtts import gTTS
import torch
import numpy as np
from diffusers import StableDiffusionPipeline
from moviepy import (
    ImageClip,
    AudioFileClip,
    concatenate_videoclips
)
import moviepy.video.fx as vfx

# ==================================================
# CONFIG
# ==================================================
JSON_FILE = "books.json"
OUTPUT_DIR = "output"
IMAGES_PER_CHAPTER = 2
FPS = 24

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ==================================================
# LOAD JSON
# ==================================================
def load_books(json_file=JSON_FILE):
    with open(json_file, "r", encoding="utf-8") as f:
        return json.load(f)["books"]

def list_books(json_file=JSON_FILE):
    try:
        books = load_books(json_file)
        return [b["book_name"] for b in books]
    except Exception:
        return []


# ==================================================
# AUTO CHAPTER SPLIT (FALLBACK)
# ==================================================
def auto_split(text):
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chapters = []
    for i, p in enumerate(paragraphs):
        chapters.append({
            "title": f"Chapter {i+1}",
            "text": p
        })
    return chapters


# ==================================================
# VOICE (OFFLINE)
# ==================================================
def create_voice(chapters, audio_path, lang="en"):
    narration = ""
    for ch in chapters:
        narration += f"{ch['title']}. {ch['text']}...\n"

    tts = gTTS(text=narration, lang=lang)
    tts.save(audio_path)


# ==================================================
# IMAGE GENERATION
# ==================================================
def generate_images(chapters, style, book_slug, output_dir=OUTPUT_DIR, images_per_chapter=IMAGES_PER_CHAPTER):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    
    pipe = StableDiffusionPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        torch_dtype=dtype
    )
    pipe = pipe.to(device)
    
    # Memory Optimizations
    if device == "cuda":
        pipe.enable_xformers_memory_efficient_attention()
    pipe.enable_attention_slicing()

    image_files = []

    for ch in chapters:
        prompt = f"{ch['title']}, {style}"
        for i in range(images_per_chapter):
            filename = f"{book_slug}_{ch['title'].replace(' ', '_')}_{i}.png"
            path = os.path.join(output_dir, filename)
            
            if os.path.exists(path):
                print(f"  - Using existing image: {filename}")
                image_files.append(path)
                continue

            print(f"  - Generating image: {filename} (this may take time on CPU)...")
            image = pipe(prompt).images[0]
            image.save(path)
            image_files.append(path)

    return image_files


# ==================================================
# KEN BURNS EFFECT (ZOOM & PAN)
# ==================================================
def ken_burns(image_path, duration):
    clip = ImageClip(image_path).with_duration(duration)
    
    # In MoviePy 2.x, we use transformed for time-dependent resizing
    # Zoom from 1.0 to 1.2 over the duration
    zoom = lambda t: 1 + 0.04 * t
    clip = clip.resized(lambda t: zoom(t))
    clip = clip.with_position(("center", "center"))

    return clip


# ==================================================
# VIDEO CREATION
# ==================================================
def create_video(images, audio_path, output_path, fps=FPS):
    audio = AudioFileClip(audio_path)
    duration = audio.duration / len(images)

    clips = [ken_burns(img, duration) for img in images]

    video = concatenate_videoclips(clips, method="compose")
    video = video.with_audio(audio)
    video.write_videofile(output_path, fps=fps)


# ==================================================
# PROCESS ONE BOOK
# ==================================================
def process_book(book, output_dir=OUTPUT_DIR, images_per_chapter=IMAGES_PER_CHAPTER, fps=FPS, voice_rate=150, voice_volume=1.0):
    book_name = book["book_name"]
    book_slug = book_name.lower().replace(" ", "_")

    print(f"\nProcessing: {book_name}")

    chapters = book.get("chapters", [])
    if not chapters:
        chapters = auto_split(book["full_text"])

    os.makedirs(output_dir, exist_ok=True)
    audio_path = os.path.join(output_dir, f"{book_slug}.mp3")
    video_path = os.path.join(output_dir, f"{book_slug}.mp4")

    if os.path.exists(video_path):
        print(f"  - Video already exists, skipping: {video_path}")
        return

    print("  - Generating voice...")
    create_voice(chapters, audio_path)

    print("  - Generating images...")
    images = generate_images(
        chapters,
        book["image_style"],
        book_slug,
        output_dir=output_dir,
        images_per_chapter=images_per_chapter
    )

    print("  - Assembling video...")
    create_video(images, audio_path, video_path, fps=fps)

    print(f"Finished: {video_path}")


# ==================================================
# BATCH PROCESS ALL BOOKS
# ==================================================
if __name__ == "__main__":
    books = load_books()

    for book in books:
        process_book(book)

    print("\nALL BOOK VIDEOS GENERATED!")
