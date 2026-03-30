#!/usr/bin/env python3
"""
Test Local Stable Diffusion XL Image Generation
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

print("=" * 70)
print("LOCAL STABLE DIFFUSION XL TEST")
print("=" * 70)

# Check if required packages are installed
print("\n1. Checking dependencies...")
try:
    import torch
    print(f"   ✅ torch: {torch.__version__}")
    if torch.cuda.is_available():
        print(f"   ✅ CUDA: {torch.version.cuda} | GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("   ⚠️ CUDA not available - will use CPU (slower)")
except ImportError as e:
    print(f"   ❌ torch not installed: {e}")
    print("   Install: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118")
    sys.exit(1)

try:
    import diffusers
    print(f"   ✅ diffusers: {diffusers.__version__}")
except ImportError:
    print("   ❌ diffusers not installed")
    print("   Install: pip install diffusers")
    sys.exit(1)

try:
    from diffusers import StableDiffusionXLPipeline
    print("   ✅ StableDiffusionXLPipeline available")
except ImportError:
    print("   ❌ StableDiffusionXLPipeline not available")
    sys.exit(1)

# Test configuration
print("\n2. Configuration:")
from youtube_mp3_transcript import SD_MODEL, SD_DEVICE
print(f"   Model: {SD_MODEL}")
print(f"   Device: {SD_DEVICE}")

# Test generation
print("\n3. Testing image generation...")
print("   This will:")
print("   - Download ~7GB model on first run (one-time)")
print("   - Generate a test image (may take 30-60s on first run)")

test_prompt = "A beautiful landscape with mountains and lake at sunset, cinematic"
test_output = Path("test_sd_output.jpg")

try:
    from youtube_mp3_transcript import generate_with_stable_diffusion

    print(f"\n   Prompt: {test_prompt}")
    result = generate_with_stable_diffusion(
        image_prompt=test_prompt,
        style="cinematic",
        output_path=test_output,
        width=1024,  # SDXL default (use 1024 for best quality)
        height=1024
    )

    if result and Path(result).exists():
        size = Path(result).stat().st_size / 1024
        print(f"\n✅ SUCCESS! Image generated: {Path(result).absolute()}")
        print(f"   Size: {size:.1f} KB")
        print("\n💡 You can now use --image-generator stable-diffusion for FREE!")
    else:
        print("\n❌ FAILED: No image was generated")
        sys.exit(1)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ LOCAL STABLE DIFFUSION IS READY TO USE!")
print("=" * 70)
