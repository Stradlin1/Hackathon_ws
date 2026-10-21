"""Optional DeepSeek vision enrichment for found-item photos.

With DEEPSEEK_API_KEY set, the photo is sent to DeepSeek's multimodal chat model
(deepseek-flash) and comes back as a detailed Chinese description plus any visible
text. The local BLIP captioner remains the offline fallback, so the app still works
without a key or network.

The call happens once per photo, at registration time. Retrieval and reranking stay
local. The response is a proposal, not a fact: the description is shown to the user
for editing, and attributes are still derived by the evidence-checked extractor.
"""

from __future__ import annotations

import base64
import io
import json
import os
import urllib.error
import urllib.request

from .settings import flag, get, number

DEFAULT_MODEL = get('deepseek.model', 'deepseek-flash', env='DEEPSEEK_VISION_MODEL')
ENDPOINT = get('deepseek.url', 'https://api.deepseek.com/chat/completions',
               env='DEEPSEEK_API_URL')
TIMEOUT = number('deepseek.timeout', 25.0, env='DEEPSEEK_TIMEOUT')

PROMPT = """你是失物招领系统的视觉助手。看这张物品照片，只输出 json，格式：
{
  "description": "一句中文描述：物品类型、颜色、材质、形状、品牌、可见标记",
  "visible_text": "图片上清晰可读的文字（型号、品牌、序列号、名字），没有就空字符串",
  "attributes": {"category": "", "color": "", "material": "", "shape": "", "brand": "", "mark": ""}
}
只写照片里确实看得到的；不确定就留空字符串，不要猜。"""


def _api_key() -> str:
    return str(get('deepseek.api_key', '', env='DEEPSEEK_API_KEY') or '')


def available() -> bool:
    """True when settings.yaml (or the environment) provides a key and enables it."""
    if not flag('deepseek.enabled', True, env='DEEPSEEK_VISION'):
        return False
    return bool(_api_key())


def _encode(image) -> str:
    buffer = io.BytesIO()
    image.convert('RGB').save(buffer, format='JPEG', quality=85)
    return base64.b64encode(buffer.getvalue()).decode('ascii')


def _parse(content) -> dict | None:
    """Accept the model's JSON object, ignoring any surrounding prose."""
    if not isinstance(content, str) or not content.strip():
        return None
    start, end = content.find('{'), content.rfind('}')
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(content[start:end + 1])
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    description = data.get('description')
    if not isinstance(description, str) or not description.strip():
        return None
    visible = data.get('visible_text')
    attributes = data.get('attributes')
    cleaned = {}
    if isinstance(attributes, dict):
        for key, value in attributes.items():
            if isinstance(value, str) and value.strip():
                cleaned[key] = value.strip()[:60]
    return {
        'description': description.strip()[:400],
        'visible_text': visible.strip()[:120] if isinstance(visible, str) else '',
        'attributes': cleaned,
        'model': DEFAULT_MODEL,
    }


def describe_image(image) -> dict | None:
    """Return {'description', 'visible_text', 'attributes', 'model'} or None.

    None means the integration is off or the call failed, and the caller should fall
    back to the local captioner. No exception escapes: registration must not break
    because a third party is unreachable.
    """
    if not available():
        return None
    payload = {
        'model': DEFAULT_MODEL,
        'messages': [{
            'role': 'user',
            'content': [
                {'type': 'text', 'text': PROMPT},
                {'type': 'image_url',
                 'image_url': {'url': 'data:image/jpeg;base64,' + _encode(image)}},
            ],
        }],
        'response_format': {'type': 'json_object'},
        'max_tokens': 400,
        'temperature': 0.2,
    }
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + _api_key(),
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = json.loads(response.read().decode('utf-8'))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None
    try:
        content = body['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError):
        return None
    return _parse(content)
