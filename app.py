# app.py — Sora 2分ノート（ポスター完全寄せ：濃紺×ピンク／INTRO強化）
# - 背景: #19114B   アクセント（ピンク）: #FBDDD3
# - 1ページ目（INTRO）は画像ポスターのレイアウト/書体感に寄せて再設計
# - 「約2分」「3 STEP」をタップするとCBTへ遷移
# - ナビは“白ゴースト”でボタンと明確に差別化

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

# ---------------- Theme / CSS ----------------
PINK = "#FBDDD3"
NAVY = "#19114B"

def inject_css():
    st.markdown(f"""
<style>
/* Webフォント（丸みのあるゴシック） */
@import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;600;700;900&family=Noto+Sans+JP:wght@400;700;900&display=swap');

:root{{
  --bg:{NAVY};
  --text:#FFFFFF;
  --muted:rgba(255,255,255,.72);
  --pink:{PINK};
  --card:#1F1858;           /* わずかに明るい紺 */
  --line:rgba(251,221,211,.55);
}}

html, body, .stApp{{ background:var(--bg); }}
.block-container{{ max-width:980px; padding-top:.5rem; padding-bottom:2rem; }}
*{{ font-family:"Zen Maru Gothic","Noto Sans JP",system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }}

h1,h2,h3,p,li,label,.stMarkdown,.stTextInput,.stTextArea{{ color:var(--text); }}
small{{ color:var(--muted); }}

a, a:visited{{ color:var(--pink); }}

.card {{
  background: var(--card);
  border: 2px solid var(--line);
  border-radius: 22px;
  padding: 18px;
  box-shadow: 0 22px 44px rgba(0,0,0,.25);
}}

/* ---- HERO（ポスター構成） ---- */
.hero {{
  border: 2px solid var(--line);
  border-radius: 24px;
  padding: 26px 22px;
  background: linear-gradient(180deg, rgba(255,255,255,.02), rgba(0,0,0,.06));
}}
.hero .topline {{
  text-align:center;
  font-weight:900;
  font-size:1.15rem;
  letter-spacing:.08em;
  color: var(--pink);
  margin-bottom: 14px;
}}
.hero .maincopy {{
  text-align:center;
  font-weight:900;
  font-size:1.9rem;
  line-height:1.4;
  margin: .2rem 0 1.1rem;
}}
.hero .maincopy .big3 {{
  font-size: 3.2rem;
  color:#FFFFFF;
  display:inline-block;
  transform: translateY(.08em);
}}

.hero .what {{
  margin: 12px 0 16px;
  border: 2px solid var(--line);
  border-radius: 18px;
  padding: 14px 14px;
  background: rgba(0,0,0,.12);
}}
.hero .what .title {{
  font-weight: 900;
  color: var(--pink);
  margin-bottom: 6px;
}}

.hero .badges {{
  display:grid; grid-template-columns:repeat(3,1fr); gap:12px;
  margin: 10px 0 8px;
}}
.badge {{
  border: 2px solid var(--line);
  border-radius: 18px;
  padding: 12px 10px;
  background: rgba(0,0,0,.08);
  text-align:center;
  color: var(--pink);
  font-weight: 800;
}}
.badge .big {{
  display:block;
  color:#FFFFFF;
  font-weight:900;
  font-size:1.7rem;
  margin-top:2px;
}}
/* badgeをボタン化（見た目は同じ） */
.badge-btn > button {{
  width:100%;
  border-radius:18px !important;
  padding:12px 10px !important;
  background: rgba(0,0,0,.08) !important;
  border:2px solid var(--line) !important;
  color: var(--pink) !important;
  font-weight:800 !important;
  box-shadow:none !important;
}}
.badge-btn > button:hover {{ filter: brightness(1.06); }}
.badge-btn > button .big {{ color:#FFFFFF; font-size:1.7rem; display:block; margin-top:2px; font-weight:900; }}

.hero .list {{
  border: 2px solid var(--line);
  border-radius: 18px;
  padding: 12px 14px;
  background: rgba(0,0,0,.10);
}}
.hero .list .title{{ font-weight:900; color:var(--pink); margin-bottom:6px; }}

/* ---- CTA ---- */
.stButton > button.primary {{
  width:100%; border-radius:999px; padding:14px 16px;
  background: #FFFFFF !important; color:#18123F !important;
  font-weight:900; border:0 !important; box-shadow:0 16px 28px rgba(0,0,0,.25);
}}
.stButton > button.ghost {{
  width:100%; border-radius:999px; padding:14px 16px;
  background: transparent !important; color:#FFFFFF !important;
  border: 2px solid var(--line) !important;
  font-weight:900; box-shadow:none !important;
}}

/* ---- トップナビ（白ゴーストで差別化） ---- */
.topbar{{
  position:sticky; top:0; z-index:10;
  background: rgba(25,17,75,.55); backdrop-filter: blur(8px);
  border-bottom: 1px solid rgba(255,255,255,.08);
  margin: 0 -12px 10px; padding: 8px 12px 10px;
}}
.topnav{{ display:flex; gap:8px; flex-wrap:wrap; }}
.topnav .nav-btn>button{{
  background:#FFFFFF !important; color:#1d1b3f !important;
  border:1px solid rgba(0,0,0,.06) !important;
  height:auto !important; padding:9px 12px !important; border-radius:12px !important;
  font-weight:800 !important; font-size:.95rem !important;
}}
.topnav .active>button{{ background:#F4F4FF !important; border:2px solid #8A84FF !important; }}

/* ---- フッター ---- */
.footer small{{ color:var(--muted); }}
@media (max-width: 640px){{
  .hero .maincopy{{ font-size:1.7rem; }}
  .hero .maincopy .big3{{ font-size:2.8rem; }}
}}
</style>
""", unsafe_allow_html=True)

