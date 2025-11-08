# app.py — Sora / With You.（UI磨き込み版 / 丸アイコン・下線タブ・カードUI）
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple
import pandas as pd
import streamlit as st
import json, time, re

# ==== Firestore ====
from google.cloud import firestore
import google.oauth2.service_account as service_account

# ---------------- Page config ----------------
st.set_page_config(page_title="With You.", page_icon="🌙", layout="centered", initial_sidebar_state="collapsed")

# ---------------- Theme / CSS ----------------
def inject_css():
    st.markdown("""
<style>
:root{
  --bg1:#f3f7ff; --bg2:#eefaff; --panel:#ffffffee; --panel-brd:#e1e9ff;
  --text:#21324b; --muted:#5a6b86; --accent:#76a8ff; --accent-2:#95b9ff;
  --nav-pill:#cfe0ff; --nav-pill2:#b7d1ff; --chip-brd:#d6e7ff;
  --card:#fff; --shadow:0 10px 28px rgba(40,80,160,.08);
}
html, body, .stApp{
  background:
    radial-gradient(1200px 600px at 20% -10%, #ffffff 0%, var(--bg1) 40%, transparent 70%),
    radial-gradient(1000px 520px at 100% 0%,  #ffffff 0%, var(--bg2) 50%, transparent 80%),
    linear-gradient(180deg, var(--bg1), var(--bg2));
}
.block-container{ max-width:980px; padding-top:.6rem; padding-bottom:2rem }
h1,h2,h3{ color:var(--text); letter-spacing:.2px }
small, .subtle{ color:var(--muted) }

.card{ background:var(--panel); border:1px solid var(--panel-brd); border-radius:16px; padding:18px; box-shadow:var(--shadow); }

.grid-2{ display:grid; grid-template-columns:1fr 1fr; gap:16px }
.grid-3{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px }
.grid-4{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px }
@media (max-width: 820px){ .grid-3,.grid-4{ grid-template-columns:1fr 1fr } }
@media (max-width: 520px){ .grid-2,.grid-3,.grid-4{ grid-template-columns:1fr } }

.bigbtn .stButton>button{
  width:100%; padding:18px 16px; border-radius:16px;
  border:1px solid var(--nav-pill2); background:linear-gradient(180deg,var(--nav-pill),var(--nav-pill2));
  color:#14365a; font-weight:900; font-size:1.05rem; box-shadow:0 12px 26px rgba(70,120,200,.16);
}

/* 丸アイコンメニュー */
.circlegrid{ display:grid; grid-template-columns:repeat(3,1fr); gap:18px; margin:6px 0 8px }
@media (min-width:760px){ .circlegrid{ grid-template-columns:repeat(6,1fr) } }
.circlebtn .stButton>button{
  width:76px; height:76px; border-radius:999px; border:1px solid #dfe9ff;
  background: radial-gradient(120% 120% at 30% 20%, #ffffff 0%, #f2f7ff 60%, #e8f1ff 100%);
  box-shadow:0 6px 14px rgba(70,120,200,.16), inset 0 -8px 18px rgba(120,150,200,.12);
  font-size:28px; line-height:1; color:#24466e; padding:0;
}
.circlecap{ margin-top:6px; font-size:.88rem; color:#284265; font-weight:700; text-align:center }

/* 下線タブ（添付UI風） */
.Utabs .stTabs [data-baseweb="tab-list"]{
  gap: 22px; border-bottom: 2px solid #e5eeff; margin-bottom: 6px; padding-bottom: 0;
}
.Utabs .stTabs [data-baseweb="tab"]{
  height: 42px; padding: 0 0 8px 0; font-weight:800; color:#66799a;
}
.Utabs .stTabs [aria-selected="true"]{
  color:#1e3a66; border-bottom: 3px solid var(--accent);
}

/* 呼吸丸（CSSアニメ） */
.breath-wrap{display:flex; justify-content:center; align-items:center; padding:8px 0 4px}
.breath-circle{
  width:230px; height:230px; border-radius:999px;
  background:radial-gradient(circle at 50% 40%, #f7fbff, #e8f2ff 60%, #eef8ff 100%);
  box-shadow:0 16px 32px rgba(90,140,190,.14), inset 0 -10px 25px rgba(120,150,200,.15);
  transform:scale(1); border: solid #dbe9ff;
}
@keyframes sora-grow{ from{ transform:scale(1.0); border-width:10px;} to{ transform:scale(1.6); border-width:14px;} }
@keyframes sora-steady{ from{ transform:scale(1.6); border-width:14px;} to{ transform:scale(1.6); border-width:14px;} }
@keyframes sora-shrink{ from{ transform:scale(1.6); border-width:14px;} to{ transform:scale(1.0); border-width:8px;} }
.phase-pill{display:inline-block; padding:.20rem .7rem; border-radius:999px; background:#edf5ff; color:#2c4b77; border:1px solid #d6e7ff; font-weight:700}

/* ピルボタン（感情） */
.emopills{display:grid; grid-template-columns:repeat(6,1fr); gap:10px}
.emopills .stButton>button{
  background:#ffffff !important; color:#223552 !important;
  border:1.5px solid #d6e7ff !important; border-radius:14px !important;
  box-shadow:none !important; font-weight:700 !important; padding:10px 12px !important;
}
.emopills .on>button{border:2px solid var(--accent) !important; background:#f3f9ff !important}

/* カード */
.item{ background:var(--card); border:1px solid var(--panel-brd); border-radius:16px; padding:14px; box-shadow:var(--shadow) }
.item .meta{ color:var(--muted); font-size:.9rem; margin-bottom:.2rem }
.badge{ display:inline-block; padding:.15rem .6rem; border:1px solid #d6e7ff; border-radius:999px; margin-right:.4rem; color:#29466e; background:#f6faff }

/* 進捗バー */
.prog{height:10px; background:#eef4ff; border-radius:999px; overflow:hidden}
.prog > div{height:10px; background:var(--accent-2)}

/* ボトム・サブナビ（任意表示用クラス） */
.bottombar{
  position:sticky; bottom:0; background:#f7fbffcc; backdrop-filter: blur(6px);
  border:1px solid #e6efff; border-radius:12px; padding:10px 14px; box-shadow:0 6px 20px rgba(30,60,120,.12);
}
</style>
""", unsafe_allow_html=True)

