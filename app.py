# app.py — Sora（安全設計版：呼吸×CBT×生活リズム）
# 要件反映：
#  - 呼吸：初回90秒固定 / 穏やか版(吸4-吐6)→安定で落ち着き用(吸5-止2-吐6)へ自動
#  - 息止めは最大2秒、途中停止(×)、連続3回で休憩案内、実行中は入力不可
#  - CBT：emoji強度1-5、きっかけチップ、認知パターン→再評価一行、セルフ・コンパッション、
#          今日の一歩（価値タグ連動）、結果は1スクロール表示
#  - 追加：良いことの振り返り、朝1分、Study Tracker、Me（週リズム）
#  - 保存：data/*.csv（端末のみ）。学校共有は数値のみDL

from __future__ import annotations
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import pandas as pd
import streamlit as st
import time, uuid, json

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
  --bg:#0f1022; --panel:#171833; --panel-brd:#3a3d66; --text:#f6f4ff; --muted:#b5b7d4;
  --accent1:#ffd9cc; --accent2:#ff9ec3; --accent3:#ffc4dd; --outline:#6a6fb0;
  --grad-from:#ff9fb0; --grad-to:#ff78a2; --chip-brd:rgba(255,189,222,.35);
  --tile-a:#ffb37c; --tile-b:#ffe0c2; --tile-c:#ff9ec3; --tile-d:#ffd6ea;
  --tile-e:#c4a4ff; --tile-f:#e8dbff; --tile-g:#89d7ff; --tile-h:#d4f2ff;
}
html, body, .stApp{background:var(--bg)}
.block-container{max-width:980px; padding-top:0.4rem; padding-bottom:2rem; position:relative; z-index:1}
h1,h2,h3{color:var(--text); letter-spacing:.2px}
p,label,.stMarkdown,.stTextInput,.stTextArea{color:var(--text); font-size:1.05rem}
small{color:var(--muted)}
.card{background:var(--panel); border:1px solid var(--panel-brd); border-radius:20px; padding:18px; margin-bottom:14px;
      box-shadow:0 22px 44px rgba(11,12,30,.25)}

.hero{
  border:2px solid rgba(255,217,204,.45);
  background:linear-gradient(180deg, rgba(36,38,80,.55), rgba(26,27,58,.55));
  padding:22px; border-radius:24px; margin:10px 0 14px;
}
.hero h1{color:var(--text); font-size:1.5rem; font-weight:900; margin:.2rem 0 1rem}
.hero .lead{font-size:1.9rem; font-weight:900; color:var(--accent1); margin:.4rem 0 1.2rem}
.hero .box{border:2px solid rgba(255,217,204,.55); border-radius:18px; padding:14px; margin:10px 0 14px;
           background:linear-gradient(180deg, rgba(28,29,66,.7), rgba(23,24,52,.7)); color:var(--text)}
