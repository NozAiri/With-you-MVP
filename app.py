# app_ba_plus.py — Sora かんたんノート + 行動活性化（落ち着くUI・絵文字つき）
# 起動: streamlit run app_ba_plus.py

from datetime import datetime, date
from pathlib import Path
from typing import List
import pandas as pd
import streamlit as st

# ================= 基本設定 =================
st.set_page_config(page_title="Sora かんたんノート＋BA", page_icon="🌙", layout="centered")

DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
CSV_NOTE = DATA_DIR / "simple_notes.csv"
CSV_BA   = DATA_DIR / "ba_sessions.csv"

# ----------------- ほんの少しだけ落ち着くCSS -----------------
CALM_CSS = """
<style>
:root{ --ink:#2b2d33; --muted:#6e7380; --panel:#ffffff; }
.stApp{
  background:
    radial-gradient(800px 480px at 0% -10%, rgba(212,232,255,.35), transparent 60%),
    radial-gradient(900px 560px at 100% -8%, rgba(255,221,236,.32), transparent 60%),
    linear-gradient(180deg,#fbfcff, #f8fbff 45%, #f9f6ff 100%);
}
.block-container{max-width:900px}
h1,h2,h3{ color:var(--ink); letter-spacing:.2px }
.stMarkdown, p, label{ color:var(--ink) }
.small{color:var(--muted); font-size:.9rem}
div[data-testid="stVerticalBlock"] > div[role="radiogroup"] label{ font-weight:600; }
.container-like{
  border:1px solid rgba(120,120,200,.12);
  background:var(--panel);
  border-radius:18px; padding:16px; margin:8px 0;
  box-shadow:0 16px 36px rgba(40,40,80,.06);
}
</style>
"""
st.markdown(CALM_CSS, unsafe_allow_html=True)

# ================= データユーティリティ =================
NOTE_COLS = ["ts","date","feeling","trigger","tags","note","self_msg","next_step","distress"]
BA_COLS   = ["ts_start","ts_end","date","category","activity","duration_min",
             "obstacles","first_step","mood_before","distress_before","pleasure_before",
             "mood_after","distress_after","pleasure_after","notes"]

