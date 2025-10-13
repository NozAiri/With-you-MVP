# ・・・冒頭はそのまま・・・

def inject_css():
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;600;700;900&display=swap');

:root {{
  --bg:{NAVY};
  --text:#FFFFFF;
  --muted:rgba(255,255,255,.75);
  --pink:{PINK};
  --card:#221A63;
  --line:rgba(251,221,211,.55);
}}

html, body, .stApp {{ background: var(--bg); }}
.block-container {{ max-width:980px; padding-top:.6rem; padding-bottom:3.2rem; }}
* {{ font-family:"Zen Maru Gothic", system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }}
h1,h2,h3,p,li,label,.stMarkdown,.stTextInput,.stTextArea {{ color: var(--text); }}
small {{ color: var(--muted); }}

/* --- NAV (ghost) --- */
.topbar {{ position:sticky; top:0; z-index:10; background: rgba(25,17,75,.55); backdrop-filter: blur(8px);
  border-bottom:1px solid rgba(255,255,255,.08); margin:0 -12px 12px; padding:8px 12px 10px; }}
.topnav {{ display:flex; gap:8px; flex-wrap:wrap; }}
.topnav .nav-btn > button {{
  background:#FFFFFF !important; color:#1b1742 !important; border:1px solid rgba(0,0,0,.06) !important;
  height:auto !important; padding:9px 12px !important; border-radius:12px !important; font-weight:800 !important; font-size:.95rem !important;
}}
.topnav .active > button {{ background:#F4F4FF !important; border:2px solid #8A84FF !important; }}

/* --- HERO --- */
.hero {{ border:2px solid var(--line); border-radius:24px; padding:26px 22px;
  background:linear-gradient(180deg, rgba(255,255,255,.02), rgba(0,0,0,.06)); }}
.hero .topline {{ text-align:center; font-weight:900; font-size:1.14rem; letter-spacing:.08em; color:var(--pink); margin-bottom:14px; }}
.hero .maincopy {{ text-align:center; font-weight:900; font-size:1.9rem; line-height:1.4; margin:.2rem 0 1.1rem; }}
.hero .maincopy .big3 {{ font-size:3.2rem; color:#fff; display:inline-block; transform:translateY(.06em); }}
.hero .what {{ margin:12px 0 16px; border:2px solid var(--line); border-radius:18px; padding:14px; background:rgba(0,0,0,.12); }}
.hero .what .title {{ font-weight:900; color:var(--pink); margin-bottom:6px; }}

/* --- badges --- */
.hero .badges {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin:10px 0 8px; }}
.badge, .badge-btn > button {{
  border:2px solid var(--line); border-radius:18px; background:rgba(0,0,0,.08);
  text-align:center; padding:12px 10px; color:var(--pink); font-weight:800;
}}
/* ここが重要：改行テキストをそのまま表示 */
.badge-btn > button {{
  width:100%; box-shadow:none !important; white-space: pre-line;    /* ← 改行を生かす */
  line-height:1.25; font-size:1.15rem;                              /* テキストも見える大きさに */
}}
.badge-btn > button:hover {{ filter:brightness(1.06); }}

/* 静的バッジ内の数字は少し大きく */
.badge .big {{ display:block; color:#fff; font-weight:900; font-size:1.6rem; margin-top:2px; }}

/* 内容ボックス */
.hero .list {{ border:2px solid var(--line); border-radius:18px; padding:12px 14px; background:rgba(0,0,0,.10); }}
.hero .list .title {{ font-weight:900; color:var(--pink); margin-bottom:6px; }}

/* CTA */
.cta-primary .stButton > button {{ width:100%; border-radius:999px; padding:14px 16px;
  background:#FFFFFF !important; color:#18123F !important; font-weight:900; border:0 !important; box-shadow:0 16px 28px rgba(0,0,0,.25); }}
.cta-ghost   .stButton > button {{ width:100%; border-radius:999px; padding:14px 16px;
  background:transparent !important; color:#FFFFFF !important; border:2px solid var(--line) !important; font-weight:900; box-shadow:none !important; }}

.footer small {{ color:var(--muted); }}

@media (max-width: 640px) {{
  .hero .maincopy{{ font-size:1.7rem; }}
  .hero .maincopy .big3{{ font-size:2.8rem; }}
}}
</style>
""", unsafe_allow_html=True)

# ・・・中略（既存の関数はそのまま）・・・

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

    # ← 改行込みのラベルでそのまま表示
    c1,c2,c3 = st.columns(3)
    with c1:
        st.markdown('<div class="badge-btn">', unsafe_allow_html=True)
        if st.button("🕒\n約 2 分", key="intro_to_cbt_2", use_container_width=True):
            st.session_state.view="CBT"
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="badge-btn">', unsafe_allow_html=True)
        if st.button("👣\n3 STEP", key="intro_to_cbt_3", use_container_width=True):
            st.session_state.view="CBT"
        st.markdown('</div>', unsafe_allow_html=True)

    with c3:
        st.markdown("""
<div class="badge">
  <div>🔒</div>
  <div class="big" style="font-size:1.05rem;line-height:1.25;margin-top:6px">
    <span style="font-size:.95rem;display:block;color:#fff;line-height:1.25">
      この端末のみ保存<br>途中でやめてもOK<br>医療・診断ではありません
    </span>
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
</div>
""", unsafe_allow_html=True)

    cta1, cta2 = st.columns([3,2])
    with cta1:
        st.markdown('<div class="cta-primary">', unsafe_allow_html=True)
        if st.button("今すぐはじめる（約2分）", key="cta_start", use_container_width=True):
            st.session_state.view = "CBT"
        st.markdown('</div>', unsafe_allow_html=True)
    with cta2:
        st.markdown('<div class="cta-ghost">', unsafe_allow_html=True)
        if st.button("ホームを見る", key="cta_home", use_container_width=True):
            st.session_state.view = "HOME"
        st.markdown('</div>', unsafe_allow_html=True)
