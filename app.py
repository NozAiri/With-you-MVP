# app.py — Sora Hybrid (メモリ保存版 / 書き込み不要 / 敬語・専門用語なし)
# 目的:
#   3分以内で「落ち着く → 考えを整える → 今日の行動」につなげます
#   保存はメモリのみ（この起動中）。CSVをその場でダウンロードできます。

import streamlit as st
import json, uuid, time
from datetime import datetime, timezone, timedelta
import pandas as pd

# ============== 基本設定 ==============
st.set_page_config(page_title="Sora（ハイブリッド）", page_icon="🌙", layout="centered")

# -------------- スタイル ---------------
st.markdown("""
<style>
:root { --accent:#3b82f6; --text:#e5e7eb; --sub:#94a3b8; --card1:#0f172a; --card2:#111827; }
html, body { background: radial-gradient(1200px 600px at 20% -10%, #0f172a, #0b1220); }
.block-container { padding-top: 1.1rem; padding-bottom: 1.4rem; }
h2,h3 { color: var(--text); letter-spacing:.2px; }
label, p, .small { color:#cbd5e1; } .small { font-size:.9rem; color: var(--sub); }
.card { background: linear-gradient(180deg, var(--card1), var(--card2));
  border: 1px solid rgba(148,163,184,.12); border-radius: 16px; padding: 16px 18px;
  box-shadow: 0 6px 24px rgba(0,0,0,.25), inset 0 1px 0 rgba(255,255,255,.02); margin-bottom: 14px; }
button[kind="primary"]{ border-radius:12px; border:1px solid rgba(59,130,246,.35);
  box-shadow: 0 6px 18px rgba(59,130,246,.25); }
button[kind="secondary"]{ border-radius:12px; }
.stTextArea, .stTextInput, .stNumberInput, .stSelectbox, .stSlider, .stRadio, .stButton { margin:.25rem 0; }
.phase-pill{ display:inline-block; padding:.2rem .75rem; border-radius:999px;
  background: rgba(59,130,246,.12); color:#bfdbfe; border:1px solid rgba(59,130,246,.25);
  margin-bottom:6px; font-weight:600; }
.count-box{ font-size: 42px; font-weight: 700; letter-spacing: .5px; text-align:center;
  color:#e2e8f0; padding: 8px 0 2px 0; }
.dataframe tbody tr th, .dataframe tbody tr td { padding: .40rem .55rem; }
</style>
""", unsafe_allow_html=True)

# ============== セッションと保存（メモリのみ） ==============
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
if "records" not in st.session_state:
    st.session_state.records = []   # ここに辞書を積む（この起動中のみ保持）

def jst_now():
    return datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")

def save_record(path: str, emotion: str, data: dict) -> int:
    rec_id = len(st.session_state.records) + 1
    st.session_state.records.append({
        "id": rec_id,
        "session": st.session_state.session_id,
        "ts": jst_now(),
        "path": path,                 # 'breathing' or 'thinking'
        "emotion": emotion,
        "data_json": json.dumps(data, ensure_ascii=False)
    })
    return rec_id

def update_record(rec_id: int, extra: dict):
    for r in st.session_state.records:
        if r["id"] == rec_id:
            try:
                d = json.loads(r["data_json"]) if r["data_json"] else {}
            except Exception:
                d = {}
            d.update(extra)
            r["data_json"] = json.dumps(d, ensure_ascii=False)
            break

def load_my_records(limit: int = 300):
    rows = [r for r in st.session_state.records if r["session"] == st.session_state.session_id]
    rows.sort(key=lambda x: x["ts"], reverse=True)
    return rows[:limit]

# ============== ヘッダー ==============
st.markdown("<h2>🌙 Sora — ハイブリッド（呼吸 と 考えの整理）</h2>", unsafe_allow_html=True)
st.markdown("<p class='small'>短い時間で「落ち着く → 考えを整える → 今日の行動」につながる体験をご用意しました。</p>", unsafe_allow_html=True)

tab_use, tab_hist, tab_about = st.tabs(["体験", "履歴", "使い方"])

