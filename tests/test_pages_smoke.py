"""Exercise the new Streamlit page flows without downloading model weights."""

from __future__ import annotations

import importlib
import io
import sys
import types
from contextlib import nullcontext
from datetime import date
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image


class Rerun(Exception):
    pass


class Session(dict):
    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


class UI(types.ModuleType):
    def __init__(self):
        super().__init__('streamlit')
        self.session_state = Session(username='owner', authentication_status=True)
        self.sidebar = self
        self.uploaded = None
        self.submit = False
        self.clicked = set()
        self.warning_messages = []
        self.cache_data = lambda **kwargs: (lambda f: f)

    def form(self, *args, **kwargs):
        return nullcontext()

    def spinner(self, *args, **kwargs):
        return nullcontext()

    def expander(self, *args, **kwargs):
        return nullcontext()

    def columns(self, n):
        return [nullcontext() for _ in range(n)]

    def button(self, label, **kwargs):
        return (kwargs.get('key') or label) in self.clicked

    def form_submit_button(self, label, **kwargs):
        return self.submit and label in {'查找可能匹配', '提交并查找可能匹配', '更新匹配结果'}

    def text_area(self, label, value='', **kwargs):
        return value or ('lost black umbrella' if label.startswith('描述物品') else 'found black umbrella')

    def text_input(self, label, **kwargs):
        return '红色贴纸'

    def selectbox(self, label, options, **kwargs):
        return options[0]

    def date_input(self, *args, **kwargs):
        return date(2026, 10, 20)

    def file_uploader(self, *args, **kwargs):
        return self.uploaded

    def rerun(self):
        raise Rerun()

    def warning(self, message):
        self.warning_messages.append(str(message))

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class FakeDatabase:
    inserted = []
    closed = False

    def __init__(self):
        self.closed = False

    def insert_item(self, item):
        self.inserted.append(item)

    def get_user(self, username):
        return SimpleNamespace(username=username)

    def insert_lost_item(self, item, owner):
        pass

    def insert_found_item(self, item, owner):
        pass

    def get_item(self, id):
        return SimpleNamespace(id=id, image=None, description=f'item-{id}')

    def close(self):
        self.closed = True


def install_fake_modules(monkeypatch):
    ui = UI()
    monkeypatch.setitem(sys.modules, 'streamlit', ui)
    fake_db = types.ModuleType('db_manager')
    fake_db.Database = FakeDatabase
    fake_db.Item = lambda *args: SimpleNamespace(id=args[0], image=args[1], emb=args[2], description=args[3], time=args[4], location=args[5])
    monkeypatch.setitem(sys.modules, 'db_manager', fake_db)
    return ui


def test_lost_report_page_generates_session(monkeypatch):
    ui = install_fake_modules(monkeypatch)
    ui.submit = True
    module = importlib.import_module('state.lost')
    monkeypatch.setattr(module, 'st', ui)
    monkeypatch.setattr(module, 'encode_text', lambda text: np.array([1., 0.]))
    monkeypatch.setattr(module, 'fingerprint_from_text', lambda text: {'attributes': {'color': 'black'}, 'method': 'rules'})
    monkeypatch.setattr(module, 'FingerprintStore', lambda: SimpleNamespace(put=lambda *args: None))
    monkeypatch.setattr(module, 'build_session', lambda **kwargs: {'user': 'owner', 'asked': [], 'answers': {}})
    with pytest.raises(Rerun):
        module.lost(SimpleNamespace(logout=lambda **kwargs: None))
    assert ui.session_state.state == 'interactive_match'
    assert ui.session_state.match_session['user'] == 'owner'


