# app.py — With You.（水色パステル｜Firestoreストレージ版）
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple, List
import pandas as pd
import streamlit as st
import time, json, re

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
    st.markdown("""
<style>
:root{
  --bg1:#f3f7ff; --bg2:#eefaff;
  --panel:#ffffffee; --panel-brd:#e1e9ff;
  --text:#21324b; --muted:#5a6b86; --outline:#76a8ff;
  --grad-from:#cfe4ff; --grad-to:#b9d8ff; --chip-brd:rgba(148,188,255,.45);
  --tile-a:#d9ebff; --tile-b:#edf5ff; --tile-c:#d0f1ff; --tile-d:#ebfbff;

  /* 新：ナビUI（白×ネイビー）／入力UI（パステルブルー）を分離 */
  --nav-bg:#ffffff; --nav-fg:#1f3352; --nav-brd:#d9e5ff;
  --form-bg:#f8fbff; --form-brd:#e1e9ff;
}
html, body, .stApp{
  background: radial-gradient(1200px 600px at 20% -10%, #ffffff 0%, var(--bg1) 40%, transparent 70%),
              radial-gradient(1000px 520px at 100% 0%,  #ffffff 0%, var(--bg2) 50%, transparent 80%),
              linear-gradient(180deg, var(--bg1), var(--bg2));
}
.block-container{max-width:980px; padding-top:.4rem; padding-bottom:2rem}
h1,h2,h3{color:var(--text); letter-spacing:.2px}
p,label,.stMarkdown,.stTextInput,.stTextArea{color:var(--text); font-size:1.02rem}
small{color:#5a6b86}
.card{
  background:var(--panel); border:1px solid var(--panel-brd);
  border-radius:16px; padding:18px; margin-bottom:14px;
  box-shadow:0 10px 30px rgba(40,80,160,.07)
}

/* Topbar nav（白×ネイビー） */
.topbar{
  position:sticky; top:0; z-index:10; background:#fffffff2; backdrop-filter:blur(8px);
  border-bottom:1px solid var(--panel-brd); margin:0 -12px 8px; padding:8px 12px 10px
}
.topnav{display:flex; gap:8px; flex-wrap:wrap; margin:2px 0}
.topnav .nav-btn>button{
  background:var(--nav-bg) !important; color:var(--nav-fg) !important; border:1px solid var(--nav-brd) !important;
  height:auto !important; padding:9px 12px !important; border-radius:999px !important;
  font-weight:700 !important; font-size:.95rem !important;
  box-shadow:0 6px 14px rgba(40,80,160,.08) !important;
}
.topnav .active>button{background:#f6fbff !important; border:2px solid var(--outline) !important}
.nav-hint{font-size:.78rem; color:#6d7fa2; margin:0 2px 6px 2px}

/* 入力エリア（パステル） */
.form-wrap{border:1px solid var(--form-brd); background:var(--form-bg); border-radius:14px; padding:12px}

/* Buttons */
.stButton>button,.stDownloadButton>button{
  width:100%; padding:12px 16px; border-radius:999px; border:1px solid var(--chip-brd);
  background:linear-gradient(180deg,var(--grad-from),var(--grad-to)); color:#25334a; font-weight:900; font-size:1.02rem;
  box-shadow:0 10px 24px rgba(90,150,240,.16)
}
.stButton>button:hover{filter:brightness(.98)}

/* タイル */
.tile-grid{display:grid; grid-template-columns:1fr; gap:18px; margin-top:8px}
.tile .stButton>button{
  aspect-ratio:7/2; min-height:76px; border-radius:22px; text-align:center; padding:18px;
  border:none; font-weight:900; font-size:1.12rem; color:#1e2e49; box-shadow:0 12px 26px rgba(40,80,160,.12);
  display:flex; align-items:center; justify-content:center;
}
.tile-a .stButton>button{background:linear-gradient(160deg,var(--tile-a),var(--tile-b))}

/* 呼吸丸（CSSアニメ） */
.breath-wrap{display:flex; justify-content:center; align-items:center; padding:8px 0 4px}
.breath-circle{
  width:230px; height:230px; border-radius:999px;
  background:radial-gradient(circle at 50% 40%, #f7fbff, #e8f2ff 60%, #eef8ff 100%);
  box-shadow:0 16px 32px rgba(90,140,190,.14), inset 0 -10px 25px rgba(120,150,200,.15);
  transform:scale(1);
  border: solid #dbe9ff;
}
@keyframes sora-grow{ from{ transform:scale(1.0);   border-width:10px;} to{ transform:scale(1.6); border-width:14px;} }
@keyframes sora-steady{ from{ transform:scale(1.6);   border-width:14px;} to{ transform:scale(1.6); border-width:14px;} }
@keyframes sora-shrink{from{ transform:scale(1.6);   border-width:14px;} to{ transform:scale(1.0); border-width:8px;} }

.phase-pill{display:inline-block; padding:.20rem .7rem; border-radius:999px; background:#edf5ff;
  color:#2c4b77; border:1px solid #d6e7ff; font-weight:700}
.subtle{color:#5d6f92; font-size:.92rem}

/* Emotion pills（白ベース＋青アウトライン） */
.emopills{display:grid; grid-template-columns:repeat(6,1fr); gap:8px}
.emopills .stButton>button{
  background:#ffffff !important; color:#223552 !important;
  border:1.5px solid #d6e7ff !important; border-radius:14px !important;
  box-shadow:none !important; font-weight:700 !important; padding:10px 12px !important;
}
.emopills .on>button{border:2px solid #76a8ff !important; background:#f3f9ff !important}

/* バッジ */
.badge{display:inline-block; padding:.2rem .6rem; border-radius:999px; border:1px solid #dbe6ff; background:#fff; color:#28456e; font-weight:700}

/* KPIカード */
.kpi-grid{display:grid; grid-template-columns:repeat(3,1fr); gap:12px}
.kpi{ background:#fff; border:1px solid var(--panel-brd); border-radius:16px; padding:14px; text-align:center;
  box-shadow:0 8px 20px rgba(40,80,160,.06) }
.kpi .num{font-size:1.6rem; font-weight:900; color:#28456e}
.kpi .lab{color:#5a6b86; font-size:.9rem}

/* 入力 */
textarea, input, .stTextInput>div>div>input{
  border-radius:12px!important; background:#ffffff; color:#2a3a55; border:1px solid #e1e9ff
}

/* Mobile */
@media (max-width: 680px){
  .kpi-grid{grid-template-columns:1fr 1fr}
  .tile-grid{grid-template-columns:1fr}
  .emopills{grid-template-columns:repeat(4,1fr)}
}
</style>
""", unsafe_allow_html=True)

