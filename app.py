# app.py — Sora（簡潔ナビ版：ホーム統合／名称変更／色調統一）
# 変更点（ご要望反映）：
# - 「はじめに」と「ホーム」を統合（HOME=入口）
# - タブを6つに整理：HOME / 呼吸（心を休める呼吸ワーク）/ 心を整える / Study / 今日一日を振り返る / 記録・エクスポート
# - 「２分ノート」「良いこと」「朝1分」を「心を整える」に統合（1画面完結・最少タップ）
# - ヒーロー下の四角ボックス内から全機能へ遷移可能（大ボタン＋チップ）
# - 色トーン統一（ネイビー×ピンクグラデ）・モバイル最適化（少スクロール）

from __future__ import annotations
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, Tuple
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

# ---------------- Theme / CSS ----------------
def inject_css():
    st.markdown("""
<style>
:root{
  /* ネイビー×ピンクで統一 */
  --bg:#0f1022; --panel:#171833; --panel-brd:#3a3d66;
  --text:#f8f6ff; --muted:#b9bde0; --outline:#7d74ff;
  --grad-from:#ff9fb0; --grad-to:#ff78a2;
  --chip-brd:rgba(255,189,222,.35);
  --tile-a:#ffb37c; --tile-b:#ffe0c2;
  --tile-c:#ff9ec3; --tile-d:#ffd6ea;
  --tile-e:#c4a4ff; --tile-f:#e8dbff;
  --tile-g:#89d7ff; --tile-h:#d4f2ff;
}
html, body, .stApp{background:var(--bg)}
.block-container{max-width:980px; padding-top:.4rem; padding-bottom:2rem}
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
.hero .lead{font-size:1.9rem; font-weight:900; color:#ffd9cc; margin:.4rem 0 1.2rem}
.hero .box{border:2px solid rgba(255,217,204,.55); border-radius:18px; padding:14px; margin:10px 0 14px;
           background:linear-gradient(180deg, rgba(28,29,66,.7), rgba(23,24,52,.7)); color:var(--text)}
.hero .list{background:linear-gradient(180deg,#23244d,#1b1c41); border:2px solid rgba(255,217,204,.45);
            border-radius:18px; padding:12px 14px}
.hero .actions{display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:10px}
.hero .chips{display:flex; gap:8px; flex-wrap:wrap; margin:8px 0 0}

.topbar{position:sticky; top:0; z-index:10; background:rgba(15,16,34,.7); backdrop-filter:blur(8px);
        border-bottom:1px solid #2e3263; margin:0 -12px 8px; padding:8px 12px 10px}
.topnav{display:flex; gap:8px; flex-wrap:wrap; margin:2px 0}
.topnav .nav-btn>button{
  background:#fbfbff !important; color:#1e1f3f !important; border:1px solid #d9dbe8 !important; box-shadow:none !important;
  height:auto !important; padding:9px 12px !important; border-radius:12px !important; font-weight:700 !important; font-size:.95rem !important;
}
.topnav .active>button{background:#f4f3ff !important; border:2px solid var(--outline) !important}
.nav-hint{font-size:.78rem; color:#aeb2df; margin:0 2px 6px 2px}

.stButton>button,.stDownloadButton>button{
  width:100%; padding:12px 16px; border-radius:999px; border:1px solid var(--chip-brd);
  background:linear-gradient(180deg,var(--grad-from),var(--grad-to)); color:#fff; font-weight:900; font-size:1.02rem;
  box-shadow:0 14px 28px rgba(255,120,162,.22)
}
.stButton>button:hover{filter:brightness(.98)}

.tile-grid{display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:8px}
.tile .stButton>button{
  aspect-ratio:1/1; min-height:190px; border-radius:28px; text-align:left; padding:20px; white-space:normal; line-height:1.2;
  border:none; font-weight:900; font-size:1.16rem; color:#2d2a33; box-shadow:0 20px 36px rgba(8,8,22,.45);
  display:flex; align-items:flex-end; justify-content:flex-start;
}
.tile-a .stButton>button{background:linear-gradient(160deg,var(--tile-a),var(--tile-b))}
.tile-b .stButton>button{background:linear-gradient(160deg,var(--tile-c),var(--tile-d))}
.tile-c .stButton>button{background:linear-gradient(160deg,var(--tile-e),var(--tile-f))}
.tile-d .stButton>button{background:linear-gradient(160deg,var(--tile-g),var(--tile-h))}

/* 呼吸丸 */
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

/* 心を整える（最少UI） */
.emoji-row{display:grid; grid-template-columns:repeat(6,1fr); gap:8px}
.emoji-row .stButton>button{background:#fff!important; color:#222!important; border:1px solid #eadfff!important; border-radius:16px!important}
.chips{display:flex; gap:8px; flex-wrap:wrap; margin:8px 0 10px}
.chips .chip-btn>button{
  background:linear-gradient(180deg,#ffbcd2,#ff99bc); color:#3a2144; border:1px solid var(--chip-brd)!important;
  padding:8px 12px; height:auto; border-radius:999px!important; font-weight:900; box-shadow:0 10px 20px rgba(255,153,188,.12)
}

textarea, input, .stTextInput>div>div>input{border-radius:14px!important; background:#0f0f23; color:#f0eeff; border:1px solid #3a3d66}

@media (max-width: 680px){
  .tile-grid{grid-template-columns:1fr}
  .tile .stButton>button{min-height:170px}
  .emoji-row{grid-template-columns:repeat(4,1fr)}
  .block-container{padding-left:1rem; padding-right:1rem}
}
</style>
""", unsafe_allow_html=True)

