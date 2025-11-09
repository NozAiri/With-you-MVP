# app.py — With You.（端末Cookie × 入室コードで一意化 / ADMIN固定コード）
# 2025-11-09 fix2:
#  - Cookie無効でも入室OK（セッション内一時IDで代替）
#  - 相談欄 value衝突修正（Session統一管理）

from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import streamlit as st
import json, time, re, uuid, os, hashlib
import altair as alt

# ================== 基本設定 ==================
st.set_page_config(page_title="With You.", page_icon="🌙", layout="centered", initial_sidebar_state="collapsed")
ADMIN_MASTER_CODE = "uneiairi0931"   # 運営はこれだけ

# ================== Firestore ==================
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

# ================== Cookie ==================
COOKIES_OK = False
COOKIE_PASSWORD = st.secrets.get("COOKIE_PASSWORD", os.environ.get("COOKIES_PW", "withyou-cookie-v1"))
try:
    from streamlit_cookies_manager import EncryptedCookieManager
    cookies = EncryptedCookieManager(prefix="withyou_", password=COOKIE_PASSWORD)
    COOKIES_OK = cookies.ready()
except Exception:
    COOKIES_OK = False
    cookies = None

def get_device_id() -> Optional[str]:
    if COOKIES_OK:
        did = cookies.get("device_id")
        if not did:
            did = uuid.uuid4().hex
            cookies.set("device_id", did, expires_at=datetime.now()+timedelta(days=365*5))
            cookies.save()
        return did
    return None

# ================== スタイル ==================
def inject_css():
    st.markdown("""
<style>
:root{
  --text:#182742; --muted:#63728a; --panel:#ffffffee; --panel-brd:#e1e9ff;
  --shadow:0 14px 34px rgba(40,80,160,.12);
  --grad:
    radial-gradient(1400px 600px at -10% -10%, #e8f1ff 0%, rgba(232,241,255,0) 60%),
    radial-gradient(1200px 500px at 110% -10%, #ffeef6 0%, rgba(255,238,246,0) 60%),
    radial-gradient(1200px 500px at 50% 110%, #e9fff7 0%, rgba(233,255,247,0) 60%),
    linear-gradient(180deg, #f9fbff 0%, #eef5ff 100%);
}
html, body, .stApp{ background:var(--grad); color:var(--text); }
.block-container{ max-width:980px; padding-top:1rem; padding-bottom:2rem }
.card{ background:var(--panel); border:1px solid var(--panel-brd); border-radius:22px; padding:18px; box-shadow:var(--shadow); }
.item{ background:#fff; border:1px solid #e3e8ff; border-radius:18px; padding:16px; box-shadow:var(--shadow) }
.badge{ display:inline-block; padding:.18rem .6rem; border:1px solid #d6e7ff; border-radius:999px; margin-right:.35rem; color:#29466e; background:#f6faff; font-weight:800 }
.tip{ color:#6a7d9e; font-size:.92rem; }
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
.bigbtn{ margin-bottom:12px; }
.bigbtn .stButton>button{
  width:100%; text-align:left; border-radius:22px; border:1px solid #dfe6ff; box-shadow:var(--shadow);
  padding:18px 18px 16px; white-space:pre-wrap; line-height:1.35;
  background:linear-gradient(135deg,#ffffff 0%,#eef5ff 100%); color:#132748; font-weight:600;
}
.bigbtn .stButton>button::first-line{ font-weight:900; font-size:1.06rem; color:#0f2545; }
.cbt-card{ background:#fff; border:1px solid #e3e8ff; border-radius:18px; padding:18px 18px 14px; box-shadow:0 6px 20px rgba(31,59,179,0.06); margin-bottom:14px; }
.cbt-heading{ font-weight:900; font-size:1.05rem; color:#1b2440; margin:0 0 6px 0;}
.cbt-sub{ color:#63728a; font-size:0.92rem; margin:-2px 0 10px 0;}
.ok-chip{ display:inline-block; padding:2px 8px; border-radius:999px; background:#e8fff3; color:#156f3a; font-size:12px; border:1px solid #b9f3cf; }
</style>
""", unsafe_allow_html=True)
inject_css()

# ================== 共通関数 ==================
def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

