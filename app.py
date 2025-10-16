# app.py — Sora（シンプル版：考えの整理 + 今日の一歩 + 呼吸）
# 目的：
#  - はじめてでも迷わず「落ち着く → 考えを整える → 今日の一歩」へ進める
#  - 入力は最小限：出来事 / 浮かんだ考え / 別の見方 + 今日の一歩（所要時間つき）
#  - CSV保存（失敗時もメモリ保持＆ダウンロード可能）
#  - 敬語・専門用語なし、落ち着いたUI

from datetime import datetime, date
from pathlib import Path
import pandas as pd
import streamlit as st
import uuid, json, time

# ---------------- 基本設定 ----------------
st.set_page_config(page_title="Sora — シンプルノート", page_icon="🌙", layout="centered")

# ---------------- 見た目 ----------------
st.markdown("""
<style>
:root{ --text:#2a2731; --muted:#6f7180; --glass:rgba(255,255,255,.94); --brd:rgba(185,170,255,.28);
       --grad-a:#ffa16d; --grad-b:#ff77a3; }
.stApp{ background:linear-gradient(180deg,#fffefd 0%,#fff8fb 28%,#f7f3ff 58%,#f2fbff 100%); }
.block-container{ max-width:900px; padding-top:1rem; padding-bottom:1.6rem }
h2,h3{ color:var(--text); letter-spacing:.2px }
p,label,.stMarkdown{ color:var(--text); font-size:1.05rem }
.small{ color:var(--muted); font-size:.9rem }
.card{ background:var(--glass); border:1px solid var(--brd); border-radius:18px; padding:16px; margin-bottom:14px;
       box-shadow:0 14px 32px rgba(80,70,120,.14); backdrop-filter:blur(6px); }
.hr{ height:1px; background:linear-gradient(to right,transparent,#c7b8ff,transparent); margin:12px 0 10px }
.stButton>button,.stDownloadButton>button{
  width:100%; padding:12px 14px; border-radius:999px; border:1px solid #eadfff;
  background:linear-gradient(180deg,var(--grad-a),var(--grad-b)); color:#fff; font-weight:900; font-size:1.02rem;
  box-shadow:0 12px 26px rgba(255,145,175,.22);
}
.stButton>button:hover{ filter:brightness(.98) }
.phase-pill{ display:inline-block; padding:.2rem .75rem; border-radius:999px;
  background:rgba(125,116,255,.12); color:#5d55ff; border:1px solid rgba(125,116,255,.35); font-weight:700; }
.count-box{ font-size:40px; font-weight:900; text-align:center; color:#2f2a3b; padding:6px 0 2px; }
.pill{ display:inline-block; padding:.35rem .75rem; border-radius:999px; border:1px solid #e6e0ff;
       background:#fff; font-weight:700; }
.tip-grid{ display:flex; flex-wrap:wrap; gap:8px; margin:6px 0 4px }
.tip-grid .stButton>button{ background:#fff; color:#2a2731; border:1px solid #eadfff;
  box-shadow:none; border-radius:999px; padding:8px 12px; font-weight:800 }
.tile-grid{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }
.tile .stButton>button{ min-height:120px; border-radius:18px; text-align:left; padding:16px; font-weight:900;
  background:linear-gradient(160deg,#ffd7b6,#fff2e4); color:#2a2731; border:none; box-shadow:0 14px 28px rgba(60,45,90,.12) }
.tile.alt .stButton>button{ background:linear-gradient(160deg,#ffd1e6,#fff0f8) }
@media (max-width:640px){ .tile-grid{ grid-template-columns:1fr } }
</style>
""", unsafe_allow_html=True)

# ---------------- 保存（CSV + メモリ） ----------------
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
CBT_CSV = DATA_DIR / "simple_entries.csv"
BREATH_CSV = DATA_DIR / "breathing_entries.csv"

if "mem" not in st.session_state:
    st.session_state.mem = {"entries": [], "breath": [], "actions": {}}
if "view" not in st.session_state:
    st.session_state.view = "HOME"

def _load_csv(p: Path) -> pd.DataFrame:
    if p.exists():
        try: return pd.read_csv(p)
        except Exception: return pd.DataFrame()
    return pd.DataFrame()

def _append_csv_safe(p: Path, row: dict) -> bool:
    try:
        df = _load_csv(p)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        df.to_csv(p, index=False)
        return True
    except Exception:
        return False

# ---------- 便利 ----------
def now_ts(): return datetime.now().isoformat(timespec="seconds")

def section(title: str, sub: str | None = None):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader(title)
    if sub: st.caption(sub)

def end_section(): st.markdown('</div>', unsafe_allow_html=True)

