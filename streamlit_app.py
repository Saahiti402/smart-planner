import streamlit as st
import requests
import json
import ast
import re
from datetime import date, timedelta
from html import escape

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Smart Travel Planner 🌍",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed"   # sidebar fully hidden, we use top nav
)

# ─────────────────────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

    :root {
        --bg: #f8fafc;
        --paper: #ffffff;
        --ink: #0f172a;
        --muted: #64748b;
        --line: #e2e8f0;
        --accent: #2563eb;
        --accent-dark: #1d4ed8;
        --teal: #0ea5a4;
        --gold: #d97706;
        --success: #059669;
        --danger: #dc2626;
        --warning: #b45309;
        --shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
    }

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif !important;
        background: radial-gradient(circle at 6% 0%, #eef4ff 0%, transparent 45%),
                    radial-gradient(circle at 90% 100%, #ecfeff 0%, transparent 36%),
                    var(--bg) !important;
        color: var(--ink) !important;
    }

    #MainMenu, footer, header { visibility: hidden; }
    section[data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"]  { display: none !important; }
    .block-container { padding: 0.5rem 1.2rem 2.5rem !important; max-width: 1280px; }

    .top-nav {
        background: rgba(255, 255, 255, 0.88);
        backdrop-filter: blur(8px);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 10px 16px;
        margin: 8px 0 18px;
        box-shadow: var(--shadow);
    }
    .top-nav-brand {
        font-family: 'Manrope', sans-serif;
        font-size: 34px;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: var(--accent);
        white-space: nowrap;
        margin-bottom: 2px;
    }
    .nav-user {
        font-size: 12px;
        color: var(--muted);
        background: #fff;
        border: 1px solid var(--line);
        border-radius: 999px;
        padding: 7px 12px;
        white-space: nowrap;
    }
    .nav-user strong { color: var(--teal); }

    .top-nav-meta {
        display: flex;
        flex-direction: column;
        gap: 7px;
        align-items: flex-end;
    }
    .top-nav-helper {
        color: #8ea0b8;
        font-size: 12px;
        margin-bottom: 8px;
    }

    div[data-testid="stRadio"] {
        margin-top: 2px;
    }
    div[data-testid="stRadio"] > div {
        background: #0f172a;
        border: 1px solid #273244;
        border-radius: 12px;
        padding: 6px;
    }
    div[data-testid="stRadio"] [role="radiogroup"] {
        gap: 7px;
        flex-wrap: wrap;
        align-items: center;
    }
    div[data-testid="stRadio"] [role="radio"] {
        background: transparent;
        border: 1px solid transparent;
        border-radius: 9px;
        min-height: auto;
        padding: 7px 10px;
    }
    div[data-testid="stRadio"] [role="radio"] > div:first-child {
        display: none !important;
    }
    div[data-testid="stRadio"] [role="radio"] p {
        color: #c5d1df !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        margin: 0 !important;
    }
    div[data-testid="stRadio"] [role="radio"][aria-checked="true"] {
        background: rgba(37, 99, 235, 0.2);
        border: 1px solid rgba(59, 130, 246, 0.55);
    }
    div[data-testid="stRadio"] [role="radio"][aria-checked="true"] p {
        color: #f8fafc !important;
    }

    .page-head {
        margin-bottom: 14px;
        background: var(--paper);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 12px 14px;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05);
    }
    .page-head-title {
        font-family: 'Manrope', sans-serif;
        font-size: 24px;
        font-weight: 800;
        color: #020617 !important;
        letter-spacing: -0.02em;
        margin-bottom: 2px;
        line-height: 1.25;
    }
    .page-head-sub {
        color: #334155 !important;
        font-size: 13px;
        line-height: 1.45;
    }
    .assist-note {
        font-size: 12px;
        color: var(--muted);
        background: #fff;
        border: 1px dashed var(--line);
        border-radius: 10px;
        padding: 8px 10px;
        margin-bottom: 10px;
    }

    [data-testid="metric-container"] {
        background: var(--paper);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 14px;
        box-shadow: var(--shadow);
    }
    [data-testid="metric-container"] label {
        color: var(--muted) !important;
        font-size: 12px;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: var(--accent) !important;
        font-family: 'Manrope', sans-serif;
        font-size: 26px;
    }

    .stButton > button {
        border-radius: 10px !important;
        font-weight: 700 !important;
        font-size: 13px !important;
        padding: 8px 14px !important;
        transition: transform 0.14s ease, box-shadow 0.14s ease, filter 0.14s ease !important;
        width: 100%;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--accent), #3b82f6) !important;
        color: #fff !important;
        border: 1px solid rgba(59, 130, 246, 0.4) !important;
    }
    .stButton > button[kind="secondary"] {
        background: #0f172a !important;
        color: #dbe6f3 !important;
        border: 1px solid #273244 !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 8px 18px rgba(37, 99, 235, 0.22) !important;
        filter: brightness(1.03);
    }

    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input,
    .stTextArea textarea,
    div[data-baseweb="select"] > div,
    div[data-baseweb="select"] input {
        background: #111827 !important;
        border: 1px solid #273244 !important;
        color: #e5e7eb !important;
        border-radius: 10px !important;
        font-size: 14px !important;
    }
    .stTextInput > div > div > input::placeholder,
    .stTextArea textarea::placeholder,
    div[data-baseweb="select"] input::placeholder {
        color: #94a3b8 !important;
    }
    div[data-baseweb="select"] * {
        color: #e5e7eb !important;
    }
    div[data-baseweb="popover"] ul,
    div[data-baseweb="popover"] li,
    div[data-baseweb="menu"] {
        background: #0f172a !important;
        color: #e5e7eb !important;
        border-color: #273244 !important;
    }
    div[data-baseweb="popover"] li:hover {
        background: #1e293b !important;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea textarea:focus {
        border-color: var(--teal) !important;
        box-shadow: 0 0 0 3px rgba(14, 165, 164, 0.18) !important;
    }
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        background: #111827 !important;
        border: 1px solid #273244 !important;
        color: #e5e7eb !important;
        border-radius: 10px !important;
    }

    .stp-card {
        background: var(--paper);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 18px 20px;
        margin-bottom: 14px;
        box-shadow: var(--shadow);
    }

    .hero {
        background: linear-gradient(115deg, #eef4ff 0%, #f8fbff 48%, #ecfeff 100%);
        border: 1px solid #dbeafe;
        border-radius: 20px;
        padding: 34px 26px;
        margin-bottom: 18px;
        text-align: center;
        box-shadow: var(--shadow);
    }
    .hero-title {
        font-family: 'Manrope', sans-serif;
        font-size: 34px;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 6px;
        letter-spacing: -0.03em;
    }
    .hero-sub { color: var(--muted); font-size: 15px; }

    .user-bubble {
        background: linear-gradient(135deg, var(--accent), #3b82f6);
        color: #fff;
        padding: 12px 15px;
        border-radius: 15px 15px 3px 15px;
        margin: 8px 0 8px 70px;
        font-size: 14px;
        line-height: 1.6;
    }
    .bot-bubble {
        background: var(--paper);
        color: var(--ink);
        padding: 12px 15px;
        border-radius: 15px 15px 15px 3px;
        margin: 8px 70px 8px 0;
        font-size: 14px;
        line-height: 1.6;
        border: 1px solid var(--line);
        box-shadow: var(--shadow);
    }
    .chat-label { font-size: 11px; color: var(--muted); margin-bottom: 2px; font-weight: 600; }
    .user-label { text-align: right; }

    .day-card {
        background: #fff;
        border: 1px solid var(--line);
        border-left: 4px solid var(--teal);
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 10px;
    }
    .day-title {
        font-size: 12px;
        font-weight: 700;
        color: var(--teal);
        margin-bottom: 9px;
        text-transform: uppercase;
        letter-spacing: .05em;
    }

    .budget-bar-wrap { margin-bottom: 12px; }
    .budget-bar-label {
        display: flex;
        justify-content: space-between;
        font-size: 12px;
        color: var(--muted);
        margin-bottom: 4px;
    }
    .budget-bar-track { background: #eaf0f6; border-radius: 20px; height: 10px; overflow: hidden; }
    .budget-bar-fill { height: 100%; border-radius: 20px; background: linear-gradient(90deg, var(--teal), var(--gold)); }

    .badge-success {
        display: inline-block;
        background: rgba(5, 150, 105, .12);
        color: var(--success);
        border: 1px solid rgba(5, 150, 105, .25);
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
    }
    .badge-error {
        display: inline-block;
        background: rgba(220, 38, 38, .11);
        color: var(--danger);
        border: 1px solid rgba(220, 38, 38, .24);
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
    }
    .badge-info {
        display: inline-block;
        background: rgba(37, 99, 235, .11);
        color: var(--accent);
        border: 1px solid rgba(37, 99, 235, .24);
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
    }

    .section-header {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: .1em;
        text-transform: uppercase;
        color: var(--muted);
        margin: 20px 0 9px;
        padding-bottom: 6px;
        border-bottom: 1px solid var(--line);
    }

    .stTabs [data-baseweb="tab-list"] {
        background: #f8fafc !important;
        border-radius: 11px;
        padding: 4px;
        gap: 4px;
        border: 1px solid var(--line);
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: var(--muted) !important;
        border-radius: 8px !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        padding: 8px 16px !important;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(37, 99, 235, 0.12) !important;
        color: var(--accent) !important;
    }

    .streamlit-expanderHeader {
        background: #fff !important;
        border: 1px solid var(--line) !important;
        border-radius: 10px !important;
        color: var(--ink) !important;
        font-size: 14px !important;
    }

    .login-title {
        font-family: 'Manrope', sans-serif;
        font-size: 32px;
        font-weight: 800;
        color: #020617 !important;
        text-align: center;
        margin-bottom: 8px;
        letter-spacing: -0.02em;
    }
    .login-sub {
        color: #334155 !important;
        font-size: 14px;
        text-align: center;
        margin-bottom: 20px;
        font-weight: 500;
    }
    .login-hero {
        background: var(--paper);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 18px 14px;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
        max-width: 620px;
        margin: 0 auto;
    }
    .auth-shell {
        background: rgba(255, 255, 255, 0.88);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 16px;
        box-shadow: 0 12px 28px rgba(15, 23, 42, 0.09);
    }
    .auth-note {
        font-size: 12px;
        color: #475569;
        background: #f8fafc;
        border: 1px dashed #dbe3ee;
        border-radius: 10px;
        padding: 8px 10px;
        margin-bottom: 10px;
        text-align: center;
    }
    .auth-kpi {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 8px 10px;
        text-align: center;
    }
    .auth-kpi-val {
        font-family: 'Manrope', sans-serif;
        font-size: 15px;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 1px;
    }
    .auth-kpi-label {
        font-size: 11px;
        color: #64748b;
    }
    .auth-page-title {
        font-family: 'Manrope', sans-serif;
        font-size: 28px;
        font-weight: 800;
        color: #f8fafc;
        text-align: center;
        margin: 4px 0 16px;
        letter-spacing: -0.02em;
    }
    .auth-brand-card {
        background: linear-gradient(145deg, #0b1220 0%, #111b2f 52%, #0f1e36 100%);
        border: 1px solid #22324c;
        border-radius: 18px;
        padding: 22px 22px;
        box-shadow: 0 18px 36px rgba(2, 6, 23, 0.45);
    }
    .auth-brand-chip {
        display: inline-block;
        background: rgba(37, 99, 235, 0.2);
        color: #bfdbfe;
        border: 1px solid rgba(59, 130, 246, 0.35);
        border-radius: 999px;
        padding: 4px 10px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: .04em;
        text-transform: uppercase;
        margin-bottom: 12px;
    }
    .auth-brand-title {
        font-family: 'Manrope', sans-serif;
        font-size: 32px;
        line-height: 1.15;
        font-weight: 800;
        color: #e2e8f0;
        margin: 0 0 8px;
    }
    .auth-brand-sub {
        color: #9fb0c7;
        font-size: 14px;
        line-height: 1.6;
        margin-bottom: 16px;
    }
    .auth-feature-row {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-bottom: 16px;
    }
    .auth-feature-item {
        background: rgba(15, 23, 42, 0.55);
        border: 1px solid #2a3b58;
        border-radius: 10px;
        padding: 8px 10px;
        color: #dbe6f3;
        font-size: 13px;
    }
    .auth-brand-stats {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 8px;
    }
    .auth-brand-stat {
        background: rgba(15, 23, 42, 0.62);
        border: 1px solid #2a3b58;
        border-radius: 10px;
        padding: 8px;
        text-align: center;
    }
    .auth-brand-stat-val {
        font-family: 'Manrope', sans-serif;
        color: #f8fafc;
        font-size: 14px;
        font-weight: 800;
    }
    .auth-brand-stat-label {
        color: #8fa3bc;
        font-size: 10px;
        margin-top: 1px;
    }
    .auth-form-card {
        background: rgba(255, 255, 255, 0.93);
        border: 1px solid #dbe6f3;
        border-radius: 16px;
        padding: 18px;
        box-shadow: 0 12px 28px rgba(15, 23, 42, 0.12);
    }
    .auth-form-title {
        font-family: 'Manrope', sans-serif;
        font-size: 22px;
        font-weight: 800;
        color: #f8fafc;
        margin-bottom: 4px;
    }
    .auth-form-sub {
        color: #94a3b8;
        font-size: 13px;
        margin-bottom: 10px;
    }

    .cmp-point {
        font-size: 13px;
        line-height: 1.55;
        color: var(--ink);
        margin-bottom: 5px;
    }
    .resp-list {
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    .resp-item {
        background: rgba(15, 23, 42, 0.04);
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 10px 12px;
    }
    .resp-title {
        font-weight: 700;
        color: #0f172a;
        font-size: 14px;
        margin-bottom: 4px;
    }
    .resp-meta {
        color: #475569;
        font-size: 12px;
        margin-bottom: 2px;
    }
    .resp-address {
        color: #334155;
        font-size: 12px;
        line-height: 1.45;
    }
    .resp-desc {
        color: #334155;
        font-size: 13px;
        line-height: 1.55;
    }
    .resp-line {
        margin-bottom: 6px;
        line-height: 1.55;
    }

    hr { border-color: var(--line) !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "logged_in": False,
        "user_id": None,
        "user_email": None,
        "user_role": None,
        "chat_history": [],
        "page": "login",
        "page_history": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ─────────────────────────────────────────────────────────────
# NAVIGATION HELPERS
# ─────────────────────────────────────────────────────────────
def navigate_to(page: str, add_history: bool = True):
    current = st.session_state.get("page", "home")
    if current != page:
        if add_history:
            history = st.session_state.get("page_history", [])
            history.append(current)
            st.session_state.page_history = history
        else:
            st.session_state.page_history = []
    st.session_state.page = page
    st.rerun()

def go_back():
    history = st.session_state.get("page_history", [])
    if history:
        prev = history.pop()
        st.session_state.page_history = history
        st.session_state.page = prev
    else:
        st.session_state.page = "home"
    st.rerun()

# ─────────────────────────────────────────────────────────────
# API HELPERS
# ─────────────────────────────────────────────────────────────
def api_post(endpoint, payload):
    try:
        r = requests.post(f"{BASE_URL}{endpoint}", json=payload, timeout=120)
        return r.json(), r.status_code
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to backend. Make sure FastAPI is running on port 8000."}, 503
    except Exception as e:
        return {"error": str(e)}, 500

def api_get(endpoint, params=None):
    try:
        r = requests.get(f"{BASE_URL}{endpoint}", params=params, timeout=120)
        return r.json(), r.status_code
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to backend. Make sure FastAPI is running on port 8000."}, 503
    except Exception as e:
        return {"error": str(e)}, 500

def show_error(msg):
    st.error(msg)
    st.markdown(f'<div class="badge-error">❌ {msg}</div>', unsafe_allow_html=True)

def show_success(msg):
    st.success(msg)
    st.markdown(f'<div class="badge-success">✅ {msg}</div>', unsafe_allow_html=True)


def render_page_header(icon: str, title: str, subtitle: str):
    st.markdown(
        f"""
        <div class="page-head">
            <div class="page-head-title">{icon} {title}</div>
            <div class="page-head-sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────
# TOP NAV BAR  (rendered on every logged-in page)
# ─────────────────────────────────────────────────────────────
def render_top_nav():
    current = st.session_state.get("page", "home")

    nav_items = [
        ("Dashboard", "home"),
        ("AI Chat", "chat"),
        ("Plan Trip", "itinerary"),
        ("Budget", "budget"),
        ("Compare", "compare"),
        ("External", "external_tools"),
        ("Preferences", "preferences"),
        ("History", "conversations"),
    ]

    with st.container(border=True):
        shell_left, shell_right = st.columns([8, 2])

        with shell_left:
            st.markdown('<div class="top-nav-brand">✈️ TravelAI</div>', unsafe_allow_html=True)
            st.markdown('<div class="top-nav-helper">Navigate modules</div>', unsafe_allow_html=True)

            nav_top_cols = st.columns(4)
            for idx, ((label, key), col) in enumerate(zip(nav_items[:4], nav_top_cols)):
                with col:
                    if st.button(
                        label,
                        key=f"topnav_clean_top_{idx}_{key}",
                        type="primary" if current == key else "secondary",
                        use_container_width=True,
                    ):
                        navigate_to(key, add_history=False)

            nav_bottom_cols = st.columns(4)
            for idx, ((label, key), col) in enumerate(zip(nav_items[4:], nav_bottom_cols)):
                with col:
                    if st.button(
                        label,
                        key=f"topnav_clean_bottom_{idx}_{key}",
                        type="primary" if current == key else "secondary",
                        use_container_width=True,
                    ):
                        navigate_to(key, add_history=False)

        with shell_right:
            st.markdown('<div class="top-nav-helper" style="text-align:right;">Session</div>', unsafe_allow_html=True)
            st.markdown('<div class="top-nav-meta">', unsafe_allow_html=True)
            email = st.session_state.get("user_email") or ""
            role  = st.session_state.get("user_role") or ""
            if st.button("Sign Out", key="topnav_logout", type="secondary"):
                for k in ["logged_in","user_id","user_email","user_role","chat_history","page_history"]:
                    st.session_state[k] = ([] if k in ("chat_history","page_history")
                                           else (False if k=="logged_in" else None))
                st.session_state.page = "login"
                st.rerun()
            st.markdown(
                f'<div class="nav-user"><strong>●</strong> {email} · {role}</div>',
                unsafe_allow_html=True
            )
            st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# BACK BUTTON  (breadcrumb)
# ─────────────────────────────────────────────────────────────
def render_back_button(label=""):
    history = st.session_state.get("page_history", [])
    if not history:
        return

    clean_history = []
    for page in history:
        if not clean_history or clean_history[-1] != page:
            clean_history.append(page)

    if len(clean_history) > 6:
        clean_history = clean_history[-6:]

    st.session_state.page_history = clean_history

    page_names = {
        "home":"🏠 Dashboard","chat":"💬 AI Chat","itinerary":"🗺️ Plan Trip",
        "budget":"💰 Budget","compare":"🧭 Compare","external_tools":"🌐 External Tools",
        "preferences":"⚙️ Preferences","conversations":"📋 History",
    }
    crumb = " › ".join([page_names.get(p, p) for p in clean_history])
    crumb += f" › <b>{label}</b>"
    c1, c2 = st.columns([1, 8])
    with c1:
        if st.button("← Back", key="back_btn"):
            go_back()
    with c2:
        st.markdown(
            f'<div style="font-size:12px;color:#60707f;padding:10px 0 0 4px;">{crumb}</div>',
            unsafe_allow_html=True
        )
    st.markdown('<hr style="margin:8px 0 18px;">', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# PAGE: LOGIN / REGISTER
# ─────────────────────────────────────────────────────────────
def render_login_page():
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="auth-page-title">Welcome to Smart Travel Planner</div>', unsafe_allow_html=True)

    left_col, right_col = st.columns([1.1, 1], gap="large")

    with left_col:
        st.markdown("""
        <div class="auth-brand-card">
            <div class="auth-brand-chip">AI-Powered Travel</div>
            <div class="auth-brand-title">✈️ Build Better Trips, Faster</div>
            <div class="auth-brand-sub">
                Get day-wise itineraries, budget intelligence, destination comparisons,
                and live external travel insights in one workspace.
            </div>
            <div class="auth-feature-row">
                <div class="auth-feature-item">🧠 Personalized itinerary generation</div>
                <div class="auth-feature-item">💸 Smart budget allocation and optimization</div>
                <div class="auth-feature-item">🌐 Live weather, flights, hotels, and places</div>
            </div>
            <div class="auth-brand-stats">
                <div class="auth-brand-stat"><div class="auth-brand-stat-val">AI</div><div class="auth-brand-stat-label">Travel Agent</div></div>
                <div class="auth-brand-stat"><div class="auth-brand-stat-val">Live</div><div class="auth-brand-stat-label">Tooling</div></div>
                <div class="auth-brand-stat"><div class="auth-brand-stat-val">Smart</div><div class="auth-brand-stat-label">Planning</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with right_col:
        with st.container(border=True):
            st.markdown('<div class="auth-form-title">Sign in to continue</div>', unsafe_allow_html=True)
            st.markdown('<div class="auth-form-sub">Secure access to your plans, chat history, and preferences.</div>', unsafe_allow_html=True)

            tab_login, tab_register = st.tabs(["🔐 Login", "📝 Register"])

            with tab_login:
                email = st.text_input("Email Address", placeholder="you@example.com", key="login_email")
                password = st.text_input("Password", type="password", placeholder="••••••••", key="login_pass")
                if st.button("Sign In →", key="btn_login"):
                    if not email or not password:
                        show_error("Please fill in both fields.")
                    else:
                        with st.spinner("Authenticating..."):
                            data, code = api_post("/login", {"email": email, "password": password})
                        if code == 200:
                            st.session_state.logged_in  = True
                            st.session_state.user_id    = data["user_id"]
                            st.session_state.user_email = data["email"]
                            st.session_state.user_role  = data["role"]
                            st.session_state.page       = "home"
                            st.session_state.page_history = []
                            st.rerun()
                        else:
                            show_error(data.get("detail", "Login failed"))

            with tab_register:
                full_name = st.text_input("Full Name", placeholder="John Doe", key="reg_name")
                reg_email = st.text_input("Email Address", placeholder="you@example.com", key="reg_email")
                reg_pass  = st.text_input("Password", type="password", placeholder="Min 8 characters", key="reg_pass")
                role = st.selectbox("Account Type", ["user", "travel_agent", "admin"], key="reg_role")
                if st.button("Create Account →", key="btn_register"):
                    if not full_name or not reg_email or not reg_pass:
                        show_error("Please fill all fields.")
                    else:
                        with st.spinner("Creating your account..."):
                            data, code = api_post("/register", {
                                "full_name": full_name, "email": reg_email,
                                "password": reg_pass, "role": role
                            })
                        if code == 200:
                            show_success("Account created! Please log in.")
                        else:
                            show_error(data.get("detail", "Registration failed"))

            st.markdown('<div class="auth-note">By continuing, you agree to use this planner responsibly for travel insights and recommendations.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# PAGE: DASHBOARD
# ─────────────────────────────────────────────────────────────
def render_dashboard():
    st.markdown("""
    <div class="hero">
        <div class="hero-title">Welcome to Smart Travel Planner 🌍</div>
        <div class="hero-sub">Your AI-powered companion for seamless trip planning</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">Quick Actions</div>', unsafe_allow_html=True)
    qa1, qa2, qa3, qa4 = st.columns(4)
    cards = [
        ("qa1", "🗺️", "Plan a Trip", "Generate AI itinerary", "itinerary"),
        ("qa2", "💬", "Ask AI", "Chat with travel agent", "chat"),
        ("qa3", "💰", "Budget", "Smart budget breakdown", "budget"),
        ("qa4", "🧭", "Compare", "Evaluate destinations", "compare"),
    ]
    for col, (key, icon, title, sub, pg) in zip([qa1, qa2, qa3, qa4], cards):
        with col:
            st.markdown(f"""
            <div class="stp-card" style="text-align:center;">
                <div style="font-size:26px;margin-bottom:6px;">{icon}</div>
                <div style="font-weight:700;font-size:15px;margin-bottom:4px;">{title}</div>
                <div style="font-size:12px;color:#60707f;">{sub}</div>
            </div>""", unsafe_allow_html=True)
            if st.button("Open →", key=f"dash_{key}"):
                navigate_to(pg)

    st.markdown('<div class="section-header">Backend Health</div>', unsafe_allow_html=True)
    data, code = api_get("/")
    if code == 200:
        st.markdown('<span class="badge-success">✅ FastAPI backend is online</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge-error">❌ Backend unreachable — start uvicorn on port 8000</span>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# PAGE: AI CHAT
# ─────────────────────────────────────────────────────────────
def render_chat():
    render_back_button("💬 AI Travel Chat")
    render_page_header(
        "💬",
        "AI Travel Chat",
        "Ask anything about itinerary ideas, destination planning, weather, and travel budgets."
    )
    st.markdown(
        '<div class="assist-note">Tip: Ask specific questions like "3-day Goa plan under 30k for 2 people" for better responses.</div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.chat_history:
        st.markdown("""
        <div class="stp-card" style="text-align:center;padding:40px;">
            <div style="font-size:38px;margin-bottom:12px;">🤖</div>
            <div style="font-size:16px;font-weight:600;color:#1f2a37;margin-bottom:8px;">
                Hello! I'm your Smart Travel Agent
            </div>
            <div style="font-size:13px;color:#60707f;">
                Ask me anything about travel destinations, budgets, or itineraries!
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for turn in st.session_state.chat_history:
            st.markdown(f'<div class="chat-label user-label">You</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="user-bubble">{escape(str(turn["user"]))}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="chat-label">🤖 TravelAI</div>', unsafe_allow_html=True)
            bot_text = _format_assistant_response(turn["bot"])
            st.markdown(f'<div class="bot-bubble">{_to_pretty_html(bot_text)}</div>', unsafe_allow_html=True)
            if turn.get("tool"):
                st.markdown(f'<span class="badge-info">🛠 Tool: {turn["tool"]}</span>', unsafe_allow_html=True)
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    if not st.session_state.chat_history:
        st.markdown('<div class="section-header">Suggested Questions</div>', unsafe_allow_html=True)
        suggestions = [
            "Best beaches to visit in Goa?",
            "Plan a 5-day Kerala trip for 2",
            "Budget for Manali trip in winter?",
            "Things to do in Rajasthan in October",
        ]
        s1, s2 = st.columns(2)
        for i, s in enumerate(suggestions):
            with (s1 if i % 2 == 0 else s2):
                if st.button(f"💡 {s}", key=f"sugg_{i}"):
                    _process_chat(s)
                    st.rerun()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    c_inp, c_btn = st.columns([5, 1])
    with c_inp:
        user_msg = st.text_input("Message", placeholder="Ask anything about travel...",
                                 label_visibility="collapsed", key="chat_input")
    with c_btn:
        if st.button("Send ➤", key="chat_send"):
            if user_msg.strip():
                _process_chat(user_msg.strip())
                st.rerun()

    if st.session_state.chat_history:
        if st.button("🗑 Clear Chat", key="clear_chat"):
            st.session_state.chat_history = []
            st.rerun()

def _process_chat(message):
    with st.spinner("Thinking..."):
        data, code = api_get("/ask-travel", params={"query": message, "user_id": st.session_state.user_id})
    if code == 200:
        response = data.get("response", str(data))
        tool     = data.get("tool_used", "")
    else:
        response = data.get("detail", data.get("error", "Sorry, couldn't process that."))
        tool     = ""
    st.session_state.chat_history.append({"user": message, "bot": response, "tool": tool})


def _format_assistant_response(raw):
    """
    Safely extract only user-facing answer content.
    Prevents infinite recursion from nested dict/list payloads.
    """

    MAX_DEPTH = 10

    def parse_payload(value, depth=0):
        # Prevent infinite recursion
        if depth > MAX_DEPTH:
            return str(value)

        if isinstance(value, str):
            text = value.strip()
            if not text:
                return ""

            # Try parsing JSON-like strings safely
            if text.startswith("{") or text.startswith("["):
                try:
                    parsed = json.loads(text)
                    return parse_payload(parsed, depth + 1)
                except Exception:
                    try:
                        parsed = ast.literal_eval(text)
                        return parse_payload(parsed, depth + 1)
                    except Exception:
                        return text

            return text

        elif isinstance(value, dict):
            # Preferred keys first
            priority_keys = ["answer", "response", "final_answer", "message", "result", "data"]

            for key in priority_keys:
                if key in value and value[key] not in (None, "", {}, []):
                    return parse_payload(value[key], depth + 1)

            # Remove metadata keys
            metadata_keys = {
                "query",
                "source",
                "tool",
                "tool_used",
                "metadata",
                "request",
                "status"
            }

            filtered = {
                k: v for k, v in value.items()
                if k not in metadata_keys
            }

            # VERY IMPORTANT FIX
            # If filtering does not reduce structure, stop recursion
            if not filtered or filtered == value:
                return str(value)

            return parse_payload(filtered, depth + 1)

        elif isinstance(value, list):
            parts = [
                parse_payload(item, depth + 1)
                for item in value
            ]
            parts = [p for p in parts if str(p).strip()]
            return "\n".join(parts)

        return str(value)

    cleaned = parse_payload(raw)

    return cleaned if cleaned else "Sorry, I could not generate a clear answer."

def _to_pretty_html(text: str) -> str:
    """Render assistant text in a more readable and user-friendly format."""
    def _inline_markdown_to_html(line: str) -> str:
        safe = escape(line)
        # Support common markdown emphasis in model responses.
        safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
        return safe

    if not isinstance(text, str):
        text = str(text)

    cleaned = text.strip()
    if not cleaned:
        return ""

    place_pattern = re.compile(
        r"(?:^|\s)(\d+)\.\s*Place:\s*(.*?),\s*Rating:\s*([0-9.]+),\s*Address:\s*(.*?)(?=(?:\s\d+\.\s*Place:|$))",
        re.IGNORECASE | re.DOTALL,
    )
    place_matches = place_pattern.findall(cleaned)

    if place_matches:
        cards = []
        for idx, name, rating, address in place_matches:
            cards.append(
                "<div class='resp-item'>"
                f"<div class='resp-title'>{escape(idx)}. {escape(name.strip())}</div>"
                f"<div class='resp-meta'>⭐ Rating: {escape(rating.strip())}</div>"
                f"<div class='resp-address'>📍 {escape(address.strip())}</div>"
                "</div>"
            )
        return f"<div class='resp-list'>{''.join(cards)}</div>"

    # Handle markdown-style numbered lists, e.g.:
    # 1. **Baga Beach**: Description...
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    md_items = []
    intro_lines = []
    outro_lines = []
    started_items = False

    for line in lines:
        m = re.match(r"^(\d+)\.\s*\*\*(.+?)\*\*\s*:?\s*(.*)$", line)
        if m:
            started_items = True
            idx, title, desc = m.group(1), m.group(2), m.group(3)
            md_items.append((idx.strip(), title.strip(), desc.strip()))
        else:
            if not started_items:
                intro_lines.append(line)
            else:
                outro_lines.append(line)

    if len(md_items) >= 2:
        intro_html = "".join(
            [f"<div class='resp-line'>{_inline_markdown_to_html(line)}</div>" for line in intro_lines]
        )
        cards = []
        for idx, title, desc in md_items:
            cards.append(
                "<div class='resp-item'>"
                f"<div class='resp-title'>{escape(idx)}. {_inline_markdown_to_html(title)}</div>"
                f"<div class='resp-desc'>{_inline_markdown_to_html(desc)}</div>"
                "</div>"
            )
        outro_html = "".join(
            [f"<div class='resp-line'>{_inline_markdown_to_html(line)}</div>" for line in outro_lines]
        )
        return f"{intro_html}<div class='resp-list'>{''.join(cards)}</div>{outro_html}"

    if len(lines) > 1:
        return "".join([f"<div class='resp-line'>{_inline_markdown_to_html(line)}</div>" for line in lines])

    return _inline_markdown_to_html(cleaned)

# ─────────────────────────────────────────────────────────────
# PAGE: PLAN A TRIP
# ─────────────────────────────────────────────────────────────
def render_itinerary():
    render_back_button("🗺️ Plan a Trip")
    render_page_header(
        "🗺️",
        "Plan a Trip",
        "Generate a full day-by-day itinerary with practical budget insights."
    )

    with st.container(border=True):
        st.markdown(
            '<div class="assist-note">Fill the essentials first, then optionally tune travel preferences for personalization.</div>',
            unsafe_allow_html=True,
        )
        with st.form("trip_form"):
            c1, c2 = st.columns(2)
            with c1:
                source      = st.text_input("🛫 From (Source City)", value="Mumbai")
                destination = st.text_input("📍 To (Destination)",   value="Goa")
                budget      = st.number_input("💰 Total Budget (₹)", min_value=5000, max_value=1000000, value=50000, step=1000)
            with c2:
                start_date = st.date_input("📅 Start Date", value=date.today() + timedelta(days=7))
                end_date   = st.date_input("📅 End Date",   value=date.today() + timedelta(days=11))
                travelers  = st.number_input("👥 Travelers", min_value=1, max_value=20, value=2)

            with st.expander("Optional Travel Preferences", expanded=False):
                p1, p2, p3 = st.columns(3)
                with p1:
                    trip_type  = st.selectbox("Trip Type",       ["leisure","adventure","business","cultural","honeymoon"])
                    transport  = st.selectbox("Transport Mode",  ["flight","train","bus","car"])
                with p2:
                    hotel_type = st.selectbox("Hotel Category",  ["budget","3-star","4-star","5-star","luxury"])
                    food_pref  = st.selectbox("Food Preference", ["vegetarian","non-vegetarian","vegan","any"])
                with p3:
                    climate    = st.selectbox("Climate",         ["any","tropical","cold","moderate","desert"])

            submitted = st.form_submit_button("✨ Generate AI Itinerary", use_container_width=True)

    if submitted:
        if start_date >= end_date:
            show_error("End date must be after start date.")
            return
        payload = {
            "user_id": st.session_state.user_id,
            "source_location": source, "destination": destination,
            "start_date": str(start_date), "end_date": str(end_date),
            "budget": int(budget), "travelers_count": int(travelers),
        }
        with st.spinner(f"🤖 AI is planning your {destination} trip... (30–60 seconds)"):
            data, code = api_post("/plan-trip", payload)
        if code == 200:
            show_success(f"Trip planned! ID: {data.get('trip_id','—')[:8]}...")
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            _render_itinerary_result(data, destination, budget)
        else:
            show_error(data.get("detail", data.get("error", "Trip planning failed")))

def _render_itinerary_result(data, destination, budget):
    itinerary     = data.get("itinerary", {})
    recommendations = data.get("recommendations", {})
    breakdown     = recommendations.get("budget_breakdown", {})

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🏙 Destination", destination)
    c2.metric("📅 Total Days", recommendations.get("total_days", "—"))
    c3.metric("👥 Travelers",  recommendations.get("travelers", "—"))
    c4.metric("💰 Budget",     f"₹{int(budget):,}")

    tab_plan, tab_budget, tab_agent = st.tabs(["📅 Day Plan", "💰 Budget Breakdown", "🤖 Agent Log"])

    with tab_plan:
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        for day_key in sorted(itinerary.keys()):
            blocks  = itinerary[day_key]
            day_num = day_key.replace("day_", "Day ")
            st.markdown(f"""
            <div class="day-card">
                <div class="day-title">📅 {day_num.upper()}</div>
                <div style="display:flex;flex-direction:column;gap:8px;">
                    <div style="display:flex;gap:12px;align-items:flex-start;">
                        <span style="background:rgba(217,119,6,.12);color:#b45309;padding:2px 10px;
                            border-radius:10px;font-size:11px;font-weight:600;min-width:90px;text-align:center;">
                            🌅 Morning</span>
                        <span style="font-size:13px;color:#1f2a37;line-height:1.5;">{blocks.get('morning','—')}</span>
                    </div>
                    <div style="display:flex;gap:12px;align-items:flex-start;">
                        <span style="background:rgba(14,165,164,.12);color:#0ea5a4;padding:2px 10px;
                            border-radius:10px;font-size:11px;font-weight:600;min-width:90px;text-align:center;">
                            ☀️ Afternoon</span>
                        <span style="font-size:13px;color:#1f2a37;line-height:1.5;">{blocks.get('afternoon','—')}</span>
                    </div>
                    <div style="display:flex;gap:12px;align-items:flex-start;">
                        <span style="background:rgba(37,99,235,.12);color:#2563eb;padding:2px 10px;
                            border-radius:10px;font-size:11px;font-weight:600;min-width:90px;text-align:center;">
                            🌃 Evening</span>
                        <span style="font-size:13px;color:#1f2a37;line-height:1.5;">{blocks.get('evening','—')}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with tab_budget:
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if breakdown:
            total = budget
            items = {
                "🏨 Hotel":         breakdown.get("hotel_total", 0),
                "🚗 Transport":     breakdown.get("transport",   0),
                "🍽 Food":          breakdown.get("food",        0),
                "🎉 Miscellaneous": breakdown.get("misc",        0),
            }
            bc1, bc2 = st.columns(2)
            for i, (label, amount) in enumerate(items.items()):
                pct  = int((amount / total) * 100) if total else 0
                html = f"""
                <div class="budget-bar-wrap">
                    <div class="budget-bar-label">
                        <span>{label}</span>
                        <span style="color:#1f2a37;font-weight:600;">₹{int(amount):,} ({pct}%)</span>
                    </div>
                    <div class="budget-bar-track">
                        <div class="budget-bar-fill" style="width:{pct}%;"></div>
                    </div>
                </div>"""
                (bc1 if i % 2 == 0 else bc2).markdown(html, unsafe_allow_html=True)
            st.markdown(f"""
            <div class="stp-card" style="margin-top:12px;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div style="font-size:14px;font-weight:700;">Hotel Per Night</div>
                    <div style="font-size:22px;font-weight:800;color:#2563eb;">₹{breakdown.get('hotel_per_night',0):,}</div>
                </div>
                <div style="display:flex;justify-content:space-between;align-items:center;margin-top:10px;">
                    <div style="font-size:14px;font-weight:700;">Grand Total</div>
                    <div style="font-size:22px;font-weight:800;color:#059669;">₹{breakdown.get('grand_total',0):,}</div>
                </div>
            </div>""", unsafe_allow_html=True)

    with tab_agent:
        agent_log = data.get("agent_decision", {})
        if agent_log:
            for step, detail in agent_log.items():
                with st.expander(f"🔎 {step.replace('_',' ').title()}"):
                    st.json(detail)
        else:
            st.info("No agent decision log returned.")

# ─────────────────────────────────────────────────────────────
# PAGE: BUDGET OPTIMIZER
# ─────────────────────────────────────────────────────────────
def render_budget():
    render_back_button("💰 Budget Optimizer")
    render_page_header(
        "💰",
        "Budget Optimizer",
        "Get smart budget allocation across transport, stay, food, activities, and misc."
    )

    tab_s, tab_nl = st.tabs(["📋 Structured Input", "💬 Natural Language"])

    with tab_s:
        with st.container(border=True):
            st.markdown(
                '<div class="assist-note">Use structured fields for precise control over budget assumptions.</div>',
                unsafe_allow_html=True,
            )
            with st.form("budget_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    b_dest   = st.text_input("📍 Destination", value="Goa")
                    b_budget = st.number_input("💰 Budget (₹)", min_value=1000, max_value=1000000, value=50000, step=1000)
                with c2:
                    b_travelers = st.number_input("👥 Travelers", min_value=1, max_value=20, value=2)
                    b_days      = st.number_input("📅 Trip Days", min_value=1, max_value=60, value=5)
                with c3:
                    b_transport = st.selectbox("🚗 Transport",      ["flight","train","bus","car"])
                    b_hotel     = st.selectbox("🏨 Hotel Category", ["budget","3-star","4-star","5-star"])
                if st.form_submit_button("💡 Optimize Budget", use_container_width=True):
                    with st.spinner("Calculating optimal budget..."):
                        data, code = api_post("/optimize-budget", {
                            "destination": b_dest, "budget": b_budget,
                            "travelers": b_travelers, "trip_days": b_days,
                            "preferred_transport": b_transport, "hotel_category": b_hotel,
                        })
                    if code == 200 and "error" not in data:
                        _render_budget_result(data, b_budget)
                    else:
                        show_error(data.get("error", "Optimization failed"))

    with tab_nl:
        st.markdown('<div class="stp-card"><div style="font-size:13px;color:#60707f;">Describe your trip in plain English. Example: 4-day Manali trip for 3 people under ₹45,000 by train.</div></div>', unsafe_allow_html=True)
        nl_query = st.text_area("Trip description", value="Plan a 5 day trip to Goa for 2 people with a budget of ₹50000",
                                height=90, label_visibility="collapsed")
        if st.button("🤖 Optimize via AI", key="btn_nl_budget"):
            with st.spinner("AI extracting details and optimizing..."):
                data, code = api_post("/optimize-budget-nl", {"query": nl_query})
            if code == 200 and "error" not in data:
                alloc = data.get("budget_allocation", {})
                _render_budget_result(data, sum(alloc.values()) if alloc else 0)
            else:
                show_error(data.get("error", data.get("detail", "Failed")))

def _render_budget_result(data, total_budget):
    alloc = data.get("budget_allocation", {})
    if not alloc:
        st.json(data)
        return
    show_success("Budget allocated successfully!")
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    total_alloc = sum(alloc.values())
    colors = {"hotel":"#2563eb","accommodation":"#2563eb","transport":"#d97706",
              "food":"#0ea5a4","activities":"#059669","misc":"#dc2626","miscellaneous":"#dc2626"}
    for cat, amount in alloc.items():
        pct   = int((amount / total_alloc) * 100) if total_alloc else 0
        color = colors.get(cat.lower(), "#2563eb")
        st.markdown(f"""
        <div class="budget-bar-wrap">
            <div class="budget-bar-label">
                <span style="text-transform:capitalize;font-weight:600;color:#cbd5e1;">{cat}</span>
                <span style="color:#f8fafc;font-weight:700;">₹{int(amount):,} · {pct}%</span>
            </div>
            <div class="budget-bar-track">
                <div class="budget-bar-fill" style="width:{pct}%;background:{color};"></div>
            </div>
        </div>""", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Budget",  f"₹{int(total_alloc):,}")
    if data.get("per_person_budget"): c2.metric("Per Person", f"₹{int(data['per_person_budget']):,}")
    if data.get("per_day_budget"):    c3.metric("Per Day",    f"₹{int(data['per_day_budget']):,}")

# ─────────────────────────────────────────────────────────────
# PAGE: COMPARE
# ─────────────────────────────────────────────────────────────
def render_compare():
    render_back_button("🧭 Compare Destinations")
    render_page_header(
        "🧭",
        "Compare Destinations",
        "Select multiple destinations and get side-by-side travel context, pricing, and recommendation insights."
    )

    with st.spinner("Loading destinations..."):
        dest_data, code = api_get("/destinations")
    destinations = dest_data.get("destinations", []) if code == 200 else []
    destination_names = [
        d.get("name", "") if isinstance(d, dict) else str(d)
        for d in destinations
    ]
    destination_names = [name for name in destination_names if name]

    if destination_names:
        st.caption("Select 2 to 4 destinations for best comparison quality.")
        selected = st.multiselect(
            "Select 2–4 destinations to compare",
            options=destination_names,
            default=destination_names[:2] if len(destination_names) >= 2 else destination_names
        )
        if st.button("🔍 Compare Now", key="btn_compare"):
            if len(selected) < 2:
                show_error("Please select at least 2 destinations.")
            else:
                with st.spinner("AI is comparing destinations..."):
                    data, code = api_post("/compare-destinations", {"destinations": selected})
                if code == 200:
                    _render_comparison(data, selected)
                else:
                    show_error(data.get("detail", "Comparison failed"))
    else:
        st.warning("No destinations found. Please rebuild the vector store first.")
        if st.button("📄 Rebuild Vector Store", key="btn_load_dest"):
            with st.spinner("Rebuilding..."):
                r, code = api_post("/store-rag", {})
            if code == 200:
                show_success("Done! Please refresh.")
                st.rerun()

def _render_comparison(data, destinations):
    found = data.get("found", [])
    ai_verdict = data.get("ai_verdict", "")

    if not found:
        st.json(data)
        return

    show_success(f"Comparing {len(destinations)} destinations")
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    cols = st.columns(len(found))
    for col, item in zip(cols, found):
        with col:
            dest = item.get("name", "Unknown")
            emoji = ("🏖️" if any(k in dest.lower() for k in ["goa","beach","puri"]) else
                     "🏔️" if any(k in dest.lower() for k in ["manali","shimla","hill"]) else
                     "🏛️" if any(k in dest.lower() for k in ["delhi","agra","jaipur"]) else "🌏")

            attractions = item.get("popular_attractions", [])[:4]
            hotels = item.get("hotel_options", [])[:2]
            pricing = item.get("public_pricing", [])[:2]

            attraction_html = "".join([f'<div class="cmp-point">• {escape(str(a))}</div>' for a in attractions]) or '<div class="cmp-point">No attraction data</div>'
            hotel_html = "".join([f'<div class="cmp-point">• {escape(str(h))}</div>' for h in hotels]) or '<div class="cmp-point">No hotel data</div>'
            pricing_html = "".join([f'<div class="cmp-point">• {escape(str(p))}</div>' for p in pricing]) or '<div class="cmp-point">No pricing data</div>'

            st.markdown(f"""
            <div class="stp-card">
                <div style="text-align:center;font-size:32px;margin-bottom:8px;">{emoji}</div>
                <div style="text-align:center;font-weight:700;font-size:16px;color:#2563eb;margin-bottom:10px;">{escape(str(dest))}</div>
                <div class="section-header" style="margin:6px 0 8px;">Top Attractions</div>
                <div>{attraction_html}</div>
                <div class="section-header" style="margin:10px 0 8px;">Price Snapshot</div>
                <div>{pricing_html}</div>
                <div class="section-header" style="margin:10px 0 8px;">Hotel Options</div>
                <div>{hotel_html}</div>
                <div style="font-size:12px;color:#60707f;margin-top:10px;">
                    <b>Best time:</b> {escape(str(item.get("best_time") or "Not specified"))}
                </div>
            </div>""", unsafe_allow_html=True)

    if ai_verdict:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        with st.expander("AI Comparison Verdict", expanded=True):
            st.write(ai_verdict)


# ─────────────────────────────────────────────────────────────
# PAGE: EXTERNAL TRAVEL TOOLS
# ─────────────────────────────────────────────────────────────
def _render_external_result(title: str, payload: dict):
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='section-header'>{title}</div>", unsafe_allow_html=True)

    response_type = payload.get("type", "result")
    data = payload.get("data", payload)

    st.markdown(f"<span class='badge-info'>Tool: {response_type}</span>", unsafe_allow_html=True)

    if isinstance(data, (dict, list)):
        st.json(data)
        return

    text = str(data).strip()
    if not text:
        st.info("No data returned.")
        return

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) <= 1:
        st.markdown(f"<div class='stp-card'>{escape(text)}</div>", unsafe_allow_html=True)
        return

    bullet_html = "".join([f"<div class='cmp-point'>• {escape(line)}</div>" for line in lines])
    st.markdown(f"<div class='stp-card'>{bullet_html}</div>", unsafe_allow_html=True)


def render_external_tools():
    render_back_button("🌐 External Travel Tools")
    render_page_header(
        "🌐",
        "External Travel Tools",
        "Access live weather, flights, hotels, and places using the external travel service."
    )
    st.markdown(
        '<div class="assist-note">Use these tools for real-time travel context. Results depend on your API keys and external provider availability.</div>',
        unsafe_allow_html=True,
    )

    tab_weather, tab_flights, tab_hotels, tab_places = st.tabs([
        "🌤 Weather",
        "✈️ Flights",
        "🏨 Hotels",
        "📍 Places"
    ])

    with tab_weather:
        with st.container(border=True):
            with st.form("ext_weather_form"):
                city = st.text_input("City", value="Goa", placeholder="Enter city name")
                submit = st.form_submit_button("Get Weather", use_container_width=True)

            if submit:
                with st.spinner("Fetching weather data..."):
                    data, code = api_post("/tools/external-travel", {"type": "weather", "city": city})
                if code == 200 and "error" not in data:
                    show_success("Weather data fetched")
                    _render_external_result("Weather Forecast", data)
                else:
                    show_error(data.get("error", data.get("detail", "Weather request failed")))

    with tab_flights:
        with st.container(border=True):
            with st.form("ext_flights_form"):
                c1, c2 = st.columns(2)
                with c1:
                    origin = st.text_input("Origin", value="Bangalore")
                    depart_date = st.date_input("Departure Date", value=date.today() + timedelta(days=10), key="ext_depart_date")
                with c2:
                    destination = st.text_input("Destination", value="Delhi")
                    return_date = st.date_input("Return Date (optional)", value=date.today() + timedelta(days=13), key="ext_return_date")
                submit = st.form_submit_button("Search Flights", use_container_width=True)

            if submit:
                payload = {
                    "type": "flights",
                    "origin": origin,
                    "destination": destination,
                    "date": str(depart_date),
                }
                if return_date:
                    payload["return_date"] = str(return_date)

                with st.spinner("Searching flights..."):
                    data, code = api_post("/tools/external-travel", payload)
                if code == 200 and "error" not in data:
                    show_success("Flight results fetched")
                    _render_external_result("Flight Options", data)
                else:
                    show_error(data.get("error", data.get("detail", "Flights request failed")))

    with tab_hotels:
        with st.container(border=True):
            with st.form("ext_hotels_form"):
                c1, c2 = st.columns(2)
                with c1:
                    city = st.text_input("City", value="Goa", key="ext_hotel_city")
                    check_in = st.date_input("Check-in", value=date.today() + timedelta(days=10), key="ext_check_in")
                with c2:
                    check_out = st.date_input("Check-out", value=date.today() + timedelta(days=13), key="ext_check_out")
                submit = st.form_submit_button("Find Hotels", use_container_width=True)

            if submit:
                if check_out <= check_in:
                    show_error("Check-out date must be after check-in date.")
                else:
                    payload = {
                        "type": "hotels",
                        "city": city,
                        "check_in": str(check_in),
                        "check_out": str(check_out),
                    }
                    with st.spinner("Fetching hotel options..."):
                        data, code = api_post("/tools/external-travel", payload)
                    if code == 200 and "error" not in data:
                        show_success("Hotel data fetched")
                        _render_external_result("Hotel Options", data)
                    else:
                        show_error(data.get("error", data.get("detail", "Hotels request failed")))

    with tab_places:
        with st.container(border=True):
            with st.form("ext_places_form"):
                city = st.text_input("City", value="Goa", key="ext_places_city")
                submit = st.form_submit_button("Find Places", use_container_width=True)

            if submit:
                with st.spinner("Fetching popular places..."):
                    data, code = api_post("/tools/external-travel", {"type": "places", "city": city})
                if code == 200 and "error" not in data:
                    show_success("Places data fetched")
                    _render_external_result("Top Places", data)
                else:
                    show_error(data.get("error", data.get("detail", "Places request failed")))

# ─────────────────────────────────────────────────────────────
# PAGE: PREFERENCES
# ─────────────────────────────────────────────────────────────
def render_preferences():
    render_back_button("⚙️ My Preferences")
    render_page_header(
        "⚙️",
        "My Preferences",
        "Save your default travel profile to personalize future itinerary generation."
    )

    existing, code = api_get(f"/my-preferences/{st.session_state.user_id}")
    if code == 200:
        show_success("Preferences loaded from server")
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    else:
        existing = {}

    with st.container(border=True):
        with st.form("pref_form"):
            c1, c2 = st.columns(2)
            with c1:
                tt_opts  = ["leisure","adventure","business","cultural","honeymoon"]
                tr_opts  = ["flight","train","bus","car"]
                pref_tt  = st.selectbox("✈️ Trip Type",    tt_opts,
                    index=tt_opts.index(existing.get("preferred_trip_type","leisure")) if existing.get("preferred_trip_type") in tt_opts else 0)
                pref_tr  = st.selectbox("🚗 Transport",    tr_opts,
                    index=tr_opts.index(existing.get("preferred_transport","flight")) if existing.get("preferred_transport") in tr_opts else 0)
                pref_bmin = st.number_input("💸 Min Budget (₹)", value=existing.get("budget_min") or 10000, step=1000)
            with c2:
                ht_opts  = ["budget","3-star","4-star","5-star","luxury"]
                fp_opts  = ["vegetarian","non-vegetarian","vegan","any"]
                pref_ht  = st.selectbox("🏨 Hotel",        ht_opts,
                    index=ht_opts.index(existing.get("preferred_hotel_type","3-star")) if existing.get("preferred_hotel_type") in ht_opts else 1)
                pref_fp  = st.selectbox("🍽 Food",         fp_opts,
                    index=fp_opts.index(existing.get("food_preference","vegetarian")) if existing.get("food_preference") in fp_opts else 0)
                pref_bmax = st.number_input("💰 Max Budget (₹)", value=existing.get("budget_max") or 100000, step=1000)
            cl_opts  = ["any","tropical","cold","moderate","desert","coastal"]
            pref_cl  = st.selectbox("🌡 Climate",      cl_opts,
                index=cl_opts.index(existing.get("preferred_climate","any")) if existing.get("preferred_climate") in cl_opts else 0)
            if st.form_submit_button("💾 Save Preferences", use_container_width=True):
                data, code = api_post("/save-preferences", {
                    "user_id": st.session_state.user_id,
                    "preferred_trip_type": pref_tt, "preferred_transport": pref_tr,
                    "preferred_hotel_type": pref_ht, "food_preference": pref_fp,
                    "preferred_climate": pref_cl,
                    "budget_min": int(pref_bmin), "budget_max": int(pref_bmax),
                })
                if code == 200:
                    show_success(data.get("message", "Saved!"))
                else:
                    show_error(data.get("detail", "Failed to save"))

# ─────────────────────────────────────────────────────────────
# PAGE: CONVERSATIONS
# ─────────────────────────────────────────────────────────────
def render_conversations():
    render_back_button("📋 Conversation History")
    render_page_header(
        "📋",
        "Conversation History",
        "Review your previous AI chats and tool interactions for continuity and planning context."
    )

    with st.spinner("Loading..."):
        data, code = api_get("/conversations", params={"user_id": st.session_state.user_id})
    if code != 200:
        show_error(data.get("detail", "Could not load conversations"))
        return

    convos = data.get("conversations", [])
    c1, c2 = st.columns(2)
    c1.metric("Total Conversations", data.get("total_conversations", 0))
    c2.metric("Logged In As", st.session_state.user_email)

    if not convos:
        st.markdown("""
        <div class="stp-card" style="text-align:center;padding:40px;">
            <div style="font-size:36px;margin-bottom:12px;">💬</div>
            <div style="font-size:15px;color:#60707f;">No conversations yet. Start chatting!</div>
        </div>""", unsafe_allow_html=True)
        return

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    for convo in convos:
        ts   = convo.get("created_at", "")[:16].replace("T", " ")
        tool = convo.get("tool_used", "")
        with st.expander(f"💬 {convo['user_message'][:70]}... · {ts}"):
            st.markdown(f'<div class="user-bubble">{escape(str(convo["user_message"]))}</div>', unsafe_allow_html=True)
            formatted = _format_assistant_response(convo.get("assistant_response", ""))
            st.markdown(f'<div class="bot-bubble">{_to_pretty_html(formatted)}</div>', unsafe_allow_html=True)
            if tool:
                st.markdown(f'<span class="badge-info">🛠 Tool: {tool}</span>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# MAIN ROUTER
# ─────────────────────────────────────────────────────────────
def main():
    if not st.session_state.logged_in:
        render_login_page()
        return

    render_top_nav()   # always-visible top bar, replaces sidebar

    page = st.session_state.get("page", "home")
    if   page == "home":          render_dashboard()
    elif page == "chat":          render_chat()
    elif page == "itinerary":     render_itinerary()
    elif page == "budget":        render_budget()
    elif page == "compare":       render_compare()
    elif page == "external_tools": render_external_tools()
    elif page == "preferences":   render_preferences()
    elif page == "conversations": render_conversations()
    else:                         render_dashboard()

main()