inject_css()

# ---------------- Data paths ----------------
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
CBT_CSV    = DATA_DIR / "cbt_entries.csv"
BREATH_CSV = DATA_DIR / "breath_sessions.csv"
MIX_CSV    = DATA_DIR / "mix_note.csv"          # 心を整える（統合）
STUDY_CSV  = DATA_DIR / "study_blocks.csv"
ME_CSV     = DATA_DIR / "me_color.csv"

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
st.session_state.setdefault("disable_ui", False)
st.session_state.setdefault("breath_mode", "gentle")   # gentle→calmへ自動
st.session_state.setdefault("breath_running", False)
st.session_state.setdefault("breath_runs", 0)
st.session_state.setdefault("breath_success", 0)
st.session_state.setdefault("mix", {"emo":"","trigger":"","reframe":"","act":"","value":"","note":"", "sleep_h":6.5})

# ---------------- Top Nav（6項目に整理） ----------------
def top_nav():
    st.markdown('<div class="topbar">', unsafe_allow_html=True)
    st.markdown('<div class="nav-hint">ページ移動</div>', unsafe_allow_html=True)
    st.markdown('<div class="topnav">', unsafe_allow_html=True)
    pages = [
        ("HOME", "🏠 ホーム"),
        ("BREATH", "🌙 心を休める呼吸ワーク"),
        ("NOTE", "📝 心を整える"),
        ("STUDY", "📚 Study"),
        ("ME", "🧭 今日一日を振り返る"),
        ("EXPORT", "⬇️ 記録・エクスポート"),
    ]
    cols = st.columns(len(pages))
    for i,(key,label) in enumerate(pages):
        cls = "nav-btn active" if st.session_state.view==key else "nav-btn"
        with cols[i]:
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(label, key=f"nav_{key}", use_container_width=True, disabled=st.session_state.disable_ui):
                st.session_state.view = key
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

