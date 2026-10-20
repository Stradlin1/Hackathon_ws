"""Lazy-loaded multimodal models (shared across Streamlit reruns)."""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from PIL import Image, ImageOps


def _sentence_transformer(name: str):
    """Load from the local cache first; only touch the network when it is missing."""
    from sentence_transformers import SentenceTransformer

    try:
        return SentenceTransformer(name, local_files_only=True)
    except (OSError, ValueError, AttributeError):
        return SentenceTransformer(name)


@lru_cache(maxsize=1)
def _image_encoder():
    return _sentence_transformer("sentence-transformers/clip-ViT-B-32")


@lru_cache(maxsize=1)
def _text_encoder():
    return _sentence_transformer("sentence-transformers/clip-ViT-B-32-multilingual-v1")


@lru_cache(maxsize=1)
def _image_captioner():
    import torch
    from transformers import BlipForConditionalGeneration, BlipProcessor

    name = "Salesforce/blip-image-captioning-base"
    try:
        processor = BlipProcessor.from_pretrained(name, local_files_only=True)
        model = BlipForConditionalGeneration.from_pretrained(name, local_files_only=True)
    except (OSError, ValueError, AttributeError):
        processor = BlipProcessor.from_pretrained(name)
        model = BlipForConditionalGeneration.from_pretrained(name)
    if torch.cuda.is_available():
        try:
            model = model.to("cuda")
        except (RuntimeError, OSError):
            pass
    model.eval()
    return processor, model


def clean_image(image: Image.Image) -> Image.Image:
    """Remove uploaded EXIF metadata before storing or embedding the image."""
    oriented = ImageOps.exif_transpose(image)
    oriented.thumbnail((1600, 1600))
    rgb = oriented.convert("RGB")
    return Image.fromarray(np.asarray(rgb).copy())


def encode_image(image: Image.Image) -> np.ndarray:
    arr = np.asarray(_image_encoder().encode(image), dtype=np.float32).reshape(-1)
    if not arr.size or not np.all(np.isfinite(arr)):
        raise ValueError("无效的图像向量")
    return arr


def encode_text(text: str) -> np.ndarray:
    arr = np.asarray(_text_encoder().encode(text), dtype=np.float32).reshape(-1)
    if not arr.size or not np.all(np.isfinite(arr)):
        raise ValueError("无效的文本向量")
    return arr


def caption_image(image: Image.Image) -> str:
    import torch
    processor, model = _image_captioner()
    device = next(model.parameters()).device
    inputs = processor(images=image, return_tensors="pt").to(device)
    with torch.inference_mode():
        output = model.generate(**inputs, max_new_tokens=70)
    return processor.decode(output[0], skip_special_tokens=True).strip()
