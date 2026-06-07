"""Streamlit web UI for Auto-Dock It.

Two entry paths:
    streamlit run autodock/web.py        (local)
    streamlit run streamlit_app.py       (Streamlit Cloud, calls render())

Design: a monochrome "dark/light dashboard" with CSS custom properties so a
single toggle flips every surface instantly.  Five Lottie animations are placed
at meaningful moments to give the UI personality without breaking the B&W palette.
"""
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
import streamlit as st

from .rate_limit import check_and_record

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_ROOT = PROJECT_ROOT / "output"
ASSETS = PROJECT_ROOT / "assets"
ANIM = ASSETS / "anim"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mGKHF]")


def _strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


# ─────────────────────────────────────────────────────────────── Theme helpers
def _theme() -> str:
    """Return 'light' or 'dark' based on the sidebar toggle state."""
    return "light" if st.session_state.get("adi_theme_toggle", False) else "dark"


# ──────────────────────────────────────────────────────────────────── CSS ──

# CSS custom-property values – dark mode defaults.
_CSS_VARS_DARK = """
  :root {
    --adi-bg:           #0a0a0a;
    --adi-surface:      #111111;
    --adi-sidebar:      #0c0c0c;
    --adi-text:         #f5f5f5;
    --adi-text2:        #9a9a9a;
    --adi-muted:        #5f5f5f;
    --adi-border:       #1f1f1f;
    --adi-border2:      #2a2a2a;
    --adi-btn-bg:       #161616;
    --adi-btn-text:     #f5f5f5;
    --adi-primary-bg:   #f5f5f5;
    --adi-primary-text: #0a0a0a;
    --adi-code-bg:      #0d0d0d;
    --adi-input-bg:     #121212;
    --adi-eyebrow:      #8a8a8a;
    --adi-tab-bg:       #121212;
    --adi-tab-sel:      #1f1f1f;
    --adi-tab-text:     #9a9a9a;
    --adi-tab-sel-text: #ffffff;
    --adi-scroll-track: #141414;
    --adi-scroll-thumb: #383838;
  }
"""

# CSS custom-property values – light mode overrides.
_CSS_VARS_LIGHT = """
  :root {
    --adi-bg:           #f8f8f8;
    --adi-surface:      #ffffff;
    --adi-sidebar:      #efefef;
    --adi-text:         #111111;
    --adi-text2:        #555555;
    --adi-muted:        #888888;
    --adi-border:       #e8e8e8;
    --adi-border2:      #d0d0d0;
    --adi-btn-bg:       #ffffff;
    --adi-btn-text:     #111111;
    --adi-primary-bg:   #111111;
    --adi-primary-text: #ffffff;
    --adi-code-bg:      #f4f4f4;
    --adi-input-bg:     #ffffff;
    --adi-eyebrow:      #555555;
    --adi-tab-bg:       #efefef;
    --adi-tab-sel:      #ffffff;
    --adi-tab-text:     #555555;
    --adi-tab-sel-text: #111111;
    --adi-scroll-track: #e8e8e8;
    --adi-scroll-thumb: #b8b8b8;
  }
"""

