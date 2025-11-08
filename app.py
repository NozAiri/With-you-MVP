# app.py — Sora / With You.（生徒向け体験：1分ルーチン / からだシグナル / 自分主権共有 / AI寄り添い10スタイル）
from __future__ import annotations
from datetime import datetime, timedelta, timezone, date
from typing import Dict, Tuple, List, Optional
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
    st.markdown("""
<style>
:root{
  --bg1:#f3f7ff; --bg2:#eefaff;
  --panel:#ffffffee; --panel-brd:#e1e9ff;
  --text:#21324b; --muted:#5a6b86; --outline:#76a8ff;
  --nav-pill:#cfe0ff; --nav-pill2:#b7d1ff;
  --chip-brd:#d6e7ff; --chip-on:#76a8ff;
  --chip-bg:#ffffff; --chip-on-bg:#f3f9ff;
  --cta-from:#c9f0ff; --cta-to:#d6e7ff;
}
html, body, .stApp{
  background:
    radial-gradient(1200px 600px at 20% -10%, #ffffff 0%, var(--bg1) 40%, transparent 70%),
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

/* ====== A. ナビ領域（ui-nav） ====== */
.ui-nav .topbar{
  position:sticky; top:0; z-index:10;
  background:#fffffff2; backdrop-filter:blur(8px);
  border-bottom:1px solid var(--panel-brd); margin:0 -12px 8px; padding:8px 12px 12px
}
.ui-nav .topnav{display:flex; gap:14px; flex-wrap:wrap; margin:2px 0}
.ui-nav .nav-btn>button{
  background:linear-gradient(180deg,var(--nav-pill),var(--nav-pill2)) !important;
  color:#16355d !important; border:1px solid var(--panel-brd) !important;
  height:auto !important; padding:14px 18px !important; border-radius:28px !important;
  font-weight:800 !important; font-size:1.0rem !important;
  box-shadow:0 8px 20px rgba(40,80,160,.12) !important;
}
.ui-nav .active>button{outline:3px solid var(--outline) !important; outline-offset:0px !important}

/* ====== B. 入力領域（ui-form） ====== */
.ui-form .hint{color:#6d7fa2; font-size:.9rem; margin:.2rem 0 .6rem}

/* Emotion / choice chips */
.ui-form .chip-grid{display:grid; grid-template-columns:repeat(6,1fr); gap:8px}
@media (max-width: 680px){ .ui-form .chip-grid{grid-template-columns:repeat(4,1fr)} }
.ui-form .stButton>button{
  background:var(--chip-bg) !important; color:#223552 !important;
  border:1.5px solid var(--chip-brd) !important; border-radius:14px !important;
  box-shadow:none !important; font-weight:700 !important; padding:10px 12px !important;
}
.ui-form .on>button{border:2px solid var(--chip-on) !important; background:var(--chip-on-bg) !important}

/* Inputs */
textarea, input, .stTextInput>div>div>input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"]{
  border-radius:12px!important; background:#ffffff; color:#2a3a55; border:1px solid #e1e9ff
}

/* KPI */
.kpi-grid{display:grid; grid-template-columns:repeat(3,1fr); gap:12px}
.kpi{ background:#fff; border:1px solid var(--panel-brd); border-radius:16px; padding:14px; text-align:center;
  box-shadow:0 8px 20px rgba(40,80,160,.06) }
.kpi .num{font-size:1.6rem; font-weight:900; color:#28456e}
.kpi .lab{color:#5a6b86; font-size:.9rem}

/* CTA button */
.stButton>button,.stDownloadButton>button{
  width:100%; padding:12px 16px; border-radius:16px; border:1px solid var(--chip-brd);
  background:linear-gradient(180deg,var(--cta-from),var(--cta-to)); color:#163455; font-weight:900; font-size:1.02rem;
  box-shadow:0 14px 30px rgba(90,150,240,.16)
}
</style>
""", unsafe_allow_html=True)

inject_css()

# ================= Firestore =================
def firestore_client():
    creds = service_account.Credentials.from_service_account_info(st.secrets["FIREBASE_SERVICE_ACCOUNT"])
    return firestore.Client(project=st.secrets["FIREBASE_SERVICE_ACCOUNT"]["project_id"], credentials=creds)

DB = firestore_client()