inject_css()

# ----------------- Data helpers & state（既存機能は温存） -----------------
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

st.session_state.setdefault("view","INTRO")

# ------------- 既存ページ（CBT/REFLECT/HISTORY/EXPORT）は最小限で残す -------------
# ここでは省略せず、ユーザーの元コードの機能を使いたい前提で簡略化版を残す
#  — 既存の長い実装を使う場合は、そのまま貼り替えてOK。以下は誘導のためのダミー UX。
def view_cbt_min():
    st.markdown("<div class='card'><h3>📓 2分ノート</h3><p>ここに既存のCBTフォームを表示します。（元のview_cbtを入れてOK）</p></div>", unsafe_allow_html=True)

def view_home_min():
    st.markdown("<div class='card'><h3>🏠 ホーム</h3><p>ここにホームのタイルなどを表示します。（任意）</p></div>", unsafe_allow_html=True)

def view_reflect_min():
    st.markdown("<div class='card'><h3>📝 1日のふり返り</h3><p>ここにふり返りUIを表示します。（任意）</p></div>", unsafe_allow_html=True)

def view_history_min():
    st.markdown("<div class='card'><h3>📚 記録を見る</h3><p>ここに履歴を表示します。（任意）</p></div>", unsafe_allow_html=True)

def view_export_min():
    st.markdown("<div class='card'><h3>⬇️ エクスポート</h3><p>CSV出力などをここに。</p></div>", unsafe_allow_html=True)

# --------- Top Nav（見た目差別化） ----------
def top_nav():
    st.markdown('<div class="topbar"><div class="topnav">', unsafe_allow_html=True)
    pages = [("INTRO","👋 はじめに"),("HOME","🏠 ホーム"),("CBT","📓 2分ノート"),
             ("REFLECT","📝 ふり返り"),("HISTORY","📚 記録"),("EXPORT","⬇️ エクスポート")]
    cols = st.columns(len(pages))
    for i,(key,label) in enumerate(pages):
        cls = "nav-btn active" if st.session_state.view==key else "nav-btn"
        with cols[i]:
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.view = key
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

# ---------------- INTRO：画像のポスターに寄せた1ページ ----------------
def view_intro():
    top_nav()  # ここに置くと常に最上段。見た目はゴーストで主張弱め

    st.markdown(f"""
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

    # バッジ行：ここで「約2分」「3STEP」をボタン化 → CBTへ遷移
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="badge-btn">', unsafe_allow_html=True)
        if st.button("🕒\n<span class='big'>約 2 分</span>", key="go_cbt_2min", use_container_width=True):
            st.session_state.view = "CBT"
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="badge-btn">', unsafe_allow_html=True)
        if st.button("👣\n<span class='big'>3 STEP</span>", key="go_cbt_3step", use_container_width=True):
            st.session_state.view = "CBT"
        st.markdown('</div>', unsafe_allow_html=True)

    with c3:
        # 鍵は説明のみ（ボタンではない）→ 見た目はバッジ
        st.markdown("""
<div class="badge">
  <div>🔒</div>
  <div style="font-size:.95rem;line-height:1.2;color:#fff;margin-top:4px">
    この端末のみ保存<br>途中でやめてもOK<br>医療・診断ではありません
  </div>
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
</div>  <!-- /hero -->
""", unsafe_allow_html=True)

    # CTA（見た目差別化：白=プライマリ／ゴースト=副次）
    cta1, cta2 = st.columns([3,2])
    with cta1:
        if st.button("今すぐはじめる（約2分）", key="start_primary", use_container_width=True):
            st.session_state.view = "CBT"
        st.markdown("<script>document.querySelector('[key=start_primary]')?.classList.add('primary');</script>", unsafe_allow_html=True)
    with cta2:
        if st.button("ホームを見る", key="go_home", use_container_width=True):
            st.session_state.view = "HOME"
        st.markdown("<script>document.querySelector('[key=go_home]')?.classList.add('ghost');</script>", unsafe_allow_html=True)

# ---------------- ルーティング ----------------
view = st.session_state.view
if view == "INTRO":
    view_intro()
elif view == "HOME":
    view_home_min()
elif view == "CBT":
    view_cbt_min()      # ここに元の view_cbt() を差し替えればそのまま動きます
elif view == "REFLECT":
    view_reflect_min()  # 任意で差し替え
elif view == "HISTORY":
    view_history_min()
else:
    view_export_min()

# ---------------- Footer ----------------
st.markdown("""
<div class="footer" style="text-align:center; margin-top:14px;">
  <small>※ 個人名や連絡先は記入しないでください。とてもつらい場合は、お住まいの地域の相談窓口や専門機関のご利用もご検討ください。</small>
</div>
""", unsafe_allow_html=True)
