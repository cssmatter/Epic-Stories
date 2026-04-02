# 🎤 Ghazal & Shayari Reels Automation Guide

This pipeline automates the creation and publishing of high-quality Hindi poetry reels (YouTube Shorts & Instagram Reels). It handles everything from downloading audio and transcripts to AI-powered clip selection, Hindi text rendering, and multi-platform scheduling.

## 🚀 1. Local Generation
You generate the videos on your local machine to take advantage of your hardware and avoid CI limitations.

### Batch Generation (Recommended)
1. Open `data/shayari/ghazal_songs.json`.
2. Add your song names or YouTube URLs to the list.
3. Run the auto-generator:
   ```bash
   python scripts/shayari/youtube_mp3_transcript.py --auto
   ```
   *This will process every song in the list one-by-one, wait 10s between songs, and save everything into the `downloads/` folder.*

### Single Song Generation
```bash
python scripts/shayari/youtube_mp3_transcript.py --url "https://youtu.be/..."
```

---

## 📤 2. Publishing Options

### Option A: Fully Local (No GitHub needed)
If you want to upload and schedule directly from your computer:
1. Run the local uploader:
   ```bash
   python local_bulk_upload.py
   ```
   *   **YouTube**: Publishes the 1st video immediately and schedules the rest 24 hours apart.
   *   **Cleanup**: Moves processed files from `downloads/` to `downloads/published/`.

### Option B: Remote "Daily Drip" (GitHub Actions)
If you want GitHub to handle the daily posting for you (Best for Instagram):
1. Move your generated songs into the `downloads/` folder.
2. Commit and push the folders to GitHub:
   ```bash
   git add downloads/
   git commit -m "feat: add new reels to queue"
   git push
   ```
3. **The Drip**: Every day at **06:00 UTC**, the GitHub Action will:
   *   Pick exactly **ONE** video from your queue.
   *   Post it immediately to YouTube and Instagram.
   *   Delete the files from the repository to keep the queue fresh.

---

## 🛠️ Troubleshooting

### "No Transcript Found"
If a song fails with "No transcript", the script will automatically skip it and move to the next. This happens if the chosen YouTube video doesn't have CC/Subtitles enabled. Usually, searching for a "Lyrical" version of the song helps.

### Audio/Text Out of Sync
The script now forces the audio and transcript to come from the exact same Video ID. If you still see a mismatch, try providing the direct URL of a "Lyrical Video" which typically has the cleanest timestamps.

### Missing Text on Video
Ensure you have the required fonts installed on Windows:
*   `Nirmala.ttc` (Standard Windows Hindi Font)
*   `TiroDevanagariHindi-Regular.ttf` (Standard fallback)

## 🔑 Required API Keys (Environment Variables)
*   `NVIDIA_API_KEY`: Powering the AI lyric analysis and background generation.
*   `GEMINI_API_KEY`: Fallback for vision and metadata.
*   `IG_ACCESS_TOKEN` & `IG_BUSINESS_ID`: For Instagram posting.
