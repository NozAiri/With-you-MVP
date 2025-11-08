# app.py — Sora / With You.（2025-11 完全リファイン v2：大きなアクションカード / 固定ボトムナビ / 相談オプション拡張）
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple
import pandas as pd
import streamlit as st
import json, time, re

# ==== Firestore ====
from google.cloud import firestore
import google.oauth2.service_account as service_account

# ================= Page config =================
st.set_page_config(
    page_title="With You.",
    page_icon="🌙",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ================= Theme / CSS =================
def inject_css():
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700;900&family=Noto+Sans+JP:wght@400;700;900&display=swap');

:root{
  --bg1:#f2f6ff; --bg2:#eaf4ff; --panel:#ffffffee; --panel-brd:#e1e9ff;
  --text:#1b2a45; --muted:#5c6f8f; --accent:#5EA3FF; --accent-2:#96BDFF;
  --card:#fff; --shadow:0 14px 34px rgba(40,80,160,.12);
  --grad1: linear-gradient(135deg,#e9f1ff 0%,#f7fbff 70%);
  --pill1: linear-gradient(135deg,#ffffff 0%,#eef5ff 100%);
  --good: #12b886; --warn:#ffa94d; --bad:#ff6b6b;
}

html, body, .stApp{
  font-family: "Zen Maru Gothic","Noto Sans JP",system-ui, -apple-system, sans-serif;
  background:
    radial-gradient(1200px 600px at 20% -10%, #ffffff 0%, var(--bg1) 40%, transparent 70%),
    radial-gradient(1000px 520px at 100% 0%,  #ffffff 0%, var(--bg2) 50%, transparent 80%),
    linear-gradient(180deg, var(--bg1), var(--bg2));
  color: var(--text);
}
.block-container{ max-width:980px; padding-top:1.2rem; padding-bottom:6.8rem } /* 下に余白：ボトムナビ用 */

/* ---------- Typography ---------- */
h1,h2,h3{ color:var(--text); letter-spacing:.2px }
h1{ font-weight:900 }
.section-lead{ color:#183458; font-weight:900; margin:.2rem 0 .4rem }
.caption{ color:var(--muted); }

/* ---------- Card ---------- */
.card{ background:var(--panel); border:1px solid var(--panel-brd); border-radius:22px; padding:18px; box-shadow:var(--shadow) }
.item{ background:var(--card); border:1px solid var(--panel-brd); border-radius:18px; padding:16px; box-shadow:var(--shadow) }
.item .meta{ color:var(--muted); font-size:.9rem; margin-bottom:.2rem }
.badge{ display:inline-block; padding:.2rem .6rem; border:1px solid #d6e7ff; border-radius:999px; margin-right:.4rem; color:#29466e; background:#f6faff; font-weight:900 }

/* ---------- Grids ---------- */
.grid-2{ display:grid; grid-template-columns:1fr 1fr; gap:16px }
.grid-3{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px }
.grid-4{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px }
@media (max-width: 820px){ .grid-3,.grid-4{ grid-template-columns:1fr 1fr } }
@media (max-width: 520px){ .grid-2,.grid-3,.grid-4{ grid-template-columns:1fr } }

/* ---------- Home: Big Action Cards ---------- */
.action-card{
  border-radius:26px; border:1px solid #dfe6ff; box-shadow:var(--shadow);
  background: var(--grad1);
  padding:18px 18px 16px; cursor:default; position:relative; overflow:hidden;
}
.action-card .icon{
  width:68px; height:68px; border-radius:18px;
  background:linear-gradient(135deg,#ffffff 0%,#eaf3ff 100%);
  border:1px solid #e2ebff; display:flex; align-items:center; justify-content:center;
  font-size:34px; box-shadow:inset 0 -10px 16px rgba(100,140,200,.12);
}
.action-card h3{ margin:10px 0 4px; font-size:1.28rem; font-weight:900; color:#12294a }
.action-card .desc{ color:#4b6287; font-size:.98rem; }
.action-card .cta .stButton>button{
  margin-top:10px; border-radius:14px; font-weight:900;
}

/* 学校共有を最上位で強調 */
.action-card.share{ border-color:#cfe3ff; background:linear-gradient(135deg,#e9f3ff 0%,#ffffff 90%); }
.action-card.share .icon{ background:linear-gradient(135deg,#ffffff 0%,#e8f1ff 100%); }

/* ---------- Underline Tabs (review用) ---------- */
.Utabs .stTabs [data-baseweb="tab-list"]{
  gap: 28px; border-bottom: 3px solid #e8f0ff; margin: 0 0 8px 0; padding-bottom: 0;
}
.Utabs .stTabs [data-baseweb="tab"]{
  height: 46px; padding: 0 0 10px 0; font-weight:900; color:#7a8cab; font-size:1.02rem;
}
.Utabs .stTabs [aria-selected="true"]{
  color:#16335b; border-bottom: 4px solid var(--accent);
}

/* ---------- Breathing circle ---------- */
.breath-wrap{display:flex; justify-content:center; align-items:center; padding:10px 0 6px}
.breath-circle{
  width:260px; height:260px; border-radius:999px;
  background:radial-gradient(circle at 50% 40%, #f7fbff, #e8f2ff 60%, #eef8ff 100%);
  box-shadow:0 18px 36px rgba(90,140,190,.14), inset 0 -10px 25px rgba(120,150,200,.15);
  transform:scale(1); border: solid #dbe9ff;
}
@keyframes sora-grow{ from{ transform:scale(1.0); border-width:10px;} to{ transform:scale(1.6); border-width:14px;} }
@keyframes sora-steady{ from{ transform:scale(1.6); border-width:14px;} to{ transform:scale(1.6); border-width:14px;} }
@keyframes sora-shrink{ from{ transform:scale(1.6); border-width:14px;} to{ transform:scale(1.0); border-width:8px;} }
.phase-pill{display:inline-block; padding:.28rem .9rem; border-radius:999px; background:#edf5ff; color:#2c4b77; border:1px solid #d6e7ff; font-weight:900; font-size:0.98rem}

/* ---------- Emotion pills (彩色) ---------- */
.emopills{display:grid; grid-template-columns:repeat(3,1fr); gap:10px}
@media (min-width:820px){ .emopills{ grid-template-columns:repeat(6,1fr) } }
.emopills .chip .stButton>button{
  background:var(--pill1) !important; color:#1d3457 !important;
  border:2px solid #d6e7ff !important; border-radius:16px !important;
  box-shadow:0 6px 16px rgba(100,140,200,.08) !important; font-weight:900 !important; padding:12px 12px !important;
}
.emopills .chip.on .stButton>button{
  border:2px solid var(--accent) !important; background:#f0f7ff !important;
}

/* ---------- Progress ---------- */
.prog{height:12px; background:#eef4ff; border-radius:999px; overflow:hidden}
.prog > div{height:12px; background:var(--accent-2)}

/* ---------- Primary buttons ---------- */
.stButton>button{
  border-radius:14px; font-weight:900;
}

/* ---------- Fixed Bottom Nav ---------- */
.bottom-nav{
  position:fixed; z-index:999; left:50%; transform:translateX(-50%);
  bottom:14px; width:min(940px,92vw);
  background:rgba(255,255,255,.86); backdrop-filter:saturate(150%) blur(8px);
  border:1px solid #dfe6ff; border-radius:18px; box-shadow:0 14px 28px rgba(60,100,160,.18);
  padding:8px 10px;
}
.bottom-nav .stButton>button{
  width:100%; border-radius:12px; background:#f6f9ff; border:1px solid #e1eaff;
  font-weight:900;
}
.bottom-nav .active .stButton>button{
  background:#eaf3ff; border:2px solid var(--accent); 
}
</style>
        """,
        unsafe_allow_html=True,
    )

inject_css()

# ================= Firestore =================
def firestore_client():
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["FIREBASE_SERVICE_ACCOUNT"]
    )
    return firestore.Client(
        project=st.secrets["FIREBASE_SERVICE_ACCOUNT"]["project_id"],
        credentials=creds,
    )

DB = firestore_client()

# ================= Storage =================
class Storage:
    CBT = "cbt_entries"
    BREATH = "breath_sessions"
    MIX = "mix_note"
    STUDY = "study_blocks"
    CONSULT = "consult_msgs"
    SHARED = "school_share"
    PREFS = "user_prefs"

    @staticmethod
    def now_iso():
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    @staticmethod
    def append_user(table: str, user_id: str, row: dict):
        row = dict(row)
        row["_ts_iso"] = row.get("ts", Storage.now_iso())
        row["ts"] = firestore.SERVER_TIMESTAMP
        row["user_id"] = user_id
        DB.collection(table).add(row)

    @staticmethod
    def load_user(table: str, user_id: str) -> pd.DataFrame:
        docs = (
            DB.collection(table)
            .where("user_id", "==", user_id)
            .order_by("ts", direction=firestore.Query.DESCENDING)
            .stream()
        )
        rows = []
        for d in docs:
            data = d.to_dict()
            data["_id"] = d.id
            ts = data.get("ts")
            data["ts"] = (
                ts.astimezone().isoformat(timespec="seconds") if ts else data.get("_ts_iso")
            )
            rows.append(data)
        return pd.DataFrame(rows)

    @staticmethod
    def get_subjects(uid: str) -> List[str]:
        doc = DB.collection(Storage.PREFS).document(uid).get()
        if doc.exists:
            li = doc.to_dict().get("subjects", [])
            return list(dict.fromkeys(li))
        return ["国語", "数学", "英語", "理科", "社会", "音楽", "美術", "情報", "その他"]

    @staticmethod
    def save_subjects(uid: str, subs: List[str]):
        DB.collection(Storage.PREFS).document(uid).set(
            {"subjects": list(dict.fromkeys(subs))}, merge=True
        )

# ================= Utils / State =================
def now_iso() -> str:
    return Storage.now_iso()

st.session_state.setdefault("_auth_ok", False)
st.session_state.setdefault("role", None)
st.session_state.setdefault("user_id", "")
st.session_state.setdefault("view", "HOME")
st.session_state.setdefault("_nav_stack", [])
st.session_state.setdefault("breath_mode", "calm")  # calm=(5,2,6), gentle=(4,0,6)
st.session_state.setdefault("_breath_running", False)

def admin_pass() -> str:
    try:
        return st.secrets["ADMIN_PASS"]
    except Exception:
        return "admin123"

CRISIS = [r"死にたい", r"消えたい", r"自殺", r"希死", r"傷つけ(たい|てしまう)", r"リスカ", r"OD", r"助けて"]

def crisis(text: str) -> bool:
    if not text:
        return False
    for p in CRISIS:
        if re.search(p, text):
            return True
    return False

# ================= Auth =================
def auth_ui() -> bool:
    if st.session_state._auth_ok:
        return True
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 🔐 ログイン")
        t1, t2 = st.tabs(["利用者として入る", "運営として入る"])
        with t1:
            uid = st.text_input("ユーザーID", placeholder="例: omu-2025-xxxx")
            if st.button("➡️ 入る（利用者）", type="primary"):
                if uid.strip() == "":
                    st.warning("ユーザーIDをご入力ください。")
                else:
                    st.session_state.user_id = uid.strip()
                    st.session_state.role = "user"
                    st.session_state._auth_ok = True
                    st.success("ようこそ。")
                    return True
        with t2:
            pw = st.text_input("運営パスコード", type="password")
            if st.button("➡️ 入る（運営）"):
                if pw == admin_pass():
                    st.session_state.user_id = "_admin_"
                    st.session_state.role = "admin"
                    st.session_state._auth_ok = True
                    st.success("運営ログインが完了しました。")
                    return True
                else:
                    st.error("パスコードが違います。")
        st.markdown("</div>", unsafe_allow_html=True)
    return False

def logout_btn():
    with st.sidebar:
        if st.button("🚪 ログアウト"):
            st.session_state["_auth_ok"] = False
            st.session_state["role"] = None
            st.session_state["user_id"] = ""
            st.session_state["view"] = "HOME"
            st.session_state["_nav_stack"] = []
            st.session_state["_breath_running"] = False
            st.rerun()

# ================= Nav =================
def navigate(to_key: str, push: bool = True):
    cur = st.session_state.view
    if push and cur != to_key:
        st.session_state._nav_stack.append(cur)
    st.session_state.view = to_key

def go_back(default: str = "HOME"):
    if st.session_state._nav_stack:
        st.session_state.view = st.session_state._nav_stack.pop()
    else:
        st.session_state.view = default
    st.rerun()

def top_status():
    st.markdown('<div class="card" style="padding:10px 14px">', unsafe_allow_html=True)
    st.markdown(
        f"<div class='caption'>ログイン中：{'運営' if st.session_state.role=='admin' else f'利用者（{st.session_state.user_id}）'}</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

def bottom_nav():
    active = st.session_state.view
    st.markdown('<div class="bottom-nav">', unsafe_allow_html=True)
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    def tab(btn, label, to):
        cls = "active" if active==to else ""
        with btn:
            st.markdown(f"<div class='{cls}'>", unsafe_allow_html=True)
            if st.button(label, key=f"nav_{to}"):
                navigate(to, push=False)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    tab(c1, "🏫 学校共有", "SHARE")
    tab(c2, "🌙 リラックス", "SESSION")
    tab(c3, "📝 ノート", "NOTE")
    tab(c4, "📚 Study", "STUDY")
    tab(c5, "📒 ふりかえり", "REVIEW")
    tab(c6, "🕊 相談", "CONSULT")
    st.markdown("</div>", unsafe_allow_html=True)

# ================= Breathing =================
def breath_patterns() -> Dict[str, Tuple[int, int, int]]:
    return {"gentle": (4, 0, 6), "calm": (5, 2, 6)}

def breathing_animation(total_sec: int = 90):
    inhale, hold, exhale = breath_patterns()[st.session_state.breath_mode]
    cycle = inhale + hold + exhale
    cycles = max(1, round(total_sec / cycle))
    ph = st.empty()
    spot = st.empty()
    for _ in range(cycles):
        ph.markdown('<span class="phase-pill">吸ってください</span>', unsafe_allow_html=True)
        spot.markdown(
            f'<div class="breath-wrap"><div class="breath-circle" style="animation:sora-grow {inhale}s linear forwards;"></div></div>',
            unsafe_allow_html=True,
        )
        time.sleep(inhale)
        if hold > 0:
            ph.markdown('<span class="phase-pill">止めてください</span>', unsafe_allow_html=True)
            spot.markdown(
                f'<div class="breath-wrap"><div class="breath-circle" style="animation:sora-steady {hold}s linear forwards;"></div></div>',
                unsafe_allow_html=True,
            )
            time.sleep(hold)
        ph.markdown('<span class="phase-pill">吐いてください</span>', unsafe_allow_html=True)
        spot.markdown(
            f'<div class="breath-wrap"><div class="breath-circle" style="animation:sora-shrink {exhale}s linear forwards;"></div></div>',
            unsafe_allow_html=True,
        )
        time.sleep(exhale)

# ================= Small UI helpers =================
def emo_pills(prefix: str, options: List[str], selected: List[str]) -> List[str]:
    st.markdown('<div class="emopills">', unsafe_allow_html=True)
    cols = st.columns(6)
    for i, label in enumerate(options):
        with cols[i % 6]:
            on = label in selected
            cls = "chip on" if on else "chip"
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(("✓ " if on else "") + label, key=f"{prefix}_{i}"):
                if on:
                    selected.remove(label)
                else:
                    selected.append(label)
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    return selected

def action_card(emoji: str, title: str, desc: str, key: str, accent_class: str = ""):
    st.markdown(f'<div class="action-card {accent_class}">', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 5])
    with c1:
        st.markdown(f'<div class="icon">{emoji}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f"<h3>{title}</h3>", unsafe_allow_html=True)
        st.markdown(f'<div class="desc">{desc}</div>', unsafe_allow_html=True)
        if st.button("→ 開く", key=key, type="primary"):
            navigate(title_to_view(title))
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def title_to_view(title: str) -> str:
    mapping = {
        "学校に伝える": "SHARE",
        "リラックス（呼吸）": "SESSION",
        "心を整える（ノート）": "NOTE",
        "Study": "STUDY",
        "ふりかえり": "REVIEW",
        "相談": "CONSULT",
    }
    return mapping.get(title, "HOME")

# ================= Views =================
def view_home():
    top_status()
    st.markdown("<h1>はじめに、やってみよう</h1>", unsafe_allow_html=True)
    st.caption("はじめての方でも、説明を読めばすぐ分かるようにしました。")

    # 朝の導線メッセージ（07:00〜11:00）
    local_now = datetime.now().astimezone()
    if 7 <= local_now.hour <= 11:
        st.info("☀️ 朝いちばんの“学校に伝える”をすませると、今日が少し整います。")

    # 学校共有を先頭・強調、その後に大きめカード
    action_card("🏫", "学校に伝える", "いまの気分・体調・睡眠を匿名で学校に共有します。毎朝 1 分で完了。", "OPEN_SHARE", "share")

    c1, c2 = st.columns(2)
    with c1:
        action_card("🌙", "リラックス（呼吸）", "円の動きに合わせて呼吸。90 秒で落ち着きを取り戻す。", "OPEN_SESSION")
    with c2:
        action_card("📝", "心を整える（ノート）", "気持ち・出来事・自分へのひとこと。やさしく整理するノートです。", "OPEN_NOTE")

    c3, c4 = st.columns(2)
    with c3:
        action_card("📚", "Study", "科目と時間を記録。あとで合計を可視化できます。", "OPEN_STUDY")
    with c4:
        action_card("📒", "ふりかえり", "直近の記録をカードで確認。小さな前進を見つけよう。", "OPEN_REVIEW")

    action_card("🕊", "相談", "気になること・困っていることを気軽に。匿名/非匿名も選べます。", "OPEN_CONSULT")

    st.markdown(
        """
<div style="text-align:center; color:#5a6b86; margin-top:6px;">
  <small>※ とてもつらい場合は、お住まいの地域の相談窓口や専門機関のご利用もご検討ください。<br>
  通知は夜間に鳴らないよう配慮しています。</small>
</div>
        """,
        unsafe_allow_html=True,
    )

def view_session():
    top_status()
    st.markdown('<div class="section-lead">🌙 リラックス（呼吸）</div>', unsafe_allow_html=True)
    st.caption("ゆっくり一緒に。円が大きくなったら吸って、小さくなったら吐きます。")

    mode = st.segmented_control("モード", options=["gentle","calm"], default=st.session_state.breath_mode, key="mode_seg") if hasattr(st, "segmented_control") else None
    if mode:
        st.session_state.breath_mode = mode
    else:
        st.session_state.breath_mode = st.selectbox("モード", ["gentle","calm"], index=1 if st.session_state.breath_mode=="calm" else 0)

    if st.button("🫁 はじめる（90秒）", type="primary"):
        st.session_state["_breath_running"] = True
        st.rerun()

    if st.session_state.get("_breath_running", False):
        breathing_animation(90)
        st.session_state["_breath_running"] = False
        st.success("お疲れさまでした。ありがとうございます。")

    st.divider()
    after = st.slider("いまの気分（-3 とてもつらい / +3 とても楽）", -3, 3, 0)
    if st.button("💾 記録を保存", type="primary"):
        mode = st.session_state.breath_mode
        inh, hold, exh = breath_patterns()[mode]
        Storage.append_user(
            Storage.BREATH, st.session_state.user_id,
            {"ts": now_iso(), "mode": mode, "target_sec": 90,
             "inhale": inh, "hold": hold, "exhale": exh,
             "mood_before": None, "mood_after": int(after), "delta": None, "trigger": "unknown"}
        )
        Storage.append_user(
            Storage.MIX, st.session_state.user_id,
            {"ts": now_iso(), "mode": "breath", "mood_after": int(after), "delta": None, "rescue_used": True}
        )
        st.success("保存しました。")

def view_note():
    top_status()
    st.markdown('<div class="section-lead">📝 心を整える（ノート）</div>', unsafe_allow_html=True)
    st.caption("いまの気持ちをお選びください。（複数可）")
    emos = st.session_state.get("note_emos", [])
    emos = emo_pills("emo",
        ["😟 不安", "😢 悲しい", "😠 いらだち", "😐 ぼんやり", "🙂 安心", "😊 うれしい"],
        emos)
    st.session_state["note_emos"] = emos

    st.markdown('<div class="card" style="margin-top:8px">', unsafe_allow_html=True)
    event = st.text_area("その気持ちの背景（出来事など）", value=st.session_state.get("note_event", ""), height=80)
    words = st.text_area("いまの自分への一言（やさしい言葉）", value=st.session_state.get("note_words", ""), height=70)
    switch = st.selectbox("いま合いそうな“スイッチ”", ["休息","体を少し動かす","外の空気・光に触れる","音や音楽","誰かと話す","目の前のタスクを終わらせる"], index=0)
    diary = st.text_area("今日の記録（ノート）", value=st.session_state.get("note_diary",""),
                         height=140, placeholder="例）朝は重かったけど、昼休みに外へ出たら少し楽になった。")
    st.markdown("</div>", unsafe_allow_html=True)

    st.session_state["note_event"] = event
    st.session_state["note_words"] = words
    st.session_state["note_diary"] = diary

    if st.button("💾 保存", type="primary"):
        uid = st.session_state.user_id
        Storage.append_user(Storage.CBT, uid, {
            "ts": now_iso(),
            "emotions": json.dumps({"multi": emos}, ensure_ascii=False),
            "triggers": event, "reappraise": words, "action":"", "value": switch
        })
        Storage.append_user(Storage.MIX, uid, {
            "ts": now_iso(), "mode":"note", "emos":" ".join(emos), "event":event,
            "oneword":words, "switch": switch, "memo": diary
        })
        st.success("保存しました。")

def view_share():
    top_status()
    st.markdown('<div class="section-lead">🏫 学校に伝える（匿名）</div>', unsafe_allow_html=True)
    st.caption("“いまの自分”を匿名で学校に共有します。毎朝 1 分。")

    mood = st.radio("気分", ["🙂", "😐", "😟"], index=1, horizontal=True, key="share_mood")
    body_opts = ["頭痛","腹痛","吐き気","食欲低下","だるさ","生理関連","その他なし"]
    body = st.multiselect("体調（当てはまるもの）", body_opts, default=["その他なし"], key="share_body")
    if "その他なし" in body and len(body) > 1:
        body = [b for b in body if b != "その他なし"]

    c1, c2 = st.columns(2)
    with c1:
        sh = st.number_input("睡眠時間（h）", min_value=0.0, max_value=24.0, value=6.0, step=0.5, key="share_sleep_h")
    with c2:
        sq = st.radio("睡眠の質", ["ぐっすり","ふつう","浅い"], index=1, horizontal=True, key="share_sleep_q")

    st.markdown("#### プレビュー")
    st.markdown(
        f"""
<div class="item">
  <div class="meta">{datetime.now().astimezone().isoformat(timespec="seconds")}</div>
  <div style="font-weight:900; color:#24466e; margin-bottom:.3rem">本日の共有内容</div>
  <div style="margin:.2rem 0;">気分：<span class="badge">{mood}</span></div>
  <div style="margin:.2rem 0;">体調：{"".join([f"<span class='badge'>{b}</span>" for b in (body or ['なし'])])}</div>
  <div style="margin:.2rem 0;">睡眠：<b>{sh:.1f} 時間</b> / 質：<span class="badge">{sq}</span></div>
</div>
        """, unsafe_allow_html=True
    )

    if st.button("📨 匿名で送信", type="primary", key="share_submit"):
        preview = {"mood":mood, "body":body, "sleep_hours":float(sh), "sleep_quality":sq}
        Storage.append_user(Storage.SHARED, st.session_state.user_id, {
            "ts": now_iso(), "scope":"本日", "share_flags":{"emotion":True,"body":True,"sleep":True},
            "payload": preview, "anonymous": True
        })
        st.success("送信しました。ありがとうございます。")

def view_consult():
    top_status()
    st.markdown('<div class="section-lead">🕊 相談</div>', unsafe_allow_html=True)
    st.caption("できるだけ気軽に。次の質問に答えると、届け方を選べます。")

    # 1) 相談の意図
    intent = st.selectbox(
        "どのように扱いたいですか？",
        ["AIにだけ保存（自分の記録）", "学校に共有したい", "運営（カウンセラー/先生）に相談したい", "まだ決められない"],
        index=0,
        key="c_intent"
    )

    # 2) カテゴリ
    category = st.multiselect(
        "どんな内容に近いですか？（複数可）",
        ["学校", "家庭", "友人・人間関係", "健康（心身）", "SNS/ネット", "進路・勉強", "その他"],
        default=[],
        key="c_cats"
    )

    # 3) 匿名/非匿名
    anonymous = st.checkbox("匿名で送る", value=True, key="c_anon")
    contact_pref = ""
    if not anonymous:
        contact_pref = st.text_input("差し支えなければ、連絡先（任意）", placeholder="例）メール / 学校の連絡帳 / Teamsなど", key="c_contact")

    # 4) 本文
    msg = st.text_area(
        "いまのお気持ち・状況をお聞かせください。",
        height=200,
        placeholder="（例）最近、朝がつらくて起きられません。授業の遅刻が増えて心配です…",
        key="c_msg"
    )

    # 5) 学内共有の希望（意図に応じて）
    share_scope = "非共有"
    if intent in ["学校に共有したい", "運営（カウンセラー/先生）に相談したい"]:
        share_scope = st.selectbox(
            "どの範囲に伝えたいですか？",
            ["学年の担当者まで", "担任のみ", "スクールカウンセラーのみ", "運営チームのみ"],
            index=0,
            key="c_scope"
        )

    if crisis(msg):
        st.warning("とても苦しいお気持ちが伝わってきます。必要に応じて、お住まいの地域の相談窓口や専門機関もご検討ください。")

    disabled = (msg.strip() == "")
    if st.button("🕊 送信", type="primary", disabled=disabled, key="c_submit"):
        payload = {
            "ts": now_iso(),
            "message": msg.strip(),
            "intent": intent,
            "categories": category,
            "anonymous": bool(anonymous),
            "contact_pref": contact_pref.strip() if contact_pref else "",
            "share_scope": share_scope,
        }
        Storage.append_user(Storage.CONSULT, st.session_state.user_id, payload)
        st.success("送信しました。ありがとうございます。")

def view_review():
    top_status()
    st.markdown('<div class="section-lead">📒 ふりかえり</div>', unsafe_allow_html=True)
    uid = st.session_state.user_id

    def daterange(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        df["ts"] = pd.to_datetime(df["ts"])
        today = datetime.now().date()
        c1, c2 = st.columns(2)
        with c1:
            since = st.date_input("開始日", value=today - timedelta(days=14), key="rev_since")
        with c2:
            until = st.date_input("終了日", value=today, key="rev_until")
        return (
            df[(df["ts"].dt.date >= since) & (df["ts"].dt.date <= until)]
            .copy()
            .sort_values("ts", ascending=False)
        )

    st.markdown('<div class="Utabs">', unsafe_allow_html=True)
    tabs = st.tabs(["ホーム/ノート", "呼吸", "Study"])
    st.markdown("</div>", unsafe_allow_html=True)

    # MIX
    with tabs[0]:
        df = Storage.load_user(Storage.MIX, uid)
        if df.empty:
            st.caption("まだ記録がありません。")
        else:
            df = daterange(df)
            st.markdown('<div class="grid-2">', unsafe_allow_html=True)
            for _, r in df.iterrows():
                badges = []
                if r.get("mode") == "breath":
                    badges.append("呼吸")
                title = r.get("oneword") or r.get("switch") or r.get("mode", "")
                memo = r.get("memo", "")
                st.markdown(
                    f"""
<div class="item">
  <div class="meta">{r['ts']}</div>
  <div style="font-weight:900; color:#24466e; margin-bottom:.3rem">{title}</div>
  <div style="white-space:pre-wrap; margin-bottom:.4rem">{memo}</div>
  <div>{" ".join([f"<span class='badge'>{b}</span>" for b in badges])}</div>
</div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

    # BREATH
    with tabs[1]:
        df = Storage.load_user(Storage.BREATH, uid)
        if df.empty:
            st.caption("まだ記録がありません。")
        else:
            df = daterange(df)
            st.markdown('<div class="grid-3">', unsafe_allow_html=True)
            for _, r in df.iterrows():
                delta = r.get("delta")
                dtxt = "" if delta is None else f"<span class='badge'>Δ {int(delta):+d}</span>"
                st.markdown(
                    f"""
<div class="item">
  <div class="meta">{r['ts']}</div>
  <div>モード：<b>{r.get('mode','')}</b> / 目標：{r.get('target_sec',90)}秒</div>
  <div>前後：{r.get('mood_before','-')} → {r.get('mood_after','-')} {dtxt}</div>
</div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

    # STUDY
    with tabs[2]:
        df = Storage.load_user(Storage.STUDY, uid)
        if df.empty:
            st.caption("まだ記録がありません。")
        else:
            df["ts"] = pd.to_datetime(df["ts"])
            df = df.sort_values("ts", ascending=False)
            st.markdown('<div class="grid-2">', unsafe_allow_html=True)
            for _, r in df.iterrows():
                totalmin = int(r.get("minutes", 0))
                p = max(0.0, min(100.0, float(totalmin)))  # 簡易バー（分を%表示）
                st.markdown(
                    f"""
<div class="item">
  <div class="meta">{r['ts'].isoformat(timespec="seconds") if hasattr(r['ts'],'isoformat') else r['ts']}</div>
  <div style="font-weight:900">{r.get('subject','')}</div>
  <div>分：{totalmin} / 状況：{r.get('mood','')}</div>
  <div class="prog" style="margin-top:.4rem"><div style="width:{p}%"></div></div>
  <div style="white-space:pre-wrap; color:#3b4f71; margin-top:.3rem">{r.get('memo','')}</div>
</div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

def view_study():
    top_status()
    st.markdown('<div class="section-lead">📚 Study</div>', unsafe_allow_html=True)
    uid = st.session_state.user_id
    subjects = Storage.get_subjects(uid)

    l, r = st.columns(2)
    with l:
        subj = st.selectbox("科目", subjects, index=0, key="study_subj")
        add = st.text_input("＋ 自分の科目を追加（Enter）", key="study_add")
        if add.strip():
            if add.strip() not in subjects:
                subjects.append(add.strip())
                Storage.save_subjects(uid, subjects)
                st.success(f"追加：{add.strip()}")
    with r:
        mins = st.number_input("学習時間（分）", 1, 600, 30, 5, key="study_min")
        mood = st.selectbox("状況", ["順調","難航","しんどい","集中","だるい","眠い","その他"], index=0, key="study_mood")
    memo = st.text_input("メモ（任意）", key="study_memo")

    if st.button("💾 記録", type="primary", key="study_save"):
        Storage.append_user(Storage.STUDY, uid, {
            "ts": now_iso(), "subject": (add.strip() or subj),
            "minutes": int(mins), "mood": mood, "memo": memo
        })
        st.success("保存しました。")

    df = Storage.load_user(Storage.STUDY, uid)
    if not df.empty:
        agg = (
            df.groupby("subject")["minutes"]
            .sum()
            .reset_index()
            .sort_values("minutes", ascending=False)
        )
        total = max(1, int(agg["minutes"].sum()))
        st.markdown("#### 科目別の合計")
        st.markdown('<div class="grid-2">', unsafe_allow_html=True)
        for _, r in agg.iterrows():
            p = round(r["minutes"] / total * 100, 1)
            st.markdown(
                f"""
<div class="item">
  <div style="font-weight:900">{r['subject']}</div>
  <div class="meta">合計：{int(r['minutes'])} 分</div>
  <div class="prog"><div style="width:{p}%"></div></div>
  <div class="meta">{p}%</div>
</div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

# ================= Router =================
def main_router():
    v = st.session_state.view
    if v == "HOME":
        view_home()
    elif v == "SESSION":
        view_session()
    elif v == "NOTE":
        view_note()
    elif v == "SHARE":
        view_share()
    elif v == "CONSULT":
        view_consult()
    elif v == "REVIEW":
        view_review()
    elif v == "STUDY":
        view_study()
    else:
        view_home()
    # 固定ボトムナビはどの画面でも表示
    bottom_nav()

# ================= App =================
if auth_ui():
    logout_btn()
    main_router()
