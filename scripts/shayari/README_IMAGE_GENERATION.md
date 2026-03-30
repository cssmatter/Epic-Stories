# 🎨 Image Generation for YouTube Reels

Your script now supports **5 FREE image generation options**!

## 🚀 Quick Start

### Option 1: Local Stable Diffusion (100% FREE - Recommended!)
Runs completely on your computer. No API keys, no limits, no costs.

```bash
# Make sure you have NVIDIA GPU with CUDA, or use CPU (slower)
python youtube_mp3_transcript.py --url "your song" --image-generator stable-diffusion
```

**First time**: Downloads ~7GB model (one-time only)
**After that**: Instant generation, completely free!

**Requirements for Local SD**:
- NVIDIA GPU (recommended) with 6GB+ VRAM
- Or CPU with at least 16GB RAM (slower but works)
- PyTorch with CUDA (included in requirements.txt)

### Option 2: Cloudflare Worker (⚡ Fastest Start)
Already configured, works immediately without any setup:

```bash
python youtube_mp3_transcript.py --url "your song"
# or explicitly:
python youtube_mp3_transcript.py --url "your song" --image-generator cloudflare
```

Uses internal Cloudflare Worker service (token pre-configured).

## 📋 All Image Generator Options

### 1. **stable-diffusion** (Local) ⭐
- **Cost**: 100% FREE
- **Quality**: High (SDXL)
- **Speed**: Fast on GPU, moderate on CPU
- **Limits**: None
- **First-time download**: ~7GB
- **How to use**:
  ```bash
  python youtube_mp3_transcript.py --url "song" --image-generator stable-diffusion
  ```

### 2. **cloudflare** (Cloud) ⭐⭐
- **Cost**: FREE (internal service)
- **Quality**: High
- **Speed**: Fast (~30s per image)
- **Limits**: None configured
- **Setup**: Already configured
- **How to use**:
  ```bash
  python youtube_mp3_transcript.py --url "song" --image-generator cloudflare
  ```

### 3. **gemini** (Cloud)
- **Cost**: FREE tier: 60 requests/minute
- **Quality**: Very High (Gemini 2.0 Flash)
- **Speed**: Fast
- **Limits**: Rate limits apply
- **Setup**: Get API key from https://makersuite.google.com/app/apikey
- **How to use**:
  ```bash
  export GEMINI_API_KEY="your-key"
  python youtube_mp3_transcript.py --url "song" --image-generator gemini
  ```

### 4. **huggingface** (Cloud)
- **Cost**: FREE with HF account
- **Quality**: High (Stable Diffusion XL)
- **Speed**: Moderate
- **Limits**: Queue may apply
- **Setup**: Get token from https://huggingface.co/settings/tokens
- **How to use**:
  ```bash
  export HF_TOKEN="your-token"
  python youtube_mp3_transcript.py --url "song" --image-generator huggingface
  ```

### 5. **replicate** (Cloud)
- **Cost**: FREE credits available
- **Quality**: Very High (Flux.1 Dev)
- **Speed**: Fast
- **Limits**: Free credits then paid
- **Setup**: Get token from https://replicate.com/account/api-tokens
- **How to use**:
  ```bash
  export REPLICATE_API_TOKEN="your-token"
  python youtube_mp3_transcript.py --url "song" --image-generator replicate
  ```

### 6. **auto** (Default)
Tries generators in order based on what's available:
```
Local SD → Cloudflare → Gemini → HuggingFace → Replicate → Gradient
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file (from `.env.example`) or set environment variables:

```bash
# Image Generator Choice
export IMAGE_GENERATOR=auto  # or stable-diffusion, cloudflare, gemini, etc.

# Local Stable Diffusion Settings
export SD_MODEL=stabilityai/stable-diffusion-xl-base-1.0
export SD_DEVICE=cuda  # or "cpu" for CPU-only

# Cloudflare (already set)
export CLOUDFLARE_AUTH_TOKEN="Bearer shivaay143$manish"  # optional, default included

# Other cloud services (optional)
export GEMINI_API_KEY="your-key"
export HF_TOKEN="your-token"
export REPLICATE_API_TOKEN="your-token"
```

### Command Line Options

```bash
python youtube_mp3_transcript.py \
  --url "YouTube URL or song name" \
  --image-generator stable-diffusion \
  --output ./output \
  --skip-ai     # optional: skip AI reel suggestions
