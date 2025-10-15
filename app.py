# app_simple_plus.py — Sora かんたんノート（大人向け・少し濃い版）
# 起動:  streamlit run app_simple_plus.py

from datetime import datetime, date
from pathlib import Path
from typing import List
import pandas as pd
import streamlit as st

# ================= 基本設定 =================
st.set_page_config(page_title="Sora かんたんノート", page_icon="🌙", layout="centered")

DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
CSV_PATH = DATA_DIR / "simple_notes.csv"

# ================= データユーティリティ =================
COLUMNS = [
    "ts", "date", "feeling", "trigger", "tags",
    "note", "self_msg", "next_step", "distress"
]

def load_df() -> pd.DataFrame:
    if CSV_PATH.exists():
        try:
            df = pd.read_csv(CSV_PATH)
            # 欠損列を補完（将来の拡張に備える）
            for c in COLUMNS:
                if c not in df.columns:
                    df[c] = ""
            return df
        except Exception:
            return pd.DataFrame(columns=COLUMNS)
    return pd.DataFrame(columns=COLUMNS)

def append_row(row: dict):
    df = load_df()
    for c in COLUMNS:
        row.setdefault(c, "")
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(CSV_PATH, index=False, encoding="utf-8")

# ================= 画面タブ =================
page = st.radio("メニュー", ["✏️ 書く", "📚 記録", "📈 インサイト"], horizontal=True)
st.title("🌙 Sora かんたんノート")

with st.expander("このアプリについて（短く）", expanded=False):
    st.write(
        "- 気持ちを短時間で整理し、**次の一歩**を決めるための個人ノートです。\n"
        "- データはこの端末のCSVに保存されます。医療・診断ではありません。"
    )

# ================= 1) 書く =================
if page == "✏️ 書く":
    st.header("1. いまの気持ち")
    EMOTIONS: List[str] = [
        "安定している", "不安", "悲しい", "怒り", "緊張", "疲労"
    ]
    feeling = st.radio("最も近いものを1つ", EMOTIONS, index=1)

    st.header("2. 何があった？")
    TRIGGERS = [
        "返事が来ない/遅い", "仕事・学業で消耗", "対人関係のモヤモヤ",
        "家庭/生活の負荷", "説明しにくい違和感"
    ]
    trigger = st.radio("近いものを1つ", TRIGGERS, index=2)

    tag_options = ["仕事", "学校", "家族", "友人", "SNS", "健康", "お金", "その他"]
    tags = st.multiselect("関連するタグ（任意・複数可）", tag_options, default=[])

    note = st.text_area("メモ（状況や思考を自由に）", placeholder="例）提出が遅れている。自分だけ遅れている気がして焦る。", height=90)

    st.header("3. 自分への一言（テンプレから選んで編集可）")
    STARTERS = [
        "分からない部分は保留にして、今できる範囲に集中する。",
        "事実と解釈を分けて受け止める。",
        "完璧でなくてよい。小さく進めば十分。",
        "過去の例外やうまくいった時も思い出してみる。"
    ]
    pick = st.radio("候補", STARTERS, index=2)
    self_msg = st.text_input("自分への一言（1行）", value=pick)

    st.header("4. 次の一歩（30分以内にできる行動）")
    NEXT_TEMPLATES = [
        "5分だけ深呼吸＋目を閉じる",
        "ToDoを3つに絞って1つだけ着手",
        "水を飲んで姿勢を整える",
        "返信テンプレを下書きだけ作る",
        "今日は休む、と決める"
    ]
    c1, c2 = st.columns([2, 3])
    with c1:
        choice = st.selectbox("テンプレ（任意）", ["（選ばない）"] + NEXT_TEMPLATES, index=0)
    with c2:
        next_step = st.text_input("自分の次の一歩", value="" if choice == "（選ばない）" else choice)

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
                "distress": distress
            }
            append_row(row)
            st.success("保存しました。今日はここまででOKです。")
    with colB:
        if st.button("🧼 入力をリセット（未保存）", use_container_width=True):
            st.experimental_rerun()