# Structural rules shared by both themes — all colors via var().
_CSS_STRUCTURAL = """
  /* Layout */
  .block-container { padding-top: 4.75rem; max-width: 1180px; }

  /* Typography */
  h1, h2, h3 { letter-spacing: -0.01em; font-weight: 700; }
  h1 { font-size: 2.4rem !important; }

  /* Buttons */
  .stButton > button {
    border: 1px solid var(--adi-border2);
    border-radius: 10px;
    background: var(--adi-btn-bg);
    color: var(--adi-btn-text);
    font-weight: 600;
    transition: border-color .15s ease, background .15s ease, transform .05s ease;
  }
  .stButton > button:hover { border-color: var(--adi-text2) !important; }
  .stButton > button:active { transform: translateY(1px); }
  .stButton > button[kind="primary"] {
    background: var(--adi-primary-bg) !important;
    color: var(--adi-primary-text) !important;
    border-color: var(--adi-primary-bg) !important;
  }
  .stButton > button[kind="primary"]:hover { filter: brightness(1.08); }

  .stDownloadButton > button {
    border: 1px solid var(--adi-border2);
    border-radius: 10px;
    background: var(--adi-btn-bg);
    color: var(--adi-btn-text);
  }
  .stDownloadButton > button:hover { border-color: var(--adi-text2); }

  /* ── Inputs — single border on the OUTER root only ────────────────────────
     DOM structure (confirmed via inspection):
       [data-baseweb="input"]       ← OUTER root (stTextInputRootElement)
         [data-baseweb="base-input"] ← INNER wrapper — must have NO border
           <input>
           <button> (eye)
     Giving border to both produced the double-ring. Only the outer gets it.  */

  /* OUTER root: the single visible border surface */
  [data-baseweb="input"] {
    border-radius: 10px !important;
    border: 1px solid var(--adi-border2) !important;
    background: var(--adi-input-bg) !important;
    color: var(--adi-text) !important;
    overflow: hidden !important;
    transition: border-color .15s ease, box-shadow .15s ease !important;
  }
  [data-baseweb="input"]:hover {
    border-color: var(--adi-text2) !important;
  }
  [data-baseweb="input"]:focus-within {
    border-color: var(--adi-text) !important;
    box-shadow: 0 0 0 1px var(--adi-text) !important;
  }

  /* INNER base-input: transparent, no border — parent owns all chrome */
  [data-baseweb="base-input"] {
    border: none !important;
    border-radius: 0 !important;
    background: transparent !important;
    color: var(--adi-text) !important;
    box-shadow: none !important;
  }

  /* Actual <input> / <textarea> elements: also transparent, no extra border */
  .stTextInput input,
  .stTextArea textarea,
  [data-baseweb="base-input"] input,
  [data-baseweb="base-input"] textarea {
    border: none !important;
    border-radius: 0 !important;
    background: transparent !important;
    color: var(--adi-text) !important;
    box-shadow: none !important;
    outline: none !important;
  }
  /* Selectbox trigger (not a password wrapper — keep own border) */
  .stSelectbox div[data-baseweb="select"] > div {
    border-radius: 10px !important;
    border-color: var(--adi-border2) !important;
    background: var(--adi-input-bg) !important;
    color: var(--adi-text) !important;
  }

  /* ── Password eye-icon button — both themes (was light-only, now structural) ─
     The button sits inside [data-baseweb="base-input"]. Give it NO background,
     NO border, NO shadow so it looks like part of the input field in both modes. */
  [data-testid="stTextInput"] button,
  [data-testid="stTextInput"] button:hover,
  [data-testid="stTextInput"] button:focus,
  [data-testid="stTextInput"] button:active,
  button[aria-label="Show password text"],
  button[aria-label="Hide password text"],
  button[aria-label="Show password text"]:hover,
  button[aria-label="Hide password text"]:hover {
    background: transparent !important;
    background-color: transparent !important;
    background-image: none !important;
    border: none !important;
    border-color: transparent !important;
    box-shadow: none !important;
    outline: none !important;
    color: var(--adi-text2) !important;
  }
  [data-testid="stTextInput"] button svg,
  [data-testid="stTextInput"] button svg *,
  button[aria-label="Show password text"] svg,
  button[aria-label="Show password text"] svg *,
  button[aria-label="Hide password text"] svg,
  button[aria-label="Hide password text"] svg * {
    fill: var(--adi-text2) !important;
    color: var(--adi-text2) !important;
    stroke: var(--adi-text2) !important;
  }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: var(--adi-tab-bg);
    padding: 5px;
    border: 1px solid var(--adi-border);
    border-radius: 12px;
  }
  .stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 6px 18px;
    color: var(--adi-tab-text);
  }
  .stTabs [aria-selected="true"] {
    background: var(--adi-tab-sel) !important;
    color: var(--adi-tab-sel-text) !important;
  }
  .stTabs [data-baseweb="tab-highlight"] { background: transparent; }

  /* Code */
  .stCode, pre, code {
    font-family: 'JetBrains Mono','SFMono-Regular',Consolas,monospace !important;
  }
  div[data-testid="stCodeBlock"] {
    border: 1px solid var(--adi-border);
    border-radius: 12px;
    background: var(--adi-code-bg) !important;
  }

  /* Sidebar */
  section[data-testid="stSidebar"] {
    background: var(--adi-sidebar);
    border-right: 1px solid var(--adi-border);
  }

  /* Custom primitives */
  .adi-card {
    border: 1px solid var(--adi-border);
    border-radius: 14px;
    background: var(--adi-surface);
    padding: 18px 20px;
    margin: 6px 0 14px 0;
  }
  .adi-eyebrow {
    text-transform: uppercase;
    letter-spacing: .16em;
    font-size: .72rem;
    color: var(--adi-eyebrow);
    font-weight: 600;
  }
  .adi-sechead {
    display: flex; align-items: center; gap: .55rem;
    font-size: 1.15rem; font-weight: 700; color: var(--adi-text);
    margin: .2rem 0 .1rem 0;
  }
  .adi-sechead .ico {
    display: inline-flex; align-items: center;
    color: var(--adi-text); opacity: .9;
  }
  .adi-sechead .ico svg { width: 20px; height: 20px; display: block; }
  .adi-sub { color: var(--adi-text2); font-size: .92rem; margin: 0 0 .2rem 0; }

  /* Status badges */
  .adi-badge {
    display: inline-block; padding: 2px 10px; border-radius: 999px;
    font-size: .72rem; font-weight: 700; letter-spacing: .04em;
    border: 1px solid var(--adi-border2);
    background: var(--adi-btn-bg);
    color: var(--adi-text2);
  }
  .adi-badge.ok  { color: #aaaaaa; border-color: #383838; background: #1a1a1a; }
  .adi-badge.err { color: #777777; border-color: #2a2a2a; background: #141414; border-style: dashed; }

  /* Polished error card (rendered when the pipeline surfaces a recognizable
     IngestError such as a private repo or 404). Lives outside the raw log
     panel so it cannot be lost in a wall of Rich traceback text. */
  .adi-error-card {
    margin: 1rem 0 .75rem;
    padding: 1rem 1.1rem 1rem 1.1rem;
    border: 1px solid var(--adi-border2);
    border-left: 3px solid var(--adi-text2);
    border-radius: 10px;
    background: var(--adi-surface);
    color: var(--adi-text);
  }
  .adi-error-head {
    display: flex;
    align-items: center;
    gap: .55rem;
    margin-bottom: .35rem;
  }
  .adi-error-icon {
    font-size: 22px;
    line-height: 1;
    color: var(--adi-text);
    opacity: .9;
  }
  .adi-error-title {
    font-weight: 700;
    font-size: 1.02rem;
    letter-spacing: .005em;
  }
  .adi-error-body {
    color: var(--adi-text);
    font-size: .96rem;
    line-height: 1.5;
    margin: .15rem 0 .65rem;
  }
  .adi-error-hints {
    color: var(--adi-text2);
    font-size: .9rem;
    line-height: 1.55;
    border-top: 1px dashed var(--adi-border2);
    padding-top: .55rem;
  }
  .adi-error-hints strong { color: var(--adi-text); }
  .adi-error-hints ul { margin: .25rem 0 0 1.1rem; padding: 0; }
  .adi-error-hints li { margin: .15rem 0; }
  .adi-error-hints code {
    background: var(--adi-btn-bg);
    padding: 1px 6px;
    border-radius: 4px;
    font-size: .85em;
  }

  /* Feature pills */
  .adi-pill {
    display: inline-block; padding: 3px 11px; border-radius: 999px;
    font-size: .73rem; font-weight: 600; letter-spacing: .03em;
    border: 1px solid var(--adi-border2); color: var(--adi-text2);
    margin: 0 5px 8px 0;
  }

  /* Footer */
  .adi-foot {
    color: var(--adi-muted); font-size: .8rem;
    text-align: center; margin-top: 2.4rem;
    border-top: 1px solid var(--adi-border); padding-top: 1.2rem;
  }

  /* Image desaturation */
  [data-testid="stImage"] img,
  section[data-testid="stSidebar"] img {
    filter: grayscale(1) contrast(1.05) brightness(1.15);
  }

  /* ── Monochrome top-bar decoration (running indicator) ────────────────────── */
  [data-testid="stDecoration"] {
    background-image: none !important;
    background: var(--adi-border2) !important;
  }

  /* ── Monochrome alert / info / preview-mode banners ──────────────────────── */
  /* Streamlit's actual test-id is stAlertContainer; data-baseweb="notification" */
  [data-testid="stAlertContainer"],
  [data-baseweb="notification"],
  [data-testid="stAlert"],
  [data-testid="stInfo"],
  [data-testid="stWarning"],
  [data-testid="stException"] {
    background-color: var(--adi-surface) !important;
    border: 1px solid var(--adi-border2) !important;
    border-radius: 10px !important;
    color: var(--adi-text2) !important;
  }
  [data-testid="stAlertContainer"] p,
  [data-baseweb="notification"] p,
  [data-testid="stAlert"] p,
  [data-testid="stInfo"] p,
  [data-testid="stWarning"] p,
  [data-testid="stException"] p { color: var(--adi-text2) !important; }
  [data-testid="stAlertContainer"] *,
  [data-baseweb="notification"] * { color: var(--adi-text2) !important; }
  [data-testid="stAlertContainer"] svg,
  [data-baseweb="notification"] svg,
  [data-testid="stAlert"] svg,
  [data-testid="stInfo"] svg,
  [data-testid="stWarning"] svg { filter: grayscale(1) !important; opacity: .6; }

  /* ── st.status() completion/error state icons ────────────────────────────── */
  [data-testid="stStatusContainer"] svg { filter: grayscale(1) !important; }

  /* ── Input label contrast (both themes) ──────────────────────────────────── */
  .stTextInput > label, .stTextArea > label, .stSelectbox > label {
    color: var(--adi-text2) !important;
  }

  /* ── Tab icons — force grayscale (S11: unselected 0.85, selected 1.0) ───────── */
  .stTabs [data-baseweb="tab"] span[role="img"],
  .stTabs [data-baseweb="tab"] svg { filter: grayscale(1) !important; opacity: .85; }
  .stTabs [aria-selected="true"] svg,
  .stTabs [aria-selected="true"] span[role="img"] { opacity: 1; }

  /* ── Lottie components — grayscale in ALL themes (monochrome by design).
     Light mode additionally inverts dark→light in _CSS_LIGHT_OVERRIDES. ──── */
  [data-testid="stCustomComponentV1"] {
    filter: grayscale(1);
    border-radius: 12px;
    overflow: hidden;
  }

  /* ── Heading anchor links — hide (visual noise on mobile) ───────────────── */
  [data-testid="stHeadingWithActionElements"] a {
    opacity: 0 !important;
    pointer-events: none !important;
    width: 0 !important;
    overflow: hidden !important;
  }

  /* ── Sidebar collapse button: ☰ hamburger, fixed top-left ────────────────── */
  /* Positioned fixed so it floats in the header area regardless of sidebar state */
  [data-testid="stSidebarCollapseButton"] {
    display: block !important;
    opacity: 1 !important;
    visibility: visible !important;
    position: fixed !important;
    top: 12px !important;
    left: 12px !important;
    z-index: 9999 !important;
  }
  [data-testid="stSidebarCollapseButton"] button,
  button[aria-label="Close sidebar"] {
    background: var(--adi-surface) !important;
    border: 1px solid var(--adi-border2) !important;
    border-radius: 8px !important;
    transition: background .15s ease, border-color .15s ease !important;
    cursor: pointer !important;
  }
  [data-testid="stSidebarCollapseButton"] button:hover,
  button[aria-label="Close sidebar"]:hover {
    background: var(--adi-border) !important;
    border-color: var(--adi-text2) !important;
  }
  /* Hide default chevron SVG; inject ☰ hamburger via ::after */
  [data-testid="stSidebarCollapseButton"] button svg,
  button[aria-label="Close sidebar"] svg {
    display: none !important;
  }
  [data-testid="stSidebarCollapseButton"] button::after,
  button[aria-label="Close sidebar"]::after {
    content: '☰';
    font-size: 18px;
    color: var(--adi-text2);
    font-family: system-ui, sans-serif;
    pointer-events: none;
    line-height: 1;
  }

  /* ── Tooltip / help (?) icons — sized, styled, both themes ──────────────── */
  [data-testid="stTooltipIcon"] {
    display: inline-flex !important;
    align-items: center !important;
    vertical-align: middle !important;
  }
  /* form-field ? icons have no <button>; they use stTooltipHoverTarget > svg */
  [data-testid="stTooltipHoverTarget"] svg {
    width: 14px !important;
    height: 14px !important;
    color: var(--adi-text2) !important;
    opacity: 1 !important;
    flex-shrink: 0 !important;
  }
  /* ? SVG is stroke-based (Lucide). Set stroke via currentColor, never none */
  [data-testid="stTooltipHoverTarget"] svg path,
  [data-testid="stTooltipHoverTarget"] svg circle,
  [data-testid="stTooltipHoverTarget"] svg line {
    stroke: var(--adi-text2) !important;
    fill: none !important;
  }

  /* ── Theme toggle: perfect circle icon button in sidebar ─────────────────── */
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-secondary"],
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] .stButton > button {
    width: 36px !important;
    height: 36px !important;
    min-width: 36px !important;
    min-height: 36px !important;
    max-width: 36px !important;
    max-height: 36px !important;
    border-radius: 50% !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    overflow: hidden !important;
    aspect-ratio: 1 / 1 !important;
    line-height: 1 !important;
    font-size: 1.1rem !important;
    flex-shrink: 0 !important;
  }
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-secondary"] span[role="img"],
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-secondary"] svg {
    width: 18px !important;
    height: 18px !important;
    flex-shrink: 0 !important;
  }

  /* ── Custom scrollbars (webkit + Firefox) ───────────────────────────────── */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: var(--adi-scroll-track); border-radius: 3px; }
  ::-webkit-scrollbar-thumb { background: var(--adi-scroll-thumb); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { filter: brightness(1.25); }
  * { scrollbar-width: thin; scrollbar-color: var(--adi-scroll-thumb) var(--adi-scroll-track); }

  /* ── Sidebar: position as overlay on tablet/mobile so it doesn't push content */
  @media (max-width: 900px) {
    section[data-testid="stSidebar"] {
      position: fixed !important;
      top: 0; left: 0;
      height: 100dvh !important;
      z-index: 999 !important;
      box-shadow: 4px 0 24px rgba(0,0,0,.45) !important;
    }
  }

  /* ── Mobile tweaks ───────────────────────────────────────────────────────── */
  @media (max-width: 768px) {
    h1 { font-size: 2rem !important; }
    .block-container {
      padding-top: 3rem !important;
      padding-left: 1rem !important;
      padding-right: 1rem !important;
    }
    [data-testid="stSidebarCollapseButton"] button,
    button[aria-label="Close sidebar"] {
      min-width: 44px !important;
      min-height: 44px !important;
    }
  }

  /* ── Compact at low viewport heights (keeps CTA above fold at 768px height) */
  @media (max-height: 750px) {
    .block-container { padding-top: 2.5rem !important; }
  }

  /* ── Global link styles — monochrome palette, not browser-default blue ───── */
  a, a:visited { color: var(--adi-text2); text-decoration: none; }
  a:hover { color: var(--adi-text); text-decoration: underline; }
  [data-testid="stSidebar"] a {
    color: var(--adi-text2) !important;
    text-decoration: underline !important;
  }
  [data-testid="stSidebar"] a:hover {
    color: var(--adi-text) !important;
  }

  /* ── Tooltip popup — border on the OUTERMOST element only ───────────────────
     Confirmed DOM: [data-baseweb="tooltip"][role="tooltip"] is the outer card.
     Its children (plain div → stTooltipContent → stMarkdownContainer) must have
     NO border — otherwise every level gets a visible ring.                     */
  body [data-baseweb="tooltip"][role="tooltip"] {
    background-color: var(--adi-surface) !important;
    border: 1px solid var(--adi-border2) !important;
    color: var(--adi-text) !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 16px rgba(0,0,0,.15) !important;
    max-width: 320px !important;
  }
  /* All children: no border, transparent bg, inherit text colour */
  body [data-baseweb="tooltip"][role="tooltip"] * {
    border: none !important;
    background: transparent !important;
    color: var(--adi-text) !important;
  }

  /* ── Input labels: stable data-testid selectors ─────────────────────────── */
  [data-testid="stTextInput"] > label,
  [data-testid="stTextArea"] > label,
  [data-testid="stSelectbox"] > label { color: var(--adi-text2) !important; }

  /* ── Collapsed sidebar: ☰ hamburger — always visible, themed hover ──────── */
  [data-testid="stSidebarCollapsedControl"] {
    opacity: 1 !important;
    visibility: visible !important;
  }
  [data-testid="stSidebarCollapsedControl"] button {
    background: var(--adi-surface) !important;
    border: 1px solid var(--adi-border2) !important;
    border-radius: 8px !important;
    transition: background .15s ease, border-color .15s ease !important;
  }
  [data-testid="stSidebarCollapsedControl"] button:hover {
    background: var(--adi-border) !important;
    border-color: var(--adi-text2) !important;
  }
  [data-testid="stSidebarCollapsedControl"] button svg { display: none !important; }
  [data-testid="stSidebarCollapsedControl"] button::after {
    content: '☰'; font-size: 18px; color: var(--adi-text2);
    font-family: system-ui, sans-serif; pointer-events: none;
  }

  /* ── Button data-testid transitions (supplements .stButton > button rule) ── */
  button[data-testid^="stBaseButton"] {
    transition: border-color .15s ease, background .15s ease, transform .05s ease !important;
  }
  button[data-testid^="stBaseButton"]:active { transform: translateY(1px) !important; }

  /* ── Sidebar vertical separator: subtle shadow edge ─────────────────────── */
  section[data-testid="stSidebar"] {
    box-shadow: 1px 0 0 var(--adi-border) !important;
  }

  /* ── S5: Sidebar width — 280 px default; no min/max so collapse still works ── */
  section[data-testid="stSidebar"] > div:first-child {
    width: 280px !important;
  }

  /* ── S6: Smooth theme transition — fade bg + text instead of hard snap ────── */
  .stApp,
  [data-testid="stAppViewContainer"],
  section[data-testid="stSidebar"],
  section[data-testid="stSidebar"] > div,
  [data-testid="stHeader"],
  .block-container {
    transition: background-color 0.22s ease, color 0.18s ease, border-color 0.18s ease !important;
  }

  /* ── S10: Mobile overlay backdrop (hidden by default, shown via JS) ─────── */
  #adi-sidebar-backdrop {
    display: none;
    position: fixed; inset: 0;
    background: rgba(0,0,0,.4);
    z-index: 998;
    cursor: pointer;
  }
  #adi-sidebar-backdrop.visible { display: block; }

  /* ── URL validation indicator styles ─────────────────────────────────────── */
  .adi-url-ok  { color: #333333 !important; font-size: .82rem; font-weight: 600; }
  .adi-url-err { color: #888888 !important; font-size: .82rem; font-weight: 600; }
"""

