#!/usr/bin/env python3
"""
Quick test for Cloudflare Worker image generation
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from youtube_mp3_transcript import CLOUDFLARE_WORKER_URL, CLOUDFLARE_AUTH_TOKEN, generate_with_cloudflare

print("=" * 60)
print("CLOUDFLARE WORKER IMAGE GENERATOR TEST")
print("=" * 60)

print(f"\nWorker URL: {CLOUDFLARE_WORKER_URL}")
print(f"Auth Token: {'✅ Set' if CLOUDFLARE_AUTH_TOKEN else '❌ Not set'}")

if not CLOUDFLARE_AUTH_TOKEN:
    print("\n❌ ERROR: CLOUDFLARE_AUTH_TOKEN is not set!")
    sys.exit(1)

# Test generation
test_prompt = "A beautiful sunset over mountains, cinematic, 8k resolution"
test_output = Path("test_cloudflare_output.jpg")

print(f"\n🎨 Testing image generation...")
print(f"Prompt: {test_prompt}")

try:
    result = generate_with_cloudflare(
        image_prompt=test_prompt,
        style="cinematic",
        output_path=test_output,
        width=1080,
        height=1920
    )

    if result and Path(result).exists():
        print(f"\n✅ SUCCESS! Image generated: {test_output.absolute()}")
        print(f"   Size: {test_output.stat().st_size / 1024:.1f} KB")
    else:
        print("\n❌ FAILED: No image was generated")
        sys.exit(1)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ Cloudflare Worker is working perfectly!")
print("=" * 60)
