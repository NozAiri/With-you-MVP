# app.py — Sora / With You.（HOME復活：説明つきボタンのみ／重複キー対策／ノート改訂）
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import List
import pandas as pd
import streamlit as st
import json, time, re
import altair as alt

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
@import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700;900&display=swap');

:root{
  --bg1:#f2f6ff; --bg2:#eaf4ff;
  --panel:#ffffffee; --panel-brd:#e1e9ff;
  --text:#1b2a45; --muted:#5c6f8f;
  --accent:#5EA3FF; --accent-2:#96BDFF; --accent-3:#7FD6C2; --accent-4:#F7B7C3; --accent-5:#FFE59A;
  --card:#fff; --shadow:0 14px 34px rgba(40,80,160,.12);
  --grad-app: linear-gradient(180deg, #f4f8ff, #eaf5ff);
}

html, body, .stApp{
  font-family: "Zen Maru Gothic", system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans JP", sans-serif;
  background: var(--grad-app);
  color: var(--text);
}
.block-container{ max-width:980px; padding-top:1.0rem; padding-bottom:2.2rem }

/* ---------- Sticky Top Tabs ---------- */
.top-tabs{
  position: sticky; top: 0; z-index: 50;
  background: rgba(250,253,255,.85); backdrop-filter: saturate(160%) blur(8px);
  border: 1px solid #dfe6ff; border-radius: 16px; box-shadow: 0 12px 24px rgba(70,120,200,.12);
  padding: 6px 8px; margin-bottom: 14px;
}
.top-tabs .stButton>button{
  width:100%; height:40px; border-radius: 12px;
  background: #f6f9ff; border: 1px solid #e1eaff; font-weight: 900; color:#35527a;
}
.top-tabs .active .stButton>button{
  background: #eaf3ff; border-bottom: 3px solid var(--accent); border-top: 1px solid #e1eaff; color:#17345c;
}

/* ---------- Cards ---------- */
.card{ background:var(--panel); border:1px solid var(--panel-brd); border-radius:22px; padding:18px; box-shadow:var(--shadow) }
.item{ background:var(--card); border:1px solid var(--panel-brd); border-radius:18px; padding:16px; box-shadow:var(--shadow) }
.item .meta{ color:var(--muted); font-size:.9rem; margin-bottom:.2rem }
.badge{ display:inline-block; padding:.2rem .6rem; border:1px solid #d6e7ff; border-radius:999px; margin-right:.4rem; color:#29466e; background:#f6faff; font-weight:900 }

/* ---------- Big buttons on HOME ---------- */
.bigbtn{ margin-bottom:12px; }
.bigbtn .stButton>button{
  width:100%;
  text-align:left;
  border-radius:22px;
  border:1px solid #dfe6ff;
  box-shadow:var(--shadow);
  padding:18px 18px 16px;
  font-weight:700;
  white-space:pre-wrap;           /* 改行を生かす */
  line-height:1.35;
  transition: transform .08s ease, box-shadow .08s ease;
  background: linear-gradient(135deg,#ffffff 0%,#eef5ff 100%);
  color:#12294a;
}
.bigbtn .stButton>button:hover{ transform: translateY(-1px); box-shadow:0 18px 30px rgba(70,120,200,.14); }

/* ---------- Emotion pills ---------- */
.emopills{display:grid; grid-template-columns:repeat(3,1fr); gap:10px}
@media (min-width:820px){ .emopills{ grid-template-columns:repeat(6,1fr) } }
.emopills .chip .stButton>button{
  background:linear-gradient(135deg,#ffffff 0%,#eef5ff 100%) !important; color:#1d3457 !important;
  border:2px solid #d6e7ff !important; border-radius:16px !important;
  box-shadow:0 6px 16px rgba(100,140,200,.08) !important; font-weight:900 !important; padding:12px 12px !important;
}
.emopills .chip.on .stButton>button{ border:2px solid var(--accent) !important; background:#eefdff !important }

/* ---------- Progress ---------- */
.prog{height:12px; background:#eef4ff; border-radius:999px; overflow:hidden}
.prog > div{height:12px; background:var(--accent-2)}

/* ---------- Generic Buttons ---------- */
.stButton>button{ border-radius:14px; font-weight:900; }

/* ---------- Breathing keyframes ---------- */
@keyframes sora-grow{ from{ transform:scale(1.0);} to{ transform:scale(1.6);} }
@keyframes sora-steady{ from{ transform:scale(1.6);} to{ transform:scale(1.6);} }
@keyframes sora-shrink{ from{ transform:scale(1.6);} to{ transform:scale(1.0);} }

/* ---------- Tiny helper ---------- */
.tip{ color:#6a7d9e; font-size:.92rem; }
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

# 既定ビューは HOME
st.session_state.setdefault("_auth_ok", False)
st.session_state.setdefault("role", None)
st.session_state.setdefault("user_id", "")
st.session_state.setdefault("view", "HOME")
st.session_state.setdefault("_nav_stack", [])
st.session_state.setdefault("_breath_running", False)
st.session_state.setdefault("_breath_stop", False)

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

# ================= Nav (Top Tabs) =================
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
    st.markdown('<div class="card" style="padding:8px 12px; margin-bottom:10px">', unsafe_allow_html=True)
    st.markdown(
        f"<div class='tip'>ログイン中：{'運営' if st.session_state.role=='admin' else f'利用者（{st.session_state.user_id}）'}</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ================= Breathing =================
BREATH_PATTERN = (5, 2, 6)  # 5-2-6

def breathing_animation(total_sec: int = 90):
    inhale, hold, exhale = BREATH_PATTERN
    cycle = inhale + hold + exhale
    cycles = max(1, round(total_sec / cycle))

    ph = st.empty(); spot = st.empty(); ctrl = st.empty()

    def phase(label, seconds, anim_css):
        ph.markdown(f"**{label}**")
        spot.markdown(
            f'<div style="display:flex;justify-content:center;align-items:center;padding:10px 0 6px">'
            f'<div style="width:260px;height:260px;border-radius:999px;background:radial-gradient(circle at 50% 40%, #f7fbff, #e8f2ff 60%, #eef8ff 100%);'
            f'box-shadow:0 18px 36px rgba(90,140,190,.14), inset 0 -10px 25px rgba(120,150,200,.15);animation:{anim_css} {seconds}s linear forwards;border:solid #dbe9ff"></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        for _ in range(seconds):
            if st.session_state.get("_breath_stop") or st.session_state.view != "SESSION":
                return False
            time.sleep(1)
        return True

    with ctrl.container():
        if st.button("⏹ 停止する", key="breath_stop"):
            st.session_state["_breath_stop"] = True

    for _ in range(cycles):
        if not phase("吸ってください", inhale, "sora-grow"): break
        if hold > 0 and not phase("止めてください", hold, "sora-steady"): break
        if not phase("吐いてください", exhale, "sora-shrink"): break

    st.session_state["_breath_running"] = False
    st.session_state["_breath_stop"] = False
    ph.empty(); spot.empty(); ctrl.empty()

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
                if on: selected.remove(label)
                else:  selected.append(label)
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    return selected

# ---------- HOME（説明つきボタンのみ） ----------
def home_big_button(title: str, desc: str, target_view: str, key: str, emoji: str):
    with st.container():
        st.markdown('<div class="bigbtn">', unsafe_allow_html=True)
        # ラベルはプレーンテキストのみ（改行で説明表示）
        label = f"{emoji} {title}\n{desc}"
        if st.button(label, key=key):
            navigate(target_view, push=True)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

def view_home():
    # 1列目：今日を伝える
    home_big_button(
        "今日を伝える",
        "今日の気分や体調を共有して、先生や学校に安心して知ってもらうために。",
        "SHARE", "OPEN_SHARE", "🏫"
    )
    # 2列目：2カラム（リラックス・ノート）
    c1, c2 = st.columns(2)
    with c1:
        home_big_button(
            "リラックスする",
            "呼吸に合わせて、緊張や不安を少しずつ和らげるために。",
            "SESSION", "OPEN_SESSION", "🌙"
        )
    with c2:
        home_big_button(
            "心を整えるノート",
            "感じていることを言葉にして、いまの自分を整理するために。",
            "NOTE", "OPEN_NOTE", "📝"
        )
    # 3列目：2カラム（Study・ふりかえり）
    c3, c4 = st.columns(2)
    with c3:
        home_big_button(
            "Study Tracker",
            "学習時間をふりかえり、進捗を“見える形”にするために。",
            "STUDY", "OPEN_STUDY", "📚"
        )
    with c4:
        home_big_button(
            "ふりかえり",
            "日々の小さな変化を見つめ、明日につながる気づきを得るために。",
            "REVIEW", "OPEN_REVIEW", "📒"
        )
    # 最後：相談
    home_big_button(
        "相談する",
        "不安や悩みを安心して伝え、必要なサポートにつながるために。",
        "CONSULT", "OPEN_CONSULT", "🕊"
    )

# ---------- 他ビュー ----------
NEXT_STEP_CHOICES = [
    "5分だけ深呼吸する",
    "コップ1杯の水を飲む",
    "外に出て空気を吸う／散歩1～3分",
    "信頼できる人に短く共有する",
    "先生・カウンセラーに伝える",
    "5分だけやる（宿題・片づけ）",
    "短く休む（目を閉じる・背伸び）",
    "感情をノートに書く",
]

def view_session():
    st.markdown("### 🌙 リラックス（呼吸）")
    st.caption("円が大きくなったら吸って、小さくなったら吐きます。途中で停止・ページ移動できます。")

    c1, c2 = st.columns([1,1])
    with c1:
        if not st.session_state.get("_breath_running", False):
            if st.button("🫁 はじめる（90秒）", type="primary"):
                st.session_state["_breath_running"] = True
                st.session_state["_breath_stop"] = False
                st.rerun()
        else:
            st.info("実行中です。上のタブから他ページへ移動できます。")
    with c2:
        if st.session_state.get("_breath_running", False):
            if st.button("⏹ 停止", key="stop_btn", type="secondary"):
                st.session_state["_breath_stop"] = True

    if st.session_state.get("_breath_running", False):
        breathing_animation(90)
        st.success("お疲れさまでした。ありがとうございます。")

    st.divider()
    after = st.slider("いまのご気分（1 とてもつらい / 10 とても楽）", 1, 10, 5)
    if st.button("💾 記録を保存", type="primary"):
        inh, hold, exh = BREATH_PATTERN
        Storage.append_user(
            Storage.BREATH, st.session_state.user_id,
            {"ts": now_iso(), "mode": "calm", "target_sec": 90,
             "inhale": inh, "hold": hold, "exhale": exh,
             "mood_before": None, "mood_after": int(after), "delta": None, "trigger": "unknown"}
        )
        Storage.append_user(
            Storage.MIX, st.session_state.user_id,
            {"ts": now_iso(), "mode": "breath", "mood_after": int(after), "delta": None, "rescue_used": True}
        )
        st.success("保存しました。")

def view_note():
    st.markdown("### 📝 心を整えるノート")
    st.caption("いまの気持ちを選んでから、下の3つ＋日記に進みます。")

    emos = st.session_state.get("note_emos", [])
    emos = emo_pills("emo",
        ["😟 不安", "😢 悲しい", "😠 いらだち", "😐 ぼんやり", "🙂 安心", "😊 うれしい"],
        emos)
    st.session_state["note_emos"] = emos

    st.markdown('<div class="card" style="margin-top:8px">', unsafe_allow_html=True)

    q1 = st.text_area("① その気持ちはどうして？",
                      value=st.session_state.get("note_q1",""), height=110)

    q2 = st.text_area("② どうしたいですか？",
                      value=st.session_state.get("note_q2",""), height=100)

    st.markdown("**③ 状況を少しでもよくする“次の一歩”は？（小さな行動）**")
    chosen = st.multiselect("当てはまるものを選んでください（複数選択可）",
                            NEXT_STEP_CHOICES,
                            default=st.session_state.get("note_q3_sel", []),
                            key="note_q3_sel")
    q3_free = st.text_input("自由入力（任意）", value=st.session_state.get("note_q3_free",""))
    next_step_str = " / ".join(chosen + ([q3_free] if q3_free.strip() else []))

    q4 = st.text_area("④ 今日の振り返り（日記）",
                      value=st.session_state.get("note_q4",""),
                      height=180,
                      placeholder="今日の出来事や気づきを自由にどうぞ。")

    st.markdown("</div>", unsafe_allow_html=True)

    st.session_state["note_q1"] = q1
    st.session_state["note_q2"] = q2
    st.session_state["note_q3_free"] = q3_free
    st.session_state["note_q4"] = q4

    if st.button("💾 保存", type="primary"):
        uid = st.session_state.user_id
        payload = {
            "ts": now_iso(),
            "emotions": json.dumps({"multi": emos}, ensure_ascii=False),
            "why": q1,
            "want": q2,
            "next_step": next_step_str,
            "next_step_options": chosen,
            "reflection": q4
        }
        Storage.append_user(Storage.CBT, uid, payload)
        Storage.append_user(Storage.MIX, uid, {
            "ts": now_iso(), "mode":"note", "emos":" ".join(emos),
            "event": q1, "oneword": q2, "switch": "", "memo": f"next: {next_step_str}\nref: {q4}"
        })
        st.success("保存しました。")

def view_share():
    st.markdown("### 🏫 今日を伝える（匿名可）")

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

    if st.button("📨 送信（匿名）", type="primary", key="share_submit"):
        preview = {"mood":mood, "body":body, "sleep_hours":float(sh), "sleep_quality":sq}
        Storage.append_user(Storage.SHARED, st.session_state.user_id, {
            "ts": now_iso(), "scope":"本日", "share_flags":{"emotion":True,"body":True,"sleep":True},
            "payload": preview, "anonymous": True
        })
        st.success("送信しました。ありがとうございます。")

def view_consult():
    st.markdown("### 🕊 相談")
    st.caption("お気軽に。秘密は守ります。お名前は任意です。")

    to_whom = st.radio("相談先を選んでください", ["カウンセラーに相談したい", "先生に伝えたい"], horizontal=True, key="c_to")
    anonymous = st.checkbox("匿名で送る", value=True, key="c_anon")
    name = "" if anonymous else st.text_input("お名前（任意）", value="", key="c_name")
    msg = st.text_area("ご相談したい／伝えたい内容について教えてください。", height=220, value=st.session_state.get("c_msg",""), key="c_msg")

    if crisis(msg):
        st.warning("とても苦しいお気持ちが伝わってきます。必要に応じて、お住まいの地域の相談窓口や専門機関もご検討ください。")

    if st.button("🕊 送信する", type="primary", disabled=(msg.strip()=="") , key="c_submit"):
        payload = {
            "ts": now_iso(),
            "message": msg.strip(),
            "intent": "counselor" if to_whom.startswith("カウンセラー") else "teacher",
            "anonymous": bool(anonymous),
            "name": name.strip() if name else "",
        }
        Storage.append_user(Storage.CONSULT, st.session_state.user_id, payload)
        st.success("送信しました。ありがとうございます。")

def view_review():
    st.markdown("### 📒 ふりかえり")
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

    st.markdown('<div class="card" style="padding-top:8px">', unsafe_allow_html=True)
    tabs = st.tabs(["ホーム/ノート", "呼吸", "Study Tracker"])

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
  <div>目標：{r.get('target_sec',90)}秒 / パターン：5-2-6</div>
  <div>前後：{r.get('mood_before','-')} → {r.get('mood_after','-')} {dtxt}</div>
</div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

    with tabs[2]:
        df = Storage.load_user(Storage.STUDY, uid)
        if df.empty:
            st.caption("まだ記録がありません。")
        else:
            df["ts"] = pd.to_datetime(df["ts"])
            df = df.sort_values("ts", ascending=False)

            st.markdown("### 教科別の時間配分")
            pie_agg = (
                df.groupby("subject")["minutes"]
                .sum()
                .reset_index()
                .sort_values("minutes", ascending=False)
            )
            if not pie_agg.empty:
                color_scale = alt.Scale(
                    domain=pie_agg["subject"].tolist(),
                    range=["#A5C8FF","#CDE9D3","#F9D5E5","#FFE7B3","#C9E7FF","#EAD9FF","#BFE9E2"]
                )
                pie = (
                    alt.Chart(pie_agg)
                    .mark_arc(innerRadius=60)
                    .encode(
                        theta=alt.Theta(field="minutes", type="quantitative"),
                        color=alt.Color(field="subject", type="nominal", legend=alt.Legend(title="科目"), scale=color_scale),
                        tooltip=[alt.Tooltip("subject:N", title="科目"), alt.Tooltip("minutes:Q", title="合計分")]
                    ).properties(width=340, height=340)
                )
                st.altair_chart(pie, use_container_width=False)

            st.markdown('<div class="grid-2" style="margin-top:8px">', unsafe_allow_html=True)
            for _, r in df.iterrows():
                totalmin = int(r.get("minutes", 0))
                p = max(0.0, min(100.0, float(totalmin)))
                ts_txt = pd.to_datetime(r['ts']).isoformat(timespec="seconds")
                st.markdown(
                    f"""
<div class="item">
  <div class="meta">{ts_txt}</div>
  <div style="font-weight:900">{r.get('subject','')}</div>
  <div>分：{totalmin} / 状況：{r.get('mood','')}</div>
  <div class="prog" style="margin-top:.4rem"><div style="width:{p}%"></div></div>
  <div style="white-space:pre-wrap; color:#3b4f71; margin-top:.3rem">{r.get('memo','')}</div>
</div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

            total_min = int(df["minutes"].sum())
            st.info(f"⏱️ これまでの合計学習時間：**{total_min} 分**")

def view_study():
    st.markdown("### 📚 Study Tracker")
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
        st.markdown("### 教科別の時間配分")
        pie_agg = (
            df.groupby("subject")["minutes"]
            .sum()
            .reset_index()
            .sort_values("minutes", ascending=False)
        )
        if not pie_agg.empty:
            color_scale = alt.Scale(
                domain=pie_agg["subject"].tolist(),
                range=["#A5C8FF","#CDE9D3","#F9D5E5","#FFE7B3","#C9E7FF","#EAD9FF","#BFE9E2"]
            )
            pie = (
                alt.Chart(pie_agg)
                .mark_arc(innerRadius=60)
                .encode(
                    theta=alt.Theta(field="minutes", type="quantitative"),
                    color=alt.Color(field="subject", type="nominal", legend=alt.Legend(title="科目"), scale=color_scale),
                    tooltip=[alt.Tooltip("subject:N", title="科目"), alt.Tooltip("minutes:Q", title="合計分")]
                ).properties(width=340, height=340)
            )
            st.altair_chart(pie, use_container_width=False)

        df["ts"] = pd.to_datetime(df["ts"])
        df["date"] = df["ts"].dt.date
        recent = (
            df.groupby("date")["minutes"]
            .sum()
            .reset_index()
            .sort_values("date")
        )
        recent = recent[recent["date"] >= (datetime.now().date() - timedelta(days=14))]
        if not recent.empty:
            st.markdown("### 直近14日の合計（1日あたり）")
            line = (
                alt.Chart(recent)
                .mark_line(point=True)
                .encode(
                    x=alt.X("date:T", title="日付"),
                    y=alt.Y("minutes:Q", title="合計分"),
                    tooltip=[alt.Tooltip("date:T", title="日付"), alt.Tooltip("minutes:Q", title="合計分")]
                ).properties(width="container", height=260)
            )
            st.altair_chart(line, use_container_width=True)

        total_min = int(df["minutes"].sum())
        st.info(f"⏱️ 合計学習時間：**{total_min} 分**")

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
            st.session_state["_breath_stop"] = False
            st.rerun()

# ================= App =================
if auth_ui():
    logout_btn()
    # 上部タブ & ステータスはここで1回だけ描画（重複キー回避）
    top_tabs()
    top_status()
    main_router()
