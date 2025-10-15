# app_simple.py  — Sora かんたんノート（小学生でも使える版）
# 使い方：streamlit run app_simple.py

from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit as st

# ===== 基本設定 =====
st.set_page_config(page_title="Sora かんたんノート", page_icon="🌙", layout="centered")

DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
CSV_PATH = DATA_DIR / "simple_notes.csv"

def load_df() -> pd.DataFrame:
    if CSV_PATH.exists():
        try:
            return pd.read_csv(CSV_PATH)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

def append_row(row: dict):
    df = load_df()
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(CSV_PATH, index=False, encoding="utf-8")

# ===== 画面上部 タブ（書く / 見る） =====
page = st.radio(
    "えらんでね",
    options=["✏️ ノートを書く", "📚 きろくを見る"],
    horizontal=True,
)

st.title("🌙 Sora かんたんノート")

# 共通の説明（短く）
with st.expander("これはなに？（おとな向けの説明）", expanded=False):
    st.write(
        "しんどい夜や、不安なときに、**3つだけ**うめて気もちをととのえるノートです。"
        " データはこの端末だけに保存されます。医療・診断ではありません。"
    )

# ===== ✏️ ノートを書く =====
if page == "✏️ ノートを書く":
    st.subheader("① いまの気もち")
    # 1つだけ選ぶ：文字つきにして混乱ゼロに
    EMOTIONS = [
        "🙂 だいじょうぶ",
        "😟 ちょっとしんぱい",
        "😢 かなしい",
        "😡 おこっている",
        "😰 どきどきする",
        "😴 つかれている",
    ]
    feeling = st.radio("えらんでね", EMOTIONS, index=1)

    st.subheader("② なにがあった？（ちかいものを1つ）")
    TRIGGERS = [
        "📱 メッセージのへんじがこない",
        "🏫 がっこう・べんきょうでつかれた",
        "👥 ひとづきあいでもやもや",
        "🏠 いえで ちょっとたいへん",
        "❓ うまくいえないけど もやもや",
    ]
    trigger = st.radio("えらんでね", TRIGGERS, index=2)

    st.caption("じぶんのことばで かいてもOK（かかなくてもだいじょうぶ）")
    trigger_free = st.text_input("ひとことメモ（にんい）", placeholder="れい）テストのていしゅつ…しっぱいしたかも")

    st.subheader("③ じぶんへの ひとこと")
    # 先に短い候補を置き、編集もOKに
    STARTERS = [
        "いまはゆっくりでOK。",
        "できているところも、きっとある。",
        "あした また ちょっとやってみよう。",
        "わからないときは ほりゅうでOK。",
    ]
    seed = st.radio("すきなのをえらんで へんこうしてもOK", STARTERS, index=0)
    self_msg = st.text_input("ひとこと（1行）", value=seed)

    st.subheader("いまのしんどさ（0〜10）")
    distress = st.slider("すう字が大きいほど しんどい", 0, 10, 5)

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 ほぞんする（おわり）", use_container_width=True):
            now = datetime.now().isoformat(timespec="seconds")
            row = {
                "ts": now,
                "feeling": feeling,
                "trigger": trigger,
                "trigger_free": trigger_free,
                "self_msg": self_msg,
                "distress": distress,
            }
            append_row(row)
            st.success("ほぞんしたよ。きょうは ここまででOK！")
    with col2:
        if st.button("🧼 入力をぜんぶけす（ほぞんしない）", use_container_width=True):
            # Streamlit は再実行で入力が消える。案内だけ表示。
            st.info("入力を消したよ（保存はされていません）。")

# ===== 📚 きろくを見る =====
else:
    st.subheader("これまでの きろく")
    df = load_df()

    if df.empty:
        st.caption("まだ きろく は ないよ。まずは『ノートを書く』から はじめてみてね。")
    else:
        # 新しい順
        if "ts" in df.columns:
            try:
                df["ts_dt"] = pd.to_datetime(df["ts"])
                df = df.sort_values("ts_dt", ascending=False)
            except Exception:
                pass

        # 直近10件だけ見やすく
        for _, r in df.head(10).iterrows():
            with st.container(border=True):
                st.markdown(f"**🕒 とき：** {r.get('ts','')}")
                st.markdown(f"**① きもち：** {r.get('feeling','')}")
                st.markdown(f"**② なにがあった：** {r.get('trigger','')}")
                tf = str(r.get("trigger_free","")).strip()
                if tf:
                    st.markdown(f"**（ひとこと）** {tf}")
                st.markdown(f"**③ じぶんへの ひとこと：** {r.get('self_msg','')}")
                try:
                    st.caption(f"しんどさ：{int(r.get('distress',0))} / 10")
                except Exception:
                    pass

        st.divider()
        # かんたんエクスポート
        st.markdown("**CSVでダウンロード（おとな向け）**")
        csv = df.drop(columns=[c for c in ["ts_dt"] if c in df.columns]).to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ ダウンロード", csv, file_name="simple_notes.csv", mime="text/csv")

# ===== したの注意書き =====
st.write("")
st.caption(
    "※ なまえ・れんらくさき は かかないでね。とてもつらいときは、"
    " ちかくの おとな や そうだんできる きょく に そうだんしてね。"
)
