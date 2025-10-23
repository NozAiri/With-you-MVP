# app.py — Sora（生徒コア体験フル版／パステル明るめ＋レスキュー＋気分Δ＋Sturdy）
from __future__ import annotations
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, Tuple, List
import pandas as pd
import streamlit as st
import time, json, os, random, hashlib

# =================== ページ設定 ===================
st.set_page_config(
    page_title="Sora — しんどい夜の2分ノート",
    page_icon="🌙",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# =================== テーマ / CSS ===================
def inject_css():
    st.markdown("""
<style>
:root{
  /* 明るめパステル */
  --bg1:#f7f8ff; --bg2:#fff4f7;
  --panel:#ffffffee; --panel-brd:#e6e8f6;
  --text:#2a2b44; --muted:#6d7299;
  --outline:#9aa0ff;
  --grad-from:#ffd7e4; --grad-to:#ffb7cd; --chip-brd:rgba(255,189,222,.45);
  --tile-a:#ffe2b8; --tile-b:#fff1dc; --tile-c:#ffd1e3; --tile-d:#ffe6f2;
  --tile-e:#e6dcff; --tile-f:#f5f1ff; --tile-g:#d5f1ff; --tile-h:#eef9ff;
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
  box-shadow:0 10px 30px rgba(48,56,120,.08)
}
/* Topbar nav */
.topbar{
  position:sticky; top:0; z-index:10;
  background:#ffffffd9; backdrop-filter:blur(8px);
  border-bottom:1px solid var(--panel-brd); margin:0 -12px 8px; padding:8px 12px 10px
}
.topnav{display:flex; gap:8px; flex-wrap:wrap; margin:2px 0}
.topnav .nav-btn>button{
  background:#fff !important; color:#323355 !important; border:1px solid var(--panel-brd) !important;
  height:auto !important; padding:9px 12px !important; border-radius:999px !important;
  font-weight:700 !important; font-size:.95rem !important;
  box-shadow:0 6px 14px rgba(48,56,120,.08) !important;
}
.topnav .active>button{background:#f6f7ff !important; border:2px solid var(--outline) !important}
.nav-hint{font-size:.78rem; color:#8b8fb5; margin:0 2px 6px 2px}

/* Buttons */
.stButton>button,.stDownloadButton>button{
  width:100%; padding:12px 16px; border-radius:999px; border:1px solid var(--chip-brd);
  background:linear-gradient(180deg,var(--grad-from),var(--grad-to)); color:#4a3a46; font-weight:900; font-size:1.02rem;
  box-shadow:0 10px 24px rgba(240,140,170,.18)
}
.stButton>button:hover{filter:brightness(.98)}

/* タイル */
.tile-grid{display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:8px}
.tile .stButton>button{
  aspect-ratio:1/1; min-height:176px; border-radius:22px; text-align:left; padding:18px; white-space:normal; line-height:1.2;
  border:none; font-weight:900; font-size:1.12rem; color:#2d2a33; box-shadow:0 12px 26px rgba(48,56,120,.12);
  display:flex; align-items:flex-end; justify-content:flex-start;
}
.tile-a .stButton>button{background:linear-gradient(160deg,var(--tile-a),var(--tile-b))}
.tile-b .stButton>button{background:linear-gradient(160deg,var(--tile-c),var(--tile-d))}
.tile-c .stButton>button{background:linear-gradient(160deg,var(--tile-e),var(--tile-f))}
.tile-d .stButton>button{background:linear-gradient(160deg,var(--tile-g),var(--tile-h))}

/* 呼吸丸 */
.breath-wrap{display:flex; justify-content:center; align-items:center; padding:8px 0 4px}
.breath-circle{
  width:230px; height:230px; border-radius:999px;
  background:radial-gradient(circle at 50% 40%, #fff3f8, #ffe1ee 60%, #f1eeff 100%);
  box-shadow:0 16px 32px rgba(180,150,210,.14), inset 0 -10px 25px rgba(120,120,180,.15);
  transform:scale(var(--scale, 1));
  transition:transform .9s ease-in-out, filter .3s ease-in-out;
  border: solid #f0ddea; /* 太さはインラインstyleで上書き */
}
.phase-pill{
  display:inline-block; padding:.20rem .7rem; border-radius:999px; background:#eef0ff;
  color:#4a4d88; border:1px solid #dfe3ff; font-weight:700
}
.count-box{font-size:40px; font-weight:900; text-align:center; color:#3a3a62; padding:2px 0}
.subtle{color:#7b7fb0; font-size:.92rem}

/* Emotion pills */
.emopills{display:grid; grid-template-columns:repeat(6,1fr); gap:8px}
.emopills .stButton>button{
  background:#fff !important; color:#2d2d3f !important;
  border:1px solid #e7e9fb !important; border-radius:999px !important;
  box-shadow:none !important; font-weight:700 !important; padding:8px 10px !important;
}
.emopills .on>button{border:2px solid #ffb6cc !important; background:#fff6fb !important}

/* Chips（一歩） */
.chips{display:flex; gap:8px; flex-wrap:wrap; margin:8px 0 10px}
.chips .chip-btn>button{
  background:#fff6fb; color:#4a2c50; border:1px solid var(--chip-brd)!important;
  padding:8px 12px; height:auto; border-radius:999px!important; font-weight:900; box-shadow:0 6px 12px rgba(240,140,170,.10)
}

/* KPIカード */
.kpi-grid{display:grid; grid-template-columns:repeat(3,1fr); gap:12px}
.kpi{
  background:#fff; border:1px solid var(--panel-brd); border-radius:16px; padding:14px; text-align:center;
  box-shadow:0 8px 20px rgba(48,56,120,.06)
}
.kpi .num{font-size:1.6rem; font-weight:900; color:#403a6b}
.kpi .lab{color:#6e7091; font-size:.9rem}

/* 入力 */
textarea, input, .stTextInput>div>div>input{
  border-radius:12px!important; background:#ffffff; color:var(--text); border:1px solid #e6e8f6
}

/* Mobile */
@media (max-width: 680px){
  .tile-grid{grid-template-columns:1fr}
  .tile .stButton>button{min-height:164px}
  .emopills{grid-template-columns:repeat(4,1fr)}
  .kpi-grid{grid-template-columns:1fr 1fr}
  .block-container{padding-left:1rem; padding-right:1rem}
}
</style>
""", unsafe_allow_html=True)

inject_css()

# 夜は少し彩度を落とす（目に優しく）
HOUR = datetime.now().hour
night = (HOUR>=20 or HOUR<5)
if night:
    st.markdown("<style>:root{ --muted:#5b5f84; }</style>", unsafe_allow_html=True)

# =================== データ保存 ===================
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
CBT_CSV    = DATA_DIR / "cbt_entries.csv"
BREATH_CSV = DATA_DIR / "breath_sessions.csv"
MIX_CSV    = DATA_DIR / "mix_note.csv"
STUDY_CSV  = DATA_DIR / "study_blocks.csv"

def now_ts() -> str:
    return datetime.now().isoformat(timespec="seconds")

def load_csv(p: Path) -> pd.DataFrame:
    if p.exists():
        try:
            return pd.read_csv(p)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

def append_csv(p: Path, row: dict):
    # 簡易ロック（同時保存の衝突を軽減）
    tmp = p.with_suffix(p.suffix + f".tmp.{random.randint(10**6, 10**7-1)}")
    df = load_csv(p)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(tmp, index=False)
    os.replace(tmp, p)

# =================== セッション初期値 ===================
st.session_state.setdefault("view", "HOME")
st.session_state.setdefault("breath_mode", "gentle")    # gentle: 吸4吐6 / calm: 吸5止2吐6
st.session_state.setdefault("breath_running", False)
st.session_state.setdefault("note", {"emos": [], "reason": "", "oneword": "", "step":"", "switch":"", "memo":"", "save_text": False})
st.session_state.setdefault("mood_before", None)
st.session_state.setdefault("_rescue_after_breath", False)

# =================== ナビ ===================
PAGES = [
    ("HOME",   "🏠 ホーム"),
    ("RESCUE", "🌃 レスキュー"),
    ("BREATH", "🌬 呼吸（90秒）"),
    ("NOTE",   "📝 2分ノート"),
    ("STUDY",  "📚 Sturdy Tracker"),
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
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                navigate(key)
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

# =================== ホーム（7日サマリ） ===================
def last7_kpis() -> dict:
    df = load_csv(MIX_CSV)
    if df.empty: return {"breath":0, "delta_avg":0.0, "steps":0}
    try:
        df["ts"] = pd.to_datetime(df["ts"])
        view = df[df["ts"] >= datetime.now() - timedelta(days=7)]
        breath = view[view["mode"]=="breath"]
        steps  = view[(view["mode"]=="step") & (view.get("step_done", 0)==1)]
        delta_avg = float(breath["delta"].dropna().astype(float).mean()) if not breath.empty else 0.0
        return {"breath": len(breath), "delta_avg": round(delta_avg,2), "steps": len(steps)}
    except Exception:
        return {"breath":0, "delta_avg":0.0, "steps":0}

def view_home():
    st.markdown("""
<div class="card">
  <h2 style="margin:.2rem 0 1rem 0;">言葉の前に、息をひとつ。</h2>
  <div style="font-weight:900; color:#5d5aa6; font-size:1.3rem; margin-bottom:.6rem;">“短い時間で、少し楽に。”</div>
  <div style="border:1px solid var(--panel-brd); border-radius:14px; padding:12px; background:#fafbff;">
    <b>できること</b>：90秒の呼吸で落ち着く → 今日の一歩を1つだけ決める。データはこの端末だけ。
  </div>
</div>
""", unsafe_allow_html=True)

    # KPI（直近7日）
    k = last7_kpis()
    st.markdown('<div class="kpi-grid">', unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    with c1: st.markdown(f'<div class="kpi"><div class="num">{k["breath"]}</div><div class="lab">呼吸セッション</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="kpi"><div class="num">{k["delta_avg"]:+.2f}</div><div class="lab">平均Δ（気分）</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="kpi"><div class="num">{k["steps"]}</div><div class="lab">今日の一歩</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="tile-grid">', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="tile tile-a">', unsafe_allow_html=True)
        if st.button("🌃 苦しい夜のレスキュー", key="tile_rescue"): navigate("RESCUE")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="tile tile-b">', unsafe_allow_html=True)
        if st.button("🌬 いますぐ呼吸（90秒）", key="tile_breath"): navigate("BREATH")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    if st.button("📝 2分ノート（感情→一歩）", key="tile_note", use_container_width=True): navigate("NOTE")
    st.caption("※ 学習の配分を記録したいときは「Sturdy Tracker」へ。")
    st.markdown('</div>', unsafe_allow_html=True)

# =================== 呼吸ワーク ===================
def breath_patterns() -> Dict[str, Tuple[int,int,int]]:
    return {"gentle": (4,0,6), "calm": (5,2,6)}

def compute_cycles(target_sec: int, pat: Tuple[int,int,int]) -> int:
    per = sum(pat)
    return max(1, round(target_sec / per))

def view_breath():
    st.subheader("🌬 呼吸（90秒）")
    mode_name = "穏やか版（吸4・吐6）" if st.session_state.breath_mode=="gentle" else "落ち着き用（吸5・止2・吐6）"
    st.caption(f"現在のガイド：{mode_name}")

    # 前の気分（初回のみ）
    if st.session_state.get("mood_before") is None and not st.session_state.breath_running:
        st.session_state.mood_before = st.slider("いまの気分（-3 とてもつらい / +3 とても楽）", -3, 3, -1, key="mood_before_slider")

    if not st.session_state.breath_running:
        if st.button("開始（約90秒）", type="primary", key="breath_start"): 
            run_breath_session(90)
    else:
        st.info("実行中です…")

def run_breath_session(total_sec: int=90):
    inhale, hold, exhale = breath_patterns()[st.session_state.breath_mode]
    cycles = compute_cycles(total_sec, (inhale,hold,exhale))
    st.session_state.breath_running = True

    st.caption("ここにいていいよ。目を閉じても分かるようにフェーズ表示します。")
    phase_box = st.empty(); count_box = st.empty(); circle_holder = st.empty()
    prog = st.progress(0, text="呼吸セッション")
    elapsed = 0; total = cycles * (inhale + hold + exhale)

    def draw_circle(scale: float, phase: str):
        brd = {"inhale":"12px","hold":"16px","exhale":"8px"}[phase]
        circle_holder.markdown(
            f"<div class='breath-wrap'><div class='breath-circle' style='--scale:{scale}; border-width:{brd}'></div></div>",
            unsafe_allow_html=True
        )

    def tick(label, secs, s_from, s_to):
        nonlocal elapsed
        for t in range(secs,0,-1):
            if not st.session_state.breath_running: return False
            ratio = (secs - t)/(secs-1) if secs>1 else 1
            scale = s_from + (s_to-s_from)*ratio
            phase_box.markdown(f"<span class='phase-pill'>{label}</span>", unsafe_allow_html=True)
            draw_circle(scale, {"吸う":"inhale","とまる":"hold","はく":"exhale"}[label])
            count_box.markdown(f"<div class='count-box'>{t}</div>", unsafe_allow_html=True)
            elapsed += 1; prog.progress(min(int(elapsed/total*100), 100))
            time.sleep(1)  # 体感を重視
        return True

    col_stop, col_hint = st.columns([1,2])
    with col_stop:
        if st.button("× 停止", use_container_width=True, key="breath_stop"): 
            st.session_state.breath_running=False
    with col_hint:
        st.markdown('<div class="subtle">息止めは最大2秒。無理はしないでOK。吐く息は長めに。</div>', unsafe_allow_html=True)

    for _ in range(cycles):
        if not st.session_state.breath_running: break
        if not tick("吸う", inhale, 1.0, 1.6): break
        if hold>0 and st.session_state.breath_running:
            if not tick("とまる", hold, 1.6, 1.6): break
        if not st.session_state.breath_running: break
        if not tick("はく", exhale, 1.6, 1.0): break

    finished = st.session_state.breath_running
    st.session_state.breath_running = False

    # 直後の手応え
    st.markdown("#### 終わったあとの感じ")
    mood_after = st.slider("いまの気分（-3 とてもつらい / +3 とても楽）", -3, 3, 0, key="mood_after_slider")
    before = st.session_state.get("mood_before") if st.session_state.get("mood_before") is not None else -1
    delta = int(mood_after) - int(before)
    st.caption(f"気分の変化：**{delta:+d}**")

    # 保存
    note = st.text_input("メモ（任意）", key="breath_note")
    if st.button("💾 保存", type="primary", key="breath_save"):
        append_csv(BREATH_CSV, {
            "ts": now_ts(), "mode": st.session_state.breath_mode,
            "target_sec": total_sec, "inhale": inhale, "hold": hold, "exhale": exhale,
            "mood_before": before, "mood_after": int(mood_after), "delta": delta, "note": note
        })
        append_csv(MIX_CSV, {
            "ts": now_ts(), "mode":"breath", "mood_before": before, "mood_after": int(mood_after), "delta": delta
        })
        st.success("保存しました。ここまでで十分。")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("もう一度（90秒）", key="breath_again"): run_breath_session(90)
    with c2:
        if st.button("短め（60秒）", key="breath_60"): run_breath_session(60)
    with c3:
        if st.button("ながめ（180秒）", key="breath_180"): run_breath_session(180)

# =================== レスキュー ===================
BA_SUGGEST = ["水を一口","外の光を5分","机の上を30秒片付ける","返信はスタンプだけ","英単語3つだけ"]

def view_rescue():
    st.subheader("🌃 苦しい夜のレスキュー")
    st.caption("ここにいていいよ。90秒だけ、一緒に息。")

    if not st.session_state.get("_rescue_after_breath", False):
        if st.button("🌙 いますぐ90秒だけ呼吸", type="primary", key="rescue_breath"):
            run_breath_session(90)
            st.session_state._rescue_after_breath = True
    else:
        st.markdown("#### 次の一歩（1つだけでOK）")
        for i, tip in enumerate(BA_SUGGEST):
            if st.button(f"✓ {tip}", key=f"rescue_step_{i}"):
                append_csv(MIX_CSV, {"ts": now_ts(), "mode":"step", "step_done":1, "step_label":tip})
                st.success("できたらOK。今日はここまでで大丈夫。")
                st.session_state._rescue_after_breath = False
                break

    with st.expander("相談できる場所（リンク）"):
        st.markdown("- チャット相談（例）: https://www.mhlw.go.jp/kokoro/support/chat.html\n- 電話相談（例）: https://www.mhlw.go.jp/kokoro/support/densetsu.html")

# =================== 2分ノート ===================
EMOJI_CHOICES = ["😟不安","😢悲しい","😠いらだち","😳恥ずかしい","😐ぼんやり","🙂安心","😊うれしい"]
SWITCHES = ["外の光を浴びる","体を少し動かす","誰かと軽くつながる","小さな達成感","環境を整える","ごほうび少し"]

def view_note():
    st.subheader("📝 2分ノート（必須2つ：感情＋一歩）")
    n = st.session_state.note

    st.caption("いまの気持ち（複数OK）")
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

    st.caption("今日の一歩（1つだけでOK）")
    st.markdown("<div class='chips'>", unsafe_allow_html=True)
    for i, tip in enumerate(BA_SUGGEST):
        st.markdown("<span class='chip-btn'>", unsafe_allow_html=True)
        if st.button(tip, key=f"ba_{i}"): n["step"] = tip
        st.markdown("</span>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    n["step"] = st.text_input("やること（自由入力OK）", value=n["step"], key="note_step", placeholder="例：英単語アプリで3つだけ")

    # 任意
    n["reason"]  = st.text_input("（任意）その絵文字を選んだ理由（1行）", value=n["reason"],  key="note_reason",  placeholder="例：返信が来ない／提出が近い")
    n["oneword"] = st.text_input("（任意）いまの気持ちを一言で", value=n["oneword"], key="note_oneword", placeholder="例：胸がざわざわする")
    n["switch"] = st.selectbox("（任意）気分が上がるスイッチ", SWITCHES, index=SWITCHES.index(n["switch"]) if n["switch"] in SWITCHES else 0, key="note_switch")

    st.info("自由記述は保存しなくてもOK。個人名や連絡先は書かないでね。")
    n["save_text"] = st.toggle("自由記述を保存する（OFF推奨）", value=n["save_text"], key="note_save_toggle")
    n["memo"] = st.text_area("メモ（任意）", value=n["memo"], key="note_memo", height=70)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 保存して完了", type="primary", key="note_save"):
            row_cbt = {
                "ts": now_ts(),
                "emotions": json.dumps({"multi": n["emos"]}, ensure_ascii=False),
                "triggers": n["reason"], "reappraise": n["oneword"],
                "action": n["step"], "value": n["switch"]
            }
            append_csv(CBT_CSV, row_cbt)

            row_mix = {
                "ts": now_ts(), "mode":"note", "emos":" ".join(n["emos"]), "reason": n["reason"],
                "oneword": n["oneword"], "step": n["step"], "switch": n["switch"],
                "memo_len": len(n["memo"]), "memo_saved": int(bool(n["save_text"]))
            }
            if n["save_text"] and n["memo"]:
                row_mix["memo"] = n["memo"]
            append_csv(MIX_CSV, row_mix)

            st.session_state.note = {"emos": [], "reason":"", "oneword":"", "step":"", "switch":"", "memo":"", "save_text": False}
            st.success("保存しました。ここまでで十分。次は『外の光5分』に挑戦する？")
    with c2:
        if st.button("🧼 入力を初期化", key="note_reset"):
            st.session_state.note = {"emos": [], "reason":"", "oneword":"", "step":"", "switch":"", "memo":"", "save_text": False}
            st.info("初期化しました。")

# =================== Sturdy Tracker ===================
SUBJ_DEFAULT = ["国語","数学","英語","理科","社会","小論","過去問","面接","実技"]
MOODS = ["😌集中","😕難航","😫しんどい"]

def view_study():
    st.subheader("📚 Sturdy Tracker（15分=1ブロック）")
    st.caption("5分でもOK（四捨五入で1ブロック）。“配分の手触り”を残す軽量ログ。")

    subj = st.selectbox("科目", options=SUBJ_DEFAULT + ["＋追加"], index=2, key="study_subj")
    if subj=="＋追加":
        new = st.text_input("科目名を追加", "", key="study_new")
        if new: subj = new
    blocks = st.slider("ブロック数（15分単位）", 1, 8, 1, key="study_blocks")
    mood = st.selectbox("雰囲気", options=MOODS, index=0, key="study_mood")
    memo = st.text_input("学びメモ（1行）", key="study_memo", placeholder="例：関数の文章題は朝が楽")
    if st.button("💾 記録", type="primary", key="study_save"):
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
            else:
                st.caption("直近7日の記録がありません。")
        except Exception:
            st.caption("集計時にエラーが発生しました。")
    st.markdown('</div>', unsafe_allow_html=True)

# =================== エクスポート ===================
def export_and_wipe(label: str, path: Path, download_name: str):
    df = load_csv(path)
    if df.empty:
        st.caption(f"{label}：まだデータがありません")
        return
    data = df.to_csv(index=False).encode("utf-8-sig")
    dl = st.download_button(f"⬇️ {label} を保存", data, file_name=download_name, mime="text/csv", key=f"dl_{download_name}")
    if dl and st.button(f"🗑 {label} をこの端末から消去する", type="secondary", key=f"wipe_{download_name}"):
        try:
            path.unlink(missing_ok=True)
            st.success("端末から安全に消去しました。")
        except Exception:
            st.warning("消去に失敗しました。ファイルが開かれていないか確認してください。")

def view_export():
    st.subheader("⬇️ 記録・エクスポート（CSV）／安全消去")
    export_and_wipe("2分ノート（互換）", CBT_CSV,   "cbt_entries.csv")
    export_and_wipe("呼吸",             BREATH_CSV, "breath_sessions.csv")
    export_and_wipe("心を整える（統合）", MIX_CSV,   "mix_note.csv")
    export_and_wipe("Sturdy Tracker",   STUDY_CSV,  "study_blocks.csv")

# =================== ルーター ===================
top_nav()
v = st.session_state.view
if v=="HOME":    view_home()
elif v=="RESCUE":view_rescue()
elif v=="BREATH":view_breath()
elif v=="NOTE":  view_note()
elif v=="STUDY": view_study()
else:            view_export()

# =================== フッター ===================
st.markdown("""
<div style="text-align:center; color:#8b8fb5; margin-top:12px;">
  <small>※ 個人名や連絡先は記入しないでください。<br>
  とてもつらい場合は、お住まいの地域の相談窓口や専門機関のご利用もご検討ください。</small>
</div>
""", unsafe_allow_html=True)
