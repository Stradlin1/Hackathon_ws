"""Found-item report: photo caption, generative fingerprint, CLIP retrieval.

The person holding the object is the cheapest source of high-value information,
so this page asks before retrieval instead of after: it shows what the model read
from the photo (one tap to reject a misreading) and asks up to two closed questions
picked from the pool of unmatched lost reports.
"""

from __future__ import annotations

import hashlib
import io
import json
import secrets
from datetime import datetime, timedelta

import streamlit as st
from PIL import Image, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = 20_000_000

from db_manager import Database, Item
from matching.engine import DISPLAY, UNSURE, propose_intake_questions
from matching.fingerprint import display_value, fingerprint_from_text
from matching.models import caption_image_pair, clean_image, encode_image
from matching.vlm import available as vlm_available
from matching.vlm import describe_image
from matching.storage import FingerprintStore
from matching.workflow import build_session, counterpart_fingerprints
from ui.components import card, page_header, topbar


@st.cache_data(show_spinner=False)
def _cached_analysis(image_bytes: bytes) -> dict:
    """Describe the photo once: DeepSeek vision when configured, local BLIP otherwise."""
    picture = clean_image(Image.open(io.BytesIO(image_bytes)))
    remote = describe_image(picture)
    if remote is not None:
        return {
            'description': remote['description'],
            'visible_text': remote['visible_text'],
            'english': '',
            'source': 'vlm',
        }
    english, chinese = caption_image_pair(picture)
    return {'description': chinese, 'visible_text': '', 'english': english, 'source': 'blip'}


def _lost_pool() -> list[dict]:
    """Fingerprints of the unmatched lost reports, used to pick intake questions."""
    try:
        db = Database()
        try:
            return counterpart_fingerprints('found', db, FingerprintStore())
        finally:
            db.close()
    except Exception:
        return []


def _attribute_label(field: str, value: str) -> str:
    return f'{DISPLAY.get(field, field)}：{display_value(field, value)}'


def found(authenticator):
    topbar('found', authenticator)
    page_header('camera', '登记拾获物品', '上传照片，AI 生成描述后由你确认，再开始检索失主。',
                step='第 1 步 / 共 2 步')

    form_col, side_col = st.columns([1.6, 1], gap='large')
    with side_col:
        with card('tips'):
            st.markdown('### 这条描述会怎么用')
            st.caption('照片和描述会被抽成指纹（颜色、材质、标记……），再和失主的文字描述做证据比对。')
        with card('privacy'):
            st.markdown('### 隐私')
            if vlm_available():
                st.caption('照片保存在本机 items.db；识别时会把照片发送到 DeepSeek API 一次，'
                           '检索与排序仍在本机完成。')
            else:
                st.caption('照片只保存在本机 items.db；未配置视觉模型时不联网，先做 EXIF 清洗再入库。')

    with form_col:
        uploaded = st.file_uploader('上传物品照片', type=['png', 'jpg', 'jpeg'])
        if uploaded is None:
            st.info('上传一张物品照片即可开始 AI 辅助登记。')
            return
        image_bytes = uploaded.getvalue()
        if len(image_bytes) > 8 * 1024 * 1024:
            st.error('请选择小于 8 MB 的图片。')
            return
        try:
            image = clean_image(Image.open(io.BytesIO(image_bytes)))
        except (OSError, UnidentifiedImageError, ValueError, Image.DecompressionBombError):
            st.error('无法打开这种图片格式。')
            return

        with card('preview'):
            st.image(image, caption='物品照片', width=350)

        try:
            with st.spinner('正在识别物品……'):
                analysis = _cached_analysis(image_bytes)
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            analysis = {'description': '', 'visible_text': '', 'english': '', 'source': 'none'}
            st.warning(f'自动识别不可用（{exc}）。请手动描述物品。')
        caption = analysis['description']
        caption_raw = analysis['english']
        visible_text = analysis['visible_text']
        if analysis['source'] == 'vlm':
            st.caption('由 DeepSeek 视觉模型识别，提交前请核对；断网或未配置 key 时自动改用本地 BLIP。')
        elif analysis['source'] == 'blip':
            st.caption('由本地 BLIP 生成，细节可能不准；配好 DeepSeek key 后会改用视觉模型识别。')
        default_description = caption
        if visible_text:
            default_description = f'{caption}\n可见文字：{visible_text}'

        digest = hashlib.sha1(image_bytes).hexdigest()[:12]
        preview = fingerprint_from_text('', caption=caption, caption_raw=caption_raw, generate=False)
        preview_attrs = preview.get('attributes', {})
        dropped: set[str] = set()
        if preview_attrs:
            labels = {_attribute_label(field, value): field for field, value in preview_attrs.items()}
            with card('reading'):
                st.markdown('### 照片里读到的属性')
                st.caption('误读的点一下去掉；想改值，直接在下面的描述里写清楚。')
                kept = st.pills('照片里读到的属性', list(labels), selection_mode='multi',
                                default=list(labels), key=f'attrs-{digest}',
                                label_visibility='collapsed')
                dropped = set(labels) - set(kept or [])

        known = {'attributes': {key: value for key, value in preview_attrs.items()
                                if key not in dropped}}
        questions = propose_intake_questions(known, _lost_pool(), limit=2)

        with st.form('found_report'):
            description = st.text_area('物品描述（可以修改自动生成的描述）',
                                       value=default_description, max_chars=1000,
                                       placeholder='例：白色无线鼠标，底部有一道浅划痕')
            with open('rooms.json', encoding='utf-8') as file:
                locations = json.load(file)
            location = st.selectbox('在哪里捡到的？', locations)
            date = st.date_input('拾获日期', value='today', max_value=datetime.now().date(),
                                 min_value=datetime.now().date() - timedelta(days=30))
            answers = {}
            if questions:
                st.caption(f'再确认这 {len(questions)} 件事，能直接减少候选。')
            for question in questions:
                options = [UNSURE] + [label for _, label in question['options']]
                answers[question['field']] = st.pills(
                    question['question'], options, default=UNSURE,
                    key=f"intake-{digest}-{question['field']}")
            submitted = st.form_submit_button('提交并查找可能匹配', type='primary',
                                              use_container_width=True)

    if not submitted:
        return
    if not description.strip():
        st.error('请填写物品描述。')
        return
    with st.spinner('正在生成指纹并搜索候选物品……'):
        try:
            vector = encode_image(image)
            fingerprint = fingerprint_from_text(description, caption=caption,
                                                caption_raw=caption_raw)
            attributes = dict(fingerprint.get('attributes', {}))
            for field in dropped:
                attributes.pop(field, None)
            for question in questions:
                chosen = answers.get(question['field'])
                for value, label in question['options']:
                    if chosen == label:
                        attributes[question['field']] = value
                        break
            fingerprint['attributes'] = attributes
            stamp = int(datetime.combine(date, datetime.min.time()).timestamp())
            item = Item(secrets.randbits(62), image, vector, description.strip(), stamp, location)
            db = Database()
            try:
                db.insert_item(item)
                owner = db.get_user(st.session_state.username)
                if owner is None:
                    raise ValueError('请重新登录后再登记物品。')
                db.insert_found_item(item, owner)
                store = FingerprintStore()
                store.put(item.id, fingerprint)
                session = build_session(direction='found', item_id=item.id,
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