# ---------------- ホーム ----------------
def view_home():
    st.markdown("<h2>🌙 Sora — シンプルノート</h2>", unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("最短2分。いまの出来事を短く書き、別の見方を1つ置き、今日の一歩を決めます。")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="tile-grid">', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="tile">', unsafe_allow_html=True)
        if st.button("📓 考えを整える（2分）", use_container_width=True): st.session_state.view = "NOTE"
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="tile alt">', unsafe_allow_html=True)
        if st.button("🌬 呼吸で落ち着く（1分）", use_container_width=True): st.session_state.view = "BREATH"
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 直近の未実行アクション
    pending = [e for e in st.session_state.mem["entries"] if (e.get("action_text") and not e.get("action_done"))]
    if pending:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 今日の一歩（未実行）")
        for e in pending[:5]:
            st.write(f"・{e['action_text']} 〔目安{int(e.get('action_minutes',5))}分〕")
            if st.button("完了しました", key=f"done_{e['id']}"):
                e["action_done"] = True
                e["action_done_ts"] = now_ts()
                st.success("お疲れさまでした。")
        st.markdown('</div>', unsafe_allow_html=True)

    # 履歴
    if st.session_state.mem["entries"]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 最近の記録")
        for e in list(reversed(st.session_state.mem["entries"]))[:3]:
            st.markdown(f"**🕒 {e['ts']}** — {e.get('situation','')[:40]}")
            if e.get("action_text"):
                tag = "済" if e.get("action_done") else "未"
                st.caption(f"今日の一歩：{e['action_text']}（{tag}）")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    if st.button("📚 記録を見る / エクスポート", use_container_width=True): st.session_state.view = "HISTORY"
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- 呼吸 ----------------
def view_breath():
    st.markdown("<h2>🌬 呼吸で落ち着く</h2>", unsafe_allow_html=True)
    section("カウントに合わせて、ゆっくり。", "1サイクル＝吸う → 止める → 吐く → 止める")
    preset = st.selectbox("サイクル（秒）", ["4-2-4-2（標準）", "3-1-5-1（軽め）", "4-4-4-4（均等）"], index=0)
    if "3-1-5-1" in preset: inhale, hold1, exhale, hold2 = 3,1,5,1
    elif "4-4-4-4" in preset: inhale, hold1, exhale, hold2 = 4,4,4,4
    else: inhale, hold1, exhale, hold2 = 4,2,4,2
    sets = st.slider("回数（推奨：2回）", 1, 4, 2)

    colA, colB = st.columns(2)
    with colA: start = st.button("開始", use_container_width=True)
    with colB: reset = st.button("リセット", use_container_width=True)

    phase_box = st.empty(); count_box = st.empty(); prog = st.progress(0)
    if reset: st.experimental_rerun()
    if start:
        total = sets * (inhale + hold1 + exhale + hold2); elapsed = 0
        phases = [("吸気",inhale),("停止",hold1),("呼気",exhale),("停止",hold2)]
        for _ in range(sets):
            for name, sec in phases:
                if sec<=0: continue
                phase_box.markdown(f"<span class='phase-pill'>{name}</span>", unsafe_allow_html=True)
                for t in range(sec,0,-1):
                    count_box.markdown(f"<div class='count-box'>{t}</div>", unsafe_allow_html=True)
                    elapsed += 1; prog.progress(min(int(elapsed/total*100),100)); time.sleep(1)
        phase_box.markdown("<span class='phase-pill'>完了</span>", unsafe_allow_html=True)
        count_box.markdown("<div class='count-box'>お疲れさまでした。</div>", unsafe_allow_html=True)
    end_section()

    section("メモ（任意）")
    note = st.text_input("いまの状態（短文で結構です）", placeholder="例：少し落ち着いた など")
    if st.button("保存する", type="primary"):
        row = {"id":"breath-"+now_ts(), "ts":now_ts(), "pattern":f"{inhale}-{hold1}-{exhale}-{hold2}", "sets":sets, "note":note}
        ok = _append_csv_safe(BREATH_CSV, row)
        st.session_state.mem["breath"].append(row)
        st.success("保存いたしました。" if ok else "一時的に保存しました（CSVに書き込めませんでした）。")
    end_section()

    if st.button("← ホームへ戻る"): st.session_state.view = "HOME"

