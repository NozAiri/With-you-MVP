# app.py — Sora Hybrid MVP (感情→[呼吸 or CBT]、SQLite保存/履歴閲覧つき)
# 使い方:
#   1) `pip install streamlit`
#   2) `streamlit run app.py`
# ポイント:
#  - ニックネームで簡易ログイン（マルチユーザー同時利用OK）
#  - 感情を選ぶ → 「呼吸で落ち着く」 or 「考えを整理（CBT）」 を選択
#  - 入力内容はSQLiteに保存、履歴タブでいつでも確認
#  - ボタンは必ずテキスト表示（“何のボタンか分からない”問題を解消）
#  - 謎の白い空白を出さないように余白を最小化したレイアウト

import streamlit as st
import sqlite3
import json
from datetime import datetime, timezone, timedelta
import time
import os
import pandas as pd

# ====== 基本設定 ======
st.set_page_config(page_title="Sora Hybrid MVP", page_icon="🌙", layout="centered")

# 余白・スタイル微調整（白い謎スペース対策）
st.markdown("""
<style>
/* ヘッダー余白調整 */
.block-container {padding-top: 1rem; padding-bottom: 2rem;}
/* ボタン行の余白抑制 */
button[kind="secondary"], button[kind="primary"] { margin: 0.25rem 0.25rem; }
/* 入力欄の上下マージン縮小 */
.css-1kyxreq, .stTextInput, .stTextArea { margin-top: 0.25rem; margin-bottom: 0.25rem; }
/* サブヘッダーの余白調整 */
h3, h4 { margin-top: 0.6rem; margin-bottom: 0.4rem; }
</style>
""", unsafe_allow_html=True)

# ====== タイムゾーン（JST） ======
JST = timezone(timedelta(hours=9))

def now_jst_str():
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")

# ====== データベース準備（SQLite） ======
DB_PATH = os.path.join(os.getcwd(), "sora_hybrid.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT NOT NULL,
            ts TEXT NOT NULL,
            path TEXT NOT NULL,          -- "breathing" or "cbt"
            emotion_key TEXT,            -- e.g. "sad"
            emotion_label TEXT,          -- e.g. "かなしい"
            data_json TEXT               -- path別の詳細データ
        );
    """)
    conn.commit()
    conn.close()

def save_entry(user, path, emotion_key, emotion_label, data_dict):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO entries (user, ts, path, emotion_key, emotion_label, data_json)
        VALUES (?, ?, ?, ?, ?, ?);
    """, (user, now_jst_str(), path, emotion_key, emotion_label, json.dumps(data_dict, ensure_ascii=False)))
    conn.commit()
    conn.close()

