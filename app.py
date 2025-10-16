# app_focus.py — Sora かんたんノート + やること（小さく始める版・重複解消）
# 起動: streamlit run app_focus.py

from datetime import datetime, date, time, timedelta
from pathlib import Path
from typing import List, Dict
import pandas as pd
import streamlit as st

# =============== 基本設定 & ほんの少し落ち着くCSS ===============
st.set_page_config(page_title="Sora かんたんノート", page_icon="🌙", layout="centered")

CALM_CSS = """
<style>
:root{ --ink:#2b2d33; --muted:#6e7380; --panel:#ffffff; }
.stApp{
  background:
    radial-gradient(800px 480px at 0% -10%, rgba(212,232,255,.35), transparent 60%),
    radial-gradient(900px 560px at 100% -8%, rgba(255,221,236,.32), transparent 60%),
    linear-gradient(180deg,#fbfcff, #f8fbff 45%, #f9f6ff 100%);
}
.block-container{max-width:920px}
h1,h2,h3{ color:var(--ink); letter-spacing:.2px }
.stMarkdown, p, label{ color:var(--ink) }
.small{color:var(--muted); font-size:.9rem}
.card{
  border:1px solid rgba(120,120,200,.12);
  background:var(--panel);
  border-radius:18px; padding:16px; margin:10px 0;
  box-shadow:0 16px 36px rgba(40,40,80,.06);
}
</style>
"""
st.markdown(CALM_CSS, unsafe_allow_html=True)

# =============== データ保存先 ===============
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
CSV_NOTE = DATA_DIR / "simple_notes.csv"
CSV_DO   = DATA_DIR / "do_sessions.csv"   # “やること”の記録（前後チェック付き）

NOTE_COLS = ["ts","date","feeling","trigger","tags","memo","self_msg","next_action","distress"]
DO_COLS   = ["ts_start","ts_end","date","category","idea","plan_sentence",
             "where","when_label","after_cue","duration_min",
             "mood_before","ease_before","distress_before",
             "mood_after","ease_after","distress_after","notes"]

# =============== ユーティリティ ===============
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

def append_row(path: Path, row: Dict, cols: List[str]):
    df = load_df(path, cols)
    for c in cols: row.setdefault(c, "")
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(path, index=False, encoding="utf-8")

# =============== マスタ（絵文字・トリガ・テンプレ） ===============
EMOTIONS = [
    "🙂 安定している","😟 不安","😢 悲しい","😡 怒り",
    "😰 緊張","😴 疲労","😕 混乱","😔 落ち込み",
]

TRIGGERS = [
    "📱 返事が来ない/遅い","🏫 仕事・学業で消耗","👥 対人関係のモヤモヤ",
    "🏠 家庭/生活の負荷","❓ 説明しにくい違和感",
]

TAGS = ["仕事","学校","家族","友人","SNS","健康","お金","その他"]

# “やること”候補（カテゴリ→候補）。左は「アイデア」、右は「実行プラン」に加工
CAT_MAP = {
    "😊 気分が上がる": [
        "外の光を5分浴びる","好きな音楽を1曲だけ聴く","温かい飲み物をゆっくり飲む",
        "ストレッチを2分","感謝を3つメモする","ベランダ深呼吸3回",
    ],
    "💪 ちょっと進める": [
        "机の上を2分だけ片づける","メール1通の下書きだけ","タスクを3つに絞る",
        "ToDoを1つだけ着手","洗い物を5個だけ","書類を1束だけ仕分け",
    ],
    "🤝 つながり/意味": [
        "『ありがとう』を1通送る","“お疲れさま”と伝える",
        "自分にやさしい言葉を書き出す","自然の写真を1枚撮る","挨拶をひとつ増やす",
    ],
}

WHERE_CHOICES = ["デスク","ベッド/ソファ","玄関周り","ベランダ/外","キッチン","その他"]
WHEN_CHOICES  = ["今すぐ","10分後","30分後","時間を指定"]
CUE_CHOICES   = ["タイマーが鳴ったら","飲み物を飲んだら","立ち上がったら","深呼吸3回の後で","メモを書いたら"]

def compose_plan_sentence(idea:str, where:str, when_label:str, cue:str, duration:int, specific_time:time|None):
    t = ""
    if when_label == "時間を指定" and specific_time:
        t = f"{specific_time.strftime('%H:%M')}に"
    elif when_label == "今すぐ":
        t = "このあとすぐ"
    else:
        t = when_label
    cue_part = f"{cue}、" if cue else ""
    return f"{t}、{where}で、{cue_part}{idea}を{duration}分だけ。"