inject_css()

# ---------------- Firestore ----------------
def firestore_client():
    creds = service_account.Credentials.from_service_account_info(st.secrets["FIREBASE_SERVICE_ACCOUNT"])
    return firestore.Client(project=st.secrets["FIREBASE_SERVICE_ACCOUNT"]["project_id"], credentials=creds)
DB = firestore_client()

# ---------------- Storage ----------------
class Storage:
    CBT      = "cbt_entries"
    BREATH   = "breath_sessions"
    MIX      = "mix_note"
    STUDY    = "study_blocks"
    CONSULT  = "consult_msgs"
    SHARED   = "school_share"
    PREFS    = "user_prefs"

    @staticmethod
    def now_iso(): return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    @staticmethod
    def append_user(table:str, user_id:str, row:dict):
        row = dict(row)
        row["_ts_iso"] = row.get("ts", Storage.now_iso())
        row["ts"] = firestore.SERVER_TIMESTAMP
        row["user_id"] = user_id
        DB.collection(table).add(row)

    @staticmethod
    def load_user(table:str, user_id:str) -> pd.DataFrame:
        docs = DB.collection(table).where("user_id","==",user_id).order_by("ts", direction=firestore.Query.DESCENDING).stream()
        rows=[]
        for d in docs:
            data=d.to_dict(); data["_id"]=d.id
            ts=data.get("ts"); data["ts"]=ts.astimezone().isoformat(timespec="seconds") if ts else data.get("_ts_iso")
            rows.append(data)
        return pd.DataFrame(rows)

    @staticmethod
    def get_subjects(uid:str)->List[str]:
        doc = DB.collection(Storage.PREFS).document(uid).get()
        if doc.exists:
            li = doc.to_dict().get("subjects", [])
            return list(dict.fromkeys(li))
        return ["国語","数学","英語","理科","社会","音楽","美術","情報","その他"]

    @staticmethod
    def save_subjects(uid:str, subs:List[str]):
        DB.collection(Storage.PREFS).document(uid).set({"subjects": list(dict.fromkeys(subs))}, merge=True)

# ---------------- Utils/State ----------------
def now_iso() -> str: return Storage.now_iso()
st.session_state.setdefault("_auth_ok", False)
st.session_state.setdefault("role", None)
st.session_state.setdefault("user_id","")
st.session_state.setdefault("view","HOME")
st.session_state.setdefault("_nav_stack", [])
st.session_state.setdefault("breath_mode","calm")   # calm=(5-2-6), gentle=(4-0-6)
st.session_state.setdefault("_breath_running", False)

