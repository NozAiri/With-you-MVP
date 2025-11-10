# app.py — With You.（共通パス＋自分だけの名前｜登録先着専有・同時利用OK・Cookie/URL/本人コードなし｜ADMIN対応）
from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, Tuple
import streamlit as st
import pandas as pd
import altair as alt
import hashlib, hmac, unicodedata, re, json, os, time

# ================== ページ設定 ==================
st.set_page_config(page_title="With You.", page_icon="🌙", layout="centered", initial_sidebar_state="collapsed")

# ================== Firestore 接続 ==================
FIRESTORE_ENABLED = True
try:
    from google.cloud import firestore
    import google.oauth2.service_account as service_account

    @st.cache_resource(show_spinner=False)
    def firestore_client():
        creds = service_account.Credentials.from_service_account_info(st.secrets["FIREBASE_SERVICE_ACCOUNT"])
        return firestore.Client(project=st.secrets["FIREBASE_SERVICE_ACCOUNT"]["project_id"], credentials=creds)
    DB = firestore_client()
except Exception:
    FIRESTORE_ENABLED = False
    DB = None

# ================== 運営パスワード ==================
# secrets/env優先。未設定時は既定値 "uneiaiei0931"
ADMIN_MASTER_CODE = (
    st.secrets.get("ADMIN_MASTER_CODE")
    or os.environ.get("ADMIN_MASTER_CODE")
    or "uneiaiei0931"
)

# ================== アプリ秘密鍵（HMAC用） ==================
APP_SECRET = st.secrets.get("APP_SECRET") or os.environ.get("APP_SECRET") or "dev-app-secret-change-me"

# ================== ユーティリティ ==================
def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

def hmac_sha256_hex(secret: str, data: str) -> str:
    return hmac.new(secret.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).hexdigest()

def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

HANDLE_ALLOWED_RE = re.compile(r"^[a-z0-9_\-\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]+$")  # 英数_-, ひらがな/カタカナ/漢字
def normalize_handle(s: str) -> str:
    s = (s or "").strip()
    s = unicodedata.normalize("NFKC", s)
    s = s.lower()
    return s

def validate_handle(raw: str) -> Tuple[bool, str]:
    n = normalize_handle(raw)
    if len(n) < 4 or len(n) > 12:
        return False, "4〜12文字で入力してください。"
    if not HANDLE_ALLOWED_RE.match(n):
        return False, "使えるのは、英数字・ひらがな・カタカナ・漢字と「_」「-」です。"
    return True, n

def group_id_from_password(group_password: str) -> str:
    pw = unicodedata.normalize("NFKC", (group_password or "").strip())
    return hmac_sha256_hex(APP_SECRET, f"grp:{pw}")

def user_key(group_id: str, handle_norm: str) -> str:
    return sha256_hex(f"{group_id}:{handle_norm}")

def db_create_user(group_id: str, handle_norm: str) -> Tuple[bool, str]:
    """先着専有：存在すれば失敗。"""
    if not FIRESTORE_ENABLED or DB is None:
        return False, "Firestore未接続です。"
    ref = DB.collection("groups").document(group_id).collection("users").document(handle_norm)
    try:
        ref.create({
            "user_key": user_key(group_id, handle_norm),
            "created_at": datetime.now(timezone.utc),
            "last_login_at": datetime.now(timezone.utc),
        })
        return True, ""
    except Exception:
        # 既に存在 → 使用中エラーにする
        return False, "この名前はもう使われています。他の名前にしてください。"

def db_user_exists(group_id: str, handle_norm: str) -> bool:
    if not FIRESTORE_ENABLED or DB is None:
        return False
    ref = DB.collection("groups").document(group_id).collection("users").document(handle_norm)
    doc = ref.get()
    return doc.exists

def db_touch_login(group_id: str, handle_norm: str):
    if not FIRESTORE_ENABLED or DB is None:
        return
    ref = DB.collection("groups").document(group_id).collection("users").document(handle_norm)
    try:
        ref.set({"last_login_at": datetime.now(timezone.utc)}, merge=True)
    except Exception:
        pass

