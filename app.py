# app.py — Sora Hybrid MVP v4（ログイン不要 / 上品UI / 呼吸×CBT / SQLite保存）
# 目的：
#  - 3分以内で「落ち着き→認知整理→小さな行動」に接続する体験を提供します
#  - 前後スコア・認知の偏り・行動計画を記録し、履歴で可視化します
#
# 使い方：
#   1) pip install streamlit
#   2) streamlit run app.py

import streamlit as st
import sqlite3, json, os, uuid, time
from datetime import datetime, timezone, timedelta
import pandas as pd

# ================== 基本設定 ==================
st.set_page_config(page_title="Sora Hybrid MVP", page_icon="🌙", layout="centered")

# ------------------ スタイル -------------------
st.markdown("""
<style>
/* ベース余白とタイポ */
:root {
  --brand:#334155;
  --accent:#3b82f6;
  --muted:#64748b;
  --bg:#0b1220;
  --card:#0f172a;
  --card2:#111827;
  --ring:rgba(59,130,246,.25);
}
html, body { background: radial-gradient(1200px 600px at 20% -10%, #0f172a, #0b1220); }
.block-container { padding-top: 1.2rem; padding-bottom: 1.6rem; }
h2,h3 { color:#e5e7eb; letter-spacing:.2px; }
h4 { color:#cbd5e1; margin:.6rem 0 .35rem 0; }
p, label, .small { color:#cbd5e1; }
.small { font-size:.9rem; color:#94a3b8; }
hr, .stDivider { opacity:.08; }

/* カード */
.card {
  background: linear-gradient(180deg, var(--card), var(--card2));
  border: 1px solid rgba(148,163,184,.12);
  border-radius: 16px;
  padding: 16px 18px;
  box-shadow: 0 6px 24px rgba(0,0,0,.25), inset 0 1px 0 rgba(255,255,255,.02);
  margin-bottom: 14px;
}

/* ボタン */
button[kind="primary"]{
  border-radius:12px;
  border:1px solid rgba(59,130,246,.35);
  box-shadow: 0 6px 18px var(--ring);
}
button[kind="secondary"]{ border-radius:12px; }

/* 入力余白を詰める */
.stTextArea, .stTextInput, .stNumberInput, .stSelectbox, .stSlider, .stRadio, .stButton {
  margin:.25rem 0 .25rem 0;
}

/* カウントダウン表示 */
.count-box{
  font-size: 42px;
  font-weight: 700;
  letter-spacing: .5px;
  text-align:center;
  color:#e2e8f0;
  padding: 8px 0 2px 0;
}
.phase-pill{
  display:inline-block; padding:.2rem .75rem; border-radius:999px;
  background: rgba(59,130,246,.12); color:#bfdbfe; border:1px solid rgba(59,130,246,.25);
  margin-bottom:6px; font-weight:600;
}

/* データフレームの視認性 */
.dataframe tbody tr th, .dataframe tbody tr td { padding: .40rem .55rem; }
</style>
""", unsafe_allow_html=True)

# ================== DB（SQLite） ==================
DB = os.path.join(os.getcwd(), "sora_hybrid_v4.db")