def admin_pass()->str:
    try: return st.secrets["ADMIN_PASS"]
    except: return "admin123"

CRISIS = [r"死にたい", r"消えたい", r"自殺", r"希死", r"傷つけ(たい|てしまう)", r"リスカ", r"OD", r"助けて"]
def crisis(text:str)->bool:
    if not text: return False
    for p in CRISIS:
        if re.search(p, text): return True
    return False

# ---------------- Auth ----------------
def auth_ui()->bool:
    if st.session_state._auth_ok: return True
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 🔐 ログイン")
        t1,t2 = st.tabs(["利用者として入る","運営として入る"])
        with t1:
            uid = st.text_input("ユーザーID", placeholder="例: omu-2025-xxxx")
            if st.button("➡️ 入る（利用者）", type="primary"):
                if uid.strip()=="":
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
                if pw==admin_pass():
                    st.session_state.user_id="_admin_"; st.session_state.role="admin"; st.session_state._auth_ok=True
                    st.success("運営ログインが完了しました。"); return True
                else:
                    st.error("パスコードが違います。")
        st.markdown("</div>", unsafe_allow_html=True)
    return False

def logout_btn():
    with st.sidebar:
        if st.button("🚪 ログアウト"):
            for k in ["_auth_ok","role","user_id","view","_nav_stack","_breath_running"]:
                if k=="role": st.session_state[k]=None
                elif k=="view": st.session_state[k]="HOME"
                elif k=="_nav_stack": st.session_state[k]=[]
                else: st.session_state[k]=""
            st.rerun()

# ---------------- Nav ----------------
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

def top_nav():
    st.markdown('<div class="card" style="padding:10px 14px">', unsafe_allow_html=True)
    cols = st.columns([1, 3])
    with cols[0]:
        if st.session_state.view != "HOME":
            if st.button("← 戻る", key="nav_back"):
                go_back()
    with cols[1]:
        st.write(
            "ログイン中：",
            "運営" if st.session_state.role == "admin"
            else f"利用者（{st.session_state.user_id}）"
        )
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------- Breathing ----------------
def breath_patterns()->Dict[str,Tuple[int,int,int]]:
    return {"gentle":(4,0,6), "calm":(5,2,6)}

def breathing_animation(total_sec:int=90):
    inhale, hold, exhale = breath_patterns()[st.session_state.breath_mode]
    cycle = inhale+hold+exhale
    cycles = max(1, round(total_sec / cycle))
    ph = st.empty(); spot = st.empty()
    for _ in range(cycles):
        ph.markdown('<span class="phase-pill">吸ってください</span>', unsafe_allow_html=True)
        spot.markdown(f'<div class="breath-wrap"><div class="breath-circle" style="animation:sora-grow {inhale}s linear forwards;"></div></div>', unsafe_allow_html=True)
        time.sleep(inhale)
        if hold>0:
            ph.markdown('<span class="phase-pill">止めてください</span>', unsafe_allow_html=True)
            spot.markdown(f'<div class="breath-wrap"><div class="breath-circle" style="animation:sora-steady {hold}s linear forwards;"></div></div>', unsafe_allow_html=True)
            time.sleep(hold)
        ph.markdown('<span class="phase-pill">吐いてください</span>', unsafe_allow_html=True)
        spot.markdown(f'<div class="breath-wrap"><div class="breath-circle" style="animation:sora-shrink {exhale}s linear forwards;"></div></div>', unsafe_allow_html=True)
        time.sleep(exhale)

# ---------------- Small UI helpers ----------------
def circle_button(emoji:str, label:str, key:str)->bool:
    c = st.container()
    with c:
        st.markdown('<div class="circlebtn">', unsafe_allow_html=True)
        hit = st.button(emoji, key=key)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="circlecap">{label}</div>', unsafe_allow_html=True)
    return hit

def pills(prefix:str, options:List[str], selected:List[str])->List[str]:
    st.markdown('<div class="emopills">', unsafe_allow_html=True)
    cols = st.columns(6)
    for i, label in enumerate(options):
        with cols[i%6]:
            on = label in selected
            cls = "on" if on else ""
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(("✓ " if on else "") + label, key=f"{prefix}_{i}"):
                if on: selected.remove(label)
                else: selected.append(label)
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    return selected

