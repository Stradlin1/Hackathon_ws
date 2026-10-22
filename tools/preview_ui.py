#!/usr/bin/env python3
"""Design preview: every component on one page, without models or a database.

This is a development tool, not part of the application. It imports only
streamlit and ui/*, so it can run in a throwaway venv while the project's model
dependencies are unavailable:

    python -m venv /tmp/ui-venv
    /tmp/ui-venv/bin/pip install "streamlit>=1.35,<2"
    ln -sfn ../static tools/static        # so app/static/fonts/ resolves
    /tmp/ui-venv/bin/streamlit run tools/preview_ui.py --server.port 8599

Screenshot it with any headless browser (1440x960 and 390x844) and compare with
.dsh/agents/ui.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

import ui.art as art  # noqa: E402
from ui.components import (card, empty, page_header, pill, pills_html,  # noqa: E402
                           stat_row, topbar)
from ui.theme import inject  # noqa: E402

st.set_page_config(page_title='界面预览', layout='wide')
inject()


class _FakeAuthenticator:
    """Stands in for streamlit-authenticator's logout button."""

    def logout(self, **kwargs):
        st.button(kwargs.get('button_name', '退出登录'), key='preview-logout')


topbar('lost_or_found', _FakeAuthenticator())
page_header('search', '界面预览 · 旧纸与铜版画',
            '顶栏、页头、卡片、表单、提示、照片框与空状态。', '01')

left, right = st.columns(2, gap='large')
with left:
    with card('lost'):
        st.markdown(pills_html('lost', '登记失物', '写下颜色、品牌、划痕或贴纸，越具体越容易匹配。',
                               art_name='card-lost'), unsafe_allow_html=True)
        st.button('开始登记失物', type='primary', use_container_width=True, key='p-lost')
with right:
    with card('found'):
        st.markdown(pills_html('found', '登记拾获', '上传一张照片，AI 会先生成描述，你可以随时修改。',
                               art_name='card-found'), unsafe_allow_html=True)
        st.button('开始登记拾获', type='primary', use_container_width=True, key='p-found')

stat_row([(3, '我的失物', '已登记'), (2, '我的拾获', '已登记'), (1, '待我确认', '对方在等你')])

with card('form'):
    st.markdown('### 筛选与表单控件')
    st.markdown(
        pill('失物', 'lost') + pill('拾获', 'found') + pill('属性：白色', 'brand')
        + pill('已接受', 'ok') + pill('待确认', 'warn') + pill('已拒绝', 'danger'),
        unsafe_allow_html=True,
    )
    st.text_input('关键词', placeholder='例如 充电宝')
    st.text_area('描述', placeholder='写下能区分它的细节')
    st.selectbox('方向', ['全部', '失物', '拾获'])
    st.date_input('日期')
    st.pills('模式', ['失物', '拾获'], default='失物')
    st.checkbox('允许在近期动态中公开展示', value=True)
    st.file_uploader('物品照片')
    st.button('主按钮', type='primary', key='p-primary')
    st.button('次按钮', key='p-secondary')
    st.button('文字按钮', type='tertiary', key='p-tertiary')
    st.success('账号注册成功，请登录。')
    st.warning('这张照片和已有的帖子很像。')
    st.info('排序指标只表示相似程度。')
    st.error('用户名或密码错误')

photo = ROOT / 'demo' / 'photos' / 'found-01.png'
if not photo.exists():
    photos = sorted((ROOT / 'demo' / 'photos').glob('*.png')) or sorted((ROOT / 'demo' / 'photos').glob('*.jpg'))
    photo = photos[0] if photos else None
if photo is not None:
    st.markdown('### 照片框（证据照片不调色）')
    st.image(str(photo), width=280)

st.markdown('### 空状态')
empty('search', '没有符合条件的记录', '换个关键词，或把时间范围放宽。')
empty('bell', '还没有通知', '有人捡到可能与你失物相关的物品时，会出现在这里。')
empty('clipboard', '没有进行中的失物', '已处理的物品在下面的「已处理的物品」里。')

st.markdown('### 提示条与进度')
st.progress(0.4)
st.markdown(art.figure('fleuron', caption='印刷花饰'), unsafe_allow_html=True)

st.markdown('### 登录页卷首图')
with st.container(key='auth-plate'):
    st.image(str(art.path('frontispiece') or ROOT / 'static' / 'logo_rounded.png'), width=360)
st.markdown('<div class="auth-kicker">失物招领 · 本地档案</div>'
            '<div class="auth-title">Picture is All You Need</div>', unsafe_allow_html=True)
