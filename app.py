# app.py — Sora（2分ノート + 呼吸）安全保存版
# 目的：
#  1) 短時間で「落ち着く → 考えを整える → 今日の行動」へつなぐ
#  2) CSV保存（書き込み失敗時も落ちず、メモリ保持とDLで担保）
#  3) やさしいUI（ガラス調）＋敬語・専門用語なし

from datetime import datetime, date, timezone, timedelta
from pathlib import Path
from typing import Optional, List
import pandas as pd
import streamlit as st
import json, uuid, time, io, os

# ---------------- Page config ----------------
st.set_page_config(
    page_title="Sora — 2分ノートと呼吸",
    page_icon="🌙",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------- Theme / CSS ----------------
def inject_css():
    st.markdown("""
<style>
:root{
  --text:#2a2731; --muted:#6f7180;
  --glass:rgba(255,255,255,.94); --glass-brd:rgba(185,170,255,.28);
  --outline:#e9ddff;
  --grad-from:#ffa16d; --grad-to:#ff77a3;
  --chip:#fff6fb; --chip-brd:#ffd7f0;

  --tile-a:#ffb37c; --tile-b:#ffe0c2;
  --tile-c:#ff9ec3; --tile-d:#ffd6ea;
  --tile-e:#c4a4ff; --tile-f:#e8dbff;
  --tile-g:#89d7ff; --tile-h:#d4f2ff;
}

.stApp{
  background:
    radial-gradient(820px 520px at 0% -10%,  rgba(255,226,200,.55) 0%, transparent 60%),
    radial-gradient(780px 480px at 100% -8%, rgba(255,215,242,.55) 0%, transparent 60%),
    radial-gradient(960px 560px at -10% 98%, rgba(232,216,255,.45) 0%, transparent 60%),
    radial-gradient(960px 560px at 110% 100%, rgba(217,245,255,.46) 0%, transparent 60%),
    linear-gradient(180deg, #fffefd 0%, #fff8fb 28%, #f7f3ff 58%, #f2fbff 100%);
}
/* 静かな星 */
.stApp:before{
  content:""; position:fixed; inset:0; pointer-events:none; z-index:0;
  background-image:
    radial-gradient(circle, rgba(255,255,255,.65) 0.6px, transparent 1px),
    radial-gradient(circle, rgba(255,255,255,.35) 0.5px, transparent 1px);
  background-size: 22px 22px, 34px 34px;
  background-position: 0 0, 10px 12px;
  opacity:.18;
}
.block-container{max-width:960px; padding-top:1rem; padding-bottom:2rem; position:relative; z-index:1}
h1,h2,h3{color:var(--text); letter-spacing:.2px}
p,label,.stMarkdown,.stTextInput,.stTextArea{color:var(--text); font-size:1.05rem}
small{color:var(--muted)}
.card{
  background:var(--glass); border:1px solid var(--glass-brd);
  border-radius:20px; padding:16px; margin-bottom:14px;
  box-shadow:0 18px 36px rgba(80,70,120,.14); backdrop-filter:blur(8px);
}
.hr{height:1px; background:linear-gradient(to right,transparent,#c7b8ff,transparent); margin:12px 0 10px}

/* 主ボタン（グラデ） */
.stButton>button,.stDownloadButton>button{
  width:100%; padding:14px 16px; border-radius:999px; border:1px solid var(--outline);
  background:linear-gradient(180deg,var(--grad-from),var(--grad-to)); color:#fff; font-weight:900; font-size:1.04rem;
  box-shadow:0 12px 26px rgba(255,145,175,.22);
}
.stButton>button:hover{filter:brightness(.98)}

/* ナビ（白ゴースト） */
.topbar{ position:sticky; top:0; z-index:10; background:rgba(255,255,255,.7); backdrop-filter:blur(8px);
  border-bottom:1px solid #ececff; margin:0 -12px 10px; padding:8px 12px; }
.topnav{display:flex; gap:8px; flex-wrap:wrap; margin:4px 0 2px}
.topnav .nav-btn>button{
  background:#ffffff !important; color:#2d2a33 !important; border:1px solid #d9dbe8 !important;
  box-shadow:none !important; height:auto !important; padding:9px 12px !important;
  border-radius:12px !important; font-weight:700 !important; font-size:.95rem !important; letter-spacing:.1px;
}
.topnav .nav-btn>button:hover{background:#f6f7ff !important; filter:none !important;}
.topnav .active>button{ background:#f4f3ff !important; border:2px solid #7d74ff !important; }
.nav-hint{font-size:.78rem; color:#9aa; margin:0 2px 4px 2px}

/* 選択UI */
.chips{display:flex; gap:8px; flex-wrap:wrap; margin:8px 0 10px}
.chips .chip-btn>button{
  background:linear-gradient(180deg,#ffd8e9,#ffc4e1); color:#523a6a;
  border:1px solid var(--chip-brd)!important; padding:10px 14px; height:auto;
  border-radius:999px!important; font-weight:900; box-shadow:0 10px 20px rgba(60,45,90,.08)
}
/* Emoji grid */
.emoji-grid{display:grid; grid-template-columns:repeat(8,1fr); gap:10px; margin:8px 0 6px}
.emoji-btn>button{
  width:100%!important; aspect-ratio:1/1; border-radius:18px!important;
  font-size:1.55rem!important; background:#fff; border:1px solid #eadfff!important;
  box-shadow:0 8px 16px rgba(60,45,90,.06);
}
.emoji-on>button{
  background:linear-gradient(180deg,#ffc6a3,#ff9fbe)!important;
  border:1px solid #ff80b0!important;
}
/* ホームタイル */
.tile-grid{display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:8px}
.tile .stButton>button{
  aspect-ratio:1/1; min-height:220px; border-radius:28px;
  text-align:left; padding:20px; white-space:normal; line-height:1.2;
  border:none; font-weight:900; font-size:1.18rem; color:#2d2a33;
  box-shadow:0 20px 36px rgba(60,45,90,.18); display:flex; align-items:flex-end; justify-content:flex-start;
}
.tile-a .stButton>button{background:linear-gradient(160deg,var(--tile-a),var(--tile-b))}
.tile-b .stButton>button{background:linear-gradient(160deg,var(--tile-c),var(--tile-d))}
.tile-c .stButton>button{background:linear-gradient(160deg,var(--tile-e),var(--tile-f))}
.tile-d .stButton>button{background:linear-gradient(160deg,var(--tile-g),var(--tile-h))}

/* 呼吸フェーズ */
.phase-pill{ display:inline-block; padding:.2rem .75rem; border-radius:999px;
  background:rgba(125,116,255,.12); color:#5d55ff; border:1px solid rgba(125,116,255,.35);
  margin-bottom:6px; font-weight:700; }
.count-box{ font-size:42px; font-weight:900; text-align:center; color:#2f2a3b; padding:6px 0 2px; }

/* モバイル */
@media (max-width: 840px){ .emoji-grid{grid-template-columns:repeat(6,1fr)} }
@media (max-width: 640px){
  .emoji-grid{grid-template-columns:repeat(4,1fr)}
  .tile-grid{grid-template-columns:1fr}
  .tile .stButton>button{min-height:180px}
  .block-container{padding-left:1rem; padding-right:1rem}
}
</style>
""", unsafe_allow_html=True)

inject_css()

# ---------------- 保存まわり（CSV + メモリ維持） ----------------
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
CBT_CSV = DATA_DIR / "cbt_entries.csv"
REFLECT_CSV = DATA_DIR / "daily_reflections.csv"
BREATH_CSV = DATA_DIR / "breathing_entries.csv"

# 書き込めない環境でも落とさない
def _load_csv(p: Path) -> pd.DataFrame:
    if p.exists():
        try:
            return pd.read_csv(p)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

def _append_csv_safe(p: Path, row: dict) -> bool:
    try:
        df = _load_csv(p)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        df.to_csv(p, index=False)
        return True
    except Exception:
        # 書き込み失敗時はFalseを返す（UI側で通知し、メモリ保持）
        return False

def _download_button(df: pd.DataFrame, label: str, filename: str):
    if df.empty:
        st.caption("（まだデータはございません）")
        return
    st.download_button(label, df.to_csv(index=False).encode("utf-8"),
                       file_name=filename, mime="text/csv")

# ---------------- セッション初期値 ----------------
if "view" not in st.session_state:
    st.session_state.view = "INTRO"
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
if "mem_records" not in st.session_state:
    st.session_state.mem_records = {"cbt": [], "reflect": [], "breath": []}

def ensure_cbt_defaults():
    st.session_state.setdefault("cbt", {})
    cbt = st.session_state.cbt
    cbt.setdefault("emotions", [])
    cbt.setdefault("trigger_tags", [])
    cbt.setdefault("trigger_free","")
    cbt.setdefault("fact","")
    cbt.setdefault("alt","")
    cbt.setdefault("checks", {"bw":False,"catastrophe":False,"fortune":False,"emotion":False,"decide":False})
    cbt.setdefault("distress_before",5)
    cbt.setdefault("prob_before",50)
    cbt.setdefault("rephrase","")
    cbt.setdefault("prob_after",40)
    cbt.setdefault("distress_after",4)

def ensure_reflection_defaults():
    st.session_state.setdefault("reflection", {})
    r = st.session_state.reflection
    r.setdefault("today_small_win","")
    r.setdefault("self_message","")
    r.setdefault("note_for_tomorrow","")
    r.setdefault("loneliness",5)
    d = r.get("date", date.today())
    if isinstance(d, str):
        try: d = date.fromisoformat(d)
        except Exception: d = date.today()
    r["date"] = d

ensure_cbt_defaults(); ensure_reflection_defaults()

# ---------------- UIヘルパー ----------------
def companion(emoji: str, text: str, sub: Optional[str]=None):
    st.markdown(
        f"""
<div class="card">
  <div style="font-weight:900; color:#2f2a3b">{emoji} {text}</div>
  {f"<div class='small' style='margin-top:4px; color:var(--muted)'>{sub}</div>" if sub else ""}
</div>""",
        unsafe_allow_html=True,
    )

def vibrate(ms=12):
    st.markdown("<script>try{navigator.vibrate&&navigator.vibrate(%d)}catch(e){{}}</script>"%ms,
                unsafe_allow_html=True)

def top_nav():
    st.markdown('<div class="topbar">', unsafe_allow_html=True)
    st.markdown('<div class="nav-hint">ページ移動</div>', unsafe_allow_html=True)
    st.markdown('<div class="topnav">', unsafe_allow_html=True)
    pages = [("INTRO","👋 はじめに"),("HOME","🏠 ホーム"),
             ("BREATH","🌬 呼吸"),("CBT","📓 2分ノート"),
             ("REFLECT","📝 1日のふり返り"),("HISTORY","📚 記録を見る"),("EXPORT","⬇️ エクスポート")]
    cols = st.columns(len(pages))
    for i,(key,label) in enumerate(pages):
        cls = "nav-btn active" if st.session_state.view==key else "nav-btn"
        with cols[i]:
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.view = key
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

# Emoji / Chips
EMOJIS = ["😟","😡","😢","😔","😤","😴","🙂","🤷‍♀️"]
TRIGGER_DEFS = [
    ("⏱️ さっきの出来事", "time"),
    ("🧠 浮かんだ一言", "thought_line"),
    ("🤝 人との関係", "relationship"),
    ("🫀 体のサイン", "body"),
    ("🌀 うまく言えない", "unknown"),
]

def emoji_toggle_grid(selected: List[str]) -> List[str]:
    st.caption("いまの気持ちをタップ（複数OK／途中でやめてもOK）")
    st.markdown('<div class="emoji-grid">', unsafe_allow_html=True)
    chosen = set(selected)
    cols = st.columns(8 if len(EMOJIS) >= 8 else len(EMOJIS))
    for i, e in enumerate(EMOJIS):
        with cols[i % len(cols)]:
            on = e in chosen
            cls = "emoji-btn emoji-on" if on else "emoji-btn"
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(f"{e}", key=f"emo_{i}", use_container_width=True):
                if on: chosen.remove(e)
                else: chosen.add(e)
                vibrate(10)
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.caption("選択中：" + (" ".join(list(chosen)) if chosen else "（未選択）"))
    return list(chosen)

def trigger_chip_row(selected: List[str]) -> List[str]:
    st.caption("言葉にしづらい時は、近いものだけタップで結構です。")
    st.markdown('<div class="chips">', unsafe_allow_html=True)
    cols = st.columns(len(TRIGGER_DEFS))
    chosen = set(selected)
    for i,(label,val) in enumerate(TRIGGER_DEFS):
        with cols[i]:
            on = val in chosen
            st.markdown('<div class="chip-btn">', unsafe_allow_html=True)
            if st.button(label + (" ✓" if on else ""), key=f"trg_{val}", use_container_width=True):
                if on: chosen.remove(val)
                else: chosen.add(val)
                vibrate(8)
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    return list(chosen)

def append_to_textarea(ss_key: str, phrase: str):
    cur = st.session_state.cbt.get(ss_key, "") or ""
    glue = "" if (cur.strip() == "" or cur.strip().endswith(("。","!","！"))) else " "
    st.session_state.cbt[ss_key] = (cur + glue + phrase).strip()

CHECK_LABELS = {
    "bw":          "0/100で考えていたかも",
    "catastrophe": "最悪の状態を想定していたかも",
    "fortune":     "先の展開を一つに決めていたかも",
    "emotion":     "感情が先に走っているかも",
    "decide":      "決めつけてしまっていたかも",
}
TIP_MAP = {
    "bw":          "部分的にOKも、あるかもしれません。",
    "catastrophe": "他の展開もあるかもしれません。",
    "fortune":     "他の展開になればラッキーですね。",
    "emotion":     "気持ちはそのまま、事実はそっと分けておくのもありです。",
    "decide":      "分からない場合はいったん保留にするのもありですね。",
}

def render_checks_and_tips():
    g = st.session_state.cbt.setdefault("checks", {})
    cols = st.columns(2)
    keys = list(CHECK_LABELS.keys())
    for i, k in enumerate(keys):
        with cols[i % 2]:
            g[k] = st.checkbox(CHECK_LABELS[k], value=bool(g.get(k, False)))
    st.session_state.cbt["checks"] = g

    on_keys = [k for k,v in g.items() if v]
    if on_keys:
        st.write("💡 タップで“ほかの見方”に挿入できます")
        st.markdown('<div class="chips">', unsafe_allow_html=True)
        tip_cols = st.columns(min(4, len(on_keys)))
        for i, k in enumerate(on_keys):
            tip = TIP_MAP.get(k, "")
            if not tip: continue
            with tip_cols[i % len(tip_cols)]:
                st.markdown('<div class="chip-btn">', unsafe_allow_html=True)
                if st.button(tip, key=f"tip_{k}", use_container_width=True):
                    append_to_textarea("alt", tip)
                    vibrate(8)
                st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ---------------- 各画面 ----------------
def view_intro():
    top_nav()
    st.markdown("""
<div class="card" style="padding:22px;">
  <h2 style="margin:.1rem 0 .6rem; color:#2f2a3b;">
    いま感じていることを、<b>いっしょに静かに整えます。</b>
  </h2>
  <ul style="margin:.4rem 0 .6rem;">
    <li>⏱ <b>所要</b>：約2分 ／ <b>3ステップ</b></li>
    <li>🎯 <b>内容</b>：気持ち → きっかけ → 見方の仮置き</li>
    <li>🔒 <b>安心</b>：この端末のみ保存／途中でやめてもOK／医療・診断ではありません</li>
  </ul>
  <p style="margin:.2rem 0 .2rem; color:#6f7180">空欄があっても大丈夫です。</p>
</div>
""", unsafe_allow_html=True)
    cta1, cta2, cta3 = st.columns([3,2,2])
    with cta1:
        if st.button("今すぐはじめる（約2分）", use_container_width=True):
            st.session_state.view = "CBT"
    with cta2:
        if st.button("呼吸からはじめる", use_container_width=True):
            st.session_state.view = "BREATH"
    with cta3:
        if st.button("ホームを見る", use_container_width=True):
            st.session_state.view = "HOME"

def view_home():
    top_nav()
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 本日、どのように進められますか？")
    st.markdown('<div class="tile-grid">', unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1:
        st.markdown('<div class="tile tile-a">', unsafe_allow_html=True)
        if st.button("📓 2分ノート", key="tile_cbt"): st.session_state.view="CBT"
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="tile tile-b">', unsafe_allow_html=True)
        if st.button("🌬 呼吸で落ち着く", key="tile_breath"): st.session_state.view="BREATH"
        st.markdown('</div>', unsafe_allow_html=True)
    c3,c4 = st.columns(2)
    with c3:
        st.markdown('<div class="tile tile-c">', unsafe_allow_html=True)
        if st.button("📝 1日のふり返り", key="tile_ref"): st.session_state.view="REFLECT"
        st.markdown('</div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="tile tile-d">', unsafe_allow_html=True)
        if st.button("📚 記録を見る", key="tile_hist"): st.session_state.view="HISTORY"
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

def view_breath():
    top_nav()
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("呼吸で落ち着く（約1分）")
    st.caption("1サイクル＝吸う → 止める → 吐く → 止める。無理のない回数で結構です。")

    preset = st.selectbox("サイクル（秒）",
                          ["4-2-4-2（標準）", "3-1-5-1（軽め）", "4-4-4-4（均等）"], index=0)
    if "3-1-5-1" in preset:
        inhale, hold1, exhale, hold2 = 3, 1, 5, 1
    elif "4-4-4-4" in preset:
        inhale, hold1, exhale, hold2 = 4, 4, 4, 4
    else:
        inhale, hold1, exhale, hold2 = 4, 2, 4, 2

    sets = st.slider("回数（推奨：2回）", min_value=1, max_value=4, value=2, step=1)

    colA, colB = st.columns(2)
    with colA: start = st.button("開始", use_container_width=True)
    with colB: reset = st.button("リセット", use_container_width=True)

    phase_box = st.empty()
    count_box = st.empty()
    prog = st.progress(0)

    if reset:
        st.experimental_rerun()

    if start:
        total = sets * (inhale + hold1 + exhale + hold2)
        elapsed = 0
        phases = [("吸気", inhale), ("停止", hold1), ("呼気", exhale), ("停止", hold2)]
        for _ in range(sets):
            for name, seconds in phases:
                if seconds <= 0: continue
                phase_box.markdown(f"<div class='phase-pill'>{name}</div>", unsafe_allow_html=True)
                for t in range(seconds, 0, -1):
                    count_box.markdown(f"<div class='count-box'>{t}</div>", unsafe_allow_html=True)
                    elapsed += 1
                    prog.progress(min(int(elapsed / total * 100), 100))
                    time.sleep(1)
        phase_box.markdown("<div class='phase-pill'>完了</div>", unsafe_allow_html=True)
        count_box.markdown("<div class='count-box'>お疲れさまでした。</div>", unsafe_allow_html=True)

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    st.subheader("メモ（任意）")
    note = st.text_input("現在の状態（短文で結構です）", placeholder="例：少し落ち着いた／まだ緊張が残る など")
    if st.button("保存する", type="primary"):
        now = datetime.now().isoformat(timespec="seconds")
        row = {"id":f"breath-{now}","ts":now,"pattern":f"{inhale}-{hold1}-{exhale}-{hold2}",
               "sets":sets,"note":note}
        ok = _append_csv_safe(BREATH_CSV, row)
        st.session_state.mem_records["breath"].append(row)
        if ok:
            st.success("保存いたしました。")
        else:
            st.warning("保存先に書き込めませんでした。この起動中は記録されています。エクスポートからCSVをダウンロードしてください。")
    st.markdown('</div>', unsafe_allow_html=True)

def view_cbt():
    ensure_cbt_defaults()
    top_nav()

    # Step0 感情
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("いまの気持ち")
    st.session_state.cbt["emotions"] = emoji_toggle_grid(
        st.session_state.cbt.get("emotions", [])
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # Step1 きっかけ
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("この気持ち、近かったきっかけは？")
    st.session_state.cbt["trigger_tags"] = trigger_chip_row(
        st.session_state.cbt.get("trigger_tags", [])
    )
    st.session_state.cbt["trigger_free"] = st.text_area(
        "任意の一言（なくて大丈夫です）",
        value=st.session_state.cbt.get("trigger_free",""),
        placeholder="例）返信がまだ／『また失敗する』と浮かんだ など",
        height=72
    )
    cols = st.columns(2)
    with cols[0]:
        st.session_state.cbt["distress_before"] = st.slider("いまのしんどさ（0〜10）", 0, 10, int(st.session_state.cbt.get("distress_before",5)))
    with cols[1]:
        st.session_state.cbt["prob_before"] = st.slider("いまの考えは、どのくらい“ありえそう”？（%）", 0, 100, int(st.session_state.cbt.get("prob_before",50)))
    companion("🌟","ここまでで十分です。","短くても大丈夫です。")
    st.markdown('</div>', unsafe_allow_html=True)

    # Step2 整理（いまの見方 ↔ ほかの見方）
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("考えを整理する（いまの見方 ↔ ほかの見方）")
    st.caption("片方だけでも大丈夫です。短くてOK。")
    cols2 = st.columns(2)
    with cols2[0]:
        st.session_state.cbt["fact"] = st.text_area(
            "いまの見方",
            value=st.session_state.cbt.get("fact",""),
            placeholder="例）返事が遅い＝嫌われたかも など",
            height=108
        )
    with cols2[1]:
        st.session_state.cbt["alt"] = st.text_area(
            "ほかの見方（別の説明・例外）",
            value=st.session_state.cbt.get("alt",""),
            placeholder="例）移動中かも／前も夜に返ってきた など",
            height=108
        )
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    st.subheader("視界をひろげる小さなチェック")
    st.caption("当てはまるものだけ軽くオンに。合わなければスルーで結構です。")
    render_checks_and_tips()
    st.markdown('</div>', unsafe_allow_html=True)

    # Step3 仮の見方
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("いま採用しておく“仮の見方”を1行で")
    starters = [
        "分からない部分は保留にします。",
        "可能性は一つじゃないかもしれない。",
        "今ある事実の範囲で受け止めます。",
        "決め打ちはいったん止めておきます。"
    ]
    idx = st.radio("候補（編集可）", options=list(range(len(starters))),
                   format_func=lambda i: starters[i], index=0, horizontal=False)
    seed = starters[idx] if 0 <= idx < len(starters) else ""
    st.session_state.cbt["rephrase"] = st.text_area(
        "仮の見方（1行）",
        value=st.session_state.cbt.get("rephrase","") or seed,
        height=84
    )
    ccols = st.columns(2)
    with ccols[0]:
        st.session_state.cbt["prob_after"] = st.slider("この“仮の見方”のしっくり度（%）", 0, 100, int(st.session_state.cbt.get("prob_after",40)))
    with ccols[1]:
        st.session_state.cbt["distress_after"] = st.slider("いまのしんどさ（まとめた後）", 0, 10, int(st.session_state.cbt.get("distress_after",4)))
    st.markdown('</div>', unsafe_allow_html=True)

    # 保存・初期化
    c1,c2 = st.columns(2)
    with c1:
        if st.button("💾 保存して完了（入力欄を初期化）"):
            now = datetime.now().isoformat(timespec="seconds")
            g = st.session_state.cbt["checks"]
            row = {
                "id":f"cbt-{now}","ts":now,
                "emotions":" ".join(st.session_state.cbt.get("emotions",[])),
                "trigger_tags":" ".join(st.session_state.cbt.get("trigger_tags",[])),
                "trigger_free":st.session_state.cbt.get("trigger_free",""),
                "fact":st.session_state.cbt.get("fact",""),
                "alt":st.session_state.cbt.get("alt",""),
                "bw":g.get("bw",False),
                "catastrophe":g.get("catastrophe",False),
                "fortune":g.get("fortune",False),
                "emotion":g.get("emotion",False),
                "decide":g.get("decide",False),
                "distress_before":st.session_state.cbt.get("distress_before",0),
                "prob_before":st.session_state.cbt.get("prob_before",0),
                "rephrase":st.session_state.cbt.get("rephrase",""),
                "prob_after":st.session_state.cbt.get("prob_after",0),
                "distress_after":st.session_state.cbt.get("distress_after",0),
            }
            ok = _append_csv_safe(CBT_CSV,row)
            st.session_state.mem_records["cbt"].append(row)
            st.session_state.cbt = {}
            ensure_cbt_defaults()
            if ok:
                st.success("保存いたしました。ここで完了です。")
            else:
                st.warning("保存先に書き込めませんでした。この起動中は記録されています。エクスポートからCSVをダウンロードしてください。")
    with c2:
        if st.button("🧼 入力欄のみ初期化（未保存分は消去）"):
            st.session_state.cbt = {}
            ensure_cbt_defaults()
            st.info("入力欄を初期化いたしました（記録は残っています）。")

def view_reflect():
    ensure_reflection_defaults()
    top_nav()
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("本日をやさしくふり返る")
    st.caption("点数ではなく、心が少しやわらぐ表現で短くご記入ください。")
    st.session_state.reflection["date"] = st.date_input("日付", value=st.session_state.reflection["date"])
    st.session_state.reflection["today_small_win"] = st.text_area("本日できたことを1つだけ：",
        value=st.session_state.reflection.get("today_small_win",""), height=76)
    st.session_state.reflection["self_message"] = st.text_area("いまのご自身へ一言：",
        value=st.session_state.reflection.get("self_message",""), height=76)
    st.session_state.reflection["note_for_tomorrow"] = st.text_area("明日のご自身へのメモ（任意）：",
        value=st.session_state.reflection.get("note_for_tomorrow",""), height=76)
    st.session_state.reflection["loneliness"] = st.slider("いまの孤独感（0〜10）", 0, 10,
        int(st.session_state.reflection.get("loneliness",5)))
    st.markdown('</div>', unsafe_allow_html=True)

    c1,c2 = st.columns(2)
    with c1:
        if st.button("💾 保存（入力欄を初期化）"):
            now = datetime.now().isoformat(timespec="seconds")
            dv = st.session_state.reflection["date"]
            date_str = dv.isoformat() if isinstance(dv,(date,datetime)) else str(dv)
            row = {"id":f"ref-{now}","date":date_str,"ts_saved":now,
                   "small_win":st.session_state.reflection.get("today_small_win",""),
                   "self_message":st.session_state.reflection.get("self_message",""),
                   "note_for_tomorrow":st.session_state.reflection.get("note_for_tomorrow",""),
                   "loneliness":st.session_state.reflection.get("loneliness",0)}
            ok = _append_csv_safe(REFLECT_CSV,row)
            st.session_state.mem_records["reflect"].append(row)
            st.session_state.reflection = {}
            ensure_reflection_defaults()
            if ok: st.success("保存いたしました。")
            else:  st.warning("保存先に書き込めませんでした。この起動中は記録されています。エクスポートからCSVをダウンロードしてください。")
    with c2:
        if st.button("🧼 入力欄のみ初期化（未保存分は消去）"):
            st.session_state.reflection = {}
            ensure_reflection_defaults()
            st.info("入力欄を初期化いたしました（記録は残っています）。")

def view_history():
    top_nav()
    # 2分ノート
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📓 記録（2分ノート）")
    df_file = _load_csv(CBT_CSV)
    df_mem = pd.DataFrame(st.session_state.mem_records["cbt"])
    df = pd.concat([df_file, df_mem], ignore_index=True)
    if df.empty:
        st.caption("まだ保存されたノートはございません。")
    else:
        q = st.text_input("キーワード検索（見方・一言・きっかけ・感情）", "")
        view = df.copy()
        for c in ["fact","alt","rephrase","trigger_free","emotions","trigger_tags"]:
            if c in view.columns: view[c] = view[c].astype(str)
        if q.strip():
            ql = q.strip().lower()
            mask = False
            for c in ["fact","alt","rephrase","trigger_free","emotions","trigger_tags"]:
                if c in view.columns:
                    mask = mask | view[c].str.lower().str.contains(ql)
            view = view[mask]
        if "ts" in view.columns: view = view.sort_values("ts", ascending=False)
        for _, r in view.head(50).iterrows():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"**🕒 {r.get('ts','')}**")
            st.markdown(f"**感情**：{r.get('emotions','')}")
            st.markdown(f"**きっかけ**：{r.get('trigger_tags','')} ／ {r.get('trigger_free','')}")
            st.markdown(f"**いまの見方**：{r.get('fact','')}")
            st.markdown(f"**ほかの見方**：{r.get('alt','')}")
            st.markdown(f"**仮の見方**：{r.get('rephrase','')}")
            try:
                b = int(r.get("distress_before",0)); a = int(r.get("distress_after",0))
                pb = int(r.get("prob_before",0)); pa = int(r.get("prob_after",0))
                st.caption(f"しんどさ: {b} → {a} ／ 体感の確からしさ: {pb}% → {pa}%")
            except Exception:
                pass
            st.markdown('</div>', unsafe_allow_html=True)
        try:
            chart = df[["ts","distress_before","distress_after"]].dropna()
            chart["ts"] = pd.to_datetime(chart["ts"], errors="coerce")
            chart = chart.dropna().sort_values("ts").set_index("ts")
            if not chart.empty:
                st.line_chart(chart.rename(columns={"distress_before":"しんどさ(前)","distress_after":"しんどさ(後)"}))
        except Exception:
            pass
    st.markdown('</div>', unsafe_allow_html=True)

    # 呼吸
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🌬 記録（呼吸）")
    bfile = _load_csv(BREATH_CSV)
    bmem = pd.DataFrame(st.session_state.mem_records["breath"])
    bd = pd.concat([bfile, bmem], ignore_index=True)
    if bd.empty:
        st.caption("まだ保存された呼吸の記録はございません。")
    else:
        if "ts" in bd.columns:
            bd = bd.sort_values("ts", ascending=False)
        st.dataframe(bd.rename(columns={"ts":"日時","pattern":"サイクル","sets":"回数","note":"メモ"}),
                     use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ふり返り
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📝 記録（1日のふり返り）")
    rf_file = _load_csv(REFLECT_CSV)
    rf_mem = pd.DataFrame(st.session_state.mem_records["reflect"])
    rf = pd.concat([rf_file, rf_mem], ignore_index=True)
    if rf.empty:
        st.caption("まだ保存されたふり返りはございません。")
    else:
        view = rf.copy()
        if "date" in view.columns:
            try:
                view["date"] = pd.to_datetime(view["date"], errors="coerce")
                view = view.sort_values(["date","ts_saved"], ascending=False)
            except Exception:
                pass
        for _, r in view.head(50).iterrows():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"**📅 {r.get('date','')}**  —  🕒 {r.get('ts_saved','')}")
            st.markdown(f"**小さなできたこと**：{r.get('small_win','')}")
            st.markdown(f"**いまのご自身への一言**：{r.get('self_message','')}")
            nt = r.get("note_for_tomorrow","")
            if isinstance(nt,str) and nt.strip():
                st.markdown(f"**明日のご自身へ**：{nt}")
            try:
                st.caption(f"孤独感：{int(r.get('loneliness',0))}/10")
            except Exception:
                pass
        try:
            c2 = rf[["date","loneliness"]].copy()
            c2["date"] = pd.to_datetime(c2["date"], errors="coerce")
            c2 = c2.dropna().sort_values("date").set_index("date")
            if not c2.empty:
                st.line_chart(c2.rename(columns={"loneliness":"孤独感"}))
        except Exception:
            pass
    st.markdown('</div>', unsafe_allow_html=True)

def view_export():
    top_nav()
    st.subheader("⬇️ エクスポート & 設定")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("**データのエクスポート（CSV）**")
    # ファイル分とメモリ分を合算してDL
    cbt_all = pd.concat([_load_csv(CBT_CSV), pd.DataFrame(st.session_state.mem_records["cbt"])], ignore_index=True)
    ref_all = pd.concat([_load_csv(REFLECT_CSV), pd.DataFrame(st.session_state.mem_records["reflect"])], ignore_index=True)
    br_all  = pd.concat([_load_csv(BREATH_CSV), pd.DataFrame(st.session_state.mem_records["breath"])], ignore_index=True)

    def dl_inline(df: pd.DataFrame, label: str, filename: str):
        if df.empty:
            st.caption("（まだデータはございません）")
            return
        buf = df.to_csv(index=False).encode("utf-8")
        st.download_button(label, buf, file_name=filename, mime="text/csv")

    dl_inline(cbt_all, "⬇️ 2分ノート（CSV）をダウンロード", "cbt_entries.csv")
    dl_inline(ref_all, "⬇️ ふり返り（CSV）をダウンロード", "daily_reflections.csv")
    dl_inline(br_all,  "⬇️ 呼吸（CSV）をダウンロード", "breathing_entries.csv")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("**入力欄の初期化 / データの管理**")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("🧼 入力欄のみすべて初期化（記録は残ります）"):
            st.session_state.cbt = {}; st.session_state.reflection = {}
            ensure_cbt_defaults(); ensure_reflection_defaults()
            st.success("入力欄を初期化いたしました。記録は残っています。")
    with c2:
        danger = st.checkbox("⚠️ 保存済みCSVを削除することに同意します")
        if st.button("🗑️ 保存済みCSVを削除（取り消し不可）", disabled=not danger):
            try:
                for p in [CBT_CSV, REFLECT_CSV, BREATH_CSV]:
                    if p.exists(): p.unlink()
                st.success("保存ファイルを削除いたしました。")
            except Exception as e:
                st.error(f"削除時にエラーが発生しました: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- ルーティング ----------------
view = st.session_state.view
if view == "INTRO":
    view_intro()
elif view == "HOME":
    view_home()
elif view == "BREATH":
    view_breath()
elif view == "CBT":
    view_cbt()
elif view == "REFLECT":
    view_reflect()
elif view == "HISTORY":
    view_history()
else:
    view_export()

# ---------------- Footer ----------------
st.markdown("""
<div style="text-align:center; color:var(--muted); margin-top:12px;">
  <small>※ 個人名や連絡先は記入しないでください。<br>
  とてもつらい場合は、お住まいの地域の相談窓口や専門機関のご利用もご検討ください。</small>
</div>
""", unsafe_allow_html=True)
