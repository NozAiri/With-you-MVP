# app.py — Sora Hybrid MVP v3（ログインなし / 日本語UI改善 / 呼吸アニメ強化 / CBT濃いめ）
# 使い方:
#   pip install streamlit
#   streamlit run app.py

import streamlit as st
import sqlite3, json, os, uuid, time
from datetime import datetime, timezone, timedelta
import pandas as pd

# ============== 基本設定 ==============
st.set_page_config(page_title="Sora Hybrid MVP", page_icon="🌙", layout="centered")

# ---- CSS（余白最小化＋呼吸アニメ：星＋波）----
st.markdown("""
<style>
.block-container { padding-top: 0.8rem; padding-bottom: 1.2rem; }
h3, h4 { margin: .6rem 0 .4rem 0; }
button[kind="primary"], button[kind="secondary"] { margin: .25rem .25rem; }
.stTextInput, .stTextArea, .stNumberInput, .stSlider, .stSelectbox { margin: .2rem 0; }

/* 星アニメ */
.breathing-star { width: 140px; height: 140px; margin: 10px auto 6px auto; position: relative;
  filter: drop-shadow(0 0 10px rgba(150,150,255,.35)); }
.star-shape {
  width: 100%; height: 100%;
  background: radial-gradient(circle at 50% 40%, #dfe7ff 0%, #a8b7ff 60%, #6f7cff 100%);
  -webkit-clip-path: polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%);
  clip-path: polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%);
  animation: breathe var(--cycle,12s) ease-in-out infinite;
  transform-origin: center;
}
@keyframes breathe {
  0%   { transform: scale(0.82); }
  25%  { transform: scale(1.05); }  /* 吸う */
  35%  { transform: scale(1.05); }  /* 止める */
  70%  { transform: scale(0.80); }  /* 吐く */
  80%  { transform: scale(0.80); }  /* 止める */
  100% { transform: scale(0.82); }
}

/* 波アニメ */
.wave-wrap { width: 260px; height: 70px; margin: 8px auto 0 auto; overflow: hidden;
  border-radius: 10px; position: relative; background: linear-gradient(180deg,#0f172a,#101a30);
  box-shadow: inset 0 0 20px rgba(80,120,255,.25); }
.wave {
  position: absolute; inset: 0;
  background:
    radial-gradient(circle at 10% 50%, rgba(255,255,255,.15) 2px, transparent 3px) -20px 0/40px 40px repeat-x,
    linear-gradient(90deg, rgba(150,180,255,.25), rgba(90,120,255,.15), rgba(150,180,255,.25));
  animation: waveMove 4s linear infinite; opacity: .9;
}
@keyframes waveMove {
  0% { background-position: 0 0, 0 0; }
  100% { background-position: 260px 0, 260px 0; }
}

.phase { text-align:center; font-weight:600; margin-top:2px; }
.badge { display:inline-block; padding:.1rem .5rem; border-radius:999px; background:#eef2ff; color:#3b47a1; font-size:.85rem; }
.small { color:#64748b; font-size:.85rem; }
.dataframe tbody tr th, .dataframe tbody tr td { padding: .35rem .5rem; }
</style>
""", unsafe_allow_html=True)

# ============== DB ==============
DB = os.path.join(os.getcwd(), "sora_hybrid_v3.db")
def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anon_id TEXT NOT NULL,
            ts TEXT NOT NULL,
            path TEXT NOT NULL,           -- 'breathing' or 'cbt'
            emotion TEXT,                 -- 悲しい/不安/もやもや/普通/うれしい
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
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
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
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id, ts, path, emotion, data_json FROM entries WHERE anon_id=? ORDER BY ts DESC LIMIT ?",
                (anon_id, limit))
    rows = cur.fetchall()
    conn.close()
    return rows

init_db()

# ============== 匿名セッション ==============
if "anon_id" not in st.session_state:
    st.session_state.anon_id = str(uuid.uuid4())[:8]

# ============== 画面 ==============
st.markdown("## 🌙 Sora — ハイブリッド（呼吸 × CBT）")

tab_use, tab_hist, tab_about = st.tabs(["体験", "履歴", "使い方 / 検証"])

