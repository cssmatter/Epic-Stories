# 🎮 NVIDIA GPU Setup for Stable Diffusion

Your system already has NVIDIA API configured. Here's how to leverage your **local NVIDIA GPU** for completely FREE, fast image generation!

## 📋 Prerequisites Check

Before using NVIDIA GPU for Stable Diffusion, verify:

```bash
# Check NVIDIA GPU
nvidia-smi

# Check CUDA with PyTorch
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda}')"
```

Expected output:
- NVIDIA driver visible in `nvidia-smi`
- `CUDA available: True`
- `CUDA version: 11.8` or similar

## 🚀 Quick Setup (5 Minutes)

### 1. Install CUDA-enabled PyTorch (if not already installed)

**Current version in requirements.txt**: `torch==2.0.1` with CUDA 11.8 support

```bash
# For CUDA 11.8 (most common with RTX 30xx/40xx series)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# For other CUDA versions:
# CUDA 12.1: --index-url https://download.pytorch.org/whl/cu121
# CUDA 11.7: --index-url https://download.pytorch.org/whl/cu117
# CPU only: pip install torch torchvision
```

### 2. Install xFormers (Highly Recommended for NVIDIA)

xFormers dramatically speeds up generation and reduces VRAM usage:

```bash
# pip install xformers  # Already in requirements.txt
# If installation fails, try:
pip install xformers --index-url https://download.pytorch.org/whl/cu118

# Or build from source (if pip fails):
# git clone https://github.com/facebookresearch/xformers.git
# cd xformers && pip install -e .
```

### 3. Install other dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify GPU Setup

```bash
python test_nvidia_gpu.py  # (Will create below - comprehensive GPU check)
```

## 🎯 Using NVIDIA GPU

Once setup, the script **auto-detects** your NVIDIA GPU:

```bash
# Auto-detects CUDA and uses GPU
python youtube_mp3_transcript.py --url "your song" --image-generator stable-diffusion

# Force CPU (if you want to test or GPU unavailable)
export SD_DEVICE=cpu
python youtube_mp3_transcript.py --url "song" --image-generator stable-diffusion
```

### Env Vars for Fine-tuning

```bash
# Device selection
export SD_DEVICE=cuda        # Auto-detects CUDA (use for NVIDIA GPU)
# or
export SD_DEVICE=cpu         # Force CPU (slower but works)

# xFormers (dramatically faster, less VRAM)
export SD_USE_XFORMERS=true  # Default: true

# Attention slicing (enables if VRAM < 8GB automatically)
export SD_ATTENTION_SLICING=true  # Manually force
# or
export SD_ATTENTION_SLICING=false  # Disable for maximum speed (high VRAM)

# CPU offload (for very low VRAM, trades speed for compatibility)
export SD_CPU_OFFLOAD=true   # Use if getting OOM errors on 4-6GB GPU
```

## 🎮 GPU Performance by VRAM

| GPU | VRAM | Settings | Speed | Quality |
|-----|------|----------|-------|---------|
| RTX 4090 | 24GB | SD_CPU_OFFLOAD=false | ~10s/img | ✅ Full |
| RTX 4080 | 16GB | SD_CPU_OFFLOAD=false | ~12s/img | ✅ Full |
| RTX 4070 Ti | 12GB | SD_CPU_OFFLOAD=false | ~15s/img | ✅ Full |
| RTX 3070/4070 | 8GB | SD_CPU_OFFLOAD=false | ~18s/img | ✅ Full |
| RTX 3060/4060 | 8GB | SD_ATTENTION_SLICING=true (auto) | ~20s/img | ✅ Full |
| RTX 3050/2060 | 6GB | SD_ATTENTION_SLICING=true + xFormers | ~25s/img | ✅ Good |
| GTX 1660/1060 | 6GB | SD_CPU_OFFLOAD=true (if needed) | ~30s/img | ✅ Good |
| GTX 1050 Ti | 4GB | SD_CPU_OFFLOAD=true, reduce steps to 20 | ~45s/img | ⚠️ Reduced |
| Any GPU < 4GB | ❌ | Not recommended for SDXL | ~2-5 min | ❌ Very slow |

**Note**: Times are for 1024x1024 generation; resizing to 1080x1920 adds ~1s.

## 🔧 Advanced Optimizations

### Enable TensorRT (Experimental, Faster)
```bash
# Requires TensorRT and ONNX export
export SD_USE_TENSORRT=true  # Not yet implemented in this script
```