# ---------------- Views ----------------
def view_home():
    top_nav()
    st.markdown("### こんにちは")
    st.caption("やりたいことをお選びください。")
    st.markdown('<div class="circlegrid">', unsafe_allow_html=True)

    cols = st.columns(6) if st.session_state.get("is_wide", True) else st.columns(3)
    items = [
        ("🌙","リラックス","HOME_SESSION","SESSION"),
        ("📝","心を整える","HOME_NOTE","NOTE"),
        ("📚","Study","HOME_STUDY","STUDY"),
        ("🏫","学校共有","HOME_SHARE","SHARE"),
        ("📒","ふりかえり","HOME_REVIEW","REVIEW"),
        ("🕊","相談","HOME_CONSULT","CONSULT"),
    ]
    for i,(emj,cap,k,to) in enumerate(items):
        with cols[i%len(cols)]:
            if circle_button(emj, cap, k):
                navigate(to); st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

def view_session():
    top_nav()
    st.subheader("🌙 リラックス（呼吸）")
    st.caption("ご一緒に、ゆっくり呼吸をしてまいりましょう。")
    if st.button("🫁 はじめる（90秒）", type="primary"):
        st.session_state["_breath_running"]=True; st.rerun()
    if st.session_state.get("_breath_running", False):
        breathing_animation(90)
        st.session_state["_breath_running"]=False
        st.success("お疲れさまでした。ありがとうございます。")

    after = st.slider("いまの気分（-3 とてもつらい / +3 とても楽）", -3, 3, 0)
    if st.button("💾 記録を保存", type="primary"):
        mode = st.session_state.breath_mode
        inh,hold,exh = breath_patterns()[mode]
        Storage.append_user(Storage.BREATH, st.session_state.user_id, {
            "ts": now_iso(), "mode": mode, "target_sec": 90,
            "inhale":inh,"hold":hold,"exhale":exh,
            "mood_before": None, "mood_after": int(after), "delta": None,
            "trigger":"unknown"
        })
        Storage.append_user(Storage.MIX, st.session_state.user_id, {
            "ts": now_iso(), "mode":"breath", "mood_after": int(after),
            "delta": None, "rescue_used": True
        })
        st.success("保存しました。")

def view_note():
    top_nav()
    st.subheader("📝 心を整える")
    st.caption("いまの気持ちをお選びください。（複数可）")
    emos = st.session_state.get("note_emos", [])
    emos = pills("emo", ["😟 不安","😢 悲しい","😠 いらだち","😐 ぼんやり","🙂 安心","😊 うれしい"], emos)
    st.session_state["note_emos"] = emos

    event = st.text_area("その気持ちの背景は、どんな出来事でしたか？（任意）", value=st.session_state.get("note_event",""), height=80)
    st.session_state["note_event"]=event

    words = st.text_area("いまの自分に、どんな言葉をかけたいですか？（例：それでも来られた / 少し休もう）", value=st.session_state.get("note_words",""), height=70)
    st.session_state["note_words"]=words

    switch = st.selectbox("いま合いそうな“スイッチ”をお選びください。", [
        "休息","体を少し動かす","外の空気・光に触れる","音や音楽","誰かと話す","目の前のタスクを終わらせる"
    ], index=0)

    st.markdown('<div class="card" style="background:#fbfdff;border-style:dashed">', unsafe_allow_html=True)
    diary = st.text_area("今日の記録", value=st.session_state.get("note_diary",""),
                         height=140, placeholder="例）朝は重かったけど、昼休みに外へ出たら少し楽になった。")
    st.markdown("</div>", unsafe_allow_html=True)
    st.session_state["note_diary"]=diary

    if st.button("💾 保存", type="primary"):
        uid = st.session_state.user_id
        Storage.append_user(Storage.CBT, uid, {
            "ts": now_iso(),
            "emotions": json.dumps({"multi": emos}, ensure_ascii=False),
            "triggers": event, "reappraise": words, "action":"", "value": switch
        })
        Storage.append_user(Storage.MIX, uid, {
            "ts": now_iso(), "mode":"note", "emos":" ".join(emos), "event":event, "oneword":words,
            "switch": switch, "memo": diary
        })
        st.success("保存しました。")

