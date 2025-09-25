# app.py (fixed)
from datetime import datetime, date
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Sora — 夜のモヤモヤを3分で整える",
    page_icon="🌙",
    layout="centered",
    initial_sidebar_state="collapsed",
)

CUSTOM_CSS = """
<style>
:root {
  --bg: #faf7fb;
  --card: #ffffff;
  --accent: #9b87f5;
  --text: #2d2a32;
  --muted: #6b6575;
  --soft: #efe9ff;
}
.css-1wrcr25, .stApp { background: var(--bg) !important; }
.block-container { padding-top: 2.5rem; padding-bottom: 3rem; }
h1, h2, h3 { color: var(--text); }
small, .help { color: var(--muted) !important; }
.card {
  background: var(--card);
  border: 1px solid #eee;
  border-radius: 20px;
  padding: 18px 18px 14px 18px;
  box-shadow: 0 10px 24px rgba(0,0,0,0.05);
  margin-bottom: 14px;
}
.stButton>button {
  background: var(--accent);
  color: white;
  border: none;
  padding: 0.8rem 1.2rem;
  border-radius: 999px;
  font-weight: 600;
  box-shadow: 0 8px 18px rgba(155,135,245,0.35);
}
.stButton>button:hover { filter: brightness(0.95); }
.btn-light .stButton>button {
  background: linear-gradient(0deg, #fff, #fff);
  color: #4b3f72;
  border: 1px solid #ddd;
  box-shadow: none;
}
textarea, input, .stTextInput>div>div>input { border-radius: 14px !important; }
.tag {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--soft);
  color: #5840c6;
  font-weight: 600;
  margin-right: 6px; margin-bottom: 6px;
  border: 1px solid rgba(88,64,198,0.12);
}
.hr {
  height: 1px;
  background: linear-gradient(to right, rgba(155,135,245,0.0), rgba(155,135,245,0.25), rgba(155,135,245,0.0));
  margin: 10px 0 6px 0;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

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
    if df.empty:
        st.caption("（まだデータがありません）"); return
    st.download_button(
        label=label,
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
        key=label
    )

# ---------- session init (keep types consistent) ----------
if "cbt" not in st.session_state:
    st.session_state.cbt = {
        "fact": "",
        "auto_thought": "",
        "distress_before": 5,
        "gentle_checks": {"extreme": False, "mind_read": False, "catastrophe": False},
        "reframe_text": "",
        "distress_after": 3
    }

if "reflection" not in st.session_state:
    st.session_state.reflection = {
        "today_small_win": "",
        "self_message": "",
        "note_for_tomorrow": "",
        "loneliness": 5,
        # ここを date 型で保持（以前は .isoformat() で文字列になっていた）
        "date": date.today()
    }

st.markdown("""
<div class="card" style="padding: 22px;">
  <h2>🌙 Sora — 夜のモヤモヤを、やさしく整える</h2>
  <div class="hr"></div>
  <p style="color:#6b6575;margin-bottom:6px;">
    ここは「自分を責めない」ための小さな場所。<br>
    事実と心の声を分けて、やさしい言い換えを作っていこう。
  </p>
  <span class="tag">3分でできる</span><span class="tag">専門用語なし</span><span class="tag">あとから見返せる</span>
