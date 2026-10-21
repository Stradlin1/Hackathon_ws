"""Item history and two-party approval of proposed matches."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from db_manager import Database
from matching.engine import DISPLAY
from matching.content_hash import ImageHashes, publication_text, watermark
from matching.fingerprint import FIELDS, display_value, normalize_answer
from matching.lifecycle import Lifecycle, status_label
from matching.notifications import Notifications
from matching.report_meta import ReportMeta
from matching.requests import MatchRequests, cooldown_text
from matching.storage import FingerprintStore
from ui.components import card, empty, esc, page_header, pill, pills, stat_row, status_badge, topbar

STATUS_DISPLAY = {'pending': '待确认', 'accepted': '已接受', 'rejected': '已拒绝'}


def _date_text(item) -> str:
    return datetime.fromtimestamp(item.time).strftime('%Y-%m-%d') if item.time else '未填写'


def _timestamp_text(value) -> str:
    if not value:
        return '未填写'
    try:
        return datetime.fromtimestamp(value).strftime('%Y-%m-%d')
    except (OSError, OverflowError, ValueError):
        return '未填写'


@st.dialog('补全物品信息')
def _enrich_dialog(item_id: int) -> None:
    """Let the owner add or correct attributes; saved values are shared with matches."""
    store = FingerprintStore()
    fingerprint = store.get(item_id) or {}
    attributes = fingerprint.get('attributes') or {}
    values = {}
    with st.form(f'enrich-{item_id}'):
        st.caption('留空表示不确定；写「无标记」表示没有特殊标记。保存后立刻参与匹配，对方也能看到。')
        for field in FIELDS:
            values[field] = st.text_input(
                DISPLAY.get(field, field),
                value=display_value(field, attributes.get(field, '')),
                key=f'enrich-input-{item_id}-{field}',
            )
        submitted = st.form_submit_button('保存', type='primary', use_container_width=True)
    if not submitted:
        return
    updates = {}
    unknown = []
    for field, raw in values.items():
        text = (raw or '').strip()
        if not text:
            continue
        normalized = normalize_answer(field, text)
        if normalized:
            updates[field] = normalized
        else:
            unknown.append(DISPLAY.get(field, field))
    if updates:
        store.merge(item_id, updates)
    if unknown:
        st.warning('这些没看懂，已跳过：' + '、'.join(unknown))
    else:
        st.rerun()


def _remove_report(item_id: int, username: str) -> None:
    """Delete a report the user owns, together with its requests and fingerprint."""
    db = Database()
    try:
        owns = (db.lost_item_exists(item_id, username)
                or db.found_item_exists(item_id, username))
        if not owns:
            raise PermissionError('只能撤销自己登记的物品。')
        db.remove_lost_item(item_id)
        db.remove_found_item(item_id)
        db.remove_item(item_id)
    finally:
        db.close()
    MatchRequests().cancel_for_item(item_id)
    FingerprintStore().delete(item_id)
    try:
        Notifications().delete_for_item(item_id)
    except Exception:  # cleanup is best-effort; the report is already gone
        pass
    try:
        ImageHashes().delete(item_id)
    except Exception:
        pass
    session = st.session_state.get('match_session')
    if isinstance(session, dict) and session.get('item_id') == item_id:
        st.session_state.pop('match_session', None)


@st.dialog('撤销登记')
def _withdraw_dialog(item) -> None:
    statuses = MatchRequests().statuses_for_item(item.id)
    if 'accepted' in statuses:
        st.warning('这条物品已经有双方确认的配对，不能撤销；留着记录或先和对方沟通。')
        return
    st.write(item.description)
    st.caption(f'地点：{item.location} | 日期：{_date_text(item)} | #{item.id}')
    if statuses:
        st.caption(f'撤销后会同时删除 {len(statuses)} 条相关配对请求。')
    st.caption('物品、指纹与相关请求会从本地数据库删除，无法恢复。')
    if st.button('确认撤销', key=f'confirm-withdraw-{item.id}', use_container_width=True):
        try:
            _remove_report(item.id, st.session_state.username)
        except (OSError, ValueError, PermissionError) as error:
            st.error(f'撤销失败：{error}')
        else:
            st.rerun()


@st.dialog('标记处理状态')
def _status_dialog(item, lost: bool) -> None:
    """Close a report without deleting it; it stays visible under 已处理."""
    lifecycle = Lifecycle()
    current = lifecycle.get(item.id)
    if current:
        st.info(f'当前状态：{status_label(current["status"], lost)}')
    options = {'returned': '已归还 / 已找回', 'archived': '归档（不表示归还）'}
    keys = list(options)
    index = keys.index(current['status']) if current and current['status'] in keys else 0
    with st.form(f'status-form-{item.id}'):
        choice = st.radio('处理结果', keys, index=index,
                          format_func=lambda key: options[key],
                          key=f'status-choice-{item.id}')
        note = st.text_input('备注（可选）', max_chars=80, key=f'status-note-{item.id}')
        st.caption('标记后物品会退出候选池、浏览页与通知匹配，但记录保留，可以恢复。')
        submitted = st.form_submit_button('确认', type='primary', use_container_width=True)
    if submitted:
        try:
            lifecycle.set_status(item.id, choice, st.session_state.username, note)
        except (OSError, ValueError) as error:
            st.error(f'保存失败：{error}')
        else:
            st.rerun()
    if current:
        if st.button('恢复为进行中', key=f'status-clear-{item.id}',
                     use_container_width=True):
            try:
                lifecycle.clear(item.id)
            except (OSError, ValueError) as error:
                st.error(f'恢复失败：{error}')
            else:
                st.rerun()


def _item_card(key, item, show_image=False, lost=False):
    with st.container(border=True, key=key):
        meta = ReportMeta().get(item.id)
        published_at = meta.get('published_at') if meta else None
        cols = st.columns([1, 3], gap='medium') if show_image and item.image is not None else None
        if cols is None:
            st.write(item.description)
            st.caption(f'地点：{item.location} | 日期：{_date_text(item)} | #{item.id}')
        else:
            with cols[0]:
                st.image(watermark(item.image, item.id, published_at), width=160)
            with cols[1]:
                st.write(item.description)
                st.caption(f'地点：{item.location} | 日期：{_date_text(item)} | #{item.id}')
        attributes = (FingerprintStore().get(item.id) or {}).get('attributes') or {}
        chips = ''.join(pill(f'{DISPLAY.get(field, field)}：{display_value(field, value)}')
                        for field, value in attributes.items())
        if chips:
            pills(chips)
        st.caption(publication_text(item.id, item.description or "", published_at))
        notified = False
        if lost:
            try:
                notified = Notifications().is_subscribed(st.session_state.username, item.id)
            except Exception:
                notified = False
        actions = (st.columns([2.2, 1, 1, 1], gap='small', vertical_alignment='center')
                   if lost else st.columns([3, 1, 1], gap='small', vertical_alignment='center'))
        with actions[0]:
            if st.button('补全信息', key=f'enrich-{item.id}', type='secondary',
                         use_container_width=True):
                _enrich_dialog(item.id)
        if lost:
            with actions[1]:
                if st.button('取消提醒' if notified else '提醒我', key=f'notify-{item.id}',
                             help='有新拾获物品时在站内通知你；已配对的失物不再提醒。',
                             use_container_width=True):
                    try:
                        Notifications().toggle_item(st.session_state.username, item.id)
                    except Exception as error:
                        st.error(f'提醒设置失败：{error}')
                    else:
                        st.rerun()
            with actions[2]:
                if st.button('处理', key=f'status-{item.id}',
                             help='标记已归还或归档；记录保留，可以恢复',
                             use_container_width=True):
                    _status_dialog(item, lost)
            with actions[3]:
                if st.button('撤销', key=f'withdraw-{item.id}', help='删除这条登记，无法恢复'):
                    _withdraw_dialog(item)
        else:
            with actions[1]:
                if st.button('处理', key=f'status-{item.id}',
                             help='标记已归还或归档；记录保留，可以恢复',
                             use_container_width=True):
                    _status_dialog(item, lost)
            with actions[2]:
                if st.button('撤销', key=f'withdraw-{item.id}', help='删除这条登记，无法恢复'):
                    _withdraw_dialog(item)


def _done_card(item, record, lost: bool):
    with st.container(border=True, key=f'done-{item.id}'):
        meta = ReportMeta().get(item.id)
        published_at = meta.get('published_at') if meta else None
        tone = 'ok' if record['status'] == 'returned' else 'neutral'
        st.markdown(pill(status_label(record['status'], lost), tone), unsafe_allow_html=True)
        if item.image is not None:
            st.image(watermark(item.image, item.id, published_at), width=140)
        st.write(item.description)
        st.caption(f'地点：{item.location} | 日期：{_date_text(item)} | #{item.id}')
        st.caption(publication_text(item.id, item.description or "", published_at))
        if record.get('note'):
            st.caption(f"备注：{record['note']}")
        st.caption(f"处理时间：{_timestamp_text(record.get('updated_at'))}")
        if st.button('恢复为进行中', key=f'restore-{item.id}', use_container_width=True):
            try:
                Lifecycle().clear(item.id)
            except (OSError, ValueError) as error:
                st.error(f'恢复失败：{error}')
            else:
                st.rerun()


def profile(authenticator):
    topbar('profile', authenticator)
    page_header('folder', '我的物品与请求', '你登记的东西、别人发来的请求，以及已经确认的匹配。')

    username = st.session_state.username
    db = Database()
    try:
        lost_items = db.get_user_lost_items(username)
        found_items = db.get_user_found_items(username)
    finally:
        db.close()

    lifecycle = Lifecycle() if (lost_items or found_items) else None

    def split(items):
        active, done = [], []
        for item in items:
            record = lifecycle.get(item.id) if lifecycle else None
            if record:
                done.append((item, record))
            else:
                active.append(item)
        return active, done

    lost_active, lost_done = split(lost_items)
    found_active, found_done = split(found_items)

    requests = MatchRequests()
    incoming = requests.incoming(username)

    stat_row([
        (len(lost_active), '我的失物', '进行中'),
        (len(found_active), '我的拾获', '进行中'),
        (len(incoming), '待我确认', '对方在等你'),
        (len(lost_done) + len(found_done), '已处理', '已归还/归档'),
    ])

    st.markdown('### 我的失物')
    if not lost_active:
        empty('clipboard', '没有进行中的失物', '已处理的物品在下面的「已处理的物品」里。')
    for item in lost_active:
        _item_card(f'profile-lost-{item.id}', item, show_image=True, lost=True)

    st.markdown('### 我的拾获')
    if not found_active:
        empty('camera', '没有进行中的拾获物品', '已处理的物品在下面的「已处理的物品」里。')
    for item in found_active:
        _item_card(f'profile-found-{item.id}', item, show_image=True)

    st.markdown('### 已处理的物品')
    if not lost_done and not found_done:
        empty('check', '还没有已处理的物品', '在物品卡片上点「处理」可以标记已归还或归档。')
    for item, record in lost_done:
        _done_card(item, record, lost=True)
    for item, record in found_done:
        _done_card(item, record, lost=False)

    st.markdown('### 等待你确认的请求')
    if not incoming:
        empty('inbox', '暂无待确认请求', '对方发起请求后会出现在这里。')
    else:
        st.caption(f'共 {len(incoming)} 个待确认请求；接受其中一个后，其余会自动关闭。')
    for req in incoming:
        found, lost = req['found_item_id'], req['lost_item_id']
        with st.container(border=True, key=f'req-{found}-{lost}'):
            st.write(f'拾获：{req["found_desc"]}')
            st.write(f'丢失：{req["lost_desc"]}')
            st.caption('接受之后，双方才会看到彼此的联系方式。')
            left, right = st.columns(2, gap='small')
            with left:
                if st.button('接受匹配', key=f'accept-{found}-{lost}', type='primary',
                             use_container_width=True):
                    if requests.respond(username, found, lost, True):
                        st.rerun()
                    else:
                        st.warning('这条请求已经不可接受（可能已配对或被取消）。')
            with right:
                if st.button('拒绝匹配', key=f'reject-{found}-{lost}', use_container_width=True):
                    if requests.respond(username, found, lost, False):
                        st.rerun()
                    else:
                        st.warning('这条请求已经处理过了。')

    st.markdown('### 我发出的请求')
    outgoing = requests.outgoing(username)
    if not outgoing:
        empty('inbox', '还没有发出请求', '在匹配结果里选中候选后发送。')
    lost_ids = {item.id for item in lost_items}
    found_ids = {item.id for item in found_items}
    for req in outgoing:
        found, lost = req['found_item_id'], req['lost_item_id']
        st.markdown(
            f'拾获 #{found} / 失物 #{lost}　' + status_badge(req['status']),
            unsafe_allow_html=True,
        )
        if req['status'] != 'rejected':
            continue
        db = Database()
        try:
            matched = bool(db.get_found_item_matches(found) or db.get_lost_item_matches(lost))
        finally:
            db.close()
        state = requests.state_pair(found, lost)
        if matched:
            st.caption('这条配对已经完成，不能重新发起。')
        elif state['can_request']:
            if lost in lost_ids:
                direction, query, candidate = 'lost', lost, found
            elif found in found_ids:
                direction, query, candidate = 'found', found, lost
            else:
                direction = None
            if direction is None:
                st.caption('对应物品已经撤销，不能重新发起。')
            elif st.button('重新发送匹配请求', key=f'retry-{found}-{lost}'):
                try:
                    requests.create(direction, query, candidate, username)
                except (OSError, ValueError, PermissionError) as error:
                    st.error(f'无法重新发起：{error}')
                else:
                    st.rerun()
        else:
            st.caption(f"冷却中：{cooldown_text(state['cooldown'])}后可重新发起。")

    st.markdown('### 已确认的匹配')
    accepted = requests.accepted(username)
    if not accepted:
        empty('handshake', '暂无双方确认的匹配', '双方都同意后，联系方式会出现在这里。')
    for req in accepted:
        with st.container(border=True, key=f'accepted-{req["found_item_id"]}-{req["lost_item_id"]}'):
            st.write(f'拾获 #{req["found_item_id"]} / 失物 #{req["lost_item_id"]}')
            st.markdown(
                f'<div class="pill pill-ok">联系方式</div> '
                f'<strong>{esc(req["contact_username"])}</strong> · {esc(req["contact_email"])}',
                unsafe_allow_html=True,
            )

    st.write('')
    if st.button('继续登记物品', type='primary', use_container_width=True):
        st.session_state.state = 'report'
        st.rerun()
