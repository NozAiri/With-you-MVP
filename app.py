# app.py — Sora / With You.（運営ダッシュボード付き・一発コード認証）
# 保存方針：
#  - Firestore保存＝「今日を伝える」「相談」だけ（運営が把握）
#  - それ以外（ノート／リラックス／Study／レビュー）は端末のみ（DL＋このセッション内の履歴）

from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import pandas as pd
import streamlit as st
import json, time, re
import altair as alt

# --- 万一どこかで help()/st.help(...) が残っていても出力されない応急処置（原因特定後に削除可） ---
import builtins
builtins.help = lambda *args, **kwargs: None
# -----------------------------------------------------------------------------------------------

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
.item{ background:#fff; border:1px solid #e3e8ff; border-radius:18px; padding:16px; box-shadow:var(--shadow) }
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

/* ------- CBT cards ------- */
.cbt-card{ background:#fff; border:1px solid #e3e8ff; border-radius:18px; padding:18px 18px 14px; box-shadow:0 6px 20px rgba(31,59,179,0.06); margin-bottom:14px; }
.cbt-heading{ font-weight:900; font-size:1.05rem; color:#1b2440; margin:0 0 6px 0;}
.cbt-sub{ color:#63728a; font-size:0.92rem; margin:-2px 0 10px 0;}
.ok-chip{ display:inline-block; padding:2px 8px; border-radius:999px; background:#e8fff3; color:#156f3a; font-size:12px; border:1px solid #b9f3cf; }

/* ------- 呼吸アニメ keyframes ------- */
@keyframes sora-grow   { from{transform:scale(0.85)} to{transform:scale(1.0)} }
@keyframes sora-steady { from{transform:scale(1.0)}  to{transform:scale(1.0)} }
@keyframes sora-shrink { from{transform:scale(1.0)}  to{transform:scale(0.85)} }
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

# ========= Local（端末＝このセッションに保存する辞書） =========
def init_local_logs():
    st.session_state.setdefault("_local_logs", {"note":[], "breath":[], "study":[]})
init_local_logs()

# ========= Utils / State =========
def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

st.session_state.setdefault("_auth_ok", False)
st.session_state.setdefault("role", None)          # "admin" / "user" / None
st.session_state.setdefault("user_id", "")
st.session_state.setdefault("view", "HOME")
st.session_state.setdefault("_nav_stack", [])
st.session_state.setdefault("_breath_running", False)
st.session_state.setdefault("_breath_stop", False)

# ★ 固定管理パスワード（運営コード）
def admin_pass() -> str:
    return "uneiairi0931"

CRISIS_PATTERNS = [r"死にたい", r"消えたい", r"自殺", r"希死", r"傷つけ(たい|てしまう)", r"リスカ", r"\bOD\b", r"助けて"]
def crisis(text: str) -> bool:
    if not text: return False
    for p in CRISIS_PATTERNS:
        if re.search(p, text):
            return True
    return False

# ========= Nav =========
BASE_SECTIONS = [
    ("HOME",   "🏠 ホーム"),
    ("SHARE",  "🏫 今日を伝える"),
    ("SESSION","🌙 リラックス"),
    ("NOTE",   "📝 ノート"),
    ("STUDY",  "📚 Study Tracker"),
    ("REVIEW", "📒 ふりかえり"),
    ("CONSULT","🕊 相談"),
]
ADMIN_SECTION = ("ADMIN", "🛡 運営")

def _sections_for_role() -> List[tuple]:
    if st.session_state.get("role") == "admin":
        return BASE_SECTIONS + [ADMIN_SECTION]
    return BASE_SECTIONS

def navigate(to_key: str, push: bool = True):
    cur = st.session_state.view
    if push and cur != to_key:
        st.session_state._nav_stack.append(cur)
    st.session_state.view = to_key

def top_tabs():
    if st.session_state.view == "HOME":  # HOMEでは非表示
        return
    active = st.session_state.view
    sections = _sections_for_role()
    st.markdown('<div class="top-tabs">', unsafe_allow_html=True)
    cols = st.columns(len(sections))
    for i, (key, label) in enumerate(sections):
        with cols[i]:
            cls = "active" if key == active else ""
            st.markdown(f"<div class='{cls}'>", unsafe_allow_html=True)
            if st.button(label, key=f"tab_{key}"):
                navigate(key, push=False)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def top_status():
    role_txt = '運営' if st.session_state.role=='admin' else (f'利用者（{st.session_state.user_id}）' if st.session_state.user_id else '利用者')
    fs_txt = "接続済み" if FIRESTORE_ENABLED else "未接続（オフライン送信）"
    st.markdown('<div class="card" style="padding:8px 12px; margin-bottom:10px">', unsafe_allow_html=True)
    st.markdown(f"<div class='tip'>ログイン中：{role_txt} / データ共有：{fs_txt}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ========= Small helpers =========
def home_big_button(title: str, sub: str, target_view: str, key: str, emoji: str):
    label = f"{emoji} {title}\n{sub}"
    with st.container():
        st.markdown('<div class="bigbtn">', unsafe_allow_html=True)
        if st.button(label, key=f"homebtn_{key}"):
            navigate(target_view, push=True); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ========= HOME =========
def home_intro_block():
    st.markdown("""
<div class="card" style="margin-bottom:12px">
  <div style="font-weight:900; font-size:1.05rem; margin-bottom:.3rem">🌙 With You について</div>
  <div style="color:#3a4a6a; line-height:1.65; white-space:pre-wrap">
気持ちを整理したい日も、誰かに話したい日も。
With You は、あなたの心のそばにある、小さなツールボックスです。

今の自分に合うカードを選んで、少しずつ整える時間をつくってみてください。

🔒 「今日を伝える」と「相談する」だけが運営に届きます。
それ以外の記録は、すべてあなたの端末だけに残ります。
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

# ========= リラックス（呼吸） =========
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
            f'</div>', unsafe_allow_html=True)
        for _ in range(seconds):
            if st.session_state.get("_breath_stop") or st.session_state.view != "SESSION":
                return False
            time.sleep(1)
        return True

    with ctrl.container():
        if st.button("⏹ 停止する", key="breath_stop_btn"):
            st.session_state["_breath_stop"] = True

    for _ in range(cycles):
        if not phase("吸ってください", inhale, "sora-grow"): break
        if hold > 0 and not phase("止めてください", hold, "sora-steady"): break
        if not phase("吐いてください", exhale, "sora-shrink"): break

    st.session_state["_breath_running"] = False
    st.session_state["_breath_stop"] = False
    ph.empty(); spot.empty(); ctrl.empty()

def view_session():
    st.markdown("### 🌙 リラックス（呼吸）")
    st.caption("円が大きくなったら吸って、小さくなったら吐きます。途中で停止・ページ移動できます。")

    c1, c2 = st.columns([1,1])
    with c1:
        if not st.session_state.get("_breath_running", False):
            if st.button("🫁 はじめる（90秒）", type="primary", key="breath_start"):
                st.session_state["_breath_running"] = True
                st.session_state["_breath_stop"] = False
                st.rerun()
        else:
            st.info("実行中です。上のタブから他ページへ移動できます。")
    with c2:
        if st.session_state.get("_breath_running", False):
            if st.button("⏹ 停止", key="breath_stop_top", type="secondary"):
                st.session_state["_breath_stop"] = True

    if st.session_state.get("_breath_running", False):
        breathing_animation(90)
        st.success("お疲れさまでした。ありがとうございます。")

    st.divider()
    after = st.slider("いまの気分（1 とてもつらい / 10 とても楽）", 1, 10, 5, key="breath_mood_after")
    if st.button("💾 端末に保存（このセッション内）", type="primary", key="breath_save"):
        st.session_state["_local_logs"]["breath"].append({
            "ts": now_iso(), "pattern": "5-2-6", "mood_after": int(after), "sec": 90
        })
        doc = st.session_state["_local_logs"]["breath"][-1]
        st.download_button("⬇️ この記録をダウンロード（JSON）",
                           data=json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8"),
                           file_name=f"breath_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                           mime="application/json", key=f"breath_dl_{len(st.session_state['_local_logs']['breath'])}")
        st.success("保存しました。（運営には共有されません）")

# ========= ノート =========
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

def mood_radio() -> Dict[str, Any]:
    st.markdown('<div class="cbt-card">', unsafe_allow_html=True)
    st.markdown('<div class="cbt-heading">🌤 Step 1：今の気持ちはどんな感じ？</div>', unsafe_allow_html=True)
    st.markdown('<div class="cbt-sub">いちばん近い絵文字を選んでみよう。</div>', unsafe_allow_html=True)
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

# ===== 行動活性化：絵文字カテゴリ × シンプル行動 =====
ACTION_CATEGORIES_EMOJI = {
    "身体": "🫧",
    "環境": "🌤",
    "リズム": "⏯️",
    "つながり": "💬",
}
ACTION_CATEGORIES = {
    "身体": ["顔や手を洗う","深呼吸をする","肩を回す","シャワーを浴びる"],
    "環境": ["窓を開けて外の空気を感じる","カーテンを開けて部屋を明るくする","空をながめる"],
    "リズム": ["水を飲む","温かい飲み物を飲む","立ち上がって少し歩く","外を少し歩く"],
    "つながり": ["スタンプを送る","「ありがとう」を書く","家族や友達に一言だけ話す"],
}
def _flat_action_options_emoji():
    order = ["身体", "環境", "リズム", "つながり"]
    seen, disp, vals = set(), [], []
    for cat in order:
        emoji = ACTION_CATEGORIES_EMOJI.get(cat, "•")
        for a in ACTION_CATEGORIES.get(cat, []):
            if a in seen: continue
            seen.add(a); disp.append(f"{emoji} {a}"); vals.append(a)
    return disp, vals

def action_picker(mood_key: Optional[str]):
    st.markdown('<div class="cbt-card">', unsafe_allow_html=True)
    st.markdown('<div class="cbt-heading">🌸 Step 6：今、気持ちが少し落ち着くためにできそうなことは？</div>', unsafe_allow_html=True)
    st.markdown('<div class="cbt-sub">ぴったりを1つだけ。選ばなくてもOKだよ。</div>', unsafe_allow_html=True)

    disp, vals = _flat_action_options_emoji()
    options_disp = disp + ["— 選ばない —"]
    pick_key = f"act_pick_single_{(mood_key or 'default').strip().lower()}"

    sel_disp = st.selectbox("小さな行動（任意・スクロールや入力で探せます）",
                            options=options_disp,
                            index=len(options_disp) - 1, key=pick_key)
    chosen = "" if sel_disp == "— 選ばない —" else vals[disp.index(sel_disp)]
    custom_key = f"act_custom_single_{(mood_key or 'default').strip().lower()}"
    custom = st.text_input("＋ 自分の言葉で書く（任意）", key=custom_key, placeholder="例：窓を開けて深呼吸する").strip()
    st.markdown("</div>", unsafe_allow_html=True)
    if custom:
        return "", custom
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
    cbt_intro_block()

    mood = mood_radio()
    trigger_text   = text_card("🫧 Step 2：その気持ちは、どんなことがきっかけだった？", "「○○があったからかも」「なんとなく○○って思ったから」など自由に。", "cbt_trigger")
    auto_thought   = text_card("💭 Step 3：そのとき、頭の中でどんな言葉がよぎった？", "心の中でつぶやいた言葉やイメージをそのまま書いてOK。", "cbt_auto")
    reason_for     = text_card("🔍 Step 4-1：そう思った理由はある？", "「たしかにそうかも」と思うことを書いてみよう。", "cbt_for", height=100)
    reason_against = text_card("🔍 Step 4-2：そうでもないかもと思う理由はある？", "「でも、こういう面もあるかも」も書いてみよう。", "cbt_against", height=100)
    alt_perspective= text_card("🌱 Step 5：もし友だちが同じことを感じていたら、なんて声をかける？", "自分のことじゃなく“友だち”のこととして考えてみよう。", "cbt_alt")
    act_suggested, act_custom = action_picker(mood.get("key"))
    reflection     = text_card("🌙 Step 7：今日の日記", "気づいたこと・気持ちの変化・これからのことなど自由に。", "cbt_reflect", height=120)

    if st.button("📝 記録する（端末）", key="cbt_submit"):
        doc = {
            "ts": now_iso(),
            "mood": mood,
            "trigger_text": (trigger_text or "").strip(),
            "auto_thought": (auto_thought or "").strip(),
            "reason_for": (reason_for or "").strip(),
            "reason_against": (reason_against or "").strip(),
            "alt_perspective": (alt_perspective or "").strip(),
            "action_suggested": (act_suggested or "").strip(),
            "action_custom": (act_custom or "").strip(),
            "reflection": (reflection or "").strip(),
            "meta": {"version":"cbt-note-v2","source":"with-you/streamlit"}
        }
        st.session_state["_local_logs"]["note"].append(doc)
        recap_card(doc)
        st.download_button("⬇️ この記録をダウンロード（JSON）",
                           data=json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8"),
                           file_name=f"cbt_journal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                           mime="application/json", key=f"cbt_dl_{len(st.session_state['_local_logs']['note'])}")
        st.success("保存しました。（運営には共有されません）")

# ========= 今日を伝える（Firestoreに保存） =========
def view_share():
    st.markdown("### 🏫 今日を伝える（匿名可）")

    mood = st.radio("気分", ["🙂", "😐", "😟"], index=1, horizontal=True, key="share_mood")
    body_opts = ["頭痛","腹痛","吐き気","食欲低下","だるさ","その他","なし"]
    body = st.multiselect("体調（当てはまるもの）", body_opts, default=["なし"], key="share_body")
    if "なし" in body and len(body) > 1:
        body = [b for b in body if b != "なし"]

    c1, c2 = st.columns(2)
    with c1:
        sh = st.number_input("睡眠時間（h）", min_value=0.0, max_value=24.0, value=6.0, step=0.5, key="share_sleep_h")
    with c2:
        sq = st.radio("睡眠の質", ["ぐっすり","ふつう","浅い"], index=1, horizontal=True, key="share_sleep_q")

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

    disabled = not FIRESTORE_ENABLED
    label = "📨 送信（匿名）" if FIRESTORE_ENABLED else "📨 送信（無効：データ共有未接続）"
    if st.button(label, type="primary", key="share_submit", disabled=disabled):
        ok = safe_db_add("school_share", {
            "ts": datetime.now(timezone.utc),
            "user_id": st.session_state.user_id,
            "payload": {"mood":mood, "body":body, "sleep_hours":float(sh), "sleep_quality":sq},
            "anonymous": True
        })
        if ok:
            st.success("送信しました。ありがとうございます。")
        else:
            st.error("送信できませんでした（接続が無効です）。")

# ========= 相談（Firestoreに保存） =========
CONSULT_TOPICS = ["体調","勉強","人間関係","家庭","進路","いじめ","メンタルの不調","その他"]

def view_consult():
    st.markdown("### 🕊 相談")
    st.caption("お気軽に。秘密は守ります。お名前は任意です。")

    to_whom = st.radio("相談先を選んでください", ["カウンセラーに相談したい", "先生に伝えたい"], horizontal=True, key="c_to")
    topics  = st.multiselect("内容（当てはまるもの）", CONSULT_TOPICS, default=[], key="c_topics")
    anonymous = st.checkbox("匿名で送る", value=True, key="c_anon")

    # 「匿名で送る」がONのときは name 入力を完全に隠す（評価もさせない）
    name = ""
    if not anonymous:
        name = st.text_input("お名前（任意）", value="", key="c_name")

    # text_area は key を使っているので value 指定はしない
    msg = st.text_area("ご相談したい／伝えたい内容について教えてください。", height=220, key="c_msg")

    if crisis(msg):
        st.warning("とても苦しいお気持ちが伝わってきます。必要に応じて、お住まいの地域の相談窓口や専門機関もご検討ください。")

    disabled = (not FIRESTORE_ENABLED) or (msg.strip()=="")
    label = "🕊 送信する" if FIRESTORE_ENABLED else "🕊 送信（無効：データ共有未接続）"

    if st.button(label, type="primary", disabled=disabled, key="c_submit"):
        payload = {
            "ts": datetime.now(timezone.utc),
            "user_id": st.session_state.user_id,
            "message": msg.strip(),
            "topics": topics,
            "intent": "counselor" if to_whom.startswith("カウンセラー") else "teacher",
            "anonymous": bool(anonymous),
            "name": name.strip() if (not anonymous and name) else "",
        }
        ok = safe_db_add("consult_msgs", payload)
        if ok:
            st.success("送信しました。ありがとうございます。")
            # 送信後は入力をクリア
            st.session_state["c_topics"] = []
            st.session_state["c_anon"] = True
            st.session_state["c_name"] = ""
            st.session_state["c_msg"] = ""
        else:
            st.error("送信できませんでした（接続が無効です）。")

# ========= Study（端末のみ保存） =========
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
        st.download_button("⬇️ この記録をダウンロード（JSON）",
                           data=json.dumps(rec, ensure_ascii=False, indent=2).encode("utf-8"),
                           file_name=f"study_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                           mime="application/json", key=f"study_dl_{len(st.session_state['_local_logs']['study'])}")
        st.success("保存しました。（運営には共有されません）")

# ========= ふりかえり（端末＝このセッションの履歴を表示） =========
def view_review():
    st.markdown("### 📒 ふりかえり（このセッションの履歴）")
    logs = st.session_state["_local_logs"]

    if any(len(v)>0 for v in logs.values()):
        all_json = json.dumps(logs, ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button("⬇️ このセッションの全記録をダウンロード（JSON）", data=all_json,
                           file_name=f"withyou_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                           mime="application/json", key="review_dl_all")

    tabs = st.tabs(["ノート", "呼吸", "Study"])

    with tabs[0]:
        notes = list(reversed(logs["note"]))
        if not notes:
            st.caption("まだ記録がありません。")
        else:
            for r in notes:
                st.markdown(f"""
<div class="item">
  <div class="meta">{r['ts']}</div>
  <div style="font-weight:900; color:#24466e; margin-bottom:.2rem">{r['mood'].get('emoji','')} {r['mood'].get('label','')}</div>
  <div style="white-space:pre-wrap; margin-bottom:.3rem">きっかけ：{r.get('trigger_text','')}</div>
  <div style="white-space:pre-wrap; margin-bottom:.3rem">よぎった言葉：{r.get('auto_thought','')}</div>
  <div style="white-space:pre-wrap; margin-bottom:.3rem">日記：{r.get('reflection','')}</div>
</div>
""", unsafe_allow_html=True)

    with tabs[1]:
        breaths = list(reversed(logs["breath"]))
        if not breaths:
            st.caption("まだ記録がありません。")
        else:
            for r in breaths:
                st.markdown(f"""
<div class="item">
  <div class="meta">{r['ts']}</div>
  <div>パターン：{r['pattern']} / 実施：{r['sec']}秒</div>
  <div>終了時の気分：{r['mood_after']}</div>
</div>
""", unsafe_allow_html=True)

    with tabs[2]:
        studies = list(reversed(logs["study"]))
        if not studies:
            st.caption("まだ記録がありません。")
        else:
            df = pd.DataFrame(studies)
            pie_agg = df.groupby("subject")["minutes"].sum().reset_index().sort_values("minutes", ascending=False)
            if not pie_agg.empty:
                color_scale = alt.Scale(domain=pie_agg["subject"].tolist(),
                                        range=["#A5C8FF","#CDE9D3","#F9D5E5","#FFE7B3","#C9E7FF","#EAD9FF","#BFE9E2"])
                pie = (alt.Chart(pie_agg).mark_arc(innerRadius=60).encode(
                        theta=alt.Theta(field="minutes", type="quantitative"),
                        color=alt.Color(field="subject", type="nominal", legend=alt.Legend(title="科目"), scale=color_scale),
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

# ========= 運営：Firestore 取得ヘルパ =========
def _fetch_firestore_df(coll: str, start_dt: Optional[datetime], end_dt: Optional[datetime], limit: int) -> pd.DataFrame:
    if not FIRESTORE_ENABLED or DB is None:
        return pd.DataFrame()

    q = DB.collection(coll).order_by("ts", direction=firestore.Query.DESCENDING)
    if start_dt:
        q = q.where("ts", ">=", start_dt)
    if end_dt:
        q = q.where("ts", "<=", end_dt)
    q = q.limit(limit)

    rows = []
    try:
        docs = q.stream()
    except Exception:
        return pd.DataFrame()

    for d in docs:
        data = d.to_dict() or {}
        ts = data.get("ts")
        if hasattr(ts, "to_datetime"):
            ts_dt = ts.to_datetime().astimezone(timezone.utc)
        elif isinstance(ts, datetime):
            ts_dt = ts.astimezone(timezone.utc)
        else:
            ts_dt = datetime.now(timezone.utc)

        base = {
            "_doc": d.id,
            "ts": ts_dt.astimezone().isoformat(timespec="seconds"),
            "user_id": data.get("user_id", ""),
            "anonymous": data.get("anonymous", True),
        }

        if coll == "school_share":
            payload = data.get("payload", {})
            body = payload.get("body", [])
            body_disp = " / ".join(body) if isinstance(body, list) else str(body)
            row = {
                **base,
                "mood": payload.get("mood", ""),
                "body": body_disp,
                "sleep_hours": payload.get("sleep_hours", ""),
                "sleep_quality": payload.get("sleep_quality", ""),
            }
        else:  # consult_msgs
            topics = data.get("topics", [])
            topics_disp = " / ".join(topics) if isinstance(topics, list) else str(topics)
            row = {
                **base,
                "name": data.get("name", ""),
                "intent": data.get("intent", ""),
                "topics": topics_disp,
                "message": data.get("message", ""),
            }

        rows.append(row)

    df = pd.DataFrame(rows)
    if not df.empty and "ts" in df.columns:
        df = df.sort_values("ts", ascending=False).reset_index(drop=True)
    return df

def _download_buttons(df: pd.DataFrame, basename: str = "export"):
    if df.empty:
        return
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("⬇️ CSVをダウンロード",
                           data=df.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"{basename}.csv",
                           mime="text/csv",
                           key=f"csv_{basename}")
    with c2:
        st.download_button("⬇️ JSONをダウンロード",
                           data=df.to_json(orient="records", force_ascii=False, indent=2).encode("utf-8"),
                           file_name=f"{basename}.json",
                           mime="application/json",
                           key=f"json_{basename}")

def _render_share_card(row: pd.Series):
    st.markdown(f"""
<div class="item">
  <div class="meta">{row['ts']}</div>
  <div style="display:flex; gap:.4rem; flex-wrap:wrap; margin:.2rem 0 .5rem 0">
    <span class="badge">ユーザー：{row['user_id'] or '—'}</span>
    <span class="badge">匿名：{row.get('anonymous', True)}</span>
    <span class="badge">気分：{row.get('mood','')}</span>
    <span class="badge">睡眠：{(row.get('sleep_hours') or '—')}h / {row.get('sleep_quality','')}</span>
  </div>
  <div style="margin-top:.2rem">体調：
    {" / ".join([b for b in str(row.get('body','')).split(' / ') if b]) or '—'}
  </div>
</div>
""", unsafe_allow_html=True)

def _render_consult_card(row: pd.Series):
    msg = str(row.get("message",""))
    for kw in ["死にたい","自殺","消えたい","助けて"]:
        if kw in msg:
            msg = msg.replace(kw, f"**{kw}**")
    st.markdown(f"""
<div class="item">
  <div class="meta">{row['ts']}</div>
  <div style="display:flex; gap:.4rem; flex-wrap:wrap; margin:.2rem 0 .5rem 0">
    <span class="badge">ユーザー：{row['user_id'] or '—'}</span>
    <span class="badge">匿名：{row.get('anonymous', True)}</span>
    <span class="badge">相談先：{row.get('intent','')}</span>
    <span class="badge">名前：{row.get('name','') or '—'}</span>
    <span class="badge">トピック：{row.get('topics','') or '—'}</span>
  </div>
  <div style="white-space:pre-wrap; color:#2b3d5c">{msg}</div>
</div>
""", unsafe_allow_html=True)

# ========= 運営ダッシュボード =========
def view_admin():
    st.markdown("### 🛡 運営ダッシュボード（利用データ）")
    if not FIRESTORE_ENABLED:
        st.warning("Firestore 未接続のため、一覧は表示できません。Streamlit Secrets に `FIREBASE_SERVICE_ACCOUNT` を設定してください。")

    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        days = st.selectbox("対象期間", ["直近7日","直近14日","直近30日","すべて"], index=1, key="adm_range")
    with c2:
        dataset = st.selectbox("データ種類", ["今日を伝える（school_share）","相談（consult_msgs）"], index=0, key="adm_kind")
    with c3:
        limit = st.number_input("最大取得件数", min_value=100, max_value=5000, value=1000, step=100, key="adm_limit")

    now_utc = datetime.now(timezone.utc)
    start_dt = None if days == "すべて" else now_utc - timedelta(days=int(days.replace("直近","").replace("日","")))
    end_dt = None

    coll = "school_share" if dataset.startswith("今日を伝える") else "consult_msgs"
    df = _fetch_firestore_df(coll, start_dt, end_dt, limit)

    with st.expander("🔎 追加フィルタ", expanded=False):
        if coll == "school_share":
            f_mood = st.multiselect("気分（複数選択可）", sorted(df["mood"].dropna().unique().tolist()) if not df.empty else [], key="f_mood")
            f_body = st.text_input("体調テキストを含む（例：頭痛）", key="f_body")
            f_uid  = st.text_input("ユーザーID（部分一致）", key="f_uid")
            if f_mood and not df.empty: df = df[df["mood"].isin(f_mood)]
            if f_body and not df.empty: df = df[df["body"].fillna("").str.contains(f_body)]
            if f_uid  and not df.empty: df = df[df["user_id"].fillna("").str.contains(f_uid)]
        else:
            f_int = st.multiselect("相談先", ["teacher","counselor"], key="f_int")
            f_topic = st.text_input("トピックを含む（例：いじめ）", key="f_topic")
            f_kw = st.text_input("本文キーワード", key="f_kw")
            f_uid = st.text_input("ユーザーID（部分一致）", key="f_uid_c")
            if f_int and not df.empty: df = df[df["intent"].isin(f_int)]
            if f_topic and not df.empty: df = df[df["topics"].fillna("").str.contains(f_topic)]
            if f_kw and not df.empty: df = df[df["message"].fillna("").str.contains(f_kw)]
            if f_uid and not df.empty: df = df[df["user_id"].fillna("").str.contains(f_uid)]

    if df.empty:
        st.info("該当データがありません。条件を変更してください。")
        return

    st.markdown("#### 📈 概要")
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("件数", len(df))
    with c2: st.metric("ユニーク利用者", int(df["user_id"].replace("", pd.NA).dropna().nunique()))
    with c3: st.metric("最古の記録（表示中）", df["ts"].iloc[-1] if len(df) > 0 else "-")

    st.markdown("#### 🗓 日別件数")
    df["_date"] = pd.to_datetime(df["ts"]).dt.tz_localize(None).dt.date
    agg = df.groupby("_date").size().reset_index(name="count")
    chart = alt.Chart(agg).mark_bar().encode(
        x=alt.X("_date:T", title="日付"),
        y=alt.Y("count:Q", title="件数"),
        tooltip=[alt.Tooltip("_date:T", title="日付"), alt.Tooltip("count:Q", title="件数")]
    ).properties(height=180)
    st.altair_chart(chart, use_container_width=True)

    view_mode = st.radio("表示モード", ["カード表示","テーブル表示"], index=0, horizontal=True, key="adm_viewmode")
    _download_buttons(df, basename=f"{coll}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

    st.markdown("#### 📋 一覧")
    if view_mode == "テーブル表示":
        show_cols = [c for c in df.columns if c not in ["_doc", "_date"]]
        tidy = df[show_cols].copy()
        if coll == "school_share":
            ordered = ["ts","user_id","anonymous","mood","body","sleep_hours","sleep_quality"]
        else:
            ordered = ["ts","user_id","anonymous","name","intent","topics","message"]
        tidy = tidy.reindex(columns=[c for c in ordered if c in tidy.columns] + [c for c in tidy.columns if c not in ordered])
        st.dataframe(tidy, use_container_width=True, hide_index=True)
    else:
        groups = df.sort_values("ts", ascending=False).groupby("_date", sort=False)
        max_n = max(1, min(50, len(df)))
        default_n = min(10, max_n)

        if int(max_n) <= 1:
            n_show = 1
            st.caption("表示件数（最新から）：1")
        else:
            n_show = st.slider("表示件数（最新から）", 1, int(max_n), int(default_n), key="adm_nshow")

        count = 0
        for gdate, gdf in groups:
            if count >= n_show: break
            st.markdown(f"##### 📅 {gdate}")
            for _, row in gdf.sort_values("ts", ascending=False).iterrows():
                if count >= n_show: break
                if coll == "school_share":
                    _render_share_card(row)
                else:
                    _render_consult_card(row)
                count += 1

# ========= Router =========
def main_router():
    v = st.session_state.view
    if v == "HOME":   view_home()
    elif v == "SESSION": view_session()
    elif v == "NOTE": view_note()
    elif v == "SHARE": view_share()
    elif v == "CONSULT": view_consult()
    elif v == "REVIEW": view_review()
    elif v == "STUDY": view_study()
    elif v == "ADMIN" and st.session_state.role == "admin": view_admin()
    else: view_home()

# ========= Auth（1画面コード入力。admin=uneiairi0931のみ） =========
def auth_ui() -> bool:
    if st.session_state._auth_ok: return True
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 🔐 入室コードを入力")
        code = st.text_input("アクセスコード（※運営は専用コード）", type="password", key="auth_code")
        nick = st.text_input("ニックネーム（利用者のみ・任意）", value="", key="auth_nick")
        if st.button("➡️ 入る", type="primary", key="auth_enter"):
            if code.strip() == "":
                st.warning("アクセスコードをご入力ください。")
            elif code.strip() == admin_pass():
                st.session_state.user_id = "_admin_"
                st.session_state.role = "admin"
                st.session_state._auth_ok = True
                st.success("運営ログインが完了しました。")
                st.session_state.view = "ADMIN"
                return True
            else:
                st.session_state.user_id = (nick.strip() or "user")
                st.session_state.role = "user"
                st.session_state._auth_ok = True
                st.success("ようこそ。")
                st.session_state.view = "HOME"
                return True
        st.markdown("</div>", unsafe_allow_html=True)
    return False

def logout_btn():
    with st.sidebar:
        if st.button("🚪 ログアウト", key="logout_btn"):
            st.session_state.clear()
            st.rerun()

# ========= App =========
if auth_ui():
    logout_btn()
    top_tabs()
    top_status()
    main_router()