def view_share():
    top_nav()
    st.subheader("🏫 学校に伝える（匿名）")
    st.caption("本日の“いまの自分”を、匿名で学校に共有します。")

    mood = st.radio("気分", ["🙂","😐","😟"], index=1, horizontal=True)
    body_opts = ["頭痛","腹痛","吐き気","食欲低下","だるさ","生理関連","その他なし"]
    body = st.multiselect("体調（当てはまるもの）", body_opts, default=["その他なし"])
    if "その他なし" in body and len(body)>1:
        body=[b for b in body if b!="その他なし"]

    c1,c2 = st.columns(2)
    with c1: sh = st.number_input("睡眠時間（h）", min_value=0.0, max_value=24.0, value=6.0, step=0.5)
    with c2: sq = st.radio("睡眠の質", ["ぐっすり","ふつう","浅い"], index=1, horizontal=True)

    # カードのプレビュー（コード表示は使わない）
    st.markdown("#### プレビュー")
    st.markdown(f"""
<div class="item">
  <div class="meta">{datetime.now().astimezone().isoformat(timespec="seconds")}</div>
  <div style="font-weight:900; color:#24466e; margin-bottom:.3rem">本日の共有内容</div>
  <div style="margin:.2rem 0;">気分：<span class="badge">{mood}</span></div>
  <div style="margin:.2rem 0;">体調：{"".join([f"<span class='badge'>{b}</span>" for b in (body or ['なし'])])}</div>
  <div style="margin:.2rem 0;">睡眠：<b>{sh:.1f} 時間</b> / 質：<span class="badge">{sq}</span></div>
</div>
""", unsafe_allow_html=True)

    if st.button("📨 匿名で送信", type="primary"):
        preview = {"mood":mood, "body":body, "sleep_hours":float(sh), "sleep_quality":sq}
        Storage.append_user(Storage.SHARED, st.session_state.user_id, {
            "ts": now_iso(), "scope":"本日", "share_flags":{"emotion":True,"body":True,"sleep":True},
            "payload": preview
        })
        st.success("送信しました。ありがとうございます。")

def view_consult():
    top_nav()
    st.subheader("🕊 相談（匿名）")
    msg = st.text_area("いまのお気持ち・状況をお聞かせください。", height=160)
    if crisis(msg):
        st.warning("とても苦しいお気持ちが伝わってきます。必要に応じて、お住まいの地域の相談窓口や専門機関もご検討ください。")

    if st.button("🕊 匿名で送信", type="primary", disabled=(msg.strip()=="")):
        Storage.append_user(Storage.CONSULT, st.session_state.user_id, {"ts": now_iso(), "message": msg.strip()})
        st.success("送信しました。ありがとうございます。")

