# app.py — Sora（パステル版：ナビ修正／多選択感情／行動活性化）
from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Tuple, List
import pandas as pd
import streamlit as st
import time, json

# ---------------- Page config ----------------
st.set_page_config(
    page_title="Sora — しんどい夜の2分ノート",
    page_icon="🌙",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------- Theme / CSS (pastel) ----------------
def inject_css():
    st.markdown("""
<style>
:root{
  /* pastel navy & dusty pink */
  --bg:#121429; --panel:#1a1c34; --panel-brd:#343764;
  --text:#fbfaff; --muted:#c3c6e6; --outline:#9aa0ff;
  --grad-from:#ffc9d8; --grad-to:#ff9bb9; /* くすみピンク */
  --chip-brd:rgba(255,189,222,.35);

  --tile-a:#ffd3a8; --tile-b:#ffe8cf;
  --tile-c:#ffc3d8; --tile-d:#ffe0ef;
  --tile-e:#d6c8ff; --tile-f:#efe9ff;
  --tile-g:#bfe9ff; --tile-h:#e7f6ff;
}
html, body, .stApp{background:var(--bg)}
.block-container{max-width:980px; padding-top:.4rem; padding-bottom:2rem}
h1,h2,h3{color:var(--text); letter-spacing:.2px}
p,label,.stMarkdown,.stTextInput,.stTextArea{color:var(--text); font-size:1.04rem}
small{color:var(--muted)}
.card{background:var(--panel); border:1px solid var(--panel-brd); border-radius:20px; padding:18px; margin-bottom:14px;
      box-shadow:0 18px 36px rgba(10,10,24,.28)}

.hero{
  border:2px solid rgba(255,231,238,.55);
  background:linear-gradient(180deg, rgba(32,34,70,.55), rgba(26,27,56,.55));
  padding:22px; border-radius:24px; margin:10px 0 14px;
}
.hero h1{color:var(--text); font-size:1.45rem; font-weight:900; margin:.2rem 0 1rem}
.hero .lead{font-size:1.8rem; font-weight:900; color:#ffe3ee; margin:.2rem 0 1.1rem}
.hero .box{border:2px solid rgba(255,231,238,.55); border-radius:18px; padding:14px; margin:10px 0 14px;
           background:linear-gradient(180deg, rgba(28,29,66,.65), rgba(23,24,52,.65)); color:var(--text)}
.hero .actions{display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:10px}
.hero .chips{display:flex; gap:8px; flex-wrap:wrap; margin:8px 0 0}

/* Topbar nav - always enabled */
.topbar{position:sticky; top:0; z-index:10; background:rgba(18,20,41,.7); backdrop-filter:blur(8px);
        border-bottom:1px solid #2a2e5c; margin:0 -12px 8px; padding:8px 12px 10px}
.topnav{display:flex; gap:8px; flex-wrap:wrap; margin:2px 0}
.topnav .nav-btn>button{
  background:#fcfcff !important; color:#1f2142 !important; border:1px solid #dee0f0 !important;
  height:auto !important; padding:9px 12px !important; border-radius:12px !important; font-weight:700 !important; font-size:.95rem !important;
}
.topnav .active>button{background:#f6f6ff !important; border:2px solid var(--outline) !important}
.nav-hint{font-size:.78rem; color:#aeb2df; margin:0 2px 6px 2px}

/* Buttons */
.stButton>button,.stDownloadButton>button{
  width:100%; padding:12px 16px; border-radius:999px; border:1px solid var(--chip-brd);
  background:linear-gradient(180deg,var(--grad-from),var(--grad-to)); color:#3a2740; font-weight:900; font-size:1.02rem;
  box-shadow:0 14px 28px rgba(255,155,185,.18)
}
.stButton>button:hover{filter:brightness(.98)}

/* Home tiles (BIG) */
.tile-grid{display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:8px}
.tile .stButton>button{
  aspect-ratio:1/1; min-height:184px; border-radius:28px; text-align:left; padding:20px; white-space:normal; line-height:1.2;
  border:none; font-weight:900; font-size:1.16rem; color:#2d2a33; box-shadow:0 16px 32px rgba(8,8,22,.35);
  display:flex; align-items:flex-end; justify-content:flex-start;
}
.tile-a .stButton>button{background:linear-gradient(160deg,var(--tile-a),var(--tile-b))}
.tile-b .stButton>button{background:linear-gradient(160deg,var(--tile-c),var(--tile-d))}
.tile-c .stButton>button{background:linear-gradient(160deg,var(--tile-e),var(--tile-f))}
.tile-d .stButton>button{background:linear-gradient(160deg,var(--tile-g),var(--tile-h))}

/* 呼吸丸 */
.breath-wrap{display:flex; justify-content:center; align-items:center; padding:8px 0 4px}
.breath-circle{
  width:220px; height:220px; border-radius:999px;
  background:radial-gradient(circle at 50% 40%, #ffeef5, #ffd9ea 60%, #e3defd 100%);
  box-shadow:0 18px 38px rgba(255,170,190,.16), inset 0 -10px 25px rgba(60,60,140,.22);
  transform:scale(var(--scale, 1)); transition:transform .9s ease-in-out, filter .3s ease-in-out;
  border:2px solid rgba(255,231,238,.55);
}
.phase-pill{display:inline-block; padding:.2rem .7rem; border-radius:999px; background:rgba(210,206,255,.16);
  color:#f2f1ff; border:1px solid rgba(180,176,255,.38); font-weight:700}
.count-box{font-size:40px; font-weight:900; text-align:center; color:#fff; padding:2px 0}
.subtle{color:#ccd0ff; font-size:.92rem}

/* Emotion pills (SMALL & OUTLINED) — 見た目をBIGタイルと差別化 */
.emopills{display:grid; grid-template-columns:repeat(6,1fr); gap:8px}
.emopills .stButton>button{
  background:#ffffff !important; color:#1e1e2a !important;
  border:1px solid #e5e6f7 !important; border-radius:999px !important;
  box-shadow:none !important; font-weight:700 !important; padding:8px 10px !important;
}
.emopills .on>button{border:2px solid #ffb6cc !important; background:#fff6fb !important}

/* Chips */
.chips{display:flex; gap:8px; flex-wrap:wrap; margin:8px 0 10px}
.chips .chip-btn>button{
  background:#fff6fb; color:#3a2144; border:1px solid var(--chip-brd)!important;
  padding:8px 12px; height:auto; border-radius:999px!important; font-weight:900; box-shadow:0 8px 16px rgba(255,153,188,.10)
}

/* Inputs */
textarea, input, .stTextInput>div>div>input{border-radius:14px!important; background:#12142f; color:#f5f3ff; border:1px solid #3a3d66}

/* Mobile */
@media (max-width: 680px){
  .tile-grid{grid-template-columns:1fr}
  .tile .stButton>button{min-height:170px}
  .emopills{grid-template-columns:repeat(4,1fr)}
  .block-container{padding-left:1rem; padding-right:1rem}
}
</style>
""", unsafe_allow_html=True)

inject_css()

# ---------------- Data paths ----------------
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
CBT_CSV    = DATA_DIR / "cbt_entries.csv"    # 互換保存
BREATH_CSV = DATA_DIR / "breath_sessions.csv"
MIX_CSV    = DATA_DIR / "mix_note.csv"       # 統合ノート
STUDY_CSV  = DATA_DIR / "study_blocks.csv"

def now_ts(): return datetime.now().isoformat(timespec="seconds")

def load_csv(p: Path) -> pd.DataFrame:
    if p.exists():
        try: return pd.read_csv(p)
        except Exception: return pd.DataFrame()
    return pd.DataFrame()

def append_csv(p: Path, row: dict):
    df = load_csv(p)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(p, index=False)

# ---------------- Session defaults ----------------
st.session_state.setdefault("view", "HOME")
st.session_state.setdefault("breath_mode", "gentle")
st.session_state.setdefault("breath_running", False)
st.session_state.setdefault("breath_success", 0)
st.session_state.setdefault("note", {
    "emos": [], "reason": "", "oneword": "", "step":"", "switch":"", "memo":"", "sleep_h":6.5
})

# ---------------- Top Nav（常に操作可／ページ移動で呼吸停止） ----------------
def navigate(to_key: str):
    # ページ移動時は呼吸を停止してナビを常に効かせる
    st.session_state.breath_running = False
    st.session_state.view = to_key

def top_nav():
    st.markdown('<div class="topbar">', unsafe_allow_html=True)
    st.markdown('<div class="nav-hint">ページ移動</div>', unsafe_allow_html=True)
    st.markdown('<div class="topnav">', unsafe_allow_html=True)
    pages = [
        ("HOME", "🏠 ホーム"),
        ("BREATH", "🌙 心を休める呼吸ワーク"),
        ("NOTE", "📝 心を整える"),
        ("STURDY", "📚 Sturdy Tracker"),
        ("EXPORT", "⬇️ 記録・エクスポート"),
    ]
    cols = st.columns(len(pages))
    for i,(key,label) in enumerate(pages):
        cls = "nav-btn active" if st.session_state.view==key else "nav-btn"
        with cols[i]:
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                navigate(key)
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

# ---------------- HOME ----------------
def view_home():
    st.markdown("""
<div class="hero">
  <h1>言葉の前に、息をひとつ。</h1>
  <div class="lead">“リラックスする” 小さな習慣。</div>
  <div class="box">
    <div><b>できること</b>：呼吸でおだやかさを取り戻し、複数の感情をやさしく整理し、<br>
    小さな一歩で“落ち着いた自分”に。データはこの端末だけ。</div>
    <div class="actions">
      <div>""", unsafe_allow_html=True)
    if st.button("🌙 今すぐ 呼吸をはじめる）", use_container_width=True, key="home_go_breath"):
        navigate("BREATH")
    st.markdown("</div><div>", unsafe_allow_html=True)
    if st.button("📝 心を整える）", use_container_width=True, key="home_go_note"):
        navigate("NOTE")
    st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="tile-grid">', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="tile tile-a">', unsafe_allow_html=True)
        if st.button("🌙 心を休める呼吸ワーク", key="tile_breath"): navigate("BREATH")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="tile tile-b">', unsafe_allow_html=True)
        if st.button("📝 心を整える（最少タップ）", key="tile_note"): navigate("NOTE")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