inject_css()
HOUR = datetime.now().hour
if (HOUR>=20 or HOUR<5):
    st.markdown("<style>:root{ --muted:#4a5a73; }</style>", unsafe_allow_html=True)

# ================= Firestore Storage abstraction =================
def firestore_client():
    creds = service_account.Credentials.from_service_account_info(st.secrets["FIREBASE_SERVICE_ACCOUNT"])
    return firestore.Client(project=st.secrets["FIREBASE_SERVICE_ACCOUNT"]["project_id"], credentials=creds)

DB = firestore_client()

class Storage:
    # Firestore collections
    CBT   = "cbt_entries"
    BREATH= "breath_sessions"
    MIX   = "mix_note"
    STUDY = "study_blocks"
    SCHOOL= "school_inbox"       # 新：匿名相談の投入口

    @staticmethod
    def now_ts_iso():
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    # 既存：ユーザーID付き保存
    @staticmethod
    def append_user(table: str, user_id: str, row: dict):
        row = dict(row)
        if "ts" not in row:
            row["ts"] = firestore.SERVER_TIMESTAMP
            row["_ts_iso"] = Storage.now_ts_iso()
        else:
            row["_ts_iso"] = row["ts"]
            row["ts"] = firestore.SERVER_TIMESTAMP
        row["user_id"] = user_id
        DB.collection(table).add(row)

    # 新：匿名保存（user_id を付与しない）
    @staticmethod
    def append_public(table: str, row: dict):
        row = dict(row)
        if "ts" not in row:
            row["ts"] = firestore.SERVER_TIMESTAMP
            row["_ts_iso"] = Storage.now_ts_iso()
        else:
            row["_ts_iso"] = row["ts"]
            row["ts"] = firestore.SERVER_TIMESTAMP
        DB.collection(table).add(row)

    @staticmethod
    def load_user(table: str, user_id: str) -> pd.DataFrame:
        docs = DB.collection(table).where("user_id", "==", user_id).order_by("ts", direction=firestore.Query.DESCENDING).stream()
        rows = []
        for d in docs:
            data = d.to_dict(); data["_id"] = d.id
            ts = data.get("ts")
            data["ts"] = ts.astimezone().isoformat(timespec="seconds") if ts else data.get("_ts_iso")
            rows.append(data)
        return pd.DataFrame(rows)

    @staticmethod
    def load_all(table: str) -> pd.DataFrame:
        docs = DB.collection(table).order_by("ts", direction=firestore.Query.DESCENDING).stream()
        rows = []
        for d in docs:
            data = d.to_dict(); data["_id"] = d.id
            ts = data.get("ts")
            data["ts"] = ts.astimezone().isoformat(timespec="seconds") if ts else data.get("_ts_iso")
            rows.append(data)
        return pd.DataFrame(rows)

    @staticmethod
    def update_doc(table: str, doc_id: str, fields: dict):
        DB.collection(table).document(doc_id).update(fields)

    @staticmethod
    def delete_doc(table: str, doc_id: str):
        DB.collection(table).document(doc_id).delete()

# ================= Utils & Session =================
def now_ts_iso(): return Storage.now_ts_iso()

st.session_state.setdefault("view", "HOME")
st.session_state.setdefault("breath_mode", "gentle")  # 4-0-6 / 5-2-6
st.session_state.setdefault("breath_running", False)
st.session_state.setdefault("note", {"emos": [], "reason": "", "oneword": "", "switch":"", "action":"", "diary":""})
st.session_state.setdefault("_session_stage", "before")
st.session_state.setdefault("_before_score", None)
st.session_state.setdefault("role", None)     # "user" or "admin"
st.session_state.setdefault("user_id", "")
st.session_state.setdefault("_auth_ok", False)

# Study subjects（ローカル管理＋追加可）
DEFAULT_SUBJECTS = ["国語","数学","英語","理科","社会","情報","小論文","面接対策","その他"]
if "subjects" not in st.session_state:
    st.session_state["subjects"] = DEFAULT_SUBJECTS.copy()

def admin_pass() -> str:
    try:
        return st.secrets["ADMIN_PASS"]
    except Exception:
        return "admin123"

