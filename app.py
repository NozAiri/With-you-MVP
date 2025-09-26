# app.py — Mobile-first & Simple Navigation (Streamlit 1.37+)
# 使い方：このファイルをGitHubの app.py に置き換えてデプロイ

from datetime import datetime, date
from pathlib import Path
import pandas as pd
import streamlit as st

# ---------- 基本設定 ----------
st.set_page_config(
    page_title="Sora — 夜のモヤモヤを3分で整える",
    page_icon="🌙",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------- モバイル最適化CSS（大きめタップ/読みやすさ/固定ナビ） ----------
MOBILE_CSS = """
<style>
:root{
  --bg:#faf7fb; --card:#ffffff; --text:#2d2a32; --muted:#6b6575; --accent:#7c6cf4; --soft:#efe9ff;
}
.stApp{background:var(--bg) !important;}
.block-container{padding-top:1.2rem; padding-bottom:6.5rem; max-width:720px;}
h1,h2,h3{color:var(--text); letter-spacing:0.2px;}
p, label, .stMarkdown, .stTextInput, .stTextArea{font-size:1.06rem;}
small,.help{color:var(--muted)!important; font-size:.92rem;}

.card{background:var(--card); border:1px solid #eee; border-radius:18px; padding:16px 16px 14px; box-shadow:0 10px 24px rgba(0,0,0,.05); margin-bottom:12px;}
textarea, input, .stTextInput>div>div>input{border-radius:14px !important;}
.stButton>button,.stDownloadButton>button{
  width:100%; padding:14px 16px; border-radius:999px; border:none;
  background:var(--accent); color:#fff; font-weight:700; font-size:1.02rem;
  box-shadow:0 10px 20px rgba(124,108,244,.35);
}
.stButton>button:hover,.stDownloadButton>button:hover{filter:brightness(.96);}

.btn-light .stButton>button{background:#fff; color:#4b3f72; border:1px solid #ddd; box-shadow:none;}
.hr{height:1px; background:linear-gradient(to right, transparent, rgba(124,108,244,.28), transparent); margin:10px 0 6px;}

.tag{display:inline-block; padding:4px 10px; border-radius:999px; background:var(--soft); color:#5840c6;
  font-weight:600; margin-right:6px; margin-bottom:6px; border:1px solid rgba(88,64,198,.12);}

/* 固定ボトムナビ（スマホ向け） */
.bottom-nav{
  position:fixed; left:0; right:0; bottom:0; z-index:100;
  background:#fff; border-top:1px solid #eee; box-shadow:0 -6px 18px rgba(0,0,0,.06);
  padding:8px max(12px, env(safe-area-inset-left)) calc(8px + env(safe-area-inset-bottom)) max(12px, env(safe-area-inset-right));
}
.bottom-nav .grid{display:grid; grid-template-columns:repeat(4,1fr); gap:8px;}
.bottom-nav a{
  display:flex; align-items:center; justify-content:center; height:44px; border-radius:12px; text-decoration:none;
  font-weight:700; color:#5840c6; background:#f5f2ff; border:1px solid rgba(88,64,198,.12);
}
.bottom-nav a.active{background:var(--accent); color:#fff; border-color:transparent;}
/* iOSのタップハイライト軽減 */
a{-webkit-tap-highlight-color: transparent;}
</style>
"""
st.markdown(MOBILE_CSS, unsafe_allow_html=True)

# ---------- 共有データ/関数 ----------
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
    st.download_button(label, df.to_csv(index=False).encode("utf-8"), file_name=filename, mime="text/csv")

# ---------- セッション初期化（型を安定化） ----------
if "cbt" not in st.session_state:
    st.session_state.cbt = {
        "fact":"", "auto_thought":"", "distress_before":5,
        "gentle_checks":{"extreme":False,"mind_read":False,"catastrophe":False},
        "reframe_text":"", "distress_after":3
    }
if "reflection" not in st.session_state:
    st.session_state.reflection = {
        "today_small_win":"", "self_message":"", "note_for_tomorrow":"",
        "loneliness":5, "date":date.today()
    }

# ---------- ここからページ定義 ----------
def header():
    st.markdown("""
    <div class="card" style="padding:18px;">
      <h2 style="margin:0;">🌙 Sora — 夜のモヤモヤを、やさしく整える</h2>
      <div class="hr"></div>
      <p style="color:#6b6575;margin:.2rem 0 0.4rem;">
        事実と心の声を分けて、やさしい言い換えを作っていく小さな場所。
      </p>
      <span class="tag">3分でできる</span><span class="tag">専門用語なし</span><span class="tag">あとから見返せる</span>
    </div>
    """, unsafe_allow_html=True)

def page_cbt():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("1) できごと（実況でOK）")
    st.caption("カメラ視点で“事実だけ”。気持ちや推測は次で扱うから、いまは置いておく。")
    st.session_state.cbt["fact"]=st.text_area("今日、どんなことがあった？",
        value=st.session_state.cbt["fact"],
        placeholder="例）21:20にLINEを送った。既読はまだ。明日の小テストがある。",
        height=100, label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("2) 浮かんだ考え（心の声）")
    st.session_state.cbt["auto_thought"]=st.text_area("心の声：",
        value=st.session_state.cbt["auto_thought"],
        placeholder="例）どうせ私なんて好かれてない…",
        height=88, label_visibility="collapsed")
    st.session_state.cbt["distress_before"]=st.slider("いまのつらさ（0〜10）",0,10,st.session_state.cbt["distress_before"])
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("3) やさしい確認（責めない“？”）")
    col1,col2,col3=st.columns(3)
    with col1:
        st.session_state.cbt["gentle_checks"]["extreme"]=st.checkbox("0か100で考えてない？",
            value=st.session_state.cbt["gentle_checks"]["extreme"])
    with col2:
        st.session_state.cbt["gentle_checks"]["mind_read"]=st.checkbox("相手の心を決めつけてない？",
            value=st.session_state.cbt["gentle_checks"]["mind_read"])
    with col3:
        st.session_state.cbt["gentle_checks"]["catastrophe"]=st.checkbox("最悪の未来を予言してない？",
            value=st.session_state.cbt["gentle_checks"]["catastrophe"])
    hints=[]
    if st.session_state.cbt["gentle_checks"]["extreme"]:
        hints.append("「一つうまくいかない＝全部ダメ」ではないかも。")
    if st.session_state.cbt["gentle_checks"]["mind_read"]:
        hints.append("相手の気持ちは、まだ“聞いてみないと分からない”。")
    if st.session_state.cbt["gentle_checks"]["catastrophe"]:
        hints.append("“一番悪い未来”以外にも、いくつか可能性がある。")
    if hints:
        st.write("💡 小さなヒント"); [st.markdown(f"- {h}") for h in hints]
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("4) ちょっとだけ言い換える")
    st.caption("事実によせて、現実的な言い方に。しっくり来なければ自由入力でOK。")
    s=[]
    g=st.session_state.cbt["gentle_checks"]
    if g["extreme"]: s.append("うまくいってない部分はあるけど、全部がダメとは限らない。")
    if g["mind_read"]: s.append("相手にも事情があるかも。確かめてみないと分からない。")
    if g["catastrophe"]: s.append("不安はあるけど、未来は一つじゃない。今わかる事実はここまで。")
    if not s:
        s=["いまは“既読がない”という事実だけ。気持ちは決めつけずに置いておく。",
           "私は不安。でも、それは“大事にしているものがある”サインでもある。",
           "少し休んでから考え直してもいい。焦らなくて大丈夫。"]
    idx=st.radio("候補（編集して使ってOK）", list(range(len(s))),
                 format_func=lambda i:s[i], index=0, horizontal=False)
    default_text=s[idx] if 0<=idx<len(s) else ""
    st.session_state.cbt["reframe_text"]=st.text_area("自由に整える：",
        value=st.session_state.cbt["reframe_text"] or default_text, height=90)
    st.session_state.cbt["distress_after"]=st.slider("いまのつらさ（言い換え後・任意）",0,10,st.session_state.cbt["distress_after"])
    st.markdown('</div>', unsafe_allow_html=True)

    c1,c2=st.columns(2)
    with c1:
        if st.button("💾 保存して完了（入力欄は初期化）"):
            now=datetime.now().isoformat(timespec="seconds")
            row={"id":f"cbt-{now}","ts":now,
                 "fact":st.session_state.cbt["fact"],
                 "auto_thought":st.session_state.cbt["auto_thought"],
                 "extreme":g["extreme"],"mind_read":g["mind_read"],"catastrophe":g["catastrophe"],
                 "reframe_text":st.session_state.cbt["reframe_text"],
                 "distress_before":st.session_state.cbt["distress_before"],
                 "distress_after":st.session_state.cbt["distress_after"]}
            _append_csv(CBT_CSV,row)
            st.session_state.cbt={"fact":"", "auto_thought":"", "distress_before":5,
                "gentle_checks":{"extreme":False,"mind_read":False,"catastrophe":False},
                "reframe_text":"", "distress_after":3}
            st.success("保存しました。ここまでできたの、本当にえらい。")
    with c2:
        if st.button("🧼 入力欄だけ初期化（未保存は消えます）"):
            st.session_state.cbt={"fact":"", "auto_thought":"", "distress_before":5,
                "gentle_checks":{"extreme":False,"mind_read":False,"catastrophe":False},
                "reframe_text":"", "distress_after":3}
            st.info("入力欄をリセットしました（履歴は残っています）。")

def page_reflection():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("今日をそっとふり返る")
    st.caption("点数じゃなく、心が少しやわらぐ書き方で。短くてOK。")
    # date は常に date 型で扱う
    d=st.session_state.reflection.get("date", date.today())
    if isinstance(d,str):
        try: d=date.fromisoformat(d)
        except Exception: d=date.today()
    st.session_state.reflection["date"]=st.date_input("日付", value=d)
    st.session_state.reflection["today_small_win"]=st.text_area("今日できた小さなこと（1つで十分）",
        value=st.session_state.reflection["today_small_win"], height=80)
    st.session_state.reflection["self_message"]=st.text_area("いまの自分に一言かけるなら？",
        value=st.session_state.reflection["self_message"], height=80)
    st.session_state.reflection["note_for_tomorrow"]=st.text_area("明日の自分へひとこと（任意）",
        value=st.session_state.reflection["note_for_tomorrow"], height=80)
    st.session_state.reflection["loneliness"]=st.slider("いまの孤独感（0〜10）",0,10,st.session_state.reflection["loneliness"])
    st.markdown('</div>', unsafe_allow_html=True)

    c1,c2=st.columns(2)
    with c1:
        if st.button("💾 リフレクションを保存（入力欄は初期化）"):
            now=datetime.now().isoformat(timespec="seconds")
            dv=st.session_state.reflection["date"]
            date_str=dv.isoformat() if isinstance(dv,(datetime,date)) else str(dv)
            row={"id":f"ref-{now}","date":date_str,"ts_saved":now,
                 "small_win":st.session_state.reflection["today_small_win"],
                 "self_message":st.session_state.reflection["self_message"],
                 "note_for_tomorrow":st.session_state.reflection["note_for_tomorrow"],
                 "loneliness":st.session_state.reflection["loneliness"]}
            _append_csv(REFLECT_CSV,row)
            st.session_state.reflection={"today_small_win":"", "self_message":"",
                "note_for_tomorrow":"", "loneliness":5, "date":date.today()}
            st.success("保存しました。宝物みたいな言葉が増えていくね。")
    with c2:
        if st.button("🧼 入力欄だけ初期化（未保存は消えます）"):
            st.session_state.reflection={"today_small_win":"", "self_message":"",
                "note_for_tomorrow":"", "loneliness":5, "date":date.today()}
            st.info("入力欄をリセットしました（履歴は残っています）。")

def page_history():
    st.subheader("🗂️ 履歴")
    # CBT
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### CBTワーク")
    df=_load_csv(CBT_CSV)
    if df.empty: st.caption("まだ保存されたCBTワークがありません。")
    else:
        q=st.text_input("キーワードで探す（事実・心の声・言い換え）", "")
        view=df.copy()
        if q.strip():
            q=q.strip().lower()
            for c in ["fact","auto_thought","reframe_text"]:
                view[c]=view[c].astype(str)
            mask=(view["fact"].str.lower().str.contains(q)|
                  view["auto_thought"].str.lower().str.contains(q)|
                  view["reframe_text"].str.lower().str.contains(q))
            view=view[mask]
        if "ts" in view.columns: view=view.sort_values("ts", ascending=False)
        for _,r in view.head(50).iterrows():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"**🕒 {r.get('ts','')}**")
            st.markdown(f"**出来事**：{r.get('fact','')}")
            st.markdown(f"**心の声**：{r.get('auto_thought','')}")
            st.markdown(f"**言い換え**：{r.get('reframe_text','')}")
            try:
                b=int(r.get("distress_before",0)); a=int(r.get("distress_after",0))
                st.caption(f"つらさ: {b} → {a}")
            except Exception: pass
            tags=[]
            if r.get("extreme",False): tags.append("極端に決めつけ")
            if r.get("mind_read",False): tags.append("心を決めつけ")
            if r.get("catastrophe",False): tags.append("最悪を予言")
            if tags: st.markdown(" ".join([f"<span class='tag'>{t}</span>" for t in tags]), unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        # 推移
        try:
            chart=df[["ts","distress_before","distress_after"]].copy()
            chart["ts"]=pd.to_datetime(chart["ts"]); chart=chart.sort_values("ts").set_index("ts")
            st.line_chart(chart.rename(columns={"distress_before":"つらさ(前)","distress_after":"つらさ(後)"}))
        except Exception: pass
    st.markdown('</div>', unsafe_allow_html=True)

    # Reflection
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### リフレクション")
    rf=_load_csv(REFLECT_CSV)
    if rf.empty: st.caption("まだ保存されたリフレクションがありません。")
    else:
        view=rf.copy()
        if "date" in view.columns:
            try:
                view["date"]=pd.to_datetime(view["date"])
                view=view.sort_values(["date","ts_saved"], ascending=False)
            except Exception: pass
        for _,r in view.head(50).iterrows():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"**📅 {r.get('date','')}**  —  🕒 {r.get('ts_saved','')}")
            st.markdown(f"**小さなできたこと**：{r.get('small_win','')}")
            st.markdown(f"**いまの自分への一言**：{r.get('self_message','')}")
            nt=r.get("note_for_tomorrow","")
            if isinstance(nt,str) and nt.strip(): st.markdown(f"**明日の自分へ**：{nt}")
            try: st.caption(f"孤独感：{int(r.get('loneliness',0))}/10")
            except Exception: pass
        try:
            c2=rf[["date","loneliness"]].copy()
            c2["date"]=pd.to_datetime(c2["date"]); c2=c2.sort_values("date").set_index("date")
            st.line_chart(c2.rename(columns={"loneliness":"孤独感"}))
        except Exception: pass
    st.markdown('</div>', unsafe_allow_html=True)

def page_export():
    st.subheader("⬇️ エクスポート & 設定")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("**データのエクスポート（CSV）**")
    _download_button(_load_csv(CBT_CSV), "⬇️ CBTワークをダウンロード", "cbt_entries.csv")
    _download_button(_load_csv(REFLECT_CSV), "⬇️ リフレクションをダウンロード", "daily_reflections.csv")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("**入力欄の初期化 / データの管理**")
    c1,c2=st.columns(2)
    with c1:
        if st.button("🧼 入力欄だけ全部初期化（履歴は残る）"):
            st.session_state.cbt={"fact":"", "auto_thought":"", "distress_before":5,
                "gentle_checks":{"extreme":False,"mind_read":False,"catastrophe":False},
                "reframe_text":"", "distress_after":3}
            st.session_state.reflection={"today_small_win":"", "self_message":"",
                "note_for_tomorrow":"", "loneliness":5, "date":date.today()}
            st.success("入力欄をすべて初期化しました。履歴は残っています。")
    with c2:
        danger=st.checkbox("⚠️ すべての保存データ（CSV）を削除することに同意します")
        if st.button("🗑️ すべての保存データを削除（取り消し不可）", disabled=not danger):
            try:
                if CBT_CSV.exists(): CBT_CSV.unlink()
                if REFLECT_CSV.exists(): REFLECT_CSV.unlink()
                st.success("保存データを削除しました。はじめからやり直せます。")
            except Exception as e:
                st.error(f"削除でエラーが発生: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- ルーティング（クエリパラメータでページ切替） ----------
DEFAULT_PAGE = "cbt"
page = st.query_params.get("page", DEFAULT_PAGE)
if isinstance(page, list): page = page[0]
if page not in {"cbt","reflect","history","export"}: page = DEFAULT_PAGE

# ヘッダ
header()

# ページ本体
if page=="cbt":
    page_cbt()
elif page=="reflect":
    page_reflection()
elif page=="history":
    page_history()
else:
    page_export()

# 固定ボトムナビ（リンクで?page=... を切替 → 1タップで移動・戻るも効く）
nav = f"""
<div class="bottom-nav">
  <div class="grid">
    <a href="?page=cbt" class="{'active' if page=='cbt' else ''}">CBT</a>
    <a href="?page=reflect" class="{'active' if page=='reflect' else ''}">リフレク</a>
    <a href="?page=history" class="{'active' if page=='history' else ''}">履歴</a>
    <a href="?page=export" class="{'active' if page=='export' else ''}">エクスポ</a>
  </div>
</div>
"""
st.markdown(nav, unsafe_allow_html=True)

# フッター注意書き
st.markdown("""
<div style="text-align:center; color:#6b6575; margin-top:10px;">
  <small>※ 個人名や連絡先は書かないでね。<br>
  もし今、とてもつらくて危ないと感じるときは、あなたの地域の相談先にアクセスしてね。</small>
</div>
""", unsafe_allow_html=True)
