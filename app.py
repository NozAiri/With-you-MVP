# app.py — Sora / With You.（HOME=説明＋下段ボタンのみ／やさしいフォント／グラデ）
# 要望対応：
# ・HOME 上段タブは非表示、下段ボタンのみ。タイトルは太字。柔らかフォント＋おしゃれグラデ。
# ・ノート：専門用語を出さない文面に変更。最後は“日記”。保存は端末のみ（DL＋このセッション内の履歴）。
# ・リラックス：NameError対策で関数定義を維持。記録は端末のみ。
# ・相談：相談内容カテゴリを選択可。匿名送信をユーザーが選択。これはFirestoreに送信（運営が把握）。
# ・運営が把握＝Firestore保存は「今日を伝える」「相談」のみ。他は端末内（DL＋セッション履歴）。
# ・レビュー：端末内の履歴（このセッションで記録した分）を表示。

from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import pandas as pd
import streamlit as st
import json, time, re, os
import altair as alt

# ==== Firestore（運営が把握する2機能のみ利用） ====
from google.cloud import firestore
import google.oauth2.service_account as service_account

# ===== Page config =====
st.set_page_config(page_title="With You.", page_icon="🌙", layout="centered", initial_sidebar_state="collapsed")

# ===== Fonts / Styles =====
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
.item{ background:#fff; border:1px solid var(--panel-brd); border-radius:18px; padding:16px; box-shadow:var(--shadow) }
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

/* ------- emotion pills ------- */
.emopills{display:grid; grid-template-columns:repeat(3,1fr); gap:10px}
@media (min-width:820px){ .emopills{ grid-template-columns:repeat(6,1fr) } }
.emopills .chip .stButton>button{
  background:linear-gradient(135deg,#ffffff 0%,#eef5ff 100%) !important; color:#1d3457 !important;
  border:2px solid #d6e7ff !important; border-radius:16px !important;
  box-shadow:0 6px 16px rgba(100,140,200,.08) !important; font-weight:900 !important; padding:12px 12px !important;
}
.emopills .chip.on .stButton>button{ border:2px solid #5EA3FF !important; background:#eefdff !important }

/* ------- progress ------- */
.prog{height:12px; background:#eef4ff; border-radius:999px; overflow:hidden}
.prog > div{height:12px; background:#96BDFF}

/* ------- CBT cards（用語ラベルは使わない） ------- */
.cbt-card{ background:#fff; border:1px solid #e3e8ff; border-radius:18px; padding:18px 18px 14px; box-shadow:0 6px 20px rgba(31,59,179,0.06); margin-bottom:14px; }
.cbt-heading{ font-weight:900; font-size:1.05rem; color:#1b2440; margin:0 0 6px 0;}
.cbt-sub{ color:#63728a; font-size:0.92rem; margin:-2px 0 10px 0;}
.ok-chip{ display:inline-block; padding:2px 8px; border-radius:999px; background:#e8fff3; color:#156f3a; font-size:12px; border:1px solid #b9f3cf; }
</style>
""", unsafe_allow_html=True)

inject_css()

# ===== Firestore client（今日を伝える/相談のみ） =====
def firestore_client():
    creds = service_account.Credentials.from_service_account_info(st.secrets["FIREBASE_SERVICE_ACCOUNT"])
    return firestore.Client(project=st.secrets["FIREBASE_SERVICE_ACCOUNT"]["project_id"], credentials=creds)

DB = firestore_client()

# ===== Local（端末＝このセッションに保存する辞書） =====
def init_local_logs():
    st.session_state.setdefault("_local_logs", {"note":[], "breath":[], "study":[]})
init_local_logs()

# ===== Utils / State =====
def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

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
    if not text: return False
    for p in CRISIS:
        if re.search(p, text): return True
    return False

# ===== Nav (Top Tabs) =====
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
    if st.session_state.view == "HOME":  # HOMEでは表示しない
        return
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
    st.markdown(f"<div class='tip'>ログイン中：{'運営' if st.session_state.role=='admin' else f'利用者（{st.session_state.user_id}）'}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ===== Small helpers =====
def home_big_button(title: str, sub: str, target_view: str, key: str, emoji: str):
    label = f"{emoji} {title}\n{sub}"   # 1行目=タイトル（CSSで太字）
    with st.container():
        st.markdown('<div class="bigbtn">', unsafe_allow_html=True)
        if st.button(label, key=key):
            navigate(target_view, push=True); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

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

# ===== HOME =====
def home_intro_block():
    st.markdown("""
<div class="card" style="margin-bottom:12px">
  <div style="font-weight:900; font-size:1.05rem; margin-bottom:.3rem">🌙 With You について</div>
  <div style="color:#3a4a6a; line-height:1.65; white-space:pre-wrap">
毎日の気持ちを整えて、必要なときに先生や周りとつながれる、やさしいツールボックスです。
いまの自分に合いそうなカードを選んで、短い時間からはじめてみてください。
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

# ===== リラックス（呼吸） =====
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
        if st.button("⏹ 停止する", key="breath_stop"):
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
    after = st.slider("いまの気分（1 とてもつらい / 10 とても楽）", 1, 10, 5)
    if st.button("💾 端末に保存（このセッション内）", type="primary"):
        st.session_state["_local_logs"]["breath"].append({
            "ts": now_iso(), "pattern": "5-2-6", "mood_after": int(after), "sec": 90
        })
        # 端末保存（ダウンロード）
        doc = st.session_state["_local_logs"]["breath"][-1]
        st.download_button("⬇️ この記録をダウンロード（JSON）",
                           data=json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8"),
                           file_name=f"breath_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                           mime="application/json", key=f"breath_dl_{len(st.session_state['_local_logs']['breath'])}")
        st.success("保存しました。（運営には共有されません）")

# ===== ノート（CBT風・専門用語なし） =====
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
ACTION_LIB = {
    "sad":       ["好きな音楽を1曲聴く","温かい飲み物をゆっくり飲む","“できたこと”を3つ書く"],
    "anger":     ["深呼吸×3回","その場を少し離れる","手をぎゅっと握ってから開く×5回"],
    "anx":       ["4-4-6で深呼吸×3","不安を1行だけ書いて“今できる1つ”を丸で囲む","安心できる人にスタンプだけ送る"],
    "lonely":    ["5分だけ散歩","好きな人に“元気？”と一言送る","毛布にくるまって目を閉じる1分"],
    "tired":     ["肩回し×10回","水を一杯飲む","5分だけ横になる（タイマー）"],
    "relief":    ["今日の“よかったこと”を1つメモ","深呼吸しながら背伸び","好きな香りをかぐ"],
    "joy":       ["嬉しかった理由を一言メモ","誰かに良いことをシェア","写真を1枚撮る"],
    "confuse":   ["頭に浮かぶことを30秒だけ書く","軽くストレッチ","“今やること”を1つだけ決める"],
}

def cbt_intro_block():
    st.markdown("""
<div class="cbt-card">
  <div class="cbt-heading">このワークについて</div>
  <div class="cbt-sub" style="white-space:pre-wrap">
このワークは、認知行動療法（CBT）という考え方をもとにしています。
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

# ===== 行動活性化：中高生向けの小さな行動ライブラリ =====
# 研究で推奨される「落ち着かせる/少し楽しい/つながる/書く」の4タイプをミニマムに統合
ACTION_LIB_BASE = [
    "深呼吸をしてみる",                # 落ち着かせる
    "顔や手を洗う",                    # 感覚リセット
    "外を少し歩く・空を見上げる",      # 軽い活動
    "好きな音楽を1曲だけ聴く",        # 少し楽しい
    "温かい飲み物を飲む",              # 身体×安心
    "軽く体を伸ばす",                  # ストレッチ
    "家族や友達に一言だけ話す",        # つながる
    "スタンプや一言メッセージを送る",  # 手軽な接触
    "今の気持ちを一言メモする",        # 書く
    "今日できたことを1つ思い出す",    # 達成感の想起
]

# 気分別の“相性が良い”候補（行動活性化の適合原則）
ACTION_BY_MOOD = {
    # 落ち込み：活動量↑と小さな達成感
    "sad": ["外を少し歩く・空を見上げる", "今日できたことを1つ思い出す", "軽く体を伸ばす"],
    # 不安：呼吸・感覚の安定＋安全行動の縮小
    "anxious": ["深呼吸をしてみる", "温かい飲み物を飲む", "今の気持ちを一言メモする"],
    # イライラ：身体の放電＋注意の切替
    "angry": ["軽く体を伸ばす", "顔や手を洗う", "好きな音楽を1曲だけ聴く"],
    # だるい・疲れ：低コスト行動→次の一歩
    "tired": ["温かい飲み物を飲む", "外を少し歩く・空を見上げる", "今日できたことを1つ思い出す"],
    # さみしい：社会的接触の再起動
    "lonely": ["家族や友達に一言だけ話す", "スタンプや一言メッセージを送る", "好きな音楽を1曲だけ聴く"],
    # 迷った時のデフォルト
    "default": ["深呼吸をしてみる", "今の気持ちを一言メモする", "温かい飲み物を飲む"],
}

def action_picker(mood_key: str):
    import random
    st.markdown('<div class="cbt-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="cbt-heading">🌸 Step 6：今、気持ちが少し落ち着くためにできそうなことは？</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="cbt-sub">自分に合いそうな「小さな行動」をひとつ選んでみよう。（任意）</div>',
        unsafe_allow_html=True,
    )

    # 気分に合う候補＋ベースを統合し、重複除去
    mood_key = (mood_key or "").strip().lower()
    mood_list = ACTION_BY_MOOD.get(mood_key, ACTION_BY_MOOD["default"])
    pool = list(dict.fromkeys(mood_list + ACTION_LIB_BASE))  # 順序保持でユニーク化

    # 3件だけおすすめ表示（選びやすさ優先）／poolが少なければその分だけ
    k = min(3, len(pool))
    recommended = random.sample(pool, k) if k > 0 else []

    # セレクトボックス（キーはmood別で一意に）
    select_key = f"act_pick_{mood_key or 'default'}"
    selected = st.selectbox(
        "おすすめから選ぶ",
        ["— 選ばない —"] + recommended,
        index=0,
        key=select_key,
    )

    # 自由入力（例示は“現実的で小さい行動”）
    custom_key = f"act_custom_{mood_key or 'default'}"
    custom = st.text_input(
        "自由入力",
        key=custom_key,
        placeholder="例：外を少し歩く・空を見上げる",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # 返り値：選択＞自由入力（空白は除去）
    chosen = "" if selected == "— 選ばない —" else selected
    custom = (custom or "").strip()
    return chosen, custom


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
            "trigger_text": trigger_text.strip(),
            "auto_thought": auto_thought.strip(),
            "reason_for": reason_for.strip(),
            "reason_against": reason_against.strip(),
            "alt_perspective": alt_perspective.strip(),
            "action_suggested": act_suggested.strip(),
            "action_custom": act_custom.strip(),
            "reflection": reflection.strip(),
            "meta": {"version":"cbt-note-v1","source":"with-you/streamlit"}
        }
        # 端末（このセッション）に保存
        st.session_state["_local_logs"]["note"].append(doc)
        recap_card(doc)
        # ダウンロード
        st.download_button("⬇️ この記録をダウンロード（JSON）",
                           data=json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8"),
                           file_name=f"cbt_journal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                           mime="application/json", key=f"cbt_dl_{len(st.session_state['_local_logs']['note'])}")
        st.success("保存しました。（運営には共有されません）")

# ===== 今日を伝える（Firestoreに保存：運営が把握） =====
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
    st.markdown(f"""
<div class="item">
  <div class="meta">{datetime.now().astimezone().isoformat(timespec="seconds")}</div>
  <div style="font-weight:900; color:#24466e; margin-bottom:.3rem">本日の共有内容</div>
  <div style="margin:.2rem 0;">気分：<span class="badge">{mood}</span></div>
  <div style="margin:.2rem 0;">体調：{"".join([f"<span class='badge'>{b}</span>" for b in (body or ['なし'])])}</div>
  <div style="margin:.2rem 0;">睡眠：<b>{sh:.1f} 時間</b> / 質：<span class="badge">{sq}</span></div>
</div>
""", unsafe_allow_html=True)

    if st.button("📨 送信（匿名）", type="primary", key="share_submit"):
        DB.collection("school_share").add({
            "ts": datetime.now(timezone.utc),
            "user_id": st.session_state.user_id,
            "payload": {"mood":mood, "body":body, "sleep_hours":float(sh), "sleep_quality":sq},
            "anonymous": True
        })
        st.success("送信しました。ありがとうございます。")

# ===== 相談（Firestoreに保存：運営が把握） =====
CONSULT_TOPICS = ["体調","勉強","人間関係","家庭","進路","いじめ","メンタルの不調","その他"]

def view_consult():
    st.markdown("### 🕊 相談")
    st.caption("お気軽に。秘密は守ります。お名前は任意です。")

    to_whom = st.radio("相談先を選んでください", ["カウンセラーに相談したい", "先生に伝えたい"], horizontal=True, key="c_to")
    topics  = st.multiselect("内容（当てはまるもの）", CONSULT_TOPICS, default=[], key="c_topics")
    anonymous = st.checkbox("匿名で送る", value=True, key="c_anon")
    name = "" if anonymous else st.text_input("お名前（任意）", value="", key="c_name")
    msg = st.text_area("ご相談したい／伝えたい内容について教えてください。", height=220, value=st.session_state.get("c_msg",""), key="c_msg")

    if crisis(msg):
        st.warning("とても苦しいお気持ちが伝わってきます。必要に応じて、お住まいの地域の相談窓口や専門機関もご検討ください。")

    if st.button("🕊 送信する", type="primary", disabled=(msg.strip()==""), key="c_submit"):
        payload = {
            "ts": datetime.now(timezone.utc),
            "user_id": st.session_state.user_id,
            "message": msg.strip(),
            "topics": topics,
            "intent": "counselor" if to_whom.startswith("カウンセラー") else "teacher",
            "anonymous": bool(anonymous),
            "name": name.strip() if name else "",
        }
        DB.collection("consult_msgs").add(payload)
        st.success("送信しました。ありがとうございます。")

# ===== Study（端末のみ保存） =====
def view_study():
    st.markdown("### 📚 Study Tracker")
    uid = st.session_state.user_id
    # 簡易：科目は入力・選択（端末保存のみ）
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

# ===== ふりかえり（端末＝このセッションの履歴を表示） =====
def view_review():
    st.markdown("### 📒 ふりかえり（このセッションの履歴）")
    logs = st.session_state["_local_logs"]

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
            # 円グラフ
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

# ===== Router =====
def main_router():
    v = st.session_state.view
    if v == "HOME":   view_home()
    elif v == "SESSION": view_session()        # ← NameError対策：必ず存在
    elif v == "NOTE": view_note()
    elif v == "SHARE": view_share()
    elif v == "CONSULT": view_consult()
    elif v == "REVIEW": view_review()
    elif v == "STUDY": view_study()
    else: view_home()

# ===== Auth =====
def auth_ui() -> bool:
    if st.session_state._auth_ok: return True
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 🔐 ログイン")
        t1, t2 = st.tabs(["利用者として入る", "運営として入る"])
        with t1:
            uid = st.text_input("ユーザーID", placeholder="例: omu-2025-xxxx")
            if st.button("➡️ 入る（利用者）", type="primary"):
                if uid.strip() == "": st.warning("ユーザーIDをご入力ください。")
                else:
                    st.session_state.user_id = uid.strip(); st.session_state.role = "user"
                    st.session_state._auth_ok = True; st.success("ようこそ。"); return True
        with t2:
            pw = st.text_input("運営パスコード", type="password")
            if st.button("➡️ 入る（運営）"):
                if pw == admin_pass():
                    st.session_state.user_id = "_admin_"; st.session_state.role = "admin"
                    st.session_state._auth_ok = True; st.success("運営ログインが完了しました。"); return True
                else: st.error("パスコードが違います。")
        st.markdown("</div>", unsafe_allow_html=True)
    return False

def logout_btn():
    with st.sidebar:
        if st.button("🚪 ログアウト"):
            st.session_state.clear()
            st.rerun()

# ===== App =====
if auth_ui():
    logout_btn()
    top_tabs()
    top_status()
    main_router()
