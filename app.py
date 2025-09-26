# app.py — Sora (Bright starry, mobile-first, one-page tiles)
# 明るい配色 / 星の瞬き / ガラス風カード / タイル式ホーム / ページ遷移なし

from datetime import datetime, date
from pathlib import Path
from typing import Optional
import pandas as pd
import streamlit as st

# ---------------- Base ----------------
st.set_page_config(
    page_title="Sora — 夜のモヤモヤを3分で整える",
    page_icon="🌙",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------- Theme builder ----------------
def build_css(bright: bool = True, stars: bool = True) -> str:
    if bright:
        bg_layer = """
        background:
          radial-gradient(1200px 700px at 10% -10%, #b8d7ff66 0%, transparent 60%),
          radial-gradient(900px 600px at 100% 0%, #ffd8ff55 0%, transparent 65%),
          linear-gradient(180deg, #f7fbff 0%, #eef2ff 55%, #ffffff 100%);
        """
        colors = """
        :root{
          --text:#233047; --muted:#6a7387; --outline:#cbd7ff;
          --card-bg:rgba(255,255,255,.85); --card-border:rgba(160,175,255,.35);
          --tile-cbt-from:#7e8bff; --tile-cbt-to:#b7b9ff;
          --tile-ref-from:#4fdad2; --tile-ref-to:#9fe9e2;
          --tile-his-from:#ffd36a; --tile-his-to:#ffe7a3;
          --tile-exp-from:#9aa8ff; --tile-exp-to:#c7ceff;
          --btn-from:#6c7cff; --btn-to:#4ea7ff;
          --chip:#f3f5ff;
        }
        """
        star_layers = """
        .stApp:after{
          content:""; position:fixed; inset:0; pointer-events:none; z-index:0;
          background-image:
            radial-gradient(1.7px 1.7px at 8% 18%, #9fc9ffcc, transparent 35%),
            radial-gradient(2px 2px at 25% 6%, #ffd8ffcc, transparent 40%),
            radial-gradient(1.6px 1.6px at 90% 12%, #fff7b3cc, transparent 40%),
            radial-gradient(1.8px 1.8px at 70% 40%, #b7e6ffcc, transparent 40%),
            radial-gradient(1.2px 1.2px at 50% 22%, #ffffffcc, transparent 40%),
            radial-gradient(1.4px 1.4px at 30% 52%, #ffffffaa, transparent 40%);
          background-repeat:no-repeat;
          animation: twinkle 5s ease-in-out infinite alternate;
          opacity:.9;
        }
        @keyframes twinkle { 0%{opacity:.95} 50%{opacity:.55} 100%{opacity:.95} }
        """
    else:
        # （ダーク寄りテーマ・必要なら切替可能。今回は明るめがデフォルト）
        bg_layer = """
        background:
          radial-gradient(1200px 700px at 10% -10%, #2f285f55 0%, transparent 60%),
          radial-gradient(900px 600px at 100% 0%, #274e5c40 0%, transparent 70%),
          linear-gradient(180deg, #201b45 0%, #2b2455 55%, #0e0b1f 100%);
        """
        colors = """
        :root{
          --text:#f4f2ff; --muted:#b8b3d6; --outline:#3d376c;
          --card-bg:rgba(20,17,41,.9); --card-border:#3d376c;
          --tile-cbt-from:#9b8cff; --tile-cbt-to:#6a5ff7;
          --tile-ref-from:#54dad7; --tile-ref-to:#2ea6d1;
          --tile-his-from:#ffd36a; --tile-his-to:#ff9d52;
          --tile-exp-from:#a9a2c5; --tile-exp-to:#7d76a2;
          --btn-from:#6f60ff; --btn-to:#4e41d7;
          --chip:#221e43;
        }
        """
        star_layers = """
        .stApp:after{
          content:""; position:fixed; inset:0; pointer-events:none; z-index:0;
          background-image:
            radial-gradient(2px 2px at 10% 20%, #ffffff55, transparent 40%),
            radial-gradient(2px 2px at 30% 10%, #00fff555, transparent 40%),
            radial-gradient(2px 2px at 85% 15%, #ffb6ff55, transparent 40%),
            radial-gradient(2px 2px at 70% 40%, #fff7a955, transparent 40%);
          background-repeat:no-repeat;
          animation: twinkle 5s ease-in-out infinite alternate;
        }
        @keyframes twinkle { 0%{opacity:.9} 50%{opacity:.4} 100%{opacity:.9} }
        """
    return f"""
    <style>
    .stApp{{ {bg_layer} }}
    {colors}
    .block-container{{max-width:820px; padding-top:1.05rem; padding-bottom:2.1rem; position:relative; z-index:1}}
    h1,h2,h3{{color:var(--text); letter-spacing:.2px}}
    p,label,.stMarkdown,.stTextInput,.stTextArea{{color:var(--text); font-size:1.06rem}}
    small,.help{{color:var(--muted)!important; font-size:.92rem}}
    textarea,input,.stTextInput>div>div>input{{border-radius:14px!important; background:#ffffff; color:#1d2533}}
    .card{{
      background:var(--card-bg); border:1px solid var(--card-border); border-radius:18px;
      padding:16px; box-shadow:0 16px 35px rgba(36,49,89,.18); margin-bottom:14px; backdrop-filter:blur(8px);
    }}
    .hr{{height:1px; background:linear-gradient(to right, transparent, #9fb0ff, transparent); margin:10px 0 6px}}
    .tag{{display:inline-block; padding:6px 12px; border-radius:999px; background:#eef1ff; color:#334178;
      font-weight:700; margin:0 6px 6px 0; border:1px solid var(--outline)}}
    .stButton>button,.stDownloadButton>button{{
      width:100%; padding:14px 16px; border-radius:999px; border:1px solid var(--outline);
      background:linear-gradient(180deg, var(--btn-from), var(--btn-to)); color:#fff; font-weight:800; font-size:1.02rem;
      box-shadow:0 12px 26px rgba(80,110,255,.28);
    }}
    .stButton>button:hover{{filter:brightness(.97)}}

    /* ----- Tile Home ----- */
    .tile-grid{{display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:8px}}
    .tile .stButton>button{{
      height:112px; border-radius:18px; text-align:left; padding:14px 16px; white-space:normal; line-height:1.25;
      border:none; font-weight:900; font-size:1.05rem; box-shadow:0 14px 30px rgba(0,0,0,.18); color:#142039;
    }}
    .tile .sub{{display:block; margin-top:6px; font-weight:700; font-size:.95rem; opacity:.9}}
    .tile-cbt .stButton>button{{background:linear-gradient(160deg,var(--tile-cbt-from),var(--tile-cbt-to))}}
    .tile-ref .stButton>button{{background:linear-gradient(160deg,var(--tile-ref-from),var(--tile-ref-to))}}
    .tile-his .stButton>button{{background:linear-gradient(160deg,var(--tile-his-from),var(--tile-his-to))}}
    .tile-exp .stButton>button{{background:linear-gradient(160deg,var(--tile-exp-from),var(--tile-exp-to))}}
    .tile .stButton>button:after{{content:"›"; float:right; font-size:1.6rem; opacity:.9; color:#0e1a33}}

    /* Quick chips */
    .chips{{display:flex; gap:8px; flex-wrap:wrap; margin:6px 0 10px}}
    .chips .stButton>button{{background:var(--chip); color:#263556; border:1px solid var(--outline);
      padding:8px 12px; height:auto; border-radius:999px; font-weight:800}}

    /* stars layer */
    {star_layers if stars else ""}
    </style>
    """

# ---------------- Session defaults ----------------
if "view" not in st.session_state: st.session_state.view = "HOME"  # HOME / CBT / REFLECT / HISTORY / EXPORT
if "cbt" not in st.session_state:
    st.session_state.cbt = {"fact":"", "auto_thought":"", "distress_before":5,
        "gentle_checks":{"extreme":False,"mind_read":False,"catastrophe":False},
        "reframe_text":"", "distress_after":3}
if "reflection" not in st.session_state:
    st.session_state.reflection = {"today_small_win":"", "self_message":"",
        "note_for_tomorrow":"", "loneliness":5, "date":date.today()}
st.session_state.setdefault("bright_theme", True)
st.session_state.setdefault("starry_bg", True)

# ---- Theme toggles (即時反映) ----
with st.container():
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.bright_theme = st.toggle("🌟 明るめのテーマ", value=st.session_state.bright_theme, help="見やすく気分が沈みにくい配色")
    with c2:
        st.session_state.starry_bg = st.toggle("✨ 星をちりばめる", value=st.session_state.starry_bg, help="やさしい星の瞬き（負荷は軽め）")
# inject CSS after toggles（毎回反映）
st.markdown(build_css(st.session_state.bright_theme, st.session_state.starry_bg), unsafe_allow_html=True)

# ---------------- Helper ----------------
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
CBT_CSV = DATA_DIR / "cbt_entries.csv"
REFLECT_CSV = DATA_DIR / "daily_reflections.csv"

def _load_csv(path: Path) -> pd.DataFrame:
    if path.exists():
        try: return pd.read_csv(path)
        except Exception: return pd.DataFrame()
    return pd.DataFrame()

def _append_csv(path: Path, row: dict):
    df = _load_csv(path)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(path, index=False)

def _download_button(df: pd.DataFrame, label: str, filename: str):
    if df.empty: st.caption("（まだデータがありません）"); return
    st.download_button(label, df.to_csv(index=False).encode("utf-8"),
                       file_name=filename, mime="text/csv")

def companion(emoji: str, text: str, sub: Optional[str]=None):
    st.markdown(f"""
    <div class="card">
      <div style="font-weight:800; color:#233047">{emoji} {text}</div>
      {f"<div class='small' style='margin-top:4px;'>{sub}</div>" if sub else ""}
    </div>
    """, unsafe_allow_html=True)

def support(distress: Optional[int]=None, lonely: Optional[int]=None):
    if distress is not None and distress >= 7:
        companion("🕊️","いまは“耐える時間”じゃなくて“やさしくする時間”。",
                  "ゆっくりでいい。あなたのペースで。ここに一緒にいるよ。")
    elif lonely is not None and lonely >= 7:
        companion("🤝","この瞬間、あなたは一人きりじゃない。","小さく息を吐こう。言葉はちゃんと届くから。")
    else:
        companion("🌙","書けた分だけ、ちゃんと前進。","短くても十分。続けることがいちばんの力。")

# ---------------- Header ----------------
greet = "こんばんは" if (18 <= datetime.now().hour or datetime.now().hour < 4) else "こんにちは"
st.markdown(f"""
<div class="card" style="padding:18px;">
  <h2 style="margin:0; color:#1f2a44">{greet}、Soraへようこそ。</h2>
  <div class="hr"></div>
  <p style="color:var(--muted); margin:.2rem 0 .4rem;">
    ここは、孤独な夜に“自分を責めない”ための小さな場所。<br>
    事実と心の声を分けて、やさしい言い換えをつくっていこう。
  </p>
  <span class="tag">3分でできる</span>
  <span class="tag">やさしいことば</span>
  <span class="tag">あとから見返せる</span>
</div>
""", unsafe_allow_html=True)

# ---------------- Nav (state only, no page move) ----------------
def quick_switch():
    with st.container():
        st.markdown('<div class="chips">', unsafe_allow_html=True)
        c1,c2,c3,c4,c5 = st.columns(5)
        with c1:
            if st.button("🏠 ホーム", key="qs_home"): st.session_state.view="HOME"
        with c2:
            if st.button("📓 CBT", key="qs_cbt"): st.session_state.view="CBT"
        with c3:
            if st.button("📝 リフレク", key="qs_ref"): st.session_state.view="REFLECT"
        with c4:
            if st.button("📚 履歴", key="qs_his"): st.session_state.view="HISTORY"
        with c5:
            if st.button("⬇️ エクスポ", key="qs_exp"): st.session_state.view="EXPORT"
        st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Views ----------------
def view_home():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 今やりたいことを選んでね")
    st.markdown('<div class="tile-grid">', unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1:
        st.markdown('<div class="tile tile-cbt">', unsafe_allow_html=True)
        if st.button("📓 3分CBT\n今の気持ちを整える", key="tile_cbt"): st.session_state.view="CBT"
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="tile tile-ref">', unsafe_allow_html=True)
        if st.button("📝 1日のリフレクション\nやさしく振り返る", key="tile_ref"): st.session_state.view="REFLECT"
        st.markdown('</div>', unsafe_allow_html=True)
    c3,c4 = st.columns(2)
    with c3:
        st.markdown('<div class="tile tile-his">', unsafe_allow_html=True)
        if st.button("📚 履歴を見る\n言葉のアルバム", key="tile_his"): st.session_state.view="HISTORY"
        st.markdown('</div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="tile tile-exp">', unsafe_allow_html=True)
        if st.button("⬇️ エクスポート\n& 設定", key="tile_exp"): st.session_state.view="EXPORT"
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    support()

def view_cbt():
    quick_switch()
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("1) できごと（実況でOK）")
    st.caption("カメラ視点で“事実だけ”。気持ちや推測は次で扱うから、いまは置いておく。")
    st.session_state.cbt["fact"] = st.text_area(
        "今日、どんなことがあった？",
        value=st.session_state.cbt["fact"],
        placeholder="例）21:20にLINEを送った。既読はまだ。明日の小テストがある。",
        height=96, label_visibility="collapsed"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("2) 浮かんだ考え（心の声）")
    st.session_state.cbt["auto_thought"] = st.text_area(
        "心の声：",
        value=st.session_state.cbt["auto_thought"],
        placeholder="例）どうせ私なんて好かれてない…",
        height=88, label_visibility="collapsed"
    )
    st.session_state.cbt["distress_before"] = st.slider("いまのつらさ（0〜10）", 0, 10, st.session_state.cbt["distress_before"])
    support(distress=st.session_state.cbt["distress_before"])
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("3) やさしい確認（責めない“？”）")
    col1,col2,col3 = st.columns(3)
    with col1:
        st.session_state.cbt["gentle_checks"]["extreme"] = st.checkbox("0か100で考えてない？",
            value=st.session_state.cbt["gentle_checks"]["extreme"])
    with col2:
        st.session_state.cbt["gentle_checks"]["mind_read"] = st.checkbox("相手の心を決めつけてない？",
            value=st.session_state.cbt["gentle_checks"]["mind_read"])
    with col3:
        st.session_state.cbt["gentle_checks"]["catastrophe"] = st.checkbox("最悪の未来を予言してない？",
            value=st.session_state.cbt["gentle_checks"]["catastrophe"])
    hints=[]
    g = st.session_state.cbt["gentle_checks"]
    if g["extreme"]:     hints.append("「一つうまくいかない＝全部ダメ」ではないかも。")
    if g["mind_read"]:   hints.append("相手の気持ちは、まだ“聞いてみないと分からない”。")
    if g["catastrophe"]: hints.append("“一番悪い未来”以外にも、いくつか可能性がある。")
    if hints:
        st.write("💡 小さなヒント")
        for h in hints: st.markdown(f"- {h}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("4) ちょっとだけ言い換える")
    st.caption("事実によせて、現実的な言い方に。しっくり来なければ自由入力でOK。")
    sug=[]
    if g["extreme"]:     sug.append("うまくいってない部分はあるけど、全部がダメとは限らない。")
    if g["mind_read"]:   sug.append("相手にも事情があるかも。確かめてみないと分からない。")
    if g["catastrophe"]: sug.append("不安はあるけど、未来は一つじゃない。今わかる事実はここまで。")
    if not sug:
        sug = [
            "いまは“既読がない”という事実だけ。気持ちは決めつけずに置いておく。",
            "私は不安。でも、それは“大事にしているものがある”サインでもある。",
            "少し休んでから考え直してもいい。焦らなくて大丈夫。"
        ]
    idx = st.radio("候補（編集してOK）", options=list(range(len(sug))),
                   format_func=lambda i:sug[i], index=0, horizontal=False)
    default_text = sug[idx] if 0 <= idx < len(sug) else ""
    st.session_state.cbt["reframe_text"] = st.text_area(
        "自由に整える：",
        value=st.session_state.cbt["reframe_text"] or default_text, height=90
    )
    st.session_state.cbt["distress_after"] = st.slider("いまのつらさ（言い換え後・任意）", 0, 10, st.session_state.cbt["distress_after"])
    st.markdown('</div>', unsafe_allow_html=True)

    c1,c2 = st.columns(2)
    with c1:
        if st.button("💾 保存して完了（入力欄は初期化）"):
            now = datetime.now().isoformat(timespec="seconds")
            row = {"id":f"cbt-{now}","ts":now,
                   "fact":st.session_state.cbt["fact"],
                   "auto_thought":st.session_state.cbt["auto_thought"],
                   "extreme":g["extreme"],"mind_read":g["mind_read"],"catastrophe":g["catastrophe"],
                   "reframe_text":st.session_state.cbt["reframe_text"],
                   "distress_before":st.session_state.cbt["distress_before"],
                   "distress_after":st.session_state.cbt["distress_after"]}
            _append_csv(CBT_CSV,row)
            st.session_state.cbt = {"fact":"", "auto_thought":"", "distress_before":5,
                "gentle_checks":{"extreme":False,"mind_read":False,"catastrophe":False},
                "reframe_text":"", "distress_after":3}
            st.success("保存しました。ここまでできたの、本当にえらい。")
    with c2:
        if st.button("🧼 入力欄だけ初期化（未保存は消えます）"):
            st.session_state.cbt = {"fact":"", "auto_thought":"", "distress_before":5,
                "gentle_checks":{"extreme":False,"mind_read":False,"catastrophe":False},
                "reframe_text":"", "distress_after":3}
            st.info("入力欄をリセットしました（履歴は残っています）。")

def view_reflect():
    quick_switch()
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("今日をそっとふり返る")
    st.caption("点数じゃなく、心が少しやわらぐ書き方で。短くてOK。")
    d = st.session_state.reflection.get("date", date.today())
    if isinstance(d, str):
        try: d = date.fromisoformat(d)
        except Exception: d = date.today()
    st.session_state.reflection["date"] = st.date_input("日付", value=d)
    st.session_state.reflection["today_small_win"] = st.text_area(
        "今日できた小さなこと（1つで十分）",
        value=st.session_state.reflection["today_small_win"], height=76
    )
    st.session_state.reflection["self_message"] = st.text_area(
        "いまの自分に一言かけるなら？",
        value=st.session_state.reflection["self_message"], height=76
    )
    st.session_state.reflection["note_for_tomorrow"] = st.text_area(
        "明日の自分へひとこと（任意）",
        value=st.session_state.reflection["note_for_tomorrow"], height=76
    )
    st.session_state.reflection["loneliness"] = st.slider("いまの孤独感（0〜10）", 0, 10, st.session_state.reflection["loneliness"])
    support(lonely=st.session_state.reflection["loneliness"])
    st.markdown('</div>', unsafe_allow_html=True)

    c1,c2 = st.columns(2)
    with c1:
        if st.button("💾 リフレクションを保存（入力欄は初期化）"):
            now = datetime.now().isoformat(timespec="seconds")
            dv = st.session_state.reflection["date"]
            date_str = dv.isoformat() if isinstance(dv,(date,datetime)) else str(dv)
            row = {"id":f"ref-{now}","date":date_str,"ts_saved":now,
                   "small_win":st.session_state.reflection["today_small_win"],
                   "self_message":st.session_state.reflection["self_message"],
                   "note_for_tomorrow":st.session_state.reflection["note_for_tomorrow"],
                   "loneliness":st.session_state.reflection["loneliness"]}
            _append_csv(REFLECT_CSV,row)
            st.session_state.reflection = {"today_small_win":"", "self_message":"",
                "note_for_tomorrow":"", "loneliness":5, "date":date.today()}
            st.success("保存しました。宝物みたいな言葉が増えていくね。")
    with c2:
        if st.button("🧼 入力欄だけ初期化（未保存は消えます）"):
            st.session_state.reflection = {"today_small_win":"", "self_message":"",
                "note_for_tomorrow":"", "loneliness":5, "date":date.today()}
            st.info("入力欄をリセットしました（履歴は残っています）。")

def view_history():
    quick_switch()
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🗂️ 履歴 — CBTワーク")
    df = _load_csv(CBT_CSV)
    if df.empty:
        st.caption("まだ保存されたCBTワークがありません。")
    else:
        q = st.text_input("キーワードで探す（事実・心の声・言い換え）", "")
        view = df.copy()
        if q.strip():
            q = q.strip().lower()
            for c in ["fact","auto_thought","reframe_text"]:
                view[c] = view[c].astype(str)
            mask = (view["fact"].str.lower().str.contains(q) |
                    view["auto_thought"].str.lower().str.contains(q) |
                    view["reframe_text"].str.lower().str.contains(q))
            view = view[mask]
        if "ts" in view.columns:
            view = view.sort_values("ts", ascending=False)
        for _, r in view.head(50).iterrows():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"**🕒 {r.get('ts','')}**")
            st.markdown(f"**出来事**：{r.get('fact','')}")
            st.markdown(f"**心の声**：{r.get('auto_thought','')}")
            st.markdown(f"**言い換え**：{r.get('reframe_text','')}")
            try:
                b = int(r.get("distress_before",0)); a = int(r.get("distress_after",0))
                st.caption(f"つらさ: {b} → {a}")
            except Exception: pass
            tags=[]
            if r.get("extreme",False): tags.append("極端に決めつけ")
            if r.get("mind_read",False): tags.append("心を決めつけ")
            if r.get("catastrophe",False): tags.append("最悪を予言")
            if tags:
                st.markdown(" ".join([f"<span class='tag'>{t}</span>" for t in tags]), unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        try:
            chart = df[["ts","distress_before","distress_after"]].copy()
            chart["ts"] = pd.to_datetime(chart["ts"])
            chart = chart.sort_values("ts").set_index("ts")
            st.line_chart(chart.rename(columns={"distress_before":"つらさ(前)","distress_after":"つらさ(後)"}))
        except Exception: pass
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📔 履歴 — リフレクション")
    rf = _load_csv(REFLECT_CSV)
    if rf.empty:
        st.caption("まだ保存されたリフレクションがありません。")
    else:
        view = rf.copy()
        if "date" in view.columns:
            try:
                view["date"] = pd.to_datetime(view["date"])
                view = view.sort_values(["date","ts_saved"], ascending=False)
            except Exception: pass
        for _, r in view.head(50).iterrows():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"**📅 {r.get('date','')}**  —  🕒 {r.get('ts_saved','')}")
            st.markdown(f"**小さなできたこと**：{r.get('small_win','')}")
            st.markdown(f"**いまの自分への一言**：{r.get('self_message','')}")
            nt = r.get("note_for_tomorrow","")
            if isinstance(nt,str) and nt.strip(): st.markdown(f"**明日の自分へ**：{nt}")
            try: st.caption(f"孤独感：{int(r.get('loneliness',0))}/10")
            except Exception: pass
        try:
            c2 = rf[["date","loneliness"]].copy()
            c2["date"] = pd.to_datetime(c2["date"])
            c2 = c2.sort_values("date").set_index("date")
            st.line_chart(c2.rename(columns={"loneliness":"孤独感"}))
        except Exception: pass
    st.markdown('</div>', unsafe_allow_html=True)

def view_export():
    quick_switch()
    st.subheader("⬇️ エクスポート & 設定")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("**データのエクスポート（CSV）**")
    _download_button(_load_csv(CBT_CSV), "⬇️ CBTワークをダウンロード", "cbt_entries.csv")
    _download_button(_load_csv(REFLECT_CSV), "⬇️ リフレクションをダウンロード", "daily_reflections.csv")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("**入力欄の初期化 / データの管理**")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("🧼 入力欄だけ全部初期化（履歴は残る）"):
            st.session_state.cbt = {"fact":"", "auto_thought":"", "distress_before":5,
                "gentle_checks":{"extreme":False,"mind_read":False,"catastrophe":False},
                "reframe_text":"", "distress_after":3}
            st.session_state.reflection = {"today_small_win":"", "self_message":"",
                "note_for_tomorrow":"", "loneliness":5, "date":date.today()}
            st.success("入力欄をすべて初期化しました。履歴は残っています。")
    with c2:
        danger = st.checkbox("⚠️ すべての保存データ（CSV）を削除することに同意します")
        if st.button("🗑️ すべての保存データを削除（取り消し不可）", disabled=not danger):
            try:
                if CBT_CSV.exists(): CBT_CSV.unlink()
                if REFLECT_CSV.exists(): REFLECT_CSV.unlink()
                st.success("保存データを削除しました。はじめからやり直せます。")
            except Exception as e:
                st.error(f"削除でエラーが発生: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Render ----------------
if st.session_state.view == "HOME":
    view_home()
elif st.session_state.view == "CBT":
    view_cbt()
elif st.session_state.view == "REFLECT":
    view_reflect()
elif st.session_state.view == "HISTORY":
    view_history()
else:
    view_export()

# ---------------- Footer ----------------
st.markdown("""
<div style="text-align:center; color:var(--muted); margin-top:12px;">
  <small>※ 個人名や連絡先は書かないでね。<br>
  もし今、とてもつらくて危ないと感じるときは、あなたの地域の相談先にアクセスしてね。</small>
</div>
""", unsafe_allow_html=True)