# ================= Auth =================
def auth_ui() -> bool:
    if st.session_state._auth_ok:
        return True

    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 🔐 ログイン")
        tab_user, tab_admin = st.tabs(["利用者として入る", "運営として入る"])

        with tab_user:
            st.caption("ユーザーID（例：学校コード＋匿名IDなど）。ご自身の記録だけが表示・保存されます。")
            uid = st.text_input("ユーザーID", placeholder="例: omu-2025-xxxx", key="login_uid")
            if st.button("➡️ 入る（利用者）", type="primary", key="btn_login_user"):
                uid = uid.strip()
                if uid == "":
                    st.warning("ユーザーIDを入力してください。")
                else:
                    st.session_state.user_id = uid
                    st.session_state.role = "user"
                    st.session_state._auth_ok = True
                    st.success(f"ようこそ。ユーザーID: {uid}")
                    return True

        with tab_admin:
            st.caption("運営パスコードを入力してください。全体の集計が閲覧できます。")
            pw = st.text_input("運営パスコード", type="password", key="login_admin_pw")
            if st.button("➡️ 入る（運営）", type="secondary", key="btn_login_admin"):
                if pw == admin_pass():
                    st.session_state.user_id = "_admin_"
                    st.session_state.role = "admin"
                    st.session_state._auth_ok = True
                    st.success("運営ログイン完了。")
                    return True
                else:
                    st.error("パスコードが違います。")

        st.markdown("</div>", unsafe_allow_html=True)
    return False

def logout_btn():
    with st.sidebar:
        if st.button("🚪 ログアウト"):
            for k in ["_auth_ok","role","user_id"]:
                st.session_state[k] = None if k=="role" else ""
            st.rerun()

# ================= Nav =================
def navigate(to_key: str):
    st.session_state.breath_running = False
    st.session_state.view = to_key

def top_nav():
    st.markdown('<div class="topbar">', unsafe_allow_html=True)
    who = "運営" if st.session_state.role=="admin" else f"利用者（{st.session_state.user_id}）"
    st.markdown(f'<div class="nav-hint">ログイン中：{who}</div>', unsafe_allow_html=True)

    pages = [
        ("HOME",   "🏠 ホーム"),
        ("SESSION","🌙 リラックス & レスキュー"),
        ("NOTE",   "📝 心を整える"),
        ("STUDY",  "📚 Study Tracker"),
        ("REVIEW", "📒 ふりかえり"),
        ("ANON",   "🕊️ 相談（匿名）"),     # 新規
        ("EXPORT", "⬇️ 日記・エクスポート"),
    ]
    if st.session_state.role == "admin":
        pages.insert(1, ("DASH", "📊 運営ダッシュボード"))

    st.markdown('<div class="topnav">', unsafe_allow_html=True)
    cols = st.columns(len(pages))
    for i,(key,label) in enumerate(pages):
        cls = "nav-btn active" if st.session_state.view==key else "nav-btn"
        with cols[i]:
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(label, key=f"nav_{key}", use_container_width=True): navigate(key)
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

# ================= Breath helpers =================
def breath_patterns() -> Dict[str, Tuple[int,int,int]]:
    return {"gentle": (4,0,6), "calm": (5,2,6)}

def compute_cycles(target_sec: int, pat: Tuple[int,int,int]) -> int:
    return max(1, round(target_sec / sum(pat)))

def animate_circle(container, phase: str, secs: int):
    anim = {"inhale":"sora-grow", "hold":"sora-steady", "exhale":"sora-shrink"}[phase]
    container.markdown(
        f"<div class='breath-wrap'><div class='breath-circle' style='animation:{anim} {secs}s linear 1 forwards;'></div></div>",
        unsafe_allow_html=True
    )

def run_breath_session(total_sec: int=90):
    inhale, hold, exhale = breath_patterns()[st.session_state.breath_mode]
    cycles = compute_cycles(total_sec, (inhale,hold,exhale))
    st.session_state.breath_running = True
    phase_box = st.empty(); circle_holder = st.empty()
    prog = st.progress(0, text="リラックス中")
    elapsed = 0; total = cycles * (inhale + hold + exhale)
    for _ in range(cycles):
        if not st.session_state.breath_running: break
        phase_box.markdown("<span class='phase-pill'>吸う</span>", unsafe_allow_html=True)
        animate_circle(circle_holder, "inhale", inhale)
        for _ in range(inhale):
            if not st.session_state.breath_running: break
            elapsed += 1; prog.progress(min(int(elapsed/total*100), 100)); time.sleep(1)
        if not st.session_state.breath_running: break
        if hold>0:
            phase_box.markdown("<span class='phase-pill'>とまる</span>", unsafe_allow_html=True)
            animate_circle(circle_holder, "hold", hold)
            for _ in range(hold):
                if not st.session_state.breath_running: break
                elapsed += 1; prog.progress(min(int(elapsed/total*100), 100)); time.sleep(1)
            if not st.session_state.breath_running: break
        phase_box.markdown("<span class='phase-pill'>はく</span>", unsafe_allow_html=True)
        animate_circle(circle_holder, "exhale", exhale)
        for _ in range(exhale):
            if not st.session_state.breath_running: break
            elapsed += 1; prog.progress(min(int(elapsed/total*100), 100)); time.sleep(1)
    st.session_state.breath_running = False

