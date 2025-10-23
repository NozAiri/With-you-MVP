# app_en.py — With You. (Pastel Blue | Unified Relax & Rescue)
from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Tuple
import pandas as pd
import streamlit as st
import time, json, os, random

st.set_page_config(page_title="With You.", page_icon="🌙", layout="centered", initial_sidebar_state="collapsed")

# --- Styles (same as JP, English copy) ---
def inject_css():
    st.markdown("""
<style>
:root{ --bg1:#f3f7ff; --bg2:#eefaff; --panel:#ffffffee; --panel-brd:#e1e9ff;
  --text:#21324b; --muted:#5a6b86; --outline:#76a8ff; --grad-from:#cfe4ff; --grad-to:#b9d8ff; --chip-brd:rgba(148,188,255,.45);
  --tile-a:#d9ebff; --tile-b:#edf5ff; --tile-c:#d0f1ff; --tile-d:#ebfbff;}
html, body, .stApp{
  background: radial-gradient(1200px 600px at 20% -10%, #ffffff 0%, var(--bg1) 40%, transparent 70%),
              radial-gradient(1000px 520px at 100% 0%,  #ffffff 0%, var(--bg2) 50%, transparent 80%),
              linear-gradient(180deg, var(--bg1), var(--bg2));
}
.block-container{max-width:980px; padding-top:.4rem; padding-bottom:2rem}
h1,h2,h3{color:var(--text); letter-spacing:.2px}
p,label,.stMarkdown,.stTextInput,.stTextArea{color:var(--text); font-size:1.02rem}
small{color:var(--muted)}
.card{ background:var(--panel); border:1px solid var(--panel-brd); border-radius:16px; padding:18px; margin-bottom:14px; box-shadow:0 10px 30px rgba(40,80,160,.07) }
.topbar{ position:sticky; top:0; z-index:10; background:#fffffff2; backdrop-filter:blur(8px);
  border-bottom:1px solid var(--panel-brd); margin:0 -12px 8px; padding:8px 12px 10px }
.topnav{display:flex; gap:8px; flex-wrap:wrap; margin:2px 0}
.topnav .nav-btn>button{ background:#ffffff !important; color:#1f3352 !important; border:1px solid var(--panel-brd) !important;
  height:auto !important; padding:9px 12px !important; border-radius:999px !important; font-weight:700 !important; font-size:.95rem !important;
  box-shadow:0 6px 14px rgba(40,80,160,.08) !important; }
.topnav .active>button{background:#f6fbff !important; border:2px solid var(--outline) !important}
.nav-hint{font-size:.78rem; color:#6d7fa2; margin:0 2px 6px 2px}
.stButton>button,.stDownloadButton>button{ width:100%; padding:12px 16px; border-radius:999px; border:1px solid var(--chip-brd);
  background:linear-gradient(180deg,var(--grad-from),var(--grad-to)); color:#25334a; font-weight:900; font-size:1.02rem; box-shadow:0 10px 24px rgba(90,150,240,.16)}
.tile-grid{display:grid; grid-template-columns:1fr; gap:18px; margin-top:8px}
.tile .stButton>button{ aspect-ratio:7/2; min-height:76px; border-radius:22px; text-align:center; padding:18px;
  border:none; font-weight:900; font-size:1.12rem; color:#1e2e49; box-shadow:0 12px 26px rgba(40,80,160,.12);
  display:flex; align-items:center; justify-content:center;}
.tile-a .stButton>button{background:linear-gradient(160deg,var(--tile-a),var(--tile-b))}
.breath-wrap{display:flex; justify-content:center; align-items:center; padding:8px 0 4px}
.breath-circle{ width:230px; height:230px; border-radius:999px; background:radial-gradient(circle at 50% 40%, #f7fbff, #e8f2ff 60%, #eef8ff 100%);
  box-shadow:0 16px 32px rgba(90,140,190,.14), inset 0 -10px 25px rgba(120,150,200,.15); transform:scale(1); border: solid #dbe9ff; }
@keyframes sora-grow{ from{ transform:scale(1.0); border-width:10px;} to{ transform:scale(1.6); border-width:14px;} }
@keyframes sora-steady{ from{ transform:scale(1.6); border-width:14px;} to{ transform:scale(1.6); border-width:14px;} }
@keyframes sora-shrink{ from{ transform:scale(1.6); border-width:14px;} to{ transform:scale(1.0); border-width:8px;} }
.phase-pill{display:inline-block; padding:.20rem .7rem; border-radius:999px; background:#edf5ff; color:#2c4b77; border:1px solid #d6e7ff; font-weight:700}
.subtle{color:#5d6f92; font-size:.92rem}
.emopills{display:grid; grid-template-columns:repeat(6,1fr); gap:8px}
.emopills .stButton>button{ background:#ffffff !important; color:#223552 !important; border:1.5px solid #d6e7ff !important; border-radius:14px !important;
  box-shadow:none !important; font-weight:700 !important; padding:10px 12px !important; }
.emopills .on>button{border:2px solid #76a8ff !important; background:#f3f9ff !important}
.kpi-grid{display:grid; grid-template-columns:repeat(3,1fr); gap:12px}
.kpi{ background:#fff; border:1px solid var(--panel-brd); border-radius:16px; padding:14px; text-align:center; box-shadow:0 8px 20px rgba(40,80,160,.06) }
.kpi .num{font-size:1.6rem; font-weight:900; color:#28456e}
.kpi .lab{color:#5a6b86; font-size:.9rem}
textarea, input, .stTextInput>div>div>input{ border-radius:12px!important; background:#ffffff; color:#2a3a55; border:1px solid #e1e9ff }
@media (max-width: 680px){ .kpi-grid{grid-template-columns:1fr 1fr} .tile-grid{grid-template-columns:1fr} .emopills{grid-template-columns:repeat(4,1fr)} }
</style>
""", unsafe_allow_html=True)
inject_css()
if (datetime.now().hour>=20 or datetime.now().hour<5):
    st.markdown("<style>:root{ --muted:#4a5a73; }</style>", unsafe_allow_html=True)

