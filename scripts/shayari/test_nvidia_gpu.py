#!/usr/bin/env python3
"""
Comprehensive NVIDIA GPU diagnostic for Stable Diffusion
"""
import sys
from pathlib import Path
import subprocess

print("=" * 80)
print("NVIDIA GPU DIAGNOSTIC FOR STABLE DIFFUSION")
print("=" * 80)

results = {"passed": [], "warnings": [], "failed": []}

def check_item(name, condition, message, warning=False):
    if condition:
        print(f"✅ {name}: {message}")
        results["passed"].append(name) if not warning else results["warnings"].append(name)
        return True
    else:
        print(f"{'⚠️ ' if warning else '❌'} {name}: {message}")
        results["warnings" if warning else "failed"].append(name)
        return False

# 1. Check NVIDIA Driver
print("\n1. NVIDIA DRIVER")
try:
    result = subprocess.run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                          capture_output=True, text=True, timeout=5)
    driver = result.stdout.strip()
    check_item("NVIDIA Driver", True, f"Version {driver} (nvidia-smi working)")
except FileNotFoundError:
    check_item("NVIDIA Driver", False, "nvidia-smi not found - NVIDIA drivers not installed?")
except Exception as e:
    check_item("NVIDIA Driver", False, f"nvidia-smi error: {e}")

# 2. Check CUDA Toolkit
print("\n2. CUDA TOOLKIT")
try:
    result = subprocess.run(["nvcc", "--version"], capture_output=True, text=True, timeout=5)
    if "release" in result.stderr:
        cuda_version = [line for line in result.stderr.split('\n') if 'release' in line][0].split('release')[1].strip().split(',')[0]
        check_item("CUDA Toolkit", True, f"Version {cuda_version}")
    else:
        check_item("CUDA Toolkit", False, "nvcc not found - CUDA toolkit not installed")
except FileNotFoundError:
    check_item("CUDA Toolkit", False, "nvcc not found (optional but recommended)")

# 3. Check PyTorch Installation
print("\n3. PYTORCH")
try:
    import torch
    check_item("PyTorch", True, f"Version {torch.__version__}")

    # Check CUDA support
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        cuda_version_torch = torch.version.cuda
        check_item("CUDA support", True, f"✅ GPU: {gpu_name} | VRAM: {gpu_memory:.1f} GB | CUDA: {cuda_version_torch}")
        results["passed"].append("GPU Available")
        results["gpu_memory"] = gpu_memory
        results["gpu_name"] = gpu_name
    else:
        check_item("CUDA support", False, "PyTorch installed but CUDA not available")
        check_item("GPU Recommendation", False, "Install CUDA-enabled PyTorch: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118")

except ImportError:
    check_item("PyTorch", False, "PyTorch not installed: pip install torch torchvision")
except Exception as e:
    check_item("PyTorch", False, f"Error: {e}")

# 4. Check Diffusers
print("\n4. DIFFUSERS LIBRARY")
try:
    from diffusers import StableDiffusionXLPipeline
    check_item("Diffusers", True, "StableDiffusionXLPipeline available")
except ImportError:
    check_item("Diffusers", False, "Install: pip install diffusers transformers accelerate")

# 5. Check xFormers (Optional but Recommended)
print("\n5. XFORMERS (OPTIMIZATION)")
try:
    import xformers
    check_item("xFormers", True, f"Version {xformers.__version__} - Memory-efficient attention enabled!")
except ImportError:
    check_item("xFormers", False, "Optional but recommended: pip install xformers --index-url https://download.pytorch.org/whl/cu118", warning=True)

# 6. Check Available VRAM
if "gpu_memory" in results:
    print("\n6. VRAM ANALYSIS")
    vram = results["gpu_memory"]

    print(f"\n   Current VRAM: {vram:.1f} GB")
    print(f"   Minimum for SDXL (no optimizations): 8 GB")
    print(f"   Minimum for SDXL (with xFormers): 6 GB")
    print(f"   Minimum for SDXL (with CPU offload): 4 GB")

    if vram >= 12:
        print("   ✅ EXCELLENT: Full speed, no optimizations needed!")
        recommendation = "SD_DEVICE=cuda, SD_CPU_OFFLOAD=false"
    elif vram >= 8:
        print("   ✅ GOOD: Can run with attention slicing")
        recommendation = "SD_DEVICE=cuda, SD_ATTENTION_SLICING=true"
    elif vram >= 6:
        print("   ⚠️  MODERATE: Enable xFormers and attention slicing")
        recommendation = "SD_DEVICE=cuda, SD_USE_XFORMERS=true, SD_ATTENTION_SLICING=true"
    elif vram >= 4:
        print("   ⚠️  LOW: Enable CPU offload (slower but works)")
        recommendation = "SD_DEVICE=cuda, SD_CPU_OFFLOAD=true"
    else:
        print("   ❌ INSUFFICIENT: Use CPU mode instead")
        recommendation = "SD_DEVICE=cpu"

    print(f"\n   Recommended settings: {recommendation}")
    results["recommendation"] = recommendation