# ================= KPI helpers =================
def last7_kpis_user(user_id: str) -> dict:
    df = Storage.load_user(Storage.MIX, user_id)
    if df.empty: return {"breath":0, "delta_avg":0.0, "actions":0}
    try:
        df["ts"] = pd.to_datetime(df["ts"])
        view = df[df["ts"] >= datetime.now() - timedelta(days=7)]
        breath = view[view["mode"]=="breath"]
        action_col = "action" if "action" in view.columns else ("step" if "step" in view.columns else None)
        actions = view[action_col].astype(str).str.len().gt(0).sum() if action_col else 0
        delta_avg = float(breath["delta"].dropna().astype(float).mean()) if not breath.empty else 0.0
        return {"breath": len(breath), "delta_avg": round(delta_avg,2), "actions": int(actions)}
    except Exception:
        return {"breath":0, "delta_avg":0.0, "actions":0}

def last7_kpis_all() -> dict:
    df = Storage.load_all(Storage.MIX)
    if df.empty: return {"breath":0, "delta_avg":0.0, "actions":0, "users":0}
    try:
        df["ts"] = pd.to_datetime(df["ts"])
        view = df[df["ts"] >= datetime.now() - timedelta(days=7)]
        breath = view[view["mode"]=="breath"]
        action_col = "action" if "action" in view.columns else ("step" if "step" in view.columns else None)
        actions = view[action_col].astype(str).str.len().gt(0).sum() if action_col else 0
        delta_avg = float(breath["delta"].dropna().astype(float).mean()) if not breath.empty else 0.0
        users = df["user_id"].nunique() if "user_id" in df.columns else 0
        return {"breath": len(breath), "delta_avg": round(delta_avg,2), "actions": int(actions), "users": users}
    except Exception:
        return {"breath":0, "delta_avg":0.0, "actions":0, "users":0}