# =============== ナビ ===============
page = st.radio("メニュー", ["✏️ 書く","🧭 やること（小さく始める）","📚 記録","📈 インサイト"], horizontal=True)
st.title("🌙 Sora かんたんノート")

with st.expander("このアプリについて（短く）", expanded=False):
    st.write(
        "- 気持ちを整え、**次の一歩**を決めるためのシンプルなノートです。\n"
        "- “やること”は**小さく・短く・具体的**に。前後の気分も軽く確認します。\n"
        "- データは端末内のCSVに保存。医療・診断ではありません。"
    )

# =============== 1) 書く（重複解消） ===============
if page == "✏️ 書く":
    st.header("1. いまの気持ち")
    feeling = st.radio("最も近いものを1つ", EMOTIONS, index=1)

    st.header("2. 何があった？（近いものを1つ）")
    trigger = st.radio("出来事のタイプ", TRIGGERS, index=2)

    st.header("3. メモ")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    memo = st.text_area("状況や思考（自由に）", placeholder="例）提出が遅れている。他の人は終わっていそうで焦る。", height=90)
    st.markdown('</div>', unsafe_allow_html=True)

    st.header("4. タグ（任意）")
    tags = st.multiselect("あとで探しやすくするために", TAGS, default=[])

    st.header("5. 自分への一言（テンプレから選んで編集可）")
    STARTERS = [
        "分からないところは保留。今できる範囲に集中する。",
        "事実と解釈を分けて受け止める。",
        "完璧でなくてよい。小さく進めば十分。",
        "過去の例外やうまくいった時も思い出す。",
    ]
    pick = st.radio("候補", STARTERS, index=2)
    self_msg = st.text_input("1行メッセージ", value=pick)

    st.header("6. 次の一歩（ここは**要点だけ**）")
    # ★ 重複解消：ここは「アイデア」だけ。具体化は次タブ「やること」で行う。
    idea_templates = [
        "5分だけ深呼吸＋目を閉じる","ToDoを3つに絞って1つだけ着手","水を飲んで姿勢を整える",
        "返信テンプレを下書きだけ作る","今日は休む、と決める"
    ]
    idea_choice = st.selectbox("テンプレ（任意）", ["（選ばない）"] + idea_templates, index=0)
    next_action = st.text_input("やるアイデア（短く）", value="" if idea_choice=="（選ばない）" else idea_choice)

    st.header("7. しんどさ")
    distress = st.slider("いまのしんどさ（0〜10）", 0, 10, 5)

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 保存して完了", use_container_width=True):
            now = datetime.now()
            append_row(CSV_NOTE, {
                "ts": now.isoformat(timespec="seconds"),
                "date": date.today().isoformat(),
                "feeling": feeling,
                "trigger": trigger,
                "tags": " ".join(tags),
                "memo": memo.strip(),
                "self_msg": self_msg.strip(),
                "next_action": next_action.strip(),
                "distress": distress,
            }, NOTE_COLS)
            st.success("保存しました。具体化は『やること』タブでどうぞ。")
    with c2:
        if st.button("🧼 入力をリセット（未保存）", use_container_width=True):
            st.experimental_rerun()

