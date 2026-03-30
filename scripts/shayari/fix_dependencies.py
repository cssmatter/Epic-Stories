#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Install and verify correct dependencies for Stable Diffusion
"""
import subprocess
import sys
import platform
import os

# Fix Windows console encoding for emoji support
if sys.platform == "win32":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    else:
        os.environ['PYTHONIOENCODING'] = 'utf-8'

def run_pip(args, description):
    """Run pip command"""
    print(f"\n{'='*70}")
    print(f"{description}")
    print(f"{'='*70}")
    cmd = [sys.executable, "-m", "pip"] + args
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode == 0

def detect_cuda():
    """Detect if CUDA is available"""
    try:
        import torch
        if torch.cuda.is_available():
            return True, torch.version.cuda
    except:
        pass
    return False, None

def fix_torch():
    """Fix PyTorch installation"""
    print("\n" + "="*70)
    print("FIXING PYTORCH INSTALLATION")
    print("="*70)

    # Check current version
    try:
        import torch
        current_version = torch.__version__
        print(f"Current torch: {current_version}")
        needs_fix = not (current_version.startswith("2.0.1") or current_version.startswith("2.0.1+"))
        if not needs_fix:
            print("[OK] PyTorch 2.0.1 already installed")
            return True
    except ImportError:
        print("PyTorch not installed")
        needs_fix = True

    if not needs_fix:
        return True

    print("\n[PKG] Removing incorrect PyTorch version...")
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "torch", "torchvision", "torchaudio"], capture_output=True)

    print("\n[PKG] Installing PyTorch 2.0.1...")

    # Detect CUDA capability
    has_cuda, cuda_version = detect_cuda()
    if has_cuda:
        print(f"[OK] CUDA detected: version {cuda_version}")
        if cuda_version.startswith("11.8"):
            torch_url = "https://download.pytorch.org/whl/cu118"
        elif cuda_version.startswith("12.1"):
            torch_url = "https://download.pytorch.org/whl/cu121"
        else:
            torch_url = "https://download.pytorch.org/whl/cu118"  # default to cu118
        print(f"Using CUDA PyTorch from {torch_url}")
    else:
        print("[INFO] No CUDA detected - installing CPU-only version")
        torch_url = "https://download.pytorch.org/whl/cpu"

    success = run_pip(
        ["install", "torch==2.0.1", "torchvision==0.15.2", "--index-url", torch_url],
        "Installing PyTorch 2.0.1"
    )

    if success:
        print("[OK] PyTorch 2.0.1 installed successfully")
    else:
        print("[ERROR] Failed to install PyTorch 2.0.1")
        return False

    return True

def fix_diffusers():
    """Ensure diffusers is installed"""
    print("\n" + "="*70)
    print("CHECKING DIFFUSERS")
    print("="*70)
    try:
        import diffusers
        print(f"[OK] diffusers already installed: {diffusers.__version__}")
        return True
    except ImportError:
        print("diffusers not found - installing...")
        return run_pip(["install", "diffusers", "transformers", "accelerate"], "Installing diffusers")

def fix_other_deps():
    """Install other required dependencies"""
    print("\n" + "="*70)
    print("CHECKING OTHER DEPENDENCIES")
    print("="*70)
    # Try to install from requirements.txt if available
    req_file = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if os.path.exists(req_file):
        print(f"Found requirements.txt at {req_file}")
        return run_pip(["install", "-r", req_file], "Installing from requirements.txt")
    else:
        # Install minimal dependencies
        deps = [
            "yt-dlp",
            "youtube-transcript-api",
            "google-genai",
            "Pillow>=9.0.0",
            "moviepy",
            "numpy",
            "imageio-ffmpeg"
        ]
        return run_pip(["install"] + deps, "Installing core dependencies")

def main():
    print("="*70)
    print("STABLE DIFFUSION DEPENDENCY FIXER")
    print("="*70)

    steps = [
        ("PyTorch", fix_torch),
        ("diffusers", fix_diffusers),
        ("other_deps", fix_other_deps)
    ]

    results = {}
    for name, func in steps:
        try:
            results[name] = func()
        except Exception as e:
            print(f"[ERROR] Error during {name}: {e}")
            results[name] = False

    # Final check
    print("\n" + "="*70)
    print("FINAL VERIFICATION")
    print("="*70)

    all_ok = True
    for name, success in results.items():
        status = "[OK]" if success else "[ERROR]"
        print(f"{status} {name}")
        if not success:
            all_ok = False

    if all_ok:
        print("\n[SUCCESS] All dependencies are correctly installed!")
        print("\n[INFO] Next steps:")
        print("   1. Run: python check_dependencies.py (to verify)")
        print("   2. Try the Stable Diffusion test: python test_stable_diffusion.py")
        print("   3. Run full pipeline: python youtube_mp3_transcript.py --url YOUR_URL --image-generator stable-diffusion")
    else:
        print("\n[ERROR] Some dependencies failed to install")
        print("   Please check the error messages above and try manually.")

    return all_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
