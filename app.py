# app.py — Sora 2分ノート（空白除去＆文字つきUI／完全版）

from datetime import datetime, date
from pathlib import Path
from typing import Optional, List
import pandas as pd
import streamlit as st

# ---------------- Page config ----------------
st.set_page_config(
    page_title="Sora — しんどい夜の2分ノート",
    page_icon="🌙",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------- Theme ----------------
PINK = "#FBDDD3"
NAVY = "#19114B"

# ---------------- CSS ----------------
def inject_css():
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;600;700;900&display=swap');

:root {{
  --bg:{navy};
  --text:#FFFFFF;
  --muted:rgba(255,255,255,.75);
  --pink:{pink};
  --panel:#221A63;
  --line:rgba(251,221,211,.55);
}}
html, body, .stApp {{ background:var(--bg); }}
.block-container {{ max-width:980px; padding-top:.6rem; padding-bottom:2.2rem; }}
* {{ font-family:"Zen Maru Gothic", system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }}
h1,h2,h3,p,li,label,.stMarkdown,.stTextInput,.stTextArea {{ color:var(--text); }}
small {{ color:var(--muted); }}

/* 余計な空白を消す */
.stMarkdown p:empty, .stMarkdown div:empty {{ display:none !important; }}
section.main > div:empty {{ display:none !important; }}

/* ---------- Card ---------- */
.card {{
  background: var(--panel);
  border: 2px solid var(--line);
  border-radius: 22px;
  padding: 16px 18px;
  box-shadow: 0 18px 40px rgba(0,0,0,.22);
  margin-bottom: 14px;
}}

/* ---------- HERO（導入） ---------- */
.hero {{
  border: 2px solid var(--line);
  border-radius: 24px;
  padding: 22px;
  background: linear-gradient(180deg, rgba(255,255,255,.02), rgba(0,0,0,.06));
  margin-bottom: 16px;
}}
.hero .topline {{
  text-align:center; font-weight:900; font-size:1.08rem; letter-spacing:.06em;
  color: var(--pink); margin-bottom: 10px;
}}
.hero .maincopy {{
  text-align:center; font-weight:900; font-size:1.8rem; line-height:1.35; margin:.2rem 0 .9rem;
}}
.hero .maincopy .big3 {{ font-size:3rem; color:#fff; display:inline-block; transform:translateY(.04em); }}
.hero .what {{ margin:10px 0 12px; border:2px solid var(--line); border-radius:18px; padding:12px; background:rgba(0,0,0,.12); }}
.hero .what .title {{ font-weight:900; color:var(--pink); margin-bottom:4px; }}
.hero .badges {{ display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin:8px 0 6px; }}
.badgebox, .badge-btn > button {{
  border:2px solid var(--line); border-radius:18px; background:rgba(0,0,0,.08);
  padding:12px; color:#fff;
}}
.badge-title {{ display:block; font-weight:900; font-size:1rem; }}
.badge-desc  {{ display:block; color:var(--pink); font-weight:700; margin-top:4px; }}
.badge-btn > button {{ width:100%; white-space:normal !important; line-height:1.25; text-align:left; }}
.hero .list {{ border:2px solid var(--line); border-radius:18px; padding:10px 12px; background:rgba(0,0,0,.10); }}
.hero .list .title {{ font-weight:900; color:var(--pink); margin-bottom:4px; }}

/* ---------- CTA ---------- */
.cta-primary .stButton > button {{
  width:100%; border-radius:999px; padding:12px 16px;
  background:#FFFFFF !important; color:#18123F !important;
  font-weight:900; border:0 !important; box-shadow:0 14px 26px rgba(0,0,0,.22);
}}
.cta-ghost .stButton > button {{
  width:100%; border-radius:999px; padding:12px 16px;
  background:transparent !important; color:#FFFFFF !important;
  border:2px solid var(--line) !important; font-weight:900; box-shadow:none !important;
}}

/* ---------- 入力系 ---------- */
textarea, input, .stTextInput>div>div>input{{
  border-radius:14px!important; background:#0f0f23; color:#f0eeff; border:1px solid #3a3d66;
}}
.stSlider,.stRadio>div{{ color:var(--text) }}

/* ---------- Chips / Emoji ---------- */
.chips{{display:flex; gap:8px; flex-wrap:wrap; margin:8px 0 4px}}
.chips .chip-btn>button{{
  background:linear-gradient(180deg,#ffbcd2,#ff99bc); color:#3a2144;
  border:1px solid rgba(255,189,222,.35)!important; padding:8px 12px; height:auto;
  border-radius:999px!important; font-weight:900; box-shadow:0 10px 20px rgba(255,153,188,.12)
}}
.emoji-grid{{display:grid; grid-template-columns:repeat(8,1fr); gap:10px; margin:8px 0 2px}}
.emoji-btn>button{{ width:100%!important; aspect-ratio:1/1; border-radius:18px!important;
  font-size:1.55rem!important; background:#fff; color:#111;
  border:1px solid #eadfff!important; box-shadow:0 8px 16px rgba(12,13,30,.28);
}}
.emoji-on>button{{ background:linear-gradient(180deg,#ffc6a3,#ff9fbe)!important; border:1px solid #ff80b0!important; }}

/* ---------- Sticky Navbar (Radio Tabs) ---------- */
.navbar {{
  position: sticky; top: 0; z-index: 10;
  background: rgba(25,17,75,.72); backdrop-filter: blur(8px);
  margin: 0 -12px 10px; padding: 8px 12px 8px;
  border-bottom: 1px solid rgba(255,255,255,.08);
}}
.navbar .stRadio [role="radiogroup"] {{ gap: 8px; flex-wrap: wrap; }}
.navbar label {{
  background:#fff; color:#1b1742; border:1px solid rgba(0,0,0,.06);
  border-radius:12px; padding:8px 10px; font-weight:800;
}}
.navbar input:checked + div label {{
  background:#F4F4FF; border:2px solid #8A84FF;
}}

/* ---------- Responsive ---------- */
@media (max-width: 640px) {{
  .emoji-grid {{ grid-template-columns: repeat(4,1fr); }}
  .block-container {{ padding-left:1rem; padding-right:1rem; }}
  .hero .maincopy {{ font-size:1.6rem; }}
  .hero .maincopy .big3 {{ font-size:2.6rem; }}
}}
</style>
""".format(navy=NAVY, pink=PINK)
    st.markdown(css, unsafe_allow_html=True)

inject_css()

# ---------------- Data helpers ----------------
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
CBT_CSV = DATA_DIR / "cbt_entries.csv"
REFLECT_CSV = DATA_DIR / "daily_reflections.csv"

def _load_csv(p: Path) -> pd.DataFrame:
    if p.exists():
        try: return pd.read_csv(p)
        except Exception: return pd.DataFrame()
    return pd.DataFrame()

def _append_csv(p: Path, row: dict):
    df = _load_csv(p)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(p, index=False)

def _download_button(df: pd.DataFrame, label: str, filename: str):
    if df.empty: 
        st.caption("（まだデータはございません）"); 
        return
    st.download_button(label, df.to_csv(index=False).encode("utf-8"),
                       file_name=filename, mime="text/csv")

# ---------------- Session defaults ----------------
def ensure_cbt_defaults():
    if "cbt" not in st.session_state or not isinstance(st.session_state.cbt, dict):
        st.session_state.cbt = {}
    cbt = st.session_state.cbt
    cbt.setdefault("emotions", [])
    cbt.setdefault("trigger_tags", [])
    cbt.setdefault("trigger_free","")
    cbt.setdefault("fact","")
    cbt.setdefault("alt","")
    checks = cbt.setdefault("checks", {})
    checks.setdefault("bw", False)
    checks.setdefault("catastrophe", False)
    checks.setdefault("fortune", False)
    checks.setdefault("emotion", False)
    checks.setdefault("decide", False)
    cbt.setdefault("distress_before",5)
    cbt.setdefault("prob_before",50)
    cbt.setdefault("rephrase","")
    cbt.setdefault("prob_after",40)
    cbt.setdefault("distress_after",4)

def ensure_reflection_defaults():
    if "reflection" not in st.session_state or not isinstance(st.session_state.reflection, dict):
        st.session_state.reflection = {}
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

st.session_state.setdefault("view","INTRO")
st.session_state.setdefault("cbt_step", 1)      # 1..3
st.session_state.setdefault("cbt_guided", True) # ガイドON
ensure_cbt_defaults(); ensure_reflection_defaults()

# ---------------- Helpers ----------------
def vibrate(ms=8):
    st.markdown("<script>try{navigator.vibrate&&navigator.vibrate(%d)}catch(e){{}}</script>"%ms, unsafe_allow_html=True)

def companion(emoji: str, text: str, sub: Optional[str]=None):
    st.markdown(
        f"""
<div class="card" style="margin-top:6px;margin-bottom:8px">
  <div style="font-weight:900; color:var(--pink)">{emoji} {text}</div>
  {f"<div class='small' style='margin-top:2px; color:var(--muted)'>{sub}</div>" if sub else ""}
</div>
        """,
        unsafe_allow_html=True,
    )

def support(distress: Optional[int]=None, lonely: Optional[int]=None):
    if distress is not None and distress >= 7:
        companion("🫶","ここでは、がんばらなくて大丈夫です。","ご自身のペースで進めていただければ十分です。")
    elif lonely is not None and lonely >= 7:
        companion("🤝","この瞬間、ひとりではありません。","深呼吸をひとつして、ゆっくり進めましょう。")
    else:
        companion("🌟","ここまで入力いただけて十分です。","空欄があっても大丈夫です。")

# ---------------- Top Nav（文字つきタブ） ----------------
def top_nav():
    st.markdown('<div class="navbar">', unsafe_allow_html=True)

    keys = ["INTRO","HOME","CBT","REFLECT","HISTORY","EXPORT"]
    labels = {
        "INTRO":   "👋 はじめに — 最初の説明",
        "HOME":    "🏠 ホーム — 用途の入口",
        "CBT":     "📓 2分ノート — 3ステップで整理",
        "REFLECT": "📝 1日のふり返り — 今日を短く記録",
        "HISTORY": "📚 記録を見る — 保存した一覧",
        "EXPORT":  "⬇️ エクスポート — CSV・設定",
    }

    current = st.session_state.get("view","INTRO")
    idx = keys.index(current) if current in keys else 0

    choice = st.radio(
        "移動先",
        options=keys,
        index=idx,
        format_func=lambda k: labels[k],
        horizontal=True,
        label_visibility="collapsed",
        key="nav_radio",
    )
    st.session_state.view = choice
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Emoji & Chips ----------------
EMOJIS = ["😟","😡","😢","😔","😤","😴","🙂","🤷‍♀️"]

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
            if st.button(f"{e}", key=f"emo_{i}", use_container_width=True, help="タップで選択／もう一度で解除"):
                if on: chosen.remove(e)
                else: chosen.add(e)
                vibrate(8)
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    sel = " ".join(list(chosen)) if chosen else "（未選択）"
    st.caption(f"選択中：{sel}")
    return list(chosen)

TRIGGER_DEFS = [
    ("⏱️ さっきの出来事", "time"),
    ("🧠 浮かんだ一言", "thought_line"),
    ("🤝 人との関係", "relationship"),
    ("🫀 体のサイン", "body"),
    ("🌀 うまく言えない", "unknown"),
]

def trigger_chip_row(selected: List[str]) -> List[str]:
    st.caption("言葉にしづらい時は、近いものだけタップで結構です。")
    st.markdown('<div class="chips">', unsafe_allow_html=True)
    cols = st.columns(len(TRIGGER_DEFS))
    chosen = set(selected)
    for i,(label,val) in enumerate(TRIGGER_DEFS):
        with cols[i]:
            on = val in chosen
            st.markdown('<div class="chip-btn">', unsafe_allow_html=True)
            if st.button(label + (" ✓" if on else ""), key=f"trg_{val}", use_container_width=True, help="タップで選択／もう一度で解除"):
                if on: chosen.remove(val)
                else: chosen.add(val)
                vibrate(6)
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    return list(chosen)

# ---------------- 一言挿入 ----------------
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
    "bw":          "🌷 部分的にOKも、あるかもしれません。",
    "catastrophe": "☁️ 他の展開もあるかもしれません。",
    "fortune":     "🎈 他の展開になればラッキーですね。",
    "emotion":     "🫶 気持ちはそのまま、事実はそっと分けておくのもありかもしれません。",
    "decide":      "🌿 分からない場合はいったん保留にするのもありですね。",
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
                    append_to_textarea("alt", tip); vibrate(6)
                st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ---------------- INTRO ----------------
def view_intro():
    top_nav()
    st.markdown("""
<div class="hero">
  <div class="topline">夜、考えすぎてしんどくなるときに。</div>
  <div class="maincopy">
    たった <span class="big3">3</span> ステップで<br>
    気持ちを整理して、少し落ち着こう。
  </div>
  <div class="what">
    <div class="title">これは何？</div>
    <div>しんどい夜に、短時間で“見方”を整えるノート。<br>
    正解探しではなく、気持ちを整える時間を届けます。</div>
  </div>
""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="badge-btn">', unsafe_allow_html=True)
        if st.button("▶ はじめる\n— 約2分で完了 —", key="go_start", use_container_width=True):
            st.session_state.view="CBT"; st.session_state.cbt_step=1; st.session_state.cbt_guided=True
        st.caption("※ はじめての方はここ")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="badge-btn">', unsafe_allow_html=True)
        if st.button("👣 3ステップで進む\n— 案内つき —", key="go_3step", use_container_width=True):
            st.session_state.view="CBT"; st.session_state.cbt_step=1; st.session_state.cbt_guided=True
        st.caption("迷わず順番に進めます")
        st.markdown('</div>', unsafe_allow_html=True)
    with c3:
        st.markdown("""
<div class="badgebox">
  <span class="badge-title">🔒 この端末のみ保存</span>
  <span class="badge-desc">途中でやめてもOK／医療・診断ではありません</span>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
  <div class="list">
    <div class="title">内容</div>
    <ol style="margin:0 0 0 1.2rem">
      <li>気持ちの整理</li>
      <li>きっかけの整理</li>
      <li>見方の仮置き</li>
    </ol>
  </div>
</div>
""", unsafe_allow_html=True)

    cta1, cta2 = st.columns([3,2])
    with cta1:
        st.markdown('<div class="cta-primary">', unsafe_allow_html=True)
        if st.button("① 今すぐはじめる（約2分）", use_container_width=True):
            st.session_state.view="CBT"; st.session_state.cbt_step=1; st.session_state.cbt_guided=True
        st.markdown('</div>', unsafe_allow_html=True)
    with cta2:
        st.markdown('<div class="cta-ghost">', unsafe_allow_html=True)
        if st.button("ホームを見る", use_container_width=True):
            st.session_state.view="HOME"
        st.markdown('</div>', unsafe_allow_html=True)

# ---------------- HOME ----------------
def view_home():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 本日、どのように進めますか？")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("📓 2分ノートへ（おすすめ） — 3ステップで整理", use_container_width=True):
            st.session_state.view="CBT"; st.session_state.cbt_step=1; st.session_state.cbt_guided=True
    with c2:
        if st.button("📝 1日のふり返りへ — 今日を短く記録", use_container_width=True):
            st.session_state.view="REFLECT"
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- CBT（ガイド／フル表示） ----------------
def _cbt_step_header():
    total = 3; step = st.session_state.cbt_step
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write(f"**2分ノート｜現在 {step} / {total}**")
    st.progress(step/total)
    left, right = st.columns(2)
    with left:
        st.session_state.cbt_guided = st.toggle("かんたんガイド（オン＝順番に表示）", value=st.session_state.cbt_guided)
    with right:
        st.caption("オフにすると全項目を一括表示します。")
    st.markdown('</div>', unsafe_allow_html=True)

def _cbt_step1():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("① いまの気持ちをえらぶ")
    st.caption("当てはまる顔をタップ（複数OK／途中でやめてもOK）")
    st.session_state.cbt["emotions"] = emoji_toggle_grid(st.session_state.cbt.get("emotions", []))
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("しんどさ・確からしさ（ざっくりでOK）")
    cols = st.columns(2)
    with cols[0]:
        st.session_state.cbt["distress_before"] = st.slider("いまのしんどさ（0〜10）", 0, 10, int(st.session_state.cbt.get("distress_before",5)))
    with cols[1]:
        st.session_state.cbt["prob_before"] = st.slider("この考えはどのくらい“ありえそう”？（%）", 0, 100, int(st.session_state.cbt.get("prob_before",50)))
    support(distress=st.session_state.cbt["distress_before"])
    st.markdown('</div>', unsafe_allow_html=True)

def _cbt_step2():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("② きっかけをえらぶ（近いものでOK）")
    st.session_state.cbt["trigger_tags"] = trigger_chip_row(st.session_state.cbt.get("trigger_tags", []))
    st.session_state.cbt["trigger_free"] = st.text_area(
        "任意の一言（なくてOK）",
        value=st.session_state.cbt.get("trigger_free",""),
        placeholder="例）返信がまだ／『また失敗する』と浮かんだ など",
        height=72
    )
    st.markdown('</div>', unsafe_allow_html=True)

def _cbt_step3():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("③ 見方の仮置き（短くでOK）")
    st.caption("左＝いまの見方／右＝ほかの見方（片方だけでもOK）")
    cols2 = st.columns(2)
    with cols2[0]:
        st.session_state.cbt["fact"] = st.text_area("いまの見方", value=st.session_state.cbt.get("fact",""),
                                                   placeholder="例）返事が遅い＝嫌われたかも など", height=108)
    with cols2[1]:
        st.session_state.cbt["alt"] = st.text_area("ほかの見方（別の説明・例外）", value=st.session_state.cbt.get("alt",""),
                                                  placeholder="例）移動中かも／前も夜に返ってきた など", height=108)
    st.subheader("視界をひろげる小さなチェック")
    st.caption("当てはまるものだけ軽くオンに。合わなければスルーでOK。")
    render_checks_and_tips()

    starters = [
        "分からない部分は保留にします。",
        "可能性は一つじゃないかもしれない。",
        "今ある事実の範囲で受け止めます。",
        "決め打ちはいったん止めておきます。"
    ]
    idx = st.radio("“仮の見方”の候補（編集可）", options=list(range(len(starters))),
                   format_func=lambda i: starters[i], index=0, horizontal=False)
    seed = starters[idx] if 0 <= idx < len(starters) else ""
    st.session_state.cbt["rephrase"] = st.text_area("仮の見方（1行）",
                                                    value=st.session_state.cbt.get("rephrase","") or seed, height=84)
    ccols = st.columns(2)
    with ccols[0]:
        st.session_state.cbt["prob_after"] = st.slider("この“仮の見方”のしっくり度（%）", 0, 100, int(st.session_state.cbt.get("prob_after",40)))
    with ccols[1]:
        st.session_state.cbt["distress_after"] = st.slider("いまのしんどさ（まとめた後）", 0, 10, int(st.session_state.cbt.get("distress_after",4)))
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1:
        if st.button("💾 保存して完了（入力欄を初期化）", help="ここで完了。行動は決めなくてOK。"):
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
            _append_csv(CBT_CSV,row)
            st.session_state.cbt = {}; ensure_cbt_defaults()
            st.session_state.cbt_step = 1
            st.success("保存いたしました。ここで完了です。行動は決めなくて大丈夫です。")
    with c2:
        if st.button("🧼 入力欄のみ初期化（未保存分は消去）"):
            st.session_state.cbt = {}; ensure_cbt_defaults()
            st.info("入力欄を初期化いたしました（記録は残っています）。")
    st.markdown('</div>', unsafe_allow_html=True)

def _cbt_nav_buttons():
    step = st.session_state.cbt_step; total = 3
    prev_col, next_col = st.columns(2)
    with prev_col:
        if st.button("← 前へ", disabled=(step<=1), help="ひとつ前のステップへ戻る"):
            st.session_state.cbt_step = max(1, step-1); vibrate(5)
    with next_col:
        if st.button(("完了へ →" if step==total else "次へ →"),
                     help=("保存して完了します" if step==total else "次のステップへ進む")):
            st.session_state.cbt_step = min(total, step+1); vibrate(7)

def view_cbt():
    ensure_cbt_defaults()
    top_nav()
    _cbt_step_header()

    if not st.session_state.cbt_guided:
        # まとめて表示（余計な空白を作らないよう最小カード構成）
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("いまの気持ちをえらぶ")
        st.caption("当てはまる顔をタップ（複数OK／途中でやめてもOK）")
        st.session_state.cbt["emotions"] = emoji_toggle_grid(st.session_state.cbt.get("emotions", []))
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("この気持ち、近かったきっかけは？")
        st.session_state.cbt["trigger_tags"] = trigger_chip_row(st.session_state.cbt.get("trigger_tags", []))
        st.session_state.cbt["trigger_free"] = st.text_area(
            "任意の一言（なくてOK）", value=st.session_state.cbt.get("trigger_free",""),
            placeholder="例）返信がまだ／『また失敗する』と浮かんだ など", height=72
        )
        cols = st.columns(2)
        with cols[0]:
            st.session_state.cbt["distress_before"] = st.slider("いまのしんどさ（0〜10）", 0, 10, int(st.session_state.cbt.get("distress_before",5)))
        with cols[1]:
            st.session_state.cbt["prob_before"] = st.slider("この考えはどのくらい“ありえそう”？（%）", 0, 100, int(st.session_state.cbt.get("prob_before",50)))
        support(distress=st.session_state.cbt["distress_before"])
        st.markdown('</div>', unsafe_allow_html=True)

        _cbt_step3()
    else:
        # ガイド表示
        step = st.session_state.cbt_step
        if step == 1: _cbt_step1()
        if step == 2: _cbt_step2()
        if step == 3: _cbt_step3()
        _cbt_nav_buttons()

# ---------------- Reflection ----------------
def view_reflect():
    ensure_reflection_defaults()
    top_nav()
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("本日をやさしくふり返る")
    st.caption("点数ではなく、心が少しやわらぐ表現で短くご記入ください。")
    st.session_state.reflection["date"] = st.date_input("日付", value=st.session_state.reflection["date"])
    st.session_state.reflection["today_small_win"] = st.text_area("本日できたことを1つだけ：", value=st.session_state.reflection.get("today_small_win",""), height=76)
    st.session_state.reflection["self_message"] = st.text_area("いまのご自身への一言：", value=st.session_state.reflection.get("self_message",""), height=76)
    st.session_state.reflection["note_for_tomorrow"] = st.text_area("明日のご自身へのメモ（任意）：", value=st.session_state.reflection.get("note_for_tomorrow",""), height=76)
    st.session_state.reflection["loneliness"] = st.slider("いまの孤独感（0〜10）", 0, 10, int(st.session_state.reflection.get("loneliness",5)))
    support(lonely=st.session_state.reflection["loneliness"])
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
            _append_csv(REFLECT_CSV,row)
            st.session_state.reflection = {}; ensure_reflection_defaults()
            st.success("保存いたしました。")
    with c2:
        if st.button("🧼 入力欄のみ初期化（未保存分は消去）"):
            st.session_state.reflection = {}; ensure_reflection_defaults()
            st.info("入力欄を初期化いたしました（記録は残っています）。")

# ---------------- History ----------------
def view_history():
    top_nav()
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📓 記録（2分ノート）")
    df = _load_csv(CBT_CSV)
    if df.empty:
        st.caption("まだ保存されたノートはございません。最初の2分を行うと、こちらに一覧が表示されます。")
    else:
        q = st.text_input("キーワード検索（見方・一言・きっかけ・感情）", "")
        view = df.copy()
        text_cols = ["fact","alt","rephrase","trigger_free","emotions","trigger_tags"]
        for c in text_cols:
            if c in view.columns: view[c] = view[c].astype(str)
        if q.strip():
            q2 = q.strip().lower()
            mask = False
            for c in text_cols:
                if c in view.columns:
                    mask = mask | view[c].str.lower().str.contains(q2)
            view = view[mask]
        if "ts" in view.columns:
            view = view.sort_values("ts", ascending=False)
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
            tags=[]
            if r.get("bw",False): tags.append("0/100")
            if r.get("catastrophe",False): tags.append("最悪想定")
            if r.get("fortune",False): tags.append("結末決め打ち")
            if r.get("emotion",False): tags.append("感情先行")
            if r.get("decide",False): tags.append("言い切り")
            if tags:
                st.markdown(" " .join([f"<span class='tag' style='display:inline-block;padding:6px 12px;border:1px solid #3a3d66;border-radius:999px;background:#21224a;color:#ffdfef;font-weight:800;margin-right:6px'>{t}</span>" for t in tags]), unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        try:
            chart = df[["ts","distress_before","distress_after"]].copy()
            chart["ts"] = pd.to_datetime(chart["ts"])
            chart = chart.sort_values("ts").set_index("ts")
            st.line_chart(chart.rename(columns={"distress_before":"しんどさ(前)","しんどさ(後)":"しんどさ(後)"}))
        except Exception:
            pass
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📝 記録（1日のふり返り）")
    rf = _load_csv(REFLECT_CSV)
    if rf.empty:
        st.caption("まだ保存されたふり返りはございません。")
    else:
        view = rf.copy()
        if "date" in view.columns:
            try:
                view["date"] = pd.to_datetime(view["date"])
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
            c2["date"] = pd.to_datetime(c2["date"])
            c2 = c2.sort_values("date").set_index("date")
            st.line_chart(c2.rename(columns={"loneliness":"孤独感"}))
        except Exception:
            pass
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Export / Settings ----------------
def view_export():
    top_nav()
    st.subheader("⬇️ エクスポート & 設定")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("**データのエクスポート（CSV）**")
    _download_button(_load_csv(CBT_CSV), "⬇️ 2分ノート（CSV）をダウンロード", "cbt_entries.csv")
    _download_button(_load_csv(REFLECT_CSV), "⬇️ ふり返り（CSV）をダウンロード", "daily_reflections.csv")
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
        danger = st.checkbox("⚠️ すべての保存データ（CSV）を削除することに同意します")
        if st.button("🗑️ すべての保存データを削除（取り消し不可）", disabled=not danger):
            try:
                if CBT_CSV.exists(): CBT_CSV.unlink()
                if REFLECT_CSV.exists(): REFLECT_CSV.unlink()
                st.success("保存データを削除いたしました。最初からやり直せます。")
            except Exception as e:
                st.error(f"削除時にエラーが発生しました: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Router ----------------
view = st.session_state.view
if view == "INTRO":
    view_intro()
elif view == "HOME":
    top_nav(); view_home()
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
<div style="text-align:center; color:var(--muted); margin-top:10px;">
  <small>※ 個人名や連絡先は記入しないでください。<br>
  とてもつらい場合は、お住まいの地域の相談窓口や専門機関のご利用もご検討ください。</small>
</div>
""", unsafe_allow_html=True)
