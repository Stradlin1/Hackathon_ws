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
        self.errors = []
        self.pill_value = None
        self.cache_data = lambda **kwargs: (lambda f: f)

    def form(self, *args, **kwargs):
        return nullcontext()

    def container(self, *args, **kwargs):
        return nullcontext()

    def tabs(self, *args, **kwargs):
        return [nullcontext() for _ in range(len(args[0]) if args else 1)]

    def popover(self, *args, **kwargs):
        return nullcontext()

    def dialog(self, *args, **kwargs):
        def decorator(function):
            return function
        return decorator

    def pills(self, label, options, **kwargs):
        return kwargs.get('default') if self.pill_value is None else self.pill_value

    def spinner(self, *args, **kwargs):
        return nullcontext()

    def expander(self, *args, **kwargs):
        return nullcontext()

    def columns(self, spec, **kwargs):
        count = spec if isinstance(spec, int) else len(spec)
        return [nullcontext() for _ in range(count)]

    def button(self, label, **kwargs):
        return (kwargs.get('key') or label) in self.clicked

    def form_submit_button(self, label, **kwargs):
        return self.submit and label in {'查找可能匹配', '提交并查找可能匹配', '更新匹配结果', '登录'}

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

    def error(self, message):
        self.errors.append(str(message))

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

    def get_item_status(self, id):
        return None

    def get_unmatched_lost_items(self):
        return []

    def get_unmatched_found_items(self):
        return []

    def get_items(self):
        return []

    def insert_user(self, user):
        return None

    def close(self):
        self.closed = True


def install_fake_modules(monkeypatch):
    ui = UI()
    monkeypatch.setitem(sys.modules, 'streamlit', ui)
    components = importlib.import_module('ui.components')
    monkeypatch.setattr(components, 'st', ui)
    fake_db = types.ModuleType('db_manager')
    fake_db.Database = FakeDatabase
    fake_db.Item = lambda *args: SimpleNamespace(id=args[0], image=args[1], emb=args[2], description=args[3], time=args[4], location=args[5])
    fake_db.User = lambda username, password='', email='': SimpleNamespace(
        username=username, password=password, email=email)
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
    monkeypatch.setattr(module, 'ReportMeta', lambda: SimpleNamespace(publish=lambda *args, **kwargs: None))
    monkeypatch.setattr(module, 'build_session', lambda **kwargs: {'user': 'owner', 'asked': [], 'answers': {}})
    with pytest.raises(Rerun):
        module.lost(SimpleNamespace(logout=lambda **kwargs: None))
    assert ui.session_state.state == 'interactive_match'
    assert ui.session_state.match_session['user'] == 'owner'


def test_lost_report_with_photo_uses_hybrid_vector(monkeypatch):
    ui = install_fake_modules(monkeypatch)
    ui.submit = True
    picture = Image.new('RGB', (25, 25), 'red')
    memory = io.BytesIO()
    picture.save(memory, 'PNG')
    ui.uploaded = SimpleNamespace(getvalue=lambda: memory.getvalue())
    module = importlib.import_module('state.lost')
    monkeypatch.setattr(module, 'st', ui)
    monkeypatch.setattr(module, 'encode_text', lambda text: np.array([1., 0.]))
    monkeypatch.setattr(module, 'encode_image', lambda img: np.array([0., 1.]))
    calls = []
    monkeypatch.setattr(module, 'combine_text_image',
                        lambda text, image: calls.append((text, image)) or np.array([0.7, 0.7]))
    monkeypatch.setattr(module, 'fingerprint_from_text',
                        lambda text: {'attributes': {'color': 'black'}, 'method': 'rules'})
    monkeypatch.setattr(module, 'FingerprintStore', lambda: SimpleNamespace(put=lambda *args: None))
    monkeypatch.setattr(module, 'ReportMeta', lambda: SimpleNamespace(publish=lambda *args, **kwargs: None))

    class FakeHashes:
        def find_near(self, image):
            return []

        def put(self, item_id, image):
            pass

    monkeypatch.setattr(module, 'ImageHashes', FakeHashes)
    monkeypatch.setattr(module, 'build_session',
                        lambda **kwargs: {'user': 'owner', 'asked': [], 'answers': {}})
    with pytest.raises(Rerun):
        module.lost(SimpleNamespace(logout=lambda **kwargs: None))
    assert calls
    assert calls[0][0].tolist() == [1.0, 0.0]
    assert calls[0][1].tolist() == [0.0, 1.0]
    assert FakeDatabase.inserted[-1].image is not None