# ---------------- シンプルノート（CBTの簡素版） ----------------
def view_note():
    st.markdown("<h2>📓 考えを整える（2分）</h2>", unsafe_allow_html=True)

    # 0) いまの気分（数値だけ）
    section("いまの気分")
    mood_before = st.slider("0=とてもつらい / 10=落ち着いている", 0, 10, 3)
    end_section()

    # 1) 最小3項目
    section("短く3つだけ")
    situation = st.text_area("① いまの出来事", height=80, placeholder="例：返信がない／テストが近い など")
    thought   = st.text_area("② そのとき浮かんだ考え", height=80, placeholder="例：嫌われたかも／間に合わない など")
    st.caption("③ 別の見方（候補はタップで挿入できます）")
    tip_cols = st.columns(3)
    tips = ["可能性は一つじゃない。","相手が忙しいだけかもしれない。","まず5分だけ手をつける。"]
    for i,t in enumerate(tips):
        with tip_cols[i%3]:
            if st.button(t, key=f"tip_{i}"):
                cur = st.session_state.get("alt_text","")
                st.session_state["alt_text"] = (cur + (" " if cur else "") + t).strip()
    alt = st.text_area("③ 別の見方（1行でもOK）", key="alt_text", height=80, placeholder="例：移動中かも／前も夜に返ってきた など")
    end_section()

    # 2) 今日の一歩（行動活性化）
    section("今日の一歩（5〜15分で終わること）", "実行しやすいものを1つだけ。")
    presets = ["タイマー5分で1ページだけ進める","LINEを下書きだけ作る","水を一杯飲む","外に出て3分歩く","机の上を30秒だけ片づける"]
    st.markdown("<div class='tip-grid'>", unsafe_allow_html=True)
    for i, p in enumerate(presets):
        if st.button(p, key=f"act_{i}"): st.session_state["act_text"] = p
    st.markdown("</div>", unsafe_allow_html=True)
    action_text = st.text_input("内容（編集可）", key="act_text", placeholder="例：タイマー10分でプリント1枚だけ解く")
    minutes = st.slider("目安の時間（分）", 5, 15, 10, step=5)
    end_section()

    # 3) 保存 → 後の気分（任意）
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 保存して完了"):
            entry_id = str(uuid.uuid4())[:8]
            row = {
                "id": entry_id, "ts": now_ts(),
                "mood_before": mood_before,
                "situation": situation.strip(),
                "thought": thought.strip(),
                "alt": alt.strip(),
                "action_text": action_text.strip(),
                "action_minutes": minutes,
                "action_done": False,
                "action_done_ts": "",
                "mood_after": ""
            }
            ok = _append_csv_safe(CBT_CSV, row)
            st.session_state.mem["entries"].append(row)
            st.success("保存いたしました。" if ok else "一時的に保存しました（CSVに書き込めませんでした）。")

    with c2:
        if st.button("🧼 入力欄を初期化"):
            for k in ["alt_text","act_text"]: st.session_state[k] = ""
            st.info("入力欄を初期化いたしました。")

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    if st.button("← ホームへ戻る"): st.session_state.view = "HOME"

# ---------------- 記録 / エクスポート ----------------
def view_history():
    st.markdown("<h2>📚 記録とエクスポート</h2>", unsafe_allow_html=True)

    # 1) ノート
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 考えの記録")
    df_file = _load_csv(CBT_CSV)
    df_mem  = pd.DataFrame(st.session_state.mem["entries"])
    df = pd.concat([df_file, df_mem], ignore_index=True)
    if df.empty:
        st.caption("まだ記録がございません。")
    else:
        if "ts" in df.columns:
            try: df["ts"] = pd.to_datetime(df["ts"]); df = df.sort_values("ts", ascending=False)
            except Exception: pass
        for _, r in df.head(30).iterrows():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"**🕒 {r.get('ts','')}**")
            st.markdown(f"**出来事**：{r.get('situation','')}")
            st.markdown(f"**考え**：{r.get('thought','')}")
            if r.get("alt"): st.markdown(f"**別の見方**：{r.get('alt','')}")
            if r.get("action_text"):
                done = r.get("action_done", False)
                tag = "済" if done else "未"
                st.markdown(f"<span class='pill'>今日の一歩（{tag}）</span> {r.get('action_text','')} ／ 目安{int(r.get('action_minutes',0))}分", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        # DL
        if not df.empty:
            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ 考えの記録（CSV）をダウンロード", data=csv, file_name="simple_entries.csv", mime="text/csv")
    st.markdown('</div>', unsafe_allow_html=True)

    # 2) 呼吸
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 呼吸の記録")
    b_file = _load_csv(BREATH_CSV)
    b_mem  = pd.DataFrame(st.session_state.mem["breath"])
    bd = pd.concat([b_file, b_mem], ignore_index=True)
    if bd.empty:
        st.caption("まだ記録がございません。")
    else:
        if "ts" in bd.columns:
            try: bd["ts"] = pd.to_datetime(bd["ts"]); bd = bd.sort_values("ts", ascending=False)
            except Exception: pass
        st.dataframe(bd.rename(columns={"ts":"日時","pattern":"サイクル","sets":"回数","note":"メモ"}),
                     use_container_width=True, hide_index=True)
        csv2 = bd.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ 呼吸（CSV）をダウンロード", data=csv2, file_name="breathing_entries.csv", mime="text/csv")
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("← ホームへ戻る"): st.session_state.view = "HOME"

# ---------------- ルーティング ----------------
if st.session_state.view == "HOME":   view_home()
elif st.session_state.view == "BREATH": view_breath()
elif st.session_state.view == "NOTE":  view_note()
else:                                  view_history()