# ---------------- HOME（=はじめに） ----------------
def view_home():
    st.markdown("""
<div class="hero">
  <h1>言葉の前に、息をひとつ。</h1>
  <div class="lead">“がんばらないで落ち着ける” 2分の小さな習慣。</div>
  <div class="box">
    <div><b>できること</b>：呼吸でおだやかさを取り戻し、3タップで気持ちを整え、生活の流れをやさしく戻します。<br>
    データはこの端末だけ。学校共有は希望時に数値のみ。</div>
    <div class="actions">
      <div>""" , unsafe_allow_html=True)
    if st.button("🌙 今すぐ 呼吸をはじめる（約90秒）", use_container_width=True, key="home_go_breath"):
        st.session_state.view = "BREATH"
    st.markdown("</div><div>", unsafe_allow_html=True)
    if st.button("📝 心を整える（2分ノート＋良いこと＋朝1分）", use_container_width=True, key="home_go_note"):
        st.session_state.view = "NOTE"
    st.markdown("</div></div>", unsafe_allow_html=True)
    st.markdown('<div class="chips">', unsafe_allow_html=True)
    for label,key in [("📚 Study","STUDY"),("🧭 今日一日を振り返る","ME"),("⬇️ 記録・エクスポート","EXPORT")]:
        st.markdown('<span class="chip-btn">', unsafe_allow_html=True)
        if st.button(label, key=f"home_chip_{key}"): st.session_state.view = key
        st.markdown('</span>', unsafe_allow_html=True)
    st.markdown("</div></div>", unsafe_allow_html=True)

    # 下部に大きめの入口タイル（2つのみ）
    st.markdown('<div class="card"><div class="tile-grid">', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="tile tile-a">', unsafe_allow_html=True)
        if st.button("🌙 心を休める呼吸ワーク", key="tile_breath"): st.session_state.view="BREATH"
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="tile tile-b">', unsafe_allow_html=True)
        if st.button("📝 心を整える（最少タップ）", key="tile_note"): st.session_state.view="NOTE"
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

# ---------------- 呼吸（安全設計×自動） ----------------
def breath_patterns() -> Dict[str, Tuple[int,int,int]]:
    return {"gentle": (4,0,6), "calm": (5,2,6)}

def compute_cycles(target_sec: int, pat: Tuple[int,int,int]) -> int:
    per = sum(pat); return max(1, round(target_sec / per))

def run_breath_session(total_sec: int=90):
    inhale, hold, exhale = breath_patterns()[st.session_state.breath_mode]
    cycles = compute_cycles(total_sec, (inhale,hold,exhale))
    st.session_state.breath_running = True
    st.session_state.disable_ui = True
    st.subheader("いっしょに息を。ここにいていいよ。")
    st.caption("※ 手は使わなくてOK。目を閉じても分かるフェーズ表示。")

    phase_box = st.empty(); count_box = st.empty(); circle_holder = st.empty()
    prog = st.progress(0, text="呼吸セッション")
    elapsed = 0; total = cycles * (inhale + hold + exhale)

    col_stop, col_hint = st.columns([1,2])
    with col_stop:
        if st.button("× 停止", use_container_width=True): st.session_state.breath_running=False
    with col_hint:
        st.markdown('<div class="subtle">息止めは最大2秒。無理はしないでOK。</div>', unsafe_allow_html=True)

    def tick(label, secs, scale_from, scale_to):
        nonlocal elapsed
        for t in range(secs,0,-1):
            if not st.session_state.breath_running: return False
            phase_box.markdown(f"<span class='phase-pill'>{label}</span>", unsafe_allow_html=True)
            ratio = (secs - t)/(secs-1) if secs>1 else 1
            scale = scale_from + (scale_to-scale_from)*ratio
            circle_holder.markdown(f"<div class='breath-wrap'><div class='breath-circle' style='--scale:{scale}'></div></div>", unsafe_allow_html=True)
            count_box.markdown(f"<div class='count-box'>{t}</div>", unsafe_allow_html=True)
            elapsed += 1; prog.progress(min(int(elapsed/total*100), 100))
            time.sleep(1)
        return True

    for _ in range(cycles):
        if not st.session_state.breath_running: break
        if not tick("吸う", inhale, 1.0, 1.6): break
        if hold>0 and st.session_state.breath_running:
            if not tick("とまる", hold, 1.6, 1.6): break
        if not st.session_state.breath_running: break
        if not tick("はく", exhale, 1.6, 1.0): break

    finished = st.session_state.breath_running
    st.session_state.breath_running = False
    st.session_state.disable_ui = False

    if finished:
        st.success("ここまで来たあなたは十分えらい。おつかれさま。")
        st.session_state.breath_runs += 1
        st.session_state.breath_success += 1
        if st.session_state.breath_mode=="gentle" and st.session_state.breath_success>=2:
            st.info("次回から少し深い呼吸に切り替えます（吸5・止2・吐6）。")
            st.session_state.breath_mode = "calm"
    else:
        st.warning("今回はここまでにしましょう。いつでも再開できます。")
        st.session_state.breath_runs = 0

    note = st.text_input("メモ（任意）", placeholder="例：少し肩の力が抜けた")
    if st.button("💾 保存", type="primary"):
        append_csv(BREATH_CSV, {
            "ts": now_ts(), "mode": st.session_state.breath_mode,
            "target_sec": total_sec, "inhale": inhale, "hold": hold, "exhale": exhale,
            "note": note
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

# ---------------- 心を整える（2分ノート＋良いこと＋朝1分 統合）----------------
EMOJI_CHOICES = ["😟不安","😢悲しい","😠いらだち","😳恥ずかしい","🙂安心","😊うれしい"]
PATTERNS = [
    ("先読み不安","起きていない未来はいったん保留"),
    ("全か無か","全部じゃなくて“今の1つ”かも"),
    ("心の読み過ぎ","相手の頭の中は分からない"),
]
ACTIONS = ["課題を1問だけ","水を一口","外の光を5分","机の上を30秒だけ片付ける"]
VALUES = ["挑戦","健康","友情","学び","自分を大切に"]

def view_note():
    st.subheader("📝 心を整える（最少タップで1画面完結）")

    c = st.session_state.mix

    # 1) いまの気持ち（単一選択に絞って最少タップ）
    st.caption("いまの気持ち（1つ選ぶ）")
    cols = st.columns(6)
    for i, label in enumerate(EMOJI_CHOICES):
        with cols[i%6]:
            if st.button(("✓ " if c["emo"]==label else "")+label, key=f"emo_{i}"):
                c["emo"] = label

    # 2) きっかけ1行
    c["trigger"] = st.text_input("きっかけ（1行）", value=c["trigger"], placeholder="例：返信が来ない／提出が近い")

    # 3) やさしい捉え直し（テンプレタップ→編集可）
    st.caption("やさしい捉え直し（テンプレ→編集可）")
    cols2 = st.columns(3)
    for i,(name,tmpl) in enumerate(PATTERNS):
        with cols2[i%3]:
            if st.button(name, key=f"pt_{i}"): c["reframe"]=tmpl
    c["reframe"] = st.text_input("一言", value=c["reframe"])

    # 4) 今日の一歩（価値タグとセット）
    st.caption("“今日の一歩”（1〜3分）")
    cols3 = st.columns(4)
    for i,act in enumerate(ACTIONS):
        with cols3[i%4]:
            if st.button(act, key=f"ac_{i}"): c["act"]=act
    c["act"]   = st.text_input("内容（編集可）", value=c["act"], placeholder="例：プリント半分だけ")
    c["value"] = st.selectbox("価値タグ", VALUES, index=VALUES.index(c["value"]) if c["value"] in VALUES else 0)

    # 5) 朝1分（睡眠だけ簡略入力）
    st.caption("睡眠時間（時間）※任意")
    c["sleep_h"] = st.number_input("", 0.0, 24.0, float(c["sleep_h"]), 0.5, label_visibility="collapsed")

    # 6) メモ（任意）
    c["note"] = st.text_area("メモ（任意）", value=c["note"], height=70, placeholder="書かなくてもOK")

    # 保存
    col_s, col_reset = st.columns(2)
    with col_s:
        if st.button("💾 保存して完了", type="primary"):
            append_csv(CBT_CSV, {  # 互換のためCBTにも残す
                "ts": now_ts(), "emotions": json.dumps({"main":c["emo"]}, ensure_ascii=False),
                "triggers": c["trigger"], "reappraise": c["reframe"],
                "action": c["act"], "value": c["value"]
            })
            append_csv(MIX_CSV, {
                "ts": now_ts(), "emo": c["emo"], "trigger": c["trigger"], "reframe": c["reframe"],
                "act": c["act"], "value": c["value"], "sleep_h": c["sleep_h"], "note": c["note"]
            })
            st.session_state.mix = {"emo":"","trigger":"","reframe":"","act":"","value":"","note":"", "sleep_h":6.5}
            st.success("保存しました。今日はここでおしまいでもOK。")
    with col_reset:
        if st.button("🧼 入力を初期化"):
            st.session_state.mix = {"emo":"","trigger":"","reframe":"","act":"","value":"","note":"", "sleep_h":6.5}
            st.info("初期化しました。")

# ---------------- Study ----------------
SUBJ_DEFAULT = ["国語","数学","英語","理科","社会","小論","過去問","面接","実技"]
MOODS = ["😌集中","😕難航","😫しんどい"]

def view_study():
    st.subheader("📚 Study（配分×手触り）")
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

# ---------------- 今日一日を振り返る（Me） ----------------
def view_me():
    st.subheader("🧭 今日一日を振り返る")
    st.caption("“点数化しない”ふりかえり。ざっくり推移を見る（睡眠・メモ等）。")
    mix = load_csv(MIX_CSV)
    if mix.empty:
        st.caption("まだ記録がありません。")
    else:
        st.dataframe(mix.tail(50), use_container_width=True, hide_index=True)

# ---------------- 記録・エクスポート ----------------
def view_export():
    st.subheader("⬇️ 記録・エクスポート（CSV）／設定")
    def dl(df: pd.DataFrame, label: str, name: str):
        if df.empty: st.caption(f"{label}：まだデータがありません"); return
        st.download_button(f"⬇️ {label}", df.to_csv(index=False).encode("utf-8-sig"), file_name=name, mime="text/csv")
    dl(load_csv(CBT_CSV),   "2分ノート（互換フォーマット）", "cbt_entries.csv")
    dl(load_csv(BREATH_CSV),"呼吸", "breath_sessions.csv")
    dl(load_csv(MIX_CSV),   "心を整える（統合）", "mix_note.csv")
    dl(load_csv(STUDY_CSV), "Study", "study_blocks.csv")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    danger = st.checkbox("⚠️ すべての保存データ（CSV）を削除することに同意します")
    if st.button("🗑️ すべて削除（取り消し不可）", disabled=not danger):
        for p in [CBT_CSV,BREATH_CSV,MIX_CSV,STUDY_CSV,ME_CSV]:
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
elif v=="ME":    view_me()
else:            view_export()

# ---------------- Footer ----------------
st.markdown("""
<div style="text-align:center; color:var(--muted); margin-top:12px;">
  <small>※ 個人名や連絡先は記入しないでください。<br>
  とてもつらい場合は、お住まいの地域の相談窓口や専門機関のご利用もご検討ください。</small>
</div>
""", unsafe_allow_html=True)