CRISIS_PATTERNS = [r"死にたい", r"消えたい", r"自殺", r"希死", r"傷つけ(たい|てしまう)", r"\bOD\b", r"助けて"]
def crisis(text: str) -> bool:
    if not text: return False
    for p in CRISIS_PATTERNS:
        if re.search(p, text):
            return True
    return False

# ================== セッション初期化 ==================
st.session_state.setdefault("_auth_ok", False)
st.session_state.setdefault("role", None)
st.session_state.setdefault("user_id", "")
st.session_state.setdefault("nickname", "")
st.session_state.setdefault("code", "")
st.session_state.setdefault("view", "HOME")
st.session_state.setdefault("_local_logs", {"note":[], "breath":[], "study":[]})
st.session_state.setdefault("_did_src", "")

# ✅ 相談タブ初期値追加（重複防止）
st.session_state.setdefault("c_msg", "")
st.session_state.setdefault("c_topics", [])
st.session_state.setdefault("c_anon", True)
st.session_state.setdefault("c_name", "")

# ================== 入室処理 ==================
def try_enter_with_code(code: str, nickname: str) -> Tuple[bool, str, str]:
    code = (code or "").strip()
    if not code:
        return False, "", "コードを入力してください。"
    if code == ADMIN_MASTER_CODE:
        return True, "admin", nickname or "admin"
    cur_did = get_device_id()
    did_src = "cookie"
    if cur_did is None:
        cur_did = st.session_state.setdefault("_session_did", uuid.uuid4().hex)
        did_src = "session"
    user_hash = sha256_hex(f"{cur_did}:{code}")
    display_user_id = user_hash[:10]
    if FIRESTORE_ENABLED and DB is not None:
        try:
            DB.collection("users_meta").document(user_hash).set({
                "created_at": datetime.now(timezone.utc),
                "nickname": nickname or "",
                "device_hint": (cur_did or "")[:6],
                "ver": "device+code@v2" if did_src=="cookie" else "session-fallback@v2"
            }, merge=True)
        except Exception:
            pass
    st.session_state["user_id"] = display_user_id
    st.session_state["nickname"] = nickname or ""
    st.session_state["_did_src"] = did_src
    return True, "user", nickname or display_user_id

# ================== ナビ関連 ==================
BASE_SECTIONS = [
    ("HOME","🏠 ホーム"),
    ("SHARE","🏫 今日を伝える"),
    ("SESSION","🌙 リラックス"),
    ("NOTE","📝 ノート"),
    ("STUDY","📚 Study Tracker"),
    ("REVIEW","📒 ふりかえり"),
    ("CONSULT","🕊 相談"),
]
ADMIN_SECTION = ("ADMIN","🛡 運営")

def _sections_for_role():
    if st.session_state.get("role") == "admin":
        return BASE_SECTIONS + [ADMIN_SECTION]
    return BASE_SECTIONS

def navigate(to_key:str):
    st.session_state.view = to_key

def top_tabs():
    if st.session_state.view=="HOME": return
    active = st.session_state.view
    sections = _sections_for_role()
    st.markdown('<div class="top-tabs">', unsafe_allow_html=True)
    cols = st.columns(len(sections))
    for i,(key,label) in enumerate(sections):
        with cols[i]:
            cls = "active" if key==active else ""
            st.markdown(f"<div class='{cls}'>", unsafe_allow_html=True)
            if st.button(label,key=f"tab_{key}"):
                navigate(key); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def top_status():
    role_txt = '運営' if st.session_state.role=='admin' else f'利用者（{st.session_state.nickname or st.session_state.user_id}）'
    fs_txt = "接続済み" if FIRESTORE_ENABLED else "未接続"
    cookie_txt = "ON" if COOKIES_OK else "OFF"
    st.markdown(f"<div class='card'><div class='tip'>ログイン中：{role_txt} / Firestore：{fs_txt} / Cookie：{cookie_txt}</div></div>", unsafe_allow_html=True)