def get_user_history(user, limit=100):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT ts, path, emotion_label, data_json
        FROM entries
        WHERE user = ?
        ORDER BY ts DESC
        LIMIT ?;
    """, (user, limit))
    rows = cur.fetchall()
    conn.close()
    return rows

init_db()

# ====== セッション初期化 ======
if "user" not in st.session_state:
    st.session_state.user = ""
if "emotion" not in st.session_state:
    st.session_state.emotion = {"key": None, "label": None}
if "path" not in st.session_state:
    st.session_state.path = None
if "breathing_run" not in st.session_state:
    st.session_state.breathing_run = False

# ====== サイドバー：ログイン & ナビ ======
with st.sidebar:
    st.markdown("## 🌙 Sora Hybrid MVP")
    st.caption("中高生の“今この瞬間”に寄り添う、短時間ハイブリッド体験")

    st.markdown("### 👤 ログイン（ニックネーム）")
    user_input = st.text_input("ニックネーム（ひらがな/英数OK）", value=st.session_state.user)
    if st.button("ログイン / 更新", use_container_width=True):
        st.session_state.user = user_input.strip()
        st.success("ログインしました")

    st.markdown("---")
    nav = st.radio("ページ", ["体験する", "履歴を見る", "使い方 / メモ"], index=0)

# ====== ログインチェック ======
if not st.session_state.user:
    st.warning("まず左のサイドバーで **ニックネーム** を入力して「ログイン / 更新」を押してね。")
    st.stop()

# ====== メイン：体験ページ ======
if nav == "体験する":
    st.markdown("### ① 今の気持ちを選ぶ")
    st.caption("ボタンはテキストつきで“何のボタンか分からない”問題を回避しています。")

    # 感情ボタン（テキスト＋絵文字）
    emotions = [
        {"key": "sad", "emoji": "😢", "label": "かなしい"},
        {"key": "anx", "emoji": "😟", "label": "ふあん"},
        {"key": "meh", "emoji": "😐", "label": "ふつう"},
        {"key": "ok",  "emoji": "🙂", "label": "だいじょうぶ"},
        {"key": "joy", "emoji": "😊", "label": "うれしい"},
    ]

    cols = st.columns(5)
    for i, e in enumerate(emotions):
        with cols[i]:
            if st.button(f"{e['emoji']} {e['label']}", key=f"emo_{e['key']}", use_container_width=True):
                st.session_state.emotion = {"key": e["key"], "label": e["label"]}
                st.toast(f"今の気持ち：{e['emoji']} {e['label']}", icon="✅")

    # 選択中表示
    if st.session_state.emotion["key"] is None:
        st.info("↑ まず“今の気持ち”を選んでね。")
        st.stop()
    else:
        st.success(f"選択中：{st.session_state.emotion['label']}")

    st.markdown("### ② どちらをやってみる？（ハイブリッド）")
    path_choice = st.radio(
        "今は、落ち着きたい？ それとも考えを整理したい？",
        ["呼吸で落ち着く（約1分）", "考えを整理（CBT 3分）"],
        horizontal=False,
    )
    st.session_state.path = "breathing" if "呼吸" in path_choice else "cbt"

    st.markdown("---")

    # ====== 呼吸モード ======
    if st.session_state.path == "breathing":
        st.markdown("### ③ 呼吸で落ち着く（1分）")
        st.caption("吸って4秒 → 止めて2秒 → 吐いて4秒 → 止めて2秒 × 4セット（合計約48秒）")
        st.write("**ヒント**：肩の力を抜いて、ゆっくり。画面のガイドに合わせてみよう。")

        # 操作ボタン
        colA, colB = st.columns([1,1])
        with colA:
            start = st.button("▶ 開始", use_container_width=True)
        with colB:
            reset = st.button("⟲ リセット", use_container_width=True)

        if reset:
            st.session_state.breathing_run = False
            st.experimental_rerun()

        status = st.empty()
        phase_box = st.empty()
        prog = st.progress(0)

        if start:
            st.session_state.breathing_run = True

        # 実行ループ
        if st.session_state.breathing_run:
            total_sets = 4
            phases = [
                ("吸う", 4),
                ("止める", 2),
                ("吐く", 4),
                ("止める", 2),
            ]
            current = 0
            total_seconds = total_sets * sum(p[1] for p in phases)
            elapsed = 0

            for s in range(total_sets):
                status.info(f"セット {s+1} / {total_sets}")
                for name, sec in phases:
                    for t in range(sec, 0, -1):
                        if not st.session_state.breathing_run:
                            break
                        phase_box.markdown(f"#### {name}（残り {t} 秒）")
                        elapsed += 1
                        prog.progress(min(int((elapsed/total_seconds)*100), 100))
                        time.sleep(1)
                if not st.session_state.breathing_run:
                    break

            st.session_state.breathing_run = False
            phase_box.success("おつかれさま。少し楽になったかな？")

            st.markdown("#### ④ ひとことメモ（任意）")
            note = st.text_input("今の気持ち（短くでOK）", placeholder="例：ちょっと落ち着いた / まだ緊張してる など")
            if st.button("保存する", type="primary"):
                data = {
                    "note": note,
                    "sets": total_sets,
                    "pattern": "4-2-4-2",
                }
                save_entry(
                    user=st.session_state.user,
                    path="breathing",
                    emotion_key=st.session_state.emotion["key"],
                    emotion_label=st.session_state.emotion["label"],
                    data_dict=data
                )
                st.success("保存しました（履歴ページで見られます）")

    # ====== CBTモード ======
    if st.session_state.path == "cbt":
        st.markdown("### ③ 考えを整理（CBT 3分）")
        st.caption("“状況→自動思考→別の見方→小さな一歩” の順で短く書くと、絡まった思考がほどけやすいよ。")

        with st.form("cbt_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            with col1:
                situation = st.text_area("1) どんな状況？（事実）", placeholder="例：明日の提出、時間が足りない気がする", height=80)
                thought   = st.text_area("2) 今浮かんだ考え（自動思考）", placeholder="例：失敗するかも / 私だけ遅れてる", height=80)
            with col2:
                reframe  = st.text_area("3) 別の見方（やさしい仮説）", placeholder="例：今日は30分だけ進めたらOK / 手伝いを頼んでみよう", height=80)
                step     = st.text_input("4) 今日の小さな一歩（具体的）", placeholder="例：タイマー15分で1セクションだけやる")

            submitted = st.form_submit_button("保存する（履歴に追加）", type="primary")

        if submitted:
            if not situation.strip() and not thought.strip() and not reframe.strip() and not step.strip():
                st.warning("どれか一つでOK。短くても大丈夫！")
            else:
                data = {
                    "situation": situation.strip(),
                    "thought": thought.strip(),
                    "reframe": reframe.strip(),
                    "step": step.strip(),
                }
                save_entry(
                    user=st.session_state.user,
                    path="cbt",
                    emotion_key=st.session_state.emotion["key"],
                    emotion_label=st.session_state.emotion["label"],
                    data_dict=data
                )
                st.success("保存しました（履歴ページで見られます）")

        st.markdown("#### ✨ コツ")
        st.write("- ぜんぶ書かなくてOK。**1行**でもすごい前進。")
        st.write("- “今日の小さな一歩”は**5〜15分**で終わるサイズに。")

# ====== 履歴ページ ======
elif nav == "履歴を見る":
    st.markdown("### 履歴")
    rows = get_user_history(st.session_state.user, limit=200)
    if not rows:
        st.info("まだ履歴はありません。まずは「体験する」からどうぞ。")
    else:
        # テーブル用に整形
        records = []
        for ts, path, emo_label, data_json in rows:
            try:
                data = json.loads(data_json) if data_json else {}
            except:
                data = {}
            summary = ""
            if path == "breathing":
                summary = f"呼吸（{data.get('pattern', '4-2-4-2')}）: {data.get('note','')}"
            else:
                # cbt
                s = data.get("situation", "")
                t = data.get("thought", "")
                r = data.get("reframe", "")
                step = data.get("step", "")
                # なるべく短いサマリ
                summary = "｜".join([x for x in [f"状況:{s}", f"思考:{t}", f"別の見方:{r}", f"一歩:{step}"] if x])[:120]
            records.append({
                "日時(JST)": ts,
                "モード": "呼吸" if path=="breathing" else "CBT",
                "気持ち": emo_label or "",
                "メモ/サマリ": summary
            })
        df = pd.DataFrame(records)
        st.dataframe(df, use_container_width=True, hide_index=True)

# ====== 使い方 / メモ ======
else:
    st.markdown("### 使い方 / メモ")
    st.write("""
- 左サイドバーでニックネームを入れて **ログイン** → 「体験する」へ。
- **①気持ちを選ぶ** → **②呼吸 or CBT を選択** → **保存**。
- 保存すると **履歴** に追加され、あとで振り返れます。
- データはローカルの `sora_hybrid.db`（SQLite）に保存されます。
- Streamlit Cloud等でも動作します（同時利用OK）。**個人情報は入れない設計**を想定。
- これは**メンタル医療の代替ではありません**。緊急時は専門機関へ。
""")
    st.markdown("#### ねらい（検証視点）")
    st.write("""
- **短時間（1〜3分）**での安心感・整理感が出るか
- **感情選択 → 体験** の導線が迷わず使われるか
- CBTの**“小さな一歩”**が実行しやすいサイズで提案できているか
""")
    st.markdown("#### 次の改善のタネ")
    st.write("""
- 呼吸ガイドのアニメーションを滑らかに（CSS/Canvas化）
- 効果測定（前後の気分スケール 0-10）
- 匿名アカウントの軽量ログイン（Magic link / 一時ID）
- 学校向け: 管理画面で**集計のみ**（個人は見えない）→ 保護者配慮
""")

