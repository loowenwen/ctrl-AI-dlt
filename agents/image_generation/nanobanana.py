from google import genai
from google.genai import types as genai_types
from typing import List, Dict, Any, Optional
from PIL import Image
from io import BytesIO
import asyncio
import certifi
import os
from dotenv import load_dotenv

load_dotenv()
os.environ['SSL_CERT_FILE'] = certifi.where()


client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def gemini_generate_images(
    prompt: str,
    ref_image_paths: Optional[List[str]] = None,
    *,
    out_dir: str = "generated",
    base_name: str = "gemini_image",
    save_limit: Optional[int] = None,
    collect_text: bool = True,
) -> Dict[str, Any]:
    """Versatile Gemini 2.5 Flash Image generator.

    Generates image(s) from a text prompt, optionally conditioning on one or
    more reference images (text+image editing / composition).

    Behavior mirrors the official docs' pattern of calling
    `client.models.generate_content(model="gemini-2.5-flash-image-preview", contents=[...])`.

    Args:
        prompt: Text instruction describing what to generate.
        ref_image_paths: Optional list of local image file paths to include as input.
        out_dir: Directory to save generated images (auto-created).
        base_name: Prefix for saved filenames, e.g. "gemini_image" -> gemini_image_1.png.
        save_limit: If set, stop saving after this many image parts even if the
            model returns more (model may not honor requested counts exactly).
        collect_text: If True, capture any interleaved text parts returned by the model.

    Returns:
        A dict: {"saved": [paths...], "texts": [...], "count": int}.
    """
    # Build the request contents: prompt + optional inline image parts
    parts: List[Any] = [prompt]
    if ref_image_paths:
        for pth in ref_image_paths:
            try:
                img = Image.open(pth)
            except Exception:
                continue  # skip unreadable images
            buf = BytesIO()
            img.save(buf, format="PNG")
            img_bytes = buf.getvalue()
            parts.append(
                genai_types.Part(
                    inline_data=genai_types.Blob(mime_type="image/png", data=img_bytes)
                )
            )

    response = client.models.generate_content(
        model="gemini-2.5-flash-image-preview",
        contents=parts,
    )

    print(response)

    # Prepare output directory
    out_path = os.path.join(out_dir)
    os.makedirs(out_path, exist_ok=True)

    saved: List[str] = []
    texts: List[str] = []
    img_idx = 1

    # Iterate over response parts and save images; optionally collect text
    for part in response.candidates[0].content.parts:
        # Text side-channel
        if getattr(part, "text", None):
            if collect_text:
                texts.append(part.text)
            continue

        # Image bytes
        inline = getattr(part, "inline_data", None)
        if inline and inline.data:
            try:
                out_img = Image.open(BytesIO(inline.data))
                fname = f"{base_name}.png"
                fpath = os.path.join(out_path, fname)
                out_img.save(fpath)
                saved.append(fpath)
                if save_limit is not None and len(saved) >= save_limit:
                    break
            except Exception:
                # Skip corrupted image parts gracefully
                continue

    return {"saved": saved, "texts": texts if collect_text else [], "count": len(saved)}


gemini_generate_images("generate HDB BTO Toa Payoh")