def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anon_id TEXT NOT NULL,
            ts TEXT NOT NULL,
            path TEXT NOT NULL,         -- 'breathing' or 'cbt'
            emotion TEXT,               -- 悲しい/不安/混乱/平静/嬉しい
            data_json TEXT
        );
    """)
    conn.commit(); conn.close()

def save_entry(anon_id: str, path: str, emotion: str, data: dict) -> int:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO entries(anon_id, ts, path, emotion, data_json) VALUES (?,?,?,?,?)",
        (anon_id,
         datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S"),
         path, emotion, json.dumps(data, ensure_ascii=False))
    )
    rowid = cur.lastrowid
    conn.commit(); conn.close()
    return rowid

def update_entry_json(rowid: int, update_dict: dict):
    conn = sqlite3.connect(DB); cur = conn.cursor()
    cur.execute("SELECT data_json FROM entries WHERE id=?", (rowid,))
    row = cur.fetchone()
    if row:
        try:
            data = json.loads(row[0]) if row[0] else {}
        except Exception:
            data = {}
        data.update(update_dict)
        cur.execute("UPDATE entries SET data_json=? WHERE id=?", (json.dumps(data, ensure_ascii=False), rowid))
        conn.commit()
    conn.close()

def load_history(anon_id: str, limit=300):
    conn = sqlite3.connect(DB); cur = conn.cursor()
    cur.execute("SELECT id, ts, path, emotion, data_json FROM entries WHERE anon_id=? ORDER BY ts DESC LIMIT ?",
                (anon_id, limit))
    rows = cur.fetchall(); conn.close()
    return rows

init_db()

# ================== 匿名セッション ==================
if "anon_id" not in st.session_state:
    st.session_state.anon_id = str(uuid.uuid4())[:8]

# ================== 画面ヘッダー ==================
st.markdown("<h2>🌙 Sora — ハイブリッド（呼吸 × 認知行動療法）</h2>", unsafe_allow_html=True)
st.markdown("<p class='small'>短時間で「落ち着き → 認知の整理 → 小さな行動」に接続する体験をご提供します。</p>", unsafe_allow_html=True)

tab_use, tab_hist, tab_about = st.tabs(["体験", "履歴", "使い方 / 検証"])

# ================== 体験タブ ==================
with tab_use:
    # 1) 感情選択
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("#### ① 今の気持ちをお選びください")
    emotions = ["悲しい", "不安", "混乱", "平静", "嬉しい"]
    cols = st.columns(len(emotions))
    if "emotion" not in st.session_state:
        st.session_state.emotion = None
    for i, label in enumerate(emotions):
        with cols[i]:
            if st.button(label, use_container_width=True):
                st.session_state.emotion = label
                st.toast(f"選択：{label}", icon="✅")
    if not st.session_state.emotion:
        st.info("最初に“今の気持ち”をお選びください。")
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()
    else:
        st.success(f"選択中：{st.session_state.emotion}")
    st.markdown("</div>", unsafe_allow_html=True)

    # 2) モード選択
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("#### ② 進め方をお選びください")
    mode = st.radio(
        "後からもう一方も実施できます。",
        ["呼吸で落ち着く（約1分）", "認知行動療法で整理する（約3分）"],
        horizontal=False
    )
    path = "breathing" if "呼吸" in mode else "cbt"
    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # ---------- 呼吸 ----------
    if path == "breathing":
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("#### ③ 呼吸で落ち着く")
        st.caption("1サイクル＝吸気→停止→呼気→停止。必要回数のみで構いません。")

        preset = st.selectbox(
            "サイクル（秒）",
            ["4-2-4-2（標準）", "3-1-5-1（軽め）", "4-4-4-4（均等）"],
            index=0
        )
        if "3-1-5-1" in preset:
            inhale, hold1, exhale, hold2 = 3, 1, 5, 1
        elif "4-4-4-4" in preset:
            inhale, hold1, exhale, hold2 = 4, 4, 4, 4
        else:
            inhale, hold1, exhale, hold2 = 4, 2, 4, 2

        sets = st.slider("回数（推奨：2回）", min_value=1, max_value=4, value=2, step=1)
        st.markdown("<div class='small'>画面の指示に合わせて、無理のない範囲でお願いいたします。</div>", unsafe_allow_html=True)

        colA, colB = st.columns(2)
        with colA:
            start = st.button("開始", use_container_width=True)
        with colB:
            reset = st.button("リセット", use_container_width=True)

        phase_box = st.empty()
        count_box = st.empty()
        prog = st.progress(0)

        if reset:
            st.experimental_rerun()

        if start:
            total = sets * (inhale + hold1 + exhale + hold2)
            elapsed = 0

            def run_phase(name: str, seconds: int):
                nonlocal elapsed
                if seconds <= 0:
                    return
                phase_box.markdown(f"<div class='phase-pill'>{name}</div>", unsafe_allow_html=True)
                for t in range(seconds, 0, -1):
                    count_box.markdown(f"<div class='count-box'>{t}</div>", unsafe_allow_html=True)
                    elapsed += 1
                    prog.progress(min(int(elapsed / total * 100), 100))
                    time.sleep(1)

            for s in range(sets):
                run_phase("吸気", inhale)
                run_phase("停止", hold1)
                run_phase("呼気", exhale)
                run_phase("停止", hold2)

            phase_box.markdown("<div class='phase-pill'>完了</div>", unsafe_allow_html=True)
            count_box.markdown(f"<div class='count-box'>お疲れさまでした。</div>", unsafe_allow_html=True)

        st.markdown("##### ④ メモ（任意）")
        note = st.text_input("現在の状態（短文で結構です）", placeholder="例：落ち着いた／少し緊張が残る など")
        if st.button("保存する", type="primary"):
            save_entry(
                st.session_state.anon_id, "breathing", st.session_state.emotion,
                {"note": note, "sets": sets, "pattern": f"{inhale}-{hold1}-{exhale}-{hold2}"}
            )
            st.success("保存いたしました（「履歴」タブからご確認いただけます）。")
        st.markdown("</div>", unsafe_allow_html=True)

    # ---------- CBT ----------
    else:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("#### ③ 認知行動療法で整理する（約3分）")
        st.caption("「前後スコア → 事実 → 自動思考 → 認知の偏り → 別の見方 → 本日の行動」の順で短くご記入ください。")

        distortions = [
            "全か無か思考", "一般化のしすぎ", "心の読みすぎ", "先読みの誤り",
            "レッテル貼り", "べき思考", "拡大・過小評価", "感情的決めつけ",
            "個人化", "特になし"
        ]

        with st.form("cbt_form"):
            col0a, col0b = st.columns(2)
            with col0a:
                pre = st.slider("前の気分（0=非常に不調〜10=落ち着いている）", 0, 10, 3)
            with col0b:
                ask_post = st.checkbox("保存後に「後スコア」も記録する", value=True)

            col1, col2 = st.columns(2)
            with col1:
                situation = st.text_area("① 事実（状況）", height=90, placeholder="例：課題の期限が近い／返信がない など")
                thought   = st.text_area("② 自動思考（浮かんだ言葉）", height=90, placeholder="例：間に合わない／嫌われたかもしれない")
            with col2:
                dist = st.selectbox("③ 認知の偏り（該当するものがあれば）", options=distortions, index=len(distortions)-1)
                reframe  = st.text_area("④ 別の見方（やさしい仮説）", height=90, placeholder="例：まず10分だけ進める／相手が忙しい可能性")
            step = st.text_input("⑤ 本日の行動（5〜15分で終えられること）", placeholder="例：タイマー10分で1ページだけ進める")

            submitted = st.form_submit_button("保存する", type="primary")

        if submitted:
            rowid = save_entry(
                st.session_state.anon_id, "cbt", st.session_state.emotion,
                {
                    "pre": pre,
                    "situation": situation.strip(),
                    "thought": thought.strip(),
                    "distortion": dist,
                    "reframe": reframe.strip(),
                    "step": step.strip()
                }
            )
            st.success("保存いたしました（「履歴」タブからご確認いただけます）。")

            if ask_post:
                st.markdown("##### 後スコア（体験後にご記入ください）")
                post = st.slider("後の気分（0〜10）", 0, 10, max(0, min(10, pre)))
                if st.button("後スコアを追記する"):
                    update_entry_json(rowid, {"post": post})
                    st.success("追記いたしました。履歴に反映されています。")
        st.markdown("</div>", unsafe_allow_html=True)

# ================== 履歴タブ ==================
with tab_hist:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("#### 履歴")
    rows = load_history(st.session_state.anon_id, limit=300)
    if not rows:
        st.info("まだ記録がございません。まずは「体験」タブからご利用ください。")
    else:
        recs = []
        for _id, ts, path, emo, data_json in rows:
            try:
                data = json.loads(data_json) if data_json else {}
            except Exception:
                data = {}
            if path == "breathing":
                summary = f"呼吸 {data.get('pattern','')} × {data.get('sets','-')}回"
                if data.get("note"): summary += f"｜{data['note']}"
            else:
                bits = []
                if "pre" in data: bits.append(f"前:{data['pre']}")
                if data.get("situation"): bits.append("状況:"+data["situation"])
                if data.get("thought"): bits.append("自動:"+data["thought"])
                if data.get("distortion") and data["distortion"]!="特になし": bits.append("偏り:"+data["distortion"])
                if data.get("reframe"): bits.append("別見:"+data["reframe"])
                if data.get("step"): bits.append("行動:"+data["step"])
                if "post" in data: bits.append(f"後:{data['post']}")
                summary = "｜".join(bits)[:170]
            recs.append({
                "日時（JST）": ts,
                "モード": "呼吸" if path == "breathing" else "CBT",
                "気持ち": emo or "",
                "要約": summary
            })
        df = pd.DataFrame(recs)
        st.dataframe(df, use_container_width=True, hide_index=True)

        if st.button("CSVとして保存（/sora_history.csv）"):
            csv_path = os.path.join(os.getcwd(), "sora_history.csv")
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            st.success("保存いたしました：sora_history.csv")
    st.markdown("</div>", unsafe_allow_html=True)

# ================== 使い方 / 検証 ==================
with tab_about:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("#### 使い方 / 検証ポイント")
    st.write("- ログイン不要でご利用いただけます（ローカルSQLiteに匿名保存）。")
    st.write("- **呼吸**：カウントダウンと進捗バーで落ち着きやすい進行にしています。")
    st.write("- **認知行動療法（CBT）**：前後スコア・認知の偏り・行動計画を記録し、短時間の効果を把握します。")
    st.markdown("##### 検証で確認したい指標（例）")
    st.write("1) 前後スコア差の平均値　2) 体験完了率　3) “本日の行動”の実行確認（次回以降で追加可能）")
    st.markdown("</div>", unsafe_allow_html=True)
