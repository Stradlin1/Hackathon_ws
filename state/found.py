"""Found-item report: image caption, generative fingerprint, CLIP retrieval."""

from __future__ import annotations

import io
import json
import secrets
from datetime import datetime, timedelta

import streamlit as st
from PIL import Image, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = 20_000_000

from db_manager import Database, Item
from matching.fingerprint import fingerprint_from_text
from matching.models import caption_image, clean_image, encode_image
from matching.storage import FingerprintStore
from matching.workflow import build_session
from ui.components import card, page_header, topbar


@st.cache_data(show_spinner=False)
def _cached_caption(image_bytes: bytes) -> str:
    picture = clean_image(Image.open(io.BytesIO(image_bytes)))
    return caption_image(picture)


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
            st.caption('照片只保存在本机 items.db；先做 EXIF 清洗，再入库。')

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
            with st.spinner('正在生成图片描述……'):
                caption = _cached_caption(image_bytes)
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            caption = ''
            st.warning(f'自动图片描述不可用（{exc}）。请手动描述物品。')

        with st.form('found_report'):
            description = st.text_area('物品描述（可以修改自动生成的描述）',
                                       value=caption, max_chars=1000,
                                       placeholder='例：白色无线鼠标，底部有一道浅划痕')
            with open('rooms.json', encoding='utf-8') as file:
                locations = json.load(file)
            location = st.selectbox('在哪里捡到的？', locations)
            date = st.date_input('拾获日期', value='today', max_value=datetime.now().date(),
                                 min_value=datetime.now().date() - timedelta(days=30))
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
            fingerprint = fingerprint_from_text(description, caption=caption)
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
