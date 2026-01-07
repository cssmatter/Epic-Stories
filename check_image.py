
import subprocess
import imageio_ffmpeg
import os

def check_image():
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffprobe_exe = ffmpeg_exe.replace("ffmpeg", "ffprobe")
    
    bg_img = r"C:\git\youtube-automation\Epic-Stories-All-youtube-automation-shorts\assets\devotional_hindi\generated_backgrounds\bg_1.png"
    
    cmd = [ffprobe_exe, "-v", "error", "-show_entries", "stream=pix_fmt", "-of", "default=noprint_wrappers=1:nokey=1", bg_img]
    
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"Pixel format: {result.stdout.strip()}")
    print(f"Error (if any): {result.stderr}")

if __name__ == "__main__":
    check_image()