### Use Different SDXL Model (Faster/Quality Trade-off)
```bash
export SD_MODEL="stabilityai/stable-diffusion-xl-base-1.0"  # Default, best quality
# or faster alternatives:
# export SD_MODEL="stabilityai/sdxl-turbo"  # Turbo, 4 steps, lower quality
```

### Batch Generation (for multiple seeds)
Edit the script to generate multiple variations per prompt (not yet implemented).

## 🐛 Troubleshooting NVIDIA GPU Issues

### "CUDA out of memory"
```bash
# Solution 1: Enable attention slicing (auto for <8GB)
export SD_ATTENTION_SLICING=true

# Solution 2: Enable CPU offload (for very low VRAM)
export SD_CPU_OFFLOAD=true

# Solution 3: Reduce image resolution
# Edit generate_with_stable_diffusion(): change width/height from 1080x1920 to 768x1360

# Solution 4: Close other GPU apps (Chrome, games, etc.)
```

### "xformers not available"
```bash
# GPU mode still works without xformers, just slower
# To install xformers:
pip install xformers --index-url https://download.pytorch.org/whl/cu118

# If still failing, use CPU offload instead:
export SD_CPU_OFFLOAD=true
```

### "CUDA driver version is insufficient"
```bash
# Update NVIDIA drivers from https://www.nvidia.com/Download/index.aspx
# Or use CPU mode temporarily:
export SD_DEVICE=cpu
```

### "Torch not compiled with CUDA"
```bash
# You installed CPU-only PyTorch. Reinstall with CUDA:
pip uninstall torch torchvision -y
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Slow GPU performance
```bash
# Ensure xFormers is enabled (check logs for "Enabling xFormers")
export SD_USE_XFORMERS=true

# Check GPU utilization
nvidia-smi -l 1  # Should show 50-100% GPU usage during generation

# If GPU usage is low, try:
# 1. Reduce SD_ATTENTION_SLICING (set to false)
# 2. Increase batch_size (not applicable here)
# 3. Close background processes using GPU
```

## 🎉 Success Indicators

When working correctly, you should see:

```
🎮 Using NVIDIA GPU: NVIDIA GeForce RTX 3070 (8.0 GB VRAM)
📥 Loading Stable Diffusion XL model...
✨ Enabling xformers memory-efficient attention...
✅ Model loaded in 45.2s
🖼️ Generating image (this may take 10-30s on first run)...
✅ Stable Diffusion: Generated in 18.3s on CUDA
```

Key signs:
- ✅ Load time: 30-60s (first time), 5-10s (subsequent)
- ✅ Generation time: 10-25s on GPU (vs 60-120s on CPU)
- ✅ VRAM usage: ~4-6GB (with xFormers)

## 📊 Performance Comparison (NVIDIA GPU)

| GPU | 1st Image | Subsequent (cached model) |
|-----|-----------|--------------------------|
| RTX 4090 24GB | 45s load + 10s gen | ~10s |
| RTX 4070 12GB | 50s load + 15s gen | ~15s |
| RTX 3070 8GB | 55s load + 18s gen | ~18s |
| RTX 3060 8GB | 60s load + 25s gen | ~25s |
| GTX 1660 6GB | 60s load + 30s gen | ~30s |

**CPU (no GPU)**: 60s load + 60-120s gen

## 🌐 External References

- NVIDIA CUDA Toolkit: https://developer.nvidia.com/cuda-toolkit
- PyTorch CUDA: https://pytorch.org/get-started/locally/
- xFormers: https://github.com/facebookresearch/xformers
- Stable Diffusion XL: https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0

## 🔄 Switching Between GPU and CPU

```bash
# Use GPU
export SD_DEVICE=cuda
python youtube_mp3_transcript.py --url "song"

# Use CPU (if GPU too slow or OOM)
export SD_DEVICE=cpu
python youtube_mp3_transcript.py --url "song"
```

## 💾 Model Download Info

**First run only** (~7GB):
- Downloads from Hugging Face Hub automatically
- Cached locally: `~/.cache/huggingface/hub`
- Subsequent runs: instant (no internet needed)

**Cache location**: `[project]/scripts/shayari/downloads/[song_folder]/sd_cache/`

## 🎉 Ready to Go!

Your NVIDIA GPU + Stable Diffusion = **Unlimited, high-quality, FREE AI images**! 🚀

Best setup:
```bash
export SD_DEVICE=cuda
export SD_USE_XFORMERS=true
python youtube_mp3_transcript.py --url "your song" --image-generator stable-diffusion
```