.hero .badges{display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin:10px 0 4px}
.hero .badge{background:linear-gradient(180deg, #2b2d66, #232553); border:2px solid rgba(255,217,204,.45);
             border-radius:16px; padding:12px; text-align:center; color:var(--accent1); font-weight:800}
.hero .badge .big{font-size:1.7rem; color:#fff}
.hero .list{background:linear-gradient(180deg,#23244d,#1b1c41); border:2px solid rgba(255,217,204,.45);
            border-radius:18px; padding:12px 14px}
.hero li{margin:.2rem 0}

/* Top nav (ghost) */
.topbar{position:sticky; top:0; z-index:10; background:rgba(15,16,34,.7); backdrop-filter:blur(8px);
        border-bottom:1px solid #2e3263; margin:0 -12px 8px; padding:8px 12px 10px}
.topnav{display:flex; gap:8px; flex-wrap:wrap; margin:4px 0 2px}
.topnav .nav-btn>button{
  background:#fbfbff !important; color:#1e1f3f !important; border:1px solid #d9dbe8 !important; box-shadow:none !important;
  height:auto !important; padding:9px 12px !important; border-radius:12px !important; font-weight:700 !important; font-size:.95rem !important;
}
.topnav .nav-btn>button:hover{background:#ffffff !important;}
.topnav .active>button{background:#f4f3ff !important; border:2px solid #7d74ff !important}
.nav-hint{font-size:.78rem; color:#aeb2df; margin:0 2px 6px 2px}

/* Buttons / chips */
.stButton>button,.stDownloadButton>button{
  width:100%; padding:12px 16px; border-radius:999px; border:1px solid var(--chip-brd);
  background:linear-gradient(180deg,var(--grad-from),var(--grad-to)); color:#fff; font-weight:900; font-size:1.02rem;
  box-shadow:0 14px 28px rgba(255,120,162,.22)
}
.stButton>button:hover{filter:brightness(.98)}
.chips{display:flex; gap:8px; flex-wrap:wrap; margin:8px 0 10px}
.chips .chip-btn>button{
  background:linear-gradient(180deg,#ffbcd2,#ff99bc); color:#3a2144; border:1px solid var(--chip-brd)!important;
  padding:10px 14px; height:auto; border-radius:999px!important; font-weight:900; box-shadow:0 10px 20px rgba(255,153,188,.12)
}

/* Emoji grid with intensity */
.emoji-grid{display:grid; grid-template-columns:repeat(9,1fr); gap:8px; margin:8px 0 6px}
.emoji{display:flex; flex-direction:column; align-items:center; gap:6px}
.emoji .btn>button{
  width:100%!important; aspect-ratio:1/1; border-radius:16px!important; font-size:1.3rem!important; background:#fff; color:#111;
  border:1px solid #eadfff!important; box-shadow:0 8px 16px rgba(12,13,30,.28)
}
.intensity{height:6px; width:70%; border-radius:999px; background:#eee}
.intensity .bar{height:100%; border-radius:999px; background:linear-gradient(90deg,#ffc6a3,#ff9fbe)}

/* Inputs dark */
textarea, input, .stTextInput>div>div>input{border-radius:14px!important; background:#0f0f23; color:#f0eeff; border:1px solid #3a3d66}

/* Home tiles */
.tile-grid{display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:8px}
.tile .stButton>button{
  aspect-ratio:1/1; min-height:210px; border-radius:28px; text-align:left; padding:20px; white-space:normal; line-height:1.2;
  border:none; font-weight:900; font-size:1.16rem; color:#2d2a33; box-shadow:0 20px 36px rgba(8,8,22,.45);
  display:flex; align-items:flex-end; justify-content:flex-start;
}
.tile-a .stButton>button{background:linear-gradient(160deg,var(--tile-a),var(--tile-b))}
.tile-b .stButton>button{background:linear-gradient(160deg,var(--tile-c),var(--tile-d))}
.tile-c .stButton>button{background:linear-gradient(160deg,var(--tile-e),var(--tile-f))}
.tile-d .stButton>button{background:linear-gradient(160deg,var(--tile-g),var(--tile-h))}

/* Breath circle */
.breath-wrap{display:flex; justify-content:center; align-items:center; padding:8px 0 4px}
.breath-circle{
  width:220px; height:220px; border-radius:999px; background:radial-gradient(circle at 50% 40%, #ffe6ee, #ffd0ea 60%, #d4cfff 100%);
  box-shadow:0 18px 38px rgba(255,140,180,.18), inset 0 -10px 25px rgba(60,60,140,.25);
  transform:scale(var(--scale, 1)); transition:transform .9s ease-in-out, filter .3s ease-in-out;
  border:2px solid rgba(255,217,204,.35);
}
.phase-pill{display:inline-block; padding:.20rem .7rem; border-radius:999px; background:rgba(125,116,255,.12);
  color:#e9e5ff; border:1px solid rgba(125,116,255,.35); font-weight:700}
.count-box{font-size:40px; font-weight:900; text-align:center; color:#fff; padding:2px 0}
.subtle{color:#bfc3f3; font-size:.92rem}

/* Mobile */
@media (max-width: 840px){ .emoji-grid{grid-template-columns:repeat(6,1fr)} }
@media (max-width: 640px){ .emoji-grid{grid-template-columns:repeat(4,1fr)} .tile-grid{grid-template-columns:1fr}
  .tile .stButton>button{min-height:180px} .block-container{padding-left:1rem; padding-right:1rem} }
</style>
    """, unsafe_allow_html=True)

inject_css()

# ---------------- Data paths ----------------
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
CBT_CSV        = DATA_DIR / "cbt_entries.csv"
BREATH_CSV     = DATA_DIR / "breath_sessions.csv"
REFLECT_CSV    = DATA_DIR / "daily_good.csv"
MORNING_CSV    = DATA_DIR / "morning_check.csv"
STUDY_CSV      = DATA_DIR / "study_blocks.csv"
ME_CSV         = DATA_DIR / "me_color.csv"   # 今日の色・呼吸回数・睡眠など

def now_ts():
    return datetime.now().isoformat(timespec="seconds")

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
st.session_state.setdefault("view", "INTRO")
st.session_state.setdefault("breath_mode", "gentle")     # "gentle"(吸4-吐6) → "calm"(吸5-止2-吐6)
st.session_state.setdefault("breath_runs", 0)            # 連続回数
st.session_state.setdefault("breath_success", 0)         # 安定完走カウンタ
st.session_state.setdefault("breath_running", False)
st.session_state.setdefault("breath_stop", False)
st.session_state.setdefault("disable_ui", False)
st.session_state.setdefault("cbt", {})
st.session_state.setdefault("me_color", "")

# ---------------- Nav ----------------
def top_nav():
    st.markdown('<div class="topbar">', unsafe_allow_html=True)
    st.markdown('<div class="nav-hint">ページ移動</div>', unsafe_allow_html=True)
    st.markdown('<div class="topnav">', unsafe_allow_html=True)
    pages = [("INTRO","👋 はじめに"),("HOME","🏠 ホーム"),("BREATH","🌬 呼吸"),("CBT","📓 2分ノート"),
             ("GOOD","✨ 良いこと"),("MORNING","🌅 朝1分"),("STUDY","📚 Study Tracker"),
             ("ME","🧭 Me"),("HISTORY","📚 記録を見る"),("EXPORT","⬇️ エクスポート")]
    cols = st.columns(len(pages))
    for i,(key,label) in enumerate(pages):
        cls = "nav-btn active" if st.session_state.view==key else "nav-btn"
        with cols[i]:
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(label, key=f"nav_{key}", use_container_width=True, disabled=st.session_state.disable_ui):
                st.session_state.view = key
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

# ---------------- INTRO ----------------
def view_intro():
    st.markdown("""
<div class="hero">
  <h1>言葉の前に、息をひとつ。</h1>
  <div class="lead">“がんばらないで落ち着ける” 2分の小さな習慣。</div>
  <div class="box">
    <div style="font-weight:900; color:var(--accent1); margin-bottom:6px;">これは何？</div>
    <div>呼吸でおだやかさを取り戻し、3タップで負のループを止め、生活の流れを整えるサポートアプリです。<br>
    データはこの端末だけ。学校共有は希望時に数値のみ。</div>
  </div>
  <div class="badges">
    <div class="badge"><div>🌬</div><div class="big">安全設計</div></div>
    <div class="badge"><div>🕒</div><div class="big">約 2 分</div></div>
    <div class="badge"><div>🔒</div><div style="font-size:.95rem;line-height:1.2">端末のみ保存／途中終了OK／医療ではありません</div></div>
  </div>
  <div class="list">
    <div style="font-weight:900; color:var(--accent1); margin-bottom:6px;">今日できること</div>
    <ol style="margin:0 0 0 1.2rem">
      <li>呼吸で落ち着く（約90秒）</li>
      <li>気持ちを3タップで整理</li>
      <li>1分タスクを決めておしまい</li>
    </ol>
  </div>
</div>
    """, unsafe_allow_html=True)
    cta1, cta2 = st.columns([3,2])
    with cta1:
        if st.button("今すぐ呼吸をはじめる（約90秒）", use_container_width=True):
            st.session_state.view = "BREATH"
    with cta2:
        if st.button("ホームを見る", use_container_width=True):
            st.session_state.view = "HOME"

# ---------------- HOME ----------------
def view_home():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 本日、どのように進めますか？")
    st.markdown('<div class="tile-grid">', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="tile tile-a">', unsafe_allow_html=True)
        if st.button("🌬 呼吸（約90秒/安全設計）", key="tile_breath"): st.session_state.view="BREATH"
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="tile tile-b">', unsafe_allow_html=True)
        if st.button("📓 2分ノート（CBT）", key="tile_cbt"): st.session_state.view="CBT"
        st.markdown('</div>', unsafe_allow_html=True)
    c3, c4 = st.columns(2)
    with c3:
        st.markdown('<div class="tile tile-c">', unsafe_allow_html=True)
        if st.button("✨ 良いことの振り返り", key="tile_good"): st.session_state.view="GOOD"
        st.markdown('</div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="tile tile-d">', unsafe_allow_html=True)
        if st.button("📚 記録 / エクスポート", key="tile_hist"): st.session_state.view="HISTORY"
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.caption("夜は「呼吸/感情整理」、朝は「朝1分/Study」、昼は「1分タスク/Study」をおすすめします。")

# ---------------- 呼吸（安全設計 × 自動） ----------------
def breath_patterns() -> Dict[str, Tuple[int,int,int]]:
    # return (inhale, hold, exhale) with hold<=2
    return {
        "gentle": (4, 0, 6),   # 不安高い子向け
        "calm":   (5, 2, 6),   # 落ち着き用（止めは2秒固定）
    }

def compute_cycles(target_sec: int, pat: Tuple[int,int,int]) -> int:
    per = pat[0] + pat[1] + pat[2]
    return max(1, round(target_sec / per))

def run_breath_session(total_sec: int=90):
    pat = breath_patterns()[st.session_state.breath_mode]
    inhale, hold, exhale = pat
    cycles = compute_cycles(total_sec, pat)

    # UI lock & flags
    st.session_state.breath_running = True
    st.session_state.breath_stop = False
    st.session_state.disable_ui = True

    # Header
    st.subheader("いっしょに息を。ここにいていいよ。")
    st.caption("※ 手は使わなくて大丈夫。目を閉じても分かるようにフェーズ表示します。")

    phase_box = st.empty()
    count_box = st.empty()
    circle_holder = st.empty()
    prog = st.progress(0, text="呼吸セッション")
    t_start = time.time()
    elapsed = 0
    total = cycles * (inhale + hold + exhale)

    # STOPボタン
    col_stop, col_hint = st.columns([1,2])
    with col_stop:
        if st.button("× 停止する", use_container_width=True):
            st.session_state.breath_stop = True
    with col_hint:
        st.markdown('<div class="subtle">息止めは最大2秒まで。無理はしないでOK。</div>', unsafe_allow_html=True)

    # Loop
    for c in range(cycles):
        if st.session_state.breath_stop: break

        # 吸う
        for t in range(inhale,0,-1):
            if st.session_state.breath_stop: break
            phase_box.markdown("<span class='phase-pill'>吸う</span>", unsafe_allow_html=True)
            circle_holder.markdown(f"<div class='breath-wrap'><div class='breath-circle' style='--scale:{1.0 + 0.6*(1 - (t-1)/max(inhale-1,1))}'></div></div>", unsafe_allow_html=True)
            count_box.markdown(f"<div class='count-box'>{t}</div>", unsafe_allow_html=True)
            elapsed += 1; prog.progress(min(int(elapsed/total*100), 100))
            time.sleep(1)

        if st.session_state.breath_stop: break

        # 止める（最大2秒）
        if hold > 0:
            for t in range(hold,0,-1):
                if st.session_state.breath_stop: break
                phase_box.markdown("<span class='phase-pill'>とまる</span>", unsafe_allow_html=True)
                circle_holder.markdown(f"<div class='breath-wrap'><div class='breath-circle' style='--scale:1.6'></div></div>", unsafe_allow_html=True)
                count_box.markdown(f"<div class='count-box'>{t}</div>", unsafe_allow_html=True)
                elapsed += 1; prog.progress(min(int(elapsed/total*100), 100))
                time.sleep(1)

        if st.session_state.breath_stop: break

        # 吐く
        for t in range(exhale,0,-1):
            if st.session_state.breath_stop: break
            phase_box.markdown("<span class='phase-pill'>はく</span>", unsafe_allow_html=True)
            circle_holder.markdown(f"<div class='breath-wrap'><div class='breath-circle' style='--scale:{1.0 + 0.6*((t-1)/max(exhale-1,1))}'></div></div>", unsafe_allow_html=True)
            count_box.markdown(f"<div class='count-box'>{t}</div>", unsafe_allow_html=True)
            elapsed += 1; prog.progress(min(int(elapsed/total*100), 100))
            time.sleep(1)

        if st.session_state.breath_stop: break

    # Finish
    st.session_state.breath_running = False
    st.session_state.disable_ui = False
    finished = not st.session_state.breath_stop

    if finished:
        st.success("ここまで来たあなたは十分えらい。おつかれさま。")
        st.session_state.breath_runs += 1
        st.session_state.breath_success += 1
        # 自動モード切替（2回完走で calm へ）
        if st.session_state.breath_mode == "gentle" and st.session_state.breath_success >= 2:
            st.info("次回から少しだけ深い呼吸に切り替えます（吸5・止2・吐6）。")
            st.session_state.breath_mode = "calm"
    else:
        st.warning("今回はここまでにしましょう。いつでも再開できます。")
        st.session_state.breath_runs = 0  # リセット

    # 休憩誘導
    if st.session_state.breath_runs >= 3:
        st.info("少し休憩をはさみましょう（過換気予防）。水を一口、窓を少し開ける、手首に冷水10秒、姿勢を1ミリ。")
        st.session_state.breath_runs = 0

    # 記録＋1分タスク＋今日の色
    note = st.text_input("メモ（任意）", placeholder="例：少し肩の力が抜けた")
    tasks = ["水を一口","窓を少し開ける","手首に冷水10秒","姿勢を1ミリ正す"]
    st.caption("1分タスク（タップで挿入）")
    st.markdown("<div class='chips'>", unsafe_allow_html=True)
    for i, tsk in enumerate(tasks):
        st.markdown("<div class='chip-btn'>", unsafe_allow_html=True)
        if st.button(tsk, key=f"bpsk_{i}"): note = (note + (" / " if note else "") + tsk)
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.caption("“今日の色” をひとつ（Meに反映）")
    colors = ["🩵やわらか","💜静か","💗あたたか","💛ひかり","🩶保留"]
    col_sel = st.selectbox("今日の色", colors, index=0)
    if st.button("💾 保存", type="primary"):
        row = {
            "id": f"breath-{now_ts()}",
            "ts": now_ts(),
            "mode": st.session_state.breath_mode,
            "target_sec": total_sec,
            "inhale": inhale, "hold": hold, "exhale": exhale,
            "cycles": cycles, "stopped": (not finished),
            "note": note, "color": col_sel
        }
        append_csv(BREATH_CSV, row)
        append_csv(ME_CSV, {"ts": now_ts(), "kind":"color", "value": col_sel})
        st.session_state.me_color = col_sel
        st.success("保存しました。")

    # 再開ショートカット（UIは出しすぎない）
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("もう一度（90秒）"): run_breath_session(90)
    with c2:
        if st.button("短め（60秒）"): run_breath_session(60)
    with c3:
        if st.button("ながめ（180秒）"): run_breath_session(180)

def view_breath():
    st.subheader("🌬 呼吸で落ち着く（安全設計）")
    # モード表示のみ（設定UIは出さない）
    mode_name = "穏やか版（吸4・吐6）" if st.session_state.breath_mode=="gentle" else "落ち着き用（吸5・止2・吐6）"
    st.caption(f"現在のガイド：{mode_name}（自動で最適化）")
    # 実行
    if not st.session_state.breath_running:
        if st.button("開始（約90秒）", type="primary"):
            run_breath_session(90)
    else:
        st.info("実行中です…")

# ---------------- CBT（3タップでループを切る） ----------------
EMOJIS = [("😠","怒"),("😢","悲"),("😟","不安"),("😔","罪"),("😳","恥"),("😣","焦"),("😐","退屈"),("🙂","安心"),("😊","嬉")]
TRIGGERS = ["家族","友達","恋愛","いじめ","SNS","勉強","宿題","部活","先生","体調","お金","将来"]
PATTERNS = [
    ("全か無か", "「全部じゃなくて“今の1問が難しい”かも」"),
    ("先読み不安", "「起きていない未来は、いったん保留」"),
    ("心の読み過ぎ", "「相手の頭の中は、実は分からない」"),
    ("レッテル貼り", "「一回の事実＝その人全部じゃない」"),
    ("過度の自己責任", "「事情のせいも少しあるかも」"),
]
COMPASSION = ["こう感じるのは自然","いまはつらい。わたしに優しく","休むのも前進","今日はここまでで十分"]
ACTIONS = ["課題を“1問だけ”","友達にスタンプだけ","5分だけ外の光","水を飲む","机の上を30秒だけ"]
VALUES = ["挑戦","健康","友情","学び","自分を大切に","誠実"]

def ensure_cbt():
    c = st.session_state.cbt
    c.setdefault("emo", {k:0 for _,k in EMOJIS})
    c.setdefault("triggers", [])
    c.setdefault("trigger_free","")
    c.setdefault("pattern","")
    c.setdefault("reappraise","")
    c.setdefault("compassion","")
    c.setdefault("action","")
    c.setdefault("value","")
    st.session_state.cbt = c

def emoji_grid_with_intensity():
    st.caption("いまの気持ち（タップで強さ1→5、6で0に戻る／複数OK）")
    st.markdown('<div class="emoji-grid">', unsafe_allow_html=True)
    cols = st.columns(9)
    for i,(e,label) in enumerate(EMOJIS):
        with cols[i%len(cols)]:
            cur = st.session_state.cbt["emo"][label]
            st.markdown('<div class="emoji">', unsafe_allow_html=True)
            if st.button(e, key=f"emo_{label}", use_container_width=True):
                st.session_state.cbt["emo"][label] = 0 if cur>=5 else cur+1
            # intensity bar
            pct = int((st.session_state.cbt["emo"][label]/5)*100)
            st.markdown(f"<div class='intensity'><div class='bar' style='width:{pct}%'></div></div>", unsafe_allow_html=True)
            st.caption(label)
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def trigger_chips():
    st.caption("きっかけ（複数可）")
    st.markdown("<div class='chips'>", unsafe_allow_html=True)
    cols = st.columns(6)
    cur = set(st.session_state.cbt["triggers"])
    for i, tg in enumerate(TRIGGERS):
        with cols[i%6]:
            st.markdown("<div class='chip-btn'>", unsafe_allow_html=True)
            on = tg in cur
            if st.button(tg + (" ✓" if on else ""), key=f"tg_{tg}", use_container_width=True):
                if on: cur.remove(tg)
                else: cur.add(tg)
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.session_state.cbt["triggers"] = list(cur)
    st.session_state.cbt["trigger_free"] = st.text_input("自由ワード（1行でOK）", placeholder="例：返信なし／提出が近い など", value=st.session_state.cbt["trigger_free"])

def pattern_and_reappraise():
    st.caption("考えのパターン（近いものを1つ） → 優しい再評価テンプレが出ます")
    cols = st.columns(3)
    chosen = st.session_state.cbt["pattern"]
    for i,(name, tmpl) in enumerate(PATTERNS):
        with cols[i%3]:
            st.markdown("<div class='chip-btn'>", unsafe_allow_html=True)
            if st.button(name + (" ✓" if chosen==name else ""), key=f"pt_{name}", use_container_width=True):
                st.session_state.cbt["pattern"] = name
                st.session_state.cbt["reappraise"] = tmpl
            st.markdown("</div>", unsafe_allow_html=True)
    st.session_state.cbt["reappraise"] = st.text_area("やさしい捉え直し（編集可・1行でもOK）",
                                                     value=st.session_state.cbt["reappraise"], height=80)

def compassion_and_action():
    st.caption("セルフ・コンパッションの一言（選ぶだけでもOK）")
    cols = st.columns(3)
    for i,msg in enumerate(COMPASSION):
        with cols[i%3]:
            st.markdown("<div class='chip-btn'>", unsafe_allow_html=True)
            if st.button(msg, key=f"co_{i}", use_container_width=True):
                st.session_state.cbt["compassion"] = msg
            st.markdown("</div>", unsafe_allow_html=True)
    st.session_state.cbt["compassion"] = st.text_input("↑ 編集可", value=st.session_state.cbt["compassion"])

    st.caption("“今日の一歩”（1〜3分）※価値タグに紐づきます")
    cols2 = st.columns(3)
    for i,act in enumerate(ACTIONS):
        with cols2[i%3]:
            st.markdown("<div class='chip-btn'>", unsafe_allow_html=True)
            if st.button(act, key=f"ac_{i}", use_container_width=True):
                st.session_state.cbt["action"] = act
            st.markdown("</div>", unsafe_allow_html=True)
    st.session_state.cbt["action"] = st.text_input("内容（編集可）", value=st.session_state.cbt["action"], placeholder="例：プリント1枚の半分だけ")
    st.caption("価値タグ")
    st.session_state.cbt["value"] = st.selectbox("大事にしたいこと", VALUES, index=0)

def render_result_preview_and_save():
    # 結果プレビュー（1スクロール）
    emo_list = [f"{k}{'・'*v}" for k,v in st.session_state.cbt["emo"].items() if v>0]
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 結果（プレビュー）")
    st.markdown(f"**気持ちの色**：{' / '.join(emo_list) if emo_list else '（未選択）'}")
    tg = st.session_state.cbt["triggers"]; tf = st.session_state.cbt["trigger_free"]
    st.markdown(f"**きっかけ**：{'・'.join(tg) if tg else '（未選択）'} ／ {tf}")
    st.markdown(f"**捉え直し**：{st.session_state.cbt['reappraise']}")
    st.markdown(f"**セルフ・コンパッション**：{st.session_state.cbt['compassion']}")
    st.markdown(f"**今日の一歩**：{st.session_state.cbt['action']} 〔価値：{st.session_state.cbt['value']}〕")
    st.markdown('</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 保存して完了"):
            row = {
                "id": f"cbt-{now_ts()}",
                "ts": now_ts(),
                "emotions": json.dumps(st.session_state.cbt["emo"], ensure_ascii=False),
                "triggers": " ".join(st.session_state.cbt["triggers"]),
                "trigger_free": st.session_state.cbt["trigger_free"],
                "pattern": st.session_state.cbt["pattern"],
                "reappraise": st.session_state.cbt["reappraise"],
                "compassion": st.session_state.cbt["compassion"],
                "action": st.session_state.cbt["action"],
                "value": st.session_state.cbt["value"],
            }
            append_csv(CBT_CSV, row)
            st.session_state.cbt = {}
            ensure_cbt()
            st.success("保存しました。今日はここでおしまいでもOK。")
    with c2:
        if st.button("🧼 入力欄を初期化"):
            st.session_state.cbt = {}
            ensure_cbt()
            st.info("初期化しました。")

def view_cbt():
    ensure_cbt()
    st.subheader("📓 2分ノート（3タップで負のループを止める）")
    emoji_grid_with_intensity()
    trigger_chips()
    pattern_and_reappraise()
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("やさしい一言 と 今日の一歩")
    compassion_and_action()
    st.markdown('</div>', unsafe_allow_html=True)
    render_result_preview_and_save()

# ---------------- 良いことの振り返り（3粒度） ----------------
def view_good():
    st.subheader("✨ 良いことの振り返り（3粒度）")
    micro = st.text_input("マイクロ（今日：嬉しかった1つ）", placeholder="例：空の色がきれいだった")
    act   = st.text_input("ミクロ行動（やれた1つ）", placeholder="例：朝に窓を開けた")
    selfm = st.text_input("自己肯定（自分にかける一言）", placeholder="例：今日は十分がんばった")
    st.caption("介護や家事で忙しい人向けの文例：『助けを求められた』『自分に優しくできた』 など")
    if st.button("💾 保存", type="primary"):
        append_csv(REFLECT_CSV, {"id":f"good-{now_ts()}","ts":now_ts(),"micro":micro,"act":act,"self":selfm})
        st.success("保存しました。")

# ---------------- 朝1分 ----------------
def view_morning():
    st.subheader("🌅 朝1分（睡眠/ストレス/エネルギー/意図）")
    sleep_h = st.number_input("睡眠時間（h）", 0.0, 24.0, 6.5, 0.5)
    sleep_q = st.slider("睡眠の満足（0〜10）", 0, 10, 6)
    stress  = st.slider("ストレス（0〜10）", 0, 10, 4)
    energy  = st.slider("エネルギー（0〜10）", 0, 10, 5)
    intent  = st.text_input("今日の意図（1行）", placeholder="例：朝に英単語10分")
    if st.button("💾 保存", type="primary"):
        append_csv(MORNING_CSV, {"ts":now_ts(),"sleep_h":sleep_h,"sleep_q":sleep_q,"stress":stress,"energy":energy,"intent":intent})
        st.success("保存しました。")

# ---------------- Study Tracker ----------------
SUBJ_DEFAULT = ["国語","数学","英語","理科","社会","小論","過去問","面接","実技"]
MOODS = ["😌集中","😕難航","😫しんどい"]

def view_study():
    st.subheader("📚 Study Tracker（配分×手触り）")
    st.caption("15分ブロックで記録（5分でもOK→四捨五入で1ブロック）")
    subj = st.selectbox("科目", options=SUBJ_DEFAULT + ["＋追加"], index=2)
    if subj=="＋追加":
        new = st.text_input("科目名を追加", "")
        if new:
            subj = new
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
    st.caption("提案：英語が“夜にしんどい”→朝の10分へ。数学が“難航”→例題→教科書の順。")

# ---------------- Me（週のリズム） ----------------
def view_me():
    st.subheader("🧭 Me（週のリズム）")
    st.caption("睡眠・呼吸回数・“今日の色”の推移をざっくり見る（競争/点数化はしません）")
    me = load_csv(ME_CSV)
    if me.empty:
        st.caption("まだ記録がありません。")
    else:
        st.dataframe(me.tail(50), use_container_width=True, hide_index=True)

# ---------------- History / Export ----------------
def view_history():
    st.subheader("📚 記録を見る")
    with st.expander("📓 2分ノート"):
        df = load_csv(CBT_CSV)
        if df.empty: st.caption("記録なし")
        else:
            st.dataframe(df.tail(50), use_container_width=True, hide_index=True)
    with st.expander("🌬 呼吸"):
        df = load_csv(BREATH_CSV)
        if df.empty: st.caption("記録なし")
        else:
            st.dataframe(df.tail(50), use_container_width=True, hide_index=True)
    with st.expander("✨ 良いこと"):
        df = load_csv(REFLECT_CSV)
        if df.empty: st.caption("記録なし")
        else:
            st.dataframe(df.tail(50), use_container_width=True, hide_index=True)
    with st.expander("🌅 朝1分"):
        df = load_csv(MORNING_CSV)
        if df.empty: st.caption("記録なし")
        else:
            st.dataframe(df.tail(50), use_container_width=True, hide_index=True)
    with st.expander("📚 Study"):
        df = load_csv(STUDY_CSV)
        if df.empty: st.caption("記録なし")
        else:
            st.dataframe(df.tail(50), use_container_width=True, hide_index=True)

def view_export():
    st.subheader("⬇️ エクスポート（CSV）／設定")
    def dl(df: pd.DataFrame, label: str, name: str):
        if df.empty: st.caption(f"{label}：まだデータがありません"); return
        st.download_button(f"⬇️ {label}", df.to_csv(index=False).encode("utf-8-sig"), file_name=name, mime="text/csv")
    dl(load_csv(CBT_CSV), "2分ノート", "cbt_entries.csv")
    dl(load_csv(BREATH_CSV), "呼吸", "breath_sessions.csv")
    dl(load_csv(REFLECT_CSV), "良いこと", "daily_good.csv")
    dl(load_csv(MORNING_CSV), "朝1分（数値のみ）", "morning_check.csv")
    dl(load_csv(STUDY_CSV), "Study Tracker", "study_blocks.csv")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    danger = st.checkbox("⚠️ すべての保存データ（CSV）を削除することに同意します")
    if st.button("🗑️ すべて削除（取り消し不可）", disabled=not danger):
        for p in [CBT_CSV,BREATH_CSV,REFLECT_CSV,MORNING_CSV,STUDY_CSV,ME_CSV]:
            try:
                if p.exists(): p.unlink()
            except Exception as e:
                st.error(f"{p.name}: {e}")
        st.success("削除しました。")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Router ----------------
top_nav()
v = st.session_state.view
if v=="INTRO":   view_intro()
elif v=="HOME":  view_home()
elif v=="BREATH": view_breath()
elif v=="CBT":   view_cbt()
elif v=="GOOD":  view_good()
elif v=="MORNING": view_morning()
elif v=="STUDY": view_study()
elif v=="ME":    view_me()
elif v=="HISTORY": view_history()
else:            view_export()

# ---------------- Footer ----------------
st.markdown("""
<div style="text-align:center; color:var(--muted); margin-top:12px;">
  <small>※ 個人名や連絡先は記入しないでください。<br>
  とてもつらい場合は、お住まいの地域の相談窓口や専門機関のご利用もご検討ください。</small>
</div>
""", unsafe_allow_html=True)
