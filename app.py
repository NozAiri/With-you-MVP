# app.py — Sora / With You. （全面改訂：UI分離・優しい問いかけ・StudyTracker拡張・匿名相談）
from __future__ import annotations
from datetime import datetime, timedelta, timezone, date
from typing import Dict, Tuple, List, Optional
import pandas as pd
import streamlit as st
import json, time

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
<link href="https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700&display=swap" rel="stylesheet">
<style>
:root{
  /* 若者向けパレット（やさしいネオン） */
  --ink:#182033; --muted:#6f7b95;
  --bg1:#f9fbff; --bg2:#f3f6ff;
  --panel:#ffffffee; --panel-brd:#e6ecff;
  --pill-from:#d7e4ff; --pill-to:#bcd2ff;         /* ナビの光 */
  --cta-from:#c9f0ff; --cta-to:#d6e7ff;           /* CTAのやわらか光 */
  --chip-brd:#d6e7ff; --chip-on:#7aa7ff; --chip-on-bg:#eef4ff;

  /* アクセント（星/惑星） */
  --glow:#87b3ff; --planet:#dff2ff; --planet-deep:#cbe6ff;

  /* “SNS感”の小物 */
  --badge:#ffd8e6; --badge-txt:#5a2342;
}

html, body, .stApp{ font-family: "Zen Maru Gothic", ui-sans-serif, system-ui; }
h1,h2,h3{ color:var(--ink); letter-spacing:.2px }
.block-container{ max-width:980px; padding-top:.4rem; padding-bottom:2rem }