# --- Data helpers ---
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
    df = load_csv(p); df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(tmp, index=False); os.replace(tmp, p)

# --- Session ---
st.session_state.setdefault("view", "HOME")
st.session_state.setdefault("breath_mode", "gentle")
st.session_state.setdefault("breath_running", False)
st.session_state.setdefault("note", {"emos": [], "reason": "", "oneword": "", "step":"", "switch":"", "memo":""})
st.session_state.setdefault("_session_stage", "before")
st.session_state.setdefault("_before_score", None)

# --- Nav ---
PAGES = [("HOME","🏠 Home"), ("SESSION","🌙 Relax & Rescue"), ("NOTE","📝 Steady the Mind"), ("STUDY","📚 Study Tracker"), ("EXPORT","⬇️ Export")]
def navigate(k): st.session_state.breath_running=False; st.session_state.view=k
def top_nav():
    st.markdown('<div class="topbar"><div class="nav-hint">Navigate</div><div class="topnav">', unsafe_allow_html=True)
    cols = st.columns(len(PAGES))
    for i,(k,lbl) in enumerate(PAGES):
        cls = "nav-btn active" if st.session_state.view==k else "nav-btn"
        with cols[i]:
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(lbl, key=f"nav_{k}", use_container_width=True): navigate(k)
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div></div>", unsafe_allow_html=True)

# --- Breath helpers ---
def breath_patterns() -> Dict[str, Tuple[int,int,int]]:
    return {"gentle": (4,0,6), "calm": (5,2,6)}
def compute_cycles(target_sec: int, pat: Tuple[int,int,int]) -> int:
    return max(1, round(target_sec / sum(pat)))
def animate_circle(container, phase: str, secs: int):
    anim = {"inhale":"sora-grow","hold":"sora-steady","exhale":"sora-shrink"}[phase]
    container.markdown(f"<div class='breath-wrap'><div class='breath-circle' style='animation:{anim} {secs}s linear 1 forwards;'></div></div>", unsafe_allow_html=True)