</div>
""", unsafe_allow_html=True)

tab_cbt, tab_reflect, tab_history, tab_export = st.tabs(
    ["🪄 3分CBTワーク", "📔 1日のリフレクション", "🗂️ ふり返り（履歴）", "⬇️ エクスポート & 設定"]
)

# -------------------- CBT TAB --------------------
with tab_cbt:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("1) できごと（実況中継で OK）")
    st.caption("カメラになったつもりで、そのまま書いてみてね。推測や気持ちは次で扱うから、いまは出来事だけで大丈夫。")
    st.session_state.cbt["fact"] = st.text_area(
        "今日、どんなことがあった？",
        value=st.session_state.cbt["fact"],
        placeholder="例）21:20にLINEを送った。いま机に向かっている。明日の小テストがある。既読はまだない。",
        height=100, label_visibility="collapsed"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("2) 浮かんだ考え（心の声）")
    st.caption("そのとき、心にどんな言葉が浮かんだ？ ひとことでもOKだよ。")
    st.session_state.cbt["auto_thought"] = st.text_area(
        "心の声：",
        value=st.session_state.cbt["auto_thought"],
        placeholder="例）どうせ私なんて好かれてない…",
        height=90, label_visibility="collapsed"
    )
    st.session_state.cbt["distress_before"] = st.slider("いまのつらさ（0〜10）", 0, 10, st.session_state.cbt["distress_before"])
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("3) やさしい確認（責めない“？”）")
    st.caption("ここは“正解探し”じゃなくて、小さな気づきの時間。あてはまるものがあれば、そっとチェックしてみてね。")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.session_state.cbt["gentle_checks"]["extreme"] = st.checkbox("0か100で考えてない？", value=st.session_state.cbt["gentle_checks"]["extreme"])
    with col2:
        st.session_state.cbt["gentle_checks"]["mind_read"] = st.checkbox("相手の心を決めつけてない？", value=st.session_state.cbt["gentle_checks"]["mind_read"])
    with col3:
        st.session_state.cbt["gentle_checks"]["catastrophe"] = st.checkbox("最悪の未来を予言してない？", value=st.session_state.cbt["gentle_checks"]["catastrophe"])
    hints = []
    if st.session_state.cbt["gentle_checks"]["extreme"]:
        hints.append("「一つうまくいかない＝全部ダメ」ではないかも。")
    if st.session_state.cbt["gentle_checks"]["mind_read"]:
        hints.append("相手の気持ちは、まだ“聞いてみないと分からない”こともある。")
    if st.session_state.cbt["gentle_checks"]["catastrophe"]:
        hints.append("“一番悪い未来”以外にも、いくつか可能性があるかもしれない。")
    if hints:
        st.write("💡 小さなヒント")
        for h in hints: st.markdown(f"- {h}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("4) ちょっとだけ言い換えてみる")
    st.caption("事実によせて、すこし現実的な言い方に。しっくり来るものがなければ、自由入力でOK。")
    suggestions = []
    if st.session_state.cbt["gentle_checks"]["extreme"]:
        suggestions.append("いまうまくいってない部分はあるけど、全部がダメとまでは決められない。")
    if st.session_state.cbt["gentle_checks"]["mind_read"]:
        suggestions.append("相手にも事情があるかも。気持ちは確かめてみないと分からない。")
    if st.session_state.cbt["gentle_checks"]["catastrophe"]:
        suggestions.append("不安はあるけど、未来はひとつじゃない。今わかる事実はここまで。")
    if not suggestions:
        suggestions = [
            "いまは“既読がない”という事実だけ。気持ちは決めつけずに置いておく。",
            "私は不安。でも、それは“私が大事にしているものがある”サインでもある。",
            "少し休んでから考え直してもいい。焦らなくて大丈夫。"
        ]
    chosen = st.radio("候補（編集して使ってOK）", options=list(range(len(suggestions))),
                      format_func=lambda i: suggestions[i], index=0)
    default_text = suggestions[chosen] if 0 <= chosen < len(suggestions) else ""
    st.session_state.cbt["reframe_text"] = st.text_area("自由に整える：",
                                                        value=st.session_state.cbt["reframe_text"] or default_text,
                                                        height=90)
    st.session_state.cbt["distress_after"] = st.slider("いまのつらさ（言い換え後・任意）", 0, 10, st.session_state.cbt["distress_after"])
    st.markdown('</div>', unsafe_allow_html=True)

    colA, colB = st.columns([1, 1])
    with colA:
        if st.button("💾 保存して完了（入力欄は初期化）"):
            now = datetime.now().isoformat(timespec="seconds")
            row = {
                "id": f"cbt-{now}",
                "ts": now,
                "fact": st.session_state.cbt["fact"],
                "auto_thought": st.session_state.cbt["auto_thought"],
                "extreme": st.session_state.cbt["gentle_checks"]["extreme"],
                "mind_read": st.session_state.cbt["gentle_checks"]["mind_read"],
                "catastrophe": st.session_state.cbt["gentle_checks"]["catastrophe"],
                "reframe_text": st.session_state.cbt["reframe_text"],
                "distress_before": st.session_state.cbt["distress_before"],
                "distress_after": st.session_state.cbt["distress_after"]
            }
            _append_csv(CBT_CSV, row)
            st.session_state.cbt = {
                "fact": "", "auto_thought": "", "distress_before": 5,
                "gentle_checks": {"extreme": False, "mind_read": False, "catastrophe": False},
                "reframe_text": "", "distress_after": 3
            }
            st.success("保存しました。ここまでできたの、ほんとうにすごい。今日はここまでで大丈夫だよ。")
    with colB:
        if st.button("🧼 入力欄だけ初期化（未保存は消えます）"):
            st.session_state.cbt = {
                "fact": "", "auto_thought": "", "distress_before": 5,
                "gentle_checks": {"extreme": False, "mind_read": False, "catastrophe": False},
                "reframe_text": "", "distress_after": 3
            }
            st.info("入力欄をリセットしました（履歴は残っています）。")

# -------------------- Reflection TAB --------------------
with tab_reflect:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("今日をそっとふり返る")
    st.caption("点数や評価じゃなく、心が少しやわらぐ書き方で。短くてOK。")

    # ★★★ ここが修正ポイント：date 型に正規化してから date_input へ ★★★
    current_date = st.session_state.reflection.get("date", date.today())
    if isinstance(current_date, str):
        try:
            current_date = date.fromisoformat(current_date)
        except Exception:
            current_date = date.today()
    st.session_state.reflection["date"] = st.date_input("日付", value=current_date)

    st.session_state.reflection["today_small_win"] = st.text_area(
        "今日できた小さなこと（1つで十分）",
        value=st.session_state.reflection["today_small_win"],
        placeholder="例）朝ごはんを食べられた／3分だけ机に向かった／返信を待てた",
        height=80
    )
    st.session_state.reflection["self_message"] = st.text_area(
        "いまの自分に一言かけるなら？",
        value=st.session_state.reflection["self_message"],
        placeholder="例）よくやってる。今日はここまでで十分。",
        height=80
    )
    st.session_state.reflection["note_for_tomorrow"] = st.text_area(
        "明日の自分へひとこと（任意）",
        value=st.session_state.reflection["note_for_tomorrow"],
        placeholder="例）9:00に一度だけメッセージを送る。深呼吸してからでOK。",
        height=80
    )
    st.session_state.reflection["loneliness"] = st.slider("いまの孤独感（0〜10）", 0, 10, st.session_state.reflection["loneliness"])
    st.markdown('</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("💾 リフレクションを保存（入力欄は初期化）"):
            now = datetime.now().isoformat(timespec="seconds")
            # 保存時だけ文字列へ
            dval = st.session_state.reflection["date"]
            date_str = dval.isoformat() if isinstance(dval, (datetime, date)) else str(dval)
            row = {
                "id": f"ref-{now}",
                "date": date_str,
                "ts_saved": now,
                "small_win": st.session_state.reflection["today_small_win"],
                "self_message": st.session_state.reflection["self_message"],
                "note_for_tomorrow": st.session_state.reflection["note_for_tomorrow"],
                "loneliness": st.session_state.reflection["loneliness"],
            }
            _append_csv(REFLECT_CSV, row)
            st.session_state.reflection = {
                "today_small_win": "",
                "self_message": "",
                "note_for_tomorrow": "",
                "loneliness": 5,
                "date": date.today()
            }
            st.success("保存しました。宝物みたいな言葉が増えていくね。")
    with col2:
        if st.button("🧼 入力欄だけ初期化（未保存は消えます）", key="clear_reflection"):
            st.session_state.reflection = {
                "today_small_win": "",
                "self_message": "",
                "note_for_tomorrow": "",
                "loneliness": 5,
                "date": date.today()
            }
            st.info("入力欄をリセットしました（履歴は残っています）。")

# -------------------- History TAB --------------------
with tab_history:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("CBTワークの履歴")
    df_cbt = _load_csv(CBT_CSV)
    if df_cbt.empty:
        st.caption("まだ保存されたCBTワークがありません。")
    else:
        query = st.text_input("キーワードで探す（事実・心の声・言い換え）", "")
        view = df_cbt.copy()
        if query.strip():
            q = query.strip().lower()
            for col in ["fact", "auto_thought", "reframe_text"]:
                view[col] = view[col].astype(str)
            mask = view["fact"].str.lower().str.contains(q) | view["auto_thought"].str.lower().str.contains(q) | view["reframe_text"].str.lower().str.contains(q)
            view = view[mask]
        if "ts" in view.columns:
            view = view.sort_values("ts", ascending=False)
        for _, r in view.head(50).iterrows():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"**🕒 {r.get('ts','')}**")
            colx, coly = st.columns([2,1])
            with colx:
                st.markdown(f"**出来事**：{r.get('fact','')}")
                st.markdown(f"**心の声**：{r.get('auto_thought','')}")
                st.markdown(f"**言い換え**：{r.get('reframe_text','')}")
            with coly:
                try:
                    b = int(r.get("distress_before", 0)); a = int(r.get("distress_after", 0))
                    st.markdown(f"つらさ: {b} → {a}")
                except Exception: pass
                tags = []
                if r.get("extreme", False): tags.append("極端に決めつけ")
                if r.get("mind_read", False): tags.append("心を決めつけ")
                if r.get("catastrophe", False): tags.append("最悪を予言")
                if tags:
                    st.caption("気づけた視点")
                    for t in tags: st.markdown(f"<span class='tag'>{t}</span>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        try:
            chart_df = df_cbt[["ts","distress_before","distress_after"]].copy()
            chart_df["ts"] = pd.to_datetime(chart_df["ts"])
            chart_df = chart_df.sort_values("ts").set_index("ts")
            st.line_chart(chart_df.rename(columns={"distress_before":"つらさ(前)","distress_after":"つらさ(後)"}))
        except Exception: pass
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("リフレクションの履歴")
    df_ref = _load_csv(REFLECT_CSV)
    if df_ref.empty:
        st.caption("まだ保存されたリフレクションがありません。")
    else:
        dfv = df_ref.copy()
        if "date" in dfv.columns:
            try:
                dfv["date"] = pd.to_datetime(dfv["date"])
                dfv = dfv.sort_values(["date","ts_saved"], ascending=False)
            except Exception: pass
        for _, r in dfv.head(50).iterrows():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"**📅 {r.get('date','')}**  —  🕒 {r.get('ts_saved','')}")
            st.markdown(f"**小さなできたこと**：{r.get('small_win','')}")
            st.markdown(f"**いまの自分への一言**：{r.get('self_message','')}")
            nt = r.get("note_for_tomorrow","")
            if isinstance(nt, str) and nt.strip():
                st.markdown(f"**明日の自分へ**：{nt}")
            try:
                st.markdown(f"**孤独感**：{int(r.get('loneliness',0))}/10")
            except Exception: pass
            st.markdown('</div>', unsafe_allow_html=True)
        try:
            chart2 = df_ref[["date","loneliness"]].copy()
            chart2["date"] = pd.to_datetime(chart2["date"])
            chart2 = chart2.sort_values("date").set_index("date")
            st.line_chart(chart2.rename(columns={"loneliness":"孤独感"}))
        except Exception: pass
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------- Export & Settings TAB --------------------
with tab_export:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("データのエクスポート（CSV）")
    st.caption("あとから分析したり、別のアプリに移したいときに使えるよ。")
    _download_button(_load_csv(CBT_CSV), "⬇️ CBTワークをダウンロード", "cbt_entries.csv")
    _download_button(_load_csv(REFLECT_CSV), "⬇️ リフレクションをダウンロード", "daily_reflections.csv")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("入力欄の初期化 / データの管理")
    st.caption("入力欄だけ初期化（履歴は残る）と、すべてのデータ削除（危険）を分けています。")
    c1, c2 = st.columns([1,1])
    with c1:
        if st.button("🧼 すべての入力欄を初期化（履歴は残る）"):
            st.session_state.cbt = {
                "fact": "", "auto_thought": "", "distress_before": 5,
                "gentle_checks": {"extreme": False, "mind_read": False, "catastrophe": False},
                "reframe_text": "", "distress_after": 3
            }
            st.session_state.reflection = {
                "today_small_win": "", "self_message": "", "note_for_tomorrow": "",
                "loneliness": 5, "date": date.today()
            }
            st.success("入力欄をすべて初期化しました（履歴は残っています）。")
    with c2:
        danger = st.checkbox("⚠️ すべての保存データ（CSV）を削除することに同意します")
        if st.button("🗑️ すべての保存データを削除（取り消し不可）", disabled=not danger):
            try:
                if CBT_CSV.exists(): CBT_CSV.unlink()
                if REFLECT_CSV.exists(): REFLECT_CSV.unlink()
                st.success("保存データを削除しました。はじめからやり直せます。")
            except Exception as e:
                st.error(f"削除でエラーが発生しました: {e}")

st.markdown("""
<div style="text-align:center; color:#6b6575; margin-top:18px;">
  <small>もし今、とてもつらくて危ないと感じるときは、あなたの地域の相談先にアクセスしてね。<br>
  命の安全がいちばん大切です。</small>
</div>
""", unsafe_allow_html=True)
