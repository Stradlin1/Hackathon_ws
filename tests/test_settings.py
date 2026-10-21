"""settings.yaml: file values, environment overrides and safe fallbacks."""

from __future__ import annotations

import pytest

from matching import settings, vlm


def _use(monkeypatch, tmp_path, text):
    path = tmp_path / 'settings.yaml'
    if text is not None:
        path.write_text(text, encoding='utf-8')
    monkeypatch.setattr(settings, 'PATH', path)
    monkeypatch.setattr(settings, '_cache', None)
    for name in ('DEEPSEEK_API_KEY', 'DEEPSEEK_VISION', 'DEEPSEEK_TIMEOUT'):
        monkeypatch.delenv(name, raising=False)


def test_missing_file_falls_back_to_defaults(monkeypatch, tmp_path):
    _use(monkeypatch, tmp_path, None)
    assert settings.get('deepseek.api_key', '') == ''
    assert settings.get('deepseek.model', 'deepseek-flash') == 'deepseek-flash'
    assert settings.flag('deepseek.enabled') is True


def test_file_values_are_read(monkeypatch, tmp_path):
    _use(monkeypatch, tmp_path, 'deepseek:\n  api_key: sk-test\n  timeout: 7\n')
    assert settings.get('deepseek.api_key') == 'sk-test'
    assert settings.number('deepseek.timeout', 25) == 7
    assert vlm.available() is True


def test_environment_wins_over_the_file(monkeypatch, tmp_path):
    _use(monkeypatch, tmp_path, 'deepseek:\n  api_key: sk-file\n')
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'sk-env')
    assert settings.get('deepseek.api_key', env='DEEPSEEK_API_KEY') == 'sk-env'


def test_disabled_in_file_switches_the_integration_off(monkeypatch, tmp_path):
    _use(monkeypatch, tmp_path, 'deepseek:\n  enabled: false\n  api_key: sk-test\n')
    assert settings.flag('deepseek.enabled') is False
    assert vlm.available() is False


@pytest.mark.parametrize('value, expected', [('off', False), ('false', False), ('0', False),
                                             ('on', True), ('true', True), ('1', True)])
def test_flag_accepts_the_usual_spellings(monkeypatch, tmp_path, value, expected):
    _use(monkeypatch, tmp_path, f'deepseek:\n  enabled: "{value}"\n')
    assert settings.flag('deepseek.enabled') is expected


def test_yaml_off_disables_the_text_generator(monkeypatch, tmp_path):
    _use(monkeypatch, tmp_path, 'fingerprint:\n  text_model: off\n')
    from matching.fingerprint import _load_generator
    _load_generator.cache_clear()
    assert _load_generator() is None


def test_broken_file_is_ignored(monkeypatch, tmp_path):
    _use(monkeypatch, tmp_path, 'deepseek: [unclosed\n')
    assert settings.get('deepseek.api_key', 'fallback') == 'fallback'


def test_number_falls_back_on_garbage(monkeypatch, tmp_path):
    _use(monkeypatch, tmp_path, 'deepseek:\n  timeout: soon\n')
    assert settings.number('deepseek.timeout', 25) == 25
