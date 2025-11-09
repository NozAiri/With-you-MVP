# app.py — Sora / With You.（HOME=説明＋下段ボタンのみ／やさしいフォント／グラデ）
# 保存方針：
#  - Firestore保存＝「今日を伝える」「相談」だけ（運営が把握）
#  - それ以外（ノート／リラックス／Study／レビュー）は端末のみ（DL＋このセッション内の履歴）

from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import pandas as pd
import streamlit as st
import json, time, re, os
import altair as alt

# ========= Page config =========
st.set_page_config(page_title="With You.", page_icon="🌙", layout="centered", initial_sidebar_state="collapsed")

# ========= Fonts / Styles =========
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Varela+Round&display=swap');

:root{
  --text:#182742; --muted:#63728a; --panel:#ffffffee; --panel-brd:#e1e9ff;
  --shadow:0 14px 34px rgba(40,80,160,.12);
  --grad:
    radial-gradient(1400px 600px at -10% -10%, #e8f1ff 0%, rgba(232,241,255,0) 60%),
    radial-gradient(1200px 500px at 110% -10%, #ffeef6 0%, rgba(255,238,246,0) 60%),
    radial-gradient(1200px 500px at 50% 110%, #e9fff7 0%, rgba(233,255,247,0) 60%),
    linear-gradient(180deg, #f9fbff 0%, #eef5ff 100%);
}

html, body, .stApp{
  font-family:"Nunito","Varela Round","Noto Sans JP",ui-rounded,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  color:var(--text);
  background:var(--grad);
}
.block-container{ max-width:980px; padding-top:1rem; padding-bottom:2rem }

/* ------- top tabs（HOMEでは非表示） ------- */
.top-tabs{
  position: sticky; top: 0; z-index: 50;
  background: rgba(250,253,255,.85); backdrop-filter:saturate(160%) blur(8px);
  border:1px solid #dfe6ff; border-radius:16px; box-shadow:0 12px 24px rgba(70,120,200,.12);
  padding:6px 8px; margin-bottom:14px;
}
.top-tabs .stButton>button{
  width:100%; height:40px; border-radius:12px; font-weight:800;
  background:#f6f9ff; border:1px solid #e1eaff; color:#2b4772;
}
.top-tabs .active .stButton>button{ background:#eaf3ff; border-bottom:3px solid #5EA3FF }

/* ------- cards / helpers ------- */
.card{ background:var(--panel); border:1px solid var(--panel-brd); border-radius:22px; padding:18px; box-shadow:var(--shadow) }
.item{ background:#fff; border:1px solid var(--panel-brd); border-radius:18px; padding:16px; box-shadow:var(--shadow) }
.item .meta{ color:var(--muted); font-size:.9rem; margin-bottom:.2rem }
.badge{ display:inline-block; padding:.18rem .6rem; border:1px solid #d6e7ff; border-radius:999px; margin-right:.35rem; color:#29466e; background:#f6faff; font-weight:800 }
.tip{ color:#6a7d9e; font-size:.92rem; }

/* ------- big buttons on HOME ------- */
.bigbtn{ margin-bottom:12px; }
.bigbtn .stButton>button{
  width:100%; text-align:left; border-radius:22px; border:1px solid #dfe6ff; box-shadow:var(--shadow);
  padding:18px 18px 16px; white-space:pre-wrap; line-height:1.35;
  background:linear-gradient(135deg,#ffffff 0%,#eef5ff 100%); color:#132748; font-weight:600;
}
.bigbtn .stButton>button::first-line{ font-weight:900; font-size:1.06rem; color:#0f2545; }
.bigbtn .stButton>button:hover{ transform:translateY(-1px); box-shadow:0 18px 30px rgba(70,120,200,.14) }

/* ------- emotion pills ------- */
.emopills{display:grid; grid-template-columns:repeat(3,1fr); gap:10px}
@media (min-width:820px){ .emopills{ grid-template-columns:repeat(6,1fr) } }
.emopills .chip .stButton>button{
  background:linear-gradient(135deg,#ffffff 0%,#eef5ff 100%) !important; color:#1d3457 !important;
  border:2px solid #d6e7ff !important; border-radius:16px !important;
  box-shadow:0 6px 16px rgba(100,140,200,.08) !important; font-weight:900 !important; padding:12px 12px !important;
}
.emopills .chip.on .stButton>button{ border:2px solid #5EA3FF !important; background:#eefdff !important }

.cbt-card{ background:#fff; border:1px solid #e3e8ff; border-radius:18px; padding:18px 18px 14px; box-shadow:0 6px 20px rgba(31,59,179,0.06); margin-bottom:14px; }
.cbt-heading{ font-weight:900; font-size:1.05rem; color:#1b2440; margin:0 0 6px 0;}
.cbt-sub{ color:#63728a; font-size:0.92rem; margin:-2px 0 10px 0;}
.ok-chip{ display:inline-block; padding:2px 8px; border-radius:999px; background:#e8fff3; color:#156f3a; font-size:12px; border:1px solid #b9f3cf; }
</style>
""", unsafe_allow_html=True)

inject_css()

# ========= Firestore（今日を伝える／相談のみ） =========
FIRESTORE_ENABLED = True
try:
    from google.cloud import firestore
    import google.oauth2.service_account as service_account

    @st.cache_resource(show_spinner=False)
    def firestore_client():
        creds = service_account.Credentials.from_service_account_info(st.secrets["FIREBASE_SERVICE_ACCOUNT"])
        return firestore.Client(
            project=st.secrets["FIREBASE_SERVICE_ACCOUNT"]["project_id"],
            credentials=creds
        )
    DB = firestore_client()
except Exception:
    FIRESTORE_ENABLED = False
    DB = None

def safe_db_add(collection: str, payload: dict) -> bool:
    if not FIRESTORE_ENABLED or DB is None:
        return False
    try:
        DB.collection(collection).add(payload)
        return True
    except Exception:
        return False

# ========= Local logs =========
def init_local_logs():
    st.session_state.setdefault("_local_logs", {"note":[], "breath":[], "study":[]})
init_local_logs()

def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

st.session_state.setdefault("_auth_ok", False)
st.session_state.setdefault("role", None)
st.session_state.setdefault("user_id", "")
st.session_state.setdefault("view", "HOME")
st.session_state.setdefault("_nav_stack", [])
st.session_state.setdefault("_breath_running", False)
st.session_state.setdefault("_breath_stop", False)

# ========= 運営パスワード（固定設定） =========
def admin_pass() -> str:
    return "uneiairi0931"

CRISIS_PATTERNS = [r"死にたい", r"消えたい", r"自殺", r"希死", r"傷つけ(たい|てしまう)", r"リスカ", r"\bOD\b", r"助けて"]
def crisis(text: str) -> bool:
    if not text: return False
    for p in CRISIS_PATTERNS:
        if re.search(p, text):
            return True
    return False

# ========= Top Tabs =========
SECTIONS = [
    ("HOME",   "🏠 ホーム"),
    ("SHARE",  "🏫 今日を伝える"),
    ("SESSION","🌙 リラックス"),
    ("NOTE",   "📝 ノート"),
    ("STUDY",  "📚 Study Tracker"),
    ("REVIEW", "📒 ふりかえり"),
    ("CONSULT","🕊 相談"),
]

def navigate(to_key: str, push: bool = True):
    cur = st.session_state.view
    if push and cur != to_key:
        st.session_state._nav_stack.append(cur)
    st.session_state.view = to_key

def top_tabs():
    if st.session_state.view == "HOME":  
        return
    active = st.session_state.view
    st.markdown('<div class="top-tabs">', unsafe_allow_html=True)
    cols = st.columns(len(SECTIONS))
    for i, (key, label) in enumerate(SECTIONS):
        with cols[i]:
            cls = "active" if key == active else ""
            st.markdown(f"<div class='{cls}'>", unsafe_allow_html=True)
            if st.button(label, key=f"tab_{key}"):
                navigate(key, push=False)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def top_status():
    role_txt = '運営' if st.session_state.role=='admin' else (f'利用者（{st.session_state.user_id}）' if st.session_state.user_id else '未ログイン')
    fs_txt = "接続済み" if FIRESTORE_ENABLED else "未接続（オフライン送信）"
    st.markdown('<div class="card" style="padding:8px 12px; margin-bottom:10px">', unsafe_allow_html=True)
    st.markdown(f"<div class='tip'>ログイン中：{role_txt} / データ共有：{fs_txt}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ========= HOME画面（説明＋ボタン群） =========
def home_big_button(title: str, sub: str, target_view: str, key: str, emoji: str):
    label = f"{emoji} {title}\n{sub}"
    with st.container():
        st.markdown('<div class="bigbtn">', unsafe_allow_html=True)
        if st.button(label, key=f"homebtn_{key}"):
            navigate(target_view, push=True); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

def home_intro_block():
    st.markdown("""
<div class="card" style="margin-bottom:12px">
  <div style="font-weight:900; font-size:1.05rem; margin-bottom:.3rem">🌙 With You について</div>
  <div style="color:#3a4a6a; line-height:1.65; white-space:pre-wrap">
毎日の気持ちを整えて、必要なときに先生や周りとつながれる、やさしいツールボックスです。
いまの自分に合いそうなカードを選んで、短い時間からはじめてみてください。
  </div>
</div>
""", unsafe_allow_html=True)

def view_home():
    home_intro_block()
    home_big_button("今日を伝える", "今日の気分や体調を先生や学校と共有します。", "SHARE", "OPEN_SHARE", "🏫")
    c1, c2 = st.columns(2)
    with c1: home_big_button("リラックス", "呼吸ワークで心を整えます。", "SESSION", "OPEN_SESSION", "🌙")
    with c2: home_big_button("心を整えるノート", "感じたことを言葉にして、今の自分を整理します。", "NOTE", "OPEN_NOTE", "📝")
    c3, c4 = st.columns(2)
    with c3: home_big_button("Study Tracker", "学習時間をふりかえり、進捗を見える形にします。", "STUDY", "OPEN_STUDY", "📚")
    with c4: home_big_button("ふりかえり", "このセッションでの記録を見返せます。", "REVIEW", "OPEN_REVIEW", "📒")
    home_big_button("相談する", "不安や悩みを安心して伝え、必要なサポートにつながります。", "CONSULT", "OPEN_CONSULT", "🕊")

# ========= Auth（ログイン画面） =========
def auth_ui() -> bool:
    if st.session_state._auth_ok: return True
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 🔐 ログイン")
        t1, t2 = st.tabs(["利用者として入る", "運営として入る"])
        with t1:
            uid = st.text_input("ユーザーID", placeholder="例: omu-2025-xxxx", key="auth_uid")
            if st.button("➡️ 入る（利用者）", type="primary", key="auth_user"):
                if uid.strip() == "":
                    st.warning("ユーザーIDをご入力ください。")
                else:
                    st.session_state.user_id = uid.strip(); st.session_state.role = "user"
                    st.session_state._auth_ok = True; st.success("ようこそ。"); return True
        with t2:
            pw = st.text_input("運営パスコード", type="password", key="auth_pw")
            if st.button("➡️ 入る（運営）", key="auth_admin"):
                if pw == admin_pass():
                    st.session_state.user_id = "_admin_"; st.session_state.role = "admin"
                    st.session_state._auth_ok = True; st.success("運営ログインが完了しました。"); return True
                else:
                    st.error("パスコードが違います。")
        st.markdown("</div>", unsafe_allow_html=True)
    return False

def logout_btn():
    with st.sidebar:
        if st.button("🚪 ログアウト", key="logout_btn"):
            st.session_state.clear()
            st.rerun()

# ========= Router =========
def main_router():
    v = st.session_state.view
    if v == "HOME":   view_home()
    elif v == "SESSION": st.write("呼吸ワーク画面")
    elif v == "NOTE": st.write("CBTノート画面")
    elif v == "SHARE": st.write("今日を伝える画面")
    elif v == "CONSULT": st.write("相談画面")
    elif v == "REVIEW": st.write("ふりかえり画面")
    elif v == "STUDY": st.write("Study Tracker画面")
    else: view_home()

# ========= App =========
if auth_ui():
    logout_btn()
    top_tabs()
    top_status()
    main_router()
