"""One intake entry point; the direction is a switch, not a separate page.

The existing lost/found flows stay intact and are called with `embedded=True`
so they do not draw their own top bar or page header.
"""

from __future__ import annotations

import streamlit as st

from state.found import found
from state.lost import lost
from ui.components import page_header, topbar

MODES = {"我丢了东西": "lost", "我捡到东西": "found"}
LABELS = {value: label for label, value in MODES.items()}


def report(authenticator):
    topbar("report", authenticator)
    page_header("layers", "登记物品", "先选方向：我丢了东西，或我捡到东西。",
                step="第 1 步 / 共 2 步")

    pending = st.session_state.pop("report_mode_pending", None)
    if pending in LABELS:
        st.session_state["report-mode"] = LABELS[pending]

    default_mode = st.session_state.get("report_mode", "lost")
    default_label = LABELS.get(default_mode, "我丢了东西")
    # Set the widget value before it is created; passing both `default` and a
    # session-state value makes Streamlit emit a policy warning.
    st.session_state.setdefault("report-mode", default_label)
    choice = st.pills("登记类型", list(MODES), selection_mode="single", key="report-mode")
    mode = MODES.get(choice, default_mode if default_mode in LABELS else "lost")
    st.session_state.report_mode = mode

    if mode == "lost":
        lost(authenticator, embedded=True)
    else:
        found(authenticator, embedded=True)