def test_found_report_page_generates_session(monkeypatch):
    ui = install_fake_modules(monkeypatch)
    ui.submit = True
    picture = Image.new('RGB', (25, 25), 'red')
    memory = io.BytesIO()
    picture.save(memory, 'PNG')
    ui.uploaded = SimpleNamespace(getvalue=lambda: memory.getvalue())
    module = importlib.import_module('state.found')
    monkeypatch.setattr(module, 'st', ui)
    monkeypatch.setattr(module, '_cached_caption', lambda data: 'a black umbrella')
    monkeypatch.setattr(module, 'encode_image', lambda img: np.array([1., 0.]))
    monkeypatch.setattr(module, 'fingerprint_from_text', lambda text, caption: {'attributes': {'color': 'black'}, 'method': 'rules'})
    monkeypatch.setattr(module, 'FingerprintStore', lambda: SimpleNamespace(put=lambda *args: None))
    monkeypatch.setattr(module, 'build_session', lambda **kwargs: {'user': 'owner', 'asked': [], 'answers': {}})
    with pytest.raises(Rerun):
        module.found(SimpleNamespace(logout=lambda **kwargs: None))
    assert ui.session_state.state == 'interactive_match'
    assert FakeDatabase.inserted[-1].image.size == (25, 25)
    assert FakeDatabase.inserted[-1].image.getexif() == {}


def test_interactive_question_changes_answer_and_reranks(monkeypatch):
    ui = install_fake_modules(monkeypatch)
    ui.submit = True
    fp = lambda **attrs: {'attributes': attrs, 'method': 'rules'}
    ui.session_state.match_session = {
        'user': 'owner', 'direction': 'lost', 'item_id': 100,
        'fingerprint': fp(category='umbrella'),
        'candidates': [
            {'item_id': 1, 'description': 'red sticker', 'semantic_score': 0.7, 'fingerprint': fp(mark='red sticker')},
            {'item_id': 2, 'description': 'blue sticker', 'semantic_score': 0.71, 'fingerprint': fp(mark='blue sticker')},
        ],
        'answers': {}, 'asked': [],
    }
    module = importlib.import_module('state.interactive_match')
    monkeypatch.setattr(module, 'st', ui)
    with pytest.raises(Rerun):
        module.interactive_match(SimpleNamespace(logout=lambda **kwargs: None))
    session = ui.session_state.match_session
    assert session['asked'] == ['mark']
    assert session['answers']['mark'] == 'red sticker'
    from matching.engine import rank_candidates
    assert rank_candidates(session['fingerprint'], session['candidates'], session['answers'])[0]['item_id'] == 1


def test_interactive_match_sends_request_only_on_explicit_click(monkeypatch):
    ui = install_fake_modules(monkeypatch)
    ui.clicked.add('发送匹配请求')
    fp = lambda **attrs: {'attributes': attrs, 'method': 'rules'}
    ui.session_state.match_session = {
        'user': 'owner', 'direction': 'lost', 'item_id': 100,
        'fingerprint': fp(category='umbrella'),
        'candidates': [
            {'item_id': 1, 'description': 'Found umbrella', 'semantic_score': 0.8,
             'fingerprint': fp(category='umbrella')},
        ],
        'answers': {}, 'asked': [],
    }
    module = importlib.import_module('state.interactive_match')
    monkeypatch.setattr(module, 'st', ui)
    calls = []
    monkeypatch.setattr(module, 'MatchRequests', lambda: SimpleNamespace(create=lambda *args: calls.append(args) or 'pending'))
    module.interactive_match(SimpleNamespace(logout=lambda **kwargs: None))
    assert calls == [('lost', 100, 1, 'owner')]


def test_profile_pending_approval_action(monkeypatch):
    ui = install_fake_modules(monkeypatch)
    ui.clicked.add('accept-100-200')
    module = importlib.import_module('state.profile')
    monkeypatch.setattr(module, 'st', ui)
    monkeypatch.setattr(FakeDatabase, 'get_user_lost_items', lambda self, u: [], raising=False)
    monkeypatch.setattr(FakeDatabase, 'get_user_found_items', lambda self, u: [], raising=False)
    responses = []
    monkeypatch.setattr(module, 'MatchRequests', lambda: SimpleNamespace(
        incoming=lambda user: [{'found_item_id': 100, 'lost_item_id': 200, 'requester': 'finder',
                                'found_desc': 'umbrella', 'lost_desc': 'lost umbrella'}],
        outgoing=lambda user: [], accepted=lambda user: [],
        respond=lambda *args: responses.append(args) or True,
    ))
    with pytest.raises(Rerun):
        module.profile(SimpleNamespace(logout=lambda **kwargs: None))
    assert responses == [('owner', 100, 200, True)]
