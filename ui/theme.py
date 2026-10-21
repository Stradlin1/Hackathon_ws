"""The visual language: design tokens, one global stylesheet and its injection point.

Streamlit renders its own DOM, so the sheet hangs off the hooks it promises to keep
stable: the data-testid attributes and the st-key-* classes emitted by
st.container(key=...). Emotion class names are never used on purpose, they change
between releases. Everything here is presentation only, no page logic.

Design language (2026-10-21, see .dsh/agents/ui.md):
- navy brand taken from static/logo_rounded.png
- light theme, white cards on a cool grey page, 16px corners, soft shadow
- amber = lost, teal = found, so the two directions never rely on wording alone
"""

from __future__ import annotations

import streamlit as st

CSS = """

:root {
  --brand: #16324F;
  --brand-soft: #E8EEF6;
  --ink: #111827;
  --muted: #5B6472;
  --page: #F5F6FA;
  --surface: #FFFFFF;
  --line: #E6E8EF;
  --lost: #B45309;
  --lost-bg: #FEF3C7;
  --found: #0F766E;
  --found-bg: #CCFBF1;
  --ok: #047857;
  --warn: #B45309;
  --danger: #B91C1C;
  --radius: 16px;
  --shadow: 0 1px 2px rgba(16, 24, 40, .04), 0 8px 24px -12px rgba(16, 24, 40, .18);
}

html, body, .stApp, [data-testid="stAppViewContainer"] {
  background: var(--page);
  color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
    "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
}

/* Streamlit's own chrome: header, deploy button, menu, skill nudge, sidebar. */
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stMainMenu"],
[data-testid="stAppDeployButton"], [data-testid="stSkillsNudge"],
[data-testid="stSkillsNudgeAnchor"], [data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"] {
  display: none !important;
}

[data-testid="stMainBlockContainer"] {
  max-width: 1120px;
  padding: 2.2rem 1.4rem 5rem;
}

[data-testid="stMainBlockContainer"] h1,
[data-testid="stMainBlockContainer"] h2,
[data-testid="stMainBlockContainer"] h3 {
  letter-spacing: -.01em;
  color: var(--ink);
}
[data-testid="stMainBlockContainer"] h3 {
  font-size: 1.1rem;
  font-weight: 700;
  margin: 1.4rem 0 .5rem;
}
[data-testid="stMainBlockContainer"] h2 { font-size: 1.3rem; }
[data-testid="stHeading"] h3:first-child,
[data-testid="stMarkdownContainer"] > h3:first-child { margin-top: 0; }

/* ---------- top bar ---------- */
.st-key-topbar {
  border-bottom: 1px solid var(--line);
  padding-bottom: .8rem;
  margin-bottom: 1.6rem;
}
.brand-word {
  font-weight: 700;
  font-size: 1.02rem;
  letter-spacing: -.01em;
  color: var(--brand);
  white-space: nowrap;
}

/* ---------- page header ---------- */
.page-head { display: flex; align-items: flex-start; gap: 14px; margin: .2rem 0 1.4rem; }
.page-head-icon {
  width: 44px; height: 44px; flex: 0 0 44px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 12px; background: var(--brand-soft); color: var(--brand);
}
.page-head-icon svg, .auth-point-icon svg, .empty-icon svg { display: block; }
.empty-icon { color: var(--muted); }
.page-head-title { font-size: 1.6rem; font-weight: 700; line-height: 1.25; }
.page-head-sub { color: var(--muted); font-size: .92rem; margin-top: .25rem; }
.page-head-step {
  display: inline-block; margin-left: .6rem; vertical-align: middle;
  font-size: .72rem; font-weight: 600; color: var(--brand);
  background: var(--brand-soft); border-radius: 999px; padding: .18rem .55rem;
}

/* ---------- cards ---------- */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--surface);
  border: 1px solid var(--line) !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow);
  padding: .35rem .2rem;
}
[data-testid="stForm"] {
  background: var(--surface);
  border: 1px solid var(--line) !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow);
  padding: 1.3rem 1.3rem .9rem;
}

/* ---------- buttons ---------- */
.stButton > button, [data-testid="stFormSubmitButton"] > button, [data-testid="stDownloadButton"] > button {
  border-radius: 10px;
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--ink);
  font-weight: 600;
  padding: .48rem .9rem;
  box-shadow: none;
  transition: border-color .15s ease, color .15s ease, background .15s ease;
}
.stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
  border-color: var(--brand);
  color: var(--brand);
  background: var(--surface);
}
[data-testid="stBaseButton-primary"],
[data-testid="stFormSubmitButton"] [data-testid="stBaseButton-primary"] {
  background: var(--brand) !important;
  border-color: var(--brand) !important;
  color: #FFFFFF !important;
}
[data-testid="stBaseButton-primary"]:hover,
[data-testid="stFormSubmitButton"] [data-testid="stBaseButton-primary"]:hover {
  background: #1E4468 !important;
  border-color: #1E4468 !important;
  color: #FFFFFF !important;
}
[data-testid="stBaseButton-primaryFormSubmit"] {
  background: var(--brand) !important;
  border-color: var(--brand) !important;
  color: #FFFFFF !important;
}
[data-testid="stBaseButton-primaryFormSubmit"]:hover {
  background: #1E4468 !important;
  border-color: #1E4468 !important;
  color: #FFFFFF !important;
}
[data-testid="stBaseButton-tertiary"] {
  background: transparent !important;
  border-color: transparent !important;
  color: var(--brand) !important;
  box-shadow: none !important;
}

/* ---------- inputs ---------- */
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
[data-testid="stDateInput"] input, [data-testid="stNumberInput"] input {
  border-radius: 10px;
}
[data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus {
  border-color: var(--brand) !important;
  box-shadow: 0 0 0 3px rgba(22, 50, 79, .12) !important;
}
[data-testid="stWidgetLabel"] p { font-size: .86rem; font-weight: 600; color: var(--ink); }

/* ---------- alerts ---------- */
[data-testid="stAlert"] { border-radius: 12px; }

/* ---------- small pieces ---------- */
.pill {
  display: inline-block; margin: 0 .3rem .3rem 0;
  padding: .18rem .6rem; border-radius: 999px;
  font-size: .76rem; font-weight: 600; line-height: 1.6;
  background: #EEF1F6; color: var(--muted);
}
.pill-brand { background: var(--brand-soft); color: var(--brand); }
.pill-lost { background: var(--lost-bg); color: var(--lost); }
.pill-found { background: var(--found-bg); color: var(--found); }
.pill-ok { background: #D1FAE5; color: var(--ok); }
.pill-warn { background: var(--lost-bg); color: var(--warn); }
.pill-danger { background: #FEE2E2; color: var(--danger); }

.stat-grid { display: flex; gap: 12px; flex-wrap: wrap; }
.stat {
  flex: 1 1 150px; min-width: 140px;
  background: var(--surface); border: 1px solid var(--line);
  border-radius: 14px; padding: .85rem 1rem; box-shadow: var(--shadow);
}
.stat-value { font-size: 1.5rem; font-weight: 700; line-height: 1.2; }
.stat-label { color: var(--muted); font-size: .8rem; margin-top: .15rem; }
.stat-hint { color: var(--muted); font-size: .72rem; margin-top: .3rem; }

.empty {
  text-align: center; padding: 1.6rem 1rem; color: var(--muted);
  border: 1px dashed var(--line); border-radius: 14px; background: rgba(255, 255, 255, .6);
}
.empty-icon { font-size: 1.6rem; }
.empty-title { font-weight: 600; color: var(--ink); margin-top: .4rem; }
.empty-hint { font-size: .84rem; margin-top: .2rem; }

/* ---------- auth pages ---------- */
.auth-title { font-size: 2.1rem; font-weight: 800; letter-spacing: -.02em; margin: .9rem 0 .3rem; }
.auth-lead { color: var(--muted); font-size: .98rem; line-height: 1.7; margin-bottom: 1.1rem; }
.auth-point { display: flex; gap: 10px; align-items: flex-start; margin: .55rem 0; }
.auth-point-icon {
  width: 26px; height: 26px; flex: 0 0 26px; border-radius: 8px;
  background: var(--brand-soft); color: var(--brand);
  display: flex; align-items: center; justify-content: center; font-size: .8rem;
}
.auth-point-text { font-size: .9rem; color: var(--ink); line-height: 1.5; }
.auth-point-text span { color: var(--muted); }
.auth-card-title { font-size: 1.25rem; font-weight: 700; margin-bottom: .1rem; }
.auth-card-sub { color: var(--muted); font-size: .86rem; margin-bottom: .9rem; }
.auth-alt { color: var(--muted); font-size: .86rem; text-align: center; margin: 1rem 0 .4rem; }
.card-title { font-size: 1.18rem; font-weight: 700; margin: .45rem 0 .4rem; }
.card-copy { color: var(--muted); font-size: .92rem; line-height: 1.6; margin-bottom: .9rem; }
[class*="st-key-card-"] h3 { margin-top: 0; }
[class*="st-key-card-"] [data-testid="stHeading"] { margin-top: 0; }

/* ---------- candidates ---------- */
.cand-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: .4rem; }
.cand-rank {
  font-weight: 800; font-size: .95rem; color: var(--brand);
  background: var(--brand-soft); border-radius: 8px; padding: .1rem .45rem;
}
.cand-score { font-size: 1.25rem; font-weight: 700; }
.cand-score-cap { color: var(--muted); font-size: .78rem; }

@media (max-width: 720px) {
  [data-testid="stMainBlockContainer"] { padding: 1.2rem .9rem 3rem; }
  .page-head-title { font-size: 1.3rem; }
  .auth-title { font-size: 1.7rem; }
  .stat { min-width: 120px; }
}
/* Candidate thumbnails: portrait photos must not stretch the card. */
[class*="st-key-cand-"] [data-testid="stImage"] img {
  max-height: 200px;
  width: auto;
  border-radius: 12px;
  object-fit: cover;
}

/* Phone: keep the top bar on one scrollable row instead of a stack of buttons. */
@media (max-width: 720px) {
  [class*="st-key-topbar"] [data-testid="stHorizontalBlock"] {
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    overflow-x: auto;
    gap: .4rem;
    align-items: center;
  }
  [class*="st-key-topbar"] [data-testid="stColumn"] {
    width: auto !important;
    min-width: 0 !important;
    flex: 0 0 auto !important;
  }
  [class*="st-key-topbar"] .stButton > button {
    padding: .3rem .55rem;
    font-size: .8rem;
    white-space: nowrap;
    min-height: 0;
  }
  .brand-word { font-size: .86rem; }
}

"""


def inject() -> None:
    """Render the global stylesheet once per script run."""
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