def safe_db_add(coll: str, payload: dict) -> bool:
    if not FIRESTORE_ENABLED or DB is None:
        return False
    try:
        DB.collection(coll).add(payload)
        return True
    except Exception:
        return False

# ================== 状態 ==================
st.session_state.setdefault("auth_ok", False)
st.session_state.setdefault("mode", "LOGIN")  # "REGISTER" / "LOGIN"
st.session_state.setdefault("group_pw", "")
st.session_state.setdefault("handle_raw", "")
st.session_state.setdefault("group_id", "")
st.session_state.setdefault("handle_norm", "")
st.session_state.setdefault("user_disp", "")  # 表示用
st.session_state.setdefault("view", "HOME")   # 画面
st.session_state.setdefault("flash_msg", "")  # 再描画時の一時メッセージ
st.session_state.setdefault("role", "user")   # "user" or "admin"

# ================== スタイル ==================
def inject_css():
    st.markdown("""
<style>
:root{
  --text:#182742; --muted:#63728a; --panel:#ffffffee; --panel-brd:#e1e9ff; --shadow:0 14px 34px rgba(40,80,160,.12);
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
</style>
""", unsafe_allow_html=True)
inject_css()

# ================== ナビ ==================
def get_sections():
    base = [
        ("HOME",   "🏠 ホーム"),
        ("SHARE",  "🏫 今日を伝える"),
        ("SESSION","🌙 リラックス"),
        ("NOTE",   "📝 ノート"),
        ("STUDY",  "📚 Study Tracker"),
        ("REVIEW", "📒 ふりかえり"),
        ("CONSULT","🕊 相談"),
    ]
    if st.session_state.get("role") == "admin":
        base.append(("ADMIN", "🛠 運営"))
    return base