# ================= Storage =================
class Storage:
    CBT      = "cbt_entries"
    BREATH   = "breath_sessions"
    MIX      = "mix_note"
    STUDY    = "study_blocks"
    CONSULT  = "consult_msgs"
    PREFS    = "user_prefs"   # {user_id, subjects:[...]}
    SHARED   = "school_share" # 学校への自分主権共有ログ

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
st.session_state.setdefault("_session_stage", "idle")
st.session_state.setdefault("_before_score", None)
st.session_state.setdefault("breath_mode", "calm")  # default 5-2-6
st.session_state.setdefault("note", {"emos": [], "event":"", "words":"", "switch":"", "action":"", "memo":""})

def admin_pass() -> str:
    try:    return st.secrets["ADMIN_PASS"]
    except: return "admin123"

# ============== AI寄り添いメッセージ（10スタイル） ==============
AI_STYLES = ["encourage","humor","check","empathy","reframe","efficacy","rest","boundary","safety","thanks"]
AI_STYLE_LABEL = {
    "encourage":"励まし","humor":"ユーモア少し","check":"事実確認","empathy":"共感",
    "reframe":"見かたを変える","efficacy":"できる感覚","rest":"休む許可","boundary":"境界線",
    "safety":"安全計画","thanks":"感謝"
}

def gen_ai_message(mood:str, sleep_band:str, body:list[str], style:str) -> str:
    # mood: "🙂","😐","😟", sleep_band: "少","普","多"
    # body: ["頭痛","腹痛","だるい",...]
    base_bad = (mood=="😟") or (sleep_band=="少") or ("だるい" in body)
    if style=="encourage":
        return "ここまで来てくださって、もう十分えらいです。まずはゆっくり3回、息をしてみませんか。"
    if style=="humor":
        return "しんどい日って、Wi-Fiみたいにたまに“つながりにくい”ですよね。いまは再接続の3呼吸をどうぞ。"
    if style=="check":
        return "今日はいつもより眠れましたか。空腹や水分不足はありませんか。必要なら、まず一口のお水からどうぞ。"
    if style=="empathy":
        return "そのお気持ち、ここに届いています。無理に言葉にしなくて大丈夫です。"
    if style=="reframe":
        return "“うまくいかない日”は、からだが休憩を教えてくれているサインかもしれません。少しだけ力を抜いてみませんか。"
    if style=="efficacy":
        return "いまできることをひとつだけ。カーテンを開ける、または顔を洗う。どちらがしっくりきますか。"
    if style=="rest":
        return "休んでも大丈夫です。5分だけ目を閉じる、静かな音を流す、どちらでも。ご自身のペースで。"
    if style=="boundary":
        return "いまは“がんばらない”を選んでも大丈夫です。今日の自分を守る境界線を、一緒につくりましょう。"
    if style=="safety":
        return "もし“とてもつらい”が続くときは、地域の相談窓口もご検討ください。いま、この瞬間のあなたが大切です。"
    if style=="thanks":
        return "来てくださって、ありがとうございます。ここで過ごす1分が、明日のあなたを少し楽にしますように。"
    # fallback
    return "ここにいてくださって、ありがとうございます。いまのままで大丈夫です。"

# ============== 危機語の軽量検出（自動通報はしない） ==============
CRISIS_PATTERNS = [
    r"死にたい", r"消えたい", r"自殺", r"希死", r"傷つけ(たい|てしまう)", r"リスカ", r"OD", r"助けて"
]
def detect_crisis(text:str) -> bool:
    if not text: return False
    for p in CRISIS_PATTERNS:
        if re.search(p, text):
            return True
    return False

# ================= Auth =================
def auth_ui() -> bool:
    if st.session_state._auth_ok: return True
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 🔐 ログイン")
        tab_user, tab_admin = st.tabs(["利用者として入る", "運営として入る"])
        with tab_user:
            st.caption("ユーザーIDをご入力ください。ご自身の記録だけが表示・保存されます。")
            uid = st.text_input("ユーザーID", placeholder="例: omu-2025-xxxx", key="login_uid")
            if st.button("➡️ 入る（利用者）", type="primary"):
                uid = uid.strip()
                if uid == "": st.warning("ユーザーIDをご入力ください。")
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
                    st.success("運営ログインが完了しました。")
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

# ================= Navigation =================
def navigate(to_key: str):
    st.session_state.view = to_key

