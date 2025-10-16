# app_calm2min.py — 中高生向け「2分で止める」：ぐるぐる停止・寂しさダウン特化
# 起動: streamlit run app_calm2min.py

from __future__ import annotations
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict
import time
import pandas as pd
import streamlit as st

# ================= 基本設定 & 落ち着くUI =================
st.set_page_config(page_title="Sora 2分で止める", page_icon="🌙", layout="centered")

CALM_CSS = """
<style>
:root{
  --ink:#2b2d33; --muted:#6f7280; --panel:#ffffff;
  --tint1:rgba(212,232,255,.35); --tint2:rgba(235,218,255,.35); --bd:rgba(120,120,200,.12);
}
.stApp{
  background:
    radial-gradient(800px 520px at 0% -10%, var(--tint1), transparent 60%),
    radial-gradient(820px 520px at 100% -8%, var(--tint2), transparent 60%),
    linear-gradient(180deg,#fbfcff,#f7f9ff 50%, #faf8ff 100%);
}
.block-container{max-width:920px}
h1,h2,h3{ color:var(--ink); letter-spacing:.2px }
p,label, .stMarkdown{ color:var(--ink) }
.small{color:var(--muted); font-size:.9rem}
.card{
  border:1px solid var(--bd); background:var(--panel);
  border-radius:18px; padding:16px; margin:10px 0;
  box-shadow:0 16px 36px rgba(40,40,80,.06);
}
.kit-grid{display:grid; grid-template-columns:1fr 1fr; gap:10px}
.badge{display:inline-block; padding:2px 8px; border-radius:999px; background:#f3f5ff; border:1px solid #e2e6ff; font-size:.85rem; color:#344;}
hr{border:none; height:1px; background:linear-gradient(90deg,transparent,#dfe3ff,transparent); margin:10px 0}
</style>
"""
st.markdown(CALM_CSS, unsafe_allow_html=True)

# ================= データ保存先 =================
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
CSV_SESS  = DATA_DIR / "calm_sessions.csv"   # 2分セッション
CSV_BOX   = DATA_DIR / "comfort_box.csv"     # 安心ボックス（お気に入り）

SESS_COLS = [
    "ts_start","ts_end","date",
    "loop_labels","anchor_used","breath_count","ground_54321",
    "micro_action","from_box","notes",
    "rumination_before","rumination_after",
    "lonely_before","lonely_after"
]
BOX_COLS = ["added_ts","kind","label","detail"]

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

# ================= プリセット =================
LOOP_PRESETS = [
    "既読がつかない不安", "比較して落ち込む", "失敗の想像",
    "一人ぼっち感", "将来の心配", "体調の不安",
    "完璧にしたい気持ち", "先生/親の目が気になる",
]
MICRO_ACTIONS = [
    "スタンプだけ送る（メッセージは書かない）",
    "家の人に『おやすみ』と言う",
    "推しの曲を1曲だけ聴く",
    "制服をハンガーにかける",
    "机の上を3点だけ片づける",
    "『今日はここまででOK』と自分に書く",
]

# ================= ナビ =================
page = st.radio("メニュー", ["⏱️ 2分で止める", "📦 安心ボックス", "📚 記録 / インサイト"], horizontal=True)
st.title("🌙 Sora — 2分で止める")

with st.expander("このアプリについて（短く）", expanded=False):
    st.write(
        "【目的】考えがぐるぐる回るのを**一度止めて**、寂しさ・しんどさを**少し下げる**。\n"
        "1回**2分**、3ステップ（止める→体に戻す→つながる）。専門用語は使いません。\n"
        "データはこの端末に保存されます。医療・診断ではありません。"
    )