```

## 📦 Installation

```bash
# Install all dependencies
pip install -r requirements.txt

# Verify installation
python -c "import torch; import diffusers; print('Ready!')"
```

## 🧪 Testing

### Test Local Stable Diffusion
```bash
python test_stable_diffusion.py
```

### Test Cloudflare Worker
```bash
python test_cloudflare.py
```

### Quick Dry Run (no video rendering)
```bash
python youtube_mp3_transcript.py --url "song name" --skip-video
```

## 💾 Image Caching

All generators cache images automatically:
- **Local SD**: `./sd_cache/` (by prompt hash)
- **Cloudflare**: `./cloudflare_cache/`
- **Cloud APIs**: Same cache behavior

Cache location: `[song_folder]/[generator]_cache/`

This means:
- Same image = generated once, reused forever
- Fast reruns
- Saves API calls (if using cloud services)

## 🎯 Recommended Setup

### For Best Quality + 100% Free:
```bash
# Use Local Stable Diffusion (one-time ~7GB download)
export IMAGE_GENERATOR=stable-diffusion
python youtube_mp3_transcript.py --url "song"
```

### For Fastest Start:
```bash
# Use Cloudflare Worker (already configured)
python youtube_mp3_transcript.py --url "song"
```

### For Maximum Reliability (Auto Fallback):
```bash
# Auto tries: Local SD → Cloudflare → Gemini → ...
export IMAGE_GENERATOR=auto
python youtube_mp3_transcript.py --url "song"
```

## 📊 Performance Comparison

| Generator | Quality | Speed (1st run) | Speed (cached) | Cost | Internet Required |
|-----------|---------|----------------|----------------|------|-------------------|
| Local SD  | ⭐⭐⭐⭐⭐ | 30-60s (GPU) | <1s | FREE | No (after download) |
| Cloudflare| ⭐⭐⭐⭐⭐ | 10-30s | <1s | FREE | Yes |
| Gemini    | ⭐⭐⭐⭐⭐ | 5-15s | <1s | FREE (rate-limited) | Yes |
| HuggingFace| ⭐⭐⭐⭐ | 20-40s | <1s | FREE | Yes |
| Replicate | ⭐⭐⭐⭐⭐ | 10-20s | <1s | FREE credits | Yes |

## ❓ FAQ

**Q: How many images can I generate with Local SD?**
A: Unlimited! Completely free, no limits.

**Q: What if I don't have a GPU?**
A: CPU works but slower (~2-5 min/image). Or use Cloudflare (free, fast).

**Q: Why is my first SD generation slow?**
A: Model loading (~7GB download + GPU memory allocation). Subsequent runs are fast.

**Q: Where are images saved?**
A: Generated images saved to `[song_folder]/reel_*/frame_XXX.jpg`

**Q: Can I switch between generators?**
A: Yes! Use `--image-generator` or `IMAGE_GENERATOR` env var.

**Q: What if an image generation fails?**
A: Automatic fallback to gradient (still renders video).

**Q: Do I need internet after first SD download?**
A: No! Local SD works completely offline.

## 🐛 Troubleshooting

### CUDA Out of Memory
```bash
# Reduce image resolution (default is 1080x1920)
# Edit generate_background() call or use smaller SD model:
export SD_MODEL="stabilityai/stable-diffusion-xl-base-1.0"
```

### CPU Too Slow
```bash
# Use Cloudflare instead
python youtube_mp3_transcript.py --url "song" --image-generator cloudflare
```

### Import Errors
```bash
# Reinstall PyTorch with CUDA (for NVIDIA GPU)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
pip install diffusers transformers accelerate
```

### Download Stuck (First Time SD)
The ~7GB model downloads automatically. If it fails, manually download:
```bash
# Set cache location
export HF_HOME=~/.cache/huggingface
# Or use `huggingface-cli login` if using private models
```

## 🎉 Enjoy!

Your YouTube MP3 transcript script now has **unlimited, completely free** AI image generation! 🚀

Choose **Local SD** for unlimited offline use, or **Cloudflare** for instant start.