def top_nav():
    st.markdown('<div class="ui-nav">', unsafe_allow_html=True)
    st.markdown('<div class="topbar">', unsafe_allow_html=True)
    who = "運営" if st.session_state.role=="admin" else f"利用者（{st.session_state.user_id}）"
    st.markdown(f'<div style="font-size:.82rem;color:#6d7fa2">ログイン中：{who}</div>', unsafe_allow_html=True)
    pages = [
        ("HOME",   "🏠 ホーム"),
        ("NOTE",   "📝 心を整える"),
        ("SESSION","🌙 リラックス & レスキュー"),
        ("REVIEW", "📒 ふりかえり"),
        ("STUDY",  "📚 Study Tracker"),
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
        breath = view[view.get("mode","")=="breath"]
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
    prog = st.progress(0, text="ご一緒に、ゆっくり呼吸しましょう。")
    elapsed = 0; total = cycles * (inhale+hold+exhale)
    for _ in range(cycles):
        for name, secs in [("吸ってください", inhale), ("とめてください", hold), ("吐いてください", exhale)]:
            if secs==0: continue
            st.markdown(f"**{name}**（{secs}）")
            for _ in range(secs):
                elapsed += 1; prog.progress(min(int(elapsed/total*100), 100)); time.sleep(1)

# ================= HOME（1分ルーチン） =================
def view_home_user():
    uid = st.session_state.user_id
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 言葉の前に、息をひとつ。")
    st.caption("正確さより、いまの“感じ”。言葉にならなくても大丈夫です。")
    st.markdown('</div>', unsafe_allow_html=True)

    # ---- 1) ワンタップ・チェックイン（気分 / 体調 / 睡眠） ----
    st.markdown("#### ① いまの自分をチェック")
    col1, col2, col3 = st.columns(3)
    with col1:
        mood = st.segmented_control("気分", options=["🙂","😐","😟"], default="😐", key="home_mood")
    with col2:
        body_map = ["無","頭痛","腹痛","吐き気","食欲低下","だるい","生理関連","その他"]
        body = st.multiselect("体調", body_map, default=["無"], key="home_body")
        if "無" in body and len(body)>1:
            body = [b for b in body if b!="無"]
            st.session_state["home_body"] = body
    with col3:
        sleep = st.segmented_control("睡眠", options=["少","普","多"], default="普", key="home_sleep")
    st.caption("「言葉にならなくてもOK。今日は“どれっぽい？”で十分ですよ。」")

    # ---- 2) 整える（自動提案：呼吸 / やさしい言葉 / 1分ストレッチ案内） ----
    st.markdown("#### ② 整える")
    need_breath = (mood=="😟") or (sleep=="少") or ("だるい" in body)
    suggestion = st.radio("本日のおすすめ", ["呼吸でととのえる","やさしい言葉を受け取る","1分ストレッチ案内"],
                          index=0 if need_breath else 1, horizontal=True)
    # Before/After
    before = st.slider("いまの気分（-3 とてもつらい / +3 とても楽）", -3, 3, -1 if need_breath else 0, key="home_before")

    if suggestion=="呼吸でととのえる":
        if st.button("🫁 90秒 呼吸をはじめる", type="primary"):
            run_breath_session(90)
            st.success("お疲れさまでした。次の項目で終わりの気分をお聞かせください。")
    elif suggestion=="1分ストレッチ案内":
        st.info("無理のない範囲で、肩や首をゆっくり回してみてください。終わったら、いまの気分をお選びください。")
    else:
        # やさしいAIの一言（10スタイルから自動選択）
        style = "empathy" if need_breath else "thanks"
        msg = gen_ai_message(mood, sleep, body, style)
        st.markdown(f"> {msg}")

    after = st.slider("整えたあとの気分（-3 とてもつらい / +3 とても楽）", -3, 3, 0, key="home_after")
    delta = int(after) - int(before)
    st.caption(f"いいね。ここまで来られたのが、もうすでに一歩。 気分の変化：**{delta:+d}**")

    # ---- 3) 一言メモ ----
    st.markdown("#### ③ 一言メモ（任意）")
    oneword = st.text_input("今日いちばん近い言葉（空欄でも大丈夫です）", key="home_oneword")
    st.caption("“なんとなくムリ”でも立派なメモです。")

    # ---- 4) 保存（MIX + 必要に応じてBREATH） ----
    if st.button("💾 1分ルーチンを保存", type="primary"):
        # BREATH保存（提案=呼吸 かつ 実行フラグは取れないので、triggerを推定保存）
        if suggestion=="呼吸でととのえる":
            inhale, hold, exhale = breath_patterns()[st.session_state.breath_mode]
            Storage.append_user(Storage.BREATH, uid, {
                "ts": now_ts_iso(), "mode": st.session_state.breath_mode,
                "target_sec": 90, "inhale": inhale, "hold": hold, "exhale": exhale,
                "mood_before": int(before), "mood_after": int(after), "delta": delta,
                "trigger": "panic" if mood=="😟" else ("sleep" if sleep=="少" else "unknown")
            })
        # MIX保存（追加フィールドを含む）
        Storage.append_user(Storage.MIX, uid, {
            "ts": now_ts_iso(), "mode":"home",
            "mood_face": mood, "phys_signals": json.dumps(body, ensure_ascii=False),
            "sleep_band": sleep, "oneword": oneword.strip(),
            "mood_before": int(before), "mood_after": int(after), "delta": delta,
            "rescue_used": (suggestion=="呼吸でととのえる"),
            "ai_style_used": ("empathy" if suggestion=="やさしい言葉を受け取る" else ""),
            # 互換フィールド（REVIEW集計用）
            "emos": mood, "event":"", "action":"", "switch":"", "memo":""
        })
        st.success("保存しました。ありがとうございます。")

    # ---- つながる導線（常時表示） ----
    st.markdown("#### つながる（必要なときだけで大丈夫です）")
    c1,c2,c3,c4 = st.columns([1,1,1,1])
    with c1:
        if st.button("🤖 AIにひとこと", use_container_width=True):
            # 現在の状態からスタイルを選び、一言生成
            style = "empathy" if need_breath else "encourage"
            st.session_state["ai_last_msg"] = gen_ai_message(mood, sleep, body, style)
            st.session_state["ai_last_style"] = style
            st.toast("AIからのひとことを表示しました。")
    with c2:
        if st.button("🕊 匿名相談へ", use_container_width=True):
            navigate("CONSULT"); st.experimental_rerun()
    with c3:
        if st.button("🏫 学校に伝える", use_container_width=True):
            navigate("SHARE") if "SHARE" in [] else st.session_state.__setitem__("view","SHARE")
            st.experimental_rerun()
    with c4:
        if st.button("📝 続けてノート", use_container_width=True):
            navigate("NOTE"); st.experimental_rerun()

    # レスキュー・ショートカット（固定2ボタン）
    st.markdown("---")
    st.markdown("#### ショートカット")
    sc1, sc2 = st.columns(2)
    with sc1:
        if st.button("⚡ いま苦しい", use_container_width=True):
            st.session_state.breath_mode = "calm"
            run_breath_session(90)
            st.info(gen_ai_message("😟", sleep, body, "empathy"))
            st.success("必要であれば、匿名相談にお進みください。")
    with sc2:
        if st.button("🪄 動けない", use_container_width=True):
            st.session_state.breath_mode = "gentle"
            run_breath_session(20)
            st.info("まずは一歩だけ：窓を開ける / 水を飲む / 顔を洗う。しっくりくるものを、ひとつだけ。")

    # KPI（軽）
    k = last7_kpis_user(uid)
    st.markdown('<div class="kpi-grid">', unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    with c1: st.markdown(f'<div class="kpi"><div class="num">{k["breath"]}</div><div class="lab">リラックス回数（7日）</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="kpi"><div class="num">{k["delta_avg"]:+.2f}</div><div class="lab">平均Δ（気分）</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="kpi"><div class="num">{k["steps"]}</div><div class="lab">小さな行動の記録</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ================= NOTE =================
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
    st.caption("いまの気持ち（複数お選びいただけます）")
    n["emos"] = _emoji_pills("emo", EMOJI_CHOICES, n.get("emos",[]))

    st.markdown('<div class="hint">むずかしく考えなくて大丈夫です。思いついたことを一言で。</div>', unsafe_allow_html=True)
    n["event"] = st.text_area("今日は、どんなことが印象に残りましたか？（任意）", value=n.get("event",""))
    n["words"] = st.text_area("いまの心を、どんな言葉で表せそうでしょうか？", value=n.get("words",""))

    SWITCHES = [
        "外の空気・光に触れる（環境）", "体を少し動かす（からだ）", "安心できる音・音楽（感覚）",
        "ごろごろ休む（休息）", "どなたかと少し話す（つながり）", "小さな達成（やり切る）"
    ]
    idx = SWITCHES.index(n.get("switch", SWITCHES[0])) if n.get("switch") in SWITCHES else 0
    n["switch"] = st.selectbox("いまの自分に合いそうな“気分スイッチ”をお選びください。", SWITCHES, index=idx)

    n["action"] = st.text_area("それを少しだけ具体化すると、どんな“小さな一歩”になりそうでしょうか？（任意）", value=n.get("action",""), height=80)
    st.caption("※ やらなければならないものではありません。ご自身のペースで十分です。")

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
            "switch": n.get("switch",""), "memo": n.get("memo",""),
            # 追加フィールドの既定値
            "mood_face":"", "phys_signals": json.dumps([], ensure_ascii=False),
            "sleep_band":"", "rescue_used": False, "ai_style_used":""
        })
        st.success("保存しました。ここまでで十分です。")
        st.session_state.note = {"emos": [], "event":"", "words":"", "switch":"", "action":"", "memo":""}
    st.markdown('</div>', unsafe_allow_html=True)

# ============== SESSION（呼吸） ==============
def view_session():
    st.subheader("🌙 リラックス & レスキュー")
    st.caption("ご一緒に、ゆっくり呼吸をしてまいりましょう。90秒だけお時間ください。")
    before = st.slider("はじめる前の気分（-3 とてもつらい / +3 とても楽）", -3, 3, -2)
    if st.button("🫁 90秒 呼吸をはじめる", type="primary"):
        run_breath_session(90)
        st.success("お疲れさまでした。ありがとうございます。")
    after = st.slider("終わったあとの気分（-3 とてもつらい / +3 とても楽）", -3, 3, 0)
    delta = int(after) - int(before)
    st.caption(f"気分の変化：**{delta:+d}**")

    if st.button("💾 記録を保存", type="primary"):
        inhale, hold, exhale = breath_patterns()[st.session_state.breath_mode]
        uid = st.session_state.user_id
        Storage.append_user(Storage.BREATH, uid, {
            "ts": now_ts_iso(), "mode": st.session_state.breath_mode,
            "target_sec": 90, "inhale": inhale, "hold": hold, "exhale": exhale,
            "mood_before": int(before), "mood_after": int(after), "delta": delta,
            "trigger":"unknown"
        })
        Storage.append_user(Storage.MIX, uid, {
            "ts": now_ts_iso(), "mode":"breath",
            "mood_before": int(before), "mood_after": int(after), "delta": delta,
            "rescue_used": True, "ai_style_used":""
        })
        st.success("保存しました。")

# ============== REVIEW（ふりかえり + からだシグナル） ==============
def view_review():
    st.subheader("📒 ふりかえり")
    uid = st.session_state.user_id

    def date_filter_ui(df, prefix:str):
        if df.empty: return df
        df["ts"] = pd.to_datetime(df["ts"])
        today = datetime.now().date()
        c1, c2 = st.columns(2)
        with c1: since = st.date_input("開始日", value=today - timedelta(days=30), key=f"{prefix}_since")
        with c2: until = st.date_input("終了日", value=today, key=f"{prefix}_until")
        return df[(df["ts"].dt.date >= since) & (df["ts"].dt.date <= until)].copy()

    tabs = st.tabs(["今月のからだサイン","心の記録（HOME/NOTE/SESSION）","Study Tracker","リラックスのみ"])
    # ---- A. からだシグナル集計 ----
    with tabs[0]:
        df = Storage.load_user(Storage.MIX, uid)
        if df.empty: st.caption("まだ記録がありません。")
        else:
            df = date_filter_ui(df, "mix")
            if "phys_signals" in df.columns:
                # 展開
                df["phys_list"] = df["phys_signals"].apply(lambda x: json.loads(x) if isinstance(x,str) and x else [])
                all_signals = []
                for _,r in df.iterrows():
                    for s in r["phys_list"]:
                        all_signals.append({"ts":r["ts"],"signal":s,"mood":r.get("mood_face",""),"sleep":r.get("sleep_band","")})
                sdf = pd.DataFrame(all_signals)
                if sdf.empty:
                    st.caption("からだのサインの記録がありません。")
                else:
                    st.markdown("#### 集計")
                    cnt = sdf.groupby("signal")["signal"].count().rename("回数").reset_index().sort_values("回数", ascending=False)
                    st.dataframe(cnt, use_container_width=True, hide_index=True)
                    st.markdown("#### 気分との同時出現（🙂/😐/😟）")
                    if "mood" in sdf.columns:
                        co = sdf.groupby(["signal","mood"]).size().reset_index(name="回数").sort_values("回数", ascending=False)
                        st.dataframe(co, use_container_width=True, hide_index=True)
                    # やさしい返し（例文）
                    total = int(cnt["回数"].sum())
                    bad = int(sdf[sdf.get("mood","")== "😟"]["signal"].count()) if "mood" in sdf.columns else 0
                    st.info(f"今月の“からだのサイン”は **{total}回**。そのうち**つらい気分（😟）**と一緒に出たのは **{bad}回**でした。")
                    st.caption("「外の光に触れる」「肩や首をゆっくり回す」などが合っている日が多いかもしれません。無理のない範囲でお試しください。")
            else:
                st.caption("からだのサイン項目がまだありません。")

    # ---- B. 心の記録（HOME/NOTE/SESSION） ----
    with tabs[1]:
        df = Storage.load_user(Storage.MIX, uid)
        if df.empty: st.caption("まだ記録がありません。")
        else:
            df = date_filter_ui(df, "mix2").sort_values("ts", ascending=False)
            cols = [c for c in ["ts","mode","mood_face","emos","oneword","action","switch","memo","sleep_band","delta","_id"] if c in df.columns]
            st.dataframe(df[cols].rename(columns={
                "ts":"日時","mode":"モード","mood_face":"気分","emos":"感情","oneword":"ひとこと",
                "action":"小さな一歩","switch":"スイッチ","memo":"メモ","sleep_band":"睡眠","delta":"Δ","_id":"ID"
            }), use_container_width=True, hide_index=True)

    # ---- C. Study ----
    with tabs[2]:
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

    # ---- D. リラックス ----
    with tabs[3]:
        df = Storage.load_user(Storage.BREATH, uid)
        if df.empty: st.caption("まだ記録がありません。")
        else:
            df = date_filter_ui(df, "breath").sort_values("ts", ascending=False)
            cols = [c for c in ["ts","mode","mood_before","mood_after","delta","trigger","_id"] if c in df.columns]
            st.dataframe(df[cols].rename(columns={
                "ts":"日時","mode":"モード","mood_before":"前","mood_after":"後","delta":"Δ","trigger":"きっかけ","_id":"ID"
            }), use_container_width=True, hide_index=True)

# ============== STUDY =================
def view_study():
    st.subheader("📚 Study Tracker（学習時間の記録）")
    st.caption("“やれた”を見えるかたちに。継続の味方になります。")
    uid = st.session_state.user_id
    subjects = Storage.get_subjects(uid)
    col_left, col_right = st.columns(2)
    with col_left:
        subj = st.selectbox("科目をお選びください。", subjects, index=0, key="study_subj_sel")
        new_subj = st.text_input("＋ 自分の科目を追加（Enterで追加）", key="study_add_subj")
        if new_subj.strip():
            if new_subj.strip() not in subjects:
                subjects.append(new_subj.strip())
                Storage.save_subjects(uid, subjects)
                st.success(f"科目を追加しました：{new_subj.strip()}")
    with col_right:
        minutes = st.number_input("学習時間（分）", min_value=1, max_value=600, value=30, step=5)
        mood_choice = st.selectbox("状況をお選びください。", ["順調","難航","しんどい","集中","だるい","眠い","その他"], index=0)
        mood_free = st.text_input("状況をご自身の言葉で（空欄可）")
        mood = mood_free.strip() if mood_free.strip() else mood_choice
    note = st.text_input("メモ（任意）")

    if st.button("💾 記録", type="primary"):
        Storage.append_user(Storage.STUDY, uid, {
            "ts": now_ts_iso(), "subject": (new_subj.strip() or subj), "minutes": int(minutes),
            "mood": mood, "memo": note
        })
        st.success("保存しました。ありがとうございます。")

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
        agg = df.groupby("subject", dropna=False)["minutes"].sum().reset_index().sort_values("minutes", ascending=False)
        total = agg["minutes"].sum()
        agg["割合(%)"] = (agg["minutes"]/total*100).round(1)
        agg = agg.rename(columns={"subject":"科目","minutes":"合計（分）"})
        st.markdown("##### 科目別の割合")
        st.dataframe(agg, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ============== CONSULT（匿名相談） ==============
def view_consult():
    st.subheader("🕊 相談（匿名）")
    st.caption("このメッセージは**匿名**で相談員に届きます。お名前・連絡先はご記入なさらないでください。")
    uid = st.session_state.user_id
    col1,col2 = st.columns(2)
    with col1:
        morning_mood = st.slider("今朝の気分（-3 とてもつらい / +3 とても楽）", -3, 3, 0)
        sleep_hours  = st.number_input("昨夜の睡眠時間（h）", min_value=0.0, max_value=24.0, value=6.0, step=0.5)
    with col2:
        want_contact = st.selectbox("相談員にお伝えしたい緊急度", ["急ぎではありません","できれば早めに","なるべく急ぎで"], index=1)
        nickname     = st.text_input("匿名ニックネーム（任意）", placeholder="例）月のひと")
    msg = st.text_area("ご相談内容をご記入ください。", height=140)
    extra = st.text_area("他に伝えておきたいこと（任意）", height=80)

    # 危機語への即時案内（自動通報なし）
    if detect_crisis(msg):
        st.warning("とても苦しいお気持ちが伝わってきます。必要に応じて、お住まいの地域の相談窓口や専門機関もご検討ください。いまのあなたの安全がいちばん大切です。")

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
        st.success("送信しました。ありがとうございます。必要に応じて、全体向けのご案内を行います。")

# ============== SHARE（自分主権の学校共有） ==============
def view_share():
    st.subheader("🏫 学校に伝える（ご自身で選べます）")
    st.caption("自動で共有はされません。**あなたが選んだ内容だけ**が学校に届きます。あとで取り消すこともできます。")

    uid = st.session_state.user_id
    # 直近のHOME/NOTEからプレビュー用の簡易サマリー生成
    mix = Storage.load_user(Storage.MIX, uid)
    last = mix.head(1).to_dict(orient="records")[0] if not mix.empty else {}

    st.markdown("#### 共有する内容をお選びください。")
    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: f_em = st.checkbox("感情", value=False)
    with c2: f_bd = st.checkbox("体調", value=False)
    with c3: f_sl = st.checkbox("睡眠", value=False)
    with c4: f_st = st.checkbox("学習", value=False)
    with c5: f_cn = st.checkbox("困りごと", value=False)
    note = st.text_area("“これだけは伝えたい”こと（任意）", height=80, placeholder="例）朝に不安が強く、保健室に寄ってから教室に行きたい  など")

    # 週次 or 本日
    scope = st.radio("共有の単位をお選びください。", ["本日のサマリー","今週の傾向"], index=0, horizontal=True)

    # プレビュー
    st.markdown("#### プレビュー（この内容が学校に送られます。お名前は入りません）")
    preview = {
        "scope": scope,
        "emotion": last.get("mood_face","") if f_em else None,
        "body": json.loads(last.get("phys_signals","[]")) if f_bd else None,
        "sleep": last.get("sleep_band","") if f_sl else None,
        "study": None,  # 下で取得
        "concern": note.strip() if f_cn and note.strip() else None
    }

    # 学習（直近合計）
    if f_st:
        study = Storage.load_user(Storage.STUDY, uid)
        if not study.empty:
            study["ts"] = pd.to_datetime(study["ts"])
            week = study[study["ts"]>= datetime.now()-timedelta(days=7)]
            agg = week.groupby("subject")["minutes"].sum().reset_index().sort_values("minutes", ascending=False)
            preview["study"] = agg.to_dict(orient="records")
        else:
            preview["study"] = []

    st.code(json.dumps(preview, ensure_ascii=False, indent=2))

    if st.button("📨 この内容で学校に送る", type="primary"):
        Storage.append_user(Storage.SHARED, uid, {
            "ts": now_ts_iso(),
            "scope": scope,
            "share_flags": {"emotion":f_em, "body":f_bd, "sleep":f_sl, "study":f_st, "concern":f_cn},
            "payload": preview
        })
        st.success("送信しました。必要であれば、後から取り消すこともできます。ありがとうございます。")

# ============== EXPORT（個人 CSV） ==============
def export_and_wipe_user():
    uid = st.session_state.user_id
    st.subheader("⬇️ 記録・エクスポート（CSV）")
    for label, table in [
        ("心を整える（互換）", Storage.CBT),
        ("リラックス",         Storage.BREATH),
        ("心を整える（統合）", Storage.MIX),
        ("Study Tracker",     Storage.STUDY),
        ("匿名相談",           Storage.CONSULT),
        ("学校共有ログ",        Storage.SHARED),
    ]:
        df = Storage.load_user(table, uid)
        if df.empty:
            st.caption(f"{label}：まだデータがありません")
            continue
        data = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(f"⬇️ {label} を保存（CSV）", data, file_name=f"{uid}_{table}.csv", mime="text/csv", key=f"dl_{uid}_{table}")

# ============== Admin Dash（参考） ==============
def view_admin_dash():
    st.subheader("📊 運営ダッシュボード（全体）")

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

    st.markdown("#### 最近の『心を整える』記録（最新50件・モード混在）")
    df = Storage.load_all(Storage.MIX)
    if df.empty:
        st.caption("データなし")
    else:
        df["ts"] = pd.to_datetime(df["ts"])
        show = df.sort_values("ts", ascending=False).head(50)
        cols = [c for c in ["ts","user_id","mode","mood_face","emos","oneword","action","switch","sleep_band","delta"] if c in show.columns]
        st.dataframe(show[cols].rename(columns={
            "ts":"日時","user_id":"ユーザーID","mode":"モード","mood_face":"気分","emos":"感情",
            "oneword":"ひとこと","action":"小さな一歩","switch":"スイッチ","sleep_band":"睡眠","delta":"Δ"
        }), use_container_width=True, hide_index=True)

    st.markdown("#### ⬇️ 全体エクスポート（CSV）")
    for label, table in [
        ("心を整える（互換）", Storage.CBT),
        ("リラックス",         Storage.BREATH),
        ("心を整える（統合）", Storage.MIX),
        ("Study Tracker",     Storage.STUDY),
        ("匿名相談",           Storage.CONSULT),
        ("学校共有ログ",        Storage.SHARED),
    ]:
        all_df = Storage.load_all(table)
        if all_df.empty:
            st.caption(f"{label}：データなし")
            continue
        data = all_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(f"⬇️ 全ユーザー {label} を保存（CSV）", data, file_name=f"ALL_{table}.csv", mime="text/csv", key=f"dl_all_{table}")

# ================= Router =================
def main_router():
    top_nav()
    st.markdown('<div class="ui-form">', unsafe_allow_html=True)
    v = st.session_state.view
    if v=="HOME":
        (st.markdown("### ようこそ（運営）\n集計は「📊 運営ダッシュボード」からご確認ください。") if st.session_state.role=="admin"
         else view_home_user())
    elif v=="DASH" and st.session_state.role=="admin":
        view_admin_dash()
    elif v=="NOTE":
        (st.info("運営モードでは記入できません。利用者としてログインしてください。")
         if st.session_state.role=="admin" else view_note())
    elif v=="SESSION":
        (st.info("運営モードでは個人の記録は行いません。利用者としてログインしてください。")
         if st.session_state.role=="admin" else view_session())
    elif v=="REVIEW":
        (st.info("運営モードでは個別編集は行いません。利用者としてログインしてください。")
         if st.session_state.role=="admin" else view_review())
    elif v=="STUDY":
        (st.info("運営モードでは記録できません。利用者としてログインしてください。")
         if st.session_state.role=="admin" else view_study())
    elif v=="CONSULT":
        (st.info("運営モードでは個人の送信は行いません。利用者としてログインしてください。")
         if st.session_state.role=="admin" else view_consult())
    elif v=="SHARE":
        (st.info("運営モードでは送信できません。利用者としてログインしてください。")
         if st.session_state.role=="admin" else view_share())
    else:
        export_and_wipe_user()
    st.markdown('</div>', unsafe_allow_html=True)

# ================= App =================
if auth_ui():
    logout_btn()
    main_router()

# ================= Footer =================
st.markdown("""
<div style="text-align:center; color:#5a6b86; margin-top:12px;">
  <small>※ 個人名や連絡先は記入しないでください。<br>
  とてもつらい場合は、お住まいの地域の相談窓口や専門機関のご利用もご検討ください。<br>
  通知は夜間に鳴らないよう配慮しています（静かな夜モード）。</small>
</div>
""", unsafe_allow_html=True)