def view_review():
    top_nav()
    st.subheader("📒 ふりかえり")

    def daterange(df):
        if df.empty: return df
        df["ts"]=pd.to_datetime(df["ts"])
        today=datetime.now().date()
        c1,c2=st.columns(2)
        with c1: since=st.date_input("開始日", value=today - timedelta(days=14))
        with c2: until=st.date_input("終了日", value=today)
        return df[(df["ts"].dt.date>=since)&(df["ts"].dt.date<=until)].copy().sort_values("ts", ascending=False)

    st.markdown('<div class="Utabs">', unsafe_allow_html=True)
    tabs = st.tabs(["ホーム/ノート","呼吸","Study"])
    st.markdown('</div>', unsafe_allow_html=True)

    uid = st.session_state.user_id

    with tabs[0]:
        df = Storage.load_user(Storage.MIX, uid)
        if df.empty: st.caption("まだ記録がありません。")
        else:
            df = daterange(df)
            items=[]
            for _,r in df.iterrows():
                badge = []
                if r.get("mode")=="breath": badge.append("呼吸")
                if r.get("sleep_band"): badge.append(f"睡眠:{r.get('sleep_band')}")
                if r.get("mood_face"): badge.append(f"気分:{r.get('mood_face')}")
                items.append({
                    "ts": r["ts"],
                    "title": r.get("oneword") or r.get("switch") or r.get("mode",""),
                    "memo": r.get("memo",""),
                    "badges": badge
                })
            st.markdown('<div class="grid-2">', unsafe_allow_html=True)
            for it in items:
                st.markdown(f'''
<div class="item">
  <div class="meta">{it["ts"]}</div>
  <div style="font-weight:900; color:#24466e; margin-bottom:.3rem">{it["title"]}</div>
  <div style="white-space:pre-wrap; margin-bottom:.4rem">{it["memo"]}</div>
  <div>{" ".join([f"<span class='badge'>{b}</span>" for b in it["badges"]])}</div>
</div>''', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tabs[1]:
        df = Storage.load_user(Storage.BREATH, uid)
        if df.empty: st.caption("まだ記録がありません。")
        else:
            df = daterange(df)
            st.markdown('<div class="grid-3">', unsafe_allow_html=True)
            for _,r in df.iterrows():
                delta = r.get("delta")
delta = r.get("delta")
dtxt = "" if delta is None else f"<span class='badge'>Δ {int(delta):+d}</span>"
                st.markdown(f"""
<div class="item">
  <div class="meta">{r['ts']}</div>
  <div>モード：<b>{r.get('mode','')}</b> / 目標：{r.get('target_sec',90)}秒</div>
  <div>前後：{r.get('mood_before','-')} → {r.get('mood_after','-')} {dtxt}</div>
</div>
""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tabs[2]:
        df = Storage.load_user(Storage.STUDY, uid)
        if df.empty: st.caption("まだ記録がありません。")
        else:
            df["ts"]=pd.to_datetime(df["ts"])
            df = df.sort_values("ts", ascending=False)
            st.markdown('<div class="grid-2">', unsafe_allow_html=True)
            for _,r in df.iterrows():
                totalmin = int(r.get('minutes',0))
                p = min(100, max(0,int(totalmin)))
                st.markdown(f"""
<div class="item">
  <div class="meta">{r['ts'].isoformat(timespec="seconds")}</div>
  <div style="font-weight:900">{r.get('subject','')}</div>
  <div>分：{totalmin} / 状況：{r.get('mood','')}</div>
  <div class="prog" style="margin-top:.4rem"><div style="width:{min(100, p)}%"></div></div>
  <div style="white-space:pre-wrap; color:#3b4f71; margin-top:.3rem">{r.get('memo','')}</div>
</div>
""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

def view_study():
    top_nav()
    st.subheader("📚 Study")
    uid = st.session_state.user_id
    subjects = Storage.get_subjects(uid)
    l,r = st.columns(2)
    with l:
        subj = st.selectbox("科目", subjects, index=0)
        add = st.text_input("＋ 自分の科目を追加（Enter）")
        if add.strip():
            if add.strip() not in subjects:
                subjects.append(add.strip()); Storage.save_subjects(uid, subjects); st.success(f"追加：{add.strip()}")
    with r:
        mins = st.number_input("学習時間（分）", 1, 600, 30, 5)
        mood = st.selectbox("状況", ["順調","難航","しんどい","集中","だるい","眠い","その他"], index=0)
    memo = st.text_input("メモ（任意）")
    if st.button("💾 記録", type="primary"):
        Storage.append_user(Storage.STUDY, uid, {"ts":now_iso(),"subject":(add.strip() or subj),"minutes":int(mins),"mood":mood,"memo":memo})
        st.success("保存しました。")

    df = Storage.load_user(Storage.STUDY, uid)
    if not df.empty:
        agg = df.groupby("subject")["minutes"].sum().reset_index().sort_values("minutes", ascending=False)
        total = max(1, int(agg["minutes"].sum()))
        st.markdown("#### 科目別の合計")
        st.markdown('<div class="grid-2">', unsafe_allow_html=True)
        for _,r in agg.iterrows():
            p = round(r["minutes"]/total*100,1)
            st.markdown(f"""
<div class="item">
  <div style="font-weight:900">{r['subject']}</div>
  <div class="meta">合計：{int(r['minutes'])} 分</div>
  <div class="prog"><div style="width:{p}%"></div></div>
  <div class="meta">{p}%</div>
</div>
""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Router ----------------
def main_router():
    v = st.session_state.view
    if v=="HOME":     view_home()
    elif v=="SESSION":view_session()
    elif v=="NOTE":   view_note()
    elif v=="SHARE":  view_share()
    elif v=="CONSULT":view_consult()
    elif v=="REVIEW": view_review()
    elif v=="STUDY":  view_study()
    else:             view_home()

# ---------------- App ----------------
if auth_ui():
    logout_btn()
    main_router()

# ---------------- Footer ----------------
st.markdown("""
<div style="text-align:center; color:#5a6b86; margin-top:12px;">
  <small>※ とてもつらい場合は、お住まいの地域の相談窓口や専門機関のご利用もご検討ください。<br>
  通知は夜間に鳴らないよう配慮しています。</small>
</div>
""", unsafe_allow_html=True)
