"""Interactive clarification and dynamic reranking page."""

from __future__ import annotations

import streamlit as st

from db_manager import Database
from matching.engine import DISPLAY, MAX_QUESTIONS, QUESTIONS, add_answer, choose_question, rank_candidates
from matching.fingerprint import display_value
from matching.requests import MatchRequests

METHOD_DISPLAY = {
    'generative_verified': '生成式已验证',
    'vision_caption_rules': '图注 + 规则',
    'rules': '规则抽取',
}
STATUS_DISPLAY = {'pending': '待确认', 'accepted': '已接受', 'rejected': '已拒绝'}


def interactive_match(authenticator):
    authenticator.logout(button_name='退出登录', location='sidebar')
    session = st.session_state.get('match_session')
    if not session or session.get('user') != st.session_state.get('username'):
        st.warning('没有正在进行的匹配会话，请先登记物品。')
        st.button('返回主菜单', on_click=lambda: st.session_state.update(state='lost_or_found'))
        return

    st.title('AI 辅助物品匹配')
    st.caption('生成式指纹 + 信息增益追问 + 动态排序')
    fp = session['fingerprint']
    attrs = fp.get('attributes', {})
    st.subheader('生成的物品指纹')
    if attrs:
        st.write(' / '.join(f'{DISPLAY.get(k, k)}：{display_value(k, v)}' for k, v in attrs.items()))
    else:
        st.info('没有提取到可区分的属性，仍可查看 CLIP 候选。')
    method = METHOD_DISPLAY.get(fp.get('method'), '未知')
    st.caption(f'抽取方式：{method}。只保留有原文证据的特征。')

    ranked = rank_candidates(fp, session['candidates'], session['answers'])
    if not ranked:
        st.info('对面暂时没有可检索的报告。')
        if st.button('查看我的记录'):
            st.session_state.state = 'profile'
            st.rerun()
        return

    st.subheader('候选动态排序')
    st.caption('分数是排序指标，不是所有权概率。')
    db = Database()
    try:
        for index, result in enumerate(ranked[:5], 1):
            with st.expander(f'#{index}  候选 {result["item_id"]}  |  分数 {result["score"]:.3f}', expanded=index == 1):
                item = db.get_item(result['item_id'])
                if item.image is not None:
                    st.image(item.image, width=260)
                st.write(item.description)
                st.caption(f'CLIP 相似度：{result["semantic_score"]:.3f}')
                if result['matches']:
                    st.success('一致特征：' + ', '.join(result['matches']))
                if result['conflicts']:
                    st.warning('矛盾特征：' + ', '.join(result['conflicts']))
    finally:
        db.close()

    question_field = choose_question(fp, ranked, session['asked'])
    if question_field is not None and len(session['asked']) < MAX_QUESTIONS:
        st.subheader(f'追问 {len(session["asked"]) + 1}/{MAX_QUESTIONS}')
        st.write(QUESTIONS[question_field])
        with st.form(f'clarification_{len(session["asked"])}'):
            answer = st.text_input('你的回答', max_chars=100)
            answered = st.form_submit_button('更新匹配结果')
            skipped = st.form_submit_button('不知道 / 跳过')
        if answered or skipped:
            normalized = add_answer(session, question_field, '' if skipped else answer)
            if answered and normalized is None:
                st.warning('这个回答无法识别，已按跳过处理。')
            st.session_state.match_session = session
            st.rerun()
    else:
        st.info('没有更多可区分的追问了，请查看排序结果。')

    if session['asked']:
        answers_text = '、'.join(
            f'{DISPLAY.get(key, key)}：{display_value(key, value)}' for key, value in session['answers'].items()
        )
        answers_text = answers_text or '无'
        st.caption(f'已提问 {len(session["asked"])} 个。回答：{answers_text}')

    st.subheader('请求确认')
    st.warning('相似度结果不能证明物品归属。需要对方接受后才会显示联系方式。')
    selections = {f'#{i}：{r["description"][:55] or "物品"}（分数 {r["score"]:.3f}）': r['item_id']
                  for i, r in enumerate(ranked[:5], 1)}
    label = st.selectbox('选择要联系的候选', list(selections))
    if st.button('发送匹配请求'):
        try:
            status = MatchRequests().create(session['direction'], session['item_id'], selections[label], session['user'])
        except (OSError, ValueError, PermissionError) as error:
            st.error(f'无法创建匹配请求：{error}')
        else:
            st.success('请求状态：' + STATUS_DISPLAY.get(status, status) + '。双方确认后才会显示联系方式。')

    if st.button('前往我的记录'):
        st.session_state.state = 'profile'
        st.rerun()
