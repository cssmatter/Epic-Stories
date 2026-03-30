#!/usr/bin/env python3
"""
Check and fix dependencies for YouTube Automation + Stable Diffusion
"""
import subprocess
import sys
import platform

def run_command(cmd, description):
    """Run a command and report result"""
    print(f"\n{'='*70}")
    print(f"{description}")
    print(f"{'='*70}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    return result.returncode == 0

def check_python():
    """Check Python version"""
    print(f"\n{'='*70}")
    print("Python Environment Check")
    print(f"{'='*70}")
    print(f"Python version: {sys.version}")
    print(f"Platform: {platform.platform()}")
    print(f"System: {platform.system()} {platform.release()}")
    return True

def check_torch():
    """Check PyTorch installation"""
    print(f"\n{'='*70}")
    print("PyTorch Check")
    print(f"{'='*70}")
    try:
        import torch
        print(f"[OK] PyTorch installed: {torch.__version__}")
        try:
            cuda = torch.cuda.is_available()
            status = "[OK]" if cuda else "[WARN]"
            print(f"{status} CUDA available: {cuda}")
            if cuda:
                print(f"   GPU: {torch.cuda.get_device_name(0)}")
                print(f"   CUDA version: {torch.version.cuda}")
        except:
            print("[WARN] Could not check CUDA")
        return True
    except ImportError:
        print("[ERROR] PyTorch not installed")
        return False

def check_diffusers():
    """Check diffusers installation"""
    print(f"\n{'='*70}")
    print("Diffusers Check")
    print(f"{'='*70}")
    try:
        import diffusers
        print(f"[OK] diffusers installed: {diffusers.__version__}")
        return True
    except ImportError:
        print("[ERROR] diffusers not installed")
        return False

def check_all():
    """Run all checks"""
    check_python()
    torch_ok = check_torch()
    diffusers_ok = check_diffusers()

    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"PyTorch: {'[OK]' if torch_ok else '[ERROR] Missing/Incorrect'}")
    print(f"diffusers: {'[OK]' if diffusers_ok else '[ERROR] Missing'}")

    if not torch_ok or not diffusers_ok:
        print("\n[INFO] To install all dependencies:")
        print("   pip install -r requirements.txt")
        return False
    return True

if __name__ == "__main__":
    success = check_all()
    sys.exit(0 if success else 1)