# ============== 体験タブ ==============
with tab_use:
    # ① 気持ち
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

    # ② モード
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("#### ② 進め方をお選びください")
    mode = st.radio(
        "後からもう一方も実施できます。",
        ["呼吸で落ち着く（約1分）", "考えを整える（約3分）"],
        horizontal=False
    )
    path = "breathing" if "呼吸" in mode else "thinking"
    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # ---------- 呼吸 ----------
    if path == "breathing":
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("#### ③ 呼吸で落ち着く")
        st.caption("1サイクル＝吸う → 止める → 吐く → 止める。無理のない回数で構いません。")

        preset = st.selectbox("サイクル（秒）",
                              ["4-2-4-2（標準）", "3-1-5-1（軽め）", "4-4-4-4（均等）"], index=0)
        if "3-1-5-1" in preset:
            inhale, hold1, exhale, hold2 = 3, 1, 5, 1
        elif "4-4-4-4" in preset:
            inhale, hold1, exhale, hold2 = 4, 4, 4, 4
        else:
            inhale, hold1, exhale, hold2 = 4, 2, 4, 2

        sets = st.slider("回数（推奨：2回）", min_value=1, max_value=4, value=2, step=1)

        colA, colB = st.columns(2)
        with colA:   start = st.button("開始", use_container_width=True)
        with colB:   reset = st.button("リセット", use_container_width=True)

        phase_box = st.empty()
        count_box = st.empty()
        prog = st.progress(0)

        if reset:
            st.experimental_rerun()

        if start:
            total = sets * (inhale + hold1 + exhale + hold2)
            elapsed = 0
            phases = [("吸気", inhale), ("停止", hold1), ("呼気", exhale), ("停止", hold2)]

            for _ in range(sets):
                for name, seconds in phases:
                    if seconds <= 0:
                        continue
                    phase_box.markdown(f"<div class='phase-pill'>{name}</div>", unsafe_allow_html=True)
                    for t in range(seconds, 0, -1):
                        count_box.markdown(f"<div class='count-box'>{t}</div>", unsafe_allow_html=True)
                        elapsed += 1
                        prog.progress(min(int(elapsed / total * 100), 100))
                        time.sleep(1)

            phase_box.markdown("<div class='phase-pill'>完了</div>", unsafe_allow_html=True)
            count_box.markdown("<div class='count-box'>お疲れさまでした。</div>", unsafe_allow_html=True)

        st.markdown("##### ④ メモ（任意）")
        note = st.text_input("今の状態（短文で結構です）", placeholder="例：少し落ち着いた／まだ緊張が残る など")
        if st.button("保存する", type="primary"):
            save_record("breathing", st.session_state.emotion,
                        {"note": note, "sets": sets, "pattern": f"{inhale}-{hold1}-{exhale}-{hold2}"})
            st.success("保存いたしました（「履歴」タブからご確認いただけます）。")
        st.markdown("</div>", unsafe_allow_html=True)

    # ---------- 考えの整理 ----------
    else:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("#### ③ 考えを整える（約3分）")
        st.caption("「前の気分 → 事実 → 浮かんだ考え → 別の見方 → 今日の行動」の順に短くご記入ください。")

        with st.form("thinking_form"):
            col0a, col0b = st.columns(2)
            with col0a:
                pre = st.slider("前の気分（0=とてもつらい〜10=落ち着いている）", 0, 10, 3)
            with col0b:
                ask_post = st.checkbox("保存後に「後の気分」も記録する", value=True)

            col1, col2 = st.columns(2)
            with col1:
                situation = st.text_area("① 事実（何があったか）", height=90,
                                         placeholder="例：課題の期限が近い／返信がない など")
                thought   = st.text_area("② 浮かんだ考え", height=90,
                                         placeholder="例：間に合わないかもしれない／嫌われたかも など")
            with col2:
                view     = st.text_area("③ 別の見方（やさしい仮説）", height=90,
                                         placeholder="例：まず10分だけ進める／相手が忙しい可能性 など")
            step = st.text_input("④ 今日の行動（5〜15分で終えられること）",
                                 placeholder="例：タイマー10分で1ページだけ進める")

            submitted = st.form_submit_button("保存する", type="primary")

        if submitted:
            rec_id = save_record("thinking", st.session_state.emotion,
                                 {"pre": pre, "situation": situation.strip(),
                                  "thought": thought.strip(), "view": view.strip(),
                                  "step": step.strip()})
            st.success("保存いたしました（「履歴」タブからご確認いただけます）。")

            if ask_post:
                st.markdown("##### 後の気分（体験後にご記入ください）")
                post = st.slider("後の気分（0〜10）", 0, 10, max(0, min(10, pre)))
                if st.button("後の気分を追記する"):
                    update_record(rec_id, {"post": post})
                    st.success("追記いたしました。履歴に反映されています。")
        st.markdown("</div>", unsafe_allow_html=True)

# ============== 履歴タブ ==============
with tab_hist:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("#### 履歴")
    rows = load_my_records(limit=300)
    if not rows:
        st.info("まだ記録がございません。まずは「体験」タブからご利用ください。")
    else:
        recs = []
        for r in rows:
            data = {}
            try:
                data = json.loads(r["data_json"]) if r["data_json"] else {}
            except Exception:
                pass
            if r["path"] == "breathing":
                summary = f"呼吸 {data.get('pattern','')} × {data.get('sets','-')}回"
                if data.get("note"): summary += f"｜{data['note']}"
                mode = "呼吸"
            else:
                bits = []
                if "pre" in data: bits.append(f"前:{data['pre']}")
                if data.get("situation"): bits.append("事実:"+data["situation"])
                if data.get("thought"): bits.append("考え:"+data["thought"])
                if data.get("view"): bits.append("別の見方:"+data["view"])
                if data.get("step"): bits.append("行動:"+data["step"])
                if "post" in data: bits.append(f"後:{data['post']}")
                summary = "｜".join(bits)[:170]
                mode = "考えの整理"
            recs.append({
                "日時（JST）": r["ts"], "内容": mode,
                "気持ち": r["emotion"] or "", "要約": summary
            })
        df = pd.DataFrame(recs)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # ダウンロード（ファイルに書かず、その場でバイト列を生成）
        csv_bytes = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("CSVをダウンロード", data=csv_bytes, file_name="sora_history.csv", mime="text/csv")
    st.markdown("</div>", unsafe_allow_html=True)

# ============== 使い方タブ ==============
with tab_about:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("#### 使い方")
    st.write("- ログインは不要です。保存はこの起動中のみ有効です。必要に応じてCSVをダウンロードしてください。")
    st.write("- 「呼吸で落ち着く」はカウントに合わせてゆっくり進めてください。")
    st.write("- 「考えを整える」は短く書くことを最優先に。空欄があっても構いません。")
    st.markdown("</div>", unsafe_allow_html=True)