/* ===== HERO（ホーム上部のキャッチ） ===== */
.hero{
  position:relative; border-radius:20px; padding:18px 18px 22px;
  background: radial-gradient(140% 120% at 10% 0%, #ffffff 0%, var(--bg2) 55%, transparent 70%),
             linear-gradient(180deg, var(--bg1), var(--bg2));
  border:1px solid var(--panel-brd);
  box-shadow:0 20px 40px rgba(40,80,160,.10), inset 0 0 80px rgba(135,179,255,.16);
  overflow:hidden;
}
.hero::after{
  content:""; position:absolute; inset:-20% -20% auto auto; width:180px; height:180px; border-radius:50%;
  background: radial-gradient(circle at 40% 35%, #fff 0%, var(--planet) 60%, var(--planet-deep) 100%);
  box-shadow:0 0 28px rgba(135,179,255,.35), 0 0 14px rgba(135,179,255,.25) inset;
  filter: blur(.3px); opacity:.85; animation: floaty 6s ease-in-out infinite;
}
@keyframes floaty{ 0%{ transform:translateY(0)} 50%{ transform:translateY(-6px)} 100%{ transform:translateY(0)} }

/* ===== ナビ（ui-nav）：ぷにっとしたピル ===== */
.ui-nav .topbar{ position:sticky; top:0; z-index:10; background:#fffffff8; backdrop-filter:blur(8px);
  border-bottom:1px solid var(--panel-brd); margin:0 -12px 8px; padding:8px 12px 12px }
.ui-nav .topnav{ display:flex; gap:10px; flex-wrap:wrap; }
.ui-nav .nav-btn>button{
  background:linear-gradient(180deg,var(--pill-from),var(--pill-to)) !important;
  color:#18365d !important; border:1px solid var(--panel-brd) !important;
  padding:12px 16px !important; border-radius:999px !important; font-weight:800 !important;
  box-shadow:0 8px 20px rgba(30,80,160,.12) !important;
}
.ui-nav .active>button{ outline:3px solid var(--chip-on) !important; outline-offset:0 }

/* ===== 入力（ui-form）：カード＆チップ ===== */
.card{
  background:var(--panel); border:1px solid var(--panel-brd);
  border-radius:18px; padding:18px; margin-bottom:14px;
  box-shadow:0 10px 26px rgba(40,80,160,.08)
}
.ui-form .hint{ color:var(--muted); font-size:.92rem; margin:.1rem 0 .6rem }

.ui-form .chip-grid{ display:grid; grid-template-columns:repeat(6,1fr); gap:8px }
@media (max-width: 680px){ .ui-form .chip-grid{ grid-template-columns:repeat(4,1fr) } }
.ui-form .stButton>button{
  background:#fff !important; color:#1f3352 !important;
  border:1.5px solid var(--chip-brd) !important; border-radius:14px !important;
  font-weight:800 !important; padding:10px 12px !important;
}
.ui-form .on>button{ border:2px solid var(--chip-on) !important; background:var(--chip-on-bg) !important }

/* ===== CTAボタン（保存など） ===== */
.stButton>button,.stDownloadButton>button{
  width:100%; padding:12px 16px; border-radius:16px; border:1px solid var(--chip-brd);
  background:linear-gradient(180deg,var(--cta-from),var(--cta-to)); color:#163455; font-weight:900; font-size:1.02rem;
  box-shadow:0 14px 30px rgba(90,150,240,.16)
}

/* ===== 惑星バッジ ===== */
.planet{
  display:inline-block; border-radius:999px;


inject_css()

# ================= Firestore =================
def firestore_client():
    creds = service_account.Credentials.from_service_account_info(st.secrets["FIREBASE_SERVICE_ACCOUNT"])
    return firestore.Client(project=st.secrets["FIREBASE_SERVICE_ACCOUNT"]["project_id"], credentials=creds)

DB = firestore_client()

class Storage:
    CBT      = "cbt_entries"
    BREATH   = "breath_sessions"
    MIX      = "mix_note"
    STUDY    = "study_blocks"
    CONSULT  = "consult_msgs"
    PREFS    = "user_prefs"   # {user_id, subjects:[...]}
    @staticmethod
    def now_ts_iso():
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
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
    @staticmethod
    def load_user(table: str, user_id: str) -> pd.DataFrame:
        docs = DB.collection(table).where("user_id","==",user_id).order_by("ts", direction=firestore.Query.DESCENDING).stream()
        rows=[]
        for d in docs:
            data=d.to_dict(); data["_id"]=d.id
            ts=data.get("ts"); data["ts"]=ts.astimezone().isoformat(timespec="seconds") if ts else data.get("_ts_iso")
            rows.append(data)
        return pd.DataFrame(rows)
    @staticmethod
    def load_all(table: str) -> pd.DataFrame:
        docs = DB.collection(table).order_by("ts", direction=firestore.Query.DESCENDING).stream()
        rows=[]
        for d in docs:
            data=d.to_dict(); data["_id"]=d.id
            ts=data.get("ts"); data["ts"]=ts.astimezone().isoformat(timespec="seconds") if ts else data.get("_ts_iso")
            rows.append(data)
        return pd.DataFrame(rows)
    @staticmethod
    def update_doc(table: str, doc_id: str, fields: dict):
        DB.collection(table).document(doc_id).update(fields)
    @staticmethod
    def delete_doc(table: str, doc_id: str):
        DB.collection(table).document(doc_id).delete()
    # ---- preferences ----
    @staticmethod
    def get_subjects(user_id: str) -> List[str]:
        doc = DB.collection(Storage.PREFS).document(user_id).get()
        if doc.exists:
            d = doc.to_dict()
            return list(dict.fromkeys(d.get("subjects", [])))
        return ["国語","数学","英語","理科","社会","音楽","美術","情報","その他"]
    @staticmethod
    def save_subjects(user_id: str, subs: List[str]):
        DB.collection(Storage.PREFS).document(user_id).set({"subjects": list(dict.fromkeys(subs))}, merge=True)

# ================= Utils/State =================
def now_ts_iso(): return Storage.now_ts_iso()
st.session_state.setdefault("_auth_ok", False)
st.session_state.setdefault("role", None)          # "user" / "admin"
st.session_state.setdefault("user_id", "")
st.session_state.setdefault("view", "HOME")
st.session_state.setdefault("_session_stage", "before")
st.session_state.setdefault("_before_score", None)
st.session_state.setdefault("breath_mode", "gentle")
# NOTEオブジェクト（キー欠落で落ちないよう網羅）
st.session_state.setdefault("note", {
    "emos": [], "event":"", "words":"", "switch":"", "action":"", "memo":""
})

def admin_pass() -> str:
    try:    return st.secrets["ADMIN_PASS"]
    except: return "admin123"

# ================= Auth =================
def auth_ui() -> bool:
    if st.session_state._auth_ok: return True
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 🔐 ログイン")
        tab_user, tab_admin = st.tabs(["利用者として入る", "運営として入る"])
        with tab_user:
            st.caption("ユーザーID（例：学校コード＋匿名IDなど）。ご自身の記録だけが表示・保存されます。")
            uid = st.text_input("ユーザーID", placeholder="例: omu-2025-xxxx", key="login_uid")
            if st.button("➡️ 入る（利用者）", type="primary"):
                uid = uid.strip()
                if uid == "": st.warning("ユーザーIDを入力してください。")
                else:
                    st.session_state.user_id = uid
                    st.session_state.role = "user"
                    st.session_state._auth_ok = True
                    st.success(f"ようこそ。ユーザーID: {uid}")
                    return True
        with tab_admin:
            pw = st.text_input("運営パスコード", type="password", key="login_admin_pw")
            if st.button("➡️ 入る（運営）", type="secondary"):
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
                st.session_state[k] = (None if k=="role" else "")
            st.rerun()

# ================= Nav =================
def navigate(to_key: str):
    st.session_state.view = to_key

def top_nav():
    st.markdown('<div class="ui-nav">', unsafe_allow_html=True)
    st.markdown('<div class="topbar">', unsafe_allow_html=True)
    who = "運営" if st.session_state.role=="admin" else f"利用者（{st.session_state.user_id}）"
    st.markdown(f'<div style="font-size:.82rem;color:#6d7fa2">ログイン中：{who}</div>', unsafe_allow_html=True)
    pages = [
        ("HOME",   "🏠 ホーム"),
        ("SESSION","🌙 リラックス & レスキュー"),
        ("NOTE",   "📝 心を整える"),
        ("STUDY",  "📚 Study Tracker"),
        ("REVIEW", "📒 ふりかえり"),
        ("CONSULT","🕊 相談（匿名）"),
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
    st.markdown('</div>', unsafe_allow_html=True)  # .ui-nav

# ================= Helpers =================
def last7_kpis_user(user_id: str) -> dict:
    df = Storage.load_user(Storage.MIX, user_id)
    if df.empty: return {"breath":0, "delta_avg":0.0, "steps":0}
    try:
        df["ts"] = pd.to_datetime(df["ts"])
        view = df[df["ts"] >= datetime.now() - timedelta(days=7)]
        breath = view[view["mode"]=="breath"]
        steps  = view[(view.get("action", pd.Series(dtype=str)).astype(str) != "")]
        delta_avg = float(breath["delta"].dropna().astype(float).mean()) if not breath.empty else 0.0
        return {"breath": len(breath), "delta_avg": round(delta_avg,2), "steps": len(steps)}
    except:
        return {"breath":0, "delta_avg":0.0, "steps":0}

def breath_patterns() -> Dict[str, Tuple[int,int,int]]:
    return {"gentle": (4,0,6), "calm": (5,2,6)}

def run_breath_session(total_sec: int=90):
    inhale, hold, exhale = breath_patterns()[st.session_state.breath_mode]
    cycles = max(1, round(total_sec / (inhale+hold+exhale)))
    st.session_state._session_stage = "breathe"
    prog = st.progress(0, text="リラックス中…")
    elapsed = 0; total = cycles * (inhale+hold+exhale)
    for _ in range(cycles):
        for secs in [("吸う", inhale), ("とまる", hold), ("はく", exhale)]:
            if secs[1]==0: continue
            st.markdown(f"**{secs[0]}**（{secs[1]}）")
            for _ in range(secs[1]):
                elapsed += 1; prog.progress(min(int(elapsed/total*100), 100)); time.sleep(1)
    st.session_state._session_stage = "after"

# ================= Views =================
def view_home_user():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 言葉の前に、息をひとつ。")
    st.caption("短い時間で、少し楽に。")
    st.markdown('</div>', unsafe_allow_html=True)
    k = last7_kpis_user(st.session_state.user_id)
    st.markdown('<div class="kpi-grid">', unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    with c1: st.markdown(f'<div class="kpi"><div class="num">{k["breath"]}</div><div class="lab">リラックス回数（7日）</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="kpi"><div class="num">{k["delta_avg"]:+.2f}</div><div class="lab">平均Δ（気分）</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="kpi"><div class="num">{k["steps"]}</div><div class="lab">小さな行動の記録</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def view_session():
    st.subheader("🌙 リラックス & レスキュー")
    stage = st.session_state._session_stage
    if stage=="before":
        st.caption("ここにいていいよ。90秒だけ、一緒に息。")
        st.session_state._before_score = st.slider("いまの気分（-3 とてもつらい / +3 とても楽）", -3, 3, -2)
        if st.button("リラックスをはじめる（90秒）", type="primary"):
            run_breath_session(90)
            st.experimental_rerun()
    if stage=="after":
        st.markdown("#### 終わったあとの感じ")
        after_score = st.slider("いまの気分（-3 とてもつらい / +3 とても楽）", -3, 3, 0, key="after_slider")
        before = int(st.session_state.get("_before_score",-2))
        delta = int(after_score) - before
        st.caption(f"気分の変化：**{delta:+d}**")
        if st.button("💾 記録を保存", type="primary"):
            inhale, hold, exhale = breath_patterns()[st.session_state.breath_mode]
            uid = st.session_state.user_id
            Storage.append_user(Storage.BREATH, uid, {
                "ts": now_ts_iso(), "mode": st.session_state.breath_mode,
                "target_sec": 90, "inhale": inhale, "hold": hold, "exhale": exhale,
                "mood_before": before, "mood_after": int(after_score), "delta": delta
            })
            Storage.append_user(Storage.MIX, uid, {
                "ts": now_ts_iso(), "mode":"breath", "mood_before": before, "mood_after": int(after_score), "delta": delta
            })
            st.success("保存しました。")
            st.session_state._session_stage = "before"
            st.session_state._before_score = None

def _emoji_pills(key_prefix: str, options: List[str], selected: List[str]) -> List[str]:
    st.markdown('<div class="ui-form">', unsafe_allow_html=True)
    st.markdown('<div class="chip-grid">', unsafe_allow_html=True)
    cols = st.columns(6)
    for i, label in enumerate(options):
        with cols[i%6]:
            sel = label in selected
            cls = "on" if sel else ""
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(("✓ " if sel else "") + label, key=f"{key_prefix}_{i}"):
                if sel: selected.remove(label)
                else:   selected.append(label)
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)
    return selected

def view_note():
    st.markdown('<div class="ui-form">', unsafe_allow_html=True)
    st.subheader("📝 心を整える")
    n = st.session_state.note
    EMOJI_CHOICES = ["😟 不安","😢 悲しい","😠 いらだち","😳 恥ずかしい","😐 ぼんやり","🙂 安心","😊 うれしい"]
    st.caption("いまの気持ち（複数OK）")
    n["emos"] = _emoji_pills("emo", EMOJI_CHOICES, n.get("emos",[]))

    st.markdown('<div class="hint">むずかしく考えなくて大丈夫です。思いついたことを一言で。</div>', unsafe_allow_html=True)
    n["event"] = st.text_area("今日いちばん印象に残ったことは？（任意）", value=n.get("event",""))
    n["words"] = st.text_area("いまの心を、どんな言葉で表せそうですか？", value=n.get("words",""))

    SWITCHES = [
        "外の空気・光に触れる（環境）", "体を少し動かす（からだ）", "安心できる音・音楽（感覚）",
        "ごろごろ休む（休息）", "だれかと少し話す（つながり）", "小さな達成感（やり切る）"
    ]
    n["switch"] = st.selectbox("いまの自分に合いそうな“気分スイッチ”はどれでしょう？", SWITCHES,
                               index=SWITCHES.index(n.get("switch", SWITCHES[0])) if n.get("switch") in SWITCHES else 0)

    n["action"] = st.text_area("それを少し具体化すると、どんな“小さな一歩”になりそうですか？（任意）", value=n.get("action",""), height=80)
    st.caption("※ やらされるものではありません。自分のペースで十分です。")

    n["memo"] = st.text_area("日記（頭の整理スペース・自由記入）", value=n.get("memo",""), height=120)

    if st.button("💾 保存して完了", type="primary"):
        uid = st.session_state.user_id
        Storage.append_user(Storage.CBT, uid, {
            "ts": now_ts_iso(),
            "emotions": json.dumps({"multi": n.get("emos",[])}, ensure_ascii=False),
            "triggers": n.get("event",""), "reappraise": n.get("words",""),
            "action": n.get("action",""), "value": n.get("switch","")
        })
        Storage.append_user(Storage.MIX, uid, {
            "ts": now_ts_iso(), "mode":"note",
            "emos":" ".join(n.get("emos",[])), "event": n.get("event",""),
            "oneword": n.get("words",""), "action": n.get("action",""),
            "switch": n.get("switch",""), "memo": n.get("memo","")
        })
        st.success("保存しました。ここまでで十分です。")
        st.session_state.note = {"emos": [], "event":"", "words":"", "switch":"", "action":"", "memo":""}
    st.markdown('</div>', unsafe_allow_html=True)

def view_study():
    st.subheader("📚 Study Tracker（学習時間の記録）")
    st.caption("科目は**選択式＋自分で追加**。一覧は科目別の合計と**パーセンテージ**を表示します。")
    uid = st.session_state.user_id
    subjects = Storage.get_subjects(uid)
    col_left, col_right = st.columns(2)
    with col_left:
        subj = st.selectbox("科目を選ぶ", subjects, index=0, key="study_subj_sel")
        new_subj = st.text_input("＋ 自分の科目を追加（Enterで追加）", key="study_add_subj")
        if new_subj.strip():
            if new_subj.strip() not in subjects:
                subjects.append(new_subj.strip())
                Storage.save_subjects(uid, subjects)
                st.success(f"科目を追加しました：{new_subj.strip()}")
    with col_right:
        minutes = st.number_input("学習時間（分）", min_value=1, max_value=600, value=30, step=5)
        mood_choice = st.selectbox("状況を選ぶ", ["順調","難航","しんどい","集中","だるい","眠い","その他"], index=0)
        mood_free = st.text_input("状況を自分の言葉で（空欄可）")
        mood = mood_free.strip() if mood_free.strip() else mood_choice
    note = st.text_input("メモ（任意）")

    if st.button("💾 記録", type="primary"):
        Storage.append_user(Storage.STUDY, uid, {
            "ts": now_ts_iso(), "subject": (new_subj.strip() or subj), "minutes": int(minutes),
            "mood": mood, "memo": note
        })
        st.success("保存しました。")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 一覧・集計")
    df = Storage.load_user(Storage.STUDY, uid)
    if df.empty:
        st.caption("まだ記録がありません。")
    else:
        df["ts"] = pd.to_datetime(df["ts"])
        df = df.sort_values("ts", ascending=False)
        show = df[["ts","subject","minutes","mood","memo"]].rename(
            columns={"ts":"日時","subject":"科目","minutes":"分","mood":"状況","memo":"メモ"})
        st.dataframe(show, use_container_width=True, hide_index=True)
        # 集計（％）
        agg = df.groupby("subject", dropna=False)["minutes"].sum().reset_index().sort_values("minutes", ascending=False)
        total = agg["minutes"].sum()
        agg["割合(%)"] = (agg["minutes"]/total*100).round(1)
        agg = agg.rename(columns={"subject":"科目","minutes":"合計（分）"})
        st.markdown("##### 科目別の割合")
        st.dataframe(agg, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

def view_review():
    st.subheader("📒 ふりかえり")
    uid = st.session_state.user_id
    def date_filter_ui(df, prefix:str):
        if df.empty: return df
        df["ts"] = pd.to_datetime(df["ts"])
        today = datetime.now().date()
        c1, c2 = st.columns(2)
        with c1: since = st.date_input("開始日", value=today - timedelta(days=14), key=f"{prefix}_since")
        with c2: until = st.date_input("終了日", value=today, key=f"{prefix}_until")
        return df[(df["ts"].dt.date >= since) & (df["ts"].dt.date <= until)].copy()

    tabs = st.tabs(["心の記録（NOTE/SESSION）", "Study Tracker", "リラックス"])
    with tabs[0]:
        df = Storage.load_user(Storage.MIX, uid)
        if df.empty: st.caption("まだ記録がありません。")
        else:
            df = date_filter_ui(df, "mix").sort_values("ts", ascending=False)
            cols = [c for c in ["ts","mode","emos","event","oneword","action","switch","memo","_id"] if c in df.columns]
            st.dataframe(df[cols].rename(columns={
                "ts":"日時","mode":"モード","emos":"感情","event":"できごと","oneword":"ことば",
                "action":"小さな一歩","switch":"スイッチ","memo":"メモ","_id":"ID"
            }), use_container_width=True, hide_index=True)

    with tabs[1]:
        df = Storage.load_user(Storage.STUDY, uid)
        if df.empty: st.caption("まだ記録がありません。")
        else:
            df = date_filter_ui(df, "study").sort_values("ts", ascending=False)
            show = df[["ts","subject","minutes","mood","memo","_id"]].rename(
                columns={"ts":"日時","subject":"科目","minutes":"分","mood":"状況","memo":"メモ","_id":"ID"})
            st.dataframe(show, use_container_width=True, hide_index=True)

            agg = df.groupby("subject", dropna=False)["minutes"].sum().reset_index().sort_values("minutes", ascending=False)
            total = max(1, agg["minutes"].sum())
            agg["割合(%)"] = (agg["minutes"]/total*100).round(1)
            agg = agg.rename(columns={"subject":"科目","minutes":"合計（分）"})
            st.markdown("##### 科目別の割合")
            st.dataframe(agg, use_container_width=True, hide_index=True)

    with tabs[2]:
        df = Storage.load_user(Storage.BREATH, uid)
        if df.empty: st.caption("まだ記録がありません。")
        else:
            df = date_filter_ui(df, "breath").sort_values("ts", ascending=False)
            cols = [c for c in ["ts","mode","mood_before","mood_after","delta","_id"] if c in df.columns]
            st.dataframe(df[cols].rename(columns={
                "ts":"日時","mode":"モード","mood_before":"前","mood_after":"後","delta":"Δ","_id":"ID"
            }), use_container_width=True, hide_index=True)

def view_consult():
    st.subheader("🕊 相談（匿名）")
    st.caption("このメッセージは**匿名**で相談員に届きます。個人名・連絡先は書かないでください。")
    uid = st.session_state.user_id
    col1,col2 = st.columns(2)
    with col1:
        morning_mood = st.slider("朝の気分（-3 とてもつらい / +3 とても楽）", -3, 3, 0)
        sleep_hours  = st.number_input("昨日の睡眠時間（h）", min_value=0.0, max_value=24.0, value=6.0, step=0.5)
    with col2:
        want_contact = st.selectbox("相談員に伝えたいことの優先度", ["急ぎではない","できれば早めに","なるべく急ぎで"], index=1)
        nickname     = st.text_input("匿名ニックネーム（任意）", placeholder="例）月のひと")
    msg = st.text_area("相談したいこと（自由記入）", height=140)
    extra = st.text_area("他に伝えておきたいこと（任意）", height=80)
    if st.button("🕊 匿名で送信", type="primary", disabled=(msg.strip()=="")):
        Storage.append_user(Storage.CONSULT, uid, {
            "ts": now_ts_iso(),
            "morning_mood": int(morning_mood),
            "sleep_hours": float(sleep_hours),
            "priority": want_contact,
            "nickname": nickname.strip(),
            "message": msg.strip(),
            "extra": extra.strip()
        })
        st.success("送信しました。あなたの気持ちはここに届きました。必要に応じて相談員から全体向けの案内が行われます。")

def export_and_wipe_user():
    uid = st.session_state.user_id
    st.subheader("⬇️ 記録・エクスポート（CSV）")
    for label, table in [
        ("心を整える（互換）", Storage.CBT),
        ("リラックス",         Storage.BREATH),
        ("心を整える（統合）", Storage.MIX),
        ("Study Tracker",     Storage.STUDY),
        ("匿名相談",           Storage.CONSULT),
    ]:
        df = Storage.load_user(table, uid)
        if df.empty:
            st.caption(f"{label}：まだデータがありません")
            continue
        data = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(f"⬇️ {label} を保存（CSV）", data, file_name=f"{uid}_{table}.csv", mime="text/csv", key=f"dl_{uid}_{table}")

def view_admin_dash():
    st.subheader("📊 運営ダッシュボード（全体）")
    # 直近の匿名相談 概要
    st.markdown("#### 匿名相談（直近50件）")
    dfc = Storage.load_all(Storage.CONSULT)
    if dfc.empty:
        st.caption("データなし")
    else:
        dfc["ts"] = pd.to_datetime(dfc["ts"])
        dfc = dfc.sort_values("ts", ascending=False).head(50)
        cols = [c for c in ["ts","user_id","nickname","priority","morning_mood","sleep_hours","message"] if c in dfc.columns]
        st.dataframe(dfc[cols].rename(columns={
            "ts":"日時","user_id":"ユーザーID","nickname":"匿名名","priority":"優先度",
            "morning_mood":"朝の気分","sleep_hours":"睡眠(h)","message":"相談内容"
        }), use_container_width=True, hide_index=True)

    # 利用概況
    st.markdown("#### 最近の『心を整える』記録（最新50件・モード混在）")
    df = Storage.load_all(Storage.MIX)
    if df.empty:
        st.caption("データなし")
    else:
        df["ts"] = pd.to_datetime(df["ts"])
        show = df.sort_values("ts", ascending=False).head(50)
        cols = [c for c in ["ts","user_id","mode","emos","event","oneword","action","switch"] if c in show.columns]
        st.dataframe(show[cols].rename(columns={
            "ts":"日時","user_id":"ユーザーID","mode":"モード","emos":"感情","event":"できごと",
            "oneword":"ことば","action":"小さな一歩","switch":"スイッチ"
        }), use_container_width=True, hide_index=True)

    # 一括DL
    st.markdown("#### ⬇️ 全体エクスポート（CSV）")
    for label, table in [
        ("心を整える（互換）", Storage.CBT),
        ("リラックス",         Storage.BREATH),
        ("心を整える（統合）", Storage.MIX),
        ("Study Tracker",     Storage.STUDY),
        ("匿名相談",           Storage.CONSULT),
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
    else:
        export_and_wipe_user()

def main_router():
    # ナビ（ナビ領域とフォーム領域の見た目を分離）
    top_nav()
    st.markdown('<div class="ui-form">', unsafe_allow_html=True)
    v = st.session_state.view
    if v=="HOME":
        (st.markdown("### ようこそ（運営）\n集計は「📊 運営ダッシュボード」から確認できます。") if st.session_state.role=="admin"
         else view_home_user())
    elif v=="DASH" and st.session_state.role=="admin":
        view_admin_dash()
    elif v=="SESSION":
        (st.info("運営モードでは個人の記録は行いません。利用者としてログインしてください。")
         if st.session_state.role=="admin" else view_session())
    elif v=="NOTE":
        (st.info("運営モードでは記入できません。利用者としてログインしてください。")
         if st.session_state.role=="admin" else view_note())
    elif v=="STUDY":
        (st.info("運営モードでは記録できません。利用者としてログインしてください。")
         if st.session_state.role=="admin" else view_study())
    elif v=="REVIEW":
        (st.info("運営モードでは個別編集は行いません。利用者としてログインしてください。")
         if st.session_state.role=="admin" else view_review())
    elif v=="CONSULT":
        (st.info("運営モードでは個人の送信は行いません。利用者としてログインしてください。")
         if st.session_state.role=="admin" else view_consult())
    else:
        view_export_router()
    st.markdown('</div>', unsafe_allow_html=True)

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