def _ensure_cols(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for c in cols:
        if c not in df.columns: df[c] = ""
    return df

def load_df(path: Path, cols: List[str]) -> pd.DataFrame:
    if path.exists():
        try:
            df = pd.read_csv(path)
            return _ensure_cols(df, cols)
        except Exception:
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def append_row(path: Path, row: dict, cols: List[str]):
    df = load_df(path, cols)
    for c in cols: row.setdefault(c, "")
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(path, index=False, encoding="utf-8")

# ================= 画面タブ =================
page = st.radio("メニュー", ["✏️ 書く", "🏃 行動活性化", "📚 記録", "📈 インサイト"], horizontal=True)
st.title("🌙 Sora かんたんノート")

with st.expander("このアプリについて（短く）", expanded=False):
    st.write(
        "- 気持ちを整え、**次の一歩**を決めるためのシンプルノートです。\n"
        "- 行動活性化（BA）を“短時間で小さく始める”形で組み込みました。\n"
        "- CSVは端末内保存。医療・診断ではありません。"
    )

# 共通：絵文字つき気分
EMOTIONS = [
    "🙂 安定している",
    "😟 不安",
    "😢 悲しい",
    "😡 怒り",
    "😰 緊張",
    "😴 疲労",
    "😕 混乱",
    "😔 落ち込み",
]

# ================= 1) 書く =================
if page == "✏️ 書く":
    st.header("1. いまの気持ち")
    feeling = st.radio("最も近いものを1つ", EMOTIONS, index=1)

    st.header("2. 何があった？")
    TRIGGERS = [
        "📱 返事が来ない/遅い",
        "🏫 仕事・学業で消耗",
        "👥 対人関係のモヤモヤ",
        "🏠 家庭/生活の負荷",
        "❓ 説明しにくい違和感",
    ]
    trigger = st.radio("近いものを1つ", TRIGGERS, index=2)

    tag_options = ["仕事","学校","家族","友人","SNS","健康","お金","その他"]
    tags = st.multiselect("関連するタグ（任意・複数可）", tag_options, default=[])

    st.markdown('<div class="container-like">', unsafe_allow_html=True)
    note = st.text_area("メモ（状況や思考を自由に）", placeholder="例）提出が遅れている。自分だけ遅れている気がして焦る。", height=90)
    st.markdown('</div>', unsafe_allow_html=True)

    st.header("3. 自分への一言（テンプレから選んで編集可）")
    STARTERS = [
        "分からない部分は保留にして、今できる範囲に集中する。",
        "事実と解釈を分けて受け止める。",
        "完璧でなくてよい。小さく進めば十分。",
        "過去の例外やうまくいった時も思い出してみる。",
    ]
    pick = st.radio("候補", STARTERS, index=2)
    self_msg = st.text_input("自分への一言（1行）", value=pick)

    st.header("4. 次の一歩（30分以内にできる行動）")
    NEXT_TEMPLATES = [
        "5分だけ深呼吸＋目を閉じる",
        "ToDoを3つに絞って1つだけ着手",
        "水を飲んで姿勢を整える",
        "返信テンプレを下書きだけ作る",
        "今日は休む、と決める",
    ]
    c1, c2 = st.columns([2,3])
    with c1:
        choice = st.selectbox("テンプレ（任意）", ["（選ばない）"] + NEXT_TEMPLATES, index=0)
    with c2:
        next_step = st.text_input("自分の次の一歩", value="" if choice=="（選ばない）" else choice)

    st.header("5. しんどさ")
    distress = st.slider("いまのしんどさ（0〜10）", 0, 10, 5)

    st.divider()
    colA, colB = st.columns(2)
    with colA:
        if st.button("💾 保存して完了", use_container_width=True):
            now = datetime.now()
            row = {
                "ts": now.isoformat(timespec="seconds"),
                "date": date.today().isoformat(),
                "feeling": feeling,
                "trigger": trigger,
                "tags": " ".join(tags),
                "note": note.strip(),
                "self_msg": self_msg.strip(),
                "next_step": next_step.strip(),
                "distress": distress,
            }
            append_row(CSV_NOTE, row, NOTE_COLS)
            st.success("保存しました。今日はここまででOKです。")
    with colB:
        if st.button("🧼 入力をリセット（未保存）", use_container_width=True):
            st.experimental_rerun()

# ================= 2) 行動活性化（BA） =================
elif page == "🏃 行動活性化":
    st.header("行動活性化：小さく、すぐ始めて、終わったら気分チェック")

    # 事前の主観値（気分/快楽/しんどさ）
    st.subheader("A. いまの状態（開始前）")
    mood_before = st.radio("気分（絵文字つき）", EMOTIONS, index=1)
    pleasure_before = st.slider("楽しさ/快さ（0〜10）", 0, 10, 2)
    distress_before = st.slider("しんどさ（0〜10）", 0, 10, 6)

    st.subheader("B. 活動を選ぶ（カテゴリー → 候補 → 自分用に一言）")
    CAT_MAP = {
        "😊 気分が上がる（快）": [
            "外の光を5分浴びる","好きな音楽を1曲だけ聴く","温かい飲み物をゆっくり飲む",
            "ストレッチを2分","感謝を3つメモする","ベランダに出て深呼吸3回"
        ],
        "💪 達成感（成就）": [
            "机の上を2分だけ片づける","メール1通だけ返信の下書き","タスクを3つに絞る",
            "ToDoひとつだけ着手","洗い物を5個だけ","書類を1束だけ仕分け"
        ],
        "🤝 意味/つながり": [
            "『ありがとう』のメッセージを1通","誰かに“お疲れさま”を伝える",
            "自分に優しい言葉を書き出す","自然の写真を1枚撮る","挨拶をひとつ増やす"
        ],
    }
    category = st.selectbox("カテゴリーを選ぶ", list(CAT_MAP.keys()), index=0)
    template = st.selectbox("候補を選ぶ（編集可）", CAT_MAP[category], index=0)
    activity = st.text_input("今回の活動（短く1行）", value=template)

    c1, c2 = st.columns(2)
    with c1:
        duration = st.slider("時間（分）", 3, 30, 5)
    with c2:
        obstacles = st.multiselect("つまずきそうな点（任意）",
                                   ["面倒に感じる","時間がない","気力がない","道具が必要","場所がない","他の予定がある"])
    first_step = st.text_input("最初の一歩（10〜30秒でできる分解）", value="椅子から立つ／タイマーをセット／水を一口飲む")

    # セッション状態
    st.session_state.setdefault("ba_active", False)
    st.session_state.setdefault("ba_start_ts", "")

    st.divider()
    c3, c4 = st.columns(2)
    with c3:
        if not st.session_state.ba_active:
            if st.button("▶️ 開始（最初の一歩から）", use_container_width=True):
                st.session_state.ba_active = True
                st.session_state.ba_start_ts = datetime.now().isoformat(timespec="seconds")
                st.success("スタート！“最初の一歩”だけでOK。できたら、そのまま活動に入ろう。")
        else:
            st.info(f"開始時刻：{st.session_state.ba_start_ts}")
    with c4:
        if st.session_state.ba_active:
            if st.button("✅ 完了して記録する", use_container_width=True):
                ts_end = datetime.now().isoformat(timespec="seconds")
                # 終了時の主観値
                st.session_state.ba_active = False
                # 入力を促すためのプレースホルダ（完了後に評価UIを出す）
                st.session_state["ba_pending_end"] = ts_end

    # 完了後の評価
    if st.session_state.get("ba_pending_end"):
        st.subheader("C. 終了後の確認（効果測定）")
        mood_after = st.radio("今の気分（絵文字つき）", EMOTIONS, index=0, key="mood_after_radio")
        pleasure_after = st.slider("楽しさ/快さ（0〜10）", 0, 10, max(pleasure_before, 3), key="ple_after")
        distress_after = st.slider("しんどさ（0〜10）", 0, 10, max(0, distress_before-1), key="dist_after")
        notes = st.text_area("ひとことメモ（任意）", placeholder="やってみてどうだった？次は何を変える？", height=70)

        colX, colY = st.columns(2)
        with colX:
            if st.button("💾 BAセッションを保存", use_container_width=True, key="save_ba"):
                append_row(CSV_BA, {
                    "ts_start": st.session_state.ba_start_ts,
                    "ts_end": st.session_state["ba_pending_end"],
                    "date": date.today().isoformat(),
                    "category": category,
                    "activity": activity.strip(),
                    "duration_min": duration,
                    "obstacles": " ".join(obstacles),
                    "first_step": first_step.strip(),
                    "mood_before": mood_before,
                    "distress_before": distress_before,
                    "pleasure_before": pleasure_before,
                    "mood_after": mood_after,
                    "distress_after": distress_after,
                    "pleasure_after": pleasure_after,
                    "notes": notes.strip(),
                }, BA_COLS)
                st.session_state["ba_pending_end"] = ""
                st.session_state.ba_start_ts = ""
                st.success("保存しました。小さく動けたら十分です！")
        with colY:
            if st.button("🧼 破棄（保存しない）", use_container_width=True, key="discard_ba"):
                st.session_state["ba_pending_end"] = ""
                st.session_state.ba_start_ts = ""
                st.info("記録を破棄しました。")

# ================= 3) 記録 =================
elif page == "📚 記録":
    st.header("ノートの記録")
    df = load_df(CSV_NOTE, NOTE_COLS)
    if df.empty:
        st.caption("まだノートの記録がありません。")
    else:
        # フィルタ
        c1, c2, c3 = st.columns(3)
        with c1:
            q = st.text_input("キーワード（本文・タグ）", "")
        with c2:
            emo_f = st.multiselect("気持ち", sorted(df["feeling"].dropna().unique().tolist()))
        with c3:
            dmin, dmax = st.slider("しんどさ", 0, 10, (0, 10))

        view = df.copy()
        for col in ["note","self_msg","next_step","tags","trigger","feeling"]:
            view[col] = view[col].astype(str)

        if q.strip():
            ql = q.lower().strip()
            mask = False
            for col in ["note","self_msg","next_step","tags","trigger","feeling"]:
                mask = mask | view[col].str.lower().str.contains(ql)
            view = view[mask]

        view["distress"] = pd.to_numeric(view["distress"], errors="coerce")
        view = view[(view["distress"] >= dmin) & (view["distress"] <= dmax)]

        try:
            view["ts_dt"] = pd.to_datetime(view["ts"])
            view = view.sort_values("ts_dt", ascending=False)
        except Exception:
            pass

        for _, r in view.head(20).iterrows():
            with st.container(border=True):
                st.markdown(f"**🕒 {r.get('ts','')}**  /  **📅 {r.get('date','')}**")
                st.markdown(f"**気持ち：** {r.get('feeling','')}  |  **出来事：** {r.get('trigger','')}")
                if str(r.get("tags","")).strip():
                    st.markdown(f"**タグ：** {r.get('tags','')}")
                if str(r.get("note","")).strip():
                    st.markdown(f"**メモ：** {r.get('note','')}")
                st.markdown(f"**自分への一言：** {r.get('self_msg','')}")
                if str(r.get("next_step","")).strip():
                    st.markdown(f"**次の一歩：** {r.get('next_step','')}")
                try:
                    st.caption(f"しんどさ：{int(r.get('distress',0))}/10")
                except Exception:
                    pass

        st.divider()
        csv = view.drop(columns=[c for c in ["ts_dt"] if c in view.columns]).to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ CSVダウンロード（ノート）", csv, file_name="simple_notes.csv", mime="text/csv")

    st.header("BAセッションの記録")
    ba = load_df(CSV_BA, BA_COLS)
    if ba.empty:
        st.caption("まだBAの記録がありません。")
    else:
        try:
            ba["ts_start_dt"] = pd.to_datetime(ba["ts_start"])
            ba = ba.sort_values("ts_start_dt", ascending=False)
        except Exception:
            pass

        for _, r in ba.head(20).iterrows():
            with st.container(border=True):
                st.markdown(f"**⏱ {r.get('ts_start','')} → {r.get('ts_end','')}**  /  **📅 {r.get('date','')}**")
                st.markdown(f"**カテゴリー：** {r.get('category','')}  |  **活動：** {r.get('activity','')}")
                st.markdown(f"**時間：** {r.get('duration_min','')} 分  |  **最初の一歩：** {r.get('first_step','')}")
                obs = str(r.get("obstacles","")).strip()
                if obs: st.markdown(f"**障害見込み：** {obs}")
                st.markdown(
                    f"**前**（気分/しんどさ/快さ）：{r.get('mood_before','')} / {r.get('distress_before','')} / {r.get('pleasure_before','')}"
                )
                st.markdown(
                    f"**後**（気分/しんどさ/快さ）：{r.get('mood_after','')} / {r.get('distress_after','')} / {r.get('pleasure_after','')}"
                )
                nt = str(r.get("notes","")).strip()
                if nt: st.markdown(f"**メモ：** {nt}")

        st.divider()
        csv_ba = ba.drop(columns=[c for c in ["ts_start_dt"] if c in ba.columns]).to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ CSVダウンロード（BA）", csv_ba, file_name="ba_sessions.csv", mime="text/csv")

# ================= 4) インサイト =================
else:
    st.header("簡単な傾向を見る")
    df = load_df(CSV_NOTE, NOTE_COLS)
    ba = load_df(CSV_BA, BA_COLS)

    if df.empty and ba.empty:
        st.caption("記録がまだありません。")
    else:
        # ノートの推移
        if not df.empty:
            st.subheader("しんどさの推移（ノート）")
            try:
                df["ts_dt"] = pd.to_datetime(df["ts"])
                df["distress"] = pd.to_numeric(df["distress"], errors="coerce")
                chart = df[["ts_dt","distress"]].dropna().sort_values("ts_dt").set_index("ts_dt")
                st.line_chart(chart)
            except Exception:
                st.caption("グラフを表示できませんでした。")

            st.subheader("よく出る気持ち / 出来事（トップ5）")
            c1, c2 = st.columns(2)
            with c1:
                st.bar_chart(df["feeling"].value_counts().head(5))
            with c2:
                st.bar_chart(df["trigger"].value_counts().head(5))

            # タグ別の平均しんどさ
            st.subheader("タグ別の平均しんどさ")
            tag_rows = []
            for _, r in df.iterrows():
                for t in str(r.get("tags","")).split():
                    if t.strip():
                        tag_rows.append((t.strip(), r.get("distress", None)))
            if tag_rows:
                tag_df = pd.DataFrame(tag_rows, columns=["tag","distress"]).dropna()
                try:
                    tag_df["distress"] = pd.to_numeric(tag_df["distress"], errors="coerce")
                    st.bar_chart(tag_df.groupby("tag")["distress"].mean().sort_values(ascending=False).head(10))
                except Exception:
                    pass

        # BAの効果
        if not ba.empty:
            st.subheader("BA前後の変化（しんどさ/快さの差）")
            try:
                ba["distress_before"] = pd.to_numeric(ba["distress_before"], errors="coerce")
                ba["distress_after"]  = pd.to_numeric(ba["distress_after"], errors="coerce")
                ba["pleasure_before"] = pd.to_numeric(ba["pleasure_before"], errors="coerce")
                ba["pleasure_after"]  = pd.to_numeric(ba["pleasure_after"], errors="coerce")
                ba["Δしんどさ"] = ba["distress_before"] - ba["distress_after"]
                ba["Δ快さ"] = ba["pleasure_after"] - ba["pleasure_before"]
                c3, c4 = st.columns(2)
                with c3:
                    st.bar_chart(ba["Δしんどさ"])
                with c4:
                    st.bar_chart(ba["Δ快さ"])
            except Exception:
                st.caption("BAの集計に失敗しました。")

st.write("")
st.caption("※ 個人情報（氏名・連絡先）は書かないでください。強い苦痛が続く場合は専門機関の利用も検討してください。")