# ================== HOME ==================
def view_home():
    st.markdown("""
<div class="card">
🌙 With You  
気持ちを整える、やさしいノートです。

🔒 「今日を伝える」と「相談」だけが運営に届きます。
それ以外の記録は、この端末だけに残ります。
</div>
""", unsafe_allow_html=True)
    st.button("🏫 今日を伝える", on_click=lambda: navigate("SHARE"), key="home1")
    st.button("🌙 リラックス", on_click=lambda: navigate("SESSION"), key="home2")
    st.button("📝 ノート", on_click=lambda: navigate("NOTE"), key="home3")
    st.button("📚 Study Tracker", on_click=lambda: navigate("STUDY"), key="home4")
    st.button("📒 ふりかえり", on_click=lambda: navigate("REVIEW"), key="home5")
    st.button("🕊 相談", on_click=lambda: navigate("CONSULT"), key="home6")

# ================== 相談（修正版） ==================
CONSULT_TOPICS = ["体調","勉強","人間関係","家庭","進路","いじめ","メンタルの不調","その他"]
def view_consult():
    st.markdown("### 🕊 相談（匿名OK）")
    st.caption("誰にも言いにくいことでも大丈夫。お名前は空欄のまま送れます。")

    to_whom = st.radio("相談先", ["カウンセラーに相談したい","先生に伝えたい"], horizontal=True, key="c_to")
    topics  = st.multiselect("内容（当てはまるもの）", CONSULT_TOPICS,
                             default=st.session_state.get("c_topics", []), key="c_topics")
    anonymous = st.checkbox("匿名で送る", value=st.session_state.get("c_anon", True), key="c_anon")
    name = "" if st.session_state.get("c_anon", True) else st.text_input("お名前（任意）", key="c_name")
    msg = st.text_area("ご相談内容", height=220, key="c_msg")

    if crisis(msg):
        st.warning("とても苦しい状況かもしれません。地域の相談窓口や信頼できる大人にも相談してください。")

    disabled = not FIRESTORE_ENABLED or (msg.strip()=="")
    label = "🕊 送信する" if FIRESTORE_ENABLED else "🕊 送信（無効：未接続）"
    if st.button(label, type="primary", disabled=disabled, key="c_submit"):
        payload = {
            "ts": datetime.now(timezone.utc),
            "user_id": st.session_state.user_id,
            "message": msg.strip(),
            "topics": topics,
            "intent": "counselor" if to_whom.startswith("カウンセラー") else "teacher",
            "anonymous": bool(anonymous),
            "name": name.strip() if name else "",
        }
        ok = safe_db_add("consult_msgs", payload)
        if ok:
            st.success("送信しました。ありがとうございます。")
            st.session_state.update({
                "c_msg": "",
                "c_topics": [],
                "c_anon": True,
                "c_name": "",
            })
            st.rerun()
        else:
            st.error("送信できませんでした。")

# ================== 他ビュー省略 ==================
# （NOTE, SHARE, STUDY, REVIEW, ADMIN は前バージョンと同じ内容でOK）

# ================== ルーター ==================
def main_router():
    v = st.session_state.view
    if v == "HOME": view_home()
    elif v == "CONSULT": view_consult()
    else: view_home()

# ================== ログインUI ==================
def login_ui() -> bool:
    if st.session_state._auth_ok: return True
    st.markdown("### 🌙 With You")
    code = st.text_input("🔑 入室コード", key="login_code")
    nick = st.text_input("🪞 ニックネーム（任意）", key="login_nick")
    if st.button("➡️ はじめる", key="login_go"):
        ok, role, msg = try_enter_with_code(code, nick)
        if ok:
            st.session_state["_auth_ok"]=True
            st.session_state["role"]=role
            st.session_state["nickname"]=nick
            st.session_state["code"]=code
            st.session_state["view"]="ADMIN" if role=="admin" else "HOME"
            st.rerun()
        else:
            st.error(msg)
    return False

def logout_btn():
    with st.sidebar:
        if st.button("🚪 ログアウト"):
            keep_cookie = cookies.get("device_id") if COOKIES_OK else None
            st.session_state.clear()
            if COOKIES_OK and keep_cookie:
                cookies.set("device_id", keep_cookie, expires_at=datetime.now()+timedelta(days=365*5))
                cookies.save()
            st.rerun()

# ================== 実行 ==================
if st.session_state.get("_auth_ok", False):
    logout_btn()
    top_tabs()
    top_status()
    main_router()
else:
    login_ui()