# Extra Streamlit surface overrides needed ONLY in light mode.
_CSS_LIGHT_OVERRIDES = """
  /* Force Streamlit's dark-theme surfaces to light */
  .stApp,
  [data-testid="stAppViewContainer"],
  .main { background-color: var(--adi-bg) !important; }

  [data-testid="stHeader"] {
    background-color: rgba(248,248,248,0.95) !important;
    border-bottom: 1px solid var(--adi-border) !important;
    box-shadow: none !important;
  }
  section[data-testid="stSidebar"] > div {
    background-color: var(--adi-sidebar) !important;
  }

  /* Text — Streamlit's dark theme hard-codes light text; override all of it */
  p, .stMarkdown p, label,
  li, ul li, ol li,
  [data-testid="stMarkdown"] li,
  [data-testid="stMarkdownContainer"] li { color: var(--adi-text) !important; }
  .stCaption p { color: var(--adi-text2) !important; }
  h1, h2, h3, h4, h5, h6 { color: var(--adi-text) !important; }
  [data-testid="stHeadingWithActionElements"] h1,
  [data-testid="stHeadingWithActionElements"] h2,
  [data-testid="stHeadingWithActionElements"] h3 { color: var(--adi-text) !important; }
  /* Streamlit title widget */
  [data-testid="stMarkdownContainer"] p { color: var(--adi-text) !important; }
  [data-testid="stMarkdownContainer"] h1 { color: var(--adi-text) !important; }

  /* ── Fix: Inline code tokens get dark-theme black bg in light mode ───────
     :not(pre)>code targets backtick spans inside p/li — excludes fenced blocks */
  :not(pre) > code {
    background-color: var(--adi-code-bg) !important;
    color: var(--adi-text) !important;
    border: 1px solid var(--adi-border2) !important;
    border-radius: 4px !important;
  }
  [data-testid="stMarkdownContainer"] p code,
  [data-testid="stMarkdownContainer"] li code {
    background-color: var(--adi-code-bg) !important;
    color: var(--adi-text) !important;
    border: 1px solid var(--adi-border2) !important;
    border-radius: 4px !important;
  }

  /* Expanders */
  [data-testid="stExpander"] details {
    border-color: var(--adi-border) !important;
    background-color: var(--adi-surface) !important;
  }
  [data-testid="stExpander"] summary p { color: var(--adi-text) !important; }

  /* Info / alert banner — monochrome in light mode (real testid: stAlertContainer) */
  [data-testid="stAlertContainer"],
  [data-baseweb="notification"],
  [data-testid="stInfo"] {
    background-color: var(--adi-surface) !important;
    border-color: var(--adi-border2) !important;
  }
  [data-testid="stAlertContainer"] *,
  [data-baseweb="notification"] *,
  [data-testid="stAlertContainer"] p,
  [data-baseweb="notification"] p,
  [data-testid="stInfo"] p { color: var(--adi-text2) !important; }

  /* ── Fix: BaseWeb elements inherit dark-theme white text in light mode ─────
     Streamlit's dark base sets color:rgb(245,245,245) on [data-baseweb] roots;
     the light override CSS doesn't reach these — force them to adi-text. */
  [data-baseweb="select"],
  [data-baseweb="base-input"],
  [data-baseweb="input"],
  [data-baseweb="checkbox"],
  [data-baseweb="icon"],
  [data-baseweb="select"] *,
  [data-baseweb="tag"] { color: var(--adi-text) !important; }

  /* Selectbox dropdown popup / options list */
  [data-baseweb="popover"],
  [data-baseweb="menu"] {
    background-color: var(--adi-surface) !important;
    border: 1px solid var(--adi-border2) !important;
    border-radius: 10px !important;
  }
  [data-baseweb="option"] {
    background-color: var(--adi-surface) !important;
    color: var(--adi-text) !important;
  }
  [data-baseweb="option"]:hover,
  [data-baseweb="option"][aria-selected="true"] {
    background-color: var(--adi-border) !important;
    color: var(--adi-text) !important;
  }

  /* ── Fix: Theme toggle — Streamlit uses [data-baseweb="checkbox"], NOT
     [role="switch"]. Track child-div gets primaryColor=#fafafa which is
     invisible on light bg. Use :has() to target checked vs unchecked state. */
  [data-baseweb="checkbox"] > div:first-child {
    background-color: var(--adi-border2) !important;
    border-color: var(--adi-border2) !important;
  }
  [data-baseweb="checkbox"]:has(input[aria-checked="true"]) > div:first-child {
    background-color: #333333 !important;
    border-color: #333333 !important;
  }
  /* Checkmark tick inside track should be white on the dark track */
  [data-baseweb="checkbox"]:has(input[aria-checked="true"]) > div:first-child > div {
    border-color: #ffffff !important;
    background-color: transparent !important;
  }

  /* ── Password eye icon: light-mode SVG colour boost (bg/border in STRUCTURAL) */
  [data-testid="stTextInput"] button svg,
  [data-testid="stTextInput"] button svg *,
  button[aria-label="Show password text"] svg,
  button[aria-label="Show password text"] svg *,
  button[aria-label="Hide password text"] svg,
  button[aria-label="Hide password text"] svg * {
    fill: var(--adi-text) !important;
    color: var(--adi-text) !important;
    stroke: var(--adi-text) !important;
  }

  /* ── Fix: Primary button text visibility (all states including disabled) ─── */
  /* Includes the form-submit variant: when the primary button lives inside
     st.form(...) it ships as .stFormSubmitButton, NOT .stButton, so previous
     rules silently fell through and produced white text on the white pill. */
  .stButton > button[kind="primary"],
  .stButton > button[kind="primary"]:hover,
  .stButton > button[kind="primary"]:focus,
  .stButton > button[kind="primary"]:active,
  .stButton > button[kind="primary"][disabled],
  .stFormSubmitButton > button[kind="primary"],
  .stFormSubmitButton > button[kind="primary"]:hover,
  .stFormSubmitButton > button[kind="primary"]:focus,
  .stFormSubmitButton > button[kind="primary"]:active,
  .stFormSubmitButton > button[kind="primary"][disabled],
  [data-testid="stFormSubmitButton"] button[kind="primary"],
  button[data-testid="stBaseButton-primaryFormSubmit"] {
    background-color: var(--adi-primary-bg) !important;
    color: var(--adi-primary-text) !important;
    border-color: var(--adi-primary-bg) !important;
  }
  .stButton > button[kind="primary"] p,
  .stButton > button[kind="primary"] span,
  .stButton > button[kind="primary"] *,
  .stFormSubmitButton > button[kind="primary"] p,
  .stFormSubmitButton > button[kind="primary"] span,
  .stFormSubmitButton > button[kind="primary"] *,
  [data-testid="stFormSubmitButton"] button[kind="primary"] *,
  button[data-testid="stBaseButton-primaryFormSubmit"] * {
    color: var(--adi-primary-text) !important;
  }

  /* ── Fix: Placeholder text visibility in inputs ──────────────────────── */
  .stTextArea textarea::placeholder,
  .stTextInput input::placeholder {
    color: #999999 !important;
    opacity: 1 !important;
  }
  /* Selectbox text color */
  .stSelectbox [data-baseweb="select"] [data-testid="stMarkdownContainer"] p {
    color: var(--adi-text) !important;
  }

  /* Lottie: grayscale first (strips any colored lottie), then invert dark→light.
     grayscale(1) prevents colored lotties (explain-geo, improve-star) from
     inverting to wrong hues (green → pink). border-radius = intentional dark card. */
  [data-testid="stCustomComponentV1"] {
    filter: grayscale(1) invert(0.88);
    border-radius: 12px;
    overflow: hidden;
  }

  /* ── All secondary buttons: force light bg in light mode ────────────────────
     Streamlit's base="dark" config injects its own dark button CSS with high
     specificity; we override via [data-testid] to win the cascade. */
  button[data-testid="stBaseButton-secondary"] {
    background-color: var(--adi-btn-bg) !important;
    color: var(--adi-btn-text) !important;
    border-color: var(--adi-border2) !important;
  }
  button[data-testid="stBaseButton-secondary"]:hover {
    border-color: var(--adi-text2) !important;
  }

  /* ── Theme toggle button: perfect circle + DOM-agnostic centred icon ──────── */
  /* The button is a 40x40 grid container with `place-items: center`, so any
     descendant Streamlit injects -- a div wrapper, a <p>, a Material span, an
     <svg> -- lands at the geometric centre regardless of the inner markup. */
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-secondary"] {
    background-color: var(--adi-surface) !important;
    color: var(--adi-text) !important;
    border: 1.5px solid var(--adi-border2) !important;
    width: 40px !important;
    height: 40px !important;
    min-width: 40px !important;
    min-height: 40px !important;
    padding: 0 !important;
    border-radius: 50% !important;
    display: grid !important;
    place-items: center !important;
    line-height: 1 !important;
    margin-left: auto !important;
    overflow: hidden !important;  /* keep stray inner-wrapper edges inside the circle */
  }
  /* Every descendant: zero own margin/padding, collapse to its content size,
     and centre its own children too. Belt-and-braces against future Streamlit
     wrapper changes. */
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-secondary"] *,
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-secondary"] > * {
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1 !important;
    display: grid !important;
    place-items: center !important;
    text-align: center !important;
    width: auto !important;
    height: auto !important;
  }
  /* Pin the Material glyph itself to a fixed size and nudge it down 1 px for
     optical centring (baseline metrics include a descender slack the visible
     drawing does not use). */
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-secondary"] span[class*="material"],
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-secondary"] .material-symbols-outlined,
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-secondary"] .material-icons,
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-secondary"] svg {
    font-size: 20px !important;
    line-height: 1 !important;
    transform: translateY(1px) !important;
  }
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-secondary"]:hover {
    border-color: var(--adi-text2) !important;
  }
  /* Round focus ring + remove every default outline source (browser default
     :focus, Streamlit's primary-coloured :focus-visible, OS accent ring). */
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-secondary"]:focus,
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-secondary"]:focus-visible,
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-secondary"]:focus-within {
    outline: 0 none transparent !important;
    outline-offset: 0 !important;
    box-shadow: 0 0 0 2px var(--adi-text2) !important;
    border-color: var(--adi-text) !important;
  }
  /* Also kill the outline on the .stButton wrapper, which Streamlit sometimes
     receives :focus-within and re-paints with its primary outline. */
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] .stButton:focus,
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] .stButton:focus-within,
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] .stButton:focus-visible {
    outline: 0 none transparent !important;
    box-shadow: none !important;
  }
  /* Make the parent column hug the round button so the focus ring stays round
     instead of stretching across the column's full width. */
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:has(button[data-testid="stBaseButton-secondary"][aria-describedby*="adi_theme"]),
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:has(button[data-testid="stBaseButton-secondary"]) {
    flex: 0 0 auto !important;
    width: 40px !important;
    min-width: 40px !important;
    max-width: 40px !important;
    display: flex !important;
    justify-content: flex-end !important;
    align-items: center !important;
  }
  /* Wrapper Streamlit injects directly inside the column also needs to collapse,
     otherwise the .stButton wrapper inherits the full column width and the focus
     ring renders as a wide rounded rectangle around an inner round button. */
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] .stButton:has(button[data-testid="stBaseButton-secondary"]) {
    width: 40px !important;
    min-width: 40px !important;
    max-width: 40px !important;
    display: inline-block !important;
  }

  /* ── Question mark / tooltip icons — force visible in light mode ──────────
     ? icons use stroke-based Lucide SVG (fill="none" stroke="currentColor").
     Only override the color via stroke; never set stroke:none (erases the ?). */
  [data-testid="stTooltipHoverTarget"] svg {
    color: var(--adi-text2) !important;
    opacity: 1 !important;
  }
  [data-testid="stTooltipHoverTarget"] svg path,
  [data-testid="stTooltipHoverTarget"] svg circle,
  [data-testid="stTooltipHoverTarget"] svg line {
    stroke: var(--adi-text2) !important;
    fill: none !important;
  }

  /* ── Tooltip popup: light-mode override — outer card only, children clean ─── */
  body [data-baseweb="tooltip"][role="tooltip"] {
    background-color: #ffffff !important;
    border: 1px solid #d0d0d0 !important;
    color: #111111 !important;
  }
  body [data-baseweb="tooltip"][role="tooltip"] * {
    color: #111111 !important;
    border: none !important;
    background: transparent !important;
  }

  /* ── Typing cursor (caret) visible in inputs ─────────────────────────────── */
  .stTextInput input,
  .stTextArea textarea,
  [data-baseweb="base-input"] input,
  [data-baseweb="base-input"] textarea {
    caret-color: var(--adi-text) !important;
    color: var(--adi-text) !important;
  }

  /* ── LLM provider dropdown: nuclear override ─────────────────────────────── */
  /* Select input trigger */
  [data-baseweb="select"] > div,
  [data-baseweb="select"] > div > div,
  [data-baseweb="select"] [role="button"],
  [data-baseweb="select"] [role="combobox"] {
    background-color: var(--adi-input-bg) !important;
    color: var(--adi-text) !important;
  }
  /* Dropdown portal (rendered at body level) — body prefix wins specificity war */
  body [data-baseweb="popover"],
  body [data-baseweb="popover"] > div,
  body [data-baseweb="menu"] {
    background-color: var(--adi-surface) !important;
    border: 1px solid var(--adi-border2) !important;
    border-radius: 10px !important;
  }
  body li[role="option"],
  body [data-baseweb="option"] {
    background-color: var(--adi-surface) !important;
    color: var(--adi-text) !important;
  }
  body li[role="option"]:hover,
  body li[role="option"][aria-selected="true"],
  body [data-baseweb="option"]:hover,
  body [data-baseweb="option"][aria-selected="true"] {
    background-color: var(--adi-border) !important;
    color: var(--adi-text) !important;
  }
  body [data-baseweb="option"] *,
  body [data-baseweb="option"] span,
  body [data-baseweb="option"] p { color: var(--adi-text) !important; }

  /* ── Code blocks: clean single-card design (light mode) ─────────────────── */
  /* One white card at the outer stCodeBlock boundary — zero nested boxes.
     All inner emotion-generated wrappers collapse to transparent so only the
     outer border/shadow is visible.  Syntax-highlight span colours (diff
     red/green) are unaffected because they're set directly on child spans.    */

  /* Outer container — the ONE styled surface */
  div[data-testid="stCodeBlock"] {
    background: #ffffff !important;
    border: 1px solid #e0e0e0 !important;
    border-radius: 10px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07) !important;
  }
  /* Inner emotion wrappers + plain div layers → transparent, no borders
     (kills both the double-box AND the per-line separator that appears when
     Streamlit's toolbar-row border-bottom is exposed by a transparent bg)    */
  div[data-testid="stCodeBlock"] [class*="st-emotion-cache"],
  div[data-testid="stCodeBlock"] > div,
  div[data-testid="stCodeBlock"] > div > div,
  div[data-testid="stCodeBlock"] > div > div > div {
    background: transparent !important;
    border-top: none !important;
    border-bottom: none !important;
  }
  /* pre + code: transparent so outer white shows through; text pure near-black */
  div[data-testid="stCodeBlock"] pre,
  div[data-testid="stCodeBlock"] code,
  div[data-testid="stCodeBlock"] pre code {
    background: transparent !important;
    color: #111111 !important;
    border: none !important;
  }
  /* Spans inside code (syntax-highlight tokens): no borders, strict B&W colours */
  div[data-testid="stCodeBlock"] pre span,
  div[data-testid="stCodeBlock"] code span {
    border: none !important;
    border-bottom: none !important;
  }
  /* Diff token colours → B&W only (deleted = grey, inserted = near-black) */
  div[data-testid="stCodeBlock"] .token.deleted,
  div[data-testid="stCodeBlock"] .hljs-deletion,
  div[data-testid="stCodeBlock"] span[class*="deleted"] {
    color: #888888 !important;
  }
  div[data-testid="stCodeBlock"] .token.inserted,
  div[data-testid="stCodeBlock"] .hljs-addition,
  div[data-testid="stCodeBlock"] span[class*="inserted"] {
    color: #111111 !important;
  }

  /* Fenced blocks inside st.markdown — emotion wrapper IS the card here.
     Padding goes on the wrapper (not pre) to avoid double-padding.           */
  [data-testid="stMarkdownContainer"] [class*="st-emotion-cache"]:has(pre) {
    background: #ffffff !important;
    border: 1px solid #e0e0e0 !important;
    border-radius: 10px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07) !important;
    padding: 1rem !important;
  }
  [data-testid="stMarkdownContainer"] pre {
    background: transparent !important;
    margin: 0 !important;
    border: none !important;
  }
  [data-testid="stMarkdownContainer"] pre code {
    background: transparent !important;
    color: #111111 !important;
    border: none !important;
  }
  /* No per-line separators on markdown spans */
  [data-testid="stMarkdownContainer"] pre span {
    border: none !important;
  }
  /* Diff tokens in markdown fenced blocks: same B&W treatment */
  [data-testid="stMarkdownContainer"] .token.deleted,
  [data-testid="stMarkdownContainer"] .hljs-deletion,
  [data-testid="stMarkdownContainer"] span[class*="deleted"] {
    color: #888888 !important;
  }
  [data-testid="stMarkdownContainer"] .token.inserted,
  [data-testid="stMarkdownContainer"] .hljs-addition,
  [data-testid="stMarkdownContainer"] span[class*="inserted"] {
    color: #111111 !important;
  }

  /* ── Inline code spans (backtick `code` in markdown / Last Run URL) ──────── */
  /* The emotion class hardcodes background:rgb(16,16,16). Override it here.    */
  :not(pre) > code {
    background: #e8e8e8 !important;
    color: #111111 !important;
    border: 1px solid #d0d0d0 !important;
    border-radius: 4px !important;
  }

  /* ── Suggestion / explanation result text ────────────────────────────────── */
  [data-testid="stMarkdownContainer"] {
    color: var(--adi-text) !important;
  }
  [data-testid="stMarkdownContainer"] strong,
  [data-testid="stMarkdownContainer"] b {
    color: var(--adi-text) !important;
  }
  [data-testid="stMarkdownContainer"] a {
    color: var(--adi-text2) !important;
    text-decoration: underline !important;
  }
  /* Ensure headings inside result output are dark */
  [data-testid="stMarkdownContainer"] h1,
  [data-testid="stMarkdownContainer"] h2,
  [data-testid="stMarkdownContainer"] h3,
  [data-testid="stMarkdownContainer"] h4 { color: var(--adi-text) !important; }

  /* ── Status badges: strict B&W in light mode — no hues, distinguish by weight */
  .adi-badge.ok  { color: #333333 !important; border-color: #999999 !important; background: #f5f5f5 !important; border-style: solid !important; }
  .adi-badge.err { color: #777777 !important; border-color: #cccccc !important; background: #f8f8f8 !important; border-style: dashed !important; }

  /* ── Disabled primary button: legible in light mode ─────────────────────── */
  button[data-testid="stBaseButton-primary"][disabled] {
    opacity: 0.45 !important;
    cursor: not-allowed !important;
  }

  /* ── Collapsed sidebar open-button: light mode surface ─────────────────── */
  [data-testid="stSidebarCollapsedControl"] button {
    background: var(--adi-surface) !important;
    border-color: var(--adi-border2) !important;
  }
  [data-testid="stSidebarCollapsedControl"] button::after {
    color: var(--adi-text2) !important;
  }

  /* ── Placeholder text: adequate contrast in light mode ─────────────────── */
  .stTextInput input::placeholder,
  .stTextArea textarea::placeholder {
    color: var(--adi-muted) !important;
    opacity: 1 !important;
  }
"""