# ================= 1) 2分で止める =================
if page == "⏱️ 2分で止める":
    st.header("1. いまのぐるぐるに名前をつける（最大3つ）")
    col1, col2 = st.columns(2)
    with col1:
        picked = st.multiselect("近いものを選ぶ", LOOP_PRESETS, max_selections=3)
    with col2:
        free = st.text_input("自分の言葉で（任意）", placeholder="例）明日の提出が不安")
        if free.strip():
            if free.strip() not in picked and len(picked) < 3:
                # ユーザーの自由入力も候補に含められるよう表示
                st.caption("✔️ 入れる場合は左の選択から追加してください。")

    st.subheader("測っておく（前）")
    cA, cB = st.columns(2)
    with cA:
        rum_b = st.slider("ぐるぐるの強さ（0〜10）", 0, 10, 6)
    with cB:
        lon_b = st.slider("寂しさの強さ（0〜10）", 0, 10, 5)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("2. この話題から**20秒だけ離れる**")
    st.caption("ボタンを押すと20秒のカウントが始まります。目を閉じても、画面をぼんやり見てもOK。")
    if st.button("▶︎ 20秒だけ離れる"):
        pb = st.progress(0, text="20秒 だけ 離れる")
        for i in range(20):
            time.sleep(1)
            pb.progress((i+1)/20, text=f"{20-(i+1)} 秒")
        st.success("OK。ここまでで十分です。")
    st.markdown('</div>', unsafe_allow_html=True)

    st.header("3. 体に戻す（どちらか1つでOK）")
    tab1, tab2 = st.tabs(["👀 5-4-3-2-1", "🌬️ 呼吸 × 4"])
    ground_54321 = ""
    breath_count = 0
    with tab1:
        st.caption("見える/触れる/聞こえる/嗅げる/味わう を各1つずつ。テキストは短くでOK。")
        g1 = st.text_input("見えるもの", key="g1")
        g2 = st.text_input("触れるもの", key="g2")
        g3 = st.text_input("聞こえる音", key="g3")
        g4 = st.text_input("香り/空気", key="g4")
        g5 = st.text_input("味/口の感覚", key="g5")
        ground_54321 = " | ".join([g for g in [g1,g2,g3,g4,g5] if g.strip()])
    with tab2:
        st.caption("押すたびに数えます（4回で十分）。")
        st.session_state.setdefault("breath", 0)
        c1, c2, c3 = st.columns([2,1,1])
        with c1:
            if st.button("ゆっくり吸って吐く（+1）"):
                st.session_state.breath = min(4, st.session_state.breath + 1)
        with c2:
            if st.button("−1"):
                st.session_state.breath = max(0, st.session_state.breath - 1)
        with c3:
            if st.button("リセット"):
                st.session_state.breath = 0
        st.markdown(f"**回数：{st.session_state.breath} / 4**")
        breath_count = int(st.session_state.breath)

    st.header("4. つながり/安心を**1つだけ**足す")
    st.caption("“誰かに連絡”でも“連絡しないで自分をねぎらう”でもOK。")
    box_df = load_df(CSV_BOX, BOX_COLS)
    favorites = box_df["label"].tolist() if not box_df.empty else []
    left, right = st.columns(2)
    with left:
        fav = st.selectbox("安心ボックス（自分に効いたもの）", ["（選ばない）"] + favorites, index=0)
    with right:
        templ = st.selectbox("おすすめから選ぶ", ["（選ばない）"] + MICRO_ACTIONS, index=0)
    micro_action = st.text_input("今回やること（1行）", value=(fav if fav!="（選ばない）" else (templ if templ!="（選ばない）" else "")))
    notes = st.text_area("ひとことメモ（任意）", placeholder="やってみてどうだった？次は何を変える？", height=68)

    st.subheader("測っておく（後）")
    cC, cD = st.columns(2)
    with cC:
        rum_a = st.slider("ぐるぐるの強さ（0〜10）", 0, 10, max(0, rum_b-1), key="rum_after")
    with cD:
        lon_a = st.slider("寂しさの強さ（0〜10）", 0, 10, max(0, lon_b-1), key="lon_after")

    st.markdown('<hr/>', unsafe_allow_html=True)
    cS, cT = st.columns(2)
    with cS:
        save_to_box = st.checkbox("今回の“安心”をボックスに保存する", value=False)
    with cT:
        if st.button("💾 記録を保存"):
            now = datetime.now()
            if save_to_box and micro_action.strip():
                append_row(CSV_BOX, {
                    "added_ts": now.isoformat(timespec="seconds"),
                    "kind": "custom",
                    "label": micro_action.strip(),
                    "detail": notes.strip()
                }, BOX_COLS)
            append_row(CSV_SESS, {
                "ts_start": now.isoformat(timespec="seconds"),
                "ts_end": now.isoformat(timespec="seconds"),
                "date": date.today().isoformat(),
                "loop_labels": " / ".join(picked + ([free.strip()] if free.strip() else [])),
                "anchor_used": "54321" if ground_54321 else ("breath" if breath_count>0 else ""),
                "breath_count": breath_count,
                "ground_54321": ground_54321,
                "micro_action": micro_action.strip(),
                "from_box": fav if fav!="（選ばない）" else "",
                "notes": notes.strip(),
                "rumination_before": rum_b,
                "rumination_after": rum_a,
                "lonely_before": lon_b,
                "lonely_after": lon_a
            }, SESS_COLS)
            st.success("保存しました。**ここまでで十分**です。")
            # 後の回に備えて呼吸カウンタだけリセット
            st.session_state.breath = 0