def top_tabs():
    if st.session_state.view == "HOME": return
    active = st.session_state.view
    st.markdown('<div class="top-tabs">', unsafe_allow_html=True)
    sections = get_sections()
    cols = st.columns(len(sections))
    for i, (key, label) in enumerate(sections):
        with cols[i]:
            cls = "active" if key == active else ""
            st.markdown(f"<div class='{cls}'>", unsafe_allow_html=True)
            if st.button(label, key=f"tab_{key}"):
                st.session_state.view = key; st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def status_bar():
    # フラッシュ（あれば表示→消す）
    if st.session_state.get("flash_msg"):
        st.toast(st.session_state["flash_msg"])
        st.markdown(
            f"<div class='card' style='padding:10px 12px; margin-bottom:10px; border-left:6px solid #69c27a'><b>{st.session_state['flash_msg']}</b></div>",
            unsafe_allow_html=True,
        )
        st.session_state["flash_msg"] = ""

    gid = st.session_state.get("group_id", "")
    handle = st.session_state.get("handle_norm", "")
    disp = st.session_state.get("user_disp", "")
    role = st.session_state.get("role","user")
    fs = "接続済み" if FIRESTORE_ENABLED else "未接続"
    st.markdown('<div class="card" style="padding:8px 12px; margin-bottom:10px">', unsafe_allow_html=True)
    st.markdown(f"<div class='tip'>ログイン中：{disp or handle or '—'} / ロール：{role} / データ共有：{fs}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ================== ログイン / 登録 ==================
def login_register_ui() -> bool:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🌙 With You")
    st.caption("気持ちを整える、やさしいノート。")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("はじめての人（登録）", use_container_width=True, key="btn_reg"):
            st.session_state.mode = "REGISTER"
    with c2:
        if st.button("前に登録した人（ログイン）", use_container_width=True, key="btn_login"):
            st.session_state.mode = "LOGIN"

    st.divider()
    st.markdown("**ご自由なパスワード（みんな共通）**")
    group_pw = st.text_input("パスワード（例：sakura2025）", key="inp_group_pw", label_visibility="collapsed", placeholder="例：sakura2025")
    st.markdown("**自分だけの名前（4〜12文字）**")
    st.caption("同じ名前は1人だけ使えます（先着）。英数字・ひらがな・カタカナ・漢字と _ - が使えます。")
    handle_raw = st.text_input("自分だけの名前", key="inp_handle", label_visibility="collapsed", placeholder="例：mika / ねこ_3 / sora")

    err = ""
    ok_handle, handle_norm = validate_handle(handle_raw)
    if group_pw.strip() == "":
        err = "パスワードを入力してください。"
    elif not ok_handle:
        err = handle_norm  # エラーメッセージ

    mode = st.session_state.mode
    btn_label = "登録してはじめる" if mode == "REGISTER" else "入る"
    disabled = (err != "")
    if st.button(btn_label, type="primary", use_container_width=True, disabled=disabled, key="btn_go"):
        # group_id とハンドルを確定
        gid = group_id_from_password(group_pw)
        st.session_state.group_id = gid
        st.session_state.handle_norm = handle_norm
        st.session_state.user_disp = handle_norm

        # 管理者判定（パスワードがADMIN_MASTER_CODEと完全一致ならadmin）
        if group_pw.strip() == ADMIN_MASTER_CODE:
            st.session_state.role = "admin"
        else:
            st.session_state.role = "user"

        if mode == "REGISTER":
            ok, msg = db_create_user(gid, handle_norm)
            if not ok:
                st.error(msg); st.stop()
            st.session_state.auth_ok = True
            st.session_state.view = "HOME"
            st.session_state.flash_msg = "登録が完了しました。ようこそ！"
            st.rerun()
        else:
            if not db_user_exists(gid, handle_norm):
                st.error("まだ登録がありません。「はじめての人（登録）」から設定してください。"); st.stop()
            db_touch_login(gid, handle_norm)
            st.session_state.auth_ok = True
            st.session_state.view = "HOME"
            st.session_state.flash_msg = "ログインしました。"
            st.rerun()

    if err:
        st.caption(f"⚠️ {err}")

    st.markdown("</div>", unsafe_allow_html=True)
    return False

def logout_btn():
    with st.sidebar:
        if st.button("🚪 ログアウト", key="logout_btn"):
            keep = {"mode": st.session_state.get("mode","LOGIN")}
            st.session_state.clear()
            st.session_state.update(keep)
            st.rerun()

# ================== HOME / 機能UI ==================
def home_intro():
    st.markdown("""
<div class="card" style="margin-bottom:12px">
  <div style="font-weight:900; font-size:1.05rem; margin-bottom:.3rem">🌙 With You</div>
  <div style="color:#3a4a6a; line-height:1.65; white-space:pre-wrap">
気持ちを整える、やさしいノートです。

🏫 <b>今日を伝える</b> と 🕊 <b>相談</b> だけが先生・学校に届きます。
それ以外の記録は <b>この端末だけ</b> に残ります。
  </div>
</div>
""", unsafe_allow_html=True)

def big_button(title: str, sub: str, to_view: str, key: str, emoji: str):
    label = f"{emoji} {title}\n{sub}"
    st.markdown('<div class="bigbtn">', unsafe_allow_html=True)
    if st.button(label, key=f"home_{key}"):
        st.session_state.view = to_view; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def view_home():
    home_intro()
    big_button("今日を伝える", "今日の体調や気分を先生・学校に共有します。", "SHARE", "share", "🏫")
    c1, c2 = st.columns(2)
    with c1: big_button("リラックス", "90秒の呼吸で、いまを落ち着ける。", "SESSION", "session", "🌙")
    with c2: big_button("心を整えるノート", "気持ちを言葉にして、頭の中を整理。", "NOTE", "note", "📝")
    c3, c4 = st.columns(2)
    with c3: big_button("Study Tracker", "学習時間を見える化。", "STUDY", "study", "📚")
    with c4: big_button("ふりかえり", "この端末に残した記録をまとめて確認。", "REVIEW", "review", "📒")
    big_button("相談する", "匿名OK。困りごとがあれば短くでも。", "CONSULT", "consult", "🕊")

# ----- リラックス（簡易） -----
BREATH_PATTERN = (5,2,6)
def breathing_animation(total_sec: int = 90):
    inhale, hold, exhale = BREATH_PATTERN
    cycle = inhale + hold + exhale
    cycles = max(1, round(total_sec / cycle))
    ph = st.empty(); spot = st.empty(); ctrl = st.empty()
    def phase(label, seconds):
        ph.markdown(f"**{label}**")
        spot.markdown(
            f'<div style="display:flex;justify-content:center;align-items:center;padding:10px 0 6px">'
            f'<div style="width:240px;height:240px;border-radius:999px;background:radial-gradient(circle at 50% 40%, #f7fbff, #e8f2ff 60%, #eef8ff 100%);'
            f'box-shadow:0 18px 36px rgba(90,140,190,.14), inset 0 -10px 25px rgba(120,150,200,.15);border:solid #dbe9ff"></div>'
            f'</div>', unsafe_allow_html=True)
        for _ in range(seconds): time.sleep(1)
        return True
    with ctrl.container():
        if st.button("⏹ 停止する", key="breath_stop"): return
    for _ in range(cycles):
        if not phase("吸ってください", inhale): break
        if hold>0 and not phase("止めてください", hold): break
        if not phase("吐いてください", exhale): break
    ph.empty(); spot.empty(); ctrl.empty()

def view_session():
    st.markdown("### 🌙 リラックス（呼吸）")
    st.caption("円が大きくなったら吸って、小さくなったら吐きます。")
    if st.button("🫁 はじめる（90秒）", type="primary", key="breath_start"):
        breathing_animation(90); st.success("お疲れさまでした。ありがとうございます。")

# ----- ノート（ローカル保存） -----
st.session_state.setdefault("_local_logs", {"note":[], "breath":[], "study":[]})

MOODS = [
    {"emoji":"😢","label":"悲しい","key":"sad"},
    {"emoji":"😠","label":"イライラ","key":"anger"},
    {"emoji":"😟","label":"不安","key":"anx"},
    {"emoji":"😔","label":"さみしい","key":"lonely"},
    {"emoji":"😩","label":"しんどい","key":"tired"},
    {"emoji":"😊","label":"少しホッとした","key":"relief"},
    {"emoji":"😄","label":"うれしい","key":"joy"},
    {"emoji":"😕","label":"モヤモヤ","key":"confuse"},
]
def cbt_intro():
    st.markdown("""
<div class="cbt-card">
  <div class="cbt-heading">このワークについて</div>
  <div class="cbt-sub" style="white-space:pre-wrap">
このノートは、考え方や気持ちを整理するためのシンプルなワークです。
自分のペースで、思いつくことを自由に書いてみてください。
  </div>
</div>
""", unsafe_allow_html=True)

def mood_radio() -> Dict:
    st.markdown('<div class="cbt-card">', unsafe_allow_html=True)
    st.markdown('<div class="cbt-heading">🌤 Step 1：今の気持ちは？</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for i, m in enumerate(MOODS):
        with cols[i % 4]:
            if st.button(f"{m['emoji']} {m['label']}", key=f"m_{m['key']}"):
                st.session_state["cbt_mood"] = m
    cur = st.session_state.get("cbt_mood", {"emoji":"","label":"未選択","key":None})
    st.write(f"選択中：**{cur.get('emoji','')} {cur.get('label','')}**")
    intensity = st.slider("今の強さ（0〜100）", 0, 100, 60, key="cbt_int")
    st.markdown("</div>", unsafe_allow_html=True)
    return {"emoji":cur.get("emoji",""), "label":cur.get("label",""), "key":cur.get("key"), "intensity":intensity}

def text_card(title: str, sub: str, key: str, height=120, placeholder="ここに書いてみてね") -> str:
    st.markdown('<div class="cbt-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="cbt-heading">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cbt-sub">{sub}</div>', unsafe_allow_html=True)
    val = st.text_area("", height=height, key=key, placeholder=placeholder, label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)
    return val

def view_note():
    st.markdown("### 📝 心を整えるノート")
    cbt_intro()
    mood = mood_radio()
    trigger = text_card("🫧 きっかけ", "「○○があったからかも」「なんとなく○○って思った」など自由に。", "t_trigger")
    auto   = text_card("💭 よぎった言葉", "頭の中でつぶやいた言葉やイメージ。", "t_auto")
    diary  = text_card("🌙 今日の日記", "気づいたこと・変化・これからのことなど自由に。", "t_diary", height=140)
    if st.button("💾 記録（この端末）", type="primary", key="cbt_save"):
        doc = {"ts": now_iso(), "mood": mood, "trigger": (trigger or "").strip(), "auto": (auto or "").strip(), "diary": (diary or "").strip()}
        st.session_state["_local_logs"]["note"].append(doc)
        st.success("保存しました。（運営には共有されません）")
        st.download_button("⬇️ この記録をダウンロード（JSON）",
                           data=json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8"),
                           file_name=f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                           mime="application/json", key=f"dl_note_{len(st.session_state['_local_logs']['note'])}")

# ----- 今日を伝える（Firestoreに匿名共有） -----
def view_share():
    st.markdown("### 🏫 今日を伝える（匿名）")
    mood = st.radio("気分", ["🙂","😐","😟"], index=1, horizontal=True, key="share_mood")
    body_opts = ["頭痛","腹痛","吐き気","食欲低下","だるさ","その他","なし"]
    body = st.multiselect("体調（当てはまるもの）", body_opts, default=["なし"], key="share_body")
    if "なし" in body and len(body) > 1:
        body = [b for b in body if b != "なし"]
    c1, c2 = st.columns(2)
    with c1: sleep_h = st.number_input("睡眠時間（h）", min_value=0.0, max_value=24.0, value=6.0, step=0.5, key="share_sleep_h")
    with c2: sleep_q = st.radio("睡眠の質", ["ぐっすり","ふつう","浅い"], index=1, horizontal=True, key="share_sleep_q")

    disabled = not FIRESTORE_ENABLED
    label = "📨 先生に送る" if FIRESTORE_ENABLED else "📨 送信（未接続）"
    if st.button(label, type="primary", disabled=disabled, key="share_send"):
        gid = st.session_state.get("group_id","")
        hdl = st.session_state.get("handle_norm","")
        ok = safe_db_add("school_share", {
            "ts": datetime.now(timezone.utc),
            "group_id": gid,
            "handle": hdl,
            "user_key": user_key(gid, hdl) if (gid and hdl) else "",
            "payload": {"mood":mood, "body":body, "sleep_hours":float(sleep_h), "sleep_quality":sleep_q},
            "anonymous": True
        })
        if ok:
            st.session_state.flash_msg = "「今日を伝える」を送信しました。ありがとうございます。"
            st.rerun()
        else:
            st.error("送信できませんでした。")

# ----- 相談（Firestoreに匿名送信） -----
CONSULT_TOPICS = ["体調","勉強","人間関係","家庭","進路","いじめ","メンタルの不調","その他"]
def view_consult():
    st.markdown("### 🕊 相談（匿名OK）")
    st.caption("誰にも言いにくいことでも大丈夫。お名前は空欄のまま送れます。")
    to_whom = st.radio("相談先", ["カウンセラーに相談したい","先生に伝えたい"], horizontal=True, key="c_to")
    topics  = st.multiselect("内容（当てはまるもの）", CONSULT_TOPICS, default=[], key="c_topics")
    anonymous = st.checkbox("匿名で送る", value=True, key="c_anon")
    name = "" if anonymous else st.text_input("お名前（任意）", value="", key="c_name")
    msg = st.text_area("ご相談内容", height=220, value="", key="c_msg")

    disabled = not FIRESTORE_ENABLED or (msg.strip()=="")
    label = "🕊 送信する" if FIRESTORE_ENABLED else "🕊 送信（未接続）"
    if st.button(label, type="primary", disabled=disabled, key="c_send"):
        gid = st.session_state.get("group_id","")
        hdl = st.session_state.get("handle_norm","")
        payload = {
            "ts": datetime.now(timezone.utc),
            "group_id": gid,
            "handle": hdl,
            "user_key": user_key(gid, hdl) if (gid and hdl) else "",
            "message": msg.strip(),
            "topics": topics,
            "intent": "counselor" if to_whom.startswith("カウンセラー") else "teacher",
            "anonymous": bool(anonymous),
            "name": name.strip() if (not anonymous and name) else "",
        }
        ok = safe_db_add("consult_msgs", payload)
        if ok:
            st.session_state.flash_msg = "相談を送信しました。ありがとうございます。"
            # 入力欄リセット
            for k in ["c_topics","c_msg","c_name","c_anon","c_to"]:
                if k in st.session_state: del st.session_state[k]
            st.rerun()
        else:
            st.error("送信できませんでした。")

# ----- Study（ローカル保存） -----
def view_study():
    st.markdown("### 📚 Study Tracker")
    subjects_default = ["国語","数学","英語","理科","社会","音楽","美術","情報","その他"]
    subj = st.selectbox("科目", subjects_default, index=0, key="study_subj")
    add  = st.text_input("＋ 自分の科目を追加（Enter）", key="study_add")
    if add.strip(): subj = add.strip()
    mins = st.number_input("学習時間（分）", 1, 600, 30, 5, key="study_min")
    mood = st.selectbox("状況", ["順調","難航","しんどい","集中","だるい","眠い","その他"], index=0, key="study_mood")
    memo = st.text_input("メモ（任意）", key="study_memo")
    if st.button("💾 記録（端末）", type="primary", key="study_save"):
        rec = {"ts": now_iso(), "subject": subj, "minutes": int(mins), "mood": mood, "memo": memo}
        st.session_state["_local_logs"]["study"].append(rec)
        st.success("保存しました。（運営には共有されません）")

# ----- ふりかえり（ローカル） -----
def view_review():
    st.markdown("### 📒 ふりかえり（このセッションの履歴）")
    logs = st.session_state["_local_logs"]
    if any(len(v)>0 for v in logs.values()):
        all_json = json.dumps(logs, ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button("⬇️ このセッションの全記録（JSON）", data=all_json,
                           file_name=f"withyou_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                           mime="application/json", key="review_dl_all")
    tabs = st.tabs(["ノート","呼吸","Study"])
    with tabs[0]:
        notes = list(reversed(logs["note"]))
        if not notes: st.caption("まだ記録がありません。")
        else:
            for r in notes:
                st.markdown(f"""
<div class="item">
  <div class="meta">{r['ts']}</div>
  <div style="font-weight:900; color:#24466e; margin-bottom:.2rem">{r['mood'].get('emoji','')} {r['mood'].get('label','')}</div>
  <div style="white-space:pre-wrap; margin-bottom:.3rem">きっかけ：{r.get('trigger','')}</div>
  <div style="white-space:pre-wrap; margin-bottom:.3rem">よぎった言葉：{r.get('auto','')}</div>
  <div style="white-space:pre-wrap; margin-bottom:.3rem">日記：{r.get('diary','')}</div>
</div>
""", unsafe_allow_html=True)
    with tabs[1]:
        breaths = list(reversed(logs["breath"]))
        if not breaths: st.caption("まだ記録がありません。")
        else:
            for r in breaths:
                st.markdown(f"""
<div class="item">
  <div class="meta">{r['ts']}</div>
  <div>パターン：{r.get('pattern','5-2-6')} / 実施：{r.get('sec',90)}秒</div>
  <div>終了時の気分：{r.get('mood_after','')}</div>
</div>
""", unsafe_allow_html=True)
    with tabs[2]:
        studies = list(reversed(logs["study"]))
        if not studies: st.caption("まだ記録がありません。")
        else:
            df = pd.DataFrame(studies)
            pie_agg = df.groupby("subject")["minutes"].sum().reset_index().sort_values("minutes", ascending=False)
            if not pie_agg.empty:
                pie = (alt.Chart(pie_agg).mark_arc(innerRadius=60).encode(
                        theta=alt.Theta(field="minutes", type="quantitative"),
                        color=alt.Color(field="subject", type="nominal", legend=alt.Legend(title="科目")),
                        tooltip=[alt.Tooltip("subject:N", title="科目"), alt.Tooltip("minutes:Q", title="合計分")]
                    ).properties(width=340, height=340))
                st.altair_chart(pie, use_container_width=False)
            for _, r in df.sort_values("ts", ascending=False).iterrows():
                st.markdown(f"""
<div class="item">
  <div class="meta">{r['ts']}</div>
  <div style="font-weight:900">{r['subject']}</div>
  <div>分：{int(r['minutes'])} / 状況：{r.get('mood','')}</div>
  <div style="white-space:pre-wrap; color:#3b4f71; margin-top:.3rem">{r.get('memo','')}</div>
</div>
""", unsafe_allow_html=True)

# ----- 運営（ADMIN） -----
def view_admin():
    st.markdown("### 🛠 運営ダッシュボード")
    if not FIRESTORE_ENABLED:
        st.error("Firestore未接続です。st.secretsの設定を確認してください。")
        return
    gid = st.session_state.get("group_id","")

    st.markdown("#### 🏫 今日を伝える（school_share）")
    n1 = st.number_input("取得件数（最新から）", 1, 200, 50, 1, key="adm_n1")
    q1 = DB.collection("school_share")
    if gid: q1 = q1.where("group_id", "==", gid)
    try:
        q1 = q1.order_by("ts", direction="DESCENDING").limit(int(n1))
    except Exception:
        st.caption("（インデックス未作成の場合があります。Firestoreのインデックスを確認してください。）")
    rows1 = []
    try:
        for d in q1.stream():
            r = d.to_dict()
            rows1.append({
                "時刻": r.get("ts"),
                "名前": r.get("handle",""),
                "気分": r.get("payload",{}).get("mood",""),
                "体調": ",".join(r.get("payload",{}).get("body",[])),
                "睡眠(h)": r.get("payload",{}).get("sleep_hours",""),
                "睡眠の質": r.get("payload",{}).get("sleep_quality",""),
                "匿名": r.get("anonymous", True),
            })
    except Exception as e:
        st.error(f"取得エラー: {e}")
    if rows1:
        df1 = pd.DataFrame(rows1)
        st.dataframe(df1, use_container_width=True, hide_index=True)
    else:
        st.caption("データがありません。")

    st.markdown("#### 🕊 相談（consult_msgs）")
    n2 = st.number_input("取得件数（最新から） ", 1, 200, 50, 1, key="adm_n2")
    q2 = DB.collection("consult_msgs")
    if gid: q2 = q2.where("group_id", "==", gid)
    try:
        q2 = q2.order_by("ts", direction="DESCENDING").limit(int(n2))
    except Exception:
        st.caption("（インデックス未作成の場合があります。Firestoreのインデックスを確認してください。）")
    rows2 = []
    try:
        for d in q2.stream():
            r = d.to_dict()
            rows2.append({
                "時刻": r.get("ts"),
                "名前": (r.get("name") or r.get("handle") or ""),
                "匿名": r.get("anonymous", True),
                "宛先": r.get("intent",""),
                "内容": r.get("message",""),
                "トピック": ",".join(r.get("topics",[])),
            })
    except Exception as e:
        st.error(f"取得エラー: {e}")
    if rows2:
        df2 = pd.DataFrame(rows2)
        st.dataframe(df2, use_container_width=True, hide_index=True)
    else:
        st.caption("データがありません。")

# ================== ルーター ==================
def main_router():
    v = st.session_state.view
    if v == "HOME":     view_home()
    elif v == "SHARE":  view_share()
    elif v == "SESSION":view_session()
    elif v == "NOTE":   view_note()
    elif v == "STUDY":  view_study()
    elif v == "REVIEW": view_review()
    elif v == "CONSULT":view_consult()
    elif v == "ADMIN":  view_admin()
    else:               view_home()
    return None

# ================== アプリ起動 ==================
if st.session_state.get("auth_ok", False):
    logout_btn()
    status_bar()
    top_tabs()
    main_router()
else:
    login_register_ui()
