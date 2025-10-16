# app.py — Sora Hybrid MVP v2
# 変更点:
# - ひらがな感情選択／ログインなし（匿名セッション）
# - CBTを濃く：前後スコア、認知のくせドロップダウン、行動計画
# - 呼吸: デフォ2セット（可変）、星と波のCSSアニメ
# 使い方:
#   pip install streamlit
#   streamlit run app.py

import streamlit as st
import sqlite3, json, os, uuid, time
from datetime import datetime, timezone, timedelta
import pandas as pd

# ===== 基本設定 =====
st.set_page_config(page_title="Sora Hybrid MVP", page_icon="🌙", layout="centered")

# スタイル（余白最小化＋アニメ）
st.markdown("""
<style>
.block-container { padding-top: 0.8rem; padding-bottom: 1.2rem; }

/* --- 見出し調整 --- */
h3, h4 { margin: .6rem 0 .4rem 0; }

/* --- ボタンの行間 --- */
button[kind="primary"], button[kind="secondary"] { margin: .25rem .25rem; }

/* --- 入力欄余白 --- */
.stTextInput, .stTextArea, .stNumberInput, .stSlider { margin: .2rem 0; }

/* --- 呼吸アニメ: 星 --- */
.breathing-star {
  width: 140px; height: 140px;
  margin: 10px auto 6px auto;
  position: relative;
  filter: drop-shadow(0 0 10px rgba(150,150,255,.35));
}
.star-shape {
  width: 100%; height: 100%;
  background: radial-gradient(circle at 50% 40%, #dfe7ff 0%, #a8b7ff 60%, #6f7cff 100%);
  -webkit-clip-path: polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%,
                             79% 91%, 50% 70%, 21% 91%, 32% 57%,
                             2% 35%, 39% 35%);
          clip-path: polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%,
                             79% 91%, 50% 70%, 21% 91%, 32% 57%,
                             2% 35%, 39% 35%);
  animation: breathe var(--cycle,12s) ease-in-out infinite;
  transform-origin: center;
}
@keyframes breathe {
  0%   { transform: scale(0.82); }
  25%  { transform: scale(1.05); }  /* 吸う(膨らむ) */
  35%  { transform: scale(1.05); }  /* 止める */
  70%  { transform: scale(0.80); }  /* 吐く(縮む) */
  80%  { transform: scale(0.80); }  /* 止める */
  100% { transform: scale(0.82); }
}

/* --- 呼吸アニメ: 波 --- */
.wave-wrap {
  width: 260px; height: 70px; margin: 8px auto 0 auto; overflow: hidden;
  border-radius: 10px; position: relative;
  background: linear-gradient(180deg,#0f172a,#101a30);
  box-shadow: inset 0 0 20px rgba(80,120,255,.25);
}
.wave {
  position: absolute; left: 0; right: 0; top: 0; bottom: 0;
  background:
    radial-gradient(circle at 10% 50%, rgba(255,255,255,.15) 2px, transparent 3px) -20px 0/40px 40px repeat-x,
    linear-gradient(90deg, rgba(150,180,255,.25), rgba(90,120,255,.15), rgba(150,180,255,.25));
  animation: waveMove 4s linear infinite;
  opacity: .9;
}
@keyframes waveMove {
  0% { background-position: 0 0, 0 0; }
  100% { background-position: 260px 0, 260px 0; }
}
.phase {
  text-align:center; font-weight:600; margin-top:2px;
}
.badge { display:inline-block; padding:.1rem .5rem; border-radius:999px; background:#eef2ff; color:#3b47a1; font-size:.85rem; }
.small { color:#64748b; font-size:.85rem; }

/* テーブルの余白軽減 */
.dataframe tbody tr th, .dataframe tbody tr td { padding: .35rem .5rem; }
</style>
""", unsafe_allow_html=True)

