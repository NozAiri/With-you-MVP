# app.py — Companion tone / 2min note / no action-forcing
# 入口：絵文字（ラベルなし）→ きっかけ → 手がかり → 一言で言い直す
# トグルUI（選択状態が残る）＋簡易バイブ（対応端末のみ）。
# 医療/診断ではありません。行動は決めさせません。

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

/* Emoji grid */
.emoji-grid{display:grid; grid-template-columns:repeat(8,1fr); gap:8px; margin:8px 0 6px}
.emoji-btn>button{
  width:100%!important; aspect-ratio:1/1; border-radius:18px!important;
  font-size:1.55rem!important; background:#fff; border:1px solid #eadfff!important;
  box-shadow:0 8px 16px rgba(60,45,90,.06);
}
/* 選択中は少し濃く・縁取り */
.emoji-on>button{
  background:linear-gradient(180deg,#ffc6a3,#ff9fbe)!important;
  border:1px solid #ff80b0!important;
}

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
    if df.empty: st.caption("（まだデータはございません）"); return
    st.download_button(label, df.to_csv(index=False).encode("utf-8"),
                       file_name=filename, mime="text/csv")

# ---------------- Session defaults ----------------
def ensure_cbt_defaults():
    if "cbt" not in st.session_state or not isinstance(st.session_state.cbt, dict):
        st.session_state.cbt = {}
    cbt = st.session_state.cbt
    flat_defaults = {
        "emotions": [],    # 入口：絵文字の選択
        "trigger_tags": [],# きっかけチップ
        "trigger_free":"", # 任意の一言
        "fact":"",         # 見えている手がかり（事実）
        "alt":"",          # ほかの手がかり（別の説明/例外）
        "checks":{         # 結論は少し保留（やわらかい点検）
            "extreme":False,"mind_read":False,"fortune":False,"catastrophe":False
        },
        "distress_before":5,
        "prob_before":50,
        "rephrase":"",     # 一言で言い直す（最終）
        "prob_after":40,
        "distress_after":4
    }
    for k,v in flat_defaults.items():
        if isinstance(v, dict):
            cbt.setdefault(k,{})
            for kk,vv in v.items(): cbt[k].setdefault(kk,vv)
        else:
            cbt.setdefault(k,v)

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
ensure_cbt_defaults(); ensure_reflection_defaults()

# ---------------- Gentle companion ----------------
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

# ---------------- 小さなハプティクス（対応端末限定） ----------------
def vibrate(ms=12):
    st.markdown(
        f"""
<script>
  if ('vibrate' in navigator) {{
    try {{ navigator.vibrate({ms}); }} catch(e) {{}}
  }}
</script>
""",
        unsafe_allow_html=True,
    )

# ---------------- INTRO ----------------
def view_intro():
    st.markdown("""
<div class="card" style="padding:22px;">
  <h2 style="margin:.1rem 0 .6rem; color:#2f2a3b;">
    いま感じていることを、<b>いっしょに静かに整えます。</b>
  </h2>
  <ul style="margin:.4rem 0 .6rem;">
    <li>⏱ <b>所要</b>：約2分 ／ <b>3ステップ</b></li>
    <li>🎯 <b>内容</b>：気持ちのきっかけ→手がかり→一言で言い直す</li>
    <li>🔒 <b>安心</b>：この端末の中だけ／いつでも全消去可／医療・診断ではありません</li>
  </ul>
  <p style="margin:.2rem 0 .2rem; color:#6f7180">
    ※ 空欄があっても大丈夫です。途中でやめても問題ございません。
  </p>
</div>
""", unsafe_allow_html=True)

    cta1, cta2 = st.columns([3,2])
    with cta1:
        if st.button("今すぐはじめる（約2分）", use_container_width=True):
            st.session_state.view = "CBT"
    with cta2:
        if st.button("ホームを見る", use_container_width=True):
            st.session_state.view = "HOME"

    st.markdown("""
<div class="card">
  <h3 style="margin:.2rem 0 .6rem;">初めての方向け（Q&A）</h3>
  <p><b>これは何ですか？</b><br>
  しんどい夜に、短時間で“考え方”を静かに確かめるためのノートです。</p>
  <p><b>いつ使いますか？</b></p>
  <ul>
    <li>寝る前に考えが止まらないとき</li>
    <li>返信が来なくて不安なとき</li>
    <li>提出・発表を前に落ち着かせたいとき</li>
  </ul>
  <p><b>どう進みますか？（3ステップ）</b></p>
  <ol>
    <li>いまの気持ちを絵文字で選ぶ／近いきっかけを選ぶ</li>
    <li>見えている手がかり／ほかの手がかりを並べる</li>
    <li>いまの考えを一言で言い直す（行動は決めなくてOK）</li>
  </ol>
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
        if st.button("📓 2分ノート", key="qs_cbt"): st.session_state.view="CBT"
    with c4:
        if st.button("📝 1日のふり返り", key="qs_ref"): st.session_state.view="REFLECT"
    with c5:
        if st.button("📚 記録を見る", key="qs_his"): st.session_state.view="HISTORY"
    with c6:
        if st.button("⬇️ エクスポート", key="qs_exp"): st.session_state.view="EXPORT"
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- HOME ----------------
def view_home():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 本日、どのように進められますか？")
    st.markdown('<div class="tile-grid">', unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1:
        st.markdown('<div class="tile tile-cbt">', unsafe_allow_html=True)
        if st.button("📓 2分ノート", key="tile_cbt"): st.session_state.view="CBT"
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

# ---------------- Emoji & chips (toggle UI) ----------------
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
            # CSSクラスを当てるために空divでラップ
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(f"{e}", key=f"emo_btn_{i}", use_container_width=True):
                if on: chosen.remove(e)
                else: chosen.add(e)
                vibrate(12)
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    picked = " ".join(list(chosen)) or "（未選択）"
    st.caption(f"選択中：{picked}")
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
            lbl = f"{label}{' ✓' if on else ''}"
            if st.button(lbl, key=f"trg_{val}", use_container_width=True):
                if on: chosen.remove(val)
                else: chosen.add(val)
                vibrate(10)
    st.markdown('</div>', unsafe_allow_html=True)
    human = [lbl for (lbl, v) in TRIGGER_DEFS if v in chosen]
    st.caption("選択中：" + (" / ".join(human) if human else "（未選択）"))
    return list(chosen)

# ---------------- CBT（2分ノート：行動なし） ----------------
def view_cbt():
    ensure_cbt_defaults()
    quick_switch()

    # Step0 絵文字
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
        placeholder="例）21:20に送信→返信まだ／「また失敗する」と浮かんだ",
        height=76
    )
    cols = st.columns(2)
    with cols[0]:
        st.session_state.cbt["distress_before"] = st.slider("いまのしんどさ（0〜10）", 0, 10, int(st.session_state.cbt.get("distress_before",5)))
    with cols[1]:
        st.session_state.cbt["prob_before"] = st.slider("いまの考えは、どのくらい“ありえそう”？（%）", 0, 100, int(st.session_state.cbt.get("prob_before",50)))
    support(distress=st.session_state.cbt["distress_before"])
    st.markdown('</div>', unsafe_allow_html=True)

    # Step2 手がかり
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("手がかりを並べてみる")
    st.caption("片方だけでも構いません。思いついた分だけで結構です。")
    cols = st.columns(2)
    with cols[0]:
        st.session_state.cbt["fact"] = st.text_area(
            "見えている手がかり（事実）",
            value=st.session_state.cbt.get("fact",""),
            placeholder="例）返信がまだ来ていない／明日が提出日 など", height=96)
    with cols[1]:
        st.session_state.cbt["alt"] = st.text_area(
            "ほかの手がかり（別の説明・例外）",
            value=st.session_state.cbt.get("alt",""),
            placeholder="例）移動中かも／前も夜に返ってきた など", height=96)

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    st.subheader("結論は少しだけ保留にする")
    st.caption("当てはまるものだけ軽くチェック。“かもしれない”の視点で。")
    g = st.session_state.cbt["checks"]
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        g["extreme"] = st.checkbox("0/100で考えたかも", value=bool(g.get("extreme",False)))
    with c2:
        g["mind_read"] = st.checkbox("心を読み切った気になったかも", value=bool(g.get("mind_read",False)))
    with c3:
        g["fortune"] = st.checkbox("先の展開を決め打ちしたかも", value=bool(g.get("fortune",False)))
    with c4:
        g["catastrophe"] = st.checkbox("最悪だけを優先したかも", value=bool(g.get("catastrophe",False)))
    st.markdown('</div>', unsafe_allow_html=True)

    # Step3 一言で言い直す
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("いまの考えを、一言で言い直す")
    st.caption("分からない部分は保留で大丈夫です。選んでから編集いただけます。")
    starters = [
        "分からない部分は保留にします。",
        "可能性は1つではありません。",
        "途中経過として受け止めます。",
        "今ある事実の範囲で考え直します。",
        "決め打ちはいったん止めて、様子を見ます。"
    ]
    idx = st.radio("候補（編集可）", options=list(range(len(starters))),
                   format_func=lambda i: starters[i], index=0, horizontal=False)
    default_text = starters[idx] if 0 <= idx < len(starters) else ""
    st.session_state.cbt["rephrase"] = st.text_area(
        "一言（1行程度）",
        value=st.session_state.cbt.get("rephrase","") or default_text,
        height=84
    )

    ccols = st.columns(2)
    with ccols[0]:
        st.session_state.cbt["prob_after"] = st.slider("いまの言い直しは、どのくらい“しっくり”？（%）", 0, 100, int(st.session_state.cbt.get("prob_after",40)))
    with ccols[1]:
        st.session_state.cbt["distress_after"] = st.slider("いまのしんどさ（言い直し後）", 0, 10, int(st.session_state.cbt.get("distress_after",4)))
    st.markdown('</div>', unsafe_allow_html=True)

    # 保存・初期化
    c1,c2 = st.columns(2)
    with c1:
        if st.button("💾 保存して完了（入力欄を初期化）"):
            now = datetime.now().isoformat(timespec="seconds")
            row = {
                "id":f"cbt-{now}","ts":now,
                "emotions":" ".join(st.session_state.cbt.get("emotions",[])),
                "trigger_tags":" ".join(st.session_state.cbt.get("trigger_tags",[])),
                "trigger_free":st.session_state.cbt.get("trigger_free",""),
                "fact":st.session_state.cbt.get("fact",""),
                "alt":st.session_state.cbt.get("alt",""),
                "extreme":st.session_state.cbt["checks"].get("extreme",False),
                "mind_read":st.session_state.cbt["checks"].get("mind_read",False),
                "fortune":st.session_state.cbt["checks"].get("fortune",False),
                "catastrophe":st.session_state.cbt["checks"].get("catastrophe",False),
                "distress_before":st.session_state.cbt.get("distress_before",0),
                "prob_before":st.session_state.cbt.get("prob_before",0),
                "rephrase":st.session_state.cbt.get("rephrase",""),
                "prob_after":st.session_state.cbt.get("prob_after",0),
                "distress_after":st.session_state.cbt.get("distress_after",0),
            }
            _append_csv(CBT_CSV,row)
            st.session_state.cbt = {}
            ensure_cbt_defaults()
            st.success("保存いたしました。ここで完了です。行動は決めなくて大丈夫です。")
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
        "本日できたことを1つだけ：",
        value=st.session_state.reflection.get("today_small_win",""), height=76
    )
    st.session_state.reflection["self_message"] = st.text_area(
        "いまのご自身へ一言：",
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
    st.subheader("📓 記録（2分ノート）")
    df = _load_csv(CBT_CSV)
    if df.empty:
        st.caption("まだ保存されたノートはございません。最初の2分を行うと、こちらに一覧が表示されます。")
    else:
        q = st.text_input("キーワード検索（手がかり・言い直し・きっかけ・感情）", "")
        view = df.copy()
        text_cols = ["fact","alt","rephrase","trigger_free","emotions","trigger_tags"]
        for c in text_cols:
            if c in view.columns: view[c] = view[c].astype(str)
        if q.strip():
            q = q.strip().lower()
            mask = False
            for c in text_cols:
                if c in view.columns:
                    mask = mask | view[c].str.lower().str.contains(q)
            view = view[mask]
        if "ts" in view.columns:
            view = view.sort_values("ts", ascending=False)
        for _, r in view.head(50).iterrows():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"**🕒 {r.get('ts','')}**")
            st.markdown(f"**感情**：{r.get('emotions','')}")
            st.markdown(f"**きっかけ**：{r.get('trigger_tags','')} ／ {r.get('trigger_free','')}")
            st.markdown(f"**見えている手がかり**：{r.get('fact','')}")
            st.markdown(f"**ほかの手がかり**：{r.get('alt','')}")
            st.markdown(f"**一言で言い直す**：{r.get('rephrase','')}")
            try:
                b = int(r.get("distress_before",0)); a = int(r.get("distress_after",0))
                pb = int(r.get("prob_before",0)); pa = int(r.get("prob_after",0))
                st.caption(f"しんどさ: {b} → {a} ／ 体感の確からしさ: {pb}% → {pa}%")
            except Exception:
                pass
            tags=[]
            if r.get("extreme",False): tags.append("0/100の見方")
            if r.get("mind_read",False): tags.append("読心の見方")
            if r.get("fortune",False): tags.append("先の決め打ち")
            if r.get("catastrophe",False): tags.append("最悪を優先")
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
