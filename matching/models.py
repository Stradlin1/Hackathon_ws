"""Lazy-loaded multimodal models (shared across Streamlit reruns)."""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from PIL import Image, ImageOps


@lru_cache(maxsize=1)
def _image_encoder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("sentence-transformers/clip-ViT-B-32")


@lru_cache(maxsize=1)
def _text_encoder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("sentence-transformers/clip-ViT-B-32-multilingual-v1")


@lru_cache(maxsize=1)
def _image_captioner():
    from transformers import BlipForConditionalGeneration, BlipProcessor
    name = "Salesforce/blip-image-captioning-base"
    return BlipProcessor.from_pretrained(name), BlipForConditionalGeneration.from_pretrained(name)


def clean_image(image: Image.Image) -> Image.Image:
    """Remove uploaded EXIF metadata before storing or embedding the image."""
    oriented = ImageOps.exif_transpose(image)
    oriented.thumbnail((1600, 1600))
    rgb = oriented.convert("RGB")
    return Image.fromarray(np.asarray(rgb).copy())


def encode_image(image: Image.Image) -> np.ndarray:
    arr = np.asarray(_image_encoder().encode(image), dtype=np.float32).reshape(-1)
    if not arr.size or not np.all(np.isfinite(arr)):
        raise ValueError("Invalid image embedding")
    return arr


def encode_text(text: str) -> np.ndarray:
    arr = np.asarray(_text_encoder().encode(text), dtype=np.float32).reshape(-1)
    if not arr.size or not np.all(np.isfinite(arr)):
        raise ValueError("Invalid text embedding")
    return arr


def caption_image(image: Image.Image) -> str:
    import torch
    processor, model = _image_captioner()
    inputs = processor(images=image, return_tensors="pt")
    with torch.inference_mode():
        output = model.generate(**inputs, max_new_tokens=70)
    return processor.decode(output[0], skip_special_tokens=True).strip()