# ---------------- 呼吸（安全設計×自動） ----------------
def breath_patterns() -> Dict[str, Tuple[int,int,int]]:
    return {"gentle": (4,0,6), "calm": (5,2,6)}

def compute_cycles(target_sec: int, pat: Tuple[int,int,int]) -> int:
    return max(1, round(sum(pat) and target_sec / sum(pat)))

def run_breath_session(total_sec: int=90):
    inhale, hold, exhale = breath_patterns()[st.session_state.breath_mode]
    cycles = compute_cycles(total_sec, (inhale,hold,exhale))
    st.session_state.breath_running = True

    st.subheader("いっしょに息を。ここにいていいよ。")
    st.caption("※ 目を閉じても分かるフェーズ表示。")

    phase_box = st.empty(); count_box = st.empty(); circle_holder = st.empty()
    prog = st.progress(0, text="呼吸セッション")
    elapsed = 0; total = cycles * (inhale + hold + exhale)

    def tick(label, secs, scale_from, scale_to):
        nonlocal elapsed
        for t in range(secs,0,-1):
            if not st.session_state.breath_running: return False
            ratio = (secs - t)/(secs-1) if secs>1 else 1
            scale = scale_from + (scale_to-scale_from)*ratio
            phase_box.markdown(f"<span class='phase-pill'>{label}</span>", unsafe_allow_html=True)
            circle_holder.markdown(f"<div class='breath-wrap'><div class='breath-circle' style='--scale:{scale}'></div></div>", unsafe_allow_html=True)
            count_box.markdown(f"<div class='count-box'>{t}</div>", unsafe_allow_html=True)
            elapsed += 1; prog.progress(min(int(elapsed/total*100), 100))
            time.sleep(1)
        return True

    col_stop, col_hint = st.columns([1,2])
    with col_stop:
        if st.button("× 停止", use_container_width=True): st.session_state.breath_running=False
    with col_hint:
        st.markdown('<div class="subtle">息止めは最大2秒。無理はしないでOK。</div>', unsafe_allow_html=True)

    for _ in range(cycles):
        if not st.session_state.breath_running: break
        if not tick("吸う", inhale, 1.0, 1.6): break
        if hold>0 and st.session_state.breath_running:
            if not tick("とまる", hold, 1.6, 1.6): break
        if not st.session_state.breath_running: break
        if not tick("はく", exhale, 1.6, 1.0): break

    finished = st.session_state.breath_running
    st.session_state.breath_running = False

    if finished:
        st.success("お疲れ様です")
        st.session_state.breath_mode = "calm" if st.session_state.breath_mode=="gentle" else "calm"
    else:
        st.info("いつでも再開できます。")

    note = st.text_input("メモ")
    if st.button("💾 保存", type="primary"):
        append_csv(BREATH_CSV, {
            "ts": now_ts(), "mode": st.session_state.breath_mode,
            "target_sec": total_sec, "inhale": inhale, "hold": hold, "exhale": exhale, "note": note
        })
        st.success("保存しました。")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("もう一度（90秒）"): run_breath_session(90)
    with c2:
        if st.button("短め（60秒）"): run_breath_session(60)
    with c3:
        if st.button("ながめ（180秒）"): run_breath_session(180)

