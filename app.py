# app.py — With You.（水色パステル｜レスキュー+リラックス統合版）
from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Tuple
import pandas as pd
import streamlit as st
import time, json, os, random

# ---------------- Page config ----------------
st.set_page_config(
    page_title="With You.",
    page_icon="🌙",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------- Theme / CSS (pastel blue) ----------------
def inject_css():
    st.markdown("""
<style>
:root{
  --bg1:#f3f7ff; --bg2:#eefaff;
  --panel:#ffffffee; --panel-brd:#e1e9ff;
  --text:#21324b; --muted:#5a6b86; --outline:#76a8ff;
  --grad-from:#cfe4ff; --grad-to:#b9d8ff; --chip-brd:rgba(148,188,255,.45);
  --tile-a:#d9ebff; --tile-b:#edf5ff; --tile-c:#d0f1ff; --tile-d:#ebfbff;
}
html, body, .stApp{
  background: radial-gradient(1200px 600px at 20% -10%, #ffffff 0%, var(--bg1) 40%, transparent 70%),
              radial-gradient(1000px 520px at 100% 0%,  #ffffff 0%, var(--bg2) 50%, transparent 80%),
              linear-gradient(180deg, var(--bg1), var(--bg2));
}
.block-container{max-width:980px; padding-top:.4rem; padding-bottom:2rem}
h1,h2,h3{color:var(--text); letter-spacing:.2px}
p,label,.stMarkdown,.stTextInput,.stTextArea{color:var(--text); font-size:1.02rem}
small{color:var(--muted)}
.card{
  background:var(--panel); border:1px solid var(--panel-brd);
  border-radius:16px; padding:18px; margin-bottom:14px;
  box-shadow:0 10px 30px rgba(40,80,160,.07)
}

/* Topbar nav */
.topbar{
  position:sticky; top:0; z-index:10;
  background:#fffffff2; backdrop-filter:blur(8px);
  border-bottom:1px solid var(--panel-brd); margin:0 -12px 8px; padding:8px 12px 10px
}
.topnav{display:flex; gap:8px; flex-wrap:wrap; margin:2px 0}
.topnav .nav-btn>button{
  background:#ffffff !important; color:#1f3352 !important; border:1px solid var(--panel-brd) !important;
  height:auto !important; padding:9px 12px !important; border-radius:999px !important;
  font-weight:700 !important; font-size:.95rem !important;
  box-shadow:0 6px 14px rgba(40,80,160,.08) !important;
}
.topnav .active>button{background:#f6fbff !important; border:2px solid var(--outline) !important}
.nav-hint{font-size:.78rem; color:#6d7fa2; margin:0 2px 6px 2px}

/* Buttons */
.stButton>button,.stDownloadButton>button{
  width:100%; padding:12px 16px; border-radius:999px; border:1px solid var(--chip-brd);
  background:linear-gradient(180deg,var(--grad-from),var(--grad-to)); color:#25334a; font-weight:900; font-size:1.02rem;
  box-shadow:0 10px 24px rgba(90,150,240,.16)
}
.stButton>button:hover{filter:brightness(.98)}

/* タイル（ホームは1列＝統合導線のみ） */
.tile-grid{display:grid; grid-template-columns:1fr; gap:18px; margin-top:8px}
.tile .stButton>button{
  aspect-ratio:7/2; min-height:76px; border-radius:22px; text-align:center; padding:18px;
  border:none; font-weight:900; font-size:1.12rem; color:#1e2e49; box-shadow:0 12px 26px rgba(40,80,160,.12);
  display:flex; align-items:center; justify-content:center;
}
.tile-a .stButton>button{background:linear-gradient(160deg,var(--tile-a),var(--tile-b))}

/* 呼吸丸（CSSアニメ） */
.breath-wrap{display:flex; justify-content:center; align-items:center; padding:8px 0 4px}
.breath-circle{
  width:230px; height:230px; border-radius:999px;
  background:radial-gradient(circle at 50% 40%, #f7fbff, #e8f2ff 60%, #eef8ff 100%);
  box-shadow:0 16px 32px rgba(90,140,190,.14), inset 0 -10px 25px rgba(120,150,200,.15);
  transform:scale(1);
  border: solid #dbe9ff;
}
@keyframes sora-grow{ from{ transform:scale(1.0);   border-width:10px;} to{ transform:scale(1.6); border-width:14px;} }
@keyframes sora-steady{ from{ transform:scale(1.6);   border-width:14px;} to{ transform:scale(1.6); border-width:14px;} }
@keyframes sora-shrink{from{ transform:scale(1.6);   border-width:14px;} to{ transform:scale(1.0); border-width:8px;} }

.phase-pill{display:inline-block; padding:.20rem .7rem; border-radius:999px; background:#edf5ff;
  color:#2c4b77; border:1px solid #d6e7ff; font-weight:700}
.subtle{color:#5d6f92; font-size:.92rem}

/* Emotion pills（白ベース＋青アウトライン） */
.emopills{display:grid; grid-template-columns:repeat(6,1fr); gap:8px}
.emopills .stButton>button{
  background:#ffffff !important; color:#223552 !important;
  border:1.5px solid #d6e7ff !important; border-radius:14px !important;
  box-shadow:none !important; font-weight:700 !important; padding:10px 12px !important;
}
.emopills .on>button{border:2px solid #76a8ff !important; background:#f3f9ff !important}

/* KPIカード */
.kpi-grid{display:grid; grid-template-columns:repeat(3,1fr); gap:12px}
.kpi{ background:#fff; border:1px solid var(--panel-brd); border-radius:16px; padding:14px; text-align:center;
  box-shadow:0 8px 20px rgba(40,80,160,.06) }
.kpi .num{font-size:1.6rem; font-weight:900; color:#28456e}
.kpi .lab{color:#5a6b86; font-size:.9rem}

/* 入力 */
textarea, input, .stTextInput>div>div>input{
  border-radius:12px!important; background:#ffffff; color:#2a3a55; border:1px solid #e1e9ff
}

/* Mobile */
@media (max-width: 680px){
  .kpi-grid{grid-template-columns:1fr 1fr}
  .tile-grid{grid-template-columns:1fr}
  .emopills{grid-template-columns:repeat(4,1fr)}
}
</style>
""", unsafe_allow_html=True)

inject_css()

# 夜間はやや彩度を落とす
HOUR = datetime.now().hour
if (HOUR>=20 or HOUR<5):
    st.markdown("<style>:root{ --muted:#4a5a73; }</style>", unsafe_allow_html=True)

# ---------------- Data ----------------
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
CBT_CSV    = DATA_DIR / "cbt_entries.csv"
BREATH_CSV = DATA_DIR / "breath_sessions.csv"
MIX_CSV    = DATA_DIR / "mix_note.csv"
STUDY_CSV  = DATA_DIR / "study_blocks.csv"

def now_ts(): return datetime.now().isoformat(timespec="seconds")

def load_csv(p: Path) -> pd.DataFrame:
    if p.exists():
        try: return pd.read_csv(p)
        except Exception: return pd.DataFrame()
    return pd.DataFrame()

def append_csv(p: Path, row: dict):
    tmp = p.with_suffix(p.suffix + f".tmp.{random.randint(1_000_000, 9_999_999)}")
    df = load_csv(p)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(tmp, index=False)
    os.replace(tmp, p)

# ---------------- Session ----------------
st.session_state.setdefault("view", "HOME")
st.session_state.setdefault("breath_mode", "gentle")  # 4-0-6 / 5-2-6
st.session_state.setdefault("breath_running", False)
st.session_state.setdefault("note", {"emos": [], "reason": "", "oneword": "", "step":"", "switch":"", "memo":""})
st.session_state.setdefault("_session_stage", "before")  # before -> breathe -> after -> write
st.session_state.setdefault("_before_score", None)

# ---------------- Nav ----------------
PAGES = [
    ("HOME",   "🏠 ホーム"),
    ("SESSION","🌙 リラックス & レスキュー"),
    ("NOTE",   "📝 心を整える"),
    ("STUDY",  "📚 Study Tracker"),
    ("EXPORT", "⬇️ 記録・エクスポート"),
]
def navigate(to_key: str):
    st.session_state.breath_running = False
    st.session_state.view = to_key
def top_nav():
    st.markdown('<div class="topbar">', unsafe_allow_html=True)
    st.markdown('<div class="nav-hint">ページ移動</div>', unsafe_allow_html=True)
    st.markdown('<div class="topnav">', unsafe_allow_html=True)
    cols = st.columns(len(PAGES))
    for i,(key,label) in enumerate(PAGES):
        cls = "nav-btn active" if st.session_state.view==key else "nav-btn"
        with cols[i]:
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(label, key=f"nav_{key}", use_container_width=True): navigate(key)
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

# ---------------- Breath helpers ----------------
def breath_patterns() -> Dict[str, Tuple[int,int,int]]:
    return {"gentle": (4,0,6), "calm": (5,2,6)}
def compute_cycles(target_sec: int, pat: Tuple[int,int,int]) -> int:
    return max(1, round(target_sec / sum(pat)))
def animate_circle(container, phase: str, secs: int):
    anim = {"inhale":"sora-grow", "hold":"sora-steady", "exhale":"sora-shrink"}[phase]
    container.markdown(
        f"<div class='breath-wrap'><div class='breath-circle' style='animation:{anim} {secs}s linear 1 forwards;'></div></div>",
        unsafe_allow_html=True
    )
def run_breath_session(total_sec: int=90):
    inhale, hold, exhale = breath_patterns()[st.session_state.breath_mode]
    cycles = compute_cycles(total_sec, (inhale,hold,exhale))
    st.session_state.breath_running = True
    phase_box = st.empty(); circle_holder = st.empty()
    prog = st.progress(0, text="リラックス中")
    elapsed = 0; total = cycles * (inhale + hold + exhale)
    for _ in range(cycles):
        if not st.session_state.breath_running: break
        phase_box.markdown("<span class='phase-pill'>吸う</span>", unsafe_allow_html=True)
        animate_circle(circle_holder, "inhale", inhale)
        for _ in range(inhale):
            if not st.session_state.breath_running: break
            elapsed += 1; prog.progress(min(int(elapsed/total*100), 100)); time.sleep(1)
        if not st.session_state.breath_running: break
        if hold>0:
            phase_box.markdown("<span class='phase-pill'>とまる</span>", unsafe_allow_html=True)
            animate_circle(circle_holder, "hold", hold)
            for _ in range(hold):
                if not st.session_state.breath_running: break
                elapsed += 1; prog.progress(min(int(elapsed/total*100), 100)); time.sleep(1)
            if not st.session_state.breath_running: break
        phase_box.markdown("<span class='phase-pill'>はく</span>", unsafe_allow_html=True)
        animate_circle(circle_holder, "exhale", exhale)
        for _ in range(exhale):
            if not st.session_state.breath_running: break
            elapsed += 1; prog.progress(min(int(elapsed/total*100), 100)); time.sleep(1)
    st.session_state.breath_running = False

# ---------------- KPIs ----------------
def last7_kpis() -> dict:
    df = load_csv(MIX_CSV)
    if df.empty: return {"breath":0, "delta_avg":0.0, "steps":0}
    try:
        df["ts"] = pd.to_datetime(df["ts"])
        view = df[df["ts"] >= datetime.now() - timedelta(days=7)]
        breath = view[view["mode"]=="breath"]
        steps  = view[(view["step"].astype(str)!="")]  # 統合フロー/心を整える/どちらもカバー
        delta_avg = float(breath["delta"].dropna().astype(float).mean()) if not breath.empty else 0.0
        return {"breath": len(breath), "delta_avg": round(delta_avg,2), "steps": len(steps)}
    except Exception:
        return {"breath":0, "delta_avg":0.0, "steps":0}

# ---------------- Views ----------------
def view_home():
    st.markdown("""
<div class="card">
  <h2 style="margin:.2rem 0 1rem 0;">言葉の前に、息をひとつ。</h2>
  <div style="font-weight:900; color:#2767c9; font-size:1.3rem; margin-bottom:.6rem;">短い時間で、少し楽に。</div>
  <div style="border:1px solid var(--panel-brd); border-radius:14px; padding:12px; background:#f8fbff;">
    90秒のリラックス → 絵文字で気持ちを並べる → 今からすることを自分の言葉で決める。データはこの端末だけ。
  </div>
</div>
""", unsafe_allow_html=True)

    k = last7_kpis()
    st.markdown('<div class="kpi-grid">', unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    with c1: st.markdown(f'<div class="kpi"><div class="num">{k["breath"]}</div><div class="lab">リラックス回数</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="kpi"><div class="num">{k["delta_avg"]:+.2f}</div><div class="lab">平均Δ（気分）</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="kpi"><div class="num">{k["steps"]}</div><div class="lab">今からすること</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="tile-grid">', unsafe_allow_html=True)
    st.markdown('<div class="tile tile-a">', unsafe_allow_html=True)
    if st.button("🌙 はじめる（リラックス & レスキュー）", key="tile_session"): navigate("SESSION")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

def view_session():
    st.subheader("🌙 リラックス & レスキュー")
    stage = st.session_state._session_stage

    # 1) 前スコア
    if stage=="before":
        st.caption("ここにいていいよ。90秒だけ、一緒に息。")
        st.session_state._before_score = st.slider("いまの気分（-3 とてもつらい / +3 とても楽）", -3, 3, -2)
        if st.button("リラックスをはじめる（90秒）", type="primary"):
            st.session_state._session_stage = "breathe"
            run_breath_session(90)
            st.session_state._session_stage = "after"
            return

    # 2) 後スコア（Δを保存）
    if stage=="after":
        st.markdown("#### 終わったあとの感じ")
        after_score = st.slider("いまの気分（-3 とてもつらい / +3 とても楽）", -3, 3, 0, key="after_slider")
        before = int(st.session_state.get("_before_score",-2))
        delta = int(after_score) - before
        st.caption(f"気分の変化：**{delta:+d}**")
        if st.button("💾 リラックスの記録を保存", type="primary"):
            inhale, hold, exhale = breath_patterns()[st.session_state.breath_mode]
            append_csv(BREATH_CSV, {
                "ts": now_ts(), "mode": st.session_state.breath_mode,
                "target_sec": 90, "inhale": inhale, "hold": hold, "exhale": exhale,
                "mood_before": before, "mood_after": int(after_score), "delta": delta, "note": ""
            })
            append_csv(MIX_CSV, {
                "ts": now_ts(), "mode":"breath", "mood_before": before, "mood_after": int(after_score), "delta": delta
            })
            st.success("保存しました。次へ。")
            st.session_state._session_stage = "write"
            return

    # 3) 記述（理由/気持ち/今からすること/スイッチ/メモ）
    if stage=="write":
        EMOJI_CHOICES = ["😟不安","😢悲しい","😠いらだち","😳恥ずかしい","😐ぼんやり","🙂安心","😊うれしい"]
        SWITCHES = ["外の光を浴びる","体を少し動かす","誰かと軽くつながる","小さな達成感","環境を整える","ごほうび少し"]

        st.caption("いまの気持ち（複数OK）")
        st.markdown('<div class="emopills">', unsafe_allow_html=True)
        if "note" not in st.session_state: st.session_state.note = {"emos": [], "reason": "", "oneword": "", "step":"", "switch":"", "memo":""}
        n = st.session_state.note
        cols = st.columns(6)
        for i, label in enumerate(EMOJI_CHOICES):
            with cols[i%6]:
                sel = label in n["emos"]
                cls = "on" if sel else ""
                st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
                if st.button(("✓ " if sel else "") + label, key=f"emo_s_{i}"):
                    if sel: n["emos"].remove(label)
                    else:   n["emos"].append(label)
                st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        n["reason"]  = st.text_area("理由や状況", value=n["reason"])
        n["oneword"] = st.text_area("いまの気持ちを言葉にする", value=n["oneword"])
        n["step"]    = st.text_input("今からすること（自分の言葉で）", value=n["step"])
        n["switch"]  = st.selectbox("気分を上げるスイッチ", SWITCHES, index=SWITCHES.index(n["switch"]) if n["switch"] in SWITCHES else 0)
        n["memo"]    = st.text_area("メモ", value=n["memo"], height=80)

        if st.button("💾 保存して完了", type="primary"):
            append_csv(CBT_CSV, {
                "ts": now_ts(),
                "emotions": json.dumps({"multi": n["emos"]}, ensure_ascii=False),
                "triggers": n["reason"], "reappraise": n["oneword"], "action": n["step"], "value": n["switch"]
            })
            append_csv(MIX_CSV, {
                "ts": now_ts(), "mode":"session", "emos":" ".join(n["emos"]),
                "reason": n["reason"], "oneword": n["oneword"], "step": n["step"], "switch": n["switch"], "memo": n["memo"]
            })
            st.success("できたらOK。今日はここまでで大丈夫。")
            st.session_state._session_stage = "before"
            st.session_state._before_score = None
            st.session_state.note = {"emos": [], "reason": "", "oneword": "", "step":"", "switch":"", "memo":""}

def view_note():
    # 既存の「心を整える」は維持（自由記述＋スイッチ）
    st.subheader("📝 心を整える")
    if "note" not in st.session_state: st.session_state.note = {"emos": [], "reason": "", "oneword": "", "step":"", "switch":"", "memo":""}
    n = st.session_state.note
    EMOJI_CHOICES = ["😟不安","😢悲しい","😠いらだち","😳恥ずかしい","😐ぼんやり","🙂安心","😊うれしい"]
    SWITCHES = ["外の光を浴びる","体を少し動かす","誰かと軽くつながる","小さな達成感","環境を整える","ごほうび少し"]

    st.caption("いまの気持ち（複数OK）")
    st.markdown('<div class="emopills">', unsafe_allow_html=True)
    cols = st.columns(6)
    for i, label in enumerate(EMOJI_CHOICES):
        with cols[i%6]:
            sel = label in n["emos"]
            cls = "on" if sel else ""
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(("✓ " if sel else "") + label, key=f"emo_n_{i}"):
                if sel: n["emos"].remove(label)
                else:   n["emos"].append(label)
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    n["reason"]  = st.text_area("理由や状況", value=n["reason"])
    n["oneword"] = st.text_area("いまの気持ちを言葉にする", value=n["oneword"])
    n["step"]    = st.text_input("今からすること（自分の言葉で）", value=n["step"])
    n["switch"]  = st.selectbox("気分を上げるスイッチ", SWITCHES, index=SWITCHES.index(n["switch"]) if n["switch"] in SWITCHES else 0)
    n["memo"]    = st.text_area("メモ", value=n["memo"], height=80)

    if st.button("💾 保存して完了", type="primary"):
        append_csv(CBT_CSV, {
            "ts": now_ts(),
            "emotions": json.dumps({"multi": n["emos"]}, ensure_ascii=False),
            "triggers": n["reason"], "reappraise": n["oneword"], "action": n["step"], "value": n["switch"]
        })
        append_csv(MIX_CSV, {
            "ts": now_ts(), "mode":"note", "emos":" ".join(n["emos"]),
            "reason": n["reason"], "oneword": n["oneword"], "step": n["step"], "switch": n["switch"], "memo": n["memo"]
        })
        st.session_state.note = {"emos": [], "reason":"", "oneword":"", "step":"", "switch":"", "memo":""}
        st.success("保存しました。ここまでで十分。")

# ---- Study Tracker（前版のまま）/ Export もそのまま ----
DEFAULT_MOODS = ["順調","難航","しんどい","集中","だるい","眠い","その他"]
def view_study():
    st.subheader("📚 Study Tracker（学習時間の記録）")
    st.caption("時間は手入力。あとで一覧で見返せます。")

    left, right = st.columns(2)
    with left:
        subject = st.text_input("科目")
        minutes = st.number_input("学習時間（分）", min_value=1, max_value=600, value=30, step=5)
    with right:
        mood_choice = st.selectbox("雰囲気を選ぶ", DEFAULT_MOODS, index=0)
        mood_free = st.text_input("雰囲気を自分の言葉で（空欄可）")
        mood = mood_free.strip() if mood_free.strip() else mood_choice
        note = st.text_input("メモ")

    if st.button("💾 記録", type="primary"):
        append_csv(STUDY_CSV, {"ts": now_ts(),"subject":subject.strip(),"minutes":int(minutes),"mood":mood,"memo":note})
        st.success("保存しました。")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 一覧")
    df = load_csv(STUDY_CSV)
    if df.empty:
        st.caption("まだ記録がありません。")
    else:
        try:
            df["ts"] = pd.to_datetime(df["ts"])
            df = df.sort_values("ts", ascending=False)
            show = df[["ts","subject","minutes","mood","memo"]].rename(
                columns={"ts":"日時","subject":"科目","minutes":"分","mood":"雰囲気","memo":"メモ"})
            st.dataframe(show, use_container_width=True, hide_index=True)

            st.markdown("#### 合計（科目別）")
            agg = df.groupby("subject", dropna=False)["minutes"].sum().reset_index().sort_values("minutes", ascending=False)
            agg = agg.rename(columns={"subject":"科目","minutes":"合計（分）"})
            st.dataframe(agg, use_container_width=True, hide_index=True)
        except Exception:
            st.caption("集計時にエラーが発生しました。")
    st.markdown('</div>', unsafe_allow_html=True)

def export_and_wipe(label: str, path: Path, download_name: str):
    df = load_csv(path)
    if df.empty:
        st.caption(f"{label}：まだデータがありません"); return
    data = df.to_csv(index=False).encode("utf-8-sig")
    dl = st.download_button(f"⬇️ {label} を保存", data, file_name=download_name, mime="text/csv", key=f"dl_{download_name}")
    if dl and st.button(f"🗑 {label} をこの端末から消去する", type="secondary", key=f"wipe_{download_name}"):
        try: path.unlink(missing_ok=True); st.success("端末から安全に消去しました。")
        except Exception: st.warning("消去に失敗しました。ファイルが開かれていないか確認してください。")

def view_export():
    st.subheader("⬇️ 記録・エクスポート（CSV）／安全消去")
    export_and_wipe("心を整える（互換）", CBT_CSV,   "cbt_entries.csv")
    export_and_wipe("リラックス",           BREATH_CSV, "breath_sessions.csv")
    export_and_wipe("心を整える（統合）",   MIX_CSV,   "mix_note.csv")
    export_and_wipe("Study Tracker",       STUDY_CSV,  "study_blocks.csv")

# ---------------- Router ----------------
top_nav()
v = st.session_state.view
if v=="HOME":      view_home()
elif v=="SESSION": view_session()
elif v=="NOTE":    view_note()
elif v=="STUDY":   view_study()
else:              view_export()

# ---------------- Footer ----------------
st.markdown("""
<div style="text-align:center; color:#5a6b86; margin-top:12px;">
  <small>※ 個人名や連絡先は記入しないでください。<br>
  とてもつらい場合は、お住まいの地域の相談窓口や専門機関のご利用もご検討ください。</small>
</div>
""", unsafe_allow_html=True)
