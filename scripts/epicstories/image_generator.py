"""
Image Generator for Epic Stories
Uses Cloudflare Worker to generate images from text prompts
"""
import os
import hashlib
import time
import requests
import json
from PIL import Image, ImageDraw, ImageFont
import config

class ImageGenerator:
    def __init__(self):
        self.cache_dir = config.IMAGE_CACHE_DIR
        self.api_url = config.CLOUDFLARE_WORKER_URL
        self.auth_token = config.CLOUDFLARE_AUTH_TOKEN
        
    def _get_cache_path(self, prompt):
        """Generate cache file path from prompt"""
        # Create hash of prompt for filename
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{prompt_hash}.jpg")
    
    def generate_image(self, prompt, scene_number=None, is_thumbnail=False):
        """
        Generate image from text prompt using Cloudflare Worker
        
        Args:
            prompt: Text description of image
            scene_number: Optional scene number for fallback naming
            is_thumbnail: Whether to use the dedicated thumbnail worker
            
        Returns:
            Path to generated image file
        """
        # Check cache first
        cache_path = self._get_cache_path(prompt)
        if os.path.exists(cache_path):
            print(f"Using cached image for: {prompt[:50]}...")
            return cache_path
        
        # Generate new image
        return self._generate_with_cloudflare(prompt, cache_path, scene_number)
    
    def _generate_with_cloudflare(self, prompt, output_path, scene_number=None, is_thumbnail=False):
        """Generates an image using Cloudflare Worker API."""
        # Use the dedicated thumbnail worker if requested
        api_url = config.CLOUDFLARE_THUMBNAIL_WORKER_URL if is_thumbnail else self.api_url
        
        # Enhance prompt with aspect ratio request and quality keywords
        if "aspect ratio" not in prompt.lower():
            enhanced_prompt = f"{prompt}, cinematic lighting, high quality, 16:9 aspect ratio, 4k resolution"
        else:
            enhanced_prompt = prompt

        headers = {
            "Authorization": self.auth_token,
            "Content-Type": "application/json"
        }

        payload = {
            "prompt": enhanced_prompt,
            "width": 1920,
            "height": 1080
        }

        try:
            worker_name = "Lucid-Origin" if is_thumbnail else "Cloudflare"
            print(f"Generating via {worker_name}: {prompt[:40]}...")
            
            response = requests.post(api_url, json=payload, headers=headers, timeout=60)
            
            if response.status_code == 200:
                # User requested wait time after generation
                print("Waiting 2 seconds for image generation...")
                time.sleep(2)
                
                # VALIDATION: Check for "object Object" or JSON error response saved as image
                if len(response.content) < 1000 or response.content.startswith(b'{') or b'object Object' in response.content[:100]:
                    print(f"FAILED: Received invalid image data (Size: {len(response.content)} bytes). Content start: {response.content[:50]}")
                    return self._generate_placeholder(prompt, output_path, scene_number)

                with open(output_path, "wb") as f:
                    f.write(response.content)
                
                print(f"Image saved to: {output_path}")
                return output_path
            else:
                print(f"Cloudflare generation failed: {response.status_code} - {response.text}")
                return self._generate_placeholder(prompt, output_path, scene_number)

        except Exception as e:
            print(f"Error during Cloudflare generation: {e}")
            return self._generate_placeholder(prompt, output_path, scene_number)

    def _generate_placeholder(self, prompt, output_path, scene_number=None):
        """Generate placeholder image with text (Fallback)"""
        # Create a gradient background
        img = Image.new('RGB', (config.GEN_WIDTH, config.GEN_HEIGHT), color='#1a1a2e')
        draw = ImageDraw.Draw(img)
        
        # Draw gradient effect
        for y in range(config.GEN_HEIGHT):
            color_val = int(26 + (y / config.GEN_HEIGHT) * 30)
            draw.line([(0, y), (config.GEN_WIDTH, y)], fill=(color_val, color_val, color_val + 20))
        
        # Add scene number if provided
        if scene_number is not None:
            try:
                # Try to use a nice font
                title_font = ImageFont.truetype("arial.ttf", 120)
                text_font = ImageFont.truetype("arial.ttf", 40)
            except:
                title_font = ImageFont.load_default()
                text_font = ImageFont.load_default()
            
            # Draw scene number
            title = f"Scene {scene_number}"
            bbox = draw.textbbox((0, 0), title, font=title_font)
            title_width = bbox[2] - bbox[0]
            title_height = bbox[3] - bbox[1]
            draw.text(
                ((config.GEN_WIDTH - title_width) // 2, (config.GEN_HEIGHT - title_height) // 2 - 100),
                title,
                fill='white',
                font=title_font
            )
            
            # Draw prompt excerpt
            prompt_excerpt = prompt[:100] + "..." if len(prompt) > 100 else prompt
            bbox = draw.textbbox((0, 0), prompt_excerpt, font=text_font)
            text_width = bbox[2] - bbox[0]
            draw.text(
                ((config.GEN_WIDTH - text_width) // 2, (config.GEN_HEIGHT) // 2 + 50),
                prompt_excerpt,
                fill='#cccccc',
                font=text_font
            )
        
        # Save placeholder
        img.save(output_path)
        print(f"Placeholder image saved to: {output_path}")
        
        return output_path

def test_generator():
    """Test the image generator"""
    generator = ImageGenerator()
    
    test_prompts = [
        "A cute robot cooking breakfast in a futuristic kitchen",
    ]
    
    for i, prompt in enumerate(test_prompts, 1):
        image_path = generator.generate_image(prompt, scene_number=i)
        print(f"Generated: {image_path}")

if __name__ == "__main__":
    print("Testing Image Generator (Cloudflare)...")
    test_generator()