# ================= 2) 安心ボックス =================
elif page == "📦 安心ボックス":
    st.header("自分に効いた“安心”をためておく箱")
    st.caption("曲・物・言葉・香り・ルーティンなど。2分モードで先に表示されます。")
    box_df = load_df(CSV_BOX, BOX_COLS)

    c1, c2 = st.columns(2)
    with c1:
        new_label = st.text_input("追加する“安心”（1行）", placeholder="例）YOASOBI『祝福』1コーラスだけ")
    with c2:
        new_detail = st.text_input("メモ（任意）", placeholder="いつ効きやすい？注意点など")
    if st.button("➕ 追加"):
        if new_label.strip():
            append_row(CSV_BOX, {
                "added_ts": datetime.now().isoformat(timespec="seconds"),
                "kind": "custom",
                "label": new_label.strip(),
                "detail": new_detail.strip()
            }, BOX_COLS)
            st.success("追加しました。")
        else:
            st.info("1行は入力してください。")

    st.subheader("登録済み")
    box_df = load_df(CSV_BOX, BOX_COLS)
    if box_df.empty:
        st.caption("まだありません。上のフォームから追加できます。")
    else:
        try:
            box_df["added_ts_dt"] = pd.to_datetime(box_df["added_ts"])
            box_df = box_df.sort_values("added_ts_dt", ascending=False)
        except Exception:
            pass
        for _, r in box_df.iterrows():
            with st.container(border=True):
                st.markdown(f"**🕒 {r.get('added_ts','')}**  —  **{r.get('label','')}**")
                dt = str(r.get("detail","")).strip()
                if dt: st.caption(dt)

