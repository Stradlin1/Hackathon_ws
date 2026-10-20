"""Interactive clarification and dynamic reranking page."""

from __future__ import annotations

import streamlit as st

from db_manager import Database
from matching.engine import DISPLAY, MAX_QUESTIONS, QUESTIONS, add_answer, choose_question, rank_candidates
from matching.requests import MatchRequests


def interactive_match(authenticator):
    authenticator.logout(location='sidebar')
    session = st.session_state.get('match_session')
    if not session or session.get('user') != st.session_state.get('username'):
        st.warning('No active matching session. Create a report first.')
        st.button('Back to menu', on_click=lambda: st.session_state.update(state='lost_or_found'))
        return

    st.title('AI-assisted item matching')
    st.caption('Generative fingerprint + information-gain questions + dynamic ranking')
    fp = session['fingerprint']
    attrs = fp.get('attributes', {})
    st.subheader('Generated item fingerprint')
    if attrs:
        st.write(' / '.join(f'{DISPLAY.get(k, k)}: {v}' for k, v in attrs.items()))
    else:
        st.info('No distinctive attributes could be extracted. You can still review CLIP candidates.')
    st.caption('Extraction method: ' + fp.get('method', 'unknown') +
               '. Only features with source evidence are retained.')

    ranked = rank_candidates(fp, session['candidates'], session['answers'])
    if not ranked:
        st.info('There are no currently searchable reports from the other side.')
        if st.button('View my profile'):
            st.session_state.state = 'profile'
            st.rerun()
        return

    st.subheader('Dynamic candidate ranking')
    st.caption('Scores are ranking metrics, not ownership probabilities.')
    db = Database()
    try:
        for index, result in enumerate(ranked[:5], 1):
            with st.expander(f'#{index}  Candidate {result["item_id"]}  |  score {result["score"]:.3f}', expanded=index == 1):
                item = db.get_item(result['item_id'])
                if item.image is not None:
                    st.image(item.image, width=260)
                st.write(item.description)
                st.caption(f'CLIP similarity: {result["semantic_score"]:.3f}')
                if result['matches']:
                    st.success('Matching features: ' + ', '.join(result['matches']))
                if result['conflicts']:
                    st.warning('Conflicting features: ' + ', '.join(result['conflicts']))
    finally:
        db.close()

    question_field = choose_question(fp, ranked, session['asked'])
    if question_field is not None and len(session['asked']) < MAX_QUESTIONS:
        st.subheader(f'Follow-up question {len(session["asked"]) + 1}/{MAX_QUESTIONS}')
        st.write(QUESTIONS[question_field])
        with st.form(f'clarification_{len(session["asked"])}'):
            answer = st.text_input('Your answer', max_chars=100)
            answered = st.form_submit_button('Update matching results')
            skipped = st.form_submit_button('I do not know / Skip')
        if answered or skipped:
            normalized = add_answer(session, question_field, '' if skipped else answer)
            if answered and normalized is None:
                st.warning('This answer could not be recognized and was treated as a skip.')
            st.session_state.match_session = session
            st.rerun()
    else:
        st.info('No further discriminative question is available. Review the ranked candidates.')

    if session['asked']:
        st.caption(f'Questions asked: {len(session["asked"])}. Answers: {session["answers"]}')

    st.subheader('Request confirmation')
    st.warning('A similarity result is not proof of ownership. The other account must accept before contact details are shared.')
    selections = {f'#{i}: {r["description"][:55] or "Item"} (score {r["score"]:.3f})': r['item_id']
                  for i, r in enumerate(ranked[:5], 1)}
    label = st.selectbox('Choose a candidate to contact', list(selections))
    if st.button('Send match request'):
        try:
            status = MatchRequests().create(session['direction'], session['item_id'], selections[label], session['user'])
        except (OSError, ValueError, PermissionError) as error:
            st.error(f'Cannot create a match request: {error}')
        else:
            st.success('Request status: ' + status + '. Contact details are shown after mutual confirmation.')

    if st.button('Go to profile'):
        st.session_state.state = 'profile'
        st.rerun()
