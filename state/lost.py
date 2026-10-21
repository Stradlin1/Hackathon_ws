"""Lost-item report: generative fingerprint and cross-modal retrieval."""

from __future__ import annotations

import io
import json
import secrets
from datetime import datetime, timedelta

import streamlit as st
from PIL import Image, UnidentifiedImageError

from db_manager import Database, Item
from matching.content_hash import ImageHashes, find_similar_text
from matching.fingerprint import fingerprint_from_text
from matching.models import combine_text_image, clean_image, encode_image, encode_text
from matching.notifications import Notifications
from matching.report_meta import ReportMeta
from matching.storage import FingerprintStore
from matching.workflow import build_session
from ui.components import card, page_header, topbar

Image.MAX_IMAGE_PIXELS = 20_000_000


def lost(authenticator, *, embedded: bool = False):
    if not embedded:
        topbar('lost', authenticator)
        page_header('clipboard', '登记失物', '写清能区分它的细节，AI 会先检索候选，再逐条追问。',
                    step='第 1 步 / 共 2 步')

    form_col, side_col = st.columns([1.6, 1], gap='large')
    with form_col:
        uploaded = st.file_uploader('上传物品照片（可选）', type=['png', 'jpg', 'jpeg'])
        picture = None
        if uploaded is not None:
            image_bytes = uploaded.getvalue()
            if len(image_bytes) > 8 * 1024 * 1024:
                st.error('请选择小于 8 MB 的图片；本次将只使用文字描述。')
            else:
                try:
                    picture = clean_image(Image.open(io.BytesIO(image_bytes)))
                except (OSError, UnidentifiedImageError, ValueError,
                        Image.DecompressionBombError):
                    st.error('无法打开这种图片格式；本次将只使用文字描述。')
                else:
                    with card('lost-preview'):
                        st.image(picture, caption='物品照片（会一起用于匹配）', width=350)
                    try:
                        near = ImageHashes().find_near(picture)
                    except Exception:
                        near = []
                    if near:
                        ids = '、'.join(f"#{hit['item_id']}" for hit in near[:3])
                        st.warning(f"这张照片和已有帖子 {ids} 的图片高度相似；"
                                   "如果只是同一物品请忽略，照抄会在发布时间/内容指纹上留下记录。")

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
            notify = st.checkbox('有新拾获时通知我', value=True,
                                 help='只发站内通知，不会发送邮件；可以随时在「我的记录」里关闭。')
            public = st.checkbox('允许在近期动态中公开展示', value=True,
                                 help='关闭后只参与匹配，不出现在公开列表；不会展示联系方式。')
            submitted = st.form_submit_button('查找可能匹配', type='primary', use_container_width=True)

    with side_col:
        with card('tips'):
            st.markdown('### 怎么写更容易找到')
            st.markdown(
                '- 颜色、材质、品牌\n'
                '- 独特标记：贴纸、划痕、刻字\n'
                '- 大致尺寸，或者平时装什么\n'
                '- 有照片就上传：会同时用文字和照片匹配'
            )
        with card('privacy'):
            st.markdown('### 隐私')
            st.caption('描述、照片与上面选的属性只保存在本机 items.db；照片入库前会去掉 EXIF；'
                       '联系方式要等对方确认。')

    if not submitted:
        return
    if not description.strip():
        st.error('请先描述丢失的物品。')
        return
    with st.spinner('正在生成指纹并搜索候选物品……'):
        try:
            text_vector = encode_text(description)
            if picture is not None:
                vector = combine_text_image(text_vector, encode_image(picture))
                item_image = picture
            else:
                vector = text_vector
                item_image = None
            fingerprint = fingerprint_from_text(description)
            stamp = int(datetime.combine(date, datetime.min.time()).timestamp())
            item = Item(secrets.randbits(62), item_image, vector, description.strip(), stamp, location)
            db = Database()
            try:
                try:
                    similar = find_similar_text(description, db.get_items())
                except Exception:
                    similar = None
                if similar:
                    st.session_state.duplicate_notice = (
                        f"描述与已有帖子 #{similar['item_id']} 高度相似（{similar['ratio']:.0%}）。"
                        "如果只是巧合请忽略；照抄会在发布时间/内容指纹上留下记录。")
                db.insert_item(item)
                if item_image is not None:
                    try:
                        ImageHashes().put(item.id, item_image)
                    except Exception:
                        pass
                owner = db.get_user(st.session_state.username)
                if owner is None:
                    raise ValueError('请重新登录后再登记物品。')
                db.insert_lost_item(item, owner)
                store = FingerprintStore()
                store.put(item.id, fingerprint)
                if notify:
                    try:
                        Notifications().subscribe_item(owner.username, item.id)
                    except Exception:  # alerts are optional; the report still succeeds
                        pass
                try:
                    ReportMeta().publish(item.id, public=True if public is None else bool(public))
                except Exception:  # visibility metadata is optional
                    pass
                session = build_session(direction='lost', item_id=item.id,
                                        query_embedding=vector, fingerprint=fingerprint,
                                        username=owner.username, db=db, store=store,
                                        query_time=stamp, query_location=location)
            finally:
                db.close()
        except (OSError, ValueError, RuntimeError, ImportError) as error:
            st.error(f'报告处理失败：{error}')
            return
    st.session_state.match_session = session
    st.session_state.state = 'interactive_match'
    st.rerun()
