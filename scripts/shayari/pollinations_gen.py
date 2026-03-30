import requests
import random
from io import BytesIO
from PIL import Image
from urllib.parse import quote
import logging

log = logging.getLogger(__name__)

def generate_with_pollinations(
    image_prompt,
    style,
    output_path,
    width,
    height,
    crop_fill_resize_func, # Pass the function from the main script
    build_sd3_prompt_func   # Pass the function from the main script
):
    """Generate image via Pollinations AI (Flux) and save as JPEG."""
    full_prompt = build_sd3_prompt_func(image_prompt, style)
    safe_prompt = quote(full_prompt)
    
    # Pollinations URL with Flux model and 9:16 approx dimensions
    url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width={width}&height={height}&model=flux&nologo=true&seed={random.randint(0, 99999)}"
    
    log.info(f"  [Pollinations] Generating: {image_prompt[:70]}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=60)
        resp.raise_for_status()
        
        img = Image.open(BytesIO(resp.content)).convert("RGB")
        img = crop_fill_resize_func(img, width, height)
        img.save(str(output_path), "JPEG", quality=95, optimize=True)
        log.info(f"  [Pollinations] Saved → {output_path}")
        return str(output_path)
    except Exception as e:
        raise RuntimeError(f"Pollinations generation failed: {e}")