# ================= 2) 記録 =================
elif page == "📚 記録":
    st.header("記録一覧")
    df = load_df()

    if df.empty:
        st.caption("まだ記録がありません。まずは「書く」からどうぞ。")
    else:
        # フィルタ
        st.subheader("フィルタ")
        c1, c2, c3 = st.columns(3)
        with c1:
            q = st.text_input("キーワード（本文・タグ）", "")
        with c2:
            emo_f = st.multiselect("気持ち", sorted(df["feeling"].dropna().unique().tolist()), default=[])
        with c3:
            min_d, max_d = st.slider(
                "しんどさの範囲", 0, 10, (0, 10)
            )

        view = df.copy()
        # 型整備
        if "ts" in view.columns:
            try:
                view["ts_dt"] = pd.to_datetime(view["ts"])
            except Exception:
                view["ts_dt"] = pd.NaT

        # 条件
        if q.strip():
            ql = q.strip().lower()
            for col in ["note", "self_msg", "next_step", "tags", "trigger", "feeling"]:
                view[col] = view[col].astype(str)
            mask = False
            for col in ["note", "self_msg", "next_step", "tags", "trigger", "feeling"]:
                mask = mask | view[col].str.lower().str.contains(ql)
            view = view[mask]

        if emo_f:
            view = view[view["feeling"].isin(emo_f)]

        try:
            view["distress"] = pd.to_numeric(view["distress"], errors="coerce")
            view = view[(view["distress"] >= min_d) & (view["distress"] <= max_d)]
        except Exception:
            pass

        # 並び替え & 表示
        if "ts_dt" in view.columns:
            view = view.sort_values("ts_dt", ascending=False)

        # 直近20件表示
        for _, r in view.head(20).iterrows():
            with st.container(border=True):
                st.markdown(f"**🕒 {r.get('ts','')}**  /  **📅 {r.get('date','')}**")
                st.markdown(f"**気持ち：** {r.get('feeling','')}  |  **出来事：** {r.get('trigger','')}")
                tg = str(r.get("tags","")).strip()
                if tg:
                    st.markdown(f"**タグ：** {tg}")
                nt = str(r.get("note","")).strip()
                if nt:
                    st.markdown(f"**メモ：** {nt}")
                st.markdown(f"**自分への一言：** {r.get('self_msg','')}")
                ns = str(r.get("next_step","")).strip()
                if ns:
                    st.markdown(f"**次の一歩：** {ns}")
                try:
                    st.caption(f"しんどさ：{int(r.get('distress',0))}/10")
                except Exception:
                    pass

        st.divider()
        # エクスポート
        st.markdown("**CSVをダウンロード**（端末内バックアップ用）")
        export_df = view.drop(columns=[c for c in ["ts_dt"] if c in view.columns])
        csv = export_df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ ダウンロード", csv, file_name="simple_notes.csv", mime="text/csv")

# ================= 3) インサイト（簡易分析） =================
else:
    st.header("簡単な傾向を見る")
    df = load_df()

    if df.empty:
        st.caption("記録がまだありません。")
    else:
        # 型整備
        try:
            df["ts_dt"] = pd.to_datetime(df["ts"])
            df["date_dt"] = pd.to_datetime(df["date"])
            df["distress"] = pd.to_numeric(df["distress"], errors="coerce")
        except Exception:
            pass

        # 1) しんどさの推移
        st.subheader("しんどさの推移")
        try:
            chart = df[["ts_dt", "distress"]].dropna().sort_values("ts_dt").set_index("ts_dt")
            st.line_chart(chart)
        except Exception:
            st.caption("グラフを表示できませんでした。")

        # 2) よく出る気持ち・出来事（トップ5）
        st.subheader("よく出る気持ち / 出来事（トップ5）")
        c1, c2 = st.columns(2)
        with c1:
            freq_feel = df["feeling"].value_counts().head(5)
            st.bar_chart(freq_feel)
        with c2:
            freq_trig = df["trigger"].value_counts().head(5)
            st.bar_chart(freq_trig)

        # 3) タグ別の平均しんどさ（上位）
        st.subheader("タグ別の平均しんどさ")
        # タグは空白区切り想定
        tag_rows = []
        for _, r in df.iterrows():
            tags = str(r.get("tags","")).split()
            for t in tags:
                if t.strip():
                    tag_rows.append((t.strip(), r.get("distress", None)))
        if tag_rows:
            tag_df = pd.DataFrame(tag_rows, columns=["tag", "distress"]).dropna()
            try:
                tag_df["distress"] = pd.to_numeric(tag_df["distress"], errors="coerce")
                tag_avg = tag_df.groupby("tag")["distress"].mean().sort_values(ascending=False).head(10)
                st.bar_chart(tag_avg)
            except Exception:
                st.caption("タグの集計に失敗しました。")

st.write("")
st.caption(
    "※ 個人情報（氏名・連絡先）は書かないでください。強い苦痛が続く場合は、"
    "身近な大人・職場/学校の相談窓口・専門機関の利用も検討してください。"
)