def _inject_css() -> None:
    theme = _theme()
    if theme == "light":
        css = f"<style>{_CSS_VARS_LIGHT}{_CSS_STRUCTURAL}{_CSS_LIGHT_OVERRIDES}</style>"
    else:
        css = f"<style>{_CSS_VARS_DARK}{_CSS_STRUCTURAL}</style>"
    st.markdown(css, unsafe_allow_html=True)


def _inject_js() -> None:
    """Inject JS utilities:
    - Auto-collapse sidebar on narrow viewports (once per tab).
    - S1: Restore theme preference from localStorage on fresh sessions.
    - S10: Mobile overlay backdrop that closes sidebar on outside click.
    """
    st.markdown(
        """<script>
(function(){
  /* ── Auto-collapse on mobile ──────────────────────────────────────────── */
  if(window.innerWidth<=900){
    if(!sessionStorage.getItem('adi_sc')){
      function tryClose(){
        var b=document.querySelector('button[aria-label="Close sidebar"]');
        if(!b)b=document.querySelector('[data-testid="stSidebarCollapseButton"] button');
        if(b){b.click();sessionStorage.setItem('adi_sc','1');return true;}
        return false;
      }
      if(!tryClose()){var n=0,t=setInterval(function(){if(tryClose()||++n>14)clearInterval(t);},220);}
    }
  }

  /* ── S1: Theme persistence via localStorage ───────────────────────────── */
  /* On a fresh session (no sessionStorage marker), auto-apply saved pref.   */
  var LSKEY='adi_theme_pref', SSKEY='adi_theme_init';
  if(!sessionStorage.getItem(SSKEY)){
    sessionStorage.setItem(SSKEY,'1');
    var savedPref=localStorage.getItem(LSKEY);
    /* savedPref='light' means user last left it in light mode.              */
    /* The app always starts in dark (default). If pref=light, click toggle. */
    if(savedPref==='light'){
      function applyLight(){
        var btns=Array.from(document.querySelectorAll(
          '[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]'));
        var btn=btns.find(function(b){return b.offsetParent!==null;});
        /* Check CSS var to confirm we're in dark mode before clicking */
        var curBg=getComputedStyle(document.documentElement)
          .getPropertyValue('--adi-bg').trim();
        if(btn&&curBg!=='#f8f8f8'){btn.click();return true;}
        return !!(btn);
      }
      if(!applyLight()){var m=0,u=setInterval(function(){if(applyLight()||++m>25)clearInterval(u);},180);}
    }
  }
  /* Save preference whenever the toggle button is clicked */
  document.addEventListener('click',function(e){
    var btn=e.target&&e.target.closest&&e.target.closest(
      '[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]');
    if(btn){
      /* After click mode will flip; record what it's flipping TO */
      var curBg=getComputedStyle(document.documentElement)
        .getPropertyValue('--adi-bg').trim();
      localStorage.setItem(LSKEY,curBg==='#f8f8f8'?'dark':'light');
    }
  },true);

  /* ── S10: Mobile sidebar overlay backdrop ─────────────────────────────── */
  if(window.innerWidth<=900){
    function ensureBackdrop(){
      if(document.getElementById('adi-sidebar-backdrop'))return;
      var bd=document.createElement('div');
      bd.id='adi-sidebar-backdrop';
      document.body.appendChild(bd);
      bd.addEventListener('click',function(){
        var closeBtn=document.querySelector('button[aria-label="Close sidebar"]');
        if(closeBtn)closeBtn.click();
        bd.classList.remove('visible');
      });
    }
    /* Show/hide backdrop based on sidebar state */
    function watchSidebar(){
      ensureBackdrop();
      var sidebar=document.querySelector('section[data-testid="stSidebar"]');
      var bd=document.getElementById('adi-sidebar-backdrop');
      if(!sidebar||!bd)return;
      var isOpen=sidebar.offsetWidth>50;
      isOpen?bd.classList.add('visible'):bd.classList.remove('visible');
    }
    if(document.readyState==='loading'){
      document.addEventListener('DOMContentLoaded',function(){
        setTimeout(watchSidebar,500);
      });
    }else{setTimeout(watchSidebar,500);}
    /* Re-check after any Streamlit rerun mutates the DOM */
    var obs=new MutationObserver(function(){watchSidebar();});
    setTimeout(function(){
      var target=document.querySelector('[data-testid="stAppViewContainer"]');
      if(target)obs.observe(target,{childList:true,subtree:true,attributes:true,attributeFilter:['style']});
    },1000);
  }
})();
</script>""",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────── Lottie helpers
def _load_lottie(name: str):
    """Load a bundled Lottie JSON by filename; return None on any failure."""
    try:
        path = ANIM / name
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _render_lottie(
    name: str,
    *,
    height: int,
    key: str,
    loop: bool = True,
    speed: float = 1.0,
) -> bool:
    """Render a bundled Lottie animation. Returns True if successful."""
    data = _load_lottie(name)
    if data is None:
        return False
    try:
        from streamlit_lottie import st_lottie
        st_lottie(data, height=height, loop=loop, speed=speed, quality="high", key=key)
        return True
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────── Inline icons
# Lucide-style SVG paths (stroke=currentColor, no fill) used in section headers.
_ICONS: dict[str, str] = {
    "settings": (
        '<line x1="21" x2="14" y1="4" y2="4"/>'
        '<line x1="10" x2="3" y1="4" y2="4"/>'
        '<line x1="21" x2="12" y1="12" y2="12"/>'
        '<line x1="8" x2="3" y1="12" y2="12"/>'
        '<line x1="21" x2="16" y1="20" y2="20"/>'
        '<line x1="12" x2="3" y1="20" y2="20"/>'
        '<line x1="14" x2="14" y1="2" y2="6"/>'
        '<line x1="8" x2="8" y1="10" y2="14"/>'
        '<line x1="16" x2="16" y1="18" y2="22"/>'
    ),
    "book": (
        '<path d="M12 7v14"/>'
        '<path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4'
        ' 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3'
        ' 3 3 0 0 0-3-3z"/>'
    ),
    "sparkle": (
        '<path d="M9.94 15.5A2 2 0 0 0 8.5 14.06l-6.14-1.58a.5.5 0 0 1 0-.96'
        'L8.5 9.94A2 2 0 0 0 9.94 8.5l1.58-6.14a.5.5 0 0 1 .96 0L14.06 8.5'
        'A2 2 0 0 0 15.5 9.94l6.14 1.58a.5.5 0 0 1 0 .96L15.5 14.06a2 2 0 0 0'
        '-1.44 1.44l-1.58 6.14a.5.5 0 0 1-.96 0z"/>'
        '<path d="M20 3v4"/><path d="M22 5h-4"/>'
        '<path d="M4 17v2"/><path d="M5 18H3"/>'
    ),
    "package": (
        '<path d="m7.5 4.27 9 5.15"/>'
        '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8'
        'v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/>'
        '<path d="m3.3 7 8.7 5 8.7-5"/>'
        '<path d="M12 22V12"/>'
    ),
    "activity": (
        '<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0'
        'L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>'
    ),
    "folder": (
        '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9'
        'L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>'
    ),
    "file": (
        '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>'
        '<path d="M14 2v4a2 2 0 0 0 2 2h4"/>'
        '<path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/>'
    ),
    "list": (
        '<path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/>'
        '<path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/>'
    ),
    "layers": (
        '<path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83'
        'l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/>'
        '<path d="m6.08 9.5-3.49 1.59a1 1 0 0 0 0 1.83l8.59 3.91a2 2 0 0 0'
        ' 1.66 0l8.58-3.9a1 1 0 0 0 0-1.84L17.92 9.5"/>'
        '<path d="m6.08 14.5-3.49 1.59a1 1 0 0 0 0 1.83l8.59 3.91a2 2 0 0 0'
        ' 1.66 0l8.58-3.9a1 1 0 0 0 0-1.84L17.92 14.5"/>'
    ),
}


def _icon(name: str) -> str:
    paths = _ICONS.get(name, "")
    return (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'
        f"{paths}</svg>"
    )


def _section_header(icon: str, title: str, sub: str = "") -> None:
    sub_html = f'<div class="adi-sub">{sub}</div>' if sub else ""
    st.markdown(
        f'<div class="adi-sechead"><span class="ico">{icon}</span>{title}</div>{sub_html}',
        unsafe_allow_html=True,
    )


# ────────────────────────────────────────────────────────────── Utility helpers
@st.cache_data(ttl=60, show_spinner=False)
def _docker_available(docker_bin: str) -> bool:
    try:
        out = subprocess.run(
            shlex.split(docker_bin) + ["version", "--format", "{{.Server.Version}}"],
            capture_output=True, text=True, timeout=5,
        )
        return out.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _secrets_into_env(env: dict) -> None:
    """Copy Streamlit Cloud secrets into env dict if a secrets file is present."""
    secret_paths = (
        Path.home() / ".streamlit" / "secrets.toml",
        Path.cwd() / ".streamlit" / "secrets.toml",
    )
    if not any(p.exists() for p in secret_paths):
        return
    try:
        for key in ("GROQ_API_KEY", "GEMINI_API_KEY", "LLM_PROVIDER"):
            try:
                val = st.secrets[key]
            except (KeyError, FileNotFoundError):
                continue
            if val and key not in env:
                env[key] = str(val)
    except Exception:
        pass


def _valid_github_url(url: str) -> bool:
    try:
        p = urlparse(url)
    except ValueError:
        return False
    if p.scheme not in ("http", "https"):
        return False
    if p.hostname not in ("github.com", "www.github.com"):
        return False
    parts = [s for s in p.path.split("/") if s]
    if len(parts) < 2:
        return False
    owner, repo = parts[0], parts[1].removesuffix(".git")
    if not owner.replace("-", "").replace("_", "").isalnum():
        return False
    return repo.replace("-", "").replace("_", "").replace(".", "").isalnum()


# ──────────────────────────────────────────────────────────────── Main render
def render() -> None:
    # Theme-aware logo: dark mode → white-on-transparent; light → black-on-transparent
    _is_light   = st.session_state.get("adi_theme_toggle", False)
    _logo_file  = "logo.svg" if _is_light else "logo-dark.svg"
    logo_path   = ASSETS / _logo_file
    if not logo_path.exists():          # graceful fallback if dark variant missing
        logo_path = ASSETS / "logo.svg"
    favicon_path = ASSETS / "favicon.svg"
    # Favicon always black-on-transparent (browser tab chrome is always light)
    _favicon_base = ASSETS / "logo.svg"
    page_icon = (
        str(favicon_path)   if favicon_path.exists()
        else str(_favicon_base) if _favicon_base.exists()
        else ":material/directions_boat:"
    )
    st.set_page_config(
        page_title="Auto-Dock It | Agentic Dockerfile Generator",
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state="auto",
        menu_items={
            "Get Help": "https://github.com/MelvinJoshua1375/auto-dock-it",
            "Report a bug": "https://github.com/MelvinJoshua1375/auto-dock-it/issues",
            "About": "Auto-Dock It: LLM-driven Dockerfile generator with a self-healing build loop.",
        },
    )

    # CSS is injected before any widgets so the theme is applied on every re-run.
    _inject_css()
    _inject_js()

    # ── Hero ──────────────────────────────────────────────────────────────── #
    col_text, _gap, col_anim = st.columns([5, 1, 4], gap="medium")
    with col_text:
        st.markdown('<div class="adi-eyebrow">Agentic developer tooling</div>', unsafe_allow_html=True)
        st.title("Auto-Dock It")
        st.markdown(
            '<p style="font-size:1.08rem;line-height:1.6;color:var(--adi-text2);">'
            "Point it at any public GitHub repository and Auto-Dock It infers the "
            "runtime, writes a production-grade Dockerfile, builds it, and "
            "self-heals through failures - all driven by an LLM."
            "</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="margin-top:.5rem;">'
            '<span class="adi-pill">Self-healing build loop</span>'
            '<span class="adi-pill">LLM-powered analysis</span>'
            '<span class="adi-pill">Zero config</span>'
            '<span class="adi-pill">GitHub &rarr; Dockerfile</span>'
            "</div>",
            unsafe_allow_html=True,
        )
    with col_anim:
        # hero-ai.json: AI person + robot (File C, colour-remapped to B&W).
        # Fall back to hero-containers, then to the static logo, if a Lottie
        # asset is missing or fails to render.
        if (
            not _render_lottie("hero-ai.json", height=230, key="hero_ai")
            and not _render_lottie("hero-containers.json", height=140, key="hero_containers")
            and logo_path.exists()
        ):
            st.image(str(logo_path), width=92)

    # ── Sidebar ───────────────────────────────────────────────────────────── #
    with st.sidebar:
        # Top row: logo (left) + round theme-toggle button (right).
        _logo_col, _toggle_col = st.columns([4, 1])
        with _logo_col:
            if logo_path.exists():
                st.image(str(logo_path), width=44)
        with _toggle_col:
            _is_light = st.session_state.get("adi_theme_toggle", False)
            if st.button(
                ":material/dark_mode:" if _is_light else ":material/light_mode:",
                key="adi_theme_btn",
                help="Switch to dark mode" if _is_light else "Switch to light mode",
            ):
                st.session_state["adi_theme_toggle"] = not _is_light
                st.rerun()

        st.markdown("---")

        _section_header(_icon("settings"), "Settings", "Provider, keys, Docker binary.")

        provider_choice = st.selectbox(
            "LLM provider",
            ["groq", "gemini"],
            index=0 if os.environ.get("LLM_PROVIDER", "groq") == "groq" else 1,
        )
        user_key = st.text_input(
            f"Your {provider_choice} API key (optional)",
            type="password",
            placeholder="paste to use your own key",
            help=(
                "Providing your own key removes rate limits for this session. "
                "Without a key the app uses a shared key with strict daily caps."
            ),
        )
        # S7: Subtle visual divider separating LLM group from Docker binary field
        st.markdown(
            '<hr style="margin:8px 0 4px;border:none;border-top:1px solid var(--adi-border)">',
            unsafe_allow_html=True,
        )
        docker_bin = st.text_input(
            "DOCKER_BIN",
            value=os.environ.get("DOCKER_BIN", "docker"),
            help="Leave as 'docker' on a standard install. "
                 "Set to 'flatpak-spawn --host docker' inside a VSCode flatpak.",
        )

        st.markdown("---")
        st.markdown(
            "**Free API keys:**\n"
            "- [Groq](https://console.groq.com/keys) — higher daily limit\n"
            "- [Gemini](https://aistudio.google.com/apikey)"
        )

    # ── Preview mode banner ───────────────────────────────────────────────── #
    preview_mode = not _docker_available(docker_bin)
    if preview_mode:
        st.info(
            "**Preview mode** - Docker is not reachable from this environment. "
            "The pipeline will run ingest, analyze, and generate only. "
            "Clone the repo and run `autodock run <url>` locally for the full "
            "self-healing containerization flow."
        )

    # ── Tabs ──────────────────────────────────────────────────────────────── #
    tab_containerize, tab_explain, tab_improve = st.tabs([
        ":material/deployed_code:  Containerize",
        ":material/menu_book:  Explain",
        ":material/auto_awesome:  Improve",
    ])

    with tab_explain:
        _render_explain(provider_choice, user_key)
    with tab_improve:
        _render_improve(provider_choice, user_key)
    with tab_containerize:
        _render_containerize(provider_choice, user_key, docker_bin, preview_mode)

    # ── Footer — S12: tech stack attribution ─────────────────────────────── #
    st.markdown(
        '<div class="adi-foot">'
        "Auto-Dock It &mdash; agentic Dockerfile generation &middot; "
        "Built with "
        '<a href="https://streamlit.io" target="_blank" rel="noopener">Streamlit</a>'
        " &middot; "
        '<a href="https://groq.com" target="_blank" rel="noopener">Groq</a>'
        " &middot; "
        '<a href="https://ai.google.dev" target="_blank" rel="noopener">Gemini</a>'
        " &middot; "
        '<a href="https://github.com/MelvinJoshua1375/auto-dock-it" target="_blank" rel="noopener">'
        "GitHub</a>"
        "</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────── LLM factory
def _build_llm(provider: str, user_key: str):
    """Construct an LLM scoped to this request. Never mutates os.environ."""
    from .config import load_settings
    from .llm import LLM
    overrides: dict = {"LLM_PROVIDER": provider}
    if user_key.strip():
        overrides[f"{provider.upper()}_API_KEY"] = user_key.strip()
    settings = load_settings(overrides=overrides)
    return LLM(settings)


# ──────────────────────────────────────────────────────────────── Tab renders

def _show_llm_result(result: str, kind: str, lottie_key: str) -> None:
    """Render a stored LLM result (explanation or improvements) from session_state.

    Extracted so both the live render and the persistent re-render call the same
    code. `kind` is 'Explanation' or 'Suggestions'. `lottie_key` must be unique.
    """
    import json as _json

    import streamlit.components.v1 as _c1

    res_col_anim, res_col_text, res_col_copy = st.columns([1, 6, 1], gap="small")
    with res_col_anim:
        _render_lottie("check-done.json", height=70, key=lottie_key, loop=False)
    with res_col_text:
        st.markdown(f"**{kind}**")
    # S3: Copy-to-clipboard — rendered inside a sandboxed iframe via components.html()
    # so Streamlit's DOMPurify sanitizer never sees the onclick handler.
    # json.dumps() safely encodes the multi-line result text as a JS string literal.
    with res_col_copy:
        dark = _theme()
        border = "rgba(255,255,255,0.22)" if dark else "rgba(0,0,0,0.18)"
        color  = "#aaa"                   if dark else "#666"
        hover  = "rgba(255,255,255,0.08)" if dark else "rgba(0,0,0,0.06)"
        # f-strings handle CSS vars ({{→{ in f-string context); plain + for JS payload
        # so LLM result text containing "%" never trips %-format substitution.
        btn_css = (
            "<style>"
            "*{box-sizing:border-box;margin:0;padding:0}"
            f"button{{background:transparent;border:1px solid {border};"
            f"border-radius:6px;padding:4px 10px;cursor:pointer;font-size:.82rem;"
            f"color:{color};transition:border-color .15s,background .15s;"
            "font-family:system-ui,sans-serif;width:100%}"
            f"button:hover{{background:{hover};border-color:{color}}}"
            "</style>"
        )
        btn_script = (
            "<script>"
            + "var txt=" + _json.dumps(result) + ";"
            + "function doCopy(){"
            "navigator.clipboard&&navigator.clipboard.writeText(txt).then(function(){"
            "var b=document.getElementById('b');"
            "b.textContent='✓';"
            "setTimeout(function(){b.innerHTML='&#x29C9;';},1200);"
            "});}"
            + "</script>"
        )
        btn_html = (
            btn_css
            + "<button id='b' onclick='doCopy()' title='Copy to clipboard'>&#x29C9;</button>"
            + btn_script
        )
        _c1.html(btn_html, height=36, scrolling=False)
    st.markdown(result)


def _render_explain(provider: str, user_key: str) -> None:
    from .generate import generate_explanation

    # Persist result across re-renders (same pattern as Containerize).
    if "adi_explain_result" not in st.session_state:
        st.session_state.adi_explain_result = None

    # explain-geo.json: abstract geometry animation (File A, B&W-remapped)
    anim_col, title_col = st.columns([1, 5], gap="small")
    with anim_col:
        _render_lottie("explain-geo.json", height=90, key="explain_geo")
    with title_col:
        _section_header(
            _icon("book"),
            "Explain a Dockerfile",
            "Paste a Dockerfile and get a plain-English walkthrough of every instruction.",
        )

    text = st.text_area(
        "Dockerfile",
        height=260,
        key="explain_input",
        placeholder="FROM python:3.12-slim\nWORKDIR /app\n...",
    )
    go = st.button(
        ":material/menu_book:  Explain",
        type="primary",
        key="explain_btn",
        disabled=not text.strip(),
        use_container_width=True,
    )
    # S4: keyboard shortcut hint
    if not text.strip():
        st.caption("Paste a Dockerfile above, then press **Ctrl+Enter** or click Explain.")

    if not go:
        if st.session_state.adi_explain_result is not None:
            _show_llm_result(
                st.session_state.adi_explain_result,
                kind="Explanation",
                lottie_key="explain_done_p",
            )
        return

    try:
        llm = _build_llm(provider, user_key)
        with st.spinner("Reading the Dockerfile…"):
            result = generate_explanation(text, llm)

        # Store for persistence across subsequent re-renders
        st.session_state.adi_explain_result = result

        # check-done.json: circle + checkmark (new lottie #2) shown inline with result
        _show_llm_result(result, kind="Explanation", lottie_key="explain_done")
    except Exception as exc:
        st.error(f"Failed: {exc}")


def _render_improve(provider: str, user_key: str) -> None:
    from .generate import generate_improvements

    # Persist result across re-renders.
    if "adi_improve_result" not in st.session_state:
        st.session_state.adi_improve_result = None

    # S8: lottie header column (improve-spark.json) matching Containerize & Explain layout
    anim_col, title_col = st.columns([1, 5], gap="small")
    with anim_col:
        _render_lottie("improve-spark.json", height=90, key="improve_hero")
    with title_col:
        _section_header(
            _icon("sparkle"),
            "Improve a Dockerfile",
            "Paste a Dockerfile and get prioritised suggestions with diff snippets.",
        )

    text = st.text_area(
        "Dockerfile",
        height=260,
        key="improve_input",
        placeholder="FROM python:3.12-slim\nWORKDIR /app\n...",
    )
    go = st.button(
        ":material/auto_awesome:  Suggest improvements",
        type="primary",
        key="improve_btn",
        disabled=not text.strip(),
        use_container_width=True,
    )
    # S4: keyboard shortcut hint
    if not text.strip():
        st.caption("Paste a Dockerfile above, then press **Ctrl+Enter** or click Suggest.")

    if not go:
        if st.session_state.adi_improve_result is not None:
            _show_llm_result(
                st.session_state.adi_improve_result,
                kind="Suggestions",
                lottie_key="improve_done_p",
            )
        return

    try:
        llm = _build_llm(provider, user_key)
        with st.spinner("Reviewing…"):
            result = generate_improvements(text, llm)

        # Store for persistence
        st.session_state.adi_improve_result = result

        _show_llm_result(result, kind="Suggestions", lottie_key="improve_done")
    except Exception as exc:
        st.error(f"Failed: {exc}")


def _show_artifacts(last_run_dir: Path) -> None:
    """Render artifact panels for a completed pipeline run directory.

    Extracted into a helper so both the live render (inside the pipeline run)
    and the persistent re-render (on subsequent page loads from session_state)
    can call the same code without duplication.
    """
    st.markdown("")
    _section_header(_icon("folder"), "Artifacts", "Generated files from this run.")

    cols = st.columns(2, gap="medium")
    with cols[0]:
        df_path = last_run_dir / "Dockerfile"
        if df_path.exists():
            _section_header(_icon("file"), "Dockerfile")
            st.code(df_path.read_text(encoding="utf-8"), language="dockerfile")
            st.download_button(
                "Download Dockerfile",
                df_path.read_text(encoding="utf-8"),
                file_name="Dockerfile",
                use_container_width=True,
                key=f"dl-dockerfile-{last_run_dir.name}",
            )
    with cols[1]:
        yaml_path = last_run_dir / "autodock.yaml"
        if yaml_path.exists():
            _section_header(_icon("list"), "autodock.yaml")
            st.code(yaml_path.read_text(encoding="utf-8"), language="yaml")
            st.download_button(
                "Download autodock.yaml",
                yaml_path.read_text(encoding="utf-8"),
                file_name="autodock.yaml",
                use_container_width=True,
                key=f"dl-yaml-{last_run_dir.name}",
            )

    compose_path = last_run_dir / "docker-compose.yml"
    if compose_path.exists():
        _section_header(_icon("layers"), "docker-compose.yml")
        st.code(compose_path.read_text(encoding="utf-8"), language="yaml")
        st.download_button(
            "Download docker-compose.yml",
            compose_path.read_text(encoding="utf-8"),
            file_name="docker-compose.yml",
            use_container_width=True,
            key=f"dl-compose-{last_run_dir.name}",
        )

    profile_path = last_run_dir / "profile.json"
    if profile_path.exists():
        with st.expander(":material/search:  Detected project profile"):
            st.json(profile_path.read_text(encoding="utf-8"))

    attempts_dir = last_run_dir / "attempts"
    if attempts_dir.exists():
        attempt_count = len(list(attempts_dir.glob("*-Dockerfile")))
        with st.expander(f":material/autorenew:  Agentic build attempts ({attempt_count})"):
            for df in sorted(attempts_dir.glob("*-Dockerfile")):
                st.markdown(f"**Attempt {df.stem.split('-')[0]}**: `{df.name}`")
                st.code(df.read_text(encoding="utf-8"), language="dockerfile")
                log = df.with_name(df.name.replace("Dockerfile", "output.log"))
                if log.exists():
                    st.text_area(
                        f"Build output {df.stem}",
                        value=log.read_text(encoding="utf-8")[-3000:],
                        height=150,
                        key=f"log-{last_run_dir.name}-{df.name}",
                    )

    validation_path = last_run_dir / "validation.txt"
    if validation_path.exists():
        with st.expander(":material/check_circle:  Validation result"):
            st.code(validation_path.read_text(encoding="utf-8"), language="text")

    st.caption(f"All artifacts: `{last_run_dir}`")


def _show_pipeline_persist(result: dict) -> None:
    """Re-render a stored pipeline result from session_state.

    Called on subsequent page renders after a pipeline has already run so
    the user can see artifacts without having to click Containerize again.
    """
    rc = result.get("rc", 1)
    repo_url = result.get("repo_url", "")
    last_run_dir_str = result.get("last_run_dir")

    st.markdown(
        f'<div class="adi-eyebrow" style="margin:.5rem 0 .2rem">Last run</div>'
        f'<code style="font-size:.8rem;color:var(--adi-text2)">{repo_url}</code>',
        unsafe_allow_html=True,
    )
    st.markdown("")

    if rc == 0:
        notify_col, badge_col = st.columns([1, 6], gap="small")
        with notify_col:
            _render_lottie("success-notify.json", height=90, key="success_notify_p", loop=False)
        with badge_col:
            st.markdown("")
            st.markdown('<span class="adi-badge ok">SUCCESS</span>', unsafe_allow_html=True)
    else:
        st.markdown(
            f'<span class="adi-badge err">FAILED &middot; exit {rc}</span>',
            unsafe_allow_html=True,
        )

    if last_run_dir_str:
        last_run_dir = Path(last_run_dir_str)
        if last_run_dir.exists():
            _show_artifacts(last_run_dir)


def _render_containerize(
    provider_choice: str,
    user_key: str,
    docker_bin: str,
    preview_mode: bool,
) -> None:
    SAMPLE_REPOS = [
        ("Flask sample",  "https://github.com/digitalocean/sample-flask",          ":material/science:"),
        ("Node Express",  "https://github.com/heroku/node-js-getting-started",      ":material/javascript:"),
        ("Go hello",      "https://github.com/heroku/go-getting-started",           ":material/code:"),
    ]

    # The text_input below owns `repo_url_input` once it's rendered, so the sample
    # buttons must write to that same key (NOT a separate mirror). Streamlit silently
    # ignores the `value=` kwarg on a keyed widget on subsequent reruns, so writing
    # to a different key would never propagate into the input.
    if "repo_url_input" not in st.session_state:
        st.session_state.repo_url_input = ""
    if "adi_last_result" not in st.session_state:
        st.session_state.adi_last_result = None

    # S8: Add lottie animation header (same pattern as Explain tab)
    anim_col, title_col = st.columns([1, 5], gap="small")
    with anim_col:
        _render_lottie("hero-containers.json", height=90, key="containerize_hero")
    with title_col:
        _section_header(
            _icon("package"),
            "Containerize a repository",
            "Point it at a public GitHub repo - it ingests, analyses, generates, and self-heals.",
        )

    # Sample quick-start buttons — S9: differentiated with language icons (already set via icon=)
    st.markdown('<div class="adi-eyebrow" style="margin-top:.6rem;">Try a sample</div>', unsafe_allow_html=True)
    sample_cols = st.columns(len(SAMPLE_REPOS))
    for col, (label, url, icon) in zip(sample_cols, SAMPLE_REPOS, strict=True):
        if col.button(label, key=f"sample-{label}", icon=icon, use_container_width=True):
            st.session_state.repo_url_input = url
            st.rerun()

    # Wrap the URL input and the Containerize button in a form so pressing Enter
    # while focused on the input submits the form (Streamlit's default form
    # behaviour). The sample quick-start buttons stay OUTSIDE the form because
    # they only need to write to session_state, not kick off a run.
    with st.form("adi_containerize_form", clear_on_submit=False, border=False):
        repo_url = st.text_input(
            "GitHub repository URL",
            placeholder="https://github.com/user/repo",
            key="repo_url_input",
        )

        # S2: Inline URL validation feedback — shows OK / NOT-OK as user types
        if repo_url.strip():
            if _valid_github_url(repo_url.strip()):
                st.markdown(
                    '<span class="adi-url-ok">Valid GitHub URL</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<span class="adi-url-err">Enter a https://github.com/owner/repo URL</span>',
                    unsafe_allow_html=True,
                )

        go = st.form_submit_button(
            ":material/rocket_launch:  Containerize",
            type="primary",
            disabled=not repo_url,
            use_container_width=True,
        )
    # S4: Keyboard hint
    if not repo_url:
        st.caption("Paste a GitHub URL above and press **Enter**, or click Containerize.")

    if not go:
        # Show the last pipeline result if one exists so artifacts persist
        # across page interactions without requiring a re-run.
        if st.session_state.adi_last_result is not None:
            _show_pipeline_persist(st.session_state.adi_last_result)
        return

    if not _valid_github_url(repo_url):
        st.error("Please paste a valid `https://github.com/<owner>/<repo>` URL.")
        return

    # Pre-flight: bail out BEFORE spinning the pipeline subprocess if the repo
    # is private, gated, or 404. This puts the polished error card directly
    # under the Containerize button where a non-technical user will see it
    # instantly, instead of buried beneath a long Rich traceback in the live
    # agent log. The check is a 4-second HEAD request to the public GitHub
    # page; no auth, no API rate-limit risk.
    access = _check_repo_accessible(repo_url)
    if access != "ok":
        if access == "private":
            msg = (
                f"{repo_url} is private, gated, or does not exist. "
                "Auto-Dock It only supports PUBLIC GitHub repositories. "
                "Try a public repo (for example one of the sample buttons above)."
            )
            _render_repo_error_card(msg, kind="private")
        else:
            msg = (
                f"Could not reach {repo_url}. Check the URL and your network, "
                "then try again."
            )
            _render_repo_error_card(msg, kind="network")
        return

    using_own_key = bool(user_key.strip())

    if not using_own_key:
        if "session_runs" not in st.session_state:
            st.session_state.session_runs = 0
            st.session_state.last_run_at = None

        decision = check_and_record(
            session_runs=st.session_state.session_runs,
            session_last_run_at=st.session_state.last_run_at,
        )
        if not decision.allowed:
            st.warning(
                decision.reason
                + "  Tip: paste your own API key in the sidebar to skip rate limits."
            )
            return

        st.session_state.session_runs += 1
        st.session_state.last_run_at = time.monotonic()

    # ── Live pipeline log ──────────────────────────────────────────────────── #
    _section_header(
        _icon("activity"),
        "Live agent log",
        "Streaming output from the self-healing pipeline.",
    )

    log_area = st.empty()
    status_container = st.status("Running pipeline…", expanded=True)
    log_lines: list[str] = []

    env = {**os.environ, "DOCKER_BIN": docker_bin, "LLM_PROVIDER": provider_choice}
    _secrets_into_env(env)
    if using_own_key:
        env[f"{provider_choice.upper()}_API_KEY"] = user_key.strip()

    cmd = [sys.executable, "-m", "autodock.cli", "run", repo_url]
    if preview_mode:
        cmd.append("--dry-run")

    proc = subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    last_run_dir: Path | None = None

    assert proc.stdout is not None
    for line in proc.stdout:
        clean = _strip_ansi(line.rstrip())
        log_lines.append(clean)
        log_area.code("\n".join(log_lines[-60:]), language="text")
        # NOTE: regex must accept BOTH `output\<run_id>` (Windows) and
        # `output/<run_id>`. The test in tests/test_run_id_regex.py greps this
        # exact `re.search(r"...")` call and evals the pattern — do not change
        # its shape (single double-quoted raw string, trailing comma).
        match = re.search(r"output[\\/](\d{8}-\d{6}(?:-[0-9a-f]+)?)", clean)
        if match:
            last_run_dir = OUTPUT_ROOT / match.group(1)
    rc = proc.wait()

    # Persist result in session_state so artifacts survive any subsequent
    # page interaction without requiring a re-run.
    st.session_state.adi_last_result = {
        "rc": rc,
        "repo_url": repo_url,
        "last_run_dir": str(last_run_dir) if last_run_dir else None,
    }

    if rc == 0:
        status_container.update(label="Pipeline finished: success", state="complete")
        # success-notify.json: notification animation (File B, B&W-remapped)
        notify_col, badge_col = st.columns([1, 6], gap="small")
        with notify_col:
            _render_lottie("success-notify.json", height=120, key="success_notify", loop=False)
        with badge_col:
            st.markdown("")
            st.markdown('<span class="adi-badge ok">SUCCESS</span>', unsafe_allow_html=True)
    else:
        status_container.update(label=f"Pipeline finished: failed (exit {rc})", state="error")
        st.markdown(f'<span class="adi-badge err">FAILED &middot; exit {rc}</span>', unsafe_allow_html=True)
        # If the failure was a user-facing IngestError (private repo, 404, etc.),
        # surface it as a polished error card instead of leaving the user to
        # read the raw Rich traceback. The pipeline writes the IngestError
        # message to stdout via the autodock CLI's exception handler.
        _render_friendly_error_if_any(log_lines)

    # ── Artifacts ─────────────────────────────────────────────────────────── #
    if last_run_dir and last_run_dir.exists():
        _show_artifacts(last_run_dir)


_INGEST_ERROR_RE = re.compile(r"IngestError:\s*(.+?)$")


def _check_repo_accessible(repo_url: str) -> str:
    """Return 'ok', 'private', or 'network' for a github.com URL.

    Issues a 4-second unauthenticated HEAD request against the canonical repo
    page. GitHub returns 200 for public repos and 404 for private OR missing
    repos (it does not leak the distinction to anonymous clients, by design).
    Anything else (timeout, 5xx, connection error) is bucketed as 'network'
    so we don't lock the user out on a transient blip.
    """
    try:
        r = requests.head(repo_url, timeout=4, allow_redirects=True)
    except requests.RequestException:
        return "network"
    if r.status_code == 200:
        return "ok"
    if r.status_code == 404:
        return "private"
    return "network"


def _render_repo_error_card(msg: str, *, kind: str) -> None:
    """Render the polished error card under the Containerize button.

    kind:
      - 'private' : private / 404 repo (Auto-Dock It does not support these)
      - 'network' : transient reachability problem (network / GitHub 5xx)
      - 'ingest'  : IngestError surfaced from the running pipeline
    """
    if kind == "private":
        title, icon = "Repository not accessible", "lock_person"
    elif kind == "network":
        title, icon = "Could not reach the repository", "cloud_off"
    else:
        title, icon = "Could not ingest repository", "error"

    if kind == "network":
        hints_html = (
            "<li>Check the URL spelling and that github.com is reachable from your network.</li>"
            "<li>Wait a few seconds and click Containerize again.</li>"
            "<li>Try one of the <em>Try a sample</em> buttons above to confirm the pipeline itself is healthy.</li>"
        )
    else:
        hints_html = (
            "<li>Confirm the URL opens in an incognito browser tab (no GitHub login).</li>"
            "<li>Use one of the <em>Try a sample</em> buttons above for a known-public repo.</li>"
            "<li>If this is your own private repo, make it public temporarily or run <code>autodock</code> locally where it can use your git credentials.</li>"
        )

    st.markdown(
        f"""
        <div class="adi-error-card">
          <div class="adi-error-head">
            <span class="material-symbols-outlined adi-error-icon">{icon}</span>
            <span class="adi-error-title">{title}</span>
          </div>
          <div class="adi-error-body">{msg}</div>
          <div class="adi-error-hints">
            <strong>What to try:</strong>
            <ul>{hints_html}</ul>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_friendly_error_if_any(log_lines: list[str]) -> None:
    """Fallback: if the subprocess still failed with a recognisable IngestError
    (pre-flight passed but clone failed at runtime, eg. transient 5xx), surface
    the same polished card. The pre-flight in the containerize handler covers
    the common cases."""
    msg: str | None = None
    for line in reversed(log_lines):
        m = _INGEST_ERROR_RE.search(line)
        if m:
            msg = m.group(1).strip()
            break
    if not msg:
        return
    low = msg.lower()
    if "private" in low or "does not exist" in low or "public github repositories" in low:
        kind = "private"
    else:
        kind = "ingest"
    _render_repo_error_card(msg, kind=kind)


if __name__ == "__main__":
    render()
else:
    # Allow `streamlit run autodock/web.py` (script context) AND
    # `from autodock.web import render` from streamlit_app.py.
    # When imported as a module, do nothing at load time; caller invokes render().
    pass
