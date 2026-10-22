"""The visual language: design tokens, one global stylesheet and its injection point.

Streamlit renders its own DOM, so the sheet hangs off the hooks it promises to keep
stable: the data-testid attributes and the st-key-* classes emitted by
st.container(key=...). Emotion class names are never used on purpose, they change
between releases. Everything here is presentation only, no page logic.

Design language (2026-10-22, after pioneer-wiki; see .dsh/agents/ui.md):
- aged archive paper (#E9E1D1) with a procedural grain, lighter sheets laid on it
- ink text with letterpress serif display type (self-hosted Noto Serif SC subset)
- hairline rules, 2-4 px corners, almost no shadow; states are printed stamps
- brick = lost, moss = found, gold = caution, indigo = neutral accent
"""

from __future__ import annotations

import streamlit as st

CSS = """
@font-face {
  font-family: "Noto Serif SC";
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: local("Noto Serif SC"), url("app/static/fonts/noto-serif-sc-subset.woff2") format("woff2");
}

:root {
  /* Archive paper, taken from pioneer-wiki's design tokens. */
  --paper: #E9E1D1;
  --paper-sheet: #F3EEE4;
  --paper-deep: #E0D7C5;

  --ink: #24221E;
  --ink-2: #4A453C;
  --ink-3: #5C5548;

  --moss: #65745A;
  --moss-ink: #4D5A43;
  --sage: #9DA889;
  --brick: #B96A59;
  --brick-ink: #94493A;
  --indigo: #34465A;
  --gold: #B99A63;
  --gold-ink: #6E5829;

  --rule: rgba(36, 34, 30, .14);
  --rule-strong: rgba(36, 34, 30, .30);
  --mark: rgba(185, 154, 99, .34);

  /* Direction colours: brick = lost, moss = found. Text uses the darker inks. */
  --lost: var(--brick-ink);
  --lost-bg: rgba(185, 106, 89, .13);
  --found: var(--moss-ink);
  --found-bg: rgba(101, 116, 90, .14);
  --ok: var(--moss-ink);
  --warn: var(--gold-ink);
  --danger: var(--brick-ink);

  --radius: 3px;
  --shadow: 0 1px 0 rgba(36, 34, 30, .05), 0 10px 22px -18px rgba(36, 34, 30, .45);
  --shadow-lift: 0 1px 0 rgba(36, 34, 30, .07), 0 20px 40px -28px rgba(36, 34, 30, .5);

  --font-display: "Noto Serif SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", "DejaVu Serif", serif;
  --font-body: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", "Droid Sans Fallback", sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, "Cascadia Mono", Consolas, "Sarasa Mono SC", monospace;

  --ease: cubic-bezier(.25, .7, .25, 1);
  --dur: 240ms;

  /* Two procedural noise layers: soft blotching and fine grain. */
  --paper-tone: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='900' height='900'%3E%3Cfilter id='t' x='0' y='0' width='1' height='1'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.0033' numOctaves='3' seed='7' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 0.45 0 0 0 0 0.36 0 0 0 0 0.22 0 0 0 0.42 -0.18'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23t)'/%3E%3C/svg%3E");
  --paper-grain: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='g' x='0' y='0' width='1' height='1'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' seed='11' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 0.14 0 0 0 0 0.13 0 0 0 0 0.12 0 0 0 0.5 -0.2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23g)'/%3E%3C/svg%3E");
}

html, body, .stApp {
  background-color: var(--paper);
  color: var(--ink);
  font-family: var(--font-body);
  font-size: 15.5px;
  line-height: 1.7;
  -webkit-font-smoothing: antialiased;
}

[data-testid="stAppViewContainer"] {
  background-color: var(--paper);
  background-image: var(--paper-grain), var(--paper-tone);
  background-size: 240px 240px, 900px 900px;
  color: var(--ink);
}

::selection { background: var(--mark); }

/* Streamlit's own chrome: header, deploy button, menu, skill nudge, sidebar. */
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stMainMenu"],
[data-testid="stAppDeployButton"], [data-testid="stSkillsNudge"],
[data-testid="stSkillsNudgeAnchor"], [data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"] {
  display: none !important;
}

[data-testid="stMainBlockContainer"] {
  max-width: 1080px;
  padding: 2.4rem 1.5rem 5.5rem;
}

[data-testid="stMainBlockContainer"] h1,
[data-testid="stMainBlockContainer"] h2,
[data-testid="stMainBlockContainer"] h3,
[data-testid="stMainBlockContainer"] h4 {
  font-family: var(--font-display);
  font-weight: 600;
  letter-spacing: .01em;
  color: var(--ink);
}
[data-testid="stMainBlockContainer"] h1 { font-size: 2.15rem; line-height: 1.18; }
[data-testid="stMainBlockContainer"] h2 {
  font-size: 1.55rem; line-height: 1.25; margin: 1.8rem 0 .7rem;
  padding-bottom: .45rem; border-bottom: 1px solid var(--rule);
}
[data-testid="stMainBlockContainer"] h3 { font-size: 1.15rem; margin: 1.4rem 0 .5rem; }
[data-testid="stMainBlockContainer"] h4 { font-size: 1rem; }
[data-testid="stHeading"] h3:first-child,
[data-testid="stMarkdownContainer"] > h3:first-child,
[data-testid="stMarkdownContainer"] > h2:first-child { margin-top: 0; }

[data-testid="stMarkdownContainer"] p { line-height: 1.75; }
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p {
  color: var(--ink-3);
  font-size: .78rem;
  letter-spacing: .03em;
}
[data-testid="stCaptionContainer"] p { line-height: 1.55; }

/* ---------- top bar ---------- */
.st-key-topbar {
  border-bottom: 1px solid var(--rule-strong);
  box-shadow: 0 4px 0 -3px var(--rule);
  padding-bottom: .85rem;
  margin-bottom: 1.9rem;
}
.brand { display: flex; align-items: center; gap: 10px; min-width: 0; }
.brand-seal {
  width: 31px; height: 31px; flex: 0 0 31px;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--rule-strong);
  border-radius: 50%;
  color: var(--ink-2);
  font-family: var(--font-display);
  font-size: .78rem;
  letter-spacing: .02em;
  font-variant-numeric: tabular-nums;
}
.brand-word {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: .98rem;
  letter-spacing: .07em;
  color: var(--ink);
  white-space: nowrap;
  line-height: 1.15;
  text-transform: uppercase;
}
.brand-sub {
  font-size: .58rem;
  letter-spacing: .28em;
  color: var(--ink-3);
  text-transform: uppercase;
  white-space: nowrap;
  margin-top: .12rem;
}
[class*="st-key-topbar"] [data-testid="stHorizontalBlock"] { align-items: center; }
/* Navigation reads as printed tabs, not as a row of buttons. */
[class*="st-key-topbar"] [data-testid="stBaseButton-secondary"] {
  background: transparent !important;
  border: 0 !important;
  border-radius: 0 !important;
  color: var(--ink-2) !important;
  box-shadow: none !important;
  padding: .28rem .35rem !important;
  min-height: 0;
  font-size: .82rem;
  letter-spacing: .1em;
}
[class*="st-key-topbar"] [data-testid="stBaseButton-secondary"]:hover {
  background: transparent !important;
  color: var(--ink) !important;
  box-shadow: inset 0 -1px 0 var(--rule-strong) !important;
}
[class*="st-key-topbar"] [data-testid="stBaseButton-primary"] {
  background: transparent !important;
  border: 0 !important;
  border-radius: 0 !important;
  border-bottom: 2px solid var(--ink) !important;
  color: var(--ink) !important;
  box-shadow: none !important;
  padding: .28rem .35rem !important;
  min-height: 0;
  font-size: .82rem;
  letter-spacing: .1em;
}
[class*="st-key-topbar"] [data-testid="stBaseButton-primary"]:hover {
  background: transparent !important;
  color: var(--ink) !important;
}
[class*="st-key-topbar"] [data-testid="stBaseButton-primary"] p,
[class*="st-key-topbar"] [data-testid="stBaseButton-secondary"] p { font-size: .82rem; }

/* ---------- page header ---------- */
.page-head {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin: .1rem 0 1.7rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--rule);
}
.page-head-icon {
  width: 36px; height: 36px; flex: 0 0 36px;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--rule-strong);
  border-radius: 2px;
  background: transparent;
  color: var(--ink-2);
}
.page-head-icon svg, .auth-point-icon svg, .empty-icon svg { display: block; }
.page-head-title {
  font-family: var(--font-display);
  font-size: 1.85rem;
  font-weight: 600;
  line-height: 1.22;
  letter-spacing: .012em;
}
.page-head-sub {
  color: var(--ink-3);
  font-size: .9rem;
  margin-top: .32rem;
  max-width: 62ch;
}
.page-head-step {
  display: inline-block; margin-left: .65rem; vertical-align: middle;
  font-family: var(--font-body);
  font-size: .64rem; font-weight: 600; letter-spacing: .2em;
  color: var(--gold-ink);
  border: 1px solid rgba(185, 154, 99, .55);
  border-radius: 1px;
  padding: .14rem .42rem;
}

/* ---------- cards, forms, paper wells ---------- */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--paper-sheet);
  border: 1px solid rgba(36, 34, 30, .18) !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow);
  padding: .3rem .25rem;
}
[data-testid="stForm"] {
  background: var(--paper-sheet);
  border: 1px solid var(--rule) !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow);
  padding: 1.35rem 1.35rem .95rem;
}
[data-testid="stForm"] [data-testid="stFormSubmitButton"] { margin-top: .35rem; }

/* ---------- buttons ---------- */
.stButton > button,
[data-testid="stFormSubmitButton"] > button,
[data-testid="stDownloadButton"] > button,
[data-testid="stFileUploaderDropzone"] button {
  font-family: var(--font-body);
  border-radius: 2px !important;
  border: 1px solid var(--rule-strong);
  background: transparent;
  color: var(--ink-2);
  font-weight: 600;
  font-size: .86rem;
  letter-spacing: .06em;
  padding: .44rem .9rem;
  box-shadow: none;
  transition: color var(--dur) var(--ease), border-color var(--dur) var(--ease), background var(--dur) var(--ease);
}
.stButton > button:hover,
[data-testid="stFormSubmitButton"] > button:hover,
[data-testid="stDownloadButton"] > button:hover,
[data-testid="stFileUploaderDropzone"] button:hover {
  border-color: var(--ink);
  color: var(--ink);
  background: rgba(36, 34, 30, .04);
}
.stButton > button:focus-visible, [data-testid="stFormSubmitButton"] > button:focus-visible {
  outline: 2px solid var(--gold-ink);
  outline-offset: 2px;
}

/* Active navigation and every primary action: an ink block, not a coloured pill. */
[data-testid="stBaseButton-primary"],
[data-testid="stFormSubmitButton"] [data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-primaryFormSubmit"] {
  background: var(--ink) !important;
  border-color: var(--ink) !important;
  color: var(--paper-sheet) !important;
}
[data-testid="stBaseButton-primary"]:hover,
[data-testid="stFormSubmitButton"] [data-testid="stBaseButton-primary"]:hover,
[data-testid="stBaseButton-primaryFormSubmit"]:hover {
  background: #3A362F !important;
  border-color: #3A362F !important;
  color: var(--paper-sheet) !important;
}
[data-testid="stBaseButton-tertiary"] {
  background: transparent !important;
  border-color: transparent !important;
  color: var(--ink-2) !important;
  box-shadow: none !important;
  letter-spacing: .06em;
}
[data-testid="stBaseButton-tertiary"]:hover {
  color: var(--ink) !important;
  text-decoration: underline;
  text-underline-offset: 3px;
}

/* Destructive action: small brick stamp, never the primary affordance. */
[class*="st-key-withdraw-"] button,
[class*="st-key-confirm-withdraw-"] button {
  background: var(--brick-ink) !important;
  border-color: var(--brick-ink) !important;
  color: var(--paper-sheet) !important;
  padding: .28rem .7rem;
  font-size: .8rem;
  font-weight: 600;
  min-height: 0;
}
[class*="st-key-withdraw-"] button:hover,
[class*="st-key-confirm-withdraw-"] button:hover {
  background: #7A392C !important;
  border-color: #7A392C !important;
  color: var(--paper-sheet) !important;
}
[class*="st-key-withdraw-"] button p,
[class*="st-key-confirm-withdraw-"] button p { font-size: .8rem; }

/* ---------- inputs ---------- */
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div,
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
[data-testid="stDateInput"] input, [data-testid="stNumberInput"] input {
  background: var(--paper-sheet) !important;
  border: 1px solid var(--rule-strong) !important;
  border-radius: 2px !important;
  color: var(--ink) !important;
  box-shadow: none !important;
  font-family: var(--font-body);
}
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
[data-testid="stDateInput"] input, [data-testid="stNumberInput"] input {
  padding: .42rem .55rem;
}
[data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within,
[data-baseweb="select"] > div:focus-within,
[data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus,
[data-testid="stDateInput"] input:focus {
  border-color: var(--gold-ink) !important;
  box-shadow: 0 0 0 2px var(--mark) !important;
  outline: none !important;
}
[data-testid="stWidgetLabel"] p {
  font-size: .78rem;
  font-weight: 600;
  color: var(--ink-2);
  letter-spacing: .06em;
}
[data-testid="stTooltipIcon"] { color: var(--ink-3); }
.stApp input::placeholder, .stApp textarea::placeholder { color: var(--ink-3); opacity: .72; }
[data-testid="stFileUploaderDropzone"] {
  background: var(--paper-sheet);
  border: 1px dashed var(--rule-strong);
  border-radius: 2px;
  padding: .9rem 1rem;
}
[data-testid="stFileUploaderDropzoneInstructions"] div,
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzoneInstructions"] small {
  color: var(--ink-3) !important;
  font-size: .76rem !important;
  letter-spacing: .02em;
}
[data-testid="stCheckbox"], [data-testid="stRadio"] { color: var(--ink-2); }

/* ---------- alerts: paper with a printed left rule ---------- */
[data-testid="stAlert"] {
  padding: 0 !important;
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
}
/* Streamlit paints the pastel fill on the inner container; flatten it to paper. */
[data-testid="stAlertContainer"] {
  background: var(--paper-sheet) !important;
  border: 1px solid var(--rule) !important;
  border-left: 3px solid var(--rule-strong) !important;
  border-radius: 2px !important;
  padding: .6rem .8rem !important;
  box-shadow: none !important;
}
[data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]) [data-testid="stAlertContainer"] { border-left-color: var(--moss) !important; }
[data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]) [data-testid="stAlertContainer"] { border-left-color: var(--gold) !important; }
[data-testid="stAlert"]:has([data-testid="stAlertContentError"]) [data-testid="stAlertContainer"] { border-left-color: var(--brick) !important; }
[data-testid="stAlert"]:has([data-testid="stAlertContentInfo"]) [data-testid="stAlertContainer"] { border-left-color: var(--indigo) !important; }
[data-testid^="stAlertContent"] { color: var(--ink-2) !important; }
[data-testid="stAlertTitle"] { color: var(--ink) !important; font-weight: 600; }

[data-testid="stProgressBarTrack"] {
  background: var(--paper-deep) !important;
  border-radius: 0 !important;
  height: 8px !important;
}
[data-testid="stProgressBarTrack"] > div {
  background: var(--ink) !important;
  border-radius: 0 !important;
}
[data-testid="stSpinner"] { color: var(--ink-3); }

/* ---------- pills and stamps ---------- */
.pill {
  display: inline-block; margin: 0 .38rem .38rem 0;
  padding: .08rem .5rem;
  border: 1px solid currentColor;
  border-radius: 1px;
  font-family: var(--font-body);
  font-size: .68rem; font-weight: 600; line-height: 1.75; letter-spacing: .12em;
  background: transparent; color: var(--ink-3);
}
.pill-brand { color: var(--indigo); background: rgba(52, 70, 90, .06); border-color: rgba(52, 70, 90, .38); }
.pill-lost { color: var(--lost); background: var(--lost-bg); border-color: rgba(185, 106, 89, .48); }
.pill-found { color: var(--found); background: var(--found-bg); border-color: rgba(101, 116, 90, .5); }
.pill-ok { color: var(--ok); background: var(--found-bg); border-color: rgba(101, 116, 90, .5); }
.pill-warn { color: var(--warn); background: rgba(185, 154, 99, .18); border-color: rgba(185, 154, 99, .55); }
.pill-danger { color: var(--danger); background: var(--lost-bg); border-color: rgba(185, 106, 89, .48); }

/* Streamlit's segmented control, restyled as ledger tabs. */
[data-testid="stPills"] button,
[data-testid="stButtonGroup"] button {
  border-radius: 2px !important;
  border: 1px solid var(--rule-strong) !important;
  background: transparent !important;
  color: var(--ink-2) !important;
  font-size: .8rem;
  letter-spacing: .06em;
}
[data-testid="stPills"] button[aria-checked="true"],
[data-testid="stPills"] button[aria-selected="true"],
[data-testid="stButtonGroup"] button[aria-checked="true"] {
  background: var(--ink) !important;
  border-color: var(--ink) !important;
  color: var(--paper-sheet) !important;
}

/* ---------- statistics: specimen cells ---------- */
.stat-grid {
  display: flex;
  flex-wrap: wrap;
  border-top: 1px solid var(--rule-strong);
  border-bottom: 1px solid var(--rule);
  margin: .2rem 0 .6rem;
}
.stat {
  flex: 1 1 150px; min-width: 130px;
  background: transparent;
  border-right: 1px solid var(--rule);
  border-radius: 0;
  box-shadow: none;
  padding: .8rem 1rem .85rem;
}
.stat:last-child { border-right: 0; }
.stat-value {
  font-family: var(--font-display);
  font-size: 1.85rem; font-weight: 600; line-height: 1.12;
  font-variant-numeric: tabular-nums;
}
.stat-label {
  color: var(--ink-3); font-size: .68rem; letter-spacing: .16em;
  text-transform: uppercase; margin-top: .25rem;
}
.stat-hint { color: var(--ink-3); font-size: .72rem; margin-top: .15rem; opacity: .9; }

/* ---------- empty states ---------- */
.empty {
  text-align: center;
  padding: 1.5rem 1rem 1.6rem;
  color: var(--ink-3);
  background: transparent;
  border: 0;
  border-top: 1px solid var(--rule);
  border-bottom: 1px solid var(--rule);
}
.empty-art {
  width: 128px; height: 96px;
  margin: 0 auto .5rem;
  background-position: center;
  background-repeat: no-repeat;
  background-size: contain;
  opacity: .95;
}
.empty-icon { color: var(--ink-3); }
.empty-title { font-family: var(--font-display); font-size: 1.02rem; font-weight: 600; color: var(--ink); margin-top: .35rem; }
.empty-hint { font-size: .82rem; margin-top: .25rem; color: var(--ink-3); }

/* ---------- generated plates ---------- */
.plate { margin: 0; }
.plate img {
  display: block; width: 100%; height: auto;
  -webkit-mask-image: linear-gradient(to right, transparent, #000 4%, #000 96%, transparent),
    linear-gradient(to bottom, transparent, #000 4%, #000 96%, transparent);
  -webkit-mask-composite: source-in;
  mask-image: linear-gradient(to right, transparent, #000 4%, #000 96%, transparent),
    linear-gradient(to bottom, transparent, #000 4%, #000 96%, transparent);
  mask-composite: intersect;
}
.plate-ornament img { width: min(190px, 46%) !important; margin: .1rem 0 .55rem; }
.plate figcaption {
  font-size: .66rem; letter-spacing: .22em; color: var(--ink-3);
  text-align: center; margin-top: .2rem; text-transform: uppercase;
}
.entry-art {
  display: block;
  width: 96px; height: 72px;
  margin: 0 0 .35rem;
  background-position: left center;
  background-repeat: no-repeat;
  background-size: contain;
}
[class*="st-key-auth-plate"] [data-testid="stImage"] img {
  max-width: 100% !important;
  height: auto !important;
  padding: 0 !important;
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
  border-radius: 0 !important;
  -webkit-mask-image: radial-gradient(ellipse 78% 78% at 50% 52%, #000 58%, transparent 100%);
  mask-image: radial-gradient(ellipse 78% 78% at 50% 52%, #000 58%, transparent 100%);
}
.auth-kicker {
  font-size: .64rem; letter-spacing: .26em; text-transform: uppercase;
  color: var(--ink-3); margin-bottom: .1rem;
}

/* ---------- auth pages ---------- */
.auth-title {
  font-family: var(--font-display);
  font-size: 2.5rem; font-weight: 600; letter-spacing: .03em;
  line-height: 1.1; margin: .55rem 0 .35rem;
}
.auth-lead { color: var(--ink-3); font-size: .95rem; line-height: 1.75; margin-bottom: 1.1rem; max-width: 40ch; }
.auth-point { display: flex; gap: 11px; align-items: flex-start; margin: .55rem 0; }
.auth-point-icon {
  width: 27px; height: 27px; flex: 0 0 27px;
  border: 1px solid var(--rule-strong);
  border-radius: 50%;
  background: transparent;
  color: var(--ink-2);
  display: flex; align-items: center; justify-content: center;
}
.auth-point-text { font-size: .88rem; color: var(--ink-2); line-height: 1.55; }
.auth-point-text span { color: var(--ink-3); }
.auth-card-title { font-family: var(--font-display); font-size: 1.35rem; font-weight: 600; margin-bottom: .05rem; }
.auth-card-sub { color: var(--ink-3); font-size: .82rem; margin-bottom: .95rem; }
.auth-alt { color: var(--ink-3); font-size: .84rem; text-align: center; margin: 1rem 0 .4rem; }
.card-title { font-family: var(--font-display); font-size: 1.2rem; font-weight: 600; margin: .45rem 0 .35rem; }
.card-copy { color: var(--ink-3); font-size: .9rem; line-height: 1.65; margin-bottom: .9rem; }
[class*="st-key-card-"] h3 { margin-top: 0; }
[class*="st-key-card-"] [data-testid="stHeading"] { margin-top: 0; }

/* ---------- candidates ---------- */
.cand-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: .4rem; }
.cand-rank {
  font-family: var(--font-display);
  font-weight: 600; font-size: .9rem; color: var(--paper-sheet);
  background: var(--ink); border-radius: 1px; padding: .02rem .42rem;
}
.cand-score { font-family: var(--font-display); font-size: 1.3rem; font-weight: 600; font-variant-numeric: tabular-nums; }
.cand-score-cap { color: var(--ink-3); font-size: .74rem; letter-spacing: .04em; }

/* ---------- photographs: tipped-in prints, never colour-graded ---------- */
/* A photograph mounted on a card: paper matte, hairline, a resting shadow. */
[data-testid="stImage"] img {
  border-radius: 1px;
  padding: 4px;
  background: var(--paper-sheet);
  border: 1px solid var(--rule);
  box-shadow: var(--shadow);
}
[class*="st-key-cand-"] [data-testid="stImage"] img {
  max-height: 200px; width: auto; object-fit: cover;
}
[data-testid="stDialog"] > div {
  background: var(--paper-sheet);
  border: 1px solid var(--rule);
  border-radius: 3px;
  box-shadow: var(--shadow-lift);
}
[data-testid="stDialog"] h2 { border: 0; }

@media (max-width: 720px) {
  [data-testid="stMainBlockContainer"] { padding: 1.1rem .9rem 3rem; }
  [data-testid="stHorizontalBlock"] { row-gap: 1rem !important; }
  .page-head-title { font-size: 1.45rem; }
  .auth-title { font-size: 1.9rem; }
  .stat { min-width: 110px; }
  .entry-art { display: none; }
  .brand-sub { display: none; }
  .brand-word { letter-spacing: .06em; font-size: .82rem; }
  .brand-seal { width: 26px; height: 26px; flex: 0 0 26px; font-size: .48rem; }
  .empty-art { width: 104px; height: 80px; }
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
    padding: .28rem .55rem;
    font-size: .78rem;
    letter-spacing: .02em;
    white-space: nowrap;
    min-height: 0;
  }
  .brand-word { font-size: .82rem; }
  [class*="st-key-topbar"] [data-testid="stHorizontalBlock"] > div:first-child { position: sticky; left: 0; background: var(--paper); }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition-duration: 0.01ms !important; animation-duration: 0.01ms !important; }
}
"""


def inject() -> None:
    """Render the global stylesheet once per script run."""
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
