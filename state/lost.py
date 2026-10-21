"""Lost-item report: generative fingerprint and cross-modal retrieval."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta

import streamlit as st

from db_manager import Database, Item
from matching.engine import UNSURE, propose_intake_questions
from matching.fingerprint import fingerprint_from_text
from matching.models import encode_text
from matching.storage import FingerprintStore
from matching.workflow import build_session, counterpart_fingerprints
from ui.components import card, page_header, topbar


def _found_pool() -> list[dict]:
    """Fingerprints of the unmatched found reports, used to pick intake questions."""
    try:
        db = Database()
        try:
            return counterpart_fingerprints('found', db, FingerprintStore())
        finally:
            db.close()
    except Exception:
        return []


def lost(authenticator):
    topbar('lost', authenticator)
    page_header('clipboard', '登记失物', '写清能区分它的细节，AI 会先检索候选，再逐条追问。',
                step='第 1 步 / 共 2 步')

    form_col, side_col = st.columns([1.6, 1], gap='large')
    with form_col:
        with st.form('lost_report'):
            description = st.text_area(
                '描述物品，包括任何独特标记',
                max_chars=1000,
                placeholder='例：黑色胶囊耳机，充电盒盖内侧有一张红色贴纸',
            )
            with open('rooms.json', encoding='utf-8') as file:
                locations = json.load(file)
            location = st.selectbox('最后出现的地点', locations)
            date = st.date_input('丢失日期', value='today', max_value=datetime.now().date(),
                                 min_value=datetime.now().date() - timedelta(days=30))
            questions = propose_intake_questions({}, _found_pool(), limit=2)
            answers = {}
            if questions:
                st.caption('再确认这几件事，拾获者匹配时就能看到。')
            for question in questions:
                options = [UNSURE] + [label for _, label in question['options']]
                answers[question['field']] = st.pills(
                    question['question'], options, default=UNSURE,
                    key=f"lost-intake-{question['field']}")
            submitted = st.form_submit_button('查找可能匹配', type='primary', use_container_width=True)

    with side_col:
        with card('tips'):
            st.markdown('### 怎么写更容易找到')
            st.markdown(
                '- 颜色、材质、品牌\n'
                '- 独特标记：贴纸、划痕、刻字\n'
                '- 大致尺寸，或者平时装什么'
            )
        with card('privacy'):
            st.markdown('### 隐私')
            st.caption('描述、照片与上面选的属性只保存在本机 items.db；联系方式要等对方确认。')

    if not submitted:
        return
    if not description.strip():
        st.error('请先描述丢失的物品。')
        return
    with st.spinner('正在生成指纹并搜索候选物品……'):
        try:
            vector = encode_text(description)
            fingerprint = fingerprint_from_text(description)
            attributes = dict(fingerprint.get('attributes', {}))
            confirmed = set(fingerprint.get('confirmed') or [])
            for question in questions:
                if question['field'] in attributes:
                    continue  # what the user just typed in the description wins
                chosen = answers.get(question['field'])
                for value, label in question['options']:
                    if chosen == label:
                        attributes[question['field']] = value
                        confirmed.add(question['field'])
                        break
            fingerprint['attributes'] = attributes
            if confirmed:
                fingerprint['confirmed'] = sorted(confirmed)
            stamp = int(datetime.combine(date, datetime.min.time()).timestamp())
            item = Item(secrets.randbits(62), None, vector, description.strip(), stamp, location)
            db = Database()
            try:
                db.insert_item(item)
                owner = db.get_user(st.session_state.username)
                if owner is None:
                    raise ValueError('请重新登录后再登记物品。')
                db.insert_lost_item(item, owner)
                store = FingerprintStore()
                store.put(item.id, fingerprint)
                session = build_session(direction='lost', item_id=item.id,
                                        query_embedding=vector, fingerprint=fingerprint,
                                        username=owner.username, db=db, store=store)
            finally:
                db.close()
        except (OSError, ValueError, RuntimeError, ImportError) as error:
            st.error(f'报告处理失败：{error}')
            return
    st.session_state.match_session = session
    st.session_state.state = 'interactive_match'
    st.rerun()