# ===== DB =====
DB = os.path.join(os.getcwd(), "sora_hybrid_v2.db")
def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anon_id TEXT NOT NULL,
            ts TEXT NOT NULL,
            path TEXT NOT NULL,           -- 'breathing' or 'cbt'
            emotion TEXT,                 -- かなしい/ふあん/もやもや/ふつう/うれしい
            data_json TEXT
        );
    """)
    conn.commit(); conn.close()
def save(anon_id, path, emotion, data):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO entries(anon_id, ts, path, emotion, data_json) VALUES (?,?,?,?,?)",
        (anon_id, datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S"),
         path, emotion, json.dumps(data, ensure_ascii=False))
    )
    conn.commit(); conn.close()
def load_history(anon_id, limit=200):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT ts, path, emotion, data_json FROM entries WHERE anon_id=? ORDER BY ts DESC LIMIT ?",
                (anon_id, limit))
    rows = cur.fetchall()
    conn.close()
    return rows
init_db()

# ===== 匿名セッションID =====
if "anon_id" not in st.session_state:
    st.session_state.anon_id = str(uuid.uuid4())[:8]

# ===== UI: ヘッダー =====
st.markdown("## 🌙 Sora — ハイブリッド（呼吸 × CBT）MVP")

tab_use, tab_hist, tab_about = st.tabs(["体験する", "履歴", "使い方 / 検証"])

with tab_use:
    # 1) 感情選択（ひらがな）
    st.markdown("### ① いまのきもち")
　　　　emotions ＝ ［”悲しい”,”不安”,”もやもや”,”普通”,”嬉しい”］    cols = st.columns(len(emotions))
    if "emotion" not in st.session_state: st.session_state.emotion = None
    for i, label in enumerate(emotions):
        with cols[i]:
            if st.button(label, use_container_width=True):
                st.session_state.emotion = label
                st.toast(f"気持ち：{label}", icon="✅")
    if not st.session_state.emotion:
        st.info("↑ まず“今の気持ち”を選んでね。")
        st.stop()
    st.success(f"選んだ気持ち：{st.session_state.emotion}")

    # 2) モード選択
    st.markdown("### ② 何をやってみる？")
    path_choice = st.radio(
        "※後で別の方も試せるよ",
        ["よぶきを整える（約1分）", "考えを整理（CBT 3分）"],
        horizontal=False
    )
    path = "breathing" if "よぶき" in path_choice else "cbt"
    st.divider()

    # 3-A) 呼吸モード（UI強化）
    if path == "breathing":
        st.markdown("### ③ よぶきを整える")
        st.caption("吸う4秒 → 止める2秒 → 吐く4秒 → 止める2秒（1サイクル12秒）")
        sets = st.slider("回数（しんどければ2回でOK）", min_value=1, max_value=4, value=2, step=1)

        # CSSアニメ（星＋波）— サイクル長をCSS変数で渡す
        cycle_seconds = 12
        st.markdown(f"""
        <div style="--cycle:{cycle_seconds}s">
          <div class="breathing-star"><div class="star-shape"></div></div>
        </div>
        <div class="wave-wrap"><div class="wave"></div></div>
        """, unsafe_allow_html=True)

        # 簡易フェーズガイド（テキストだけ同期）
        colA, colB = st.columns(2)
        with colA:
            start = st.button("▶ 始める", use_container_width=True)
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
                # 吸う4
                for t in range(4,0,-1):
                    phase_box.markdown(f"<div class='phase'><span class='badge'>吸う</span> 残り {t} 秒</div>", unsafe_allow_html=True)
                    elapsed += 1; prog.progress(min(int(elapsed/total_seconds*100), 100)); time.sleep(1)
                # 止2
                for t in range(2,0,-1):
                    phase_box.markdown(f"<div class='phase'><span class='badge'>止める</span> 残り {t} 秒</div>", unsafe_allow_html=True)
                    elapsed += 1; prog.progress(min(int(elapsed/total_seconds*100), 100)); time.sleep(1)
                # 吐4
                for t in range(4,0,-1):
                    phase_box.markdown(f"<div class='phase'><span class='badge'>吐く</span> 残り {t} 秒</div>", unsafe_allow_html=True)
                    elapsed += 1; prog.progress(min(int(elapsed/total_seconds*100), 100)); time.sleep(1)
                # 止2
                for t in range(2,0,-1):
                    phase_box.markdown(f"<div class='phase'><span class='badge'>止める</span> 残り {t} 秒</div>", unsafe_allow_html=True)
                    elapsed += 1; prog.progress(min(int(elapsed/total_seconds*100), 100)); time.sleep(1)

            phase_box.markdown("<div class='phase'>お疲れ様です。少し楽になりましたか？</div>", unsafe_allow_html=True)

        st.markdown("#### ④ 一言メモ（日記として保存・任意）")
        note = st.text_input("今の気持ち（短くでOK）", placeholder="例：ちょっと落ちついた／まだドキドキ など")
        if st.button("保存する", type="primary"):
            save(st.session_state.anon_id, "breathing", st.session_state.emotion,
                 {"note": note, "sets": sets, "pattern": "4-2-4-2"})
            st.success("保存しました（履歴タブで見られます）")

    # 3-B) CBTモード（濃い検証設計）
    else:
        st.markdown("### ③ 考えを整理（3分）")
        st.caption("“前後スコア → 状況 → 自動思考 → 認知のくせ → 別の見方 → 今日の一歩”")

        distortions = [
            "0/100の考え方", "一般化しすぎ", "心の読みすぎ", "先読みしすぎ",
            "ラベリング", "べき思考", "拡大/過小評価", "感情的決めつけ", "個人化/責任の取りすぎ", "とくになし"
        ]

        with st.form("cbt_form"):
            col0a, col0b = st.columns(2)
            with col0a:
                pre = st.slider("前の気分（0=最悪〜10=落ちついてる）", 0, 10, 3)
            with col0b:
                post_plan = st.checkbox("後で“最新のスコア”を記録する（保存後に表示）", value=True)

            col1, col2 = st.columns(2)
            with col1:
                situation = st.text_area("1) 状況", height=80, placeholder="例：テストが近い／LINEの返事がない など")
                thought   = st.text_area("2) 浮かんだ言葉", height=80, placeholder="例：絶対失敗する／嫌われたかも")
            with col2:
                dist = st.selectbox("3) 認知のくせ（あてはまるなら）", options=distortions, index=len(distortions)-1)
                reframe  = st.text_area("4) べつの見方（やさしい仮説）", height=80, placeholder="例：まず15分だけやれば前進／相手も忙しいだけかも")
            step = st.text_input("5) 今日の一歩（5〜15分でできること）", placeholder="例：タイマー10分で1ページだけやる")

            submitted = st.form_submit_button("保存する", type="primary")

        if submitted:
            payload = {
                "pre": pre,
                "situation": situation.strip(),
                "thought": thought.strip(),
                "distortion": dist,
                "reframe": reframe.strip(),
                "step": step.strip()
            }
            save(st.session_state.anon_id, "cbt", st.session_state.emotion, payload)
            st.success("保存しました（履歴タブで見られます）")
            if post_plan:
                # “あとスコア”の入力UI（同じ画面で追加入力）
                st.markdown("#### あとスコア（やってみた後でOK）")
                post = st.slider("今の気分（0〜10）", 0, 10, min(10, max(0, pre)))
                if st.button("今のスコアを追記"):
                    # 直近のCBTレコードを読み直し→postを追記して上書き
                    rows = load_history(st.session_state.anon_id, limit=1)
                    if rows and rows[0][1] == "cbt":
                        # 単純に新規行としてpostを書き足す（上書き簡略化）
                        save(st.session_state.anon_id, "cbt", st.session_state.emotion,
                             {"post_only": post})
                        st.success("最新のスコアを追記しました（簡易保存）")

with tab_hist:
    st.markdown("### 履歴")
    rows = load_history(st.session_state.anon_id, limit=300)
    if not rows:
        st.info("まだ記録はありません。となりのタブで体験してみてね。")
    else:
        # 表示整形
        recs = []
        for ts, path, emo, data_json in rows:
            try:
                data = json.loads(data_json) if data_json else {}
            except:
                data = {}
            if path == "breathing":
                summary = f"よぶき {data.get('pattern','4-2-4-2')} × {data.get('sets',2)}回｜{data.get('note','')}"
            else:
                # cbt
                bits = []
                if "pre" in data: bits.append(f"まえ:{data.get('pre')}")
                if data.get("situation"): bits.append("状況:"+data.get("situation"))
                if data.get("thought"): bits.append("自動:"+data.get("thought"))
                if data.get("distortion"): bits.append("くせ:"+data.get("distortion"))
                if data.get("reframe"): bits.append("別見:"+data.get("reframe"))
                if data.get("step"): bits.append("一歩:"+data.get("step"))
                if "post_only" in data: bits.append(f"あと:{data.get('post_only')}")
                summary = "｜".join(bits)[:140]
            recs.append({
                "日時(JST)": ts, "モード": "よぶき" if path=="breathing" else "CBT",
                "気持ち": emo or "", "メモ/サマリ": summary
            })
        df = pd.DataFrame(recs)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # CSV保存（ローカル）
        if st.button("CSVとして保存（/sora_history.csv）"):
            csv_path = os.path.join(os.getcwd(), "sora_history.csv")
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            st.success("保存しました: sora_history.csv")

with tab_about:
    st.markdown("### 使い方 / 検証ポイント")
    st.write("- **ログインなし**で使える匿名MVP（個人テキストは手元保存、サーバ送信なし想定）")
    st.write("- **ハイブリッド**：感情→（よぶき or CBT）→保存→履歴")
    st.write("- **CBTは検証向け**：前後スコア・認知のくせ・一歩の記録で、短時間の効果をみる")
    st.markdown("#### 検証で見る指標（例）")
    st.write("1) 前後スコアの差（平均改善量）")
    st.write("2) 1セッションあたりの完了率（開始→保存まで）")
    st.write("3) “一歩”の実行率（次回ログでフラグ質問を追加予定）")
    st.markdown("#### 次の改善アイデア")
    st.write("- 呼吸アニメをCanvas化して**完全同期**（JS連携 or st_canvas等）")
    st.write("- “あとスコア”を**同一レコードに追記**（編集API or レコードID保持）")
    st.write("- 学校向けは**集計のみ**（個人テキスト非表示）ダッシュボード設計")

