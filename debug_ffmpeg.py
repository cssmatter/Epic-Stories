
import subprocess
import imageio_ffmpeg
import os

def debug_ffmpeg():
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    
    bg_img = r"C:\git\youtube-automation\Epic-Stories-All-youtube-automation-shorts\assets\devotional_hindi\generated_backgrounds\bg_1.png"
    overlay_img = r"C:\git\youtube-automation\Epic-Stories-All-youtube-automation-shorts\temp_overlay_1.png"
    music = r"C:\git\youtube-automation\Epic-Stories-All-youtube-automation-shorts\assets\shayari\Waterfall - Aakash Gandhi.mp3"
    output = r"C:\git\youtube-automation\Epic-Stories-All-youtube-automation-shorts\debug_video.mp4"
    
    # Ensure overlay exists for test
    if not os.path.exists(overlay_img):
        print("Overlay missing, creating dummy")
        with open(overlay_img, "wb") as f:
            f.write(b"dummy")

    inputs = [
        "-loop", "1", "-i", bg_img,
        "-loop", "1", "-i", overlay_img,
        "-stream_loop", "-1", "-i", music,
        "-f", "lavfi", "-i", "color=c=black:s=720x1280"
    ]
    
    filter_complex = (
        "[0:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,format=yuva420p,colorchannelmixer=aa=0.5[img_low_op];"
        "[3:v][img_low_op]overlay=format=auto[bg_layered];"
        "[bg_layered][1:v]overlay=format=auto[v_final]"
    )
    
    cmd = [ffmpeg_exe, "-y", "-threads", "1"] + inputs
    cmd.extend(["-filter_complex", filter_complex])
    cmd.extend(["-map", "[v_final]", "-map", "2:a"])
    cmd.extend([
        "-t", "5",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        output
    ])
    
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("--- STDOUT ---")
    print(result.stdout)
    print("--- STDERR ---")
    print(result.stderr)
    print(f"Return code: {result.returncode}")

if __name__ == "__main__":
    debug_ffmpeg()