def run_breath_session(total_sec: int=90):
    inhale, hold, exhale = breath_patterns()[st.session_state.breath_mode]
    cycles = compute_cycles(total_sec, (inhale,hold,exhale))
    st.session_state.breath_running = True
    phase_box = st.empty(); circle_holder = st.empty()
    prog = st.progress(0, text="Relaxing")
    elapsed = 0; total = cycles * (inhale + hold + exhale)
    for _ in range(cycles):
        if not st.session_state.breath_running: break
        phase_box.markdown("<span class='phase-pill'>Inhale</span>", unsafe_allow_html=True)
        animate_circle(circle_holder, "inhale", inhale)
        for _ in range(inhale):
            if not st.session_state.breath_running: break
            elapsed += 1; prog.progress(min(int(elapsed/total*100),100)); time.sleep(1)
        if not st.session_state.breath_running: break
        if hold>0:
            phase_box.markdown("<span class='phase-pill'>Hold</span>", unsafe_allow_html=True)
            animate_circle(circle_holder, "hold", hold)
            for _ in range(hold):
                if not st.session_state.breath_running: break
                elapsed += 1; prog.progress(min(int(elapsed/total*100),100)); time.sleep(1)
            if not st.session_state.breath_running: break
        phase_box.markdown("<span class='phase-pill'>Exhale</span>", unsafe_allow_html=True)
        animate_circle(circle_holder, "exhale", exhale)
        for _ in range(exhale):
            if not st.session_state.breath_running: break
            elapsed += 1; prog.progress(min(int(elapsed/total*100),100)); time.sleep(1)
    st.session_state.breath_running = False

# --- KPIs ---
def last7_kpis() -> dict:
    df = load_csv(MIX_CSV)
    if df.empty: return {"breath":0, "delta_avg":0.0, "steps":0}
    try:
        df["ts"]=pd.to_datetime(df["ts"]); view=df[df["ts"]>=datetime.now()-timedelta(days=7)]
        breath=view[view["mode"]=="breath"]; steps=view[(view["step"].astype(str)!="")]
        delta_avg=float(breath["delta"].dropna().astype(float).mean()) if not breath.empty else 0.0
        return {"breath":len(breath),"delta_avg":round(delta_avg,2),"steps":len(steps)}
    except Exception: return {"breath":0,"delta_avg":0.0,"steps":0}

# --- Views ---
def view_home():
    st.markdown("""
<div class="card">
  <h2 style="margin:.2rem 0 1rem 0;">Before words, take a breath.</h2>
  <div style="font-weight:900; color:#2767c9; font-size:1.3rem; margin-bottom:.6rem;">A short pause, a little relief.</div>
  <div style="border:1px solid var(--panel-brd); border-radius:14px; padding:12px; background:#f8fbff;">
    90-second relax → list feelings with emoji → decide one small next step in your words. Data stays on this device.
  </div>
</div>
""", unsafe_allow_html=True)
    k=last7_kpis()
    st.markdown('<div class="kpi-grid">', unsafe_allow_html=True)
    c1,c2,c3=st.columns(3)
    with c1: st.markdown(f'<div class="kpi"><div class="num">{k["breath"]}</div><div class="lab">Relax Sessions</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="kpi"><div class="num">{k["delta_avg"]:+.2f}</div><div class="lab">Avg Δ (mood)</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="kpi"><div class="num">{k["steps"]}</div><div class="lab">Next Steps</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="card"><div class="tile-grid">', unsafe_allow_html=True)
    st.markdown('<div class="tile tile-a">', unsafe_allow_html=True)
    if st.button("🌙 Start (Relax & Rescue)", key="tile_session"): navigate("SESSION")
    st.markdown('</div></div></div>', unsafe_allow_html=True)