# =============== 2) やること（小さく始める） ===============
elif page == "🧭 やること（小さく始める）":
    st.header("A. 開始前の確認")
    mood_before = st.radio("気分（絵文字つき）", EMOTIONS, index=1)
    ease_before = st.slider("取りかかりやすさ（0〜10）", 0, 10, 4)
    distress_before = st.slider("しんどさ（0〜10）", 0, 10, 6)

    st.header("B. アイデア → 実行プランへ（**左=アイデア** / **右=具体プラン**）")
    colL, colR = st.columns(2)

    with colL:
        category = st.selectbox("カテゴリを選ぶ", list(CAT_MAP.keys()), index=0)
        idea = st.selectbox("アイデア（編集可）", CAT_MAP[category], index=0)
        idea = st.text_input("アイデア（短く一言）", value=idea, key="idea_edit")

    with colR:
        where = st.selectbox("どこで", WHERE_CHOICES, index=0)
        when_label = st.selectbox("いつ", WHEN_CHOICES, index=0)
        specific_time = None
        if when_label == "時間を指定":
            # デフォルトは現在時刻+10分（丸め）
            now = datetime.now()
            rounded = (now + timedelta(minutes=10)).replace(second=0, microsecond=0)
            specific_time = st.time_input("開始時刻", value=time(hour=rounded.hour, minute=rounded.minute), step=300)
        after_cue = st.selectbox("きっかけ（任意）", ["（選ばない）"] + CUE_CHOICES, index=0)
        duration = st.slider("何分だけやる？", 3, 30, 5)

        plan_sentence = compose_plan_sentence(
            idea=idea.strip(),
            where=where,
            when_label=when_label,
            cue="" if after_cue=="（選ばない）" else after_cue,
            duration=duration,
            specific_time=specific_time
        )
        # ★ 右は「実行プラン文」に統合（2枚目スクショの“左右で同じに見える”問題を解消）
        st.text_area("実行プラン（自動で作成・編集可）", value=plan_sentence, height=68, key="plan_sentence")

    # セッション管理
    st.session_state.setdefault("do_active", False)
    st.session_state.setdefault("do_start_ts", "")

    st.divider()
    c3, c4 = st.columns(2)
    with c3:
        if not st.session_state.do_active:
            if st.button("▶️ 今から始める（最初の10〜30秒だけでOK）", use_container_width=True):
                st.session_state.do_active = True
                st.session_state.do_start_ts = datetime.now().isoformat(timespec="seconds")
                st.success("スタート！まずは立つ/タイマーをセット/一口飲む等から。")
        else:
            st.info(f"開始時刻：{st.session_state.do_start_ts}")
    with c4:
        if st.session_state.do_active:
            if st.button("✅ 終わった（記録へ）", use_container_width=True):
                st.session_state["do_pending_end"] = datetime.now().isoformat(timespec="seconds")
                st.session_state.do_active = False

    if st.session_state.get("do_pending_end"):
        st.header("C. 終了後の確認（気分の変化）")
        mood_after = st.radio("今の気分", EMOTIONS, index=0, key="mood_after")
        ease_after = st.slider("取りかかりやすさ（0〜10）", 0, 10, max(5, ease_before), key="ease_after")
        distress_after = st.slider("しんどさ（0〜10）", 0, 10, max(0, distress_before-1), key="dist_after")
        notes = st.text_area("ひとことメモ（任意）", placeholder="やってみて感じたこと/次はどうする？", height=70)

        c5, c6 = st.columns(2)
        with c5:
            if st.button("💾 記録を保存", use_container_width=True):
                append_row(CSV_DO, {
                    "ts_start": st.session_state.do_start_ts,
                    "ts_end": st.session_state["do_pending_end"],
                    "date": date.today().isoformat(),
                    "category": category,
                    "idea": idea.strip(),
                    "plan_sentence": st.session_state.get("plan_sentence", plan_sentence),
                    "where": where,
                    "when_label": when_label if when_label != "時間を指定" else "時間指定",
                    "after_cue": "" if after_cue=="（選ばない）" else after_cue,
                    "duration_min": duration,
                    "mood_before": mood_before,
                    "ease_before": ease_before,
                    "distress_before": distress_before,
                    "mood_after": mood_after,
                    "ease_after": ease_after,
                    "distress_after": distress_after,
                    "notes": notes.strip(),
                }, DO_COLS)
                st.session_state["do_pending_end"] = ""
                st.session_state.do_start_ts = ""
                st.success("保存しました。小さく動けたら十分です！")
        with c6:
            if st.button("🧼 破棄（保存しない）", use_container_width=True):
                st.session_state["do_pending_end"] = ""
                st.session_state.do_start_ts = ""
                st.info("記録を破棄しました。")

