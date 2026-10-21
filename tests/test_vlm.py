"""DeepSeek vision integration: graceful degradation and response parsing."""

from __future__ import annotations

import json
import urllib.error

import pytest

from matching import settings, vlm


def _isolate(monkeypatch, tmp_path):
    """Ignore whatever settings.yaml the developer has on this machine."""
    monkeypatch.setattr(settings, 'PATH', tmp_path / 'missing.yaml')
    monkeypatch.setattr(settings, '_cache', None)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode('utf-8')

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class Picture:
    def convert(self, mode):
        return self

    def save(self, buffer, format=None, quality=None):
        buffer.write(b'fake-jpeg')


def test_integration_is_off_without_a_key(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
    assert vlm.available() is False
    assert vlm.describe_image(Picture()) is None


def test_integration_can_be_switched_off_explicitly(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-key')
    monkeypatch.setenv('DEEPSEEK_VISION', 'off')
    assert vlm.available() is False


def test_parse_keeps_description_and_drops_empty_attributes():
    parsed = vlm._parse('前缀 {"description": "白色塑料水杯，杯身印有 FUGUANG",'
                        ' "visible_text": "FUGUANG", "attributes": {"color": "白色",'
                        ' "brand": "", "material": "塑料"}} 后缀')
    assert parsed['description'] == '白色塑料水杯，杯身印有 FUGUANG'
    assert parsed['visible_text'] == 'FUGUANG'
    assert parsed['attributes'] == {'color': '白色', 'material': '塑料'}


@pytest.mark.parametrize('content', ['', 'not json', '{}', '{"description": ""}', '{"description": 3}'])
def test_parse_rejects_unusable_content(content):
    assert vlm._parse(content) is None


def test_describe_image_posts_a_base64_image_and_parses_the_reply(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-key')
    monkeypatch.delenv('DEEPSEEK_VISION', raising=False)
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured['url'] = request.full_url
        captured['body'] = json.loads(request.data.decode('utf-8'))
        captured['auth'] = request.headers.get('Authorization')
        return FakeResponse({'choices': [{'message': {'content':
            '{"description": "白色充电宝", "visible_text": "", "attributes": {"category": "充电宝"}}'}}]})

    monkeypatch.setattr(vlm.urllib.request, 'urlopen', fake_urlopen)

    result = vlm.describe_image(Picture())
    assert result['description'] == '白色充电宝'
    assert captured['url'] == vlm.ENDPOINT
    assert captured['auth'] == 'Bearer test-key'
    assert captured['body']['model'] == vlm.DEFAULT_MODEL
    assert captured['body']['messages'][0]['content'][1]['image_url']['url'].startswith(
        'data:image/jpeg;base64,')


def test_describe_image_returns_none_when_the_call_fails(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-key')
    monkeypatch.delenv('DEEPSEEK_VISION', raising=False)

    def boom(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, 500, 'boom', None, None)

    monkeypatch.setattr(vlm.urllib.request, 'urlopen', boom)
    assert vlm.describe_image(Picture()) is None