def view_session():
    st.subheader("🌙 Relax & Rescue")
    stage = st.session_state._session_stage
    if stage=="before":
        st.caption("I’m here with you. Let’s breathe for 90 seconds.")
        st.session_state._before_score = st.slider("Mood now (−3 very hard / +3 quite okay)", -3, 3, -2)
        if st.button("Begin Relax (90s)", type="primary"):
            st.session_state._session_stage="breathe"
            run_breath_session(90)
            st.session_state._session_stage="after"; return
    if stage=="after":
        st.markdown("#### How do you feel now?")
        after_score = st.slider("Mood now (−3 very hard / +3 quite okay)", -3, 3, 0, key="after_slider")
        before = int(st.session_state.get("_before_score",-2))
        delta = int(after_score)-before
        st.caption(f"Change in mood: **{delta:+d}**")
        if st.button("💾 Save relax record", type="primary"):
            inh,hold,exh = breath_patterns()[st.session_state.breath_mode]
            append_csv(BREATH_CSV, {"ts":now_ts(),"mode":st.session_state.breath_mode,"target_sec":90,
                                    "inhale":inh,"hold":hold,"exhale":exh,
                                    "mood_before":before,"mood_after":int(after_score),"delta":delta,"note":""})
            append_csv(MIX_CSV, {"ts":now_ts(),"mode":"breath","mood_before":before,"mood_after":int(after_score),"delta":delta})
            st.success("Saved. Next.")
            st.session_state._session_stage="write"; return
    if stage=="write":
        EMOJI = ["😟 Anxious","😢 Sad","😠 Irritated","😳 Embarrassed","😐 Foggy","🙂 Calm","😊 Glad"]
        SWITCHES = ["Get some light","Move a little","Reach out lightly","Small win","Tidy the space","Small treat"]
        st.caption("Feelings (multi-select)")
        st.markdown('<div class="emopills">', unsafe_allow_html=True)
        n = st.session_state.note
        cols = st.columns(6)
        for i,label in enumerate(EMOJI):
            with cols[i%6]:
                sel = label in n["emos"]; cls="on" if sel else ""
                st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
                if st.button(("✓ " if sel else "")+label, key=f"emo_s_{i}"):
                    if sel: n["emos"].remove(label)
                    else:   n["emos"].append(label)
                st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        n["reason"]=st.text_area("What’s happening")
        n["oneword"]=st.text_area("Put the feeling into words")
        n["step"]=st.text_input("What I’ll do next (in my words)")
        n["switch"]=st.selectbox("Mood-lifting switch", SWITCHES, index=SWITCHES.index(n["switch"]) if n["switch"] in SWITCHES else 0)
        n["memo"]=st.text_area("Notes", height=80)
        if st.button("💾 Save and finish", type="primary"):
            append_csv(CBT_CSV, {"ts":now_ts(),"emotions":json.dumps({"multi":n["emos"]}, ensure_ascii=False),
                                 "triggers":n["reason"],"reappraise":n["oneword"],"action":n["step"],"value":n["switch"]})
            append_csv(MIX_CSV, {"ts":now_ts(),"mode":"session","emos":" ".join(n["emos"]),
                                 "reason":n["reason"],"oneword":n["oneword"],"step":n["step"],"switch":n["switch"],"memo":n["memo"]})
            st.success("Done for now. That’s enough.")
            st.session_state._session_stage="before"; st.session_state._before_score=None
            st.session_state.note={"emos": [], "reason": "", "oneword": "", "step":"", "switch":"", "memo":""}

def view_note():
    st.subheader("📝 Steady the Mind")
    n = st.session_state.note
    EMOJI = ["😟 Anxious","😢 Sad","😠 Irritated","😳 Embarrassed","😐 Foggy","🙂 Calm","😊 Glad"]
    SWITCHES = ["Get some light","Move a little","Reach out lightly","Small win","Tidy the space","Small treat"]
    st.caption("Feelings (multi-select)")
    st.markdown('<div class="emopills">', unsafe_allow_html=True)
    cols = st.columns(6)
    for i,label in enumerate(EMOJI):
        with cols[i%6]:
            sel = label in n["emos"]; cls="on" if sel else ""
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(("✓ " if sel else "")+label, key=f"emo_n_{i}"):
                if sel: n["emos"].remove(label)
                else:   n["emos"].append(label)
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    n["reason"]=st.text_area("What’s happening", value=n["reason"])
    n["oneword"]=st.text_area("Put the feeling into words", value=n["oneword"])
    n["step"]=st.text_input("What I’ll do next (in my words)", value=n["step"])
    n["switch"]=st.selectbox("Mood-lifting switch", SWITCHES, index=SWITCHES.index(n["switch"]) if n["switch"] in SWITCHES else 0)
    n["memo"]=st.text_area("Notes", value=n["memo"], height=80)
    if st.button("💾 Save and finish", type="primary"):
        append_csv(CBT_CSV, {"ts":now_ts(),"emotions":json.dumps({"multi":n["emos"]}, ensure_ascii=False),
                             "triggers":n["reason"],"reappraise":n["oneword"],"action":n["step"],"value":n["switch"]})
        append_csv(MIX_CSV, {"ts":now_ts(),"mode":"note","emos":" ".join(n["emos"]),
                             "reason":n["reason"],"oneword":n["oneword"],"step":n["step"],"switch":n["switch"],"memo":n["memo"]})
        st.success("Saved. That’s enough for today.")
        st.session_state.note={"emos": [], "reason": "", "oneword": "", "step":"", "switch":"", "memo":""}