# =============== 3) 記録（ノート/やること） ===============
elif page == "📚 記録":
    st.header("ノート")
    df = load_df(CSV_NOTE, NOTE_COLS)
    if df.empty:
        st.caption("まだノートの記録がありません。")
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            q = st.text_input("キーワード（本文・タグ）", "")
        with c2:
            emo_f = st.multiselect("気持ち", sorted(df["feeling"].dropna().unique().tolist()))
        with c3:
            dmin, dmax = st.slider("しんどさ", 0, 10, (0, 10))

        view = df.copy()
        for col in ["memo","self_msg","next_action","tags","trigger","feeling"]:
            view[col] = view[col].astype(str)

        if q.strip():
            ql = q.lower().strip()
            mask = False
            for col in ["memo","self_msg","next_action","tags","trigger","feeling"]:
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
                st.markdown(f"**🕒 {r.get('ts','')}** / **📅 {r.get('date','')}**")
                st.markdown(f"**気持ち：** {r.get('feeling','')}  |  **出来事：** {r.get('trigger','')}")
                tg = str(r.get("tags","")).strip()
                if tg: st.markdown(f"**タグ：** {tg}")
                mm = str(r.get("memo","")).strip()
                if mm: st.markdown(f"**メモ：** {mm}")
                st.markdown(f"**自分への一言：** {r.get('self_msg','')}")
                na = str(r.get("next_action","")).strip()
                if na: st.markdown(f"**次の一歩（アイデア）：** {na}")
                try:
                    st.caption(f"しんどさ：{int(r.get('distress',0))}/10")
                except Exception:
                    pass

        st.divider()
        csv = view.drop(columns=[c for c in ["ts_dt"] if c in view.columns]).to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ CSVダウンロード（ノート）", csv, file_name="simple_notes.csv", mime="text/csv")

    st.header("やること")
    do = load_df(CSV_DO, DO_COLS)
    if do.empty:
        st.caption("まだ“やること”の記録がありません。")
    else:
        try:
            do["start_dt"] = pd.to_datetime(do["ts_start"])
            do = do.sort_values("start_dt", ascending=False)
        except Exception:
            pass

        for _, r in do.head(20).iterrows():
            with st.container(border=True):
                st.markdown(f"**⏱ {r.get('ts_start','')} → {r.get('ts_end','')}** / **📅 {r.get('date','')}**")
                st.markdown(f"**カテゴリ：** {r.get('category','')}  |  **アイデア：** {r.get('idea','')}")
                st.markdown(f"**実行プラン：** {r.get('plan_sentence','')}")
                st.caption(f"場所：{r.get('where','')}  /  タイミング：{r.get('when_label','')}  /  きっかけ：{r.get('after_cue','')}  /  時間：{r.get('duration_min','')}分")
                st.markdown(
                    f"**前**（気分/取りかかりやすさ/しんどさ）：{r.get('mood_before','')} / {r.get('ease_before','')} / {r.get('distress_before','')}"
                )
                st.markdown(
                    f"**後**（気分/取りかかりやすさ/しんどさ）：{r.get('mood_after','')} / {r.get('ease_after','')} / {r.get('distress_after','')}"
                )
                nt = str(r.get("notes","")).strip()
                if nt: st.markdown(f"**メモ：** {nt}")

        st.divider()
        csv2 = do.drop(columns=[c for c in ["start_dt"] if c in do.columns]).to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ CSVダウンロード（やること）", csv2, file_name="do_sessions.csv", mime="text/csv")

# =============== 4) インサイト ===============
else:
    st.header("簡単な傾向")
    df = load_df(CSV_NOTE, NOTE_COLS)
    do = load_df(CSV_DO, DO_COLS)

    if df.empty and do.empty:
        st.caption("記録がまだありません。")
    else:
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
            with c1: st.bar_chart(df["feeling"].value_counts().head(5))
            with c2: st.bar_chart(df["trigger"].value_counts().head(5))

        if not do.empty:
            st.subheader("“やること”の前後差（取りかかりやすさ / しんどさ）")
            try:
                do["ease_before"] = pd.to_numeric(do["ease_before"], errors="coerce")
                do["ease_after"]  = pd.to_numeric(do["ease_after"],  errors="coerce")
                do["distress_before"] = pd.to_numeric(do["distress_before"], errors="coerce")
                do["distress_after"]  = pd.to_numeric(do["distress_after"],  errors="coerce")
                delta_ease = (do["ease_after"] - do["ease_before"]).fillna(0)
                delta_dist = (do["distress_before"] - do["distress_after"]).fillna(0)
                c3, c4 = st.columns(2)
                with c3: st.bar_chart(delta_ease, height=220)
                with c4: st.bar_chart(delta_dist, height=220)
            except Exception:
                st.caption("集計に失敗しました。")

st.write("")
st.caption("※ 個人情報（氏名・連絡先）は書かないでください。強い苦痛が続く場合は専門機関の利用も検討してください。")
