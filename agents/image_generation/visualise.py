from pathlib import Path
import random
from websourcer import call_agent_async
from nanobanana import gemini_generate_images



async def visualize_generated_images(prompt: str):
    await call_agent_async(gemini_generate_images, prompt)
    all_images = [str(p) for p in Path("downloads").rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}]
    image_paths = random.sample(all_images, min(5, len(all_images)))