with tab_use:
    # 1) 感情選択（漢字かな混じり）
    st.markdown("### ① 今の気持ちを選ぶ")
    emotions = ["悲しい", "不安", "もやもや", "普通", "うれしい"]
    cols = st.columns(len(emotions))
    if "emotion" not in st.session_state:
        st.session_state.emotion = None
    for i, label in enumerate(emotions):
        with cols[i]:
            if st.button(label, use_container_width=True):
                st.session_state.emotion = label
                st.toast(f"気持ち：{label}", icon="✅")
    if not st.session_state.emotion:
        st.info("↑ まず“今の気持ち”を選んでね。")
        st.stop()
    st.success(f"選択中：{st.session_state.emotion}")

    # 2) モード選択
    st.markdown("### ② やってみる内容を選ぶ")
    path_choice = st.radio(
        "※あとで別のモードも試せます",
        ["呼吸で落ち着く（約1分）", "考えを整理（CBT 3分）"],
        horizontal=False
    )
    path = "breathing" if "呼吸" in path_choice else "cbt"
    st.divider()

    # ---------- 呼吸モード ----------
    if path == "breathing":
        st.markdown("### ③ 呼吸で落ち着く")
        st.caption("吸う→止める→吐く→止める の1サイクル。デフォルトは 4-2-4-2。回数は少なめでOK。")

        # プリセット切り替え
        preset = st.selectbox("サイクル（秒）", ["4-2-4-2（標準）", "3-1-5-1（軽め）", "4-4-4-4（均等）"], index=0)
        if "3-1-5-1" in preset:
            inhale, hold1, exhale, hold2 = 3, 1, 5, 1
        elif "4-4-4-4" in preset:
            inhale, hold1, exhale, hold2 = 4, 4, 4, 4
        else:
            inhale, hold1, exhale, hold2 = 4, 2, 4, 2

        sets = st.slider("回数（しんどければ2回でOK）", min_value=1, max_value=4, value=2, step=1)

        cycle_seconds = inhale + hold1 + exhale + hold2
        st.markdown(f"""
        <div style="--cycle:{cycle_seconds}s">
          <div class="breathing-star"><div class="star-shape"></div></div>
        </div>
        <div class="wave-wrap"><div class="wave"></div></div>
        """, unsafe_allow_html=True)

        colA, colB = st.columns(2)
        with colA:
            start = st.button("▶ はじめる", use_container_width=True)
        with colB:
            reset = st.button("⟲ リセット", use_container_width=True)

        phase_box = st.empty()
        prog = st.progress(0)
        if reset:
            st.experimental_rerun()

        if start:
            total_seconds = sets * cycle_seconds
            elapsed = 0
            for s in range(sets):
                # 吸う
                for t in range(inhale, 0, -1):
                    phase_box.markdown(f"<div class='phase'><span class='badge'>吸う</span> 残り {t} 秒</div>", unsafe_allow_html=True)
                    elapsed += 1; prog.progress(min(int(elapsed/total_seconds*100), 100)); time.sleep(1)
                # 止める1
                for t in range(hold1, 0, -1):
                    phase_box.markdown(f"<div class='phase'><span class='badge'>止める</span> 残り {t} 秒</div>", unsafe_allow_html=True)
                    elapsed += 1; prog.progress(min(int(elapsed/total_seconds*100), 100)); time.sleep(1)
                # 吐く
                for t in range(exhale, 0, -1):
                    phase_box.markdown(f"<div class='phase'><span class='badge'>吐く</span> 残り {t} 秒</div>", unsafe_allow_html=True)
                    elapsed += 1; prog.progress(min(int(elapsed/total_seconds*100), 100)); time.sleep(1)
                # 止める2
                for t in range(hold2, 0, -1):
                    phase_box.markdown(f"<div class='phase'><span class='badge'>止める</span> 残り {t} 秒</div>", unsafe_allow_html=True)
                    elapsed += 1; prog.progress(min(int(elapsed/total_seconds*100), 100)); time.sleep(1)

            phase_box.markdown("<div class='phase'>おつかれさま。少し楽になった？</div>", unsafe_allow_html=True)

        st.markdown("#### ④ メモ（任意で保存）")
        note = st.text_input("今の状態（短くでOK）", placeholder="例：落ち着いた／まだ緊張 など")
        if st.button("保存する", type="primary"):
            rowid = save_entry(st.session_state.anon_id, "breathing", st.session_state.emotion,
                               {"note": note, "sets": sets, "pattern": f"{inhale}-{hold1}-{exhale}-{hold2}"})
            st.success("保存しました（履歴タブで見られます）")

    # ---------- CBTモード ----------
    else:
        st.markdown("### ③ 考えを整理（3分）")
        st.caption("“前後スコア → 状況 → 自動思考 → 認知のクセ → 別の見方 → 今日の一歩”")

        distortions = [
            "全か無か思考", "一般化のしすぎ", "心の読みすぎ", "先読みの誤り",
            "レッテル貼り", "べき思考", "拡大・過小評価", "感情的決めつけ", "個人化", "特になし"
        ]

        with st.form("cbt_form"):
            col0a, col0b = st.columns(2)
            with col0a:
                pre = st.slider("前の気分（0=最悪〜10=落ち着いている）", 0, 10, 3)
            with col0b:
                ask_post = st.checkbox("保存後に“後スコア”も記録する", value=True)

            col1, col2 = st.columns(2)
            with col1:
                situation = st.text_area("1) 事実（状況）", height=80, placeholder="例：テストが近い／返信が来ない など")
                thought   = st.text_area("2) 自動思考（浮かんだ言葉）", height=80, placeholder="例：絶対失敗する／嫌われたかも")
            with col2:
                dist = st.selectbox("3) 認知のクセ（該当あれば）", options=distortions, index=len(distortions)-1)
                reframe  = st.text_area("4) 別の見方（やさしい仮説）", height=80, placeholder="例：まず15分だけ進める／相手も忙しいだけかも")
            step = st.text_input("5) 今日の一歩（5〜15分でできること）", placeholder="例：タイマー10分で1ページ")

            submitted = st.form_submit_button("保存する", type="primary")

        if submitted:
            rowid = save_entry(
                st.session_state.anon_id, "cbt", st.session_state.emotion,
                {"pre": pre,
                 "situation": situation.strip(),
                 "thought": thought.strip(),
                 "distortion": dist,
                 "reframe": reframe.strip(),
                 "step": step.strip()}
            )
            st.success("保存しました（履歴タブで見られます）")
            if ask_post:
                st.markdown("#### 後スコア（やってみた後でもOK）")
                post = st.slider("後の気分（0〜10）", 0, 10, max(0, min(10, pre)))
                if st.button("後スコアを追記"):
                    update_entry_json(rowid, {"post": post})
                    st.success("追記しました（履歴に反映）")

