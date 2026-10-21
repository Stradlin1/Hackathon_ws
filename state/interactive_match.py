"""Interactive clarification and dynamic reranking page."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from db_manager import Database
from matching.content_hash import publication_text, watermark
from matching.engine import DISPLAY, MAX_QUESTIONS, QUESTIONS, add_answer, choose_question, rank_candidates
from matching.fingerprint import display_value
from matching.lifecycle import status_label
from matching.report_meta import ReportMeta
from matching.requests import MatchRequests, cooldown_text
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


def _date_text(value) -> str:
    if not value:
        return "未填写"
    try:
        return datetime.fromtimestamp(value).strftime("%Y-%m-%d")
    except (OSError, OverflowError, ValueError):
        return "未填写"


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

    db = Database()
    try:
        item_status = db.get_item_status(session['item_id'])
    finally:
        db.close()
    if item_status:
        closed = status_label(item_status, session.get('direction') == 'lost')
        page_header('search', 'AI 辅助物品匹配', f'这件物品已标记为{closed}')
        st.warning(f'这件物品已标记为{closed}，不再参与匹配；记录仍保留在「我的记录」里。')
        if st.button('前往我的记录', use_container_width=True):
            st.session_state.state = 'profile'
            st.rerun()
        return

    page_header('search', 'AI 辅助物品匹配', '生成式指纹 + 信息增益追问 + 动态排序',
                step='第 2 步 / 共 2 步')

    notice = st.session_state.pop('duplicate_notice', None)
    if notice:
        st.warning(notice)

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

    ranked = rank_candidates(fp, session['candidates'], session['answers'],
                             query_time=session.get('query_time'),
                             query_location=session.get('query_location'))
    if not ranked:
        st.info('对面暂时没有可检索的报告。')
        if st.button('查看我的记录'):
            st.session_state.state = 'profile'
            st.rerun()
        return

    st.markdown('### 候选排序')
    st.caption('分数是排序指标，不是所有权概率。')
    st.caption('打分 = 0.72 × CLIP 相似度 + 0.28 × 证据 + 时间/地点软先验（最多 +0.05，缺失不扣分）；'
               'CLIP 文本↔照片的原始相似度常见区间只有 0.2–0.35，所以总分看起来不高是正常的。')
    db = Database()
    report_meta = ReportMeta()
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
                meta = report_meta.get(item.id)
                published_at = meta.get('published_at') if meta else None
                body = st.columns([1, 2.4], gap='medium')
                with body[0]:
                    if item.image is not None:
                        st.image(watermark(item.image, item.id, published_at), width=220)
                with body[1]:
                    st.write(item.description)
                    st.caption(f"地点：{getattr(item, 'location', None) or '未知'} · "
                               f"日期：{_date_text(getattr(item, 'time', None))}")
                    st.caption(publication_text(item.id, item.description or "", published_at))
                    if result.get('prior_bonus'):
                        st.caption(f"时间/地点软先验 +{result['prior_bonus']:.3f}")
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
        selected_id = selections[label]
        request_state = MatchRequests().state(session['direction'], session['item_id'],
                                              selected_id)
        if request_state['status'] == 'pending':
            st.info('已发送请求，等待对方确认。')
        elif request_state['status'] == 'accepted':
            st.success('已经配对；联系方式在「我的记录 → 已确认的匹配」里。')
        elif request_state['status'] == 'rejected':
            if request_state['can_request']:
                st.warning('对方之前拒绝了这条请求，现在可以重新发起。')
            else:
                st.warning(f"对方已拒绝；{cooldown_text(request_state['cooldown'])}后可重新发起。")

        can_send = request_state['can_request']
        button_label = ('重新发送匹配请求'
                        if request_state['status'] == 'rejected' and can_send
                        else '发送匹配请求')
        if st.button(button_label, type='primary', use_container_width=True,
                     disabled=not can_send):
            try:
                status = MatchRequests().create(session['direction'], session['item_id'],
                                                selected_id, session['user'])
            except (OSError, ValueError, PermissionError) as error:
                st.error(f'无法创建匹配请求：{error}')
            else:
                st.success('请求状态：' + STATUS_DISPLAY.get(status, status)
                           + '。双方确认后才会显示联系方式。')

    if st.button('前往我的记录', use_container_width=True):
        st.session_state.state = 'profile'
        st.rerun()
