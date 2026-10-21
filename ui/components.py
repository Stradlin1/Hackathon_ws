"""Presentational building blocks shared by every page.

Every helper here only draws. Business rules (ranking, ownership, privacy) stay in
the page modules and matching package, so restyling can never change a decision.

Rule: anything that comes from the database or a form (descriptions, locations,
emails, usernames) goes through esc() before it is put into HTML. The components
render with unsafe_allow_html=True, so unescaped text would be an injection point.
"""

from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

from ui.icons import icon

ASSETS = Path(__file__).resolve().parent.parent / 'static'
LOGO = ASSETS / 'logo_rounded.png'

NAV = (
    ('lost_or_found', '首页'),
    ('lost', '登记失物'),
    ('found', '登记拾获'),
    ('profile', '我的记录'),
)

STATUS_TONE = {'pending': 'warn', 'accepted': 'ok', 'rejected': 'danger'}
STATUS_TEXT = {'pending': '待确认', 'accepted': '已接受', 'rejected': '已拒绝'}


def esc(value) -> str:
    """Escape text that will be embedded in an HTML fragment."""
    return html.escape('' if value is None else str(value), quote=True)


def _go(state: str) -> None:
    st.session_state.state = state


def topbar(current: str, authenticator) -> None:
    """Brand, primary navigation and the only logout entry point."""
    with st.container(key='topbar'):
        cols = st.columns([2.7, 1, 1, 1, 1, 1.15], gap='small', vertical_alignment='center')
        with cols[0]:
            mark, word = st.columns([0.55, 2.6], gap='small', vertical_alignment='center')
            with mark:
                st.image(str(LOGO), width=30)
            with word:
                st.markdown('<div class="brand-word">404NotFound</div>', unsafe_allow_html=True)
        for col, (state, label) in zip(cols[1:5], NAV):
            with col:
                st.button(
                    label,
                    key=f'nav-{state}',
                    use_container_width=True,
                    type='primary' if state == current else 'secondary',
                    on_click=_go,
                    args=(state,),
                )
        with cols[5]:
            authenticator.logout(button_name='退出登录', location='main')


def page_header(icon_name: str, title: str, subtitle: str = '', step: str = '') -> None:
    step_html = f'<span class="page-head-step">{esc(step)}</span>' if step else ''
    subtitle_html = f'<div class="page-head-sub">{esc(subtitle)}</div>' if subtitle else ''
    st.markdown(
        f'<div class="page-head">'
        f'<div class="page-head-icon">{icon(icon_name, 22)}</div>'
        f'<div><div class="page-head-title">{esc(title)}{step_html}</div>{subtitle_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def card(key: str):
    """A bordered container that the stylesheet renders as a card."""
    return st.container(border=True, key=f'card-{key}')


def pill(text: str, tone: str = 'neutral') -> str:
    """Return an inline chip string; use inside a markdown fragment."""
    cls = 'pill' if tone == 'neutral' else f'pill pill-{tone}'
    return f'<span class="{cls}">{esc(text)}</span>'


def pills(text: str) -> None:
    st.markdown(text, unsafe_allow_html=True)


def pills_html(tone: str, title: str, detail: str) -> str:
    """Eyebrow chip + card title + one-line explanation as one HTML block."""
    label = '失物' if tone == 'lost' else '拾获'
    return (
        f'<div>{pill(label, tone)}</div>'
        f'<div class="card-title">{esc(title)}</div>'
        f'<div class="card-copy">{esc(detail)}</div>'
    )


def status_badge(status: str) -> str:
    return pill(STATUS_TEXT.get(status, status), STATUS_TONE.get(status, 'neutral'))


def stat_row(items) -> None:
    """items: iterable of (value, label, hint)."""
    cells = ''.join(
        f'<div class="stat"><div class="stat-value">{esc(value)}</div>'
        f'<div class="stat-label">{esc(label)}</div>'
        f'<div class="stat-hint">{esc(hint)}</div></div>'
        for value, label, hint in items
    )
    st.markdown(f'<div class="stat-grid">{cells}</div>', unsafe_allow_html=True)


def empty(icon_name: str, title: str, hint: str = '') -> None:
    hint_html = f'<div class="empty-hint">{esc(hint)}</div>' if hint else ''
    st.markdown(
        f'<div class="empty"><div class="empty-icon">{icon(icon_name, 26)}</div>'
        f'<div class="empty-title">{esc(title)}</div>{hint_html}</div>',
        unsafe_allow_html=True,
    )


def auth_point(icon_name: str, title: str, detail: str) -> None:
    st.markdown(
        f'<div class="auth-point"><div class="auth-point-icon">{icon(icon_name, 15)}</div>'
        f'<div class="auth-point-text">{esc(title)} <span>{esc(detail)}</span></div></div>',
        unsafe_allow_html=True,
    )