with tab_hist:
    st.markdown("### 履歴")
    rows = load_history(st.session_state.anon_id, limit=300)
    if not rows:
        st.info("まだ記録はありません。となりのタブで体験してみてね。")
    else:
        recs = []
        for _id, ts, path, emo, data_json in rows:
            try:
                data = json.loads(data_json) if data_json else {}
            except Exception:
                data = {}
            if path == "breathing":
                summary = f"呼吸 {data.get('pattern','')}"
                if "sets" in data: summary += f" × {data['sets']}回"
                if data.get("note"): summary += f"｜{data['note']}"
            else:
                bits = []
                if "pre" in data: bits.append(f"前:{data['pre']}")
                if data.get("situation"): bits.append("状況:"+data["situation"])
                if data.get("thought"): bits.append("自動:"+data["thought"])
                if data.get("distortion") and data["distortion"]!="特になし": bits.append("クセ:"+data["distortion"])
                if data.get("reframe"): bits.append("別見:"+data["reframe"])
                if data.get("step"): bits.append("一歩:"+data["step"])
                if "post" in data: bits.append(f"後:{data['post']}")
                summary = "｜".join(bits)[:160]
            recs.append({
                "日時(JST)": ts,
                "モード": "呼吸" if path=="breathing" else "CBT",
                "気持ち": emo or "",
                "要約": summary
            })
        df = pd.DataFrame(recs)
        st.dataframe(df, use_container_width=True, hide_index=True)
        if st.button("CSVとして保存（/sora_history.csv）"):
            csv_path = os.path.join(os.getcwd(), "sora_history.csv")
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            st.success("保存しました: sora_history.csv")

with tab_about:
    st.markdown("### 使い方 / 検証ポイント")
    st.write("- **ログインなし**の匿名MVP（ローカルSQLite保存）")
    st.write("- **呼吸**：星の拡縮＋波の動きでリズムを視覚化。プリセット（4-2-4-2 / 3-1-5-1 / 4-4-4-4）と回数を選べる")
    st.write("- **CBT**：前後スコア・認知のクセ・“一歩”で、短時間の効果と行動化を記録")
    st.markdown("#### 検証で見る指標（例）")
    st.write("1) 前後スコア差の平均 / 体験完了率  2) CBT入力の各項目の記入率  3) 一歩の実行確認（次回改善）")