def view_breath():
    st.subheader("🌙 心を休める呼吸ワーク（安全設計）")
    mode_name = "穏やか版（吸4・吐6）" if st.session_state.breath_mode=="gentle" else "落ち着き用（吸5・止2・吐6）"
    st.caption(f"現在のガイド：{mode_name}（自動最適化）")
    if not st.session_state.breath_running:
        if st.button("開始（約90秒）", type="primary"): run_breath_session(90)
    else:
        st.info("実行中です…")

# ---------------- 心を整える（複数感情／行動活性化） ----------------
EMOJI_CHOICES = ["😟不安","😢悲しい","😠いらだち","😳恥ずかしい","😊うれしい"]
SWITCHES = ["外の光を浴びる","体を少し動かす","誰かと軽くつながる","小さな達成感","環境を整える","ごほうび少し"]
BA_SUGGEST = ["水を一口","窓を少し開ける","外の光を5分","返信はスタンプだけ","英単語3つだけ","机の上を30秒片付ける"]

def view_note():
    st.subheader("📝 心を整える（2分で完結）")
    n = st.session_state.note

    # 1) 今の気持ち（複数選択）
    st.caption("今の気持ち（複数OK）")
    st.markdown('<div class="emopills">', unsafe_allow_html=True)
    cols = st.columns(6)
    for i, label in enumerate(EMOJI_CHOICES):
        with cols[i%6]:
            sel = label in n["emos"]
            cls = "on" if sel else ""
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(("✓ " if sel else "") + label, key=f"emo_{i}"):
                if sel: n["emos"].remove(label)
                else:   n["emos"].append(label)
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 2) 理由（一行）※旧きっかけ
    n["reason"] = st.text_input("その絵文字を選んだ理由（1行）", value=n["reason"], placeholder="例：返信が来ない／提出が近い")

    # 3) 一言メモ（自分の言葉）
    n["oneword"] = st.text_input("いまの気持ちを言葉にすると？（一言）", value=n["oneword"], placeholder="例：胸がざわざわする")

    # 4) 今日の一歩（行動活性化）
    st.caption("今日の一歩（小さく・具体・すぐ始められる）")
    st.markdown("<div class='chips'>", unsafe_allow_html=True)
    for i, tip in enumerate(BA_SUGGEST):
        st.markdown("<span class='chip-btn'>", unsafe_allow_html=True)
        if st.button(tip, key=f"ba_{i}"): n["step"] = tip
        st.markdown("</span>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    n["step"] = st.text_input("やること（自由入力OK）", value=n["step"], placeholder="例：英単語アプリで3つだけ")

    # 5) 気分が上がるスイッチ（旧：価値タグ）
    st.caption("気分が上がるスイッチ")
    n["switch"] = st.selectbox("", SWITCHES, index=SWITCHES.index(n["switch"]) if n["switch"] in SWITCHES else 0, label_visibility="collapsed")

    # 6) メモ（任意／自由）
    n["memo"] = st.text_area("メモ", value=n["memo"], height=70, placeholder="書きたいことがあればどうぞ")

    # 7) 保存
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 保存して完了", type="primary"):
            # 互換形式にも保存
            append_csv(CBT_CSV, {
                "ts": now_ts(),
                "emotions": json.dumps({"multi": n["emos"]}, ensure_ascii=False),
                "triggers": n["reason"], "reappraise": n["oneword"],  # onewordを互換欄へ
                "action": n["step"], "value": n["switch"]
            })
            append_csv(MIX_CSV, {
                "ts": now_ts(), "emos": " ".join(n["emos"]), "reason": n["reason"], "oneword": n["oneword"],
                "step": n["step"], "switch": n["switch"], "memo": n["memo"]
            })
            st.session_state.note = {"emos": [], "reason":"", "oneword":"", "step":"", "switch":"", "memo":"", "sleep_h":6.5}
            st.success("保存しました。今日はここでおしまいでもOK。")
    with c2:
        if st.button("🧼 入力を初期化"):
            st.session_state.note = {"emos": [], "reason":"", "oneword":"", "step":"", "switch":"", "memo":"", "sleep_h":6.5}
            st.info("初期化しました。")

# ---------------- Study ----------------
SUBJ_DEFAULT = ["国語","数学","英語","理科","社会","小論","過去問","面接","実技"]
MOODS = ["😌集中","😕難航","😫しんどい"]

def view_study():
    st.subheader("📚 Sturdy Tracker（配分×手触り）")
    st.caption("15分=1ブロック。5分でもOK（四捨五入で1ブロック）。")
    subj = st.selectbox("科目", options=SUBJ_DEFAULT + ["＋追加"], index=2)
    if subj=="＋追加":
        new = st.text_input("科目名を追加", "")
        if new: subj = new
    blocks = st.slider("ブロック数（15分単位）", 1, 8, 1)
    mood = st.selectbox("雰囲気", options=MOODS, index=0)
    memo = st.text_input("学びメモ（1行）", placeholder="例：関数の文章題は朝が楽")
    if st.button("💾 記録", type="primary"):
        append_csv(STUDY_CSV, {"ts":now_ts(),"subject":subj,"blocks":blocks,"mood":mood,"memo":memo})
        st.success("保存しました。")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 今週の配分（簡易）")
    df = load_csv(STUDY_CSV)
    if df.empty:
        st.caption("まだ記録がありません。")
    else:
        try:
            df["ts"] = pd.to_datetime(df["ts"])
            week_ago = datetime.now() - timedelta(days=7)
            view = df[df["ts"]>=week_ago]
            if not view.empty:
                agg = view.groupby("subject")["blocks"].sum().reset_index().sort_values("blocks", ascending=False)
                st.dataframe(agg.rename(columns={"subject":"科目","blocks":"15分ブロック合計"}), use_container_width=True, hide_index=True)
        except Exception:
            pass
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- 記録・エクスポート ----------------
def view_export():
    st.subheader("⬇️ 記録・エクスポート（CSV）／設定")
    def dl(df: pd.DataFrame, label: str, name: str):
        if df.empty: st.caption(f"{label}：まだデータがありません"); return
        st.download_button(f"⬇️ {label}", df.to_csv(index=False).encode("utf-8-sig"), file_name=name, mime="text/csv")
    dl(load_csv(CBT_CSV),   "2分ノート（互換）", "cbt_entries.csv")
    dl(load_csv(BREATH_CSV),"呼吸", "breath_sessions.csv")
    dl(load_csv(MIX_CSV),   "心を整える（統合）", "mix_note.csv")
    dl(load_csv(STUDY_CSV), "Study", "study_blocks.csv")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    danger = st.checkbox("⚠️ すべての保存データ（CSV）を削除することに同意します")
    if st.button("🗑️ すべて削除（取り消し不可）", disabled=not danger):
        for p in [CBT_CSV,BREATH_CSV,MIX_CSV,STUDY_CSV]:
            try:
                if p.exists(): p.unlink()
            except Exception as e:
                st.error(f"{p.name}: {e}")
        st.success("削除しました。")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Router ----------------
top_nav()
v = st.session_state.view
if v=="HOME":    view_home()
elif v=="BREATH":view_breath()
elif v=="NOTE":  view_note()
elif v=="STUDY": view_study()
else:            view_export()

# ---------------- Footer ----------------
st.markdown("""
<div style="text-align:center; color:var(--muted); margin-top:12px;">
  <small>※ 個人名や連絡先は記入しないでください。<br>
  とてもつらい場合は、お住まいの地域の相談窓口や専門機関のご利用もご検討ください。</small>
</div>
""", unsafe_allow_html=True)
