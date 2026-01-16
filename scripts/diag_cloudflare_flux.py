
import requests
import os
import sys
from PIL import Image

# Add path to config
sys.path.append(os.path.join(os.getcwd(), 'scripts', 'epicstories'))
import config

def test_cloudflare_flux():
    api_url = config.CLOUDFLARE_WORKER_URL
    auth_token = config.CLOUDFLARE_AUTH_TOKEN
    
    prompt = "A majestic renaissance painting of a king on a throne, cinematic lighting, 16:9 aspect ratio"
    output_path = "test_flux_dims.jpg"
    
    headers = {
        "Authorization": auth_token,
        "Content-Type": "application/json"
    }

    payload = {
        "prompt": prompt + ", cinematic lighting, high quality, 16:9 aspect ratio, 4k resolution",
        "width": 1920,
        "height": 1080
    }

    print(f"Requesting 1920x1080 image from Cloudflare (Flux model)...")
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=60)
        
        if response.status_code == 200:
            # Check if it's actually an image or just JSON text
            if response.content.startswith(b'{"'):
                print(f"FAILED: Received JSON instead of image data: {response.content.decode()[:200]}")
                return

            with open(output_path, "wb") as f:
                f.write(response.content)
            
            try:
                with Image.open(output_path) as img:
                    width, height = img.size
                    print(f"SUCCESS! Received image: {width}x{height}")
                    if width == 1920 and height == 1080:
                        print("Status: PERFECT (1920x1080 Match)")
                    else:
                        print(f"Status: MISMATCH (Got {width}x{height})")
            except Exception as img_err:
                print(f"FAILED to identify image. First 100 bytes: {response.content[:100]}")
        else:
            print(f"ERROR: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    test_cloudflare_flux()
