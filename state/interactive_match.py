"""Interactive clarification and dynamic reranking page."""

from __future__ import annotations

import streamlit as st

from db_manager import Database
from matching.engine import DISPLAY, MAX_QUESTIONS, QUESTIONS, add_answer, choose_question, rank_candidates
from matching.fingerprint import display_value
from matching.requests import MatchRequests
from matching.storage import FingerprintStore
from ui.components import card, page_header, pill, pills, topbar

METHOD_DISPLAY = {
    'generative_verified': '生成式已验证',
    'vision_caption_rules': '图注 + 规则',
    'rules': '规则抽取',
}
STATUS_DISPLAY = {'pending': '待确认', 'accepted': '已接受', 'rejected': '已拒绝'}


def _chips(values, tone):
    return ''.join(pill(value, tone) for value in values)


def interactive_match(authenticator):
    topbar('interactive_match', authenticator)
    session = st.session_state.get('match_session')
    if not session or session.get('user') != st.session_state.get('username'):
        page_header('search', 'AI 辅助物品匹配', '没有进行中的匹配会话')
        st.warning('没有正在进行的匹配会话，请先登记物品。')
        if st.button('返回主菜单'):
            st.session_state.state = 'lost_or_found'
            st.rerun()
        return

    page_header('search', 'AI 辅助物品匹配', '生成式指纹 + 信息增益追问 + 动态排序',
                step='第 2 步 / 共 2 步')

    fp = session['fingerprint']
    attrs = fp.get('attributes', {})
    with card('fingerprint'):
        st.markdown('### 物品指纹')
        if attrs:
            pills(_chips([f'{DISPLAY.get(k, k)}：{display_value(k, v)}' for k, v in attrs.items()],
                         'brand'))
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

    st.markdown('### 候选排序')
    st.caption('分数是排序指标，不是所有权概率。')
    st.caption('打分 = 0.72 × CLIP 相似度 + 0.28 × 证据；CLIP 文本↔照片的原始相似度常见区间只有 '
               '0.2–0.35，所以总分看起来不高是正常的。')
    db = Database()
    try:
        for index, result in enumerate(ranked[:5], 1):
            with st.container(border=True, key=f'cand-{index}'):
                st.markdown(
                    f'<div class="cand-head"><span class="cand-rank">#{index}</span>'
                    f'<span class="cand-score" title="0.72 × 语义 + 0.28 × 证据">'
                    f'{result["score"]:.3f}</span>'
                    f'<span class="cand-score-cap">排序指标 · CLIP {result["semantic_score"]:.3f}</span></div>',
                    unsafe_allow_html=True,
                )
                item = db.get_item(result['item_id'])
                body = st.columns([1, 2.4], gap='medium')
                with body[0]:
                    if item.image is not None:
                        st.image(item.image, width=220)
                with body[1]:
                    st.write(item.description)
                    attributes = (result.get('fingerprint') or {}).get('attributes') or {}
                    attr_chips = ''.join(
                        pill(f'{DISPLAY.get(key, key)}：{display_value(key, value)}', 'brand')
                        for key, value in list(attributes.items())[:6]
                    )
                    if attr_chips:
                        pills(attr_chips)
                    chips = _chips(result['matches'], 'found') + _chips(result['conflicts'], 'warn')
                    if chips:
                        pills(chips)
                st.progress(min(max(float(result['score']), 0.0), 1.0))
    finally:
        db.close()

    question_field = choose_question(fp, ranked, session['asked'])
    if question_field is not None and len(session['asked']) < MAX_QUESTIONS:
        with card('question'):
            st.markdown(f'### 追问 {len(session["asked"]) + 1} / {MAX_QUESTIONS}')
            st.write(QUESTIONS[question_field])
            st.caption('回答会并入这件物品的信息，对方匹配时能看到；只保存属性值，不保存原话。')
            with st.form(f'clarification_{len(session["asked"])}'):
                answer = st.text_input('你的回答', max_chars=100,
                                       placeholder='例：有，红色圆贴纸')
                left, right = st.columns(2, gap='small')
                with left:
                    answered = st.form_submit_button('更新匹配结果', type='primary',
                                                     use_container_width=True)
                with right:
                    skipped = st.form_submit_button('不知道 / 跳过', use_container_width=True)
            if answered or skipped:
                normalized = add_answer(session, question_field, '' if skipped else answer)
                if answered and normalized is None:
                    st.warning('这个回答无法识别，已按跳过处理。')
                if normalized is not None:
                    try:
                        session['fingerprint'] = FingerprintStore().merge(
                            session['item_id'], {question_field: normalized})
                    except Exception:
                        pass
                st.session_state.match_session = session
                st.rerun()
    else:
        st.info('没有更多可区分的追问了，请查看排序结果。')

    if session['asked']:
        answers_text = '、'.join(
            f'{DISPLAY.get(key, key)}：{display_value(key, value)}' for key, value in session['answers'].items()
        )
        st.caption(f'已提问 {len(session["asked"])} 个。回答：{answers_text or "无"}')

    with card('request'):
        st.markdown('### 请求确认')
        st.warning('相似度结果不能证明物品归属。需要对方接受后才会显示联系方式。')
        selections = {f'#{i}：{r["description"][:55] or "物品"}（分数 {r["score"]:.3f}）': r['item_id']
                      for i, r in enumerate(ranked[:5], 1)}
        label = st.selectbox('选择要联系的候选', list(selections))
        if st.button('发送匹配请求', type='primary', use_container_width=True):
            try:
                status = MatchRequests().create(session['direction'], session['item_id'],
                                                selections[label], session['user'])
            except (OSError, ValueError, PermissionError) as error:
                st.error(f'无法创建匹配请求：{error}')
            else:
                st.success('请求状态：' + STATUS_DISPLAY.get(status, status)
                           + '。双方确认后才会显示联系方式。')

    if st.button('前往我的记录', use_container_width=True):
        st.session_state.state = 'profile'
        st.rerun()