# Study / Export: same structure as JP but English labels
DEFAULT_MOODS=["Going well","Stuck","Drained","Focused","Sluggish","Sleepy","Other"]
def view_study():
    st.subheader("📚 Study Tracker (manual time entry)")
    st.caption("Enter minutes manually. Review in the list below.")
    left,right=st.columns(2)
    with left:
        subject=st.text_input("Subject")
        minutes=st.number_input("Minutes", min_value=1, max_value=600, value=30, step=5)
    with right:
        mood_pick=st.selectbox("Pick a mood", DEFAULT_MOODS, index=0)
        mood_free=st.text_input("Describe mood in your words (optional)")
        mood=mood_free.strip() if mood_free.strip() else mood_pick
        note=st.text_input("Note")
    if st.button("💾 Save", type="primary"):
        append_csv(STUDY_CSV, {"ts":now_ts(),"subject":subject.strip(),"minutes":int(minutes),"mood":mood,"memo":note})
        st.success("Saved.")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### Logs")
    df=load_csv(STUDY_CSV)
    if df.empty: st.caption("No logs yet.")
    else:
        try:
            df["ts"]=pd.to_datetime(df["ts"]); df=df.sort_values("ts", ascending=False)
            show=df[["ts","subject","minutes","mood","memo"]].rename(columns={"ts":"Time","subject":"Subject","minutes":"Min","mood":"Mood","memo":"Note"})
            st.dataframe(show, use_container_width=True, hide_index=True)
            st.markdown("#### Totals by Subject")
            agg=df.groupby("subject", dropna=False)["minutes"].sum().reset_index().sort_values("minutes", ascending=False)
            agg=agg.rename(columns={"subject":"Subject","minutes":"Total (min)"})
            st.dataframe(agg, use_container_width=True, hide_index=True)
        except Exception: st.caption("Error while aggregating.")
    st.markdown('</div>', unsafe_allow_html=True)

def export_and_wipe(label: str, path: Path, name: str):
    df=load_csv(path)
    if df.empty: st.caption(f"{label}: No data yet"); return
    data=df.to_csv(index=False).encode("utf-8-sig")
    dl=st.download_button(f"⬇️ Save {label}", data, file_name=name, mime="text/csv", key=f"dl_{name}")
    if dl and st.button(f"🗑 Delete {label} from this device", type="secondary", key=f"wipe_{name}"):
        try: path.unlink(missing_ok=True); st.success("Deleted from this device.")
        except Exception: st.warning("Failed to delete. Check if the file is open.")

def view_export():
    st.subheader("⬇️ Export (CSV) / Delete safely")
    export_and_wipe("CBT-compatible notes", CBT_CSV, "cbt_entries.csv")
    export_and_wipe("Relax logs", BREATH_CSV, "breath_sessions.csv")
    export_and_wipe("Unified notes", MIX_CSV, "mix_note.csv")
    export_and_wipe("Study Tracker", STUDY_CSV, "study_blocks.csv")

# Router
top_nav()
v=st.session_state.view
if v=="HOME": view_home()
elif v=="SESSION": view_session()
elif v=="NOTE": view_note()
elif v=="STUDY": view_study()
else: view_export()

st.markdown("""
<div style="text-align:center; color:#5a6b86; margin-top:12px;">
  <small>Please avoid entering personal names or contact information.<br>
  If you’re in severe distress, consider contacting local support services.</small>
</div>
""", unsafe_allow_html=True)