# 7. Quick Test Generation (if GPU available)
if results.get("gpu_memory"):
    print("\n7. QUICK TEST GENERATION")
    test_run = input("   Run a quick 5-second test generation? (y/N): ").strip().lower()

    if test_run == 'y':
        try:
            from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler
            import torch
            from PIL import Image
            import time

            print("\n   🎨 Testing SDXL generation...")

            # Simple test with tiny resolution for speed
            device = "cuda" if torch.cuda.is_available() else "cpu"
            torch_dtype = torch.float16 if device == "cuda" else torch.float32

            # Use tiny model variant or full model with minimal steps
            print("   Loading pipeline (first time may download model)...")
            start = time.time()

            pipeline = StableDiffusionXLPipeline.from_pretrained(
                "stabilityai/stable-diffusion-xl-base-1.0",
                torch_dtype=torch_dtype,
                use_safetensors=True,
                variant="fp16" if device == "cuda" else None
            )
            pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
                pipeline.scheduler.config,
                algorithm_type="dpmsolver++",
                steps=20
            )
            pipeline = pipeline.to(device)

            load_time = time.time() - start
            print(f"   ✅ Model loaded in {load_time:.1f}s")

            # Generate tiny test image
            print("   🖼️ Generating test image (512x512, 5 steps)...")
            start = time.time()
            with torch.no_grad():
                if device == "cuda":
                    with torch.autocast("cuda"):
                        result = pipeline(
                            prompt="test image, simple pattern",
                            width=512,
                            height=512,
                            num_inference_steps=5,
                            guidance_scale=1.0,
                            output_type="pil"
                        )
                else:
                    result = pipeline(
                        prompt="test image, simple pattern",
                        width=512,
                        height=512,
                        num_inference_steps=5,
                        guidance_scale=1.0,
                        output_type="pil"
                    )

            gen_time = time.time() - start
            image = result.images[0]
            test_file = Path("test_nvidia_gpu.jpg")
            image.save(test_file, quality=85)

            print(f"   ✅ Generated test image in {gen_time:.1f}s")
            print(f"   📁 Saved: {test_file.absolute()}")
            print(f"\n   🎉 SUCCESS! Your NVIDIA GPU is ready for Stable Diffusion!")

            if device == "cuda":
                torch.cuda.empty_cache()

        except KeyboardInterrupt:
            print("\n   ⏹️ Test cancelled by user")
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
            import traceback
            traceback.print_exc()

# 8. Environment Variable Setup
print("\n8. ENVIRONMENT SETUP")
print("""
   Add to your ~/.bashrc, ~/.zshrc, or .env file:

   export SD_DEVICE=cuda                    # Use NVIDIA GPU
   export SD_USE_XFORMERS=true             # Enable optimization (if xformers installed)
   export SD_ATTENTION_SLICING=auto        # Auto-enable for low VRAM
   export SD_MODEL=stabilityai/stable-diffusion-xl-base-1.0

   Then run:
   python youtube_mp3_transcript.py --url "your song" --image-generator stable-diffusion
""")

# Summary
print("\n" + "=" * 80)
print("DIAGNOSTIC SUMMARY")
print("=" * 80)

print("\n✅ Passed:")
for item in results["passed"]:
    print(f"   - {item}")

if results["warnings"]:
    print("\n⚠️  Warnings:")
    for item in results["warnings"]:
        print(f"   - {item}")

if results["failed"]:
    print("\n❌ Failed:")
    for item in results["failed"]:
        print(f"   - {item}")

if "gpu_memory" in results and results["gpu_memory"] >= 4:
    print("\n🎉 Your NVIDIA GPU is READY for Stable Diffusion!")
    print(f"   Recommended: {results.get('recommendation', 'SD_DEVICE=cuda')}")
elif "GPU Available" in results["passed"]:
    print("\n✅ You have an NVIDIA GPU, but may need to install CUDA-enabled PyTorch")
    print("   Run: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118")
else:
    print("\n⚠️  No NVIDIA GPU detected or not configured")
    print("   You can still use CPU mode (slower) or Cloudflare Worker (fast, free)")

print("\n📖 See NVIDIA_GPU_SETUP.md for detailed setup instructions")
print("=" * 80)