def test_found_report_page_generates_session(monkeypatch):
    ui = install_fake_modules(monkeypatch)
    ui.submit = True
    picture = Image.new('RGB', (25, 25), 'red')
    memory = io.BytesIO()
    picture.save(memory, 'PNG')
    ui.uploaded = SimpleNamespace(getvalue=lambda: memory.getvalue())
    module = importlib.import_module('state.found')
    monkeypatch.setattr(module, 'st', ui)
    monkeypatch.setattr(module, 'notify_for_found_item', lambda *args, **kwargs: 0)
    monkeypatch.setattr(module, 'ReportMeta', lambda: SimpleNamespace(publish=lambda *args, **kwargs: None))

    class FakeHashes:
        def find_near(self, image):
            return []

        def put(self, item_id, image):
            pass

    monkeypatch.setattr(module, 'ImageHashes', FakeHashes)
    monkeypatch.setattr(module, '_cached_analysis', lambda data: {
        'description': 'a black umbrella', 'visible_text': '',
        'english': 'a black umbrella', 'source': 'blip'})
    monkeypatch.setattr(module, 'encode_image', lambda img: np.array([1., 0.]))
    monkeypatch.setattr(module, 'fingerprint_from_text',
                        lambda text, caption, caption_raw='', **kwargs: {'attributes': {'color': 'black'}, 'method': 'rules'})
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
    monkeypatch.setattr(module, 'MatchRequests', lambda: SimpleNamespace(
        state=lambda *args: {'status': None, 'cooldown': 0, 'can_request': True},
        create=lambda *args: 'pending'))

    class FakeMeta:
        def get(self, item_id):
            return None

    monkeypatch.setattr(module, 'ReportMeta', FakeMeta)
    merged = []

    class FakeStore:
        def merge(self, item_id, values):
            merged.append((item_id, values))
            return {'attributes': {'mark': 'red sticker'}, 'method': 'rules'}

    monkeypatch.setattr(module, 'FingerprintStore', FakeStore)
    with pytest.raises(Rerun):
        module.interactive_match(SimpleNamespace(logout=lambda **kwargs: None))
    session = ui.session_state.match_session
    assert session['asked'] == ['mark']
    assert session['answers']['mark'] == 'red sticker'
    assert merged == [(100, {'mark': 'red sticker'})]
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
    monkeypatch.setattr(module, 'MatchRequests', lambda: SimpleNamespace(
        state=lambda *args: {'status': None, 'cooldown': 0, 'can_request': True},
        create=lambda *args: calls.append(args) or 'pending'))

    class FakeMeta:
        def get(self, item_id):
            return None

    monkeypatch.setattr(module, 'ReportMeta', FakeMeta)
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


def test_login_authenticates_and_defers_cookie_write(monkeypatch):
    ui = install_fake_modules(monkeypatch)
    ui.submit = True
    ui.text_input = lambda label, **kwargs: 'alice' if '用户名' in label else 'demo-pass-alice'
    module = importlib.import_module('state.login')
    monkeypatch.setattr(module, 'st', ui)
    authenticator = SimpleNamespace(
        authentication_controller=SimpleNamespace(login=lambda username, password: True)
    )
    config = {'credentials': {'usernames': {'alice': {'email': 'alice@example.com', 'name': 'Alice'}}}}
    with pytest.raises(Rerun):
        module.login(authenticator, config)
    assert ui.session_state.state == 'lost_or_found'
    assert ui.session_state.auth_cookie_pending is True
    assert ui.session_state.user.email == 'alice@example.com'


def test_login_rejects_bad_credentials(monkeypatch):
    ui = install_fake_modules(monkeypatch)
    ui.submit = True
    ui.text_input = lambda label, **kwargs: 'alice' if '用户名' in label else 'wrong-password'
    module = importlib.import_module('state.login')
    monkeypatch.setattr(module, 'st', ui)
    authenticator = SimpleNamespace(
        authentication_controller=SimpleNamespace(login=lambda username, password: False)
    )
    config = {'credentials': {'usernames': {'alice': {'email': 'alice@example.com'}}}}
    module.login(authenticator, config)
    assert '用户名或密码错误' in ui.errors
    assert ui.session_state.state == 'login'


def test_home_page_renders_without_data(monkeypatch):
    ui = install_fake_modules(monkeypatch)
    module = importlib.import_module('state.lost_or_found')
    monkeypatch.setattr(module, 'st', ui)
    monkeypatch.setattr(module, 'Database', FakeDatabase)
    monkeypatch.setattr(FakeDatabase, 'get_user_lost_items', lambda self, u: [], raising=False)
    monkeypatch.setattr(FakeDatabase, 'get_user_found_items', lambda self, u: [], raising=False)
    monkeypatch.setattr(module, 'MatchRequests', lambda: SimpleNamespace(incoming=lambda user: []))
    module.lost_or_found(SimpleNamespace(logout=lambda **kwargs: None))
    assert ui.errors == []


