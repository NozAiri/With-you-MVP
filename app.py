# app.py — Sora (Intro-first, Polite JP, Pastel Aurora, One-page)
# 目的が最初の5秒で伝わる「イントロ画面」を追加。ワークは敬語ベース。
# パステル（オレンジ/ピンク/紫/水色）＋静止の星。ページ遷移なしの内部切替。

from datetime import datetime, date
from pathlib import Path
from typing import Optional
import pandas as pd
import streamlit as st

# ---------------- Page config ----------------
st.set_page_config(
    page_title="Sora — しんどい夜の3分ノート",
    page_icon="🌙",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------- Theme / CSS ----------------
def inject_css():
    st.markdown("""
<style>
:root{
  --text:#2a2731; --muted:#6f7180; --outline:#e8d7ff;
  --glass:rgba(255,255,255,.94); --glass-brd:rgba(185,170,255,.28);
  --btn-from:#ffa16d; --btn-to:#ff77a3;
  --chip:#fff6fb; --chip-brd:#ffd7f0;

  --tile-cbt-from:#ffb37c; --tile-cbt-to:#ffe0c2;
  --tile-ref-from:#ff9ec3; --tile-ref-to:#ffd6ea;
  --tile-his-from:#c4a4ff; --tile-his-to:#e8dbff;
  --tile-exp-from:#89d7ff; --tile-exp-to:#d4f2ff;
}

.stApp{
  background:
    radial-gradient(800px 520px at 0% -10%,  rgba(255,226,200,.55) 0%, transparent 60%),
    radial-gradient(720px 480px at 100% -8%, rgba(255,215,242,.55) 0%, transparent 60%),
    radial-gradient(900px 560px at -10% 100%, rgba(232,216,255,.45) 0%, transparent 60%),
    radial-gradient(900px 560px at 110% 100%, rgba(217,245,255,.46) 0%, transparent 60%),
    linear-gradient(180deg, #fffefd 0%, #fff8fb 28%, #f7f3ff 58%, #f2fbff 100%);
}
/* 控えめな静止の星 */
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
p,label,.stMarkdown,.stTextInput,.stTextArea{color:var(--text); font-size:1.06rem}
small{color:var(--muted)}

.card{
  background:var(--glass); border:1px solid var(--glass-brd);
  border-radius:20px; padding:16px; margin-bottom:14px;
  box-shadow:0 18px 36px rgba(80,70,120,.14); backdrop-filter:blur(8px);
}
.hr{height:1px; background:linear-gradient(to right,transparent,#c7b8ff,transparent); margin:10px 0 6px}

.tag{display:inline-block; padding:6px 12px; border-radius:999px;
  background:#f7f2ff; color:#3a2a5a; font-weight:800; margin:0 6px 6px 0; border:1px solid var(--outline)}

textarea, input, .stTextInput>div>div>input{
  border-radius:14px!important; background:#ffffff; color:#2a2731; border:1px solid #e9ddff;
}
.stSlider,.stRadio>div{color:var(--text)}
.stButton>button,.stDownloadButton>button{
  width:100%; padding:14px 16px; border-radius:999px; border:1px solid var(--outline);
  background:linear-gradient(180deg,var(--btn-from),var(--btn-to)); color:#fff; font-weight:900; font-size:1.04rem;
  box-shadow:0 12px 26px rgba(255,145,175,.22);
}
.stButton>button:hover{filter:brightness(.98)}

.tile-grid{display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:8px}
.tile .stButton>button{
  aspect-ratio:1/1; min-height:220px; border-radius:28px;
  text-align:left; padding:20px; white-space:normal; line-height:1.2;
  border:none; font-weight:900; font-size:1.18rem; color:#2d2a33;
  box-shadow:0 20px 36px rgba(60,45,90,.18);
  display:flex; align-items:flex-end; justify-content:flex-start;
}
.tile .stButton>button:after{content:"";}
.tile-cbt .stButton>button{background:linear-gradient(160deg,var(--tile-cbt-from),var(--tile-cbt-to))}
.tile-ref .stButton>button{background:linear-gradient(160deg,var(--tile-ref-from),var(--tile-ref-to))}
.tile-his .stButton>button{background:linear-gradient(160deg,var(--tile-his-from),var(--tile-his-to))}
.tile-exp .stButton>button{background:linear-gradient(160deg,var(--tile-exp-from),var(--tile-exp-to))}

.chips{display:flex; gap:8px; flex-wrap:wrap; margin:6px 0 10px}
.chips .stButton>button{
  background:var(--chip); color:#523a6a; border:1px solid var(--chip-brd);
  padding:8px 12px; height:auto; border-radius:999px; font-weight:900
}

/* モバイル */
@media (max-width: 640px){
  .tile-grid{grid-template-columns:1fr}
  .tile .stButton>button{min-height:180px}
  .block-container{padding-left:1rem; padding-right:1rem}
}
</style>
""", unsafe_allow_html=True)

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
    if df.empty: st.caption("（まだデータがございません）"); return
    st.download_button(label, df.to_csv(index=False).encode("utf-8"),
                       file_name=filename, mime="text/csv")

# ---------------- Session defaults (robust) ----------------
def ensure_cbt_defaults():
    if "cbt" not in st.session_state or not isinstance(st.session_state.cbt, dict):
        st.session_state.cbt = {}
    cbt = st.session_state.cbt
    flat_defaults = {
        "fact":"", "auto_thought":"", "distress_before":5, "prob_before":50,
        "evidence_for":"", "evidence_against":"", "reframe_text":"",
        "prob_after":40, "distress_after":3, "small_step":""
    }
    for k,v in flat_defaults.items(): cbt.setdefault(k, v)
    checks = cbt.setdefault("gentle_checks", {})
    for k in ["extreme","mind_read","catastrophe","fortune","self_blame"]:
        checks.setdefault(k, False)

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

st.session_state.setdefault("view","INTRO")  # ← 最初は必ずイントロ
ensure_cbt_defaults()
ensure_reflection_defaults()

# ---------------- Companion（やさしい声がけ） ----------------
def companion(emoji: str, text: str, sub: Optional[str]=None):
    st.markdown(
        f"""
<div class="card">
  <div style="font-weight:900; color:#2f2a3b">{emoji} {text}</div>
  {f"<div class='small' style='margin-top:4px; color:var(--muted)'>{sub}</div>" if sub else ""}
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
        companion("🌟","ここまで入力いただけて十分です。","短くても大丈夫です。")

# ---------------- Intro (FIRST VIEW) ----------------
def view_intro():
    # ヒーロー
    st.markdown("""
<div class="card" style="padding:22px;">
  <h2 style="margin:.1rem 0 .4rem; color:#2f2a3b;">しんどい夜の考えのループを、<b>3分で整理して落ち着きを取り戻す</b>。</h2>
  <p style="margin:.4rem 0;">短い質問にお答えいただくだけで、<b>いまの状況・ご自身の考え・次の一歩</b>がはっきりします。</p>
  <ul style="margin:.4rem 0 .2rem;">
    <li>⏱ <b>所要時間</b>：約3分</li>
    <li>🎯 <b>目的</b>：落ち着きを取り戻し、現実的な見方と小さな行動を決める</li>
    <li>🔒 <b>安心</b>：データは端末に保存／医療・診断ではありません</li>
  </ul>
</div>
""", unsafe_allow_html=True)

    cta1, cta2 = st.columns([3,2])
    with cta1:
        if st.button("今すぐ3分をはじめる", use_container_width=True):
            st.session_state.view = "CBT"
    with cta2:
        if st.button("ホームを見る", use_container_width=True):
            st.session_state.view = "HOME"

    # Q&Aカード
    st.markdown("""
<div class="card">
  <h3 style="margin:.2rem 0 .6rem;">初めての方へ</h3>
  <p><b>これは何ですか？</b><br>
  しんどい夜に、短時間で思考を整理し、落ち着きを取り戻すためのノートです。</p>

  <p><b>いつ使いますか？</b></p>
  <ul>
    <li>眠る前に考えが止まらないとき</li>
    <li>不安で判断がぶれるとき</li>
    <li>とりあえず状況を整えたいとき</li>
  </ul>

  <p><b>どう使いますか？（3ステップ）</b></p>
  <ol>
    <li>出来事を一行</li>
    <li>考えを一行</li>
    <li>次の一歩を一行（迷えば候補から選択）</li>
  </ol>

  <p><b>目指すゴール</b></p>
  <ul>
    <li>堂々巡りが落ち着く</li>
    <li><b>現実的な見方</b>が定まる</li>
    <li><b>具体的な一歩</b>が決まる</li>
  </ul>
</div>
""", unsafe_allow_html=True)

# ---------------- Quick switch ----------------
def quick_switch():
    st.markdown('<div class="chips">', unsafe_allow_html=True)
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    with c1:
        if st.button("👋 はじめに", key="qs_intro"): st.session_state.view="INTRO"
    with c2:
        if st.button("🏠 ホーム", key="qs_home"): st.session_state.view="HOME"
    with c3:
        if st.button("📓 整理ワーク", key="qs_cbt"): st.session_state.view="CBT"
    with c4:
        if st.button("📝 1日のふり返り", key="qs_ref"): st.session_state.view="REFLECT"
    with c5:
        if st.button("📚 記録を見る", key="qs_his"): st.session_state.view="HISTORY"
    with c6:
        if st.button("⬇️ エクスポート", key="qs_exp"): st.session_state.view="EXPORT"
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Home ----------------
def view_home():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 本日、どのように進められますか？")
    st.markdown('<div class="tile-grid">', unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1:
        st.markdown('<div class="tile tile-cbt">', unsafe_allow_html=True)
        if st.button("📓 整理ワーク\n（3分）", key="tile_cbt"): st.session_state.view="CBT"
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="tile tile-ref">', unsafe_allow_html=True)
        if st.button("📝 1日のふり返り", key="tile_ref"): st.session_state.view="REFLECT"
        st.markdown('</div>', unsafe_allow_html=True)
    c3,c4 = st.columns(2)
    with c3:
        st.markdown('<div class="tile tile-his">', unsafe_allow_html=True)
        if st.button("📚 記録を見る", key="tile_his"): st.session_state.view="HISTORY"
        st.markdown('</div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="tile tile-exp">', unsafe_allow_html=True)
        if st.button("⬇️ エクスポート / 設定", key="tile_exp"): st.session_state.view="EXPORT"
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

# ---------------- CBT (Polite) ----------------
def view_cbt():
    ensure_cbt_defaults()
    quick_switch()

    # 1) 事実
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("1) いま起きたこと（事実）")
    st.caption("気持ちや推測は次の欄で扱いますので、事実だけを短くご記入ください。")
    st.session_state.cbt["fact"] = st.text_area(
        "本日、どのようなことがございましたか？",
        value=st.session_state.cbt.get("fact",""),
        placeholder="例）21:20にメッセージを送りました。既読はまだです。明日は小テストがあります。",
        height=96, label_visibility="collapsed"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # 2) 心の声 + つらさ/確からしさ(前)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("2) こころの声（浮かんだ考え）")
    st.session_state.cbt["auto_thought"] = st.text_area(
        "その時、どのような考えが浮かびましたか？",
        value=st.session_state.cbt.get("auto_thought",""),
        placeholder="例）嫌われたのかもしれません…",
        height=88
    )
    cols = st.columns(2)
    with cols[0]:
        st.session_state.cbt["distress_before"] = st.slider(
            "いまのしんどさ（0〜10）", 0, 10, int(st.session_state.cbt.get("distress_before",5)))
    with cols[1]:
        st.session_state.cbt["prob_before"] = st.slider(
            "その考えをどの程度本当だと感じますか？（%）", 0, 100, int(st.session_state.cbt.get("prob_before",50)))
    support(distress=st.session_state.cbt["distress_before"])
    st.markdown('</div>', unsafe_allow_html=True)

    # 3) やさしい確認
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("3) やさしい確認")
    g = st.session_state.cbt["gentle_checks"]
    col1,col2,col3,col4,col5 = st.columns(5)
    with col1:
        g["extreme"] = st.checkbox("0か100で決めつけていませんか？", value=bool(g.get("extreme",False)))
    with col2:
        g["mind_read"] = st.checkbox("相手の気持ちを決めつけていませんか？", value=bool(g.get("mind_read",False)))
    with col3:
        g["catastrophe"] = st.checkbox("最悪だけを想像していませんか？", value=bool(g.get("catastrophe",False)))
    with col4:
        g["fortune"] = st.checkbox("まだ起きていない先を断言していませんか？", value=bool(g.get("fortune",False)))
    with col5:
        g["self_blame"] = st.checkbox("ご自身を過度に責めていませんか？", value=bool(g.get("self_blame",False)))

    hints=[]
    if g["extreme"]:     hints.append("一部うまくいかなくても、すべてが否定されるとは限りません。")
    if g["mind_read"]:   hints.append("相手の本音は、確かめないと分からないことが多いです。")
    if g["catastrophe"]: hints.append("一番悪い未来以外の可能性も並べてみましょう。")
    if g["fortune"]:     hints.append("現時点の情報で判断し、未来の予想は保留にしても大丈夫です。")
    if g["self_blame"]:  hints.append("出来事のすべてがご自身の責任とは限りません。")
    if hints:
        st.write("💡 ヒント")
        for h in hints: st.markdown(f"- {h}")
    st.markdown('</div>', unsafe_allow_html=True)

    # 4) 根拠
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("4) 根拠を分けて書く")
    cols = st.columns(2)
    with cols[0]:
        st.session_state.cbt["evidence_for"] = st.text_area(
            "その考えを支持する根拠", value=st.session_state.cbt.get("evidence_for",""), height=96)
    with cols[1]:
        st.session_state.cbt["evidence_against"] = st.text_area(
            "反対の根拠・例外", value=st.session_state.cbt.get("evidence_against",""), height=96)
    st.caption("片方だけでも構いません。短く箇条書きでご記入ください。")
    st.markdown('</div>', unsafe_allow_html=True)

    # 5) 言い換え + 一歩
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("5) 現実的な見方に整える")
    suggestions=[]
    if g["extreme"]:     suggestions.append("うまくいっていない部分はありますが、すべてが失敗とは言い切れません。")
    if g["mind_read"]:   suggestions.append("相手にも事情がある可能性があります。まずは事実から確認します。")
    if g["catastrophe"]: suggestions.append("不安はありますが、未来はひとつではありません。現時点の事実に基づいて考えます。")
    if g["fortune"]:     suggestions.append("今わかる範囲に焦点を当て、断定は避けます。")
    if g["self_blame"]:  suggestions.append("自分の影響は一部であり、すべてを背負う必要はありません。")
    if not suggestions:
        suggestions = [
            "いま分かっている事実に沿って考え直します。",
            "不安を認めつつ、確認できる情報を優先します。",
            "今日はここまでにして、明日また見直します。"
        ]
    idx = st.radio("候補（編集して構いません）", options=list(range(len(suggestions))),
                   format_func=lambda i:suggestions[i], index=0, horizontal=False)
    default_text = suggestions[idx] if 0 <= idx < len(suggestions) else ""
    st.session_state.cbt["reframe_text"] = st.text_area(
        "現実的な見方（1行程度）をご記入ください：",
        value=st.session_state.cbt.get("reframe_text","") or default_text, height=90)

    cols = st.columns(2)
    with cols[0]:
        st.session_state.cbt["prob_after"] = st.slider(
            "その見方はどの程度しっくりきますか？（%）", 0, 100, int(st.session_state.cbt.get("prob_after",40)))
    with cols[1]:
        st.session_state.cbt["distress_after"] = st.slider(
            "いまのしんどさ（見方の調整後）", 0, 10, int(st.session_state.cbt.get("distress_after",3)))

    st.session_state.cbt["small_step"] = st.text_input(
        "本日または明日に取れる小さな一歩を1つだけご記入ください：",
        value=st.session_state.cbt.get("small_step",""),
        placeholder="例）明日の午前に、テスト範囲を10分だけ確認します。"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # 保存・初期化
    c1,c2 = st.columns(2)
    with c1:
        if st.button("💾 保存して完了（入力欄を初期化）"):
            now = datetime.now().isoformat(timespec="seconds")
            g = st.session_state.cbt["gentle_checks"]
            row = {
                "id":f"cbt-{now}","ts":now,
                "fact":st.session_state.cbt.get("fact",""),
                "auto_thought":st.session_state.cbt.get("auto_thought",""),
                "distress_before":st.session_state.cbt.get("distress_before",0),
                "prob_before":st.session_state.cbt.get("prob_before",0),
                "extreme":g.get("extreme",False),"mind_read":g.get("mind_read",False),
                "catastrophe":g.get("catastrophe",False),"fortune":g.get("fortune",False),
                "self_blame":g.get("self_blame",False),
                "evidence_for":st.session_state.cbt.get("evidence_for",""),
                "evidence_against":st.session_state.cbt.get("evidence_against",""),
                "reframe_text":st.session_state.cbt.get("reframe_text",""),
                "prob_after":st.session_state.cbt.get("prob_after",0),
                "distress_after":st.session_state.cbt.get("distress_after",0),
                "small_step":st.session_state.cbt.get("small_step",""),
            }
            _append_csv(CBT_CSV,row)
            st.session_state.cbt = {}
            ensure_cbt_defaults()
            st.success("保存いたしました。お疲れさまでした。")
    with c2:
        if st.button("🧼 入力欄のみ初期化（未保存分は消去）"):
            st.session_state.cbt = {}
            ensure_cbt_defaults()
            st.info("入力欄を初期化いたしました（記録は残っています）。")

# ---------------- Reflection ----------------
def view_reflect():
    ensure_reflection_defaults()
    quick_switch()
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("本日をやさしくふり返る")
    st.caption("点数ではなく、心が少しやわらぐ表現で短くご記入ください。")
    st.session_state.reflection["date"] = st.date_input("日付", value=st.session_state.reflection["date"])
    st.session_state.reflection["today_small_win"] = st.text_area(
        "本日できたことを1つだけ挙げてください：",
        value=st.session_state.reflection.get("today_small_win",""), height=76
    )
    st.session_state.reflection["self_message"] = st.text_area(
        "いまのご自身へ一言かけるとしたら：",
        value=st.session_state.reflection.get("self_message",""), height=76
    )
    st.session_state.reflection["note_for_tomorrow"] = st.text_area(
        "明日のご自身へのメモ（任意）：",
        value=st.session_state.reflection.get("note_for_tomorrow",""), height=76
    )
    st.session_state.reflection["loneliness"] = st.slider(
        "いまの孤独感（0〜10）", 0, 10, int(st.session_state.reflection.get("loneliness",5)))
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
            st.session_state.reflection = {}
            ensure_reflection_defaults()
            st.success("保存いたしました。")
    with c2:
        if st.button("🧼 入力欄のみ初期化（未保存分は消去）"):
            st.session_state.reflection = {}
            ensure_reflection_defaults()
            st.info("入力欄を初期化いたしました（記録は残っています）。")

# ---------------- History ----------------
def view_history():
    quick_switch()
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📓 記録（整理ワーク）")
    df = _load_csv(CBT_CSV)
    if df.empty:
        st.caption("まだ保存されたワークはございません。最初の3分を行うと、こちらに一覧が表示されます。")
    else:
        q = st.text_input("キーワード検索（事実・考え・見方・一歩）", "")
        view = df.copy()
        if q.strip():
            q = q.strip().lower()
            for c in ["fact","auto_thought","reframe_text","evidence_for","evidence_against","small_step"]:
                view[c] = view[c].astype(str)
            mask = (
                view["fact"].str.lower().str.contains(q) |
                view["auto_thought"].str.lower().str.contains(q) |
                view["reframe_text"].str.lower().str.contains(q) |
                view["evidence_for"].str.lower().str.contains(q) |
                view["evidence_against"].str.lower().str.contains(q) |
                view["small_step"].str.lower().str.contains(q)
            )
            view = view[mask]
        if "ts" in view.columns:
            view = view.sort_values("ts", ascending=False)
        for _, r in view.head(50).iterrows():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"**🕒 {r.get('ts','')}**")
            st.markdown(f"**出来事**：{r.get('fact','')}")
            st.markdown(f"**考え**：{r.get('auto_thought','')}")
            st.markdown(f"**根拠（支持）**：{r.get('evidence_for','')}")
            st.markdown(f"**根拠（反証）**：{r.get('evidence_against','')}")
            st.markdown(f"**現実的な見方**：{r.get('reframe_text','')}")
            try:
                b = int(r.get("distress_before",0)); a = int(r.get("distress_after",0))
                pb = int(r.get("prob_before",0)); pa = int(r.get("prob_after",0))
                st.caption(f"しんどさ: {b} → {a} ／ 確からしさ: {pb}% → {pa}%")
            except Exception:
                pass
            step = r.get("small_step","")
            if isinstance(step,str) and step.strip():
                st.markdown(f"**小さな一歩**：{step}")
            tags=[]
            if r.get("extreme",False): tags.append("0/100の決めつけ")
            if r.get("mind_read",False): tags.append("相手の気持ちの決めつけ")
            if r.get("catastrophe",False): tags.append("最悪の想像")
            if r.get("fortune",False): tags.append("先の断言")
            if r.get("self_blame",False): tags.append("過度の自己責任")
            if tags:
                st.markdown(" ".join([f"<span class='tag'>{t}</span>" for t in tags]), unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        try:
            chart = df[["ts","distress_before","distress_after"]].copy()
            chart["ts"] = pd.to_datetime(chart["ts"])
            chart = chart.sort_values("ts").set_index("ts")
            st.line_chart(chart.rename(columns={"distress_before":"しんどさ(前)","distress_after":"しんどさ(後)"}))
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
    quick_switch()
    st.subheader("⬇️ エクスポート & 設定")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("**データのエクスポート（CSV）**")
    _download_button(_load_csv(CBT_CSV), "⬇️ 整理ワーク（CSV）をダウンロード", "cbt_entries.csv")
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

# ---------------- Render ----------------
view = st.session_state.view
if view == "INTRO":
    view_intro()
elif view == "HOME":
    view_home()
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
