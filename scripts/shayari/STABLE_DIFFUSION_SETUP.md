# Stable Diffusion Setup Guide

## 🎯 Quick Setup

### 1. Check Current Dependencies
```bash
cd "C:\git\youtube-automation\Epic-Stories-All-youtube-automation-shorts\scripts\shayari"
python check_dependencies.py
```

### 2. Fix Dependencies (If Needed)
```bash
# The fix script will:
# - Install correct PyTorch version (2.0.1) for your system
# - Install diffusers, transformers, accelerate
# - Install all other dependencies from requirements.txt
python fix_dependencies.py
```

### 3. Test Stable Diffusion
```bash
# Quick test without video rendering
python test_stable_diffusion.py

# Full test with your video
python youtube_mp3_transcript.py --url "YOUR_YOUTUBE_URL" --image-generator stable-diffusion
```

## 📦 Requirements

### Mandatory for CPU mode:
- **PyTorch 2.0.1** (CPU version) - NOT 2.2.0 or newer (causes segfaults!)
- **diffusers** >= 0.24.0
- **transformers** >= 4.36.0
- **accelerate** >= 0.25.0
- **8GB+ RAM** (16GB recommended for SDXL)
- **20GB+ free disk space** for model cache

### Optional (for GPU):
- NVIDIA GPU with 6GB+ VRAM
- CUDA 11.8 toolkit
- xformers for memory optimization

## ⚠️ Common Issues & Solutions

### Issue: Segmentation Fault
**Cause:** PyTorch version mismatch (you have 2.2.0, need 2.0.1)

**Fix:**
```bash
pip uninstall torch torchvision -y
pip install torch==2.0.1 torchvision --index-url https://download.pytorch.org/whl/cpu
```

### Issue: Out of Memory (OOM)
**Cause:** Not enough RAM for SDXL on CPU (~8GB minimum)

**Solutions:**
1. Use a smaller model:
   ```bash
   SD_MODEL=stabilityai/sd-turbo python youtube_mp3_transcript.py --url URL --image-generator stable-diffusion
   ```
2. Use GPU if available:
   ```bash
   # Install CUDA-enabled PyTorch first:
   pip install torch==2.0.1 torchvision --index-url https://download.pytorch.org/whl/cu118
   # Then run with:
   SD_DEVICE=cuda python youtube_mp3_transcript.py --url URL --image-generator stable-diffusion
   ```
3. Skip video rendering to reduce memory:
   ```bash
   python youtube_mp3_transcript.py --url URL --image-generator stable-diffusion --skip-video
   ```

### Issue: Slow Generation on CPU
SDXL on CPU can be very slow (1-5 minutes per image). For faster results:
- Use GPU (recommended)
- Use SD Turbo model (faster, smaller)
- Use Cloudflare Worker instead (fast, free, no setup):
  ```bash
  python youtube_mp3_transcript.py --url URL --image-generator cloudflare
  ```

## 🔧 Configuration

### Environment Variables
You can customize Stable Diffusion behavior:

```bash
# Set in command line or .env file:

# Model to use (default: stabilityai/stable-diffusion-xl-base-1.0)
export SD_MODEL=stabilityai/sd-turbo  # smaller, faster

# Device: auto (detect), cuda (GPU), cpu (CPU), mps (Mac)
export SD_DEVICE=auto

# Enable xFormers optimization (GPU only, faster)
export SD_USE_XFORMERS=true

# Auto-enable attention slicing for low VRAM (<8GB)
export SD_ATTENTION_SLICING=auto

# Enable CPU offload (GPU with very little VRAM)
export SD_CPU_OFFLOAD=false

# Image generator: auto, stable-diffusion, gemini, cloudflare, etc.
export IMAGE_GENERATOR=stable-diffusion
```

### Recommended Settings by Hardware

| Hardware | SD_DEVICE | SD_MODEL | Expected Time/Image |
|----------|-----------|----------|-------------------|
| NVIDIA GPU 8GB+ | cuda | SDXL | 5-10 seconds |
| NVIDIA GPU 4-8GB | cuda | SD Turbo + SD_CPU_OFFLOAD=true | 10-20 seconds |
| CPU 16GB RAM | cpu | SD Turbo | 60-120 seconds |
| CPU 8GB RAM | cpu | SD Turbo + lower resolution | 120-300 seconds |

## 🧪 Testing

Run the diagnostic test:
```bash
python test_stable_diffusion.py
```

This will:
- Check all dependencies
- Download model if needed
- Generate a test image
- Show you the expected performance

## 📝 Notes

- **First run** will download ~1-7GB model (depends on model size)
- Images are **cached** automatically in `sd_cache/` folder
- Subsequent runs are instant (loads from cache)
- Works **offline** after initial download
- Compatible with Windows, Linux, macOS

## 🆘 Need Help?

1. Run `python check_dependencies.py` and share output
2. Check the troubleshooting section above
3. Verify you have enough RAM (8GB minimum, 16GB recommended)
4. Make sure you're using PyTorch 2.0.1 (not 2.2.0)

## 🔄 Alternative: Use Cloudflare Worker

If you keep having issues with local Stable Diffusion, use Cloudflare Worker - it's:
- ✅ Fast (API-based)
- ✅ No setup required
- ✅ Works immediately
- ✅ No GPU/RAM requirements
- ✅ Free

```bash
python youtube_mp3_transcript.py --url "YOUR_URL" --image-generator cloudflare
```