def test_browse_page_renders_without_items(monkeypatch):
    ui = install_fake_modules(monkeypatch)
    module = importlib.import_module('state.browse')
    monkeypatch.setattr(module, 'st', ui)
    monkeypatch.setattr(module, 'FingerprintStore', lambda: SimpleNamespace(get=lambda item_id: None))

    class FakeMeta:
        def get(self, item_id):
            return None

    monkeypatch.setattr(module, 'ReportMeta', FakeMeta)
    monkeypatch.setattr(FakeDatabase, 'get_unmatched_found_items', lambda self: [], raising=False)
    module.browse(SimpleNamespace(logout=lambda **kwargs: None))
    assert ui.errors == []


def test_browse_page_renders_a_card(monkeypatch):
    ui = install_fake_modules(monkeypatch)
    ui.text_input = lambda label, **kwargs: ''
    module = importlib.import_module('state.browse')
    monkeypatch.setattr(module, 'st', ui)
    item = SimpleNamespace(id=1, description='黑色雨伞', image=None, time=1, location='图书馆')
    monkeypatch.setattr(FakeDatabase, 'get_unmatched_found_items', lambda self: [item], raising=False)

    class Store:
        def get(self, item_id):
            return {'attributes': {'category': 'umbrella', 'color': 'black'}}

    class FakeMeta:
        def get(self, item_id):
            return None

    monkeypatch.setattr(module, 'FingerprintStore', Store)
    monkeypatch.setattr(module, 'ReportMeta', FakeMeta)
    module.browse(SimpleNamespace(logout=lambda **kwargs: None))
    assert ui.errors == []


def test_lost_report_subscribes_when_requested(monkeypatch):
    ui = install_fake_modules(monkeypatch)
    ui.submit = True
    ui.checkbox = lambda *args, **kwargs: True
    module = importlib.import_module('state.lost')
    monkeypatch.setattr(module, 'st', ui)
    monkeypatch.setattr(module, 'encode_text', lambda text: np.array([1., 0.]))
    monkeypatch.setattr(module, 'fingerprint_from_text',
                        lambda text: {'attributes': {'color': 'black'}, 'method': 'rules'})
    monkeypatch.setattr(module, 'FingerprintStore', lambda: SimpleNamespace(put=lambda *args: None))
    monkeypatch.setattr(module, 'ReportMeta', lambda: SimpleNamespace(publish=lambda *args, **kwargs: None))
    monkeypatch.setattr(module, 'build_session',
                        lambda **kwargs: {'user': 'owner', 'asked': [], 'answers': {}})
    subscribed = []

    class FakeNotifications:
        def subscribe_item(self, username, item_id):
            subscribed.append((username, item_id))

    monkeypatch.setattr(module, 'Notifications', FakeNotifications)
    with pytest.raises(Rerun):
        module.lost(SimpleNamespace(logout=lambda **kwargs: None))
    assert subscribed and subscribed[0][0] == 'owner'


def test_notifications_page_renders_without_items(monkeypatch):
    ui = install_fake_modules(monkeypatch)
    module = importlib.import_module('state.notifications')
    monkeypatch.setattr(module, 'st', ui)

    class FakeMeta:
        def get(self, item_id):
            return None

    class FakeNotifications:
        def unread_count(self, username):
            return 0

        def list(self, username, limit=100):
            return []

        def mark_all_read(self, username):
            pass

    monkeypatch.setattr(module, 'Notifications', FakeNotifications)
    monkeypatch.setattr(module, 'ReportMeta', FakeMeta)
    module.notifications(SimpleNamespace(logout=lambda **kwargs: None))
    assert ui.errors == []


def test_report_page_switches_direction(monkeypatch):
    ui = install_fake_modules(monkeypatch)
    module = importlib.import_module('state.report')
    monkeypatch.setattr(module, 'st', ui)
    calls = []
    monkeypatch.setattr(module, 'lost',
                        lambda auth, embedded=False: calls.append(('lost', embedded)))
    monkeypatch.setattr(module, 'found',
                        lambda auth, embedded=False: calls.append(('found', embedded)))
    ui.pills = lambda *args, **kwargs: '我捡到东西'
    module.report(SimpleNamespace(logout=lambda **kwargs: None))
    assert calls == [('found', True)]


def test_status_dialog_writes_a_completion_state(monkeypatch):
    ui = install_fake_modules(monkeypatch)
    module = importlib.import_module('state.profile')
    monkeypatch.setattr(module, 'st', ui)
    ui.radio = lambda *args, **kwargs: 'returned'
    ui.text_input = lambda *args, **kwargs: '已还给失主'
    ui.form_submit_button = lambda *args, **kwargs: True
    calls = []

    class FakeLifecycle:
        def get(self, item_id):
            return None

        def set_status(self, item_id, status, username, note):
            calls.append((item_id, status, username, note))

    monkeypatch.setattr(module, 'Lifecycle', FakeLifecycle)
    item = SimpleNamespace(id=9, description='黑色雨伞')
    with pytest.raises(Rerun):
        module._status_dialog(item, True)
    assert calls == [(9, 'returned', 'owner', '已还给失主')]