# ================= 3) 記録 / インサイト =================
else:
    st.header("記録")
    df = load_df(CSV_SESS, SESS_COLS)
    if df.empty:
        st.caption("まだ記録がありません。『2分で止める』から始めてみてください。")
    else:
        # フィルタ
        c1, c2, c3 = st.columns(3)
        with c1:
            q = st.text_input("キーワード（ループ名・安心・メモ）", "")
        with c2:
            rmin, rmax = st.slider("ぐるぐる（前）の範囲", 0, 10, (0,10))
        with c3:
            lmin, lmax = st.slider("寂しさ（前）の範囲", 0, 10, (0,10))

        view = df.copy()
        for c in ["loop_labels","micro_action","notes","from_box","ground_54321"]:
            view[c] = view[c].astype(str)

        if q.strip():
            ql = q.lower().strip()
            m = False
            for c in ["loop_labels","micro_action","notes","from_box","ground_54321"]:
                m = m | view[c].str.lower().str.contains(ql)
            view = view[m]

        # 数値型
        for c in ["rumination_before","rumination_after","lonely_before","lonely_after"]:
            view[c] = pd.to_numeric(view[c], errors="coerce")

        view = view[
            (view["rumination_before"].between(rmin, rmax)) &
            (view["lonely_before"].between(lmin, lmax))
        ]

        try:
            view["ts_dt"] = pd.to_datetime(view["ts_start"])
            view = view.sort_values("ts_dt", ascending=False)
        except Exception:
            pass

        for _, r in view.head(30).iterrows():
            with st.container(border=True):
                st.markdown(f"**🕒 {r.get('ts_start','')}** / **📅 {r.get('date','')}**")
                loops = str(r.get("loop_labels","")).strip()
                if loops: st.markdown(f"**ループ名：** {loops}")
                anc = r.get("anchor_used","")
                if anc == "breath": st.markdown(f"**体に戻す：** 呼吸 × {int(r.get('breath_count',0))}")
                elif anc == "54321": st.markdown("**体に戻す：** 5-4-3-2-1")
                act = str(r.get("micro_action","")).strip()
                if act: st.markdown(f"**足した安心：** {act}")
                fb = str(r.get("from_box","")).strip()
                if fb: st.caption(f"（安心ボックス：{fb}）")
                nt = str(r.get("notes","")).strip()
                if nt: st.markdown(f"**メモ：** {nt}")

                # 差分バッジ
                try:
                    dr = int(r.get("rumination_before",0)) - int(r.get("rumination_after",0))
                    dl = int(r.get("lonely_before",0)) - int(r.get("lonely_after",0))
                    st.markdown(
                        f"<span class='badge'>ぐるぐる ↓ {dr}</span>  "
                        f"<span class='badge'>寂しさ ↓ {dl}</span>", unsafe_allow_html=True
                    )
                except Exception:
                    pass

        st.divider()
        csv = view.drop(columns=[c for c in ["ts_dt"] if c in view.columns]).to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ CSVダウンロード（セッション）", csv, file_name="calm_sessions.csv", mime="text/csv")

    st.header("インサイト（超シンプル）")
    if df.empty:
        st.caption("可視化するデータがありません。")
    else:
        try:
            df["ts_dt"] = pd.to_datetime(df["ts_start"])
            df["rumination_before"] = pd.to_numeric(df["rumination_before"], errors="coerce")
            df["rumination_after"]  = pd.to_numeric(df["rumination_after"],  errors="coerce")
            df["lonely_before"]     = pd.to_numeric(df["lonely_before"], errors="coerce")
            df["lonely_after"]      = pd.to_numeric(df["lonely_after"],  errors="coerce")
            df = df.sort_values("ts_dt")

            # 前後差の合計だけを見せる
            total_dr = (df["rumination_before"] - df["rumination_after"]).dropna().sum()
            total_dl = (df["lonely_before"] - df["lonely_after"]).dropna().sum()

            st.markdown(
                f"**累計の下げ幅** — ぐるぐる：{int(total_dr)} / 寂しさ：{int(total_dl)}"
            )

            # 日別の合計差
            daily = df.groupby(df["ts_dt"].dt.date).apply(
                lambda x: pd.Series({
                    "ぐるぐる↓": (x["rumination_before"] - x["rumination_after"]).sum(),
                    "寂しさ↓": (x["lonely_before"] - x["lonely_after"]).sum()
                })
            )
            st.bar_chart(daily)

        except Exception:
            st.caption("インサイトの集計に失敗しました。")

# ================= フッター =================
st.write("")
st.caption("※ 個人情報（氏名・連絡先）は書かないでください。しんどさが強い日は、身近な大人や学校/地域の窓口も検討してください。")
