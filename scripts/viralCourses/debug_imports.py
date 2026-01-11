
import sys
import os
import time

print("Starting debug...", flush=True)

def test_import(module_name):
    start = time.time()
    print(f"Importing {module_name}...", end=" ", flush=True)
    try:
        __import__(module_name)
        print(f"Done ({time.time() - start:.2f}s)", flush=True)
    except Exception as e:
        print(f"FAILED: {e}", flush=True)

test_import("json")
test_import("skia")
test_import("numpy")
print("Testing MoviePy imports...", flush=True)
try:
    s = time.time()
    from moviepy.video.io.VideoFileClip import VideoFileClip
    print(f"moviepy.video.io.VideoFileClip imported ({time.time() - s:.2f}s)", flush=True)
    s = time.time()
    from moviepy.video.compositing.CompositeVideoClip import concatenate_videoclips
    print(f"moviepy.video.compositing.CompositeVideoClip imported ({time.time() - s:.2f}s)", flush=True)
except Exception as e:
    print(f"MoviePy Import Failed: {e}", flush=True)

print("Testing TTS import (this might be slow)...", flush=True)
test_import("TTS.api")

print("Debug complete.", flush=True)
