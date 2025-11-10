# app.py — With You.
# （共通パス＋自分だけの名前｜登録先着専有・同時利用OK・Cookie/URL/本人コードなし｜ADMIN対応＋フォールバック）
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Dict, Tuple, List, Optional, Any
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
ADMIN_MASTER_CODE = (
    st.secrets.get("ADMIN_MASTER_CODE")
    or os.environ.get("ADMIN_MASTER_CODE")
    or "uneiairi0931"   # ← 既定は 0931 付き
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

# ローカルログ（端末保存）
st.session_state.setdefault("_local_logs", {"note":[], "breath":[], "study":[]})

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
.meta{ color:#6a7d9e; font-size:.86rem; margin-bottom:.3rem}
.ok-chip{ display:inline-block; background:#eefaf1; color:#147a3d; border:1px solid #cfeedd; border-radius:999px; padding:.2rem .6rem; font-size:.82rem }
.breath-spot{
  width:260px;height:260px;border-radius:999px;
  background:radial-gradient(circle at 50% 40%, #f7fbff, #e8f2ff 60%, #eef8ff 100%);
  border:1px solid #dbe9ff;
  box-shadow:0 18px 36px rgba(90,140,190,.14), inset 0 -10px 25px rgba(120,150,200,.15);
}
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
    st.markdown("**ご自由にパスワードを設定ください**")
    group_pw = st.text_input("パスワード", key="inp_group_pw", label_visibility="collapsed", placeholder="例：sakura2025")
    st.markdown("**ご自身のニックネーム（4〜12文字）**")
    st.caption("同じ名前は1人だけ使えます（先着）。英数字・ひらがな・カタカナ・漢字と _ - が使えます。")
    handle_raw = st.text_input("自分だけの名前", key="inp_handle", label_visibility="collapsed", placeholder="例：mika / ねこ_3 / sora")

    err = ""
    ok_handle, handle_norm = validate_handle(handle_raw)
    if (group_pw or "").strip() == "":
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

        # 管理者判定（normalize して完全一致）
        entered = unicodedata.normalize("NFKC", group_pw or "").strip()
        master  = unicodedata.normalize("NFKC", ADMIN_MASTER_CODE or "").strip()
        st.session_state.role = "admin" if entered == master else "user"

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
気持ちを整理したい日も、誰かに話したい日も。
With You は、あなたの心のそばにある、小さなツールボックスです。

今の自分に合うカードを選んで、少しずつ整える時間をつくってみてください。

🔒 「今日を伝える」と「相談する」だけが運営に届きます。
それ以外の記録は、すべてあなたの端末だけに残ります。
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
    with c2: big_button("心を整えるノート", "感じたことを言葉にして、今の自分を整理します。", "NOTE", "note", "📝")
    c3, c4 = st.columns(2)
    with c3: big_button("Study Tracker", "学習時間を見える化。", "STUDY", "study", "📚")
    with c4: big_button("ふりかえり", "この端末に残した記録をまとめて確認。", "REVIEW", "review", "📒")
    big_button("相談する", "匿名OK。困りごとがあれば短くでも。", "CONSULT", "consult", "🕊")

# ----- リラックス（呼吸） -----
BREATH_PATTERN = (5, 2, 6)  # 5-2-6

def breathing_animation(total_sec: int = 90):
    """円は1つのみ。カウントダウンは円の下。実行終了時に rerun してボタン復帰。"""
    st.session_state["_breath_running"] = True

    inhale, hold, exhale = BREATH_PATTERN
    cycle = inhale + hold + exhale
    cycles = max(1, round(total_sec / cycle))

    circle_area = st.empty()
    phase_area = st.empty()
    countdown_area = st.empty()
    stop_area = st.empty()

    # 円（1つだけ）
    circle_area.markdown(
        """
<div style="display:flex;justify-content:center;align-items:center;padding:8px 0 6px">
  <div class="breath-spot" style="width:260px;height:260px"></div>
</div>
""",
        unsafe_allow_html=True,
    )

    def set_countdown(sec: int, label: str = ""):
        countdown_area.markdown(
            f"""
<div style="text-align:center;font-size:1.05rem;color:#3a4a6a;">
  {label} のこり <b>{sec}</b> 秒
</div>
""",
            unsafe_allow_html=True,
        )

    # 停止ボタン（円とカウントダウンの下）
    with stop_area.container():
        cols = st.columns([1, 1, 1])
        with cols[1]:
            st.button(
                "⏹ 停止する",
                key="breath_stop_btn",
                on_click=lambda: st.session_state.update({"_breath_stop": True}),
                use_container_width=True,
            )

    try:
        for _ in range(cycles):
            for label, seconds in [("吸ってください", inhale), ("止めてください", hold), ("吐いてください", exhale)]:
                if seconds <= 0:
                    continue
                phase_area.markdown(f"**{label}**")
                for remain in range(seconds, 0, -1):
                    if st.session_state.get("_breath_stop") or st.session_state.view != "SESSION":
                        return
                    set_countdown(remain, label)
                    time.sleep(1)
    finally:
        # 後片付けと状態復帰
        phase_area.empty(); countdown_area.empty(); stop_area.empty(); circle_area.empty()
        st.session_state["_breath_running"] = False
        st.session_state["_breath_stop"] = False
        st.session_state["_breath_finished"] = True  # 次の描画で完了メッセージを出す
        st.rerun()  # ← 終了後に即座に“ボタンありの画面”へ戻す


def view_session():
    st.markdown("### 🌙 リラックス（呼吸）")
    st.caption("円が大きくなったら吸って、小さくなったら吐きます。途中で停止・ページ移動できます。")

    total_seconds = 90
    inhale, hold, exhale = BREATH_PATTERN

    running = st.session_state.get("_breath_running", False)
    finished = st.session_state.pop("_breath_finished", False)
    if finished:
        st.success("お疲れさまでした。ありがとうございます。")

    if not running:
        # 実行前だけ「はじめる」を表示（押したら状態を立てて rerun）
        cols = st.columns([1, 1, 1])
        with cols[1]:
            if st.button("🫁 はじめる（90秒）", key="breath_start", type="primary", use_container_width=True):
                st.session_state["_breath_stop"] = False
                st.session_state["_breath_running"] = True
                st.rerun()
    else:
        # 実行中：ボタンは表示しない。アニメを開始（終了時は内部で rerun）
        breathing_animation(total_seconds)

    # パターン表記（常に1箇所）
    st.caption(f"パターン：{inhale}-{hold}-{exhale}／合計 {total_seconds} 秒")

    st.divider()
    # メーターは1つ（スライダーのみ）
    after = st.slider("いまの気分（1 とてもつらい / 10 とても楽）", 1, 10, 5, key="breath_mood_after")

    if st.button("💾 端末に保存（このセッション内）", type="primary", key="breath_save"):
        st.session_state["_local_logs"]["breath"].append({
            "ts": now_iso(), "pattern": "5-2-6", "mood_after": int(after), "sec": total_seconds
        })
        st.success("保存しました。（運営には共有されません）")



# ----- ノート（ローカル保存） -----
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

def cbt_intro_block():
    # ご指定の文章をそのまま表示
    st.markdown("""
<div class="cbt-card">
  <div class="cbt-heading">このワークについて</div>
  <div class="cbt-sub" style="white-space:pre-wrap">
このノートは、認知行動療法（CBT）という考え方をもとにしています。
「気持ち」と「考え方」の関係を整理することで、
今感じている不安やしんどさが少し軽くなることを目指しています。
自分のペースで、思いつくことを自由に書いてみてください。
  </div>
</div>
""", unsafe_allow_html=True)

def cbt_intro():
    return cbt_intro_block()

def mood_radio() -> Dict[str, Any]:
    st.markdown('<div class="cbt-card">', unsafe_allow_html=True)
    st.markdown('<div class="cbt-heading">🌤 Step 1：今の気持ちは？</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for i, m in enumerate(MOODS):
        with cols[i % 4]:
            if st.button(f"{m['emoji']} {m['label']}", key=f"cbt_btn_mood_{m['key']}"):
                st.session_state["cbt_mood_key"] = m["key"]
                st.session_state["cbt_mood_label"] = m["label"]
                st.session_state["cbt_mood_emoji"] = m["emoji"]
    sel = st.session_state.get("cbt_mood_label", "未選択")
    st.write(f"選択中：**{st.session_state.get('cbt_mood_emoji','')} {sel}**")
    intensity = st.slider("今の強さ（0〜100）", 0, 100, 60, key="cbt_intensity")
    st.markdown("</div>", unsafe_allow_html=True)
    return {
        "key": st.session_state.get("cbt_mood_key"),
        "label": st.session_state.get("cbt_mood_label"),
        "emoji": st.session_state.get("cbt_mood_emoji"),
        "intensity": intensity
    }

def text_card(title: str, subtext: str, key: str, height=120, placeholder="ここに書いてみてね") -> str:
    st.markdown('<div class="cbt-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="cbt-heading">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cbt-sub">{subtext}</div>', unsafe_allow_html=True)
    val = st.text_area("", height=height, key=key, placeholder=placeholder, label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)
    return val

ACTION_CATEGORIES_EMOJI = { "身体": "🫧","環境": "🌤","リズム": "⏯️","つながり": "💬" }
ACTION_CATEGORIES = {
    "身体": ["顔や手を洗う","深呼吸をする","肩を回す","シャワーを浴びる"],
    "環境": ["窓を開けて外の空気を感じる","カーテンを開けて部屋を明るくする","空をながめる"],
    "リズム": ["水を飲む","温かい飲み物を飲む","立ち上がって少し歩く","外を少し歩く"],
    "つながり": ["スタンプを送る","「ありがとう」を書く","家族や友達に一言だけ話す"],
}
def _flat_action_options_emoji():
    order = ["身体","環境","リズム","つながり"]
    seen, disp, vals = set(), [], []
    for cat in order:
        for a in ACTION_CATEGORIES.get(cat, []):
            if a in seen: continue
            seen.add(a); disp.append(f"{ACTION_CATEGORIES_EMOJI[cat]} {a}"); vals.append(a)
    return disp, vals

def action_picker(mood_key: Optional[str]):
    st.markdown('<div class="cbt-card">', unsafe_allow_html=True)
    st.markdown('<div class="cbt-heading">🌸 Step 6：今できそうなことは？</div>', unsafe_allow_html=True)
    st.markdown('<div class="cbt-sub">ぴったりを1つだけ。選ばなくてもOKだよ。</div>', unsafe_allow_html=True)
    disp, vals = _flat_action_options_emoji()
    options_disp = disp + ["— 選ばない —"]
    key_pick = f"act_pick_single_{(mood_key or 'default').strip().lower()}"
    sel_disp = st.selectbox("小さな行動（任意）", options=options_disp, index=len(options_disp)-1, key=key_pick)
    chosen = "" if sel_disp == "— 選ばない —" else vals[disp.index(sel_disp)]
    custom_key = f"act_custom_single_{(mood_key or 'default').strip().lower()}"
    custom = st.text_input("＋ 自分の言葉で書く（任意）", key=custom_key, placeholder="例：窓を開けて深呼吸する").strip()
    st.markdown("</div>", unsafe_allow_html=True)
    if custom: return "", custom
    return (chosen or ""), ""

def recap_card(doc: dict):
    st.markdown('<div class="cbt-card">', unsafe_allow_html=True)
    st.markdown('<div class="cbt-heading">🧾 まとめ</div>', unsafe_allow_html=True)
    st.write(f"- 気持ち：{doc['mood'].get('emoji','')} **{doc['mood'].get('label','未選択')}**（強さ {doc['mood'].get('intensity',0)}）")
    st.write(f"- きっかけ：{doc.get('trigger_text','') or '—'}")
    st.write(f"- よぎった言葉：{doc.get('auto_thought','') or '—'}")
    st.write(f"- そう思った理由：{doc.get('reason_for','') or '—'}")
    st.write(f"- そうでもないかも：{doc.get('reason_against','') or '—'}")
    st.write(f"- 友だちにかける言葉：{doc.get('alt_perspective','') or '—'}")
    chosen = doc.get("action_suggested") or doc.get("action_custom") or "—"
    st.write(f"- 小さな行動：{chosen}")
    st.write(f"- 日記：{doc.get('reflection','') or '—'}")
    st.markdown('<span class="ok-chip">保存はこの端末（このセッション）に残ります。</span>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def view_note():
    st.markdown("### 📝 心を整えるノート")
    cbt_intro()  # ← ご指定の冒頭文を表示

    mood = mood_radio()
    trigger_text   = text_card("🫧 Step 2：その気持ちは、どんなことがきっかけだった？", "「○○があったからかも」「なんとなく○○って思ったから」など自由に。", "cbt_trigger")
    auto_thought   = text_card("💭 Step 3：そのとき、頭の中でどんな言葉がよぎった？", "心の中でつぶやいた言葉やイメージをそのまま書いてOK。", "cbt_auto")
    reason_for     = text_card("🔍 Step 4-1：そう思った理由はある？", "「たしかにそうかも」と思うことを書いてみよう。", "cbt_for", height=100)
    reason_against = text_card("🔍 Step 4-2：そうでもないかもと思う理由はある？", "「でも、こういう面もあるかも」も書いてみよう。", "cbt_against", height=100)
    alt_perspective= text_card("🌱 Step 5：もし友だちが同じことを感じていたら、なんて声をかける？", "自分のことじゃなく“友だち”のこととして考えてみよう。", "cbt_alt")
    act_suggested, act_custom = action_picker(mood.get("key"))
    reflection     = text_card("🌙 Step 7：今日の日記", "気づいたこと・気持ちの変化・これからのことなど自由に。", "cbt_reflect", height=120)

    if st.button("💾 記録（この端末）", type="primary", key="cbt_save"):
        # 保存用ドキュメント（UI文言は変更なし・キー名だけ整合）
        doc = {
            "ts": now_iso(),
            "mood": mood,
            "trigger": (trigger_text or "").strip(),
            "auto": (auto_thought or "").strip(),
            "reason_for": (reason_for or "").strip(),
            "reason_against": (reason_against or "").strip(),
            "alt_perspective": (alt_perspective or "").strip(),
            "action": {"suggested": act_suggested, "custom": act_custom},
            "diary": (reflection or "").strip(),
        }
        st.session_state["_local_logs"]["note"].append(doc)
        st.success("保存しました。（運営には共有されません）")
        st.download_button(
            "⬇️ この記録をダウンロード（JSON）",
            data=json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name=f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            key=f"dl_note_{len(st.session_state['_local_logs']['note'])}"
        )

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

    # ▼ 表示範囲の切替（同じパスのグループのみ / 全グループ）
    scope = st.radio("表示範囲", ["このパスワードのグループだけ", "全グループ"], horizontal=True, key="adm_scope")
    gid_filter = st.session_state.get("group_id","") if scope.startswith("この") else None

    def fetch_rows(coll_name: str, limit_n: int):
        q = DB.collection(coll_name)
        if gid_filter:
            q = q.where("group_id", "==", gid_filter)
        # 1) インデックスがあれば高速ルート（ts desc）
        try:
            q2 = q.order_by("ts", direction="DESCENDING").limit(int(limit_n))
            docs = list(q2.stream())
            return [d.to_dict() for d in docs], None
        except Exception as e:
            # 2) フォールバック：order_byなし→Python側でts降順
            try:
                docs = list(q.limit(int(limit_n)).stream())
                rows = [d.to_dict() for d in docs]
                from datetime import datetime as _dt
                def _key(r):
                    v = r.get("ts")
                    return v if isinstance(v, _dt) else _dt.min
                rows.sort(key=_key, reverse=True)
                return rows, "fallback"
            except Exception as e2:
                st.error(f"取得エラー: {e}\n{e2}")
                return [], "error"

    # ------- 今日を伝える -------
    st.markdown("#### 🏫 今日を伝える（school_share）")
    n1 = st.number_input("取得件数（最新から）", 1, 200, 50, 1, key="adm_n1")
    rows1, mode1 = fetch_rows("school_share", n1)
    if mode1 == "fallback":
        st.caption("（インデックス未作成のためフォールバック動作中：サーバ取得→クライアント側で降順）")
    if rows1:
        df1 = pd.DataFrame([{
            "時刻": r.get("ts"),
            "名前": r.get("handle",""),
            "気分": (r.get("payload",{}) or {}).get("mood",""),
            "体調": ",".join((r.get("payload",{}) or {}).get("body",[]) or []),
            "睡眠(h)": (r.get("payload",{}) or {}).get("sleep_hours",""),
            "睡眠の質": (r.get("payload",{}) or {}).get("sleep_quality",""),
            "匿名": r.get("anonymous", True),
        } for r in rows1])
        st.dataframe(df1, use_container_width=True, hide_index=True)
    else:
        st.caption("データがありません。")

    # ------- 相談 -------
    st.markdown("#### 🕊 相談（consult_msgs）")
    n2 = st.number_input("取得件数（最新から） ", 1, 200, 50, 1, key="adm_n2")
    rows2, mode2 = fetch_rows("consult_msgs", n2)
    if mode2 == "fallback":
        st.caption("（インデックス未作成のためフォールバック動作中：サーバ取得→クライアント側で降順）")
    if rows2:
        df2 = pd.DataFrame([{
            "時刻": r.get("ts"),
            "名前": (r.get("name") or r.get("handle") or ""),
            "匿名": r.get("anonymous", True),
            "宛先": r.get("intent",""),
            "内容": r.get("message",""),
            "トピック": ",".join(r.get("topics",[]) or []),
        } for r in rows2])
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