# ================= Views (User) =================
def view_home_user():
    st.markdown("""
<div class="card">
  <h2 style="margin:.2rem 0 1rem 0;">言葉の前に、息をひとつ。</h2>
  <div style="font-weight:900; color:#2767c9; font-size:1.3rem; margin-bottom:.6rem;">短い時間で、少し楽に。</div>
  <div class="form-wrap">
    90秒のリラックス → 気持ちを言葉に → “いまの自分”に合う小さな一歩を見つける。記録は安全に保存されます。
  </div>
</div>
""", unsafe_allow_html=True)

    k = last7_kpis_user(st.session_state.user_id)
    st.markdown('<div class="kpi-grid">', unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    with c1: st.markdown(f'<div class="kpi"><div class="num">{k["breath"]}</div><div class="lab">リラックス回数</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="kpi"><div class="num">{k["delta_avg"]:+.2f}</div><div class="lab">平均Δ（気分）</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="kpi"><div class="num">{k["actions"]}</div><div class="lab">小さな一歩（記録）</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="tile-grid">', unsafe_allow_html=True)
    st.markdown('<div class="tile tile-a">', unsafe_allow_html=True)
    if st.button("🌙 はじめる（リラックス & レスキュー）", key="tile_session"): navigate("SESSION")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

def view_session():
    st.subheader("🌙 リラックス & レスキュー")
    stage = st.session_state._session_stage

    if stage=="before":
        st.caption("ここにいていいよ。90秒だけ、一緒に息を合わせましょう。")
        st.session_state._before_score = st.slider("いまの気分（-3 とてもつらい / +3 とても楽）", -3, 3, -2)
        if st.button("リラックスをはじめる（90秒）", type="primary"):
            st.session_state._session_stage = "breathe"
            run_breath_session(90)
            st.session_state._session_stage = "after"
            return

    if stage=="after":
        st.markdown("#### 終わったあとの感じ")
        after_score = st.slider("いまの気分（-3 とてもつらい / +3 とても楽）", -3, 3, 0, key="after_slider")
        before = int(st.session_state.get("_before_score",-2))
        delta = int(after_score) - before
        st.caption(f"気分の変化：**{delta:+d}**")
        if st.button("💾 リラックスの記録を保存", type="primary"):
            inhale, hold, exhale = breath_patterns()[st.session_state.breath_mode]
            uid = st.session_state.user_id
            Storage.append_user(Storage.BREATH, uid, {
                "ts": now_ts_iso(), "mode": st.session_state.breath_mode,
                "target_sec": 90, "inhale": inhale, "hold": hold, "exhale": exhale,
                "mood_before": before, "mood_after": int(after_score), "delta": delta, "note": ""
            })
            Storage.append_user(Storage.MIX, uid, {
                "ts": now_ts_iso(), "mode":"breath", "mood_before": before, "mood_after": int(after_score), "delta": delta
            })
            st.success("保存しました。次へ。")
            st.session_state._session_stage = "write"
            return

    if stage=="write":
        st.markdown("#### いまの心に、やさしく問いかけます。")
        EMOJI_CHOICES = ["😟不安","😢悲しい","😠いらだち","😳恥ずかしい","😐ぼんやり","🙂安心","😊うれしい"]

        # 抽象度の高い“気分スイッチ”（行動活性化のカテゴリ）
        SWITCHES = [
            "外の空気・光に触れる（環境）",
            "からだを少し動かす（身体活性）",
            "小さな達成をつくる（行動活性）",
            "人と軽くつながる（社会的）",
            "心地よい刺激を足す（ご褒美）",
            "考え方をやわらげる（認知の切替）"
        ]

        st.caption("いまの気持ち（複数OK）")
        st.markdown('<div class="emopills">', unsafe_allow_html=True)
        if "note" not in st.session_state: st.session_state.note = {"emos": [], "reason": "", "oneword": "", "switch":"", "action":"", "diary":""}
        n = st.session_state.note
        cols = st.columns(6)
        for i, label in enumerate(EMOJI_CHOICES):
            with cols[i%6]:
                sel = label in n["emos"]; cls = "on" if sel else ""
                st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
                if st.button(("✓ " if sel else "") + label, key=f"emo_s_{i}"):
                    n["emos"].remove(label) if sel else n["emos"].append(label)
                st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        with st.container():
            st.markdown('<div class="form-wrap">', unsafe_allow_html=True)
            n["reason"]  = st.text_area("どのような出来事や状況がありましたか？（任意）", value=n["reason"])
            n["oneword"] = st.text_area("いまの心を、どんな言葉で表せそうですか？（短くて大丈夫です）", value=n["oneword"])
            n["switch"]  = st.selectbox("いまの自分に合いそうな“気分スイッチ”はどれでしょう？", SWITCHES, index=SWITCHES.index(n["switch"]) if n["switch"] in SWITCHES else 0)
            n["action"]  = st.text_area("それを少し具体化すると、どんな“小さな一歩”になりそうですか？（任意）", value=n["action"], height=80,
                                        help="思いつかなければ空欄でOKです。できると感じる範囲で、やさしく。")
            st.caption("※ やらなきゃいけないことではありません。できそうなときに、できる分だけ。")
            n["diary"]   = st.text_area("日記（頭の整理スペース・自由記入）", value=n["diary"], height=100)
            st.markdown('</div>', unsafe_allow_html=True)

        if st.button("💾 保存して完了", type="primary"):
            uid = st.session_state.user_id
            # 互換：CBTには action=value のまま残す（フィールド名維持）
            Storage.append_user(Storage.CBT, uid, {
                "ts": now_ts_iso(),
                "emotions": json.dumps({"multi": n["emos"]}, ensure_ascii=False),
                "triggers": n["reason"], "reappraise": n["oneword"],
                "action": n["action"], "value": n["switch"]
            })
            # 統合表示用
            Storage.append_user(Storage.MIX, uid, {
                "ts": now_ts_iso(), "mode":"session",
                "emos":" ".join(n["emos"]), "reason": n["reason"], "oneword": n["oneword"],
                "switch": n["switch"], "action": n["action"], "diary": n["diary"]
            })
            st.success("できました。今日はここまでで大丈夫です。")
            st.session_state._session_stage = "before"
            st.session_state._before_score = None
            st.session_state.note = {"emos": [], "reason": "", "oneword": "", "switch":"", "action":"", "diary":""}

def view_note():
    st.subheader("📝 心を整える")
    if "note" not in st.session_state: st.session_state.note = {"emos": [], "reason": "", "oneword": "", "switch":"", "action":"", "diary":""}
    n = st.session_state.note
    EMOJI_CHOICES = ["😟不安","😢悲しい","😠いらだち","😳恥ずかしい","😐ぼんやり","🙂安心","😊うれしい"]
    SWITCHES = [
        "外の空気・光に触れる（環境）",
        "からだを少し動かす（身体活性）",
        "小さな達成をつくる（行動活性）",
        "人と軽くつながる（社会的）",
        "心地よい刺激を足す（ご褒美）",
        "考え方をやわらげる（認知の切替）"
    ]

    st.caption("いまの気持ち（複数OK）")
    st.markdown('<div class="emopills">', unsafe_allow_html=True)
    cols = st.columns(6)
    for i, label in enumerate(EMOJI_CHOICES):
        with cols[i%6]:
            sel = label in n["emos"]; cls = "on" if sel else ""
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(("✓ " if sel else "") + label, key=f"emo_n_{i}"):
                n["emos"].remove(label) if sel else n["emos"].append(label)
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="form-wrap">', unsafe_allow_html=True)
        n["reason"]  = st.text_area("どのような出来事や状況がありましたか？（任意）", value=n["reason"])
        n["oneword"] = st.text_area("いまの心を、どんな言葉で表せそうですか？", value=n["oneword"])
        n["switch"]  = st.selectbox("いまの自分に合いそうな“気分スイッチ”はどれでしょう？", SWITCHES, index=SWITCHES.index(n["switch"]) if n["switch"] in SWITCHES else 0)
        n["action"]  = st.text_area("それを少し具体化すると、どんな“小さな一歩”になりそうですか？（任意）", value=n["action"], height=80)
        st.caption("※ やらされるものではありません。自分のペースで十分です。")
        n["diary"]   = st.text_area("日記（頭の整理スペース・自由記入）", value=n["diary"], height=100)
        st.markdown('</div>', unsafe_allow_html=True)

    if st.button("💾 保存して完了", type="primary"):
        uid = st.session_state.user_id
        Storage.append_user(Storage.CBT, uid, {
            "ts": now_ts_iso(),
            "emotions": json.dumps({"multi": n["emos"]}, ensure_ascii=False),
            "triggers": n["reason"], "reappraise": n["oneword"],
            "action": n["action"], "value": n["switch"]
        })
        Storage.append_user(Storage.MIX, uid, {
            "ts": now_ts_iso(), "mode":"note",
            "emos":" ".join(n["emos"]), "reason": n["reason"], "oneword": n["oneword"],
            "switch": n["switch"], "action": n["action"], "diary": n["diary"]
        })
        st.session_state.note = {"emos": [], "reason":"", "oneword":"", "switch":"", "action":"", "diary":""}
        st.success("保存しました。ここまでで十分です。")

# ============ Study Tracker ============
def _subject_manager_ui():
    with st.expander("📂 科目の管理（追加／編集）", expanded=False):
        st.write("既定：", ", ".join(DEFAULT_SUBJECTS))
        new = st.text_input("科目を追加（例：化学基礎）", key="add_subject")
        if st.button("＋ 追加", key="btn_add_subject"):
            s = new.strip()
            if s and s not in st.session_state["subjects"]:
                st.session_state["subjects"].append(s)
                st.success(f"追加しました：{s}")
        if st.button("↺ 既定に戻す", key="btn_reset_subjects"):
            st.session_state["subjects"] = DEFAULT_SUBJECTS.copy()
            st.success("既定の科目一覧に戻しました。")

def view_study():
    st.subheader("📚 Study Tracker（学習時間の記録）")
    st.caption("時間は手入力。あとで一覧で見返せます。")
    _subject_manager_ui()

    left, right = st.columns(2)
    with left:
        subject = st.selectbox("科目（選択式・自分で追加可）", st.session_state["subjects"])
        minutes = st.number_input("学習時間（分）", min_value=1, max_value=600, value=30, step=5)
    with right:
        mood_choice = st.selectbox("状況を選ぶ", ["順調","難航","しんどい","集中","だるい","眠い","その他"], index=0)
        mood_free = st.text_input("状況を自分の言葉で（空欄可）")
        mood = mood_free.strip() if mood_free.strip() else mood_choice
        note = st.text_input("メモ")

    if st.button("💾 記録", type="primary"):
        uid = st.session_state.user_id
        Storage.append_user(Storage.STUDY, uid, {"ts": now_ts_iso(),"subject":subject.strip(),"minutes":int(minutes),"mood":mood,"memo":note})
        st.success("保存しました。")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 一覧")
    df = Storage.load_user(Storage.STUDY, st.session_state.user_id)
    if df.empty:
        st.caption("まだ記録がありません。")
    else:
        try:
            df["ts"] = pd.to_datetime(df["ts"])
            df = df.sort_values("ts", ascending=False)
            show = df[["ts","subject","minutes","mood","memo"]].rename(
                columns={"ts":"日時","subject":"科目","minutes":"分","mood":"状況","memo":"メモ"})
            st.dataframe(show, use_container_width=True, hide_index=True)

            st.markdown("#### 科目別の割合（分ベース）")
            agg = df.groupby("subject", dropna=False)["minutes"].sum().reset_index().sort_values("minutes", ascending=False)
            total = int(agg["minutes"].sum())
            agg["割合(%)"] = (agg["minutes"] / total * 100).round(1)
            agg = agg.rename(columns={"subject":"科目","minutes":"合計（分）"})
            st.dataframe(agg, use_container_width=True, hide_index=True)
        except Exception:
            st.caption("集計時にエラーが発生しました。")
    st.markdown('</div>', unsafe_allow_html=True)

# ============ ふりかえり ============
def view_review():
    st.subheader("📒 ふりかえり（一覧・編集・削除）")
    tabs = st.tabs(["心の記録（NOTE/SESSION）", "Study Tracker", "リラックス"])
    uid = st.session_state.user_id

    def date_filter_ui(df, prefix: str):
        if df.empty: return df
        df["ts"] = pd.to_datetime(df["ts"])
        today = datetime.now().date()
        c1, c2 = st.columns(2)
        with c1:
            since = st.date_input("開始日", value=today - timedelta(days=14), key=f"{prefix}_since")
        with c2:
            until = st.date_input("終了日", value=today, key=f"{prefix}_until")
        return df[(df["ts"].dt.date >= since) & (df["ts"].dt.date <= until)].copy()

    with tabs[0]:
        df = Storage.load_user(Storage.MIX, uid)
        if df.empty:
            st.caption("まだ記録がありません。")
        else:
            df = date_filter_ui(df, "mix").sort_values("ts", ascending=False)
            # 互換：行動列は action or step
            df["action_disp"] = df["action"] if "action" in df.columns else df.get("step","")
            show_cols = [c for c in ["ts","mode","emos","oneword","action_disp","switch","diary","_id"] if c in df.columns or c=="action_disp"]
            st.markdown("#### 一覧")
            st.dataframe(df[show_cols].rename(columns={
                "ts":"日時","mode":"モード","emos":"感情","oneword":"ことば",
                "action_disp":"小さな一歩","switch":"スイッチ","diary":"日記","_id":"ID"
            }), use_container_width=True, hide_index=True)

            st.markdown("#### 編集 / 削除")
            options = [f'{i+1}. {r["ts"]} | {r.get("mode","")}: {r.get("oneword","")}' for i, r in df.iterrows()]
            if options:
                choice = st.selectbox("編集する記録を選択", options, index=0, key="sel_mix")
                i = int(choice.split(".")[0]) - 1
                row = df.iloc[i]
                new_one = st.text_input("ことば", value=row.get("oneword",""), key="mix_one")
                new_act = st.text_input("小さな一歩", value=row.get("action_disp",""), key="mix_action")
                new_diary = st.text_area("日記", value=row.get("diary",""), height=80, key="mix_diary")
                if st.button("💾 更新する", key="upd_mix"):
                    update_map = {"oneword":new_one, "diary":new_diary}
                    # 両対応：action or step のどちらが存在するかを見て更新
                    if "action" in row.index: update_map["action"] = new_act
                    elif "step" in row.index: update_map["step"] = new_act
                    Storage.update_doc(Storage.MIX, row["_id"], update_map)
                    st.success("更新しました。画面を再読み込みすると反映されます。")
                if st.button("🗑️ この記録を削除", key="del_mix"):
                    Storage.delete_doc(Storage.MIX, row["_id"])
                    st.success("削除しました。画面を再読み込みすると反映されます。")

    with tabs[1]:
        df = Storage.load_user(Storage.STUDY, uid)
        if df.empty:
            st.caption("まだ記録がありません。")
        else:
            df = date_filter_ui(df, "study").sort_values("ts", ascending=False)
            st.markdown("#### 一覧")
            show = df[["ts","subject","minutes","mood","memo","_id"]].rename(
                columns={"ts":"日時","subject":"科目","minutes":"分","mood":"状況","memo":"メモ","_id":"ID"}
            )
            st.dataframe(show, use_container_width=True, hide_index=True)

            st.markdown("#### 合計（科目別）")
            agg = df.groupby("subject", dropna=False)["minutes"].sum().reset_index().sort_values("minutes", ascending=False)
            total = int(agg["minutes"].sum())
            agg["割合(%)"] = (agg["minutes"]/total*100).round(1)
            agg = agg.rename(columns={"subject":"科目","minutes":"合計（分）"})
            st.dataframe(agg, use_container_width=True, hide_index=True)

            st.markdown("#### 編集 / 削除")
            options = [f'{i+1}. {r["ts"]} | {r.get("subject","")} {r.get("minutes",0)}分' for i, r in df.iterrows()]
            if options:
                choice = st.selectbox("編集する記録を選択", options, index=0, key="sel_study")
                i = int(choice.split(".")[0]) - 1
                row = df.iloc[i]
                new_subj = st.text_input("科目", value=row.get("subject",""), key="study_subj")
                new_min  = st.number_input("学習時間（分）", min_value=1, max_value=600, value=int(row.get("minutes",30)), step=5, key="study_min")
                new_mood = st.text_input("状況", value=row.get("mood",""), key="study_mood")
                new_memo = st.text_input("メモ", value=row.get("memo",""), key="study_memo")
                if st.button("💾 更新する", key="upd_study"):
                    Storage.update_doc(Storage.STUDY, row["_id"], {
                        "subject": new_subj.strip(), "minutes": int(new_min),
                        "mood": new_mood.strip(), "memo": new_memo.strip()
                    })
                    st.success("更新しました。画面を再読み込みすると反映されます。")
                if st.button("🗑️ この記録を削除", key="del_study"):
                    Storage.delete_doc(Storage.STUDY, row["_id"])
                    st.success("削除しました。画面を再読み込みすると反映されます。")

    with tabs[2]:
        df = Storage.load_user(Storage.BREATH, uid)
        if df.empty:
            st.caption("まだ記録がありません。")
        else:
            df = date_filter_ui(df, "breath").sort_values("ts", ascending=False)
            cols = [c for c in ["ts","mode","mood_before","mood_after","delta","_id"] if c in df.columns]
            st.dataframe(df[cols].rename(columns={
                "ts":"日時","mode":"モード","mood_before":"前","mood_after":"後","delta":"Δ","_id":"ID"
            }), use_container_width=True, hide_index=True)

# ============ 匿名 相談（学校向け） ============
def view_school_anonymous():
    st.subheader("🕊️ 相談（匿名）")
    st.caption("※ 個人が特定される情報は入力しないでください。内容は学校側への相談窓口に匿名で届きます。")

    # 学校コード推定（ユーザーID先頭の英数記号ブロックを抽出）
    default_org = ""
    if st.session_state.user_id:
        m = re.match(r"^([A-Za-z0-9_\\-]+)", st.session_state.user_id)
        default_org = m.group(1) if m else ""

    with st.container():
        st.markdown('<div class="form-wrap">', unsafe_allow_html=True)
        col1,col2 = st.columns(2)
        with col1:
            mood = st.slider("朝の気分（-3 とてもつらい / +3 とても楽）", -3, 3, 0)
            mood_emoji = st.select_slider("いまに近い表情", options=["😢","😟","😐","🙂","😊"], value="😐")
        with col2:
            sleep = st.number_input("昨夜の睡眠時間（時間）", min_value=0.0, max_value=24.0, value=6.0, step=0.5)
            org = st.text_input("学校コード／クラス（任意・匿名のままでOK）", value=default_org)

        want_talk = st.text_area("いま相談したいこと（匿名）", placeholder="例）朝がつらい・提出物の不安・人間関係… など")
        to_staff  = st.text_area("相談員／先生に伝えたいこと（任意）", placeholder="体調や配慮事項があれば")
        consent   = st.checkbox("上記を学校側に匿名で共有してよいです", value=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if st.button("📮 匿名で送る", type="primary", disabled=not consent):
        row = {
            "ts": now_ts_iso(),
            "org": org.strip(),
            "mood_score": int(mood),
            "mood_emoji": mood_emoji,
            "sleep_hours": float(sleep),
            "message": want_talk.strip(),
            "note": to_staff.strip(),
            "consent": bool(consent)
        }
        # 匿名保存（user_idを付けない）
        Storage.append_public(Storage.SCHOOL, row)
        st.success("送信しました。必要に応じて学校側から全体・学年向けの支援が行われます。")

# ============ Export ============
def export_and_wipe_user():
    uid = st.session_state.user_id
    st.subheader("⬇️ 記録・エクスポート（CSV）")
    for label, table in [
        ("心を整える（互換）", Storage.CBT),
        ("リラックス",         Storage.BREATH),
        ("心を整える（統合）", Storage.MIX),
        ("Study Tracker",     Storage.STUDY),
    ]:
        df = Storage.load_user(table, uid)
        if df.empty:
            st.caption(f"{label}：まだデータがありません")
            continue
        data = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(f"⬇️ {label} を保存（CSV）", data, file_name=f"{uid}_{table}.csv", mime="text/csv", key=f"dl_{uid}_{table}")

# ================= Views (Admin) =================
def view_admin_dash():
    st.subheader("📊 運営ダッシュボード（全体）")

    k = last7_kpis_all()
    st.markdown('<div class="kpi-grid">', unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    with c1: st.markdown(f'<div class="kpi"><div class="num">{k["users"]}</div><div class="lab">利用ユーザー数（累計）</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="kpi"><div class="num">{k["breath"]}</div><div class="lab">直近7日 リラックス回数</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="kpi"><div class="num">{k["delta_avg"]:+.2f}</div><div class="lab">直近7日 平均Δ</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("#### ⏱ 最近の記録（最新50件・モード混在）")
    df = Storage.load_all(Storage.MIX)
    if df.empty:
        st.caption("データなし")
    else:
        try:
            df["ts"] = pd.to_datetime(df["ts"])
            df = df.sort_values("ts", ascending=False).head(50)
            # 行動表示（action/step の互換）
            df["action_disp"] = df["action"] if "action" in df.columns else df.get("step","")
            cols = ["ts","user_id","mode","mood_before","mood_after","delta","emos","action_disp","switch","diary"]
            cols = [c for c in cols if c in df.columns]
            show = df[cols].rename(columns={
                "ts":"日時","user_id":"ユーザーID","mode":"モード","mood_before":"前","mood_after":"後","delta":"Δ",
                "emos":"感情","action_disp":"小さな一歩","switch":"スイッチ","diary":"日記"
            })
            st.dataframe(show, use_container_width=True, hide_index=True)
        except Exception:
            st.warning("一覧表示に失敗しました。")

    st.markdown("#### 😊 感情タグの頻度（上位）")
    emo_counts = {}
    df_note = Storage.load_all(Storage.MIX)
    if not df_note.empty and "emos" in df_note.columns:
        for v in df_note["emos"].dropna().astype(str):
            for tag in v.split():
                emo_counts[tag] = emo_counts.get(tag, 0) + 1
        emo_df = pd.DataFrame(sorted(emo_counts.items(), key=lambda x:-x[1]), columns=["感情タグ","件数"]).head(20)
        st.dataframe(emo_df, use_container_width=True, hide_index=True)
    else:
        st.caption("データなし")

    st.markdown("#### ⬇️ 一括エクスポート（CSV）")
    for label, table in [
        ("心を整える（互換）", Storage.CBT),
        ("リラックス",         Storage.BREATH),
        ("心を整える（統合）", Storage.MIX),
        ("Study Tracker",     Storage.STUDY),
        ("匿名相談（学校向け）",Storage.SCHOOL),
    ]:
        all_df = Storage.load_all(table)
        if all_df.empty:
            st.caption(f"{label}：データなし")
            continue
        data = all_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(f"⬇️ 全ユーザー {label} を保存（CSV）", data, file_name=f"ALL_{table}.csv", mime="text/csv", key=f"dl_all_{table}")

# ================= Router =================
def view_export_router():
    if st.session_state.role == "admin":
        st.info("運営アカウントでは個別消去は行いません。フルエクスポートはダッシュボード下部にあります。")
        st.caption("※ 個別端末の消去は利用者本人の画面から行ってください。")
    else:
        export_and_wipe_user()

def main_router():
    top_nav()
    v = st.session_state.view
    if v=="HOME":
        if st.session_state.role == "admin":
            st.markdown("### ようこそ（運営）\n集計は「📊 運営ダッシュボード」から確認できます。")
        else:
            view_home_user()
    elif v=="DASH" and st.session_state.role=="admin":
        view_admin_dash()
    elif v=="SESSION":
        if st.session_state.role == "admin":
            st.info("運営モードでは個人の記録は行いません。利用者としてログインしてください。")
        else:
            view_session()
    elif v=="NOTE":
        if st.session_state.role == "admin":
            st.info("運営モードでは記入できません。利用者としてログインしてください。")
        else:
            view_note()
    elif v=="STUDY":
        if st.session_state.role == "admin":
            st.info("運営モードでは記録できません。利用者としてログインしてください。")
        else:
            view_study()
    elif v=="REVIEW":
        if st.session_state.role == "admin":
            st.info("運営モードでは個別編集は行いません。利用者としてログインしてください。")
        else:
            view_review()
    elif v=="ANON":
        view_school_anonymous()
    else:
        view_export_router()

# ================= App =================
if auth_ui():
    logout_btn()
    main_router()

# ================= Footer =================
st.markdown("""
<div style="text-align:center; color:#5a6b86; margin-top:12px;">
  <small>※ 個人名や連絡先は記入しないでください。<br>
  とてもつらい場合は、お住まいの地域の相談窓口や専門機関のご利用もご検討ください。</small>
</div>
""", unsafe_allow_html=True)
