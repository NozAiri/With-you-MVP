# admin_app.py — With You. School Admin Dashboard
# 生徒アプリ(app.py)と同じ Firestore を読み込みつつ、
# 学校用にダッシュボード / ヒートマップ / 相談トリアージを提供する専用アプリ。

from __future__ import annotations
from datetime import datetime, timezone, timedelta, date
from typing import List, Dict, Any, Optional, Tuple

import streamlit as st
import pandas as pd
import altair as alt
import unicodedata, os, json, hmac, hashlib, re

# ================== ページ設定 ==================
st.set_page_config(
    page_title="With You. Admin",
    page_icon="🛠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ================== Firestore 接続 ==================
FIRESTORE_ENABLED = True
try:
    from google.cloud import firestore
    import google.oauth2.service_account as service_account

    @st.cache_resource(show_spinner=False)
    def firestore_client():
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["FIREBASE_SERVICE_ACCOUNT"]
        )
        return firestore.Client(
            project=st.secrets["FIREBASE_SERVICE_ACCOUNT"]["project_id"],
            credentials=creds,
        )

    DB = firestore_client()
except Exception:
    FIRESTORE_ENABLED = False
    DB = None

# ================== Secrets ==================
ADMIN_MASTER_CODE = (
    st.secrets.get("ADMIN_MASTER_CODE")
    or os.environ.get("ADMIN_MASTER_CODE")
    or "uneiairi0931"
)
APP_SECRET = st.secrets.get("APP_SECRET") or os.environ.get("APP_SECRET") or "dev-admin-secret"


# ================== ユーティリティ ==================
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def hmac_sha256_hex(secret: str, data: str) -> str:
    return hmac.new(secret.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).hexdigest()


def payload_series(v: dict, key: str, default=None):
    if not isinstance(v, dict):
        return default
    return (v.get("payload", {}) or {}).get(key, default)


@st.cache_data(show_spinner=False, ttl=60)
def fetch_rows_cached(coll: str, gid: Optional[str], days: int = 60) -> List[dict]:
    """過去days日のデータを取得（ts降順）。インデックスが無くても動くフォールバック。"""
    if not FIRESTORE_ENABLED or DB is None:
        return []
    q = DB.collection(coll)
    if gid:
        q = q.where("group_id", "==", gid)
    since = now_utc() - timedelta(days=days)
    try:
        docs = list(q.order_by("ts", direction="DESCENDING").limit(2000).stream())
    except Exception:
        docs = list(q.limit(2000).stream())
    rows = [d.to_dict() for d in docs]
    out = []
    for r in rows:
        ts = r.get("ts")
        if isinstance(ts, datetime):
            if ts >= since:
                out.append(r)
        else:
            out.append(r)
    return out


def classify_priority_by_message(msg: str) -> str:
    if not msg:
        return "low"
    text = str(msg)
    hi_kw = ["死にたい", "自殺", "消えたい", "殺", "希死", "虐待", "暴力", "首を", "リスカ"]
    mid_kw = ["眠れない", "寝れない", "吐き気", "食欲", "不安", "落ち込", "つらい", "しんど"]
    for k in hi_kw:
        if k in text:
            return "urgent"
    for k in mid_kw:
        if k in text:
            return "medium"
    return "low"


# ================== スタイル ==================
def inject_css():
    st.markdown(
        """
<style>
html, body, .stApp{
  background: radial-gradient(circle at 0% 0%, #101a33, #050b18 55%, #020511 100%);
  color:#f5f7ff;
  font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","Hiragino Sans","Noto Sans JP",system-ui,sans-serif;
}

/* 上部の白い帯を消す */
[data-testid="stAppViewContainer"]{
  background: transparent;
}
[data-testid="stHeader"]{
  background: transparent;
}

/* メインコンテナ */
.block-container{
  padding-top:0.6rem;
  padding-bottom:1.6rem;
  max-width:1180px;
}

/* サイドバー */
section[data-testid="stSidebar"]{
  background:linear-gradient(180deg,#071427 0%,#050b18 100%);
  border-right:1px solid rgba(255,255,255,0.05);
}
section[data-testid="stSidebar"] .css-1d391kg, /* old */
section[data-testid="stSidebar"] .block-container{
  padding-top:0.8rem;
}

/* 共通カード */
.admin-card{
  background:rgba(9,20,46,0.96);
  border-radius:20px;
  padding:18px 18px 14px;
  border:1px solid rgba(112,191,255,0.32);
  box-shadow:0 18px 40px rgba(4,0,40,0.45);
}
.kpi-card{
  background:rgba(13,29,66,0.95);
  border-radius:18px;
  padding:14px 16px 10px;
  border:1px solid rgba(129,194,255,0.35);
  box-shadow:0 14px 30px rgba(0,0,0,0.55);
}
.kpi-label{
  font-size:0.8rem;
  letter-spacing:.08em;
  text-transform:uppercase;
  color:rgba(210,225,255,0.8);
}
.kpi-value{
  font-size:2.0rem;
  font-weight:800;
  color:#ffffff;
}
.kpi-sub{
  font-size:0.85rem;
  color:rgba(193,212,255,0.9);
}

/* タグ */
.badge{
  display:inline-flex;
  align-items:center;
  gap:4px;
  padding:2px 9px;
  border-radius:999px;
  border:1px solid rgba(255,255,255,0.18);
  font-size:0.78rem;
  color:rgba(227,237,255,0.9);
}
.badge-dot{
  width:7px;height:7px;border-radius:999px;background:#6ad6ff;
}

/* テーブル */
.dataframe tbody tr:nth-child(even){
  background:rgba(255,255,255,0.01);
}
</style>
""",
        unsafe_allow_html=True,
    )


inject_css()

# ================== ダッシュボードページ ==================
def make_share_df(rows: List[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(
        [
            {
                "ts": r.get("ts"),
                "group_id": r.get("group_id", ""),
                "mood": payload_series(r, "mood"),
                "sleep_hours": payload_series(r, "sleep_hours"),
                "sleep_quality": payload_series(r, "sleep_quality"),
                "body": payload_series(r, "body", []),
            }
            for r in rows
        ]
    )
    # 🔧 ここが今回の修正ポイント
    # すべての ts を「UTC として解釈」し、その上で .dt.date を取るだけにする
    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    df["date"] = df["ts"].dt.date
    df["has_body"] = df["body"].apply(
        lambda x: int(any((b != "なし") for b in (x or [])))
    )
    df["is_low"] = (df["mood"] == "😟").astype(int)
    return df


def make_consult_df(rows: List[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(
        [
            {
                "ts": r.get("ts"),
                "group_id": r.get("group_id", ""),
                "message": r.get("message", ""),
                "topics": ",".join(r.get("topics", []) or []),
                "intent": r.get("intent", ""),
                "anonymous": r.get("anonymous", True),
                "priority": classify_priority_by_message(r.get("message", "")),
            }
            for r in rows
            if isinstance(r.get("ts"), datetime)
        ]
    )
    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    df["date"] = df["ts"].dt.date
    return df


def page_dashboard(group_filter: Optional[str]):
    st.markdown(
        """
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:.4rem">
  <div>
    <div style="font-size:.8rem;letter-spacing:.14em;text-transform:uppercase;color:rgba(190,210,255,.8)">With You · Admin</div>
    <div style="font-size:1.8rem;font-weight:800;">Dashboard</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    if not FIRESTORE_ENABLED:
        st.error("Firestore に接続できません。`Secrets` の設定を確認してください。")
        return

    rows_share = fetch_rows_cached("school_share", group_filter, days=60)
    rows_cons = fetch_rows_cached("consult_msgs", group_filter, days=60)

    df_share = make_share_df(rows_share)
    df_cons = make_consult_df(rows_cons)

    # ---------- KPI カード ----------
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
        n_days = df_share["date"].nunique() if not df_share.empty else 0
        n_rec = len(df_share)
        st.markdown('<div class="kpi-label">Mood check-ins (60 days)</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-value">{n_rec}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-sub">{n_days} days covered</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
        if not df_share.empty:
            low_rate = (df_share["is_low"].sum() / len(df_share) * 100.0)
            low_rate_txt = f"{low_rate:.1f}%"
        else:
            low_rate_txt = "—"
        st.markdown('<div class="kpi-label">Low mood rate</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-value">{low_rate_txt}</div>', unsafe_allow_html=True)
        st.markdown('<div class="kpi-sub">Share のうち「😟」の割合</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
        urgent = (df_cons["priority"] == "urgent").sum() if not df_cons.empty else 0
        total_cons = len(df_cons)
        st.markdown('<div class="kpi-label">Consultations</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-value">{total_cons}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-sub">urgent: {urgent}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("")

    # ---------- 時系列グラフ ----------
    if not df_share.empty:
        daily = (
            df_share.groupby("date")
            .agg(records=("mood", "count"), low=("is_low", "sum"))
            .reset_index()
        )
        daily["low_rate"] = (daily["low"] / daily["records"] * 100.0).round(1)

        ch = (
            alt.Chart(daily)
            .mark_line(point=True)
            .encode(
                x=alt.X("date:T", title="日付"),
                y=alt.Y("low_rate:Q", title="低気分率(%)"),
                tooltip=["date:T", "low_rate:Q", "records:Q"],
            )
            .properties(height=280)
        )
        st.altair_chart(ch, use_container_width=True)
    else:
        st.caption("まだ「今日を伝える」のデータがありません。")


# ================== クラス / 学年ヒートマップ ==================
def page_heatmap(group_filter: Optional[str]):
    st.markdown("### 🧊 Heatmap（クラス/学年の傾向・匿名）")

    if not FIRESTORE_ENABLED:
        st.error("Firestore に接続できません。")
        return

    # 直近何日を見るか（デフォルト30日）
    days = st.slider("表示する期間（日数）", 7, 60, 30, step=7, key="hm_days")

    rows_share = fetch_rows_cached("school_share", group_filter, days=days)
    df_share = make_share_df(rows_share)
    if df_share.empty:
        st.caption("指定期間内のデータがありません。")
        return

    df = df_share.copy()
    # 現状は group_id を「クラスID」とみなす
    df["class_id"] = df["group_id"].fillna("未設定")

    # 日付×クラス単位で集計
    agg = (
        df.groupby(["class_id", "date"])
        .agg(
            n=("mood", "count"),
            low=("is_low", "sum"),
            body_any=("has_body", "sum"),
            sleep_avg=("sleep_hours", "mean"),
        )
        .reset_index()
    )
    agg["low_rate"] = (agg["low"] / agg["n"] * 100.0).round(1)
    agg["body_rate"] = (agg["body_any"] / agg["n"] * 100.0).round(1)

    # ================== 1. 全体ヒートマップ ==================
    st.caption("低気分率ヒートマップ（色が濃いほど“しんどい日”が多い）")

    heat_chart = (
        alt.Chart(agg)
        .mark_rect()
        .encode(
            x=alt.X("date:T", title="日付"),
            y=alt.Y("class_id:N", title="クラス（group_id 相当）"),
            color=alt.Color("low_rate:Q", title="低気分率(%)"),
            tooltip=[
                alt.Tooltip("class_id:N", title="クラス"),
                alt.Tooltip("date:T", title="日付"),
                alt.Tooltip("low_rate:Q", title="低気分率(%)"),
                alt.Tooltip("n:Q", title="件数"),
            ],
        )
        .properties(height=260)
    )
    st.altair_chart(heat_chart, use_container_width=True)

    st.markdown("---")

    # ================== 2. クラスごとのランキング ==================
    st.caption("クラス別サマリー（直近期間）")

    summary = (
        agg.groupby("class_id")
        .agg(
            days=("date", "nunique"),
            records=("n", "sum"),
            low_sum=("low", "sum"),
            body_sum=("body_any", "sum"),
            sleep_avg=("sleep_avg", "mean"),
        )
        .reset_index()
    )
    summary["低気分率(%)"] = (summary["low_sum"] / summary["records"] * 100.0).round(1)
    summary["体調不良あり率(%)"] = (summary["body_sum"] / summary["records"] * 100.0).round(1)
    summary["平均睡眠(h)"] = summary["sleep_avg"].round(1)

    # 心配度ランキング（ここではシンプルに低気分率でソート）
    ranking = (
        summary[["class_id", "records", "低気分率(%)", "体調不良あり率(%)", "平均睡眠(h)", "days"]]
        .sort_values("低気分率(%)", ascending=False)
        .reset_index(drop=True)
    )
    ranking.rename(columns={"records": "件数", "days": "日数"}, inplace=True)

    st.dataframe(ranking, use_container_width=True, hide_index=True)

    st.markdown(
        "<div class='badge'><span class='badge-dot'></span>"
        " 上から順に“今週、様子を見に行った方がよいクラス”の目安になります。</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ================== 3. クラス別の時系列ドリルダウン ==================
    if not ranking.empty:
        target_class = st.selectbox(
            "詳しく見たいクラスを選択",
            options=ranking["class_id"].tolist(),
            key="hm_target_class",
        )
        focus = agg[agg["class_id"] == target_class].sort_values("date")

        st.caption(f"📈 {target_class} の低気分率の推移")
        line = (
            alt.Chart(focus)
            .mark_line(point=True)
            .encode(
                x=alt.X("date:T", title="日付"),
                y=alt.Y("low_rate:Q", title="低気分率(%)"),
                tooltip=["date:T", "low_rate:Q", "n:Q"],
            )
            .properties(height=220)
        )
        st.altair_chart(line, use_container_width=True)

        st.caption(
            "※ グラフがギザギザしている場合は、日ごとの人数が少ない可能性があります。"
        )


# ================== 相談・チケット ==================
def page_consult(group_filter: Optional[str]):
    st.markdown("### 🕊 相談・チケット")

    if not FIRESTORE_ENABLED:
        st.error("Firestore に接続できません。")
        return

    rows_cons = fetch_rows_cached("consult_msgs", group_filter, days=60)
    df = make_consult_df(rows_cons)
    if df.empty:
        st.caption("相談データがありません。")
        return

    df_view = df.sort_values("ts", ascending=False)[
        ["ts", "priority", "intent", "topics", "anonymous", "message"]
    ]
    df_view.rename(
        columns={
            "ts": "時刻",
            "priority": "優先度",
            "intent": "宛先",
            "topics": "トピック",
            "anonymous": "匿名",
            "message": "内容",
        },
        inplace=True,
    )
    st.dataframe(df_view, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.caption("⚡ 優先度ごとの件数")
    cnt = df.groupby("priority").size().reset_index(name="件数")
    cnt["priority"] = cnt["priority"].map(
        {"urgent": "urgent（緊急）", "medium": "medium（中）", "low": "low（低）"}
    )
    st.dataframe(cnt, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.caption("（MVP）相談 → チケット化")

    if st.button("最新 50 件をチケットとして起票（重複防止）", type="primary"):
        okn = 0
        head50 = df.sort_values("ts", ascending=False).head(50)
        for _, row in head50.iterrows():
            rid = hmac_sha256_hex(
                APP_SECRET, f"{row['ts'].isoformat()}_{row['group_id']}_{row['message'][:40]}"
            )
            q = DB.collection("tickets").where("rid", "==", rid).limit(1).stream()
            exists = any(True for _ in q)
            if exists:
                continue
            DB.collection("tickets").add(
                {
                    "rid": rid,
                    "created_at": now_utc(),
                    "group_id": row["group_id"],
                    "priority": row["priority"],
                    "status": "open",
                    "intent": row["intent"],
                    "topics": row["topics"].split(",") if row["topics"] else [],
                    "note_head": (
                        row["message"][:120] + "..."
                        if isinstance(row["message"], str) and len(row["message"]) > 120
                        else row["message"]
                    ),
                }
            )
            okn += 1
        st.success(f"チケット起票：{okn}件")

    st.markdown("---")
    st.markdown("#### チケット一覧（直近100件）")
    try:
        docs = (
            DB.collection("tickets")
            .order_by("created_at", direction="DESCENDING")
            .limit(100)
            .stream()
        )
        rows = [d.to_dict() | {"id": d.id} for d in docs]
    except Exception:
        rows = []

    if rows:
        tdf = pd.DataFrame(
            [
                {
                    "id": r.get("id"),
                    "作成": r.get("created_at"),
                    "優先度": r.get("priority", ""),
                    "状態": r.get("status", ""),
                    "宛先": r.get("intent", ""),
                    "要約": r.get("note_head", ""),
                }
                for r in rows
            ]
        )
        st.dataframe(
            tdf.drop(columns=["id"]),
            use_container_width=True,
            hide_index=True,
        )

        st.caption("🔧 対応済みにしたいチケットを選択して「クローズ」")
        open_ids = [r["id"] for r in rows if r.get("status") != "closed"]
        if open_ids:
            sel = st.selectbox(
                "チケットID（内部用）",
                options=["— 選択しない —"] + open_ids,
            )
            if sel != "— 選択しない —":
                if st.button("✅ 対応完了として記録", key="ticket_close_btn"):
                    try:
                        DB.collection("tickets").document(sel).set(
                            {"status": "closed", "closed_at": now_utc()}, merge=True
                        )
                        st.success("クローズしました。ページを再読み込みしてください。")
                    except Exception:
                        st.error("更新に失敗しました。")
        else:
            st.caption("オープンのチケットはありません。")
    else:
        st.caption("チケットがありません。")


# ================== 設定 ==================
def page_settings():
    st.markdown("### ⚙️ 設定（MVP：画面内のみ）")
    st.caption(
        "将来的には学校ごとに保存しますが、今はこの画面を開いている間だけ有効な簡易設定です。"
    )

    st.session_state.setdefault("_adm_alert_delta", 25)
    st.session_state.setdefault("_adm_weekday", "金")

    col1, col2 = st.columns(2)
    with col1:
        st.session_state["_adm_alert_delta"] = st.slider(
            "変化率アラート閾値（％）", 10, 60, st.session_state["_adm_alert_delta"], 1
        )
    with col2:
        st.session_state["_adm_weekday"] = st.selectbox(
            "週報の作成曜日",
            ["月", "火", "水", "木", "金"],
            index=["月", "火", "水", "木", "金"].index(
                st.session_state["_adm_weekday"]
            ),
        )

    st.markdown(
        f"現在値：変化率 **{st.session_state['_adm_alert_delta']}％** / 週報 **{st.session_state['_adm_weekday']}曜**"
    )
    st.caption("※ まだこの値を元にした自動アラートは実装していません。")


# ================== メイン ==================
def main():
    st.sidebar.markdown("## 🌙 With You. Admin")

    admin_pw = st.sidebar.text_input("運営パスワード", type="password")
    name = st.sidebar.text_input("あなたのお名前（任意）", placeholder="例：担任 山田")

    if st.sidebar.button("ログイン", type="primary"):
        entered = unicodedata.normalize("NFKC", admin_pw or "").strip()
        master = unicodedata.normalize("NFKC", ADMIN_MASTER_CODE or "").strip()
        if entered == master:
            st.session_state["admin_ok"] = True
            st.session_state["admin_name"] = name or "Admin"
        else:
            st.session_state["admin_ok"] = False
            st.sidebar.error("パスワードが違います。")

    if not st.session_state.get("admin_ok"):
        st.info("左のサイドバーから運営パスワードを入力してください。")
        return

    st.sidebar.markdown(
        f"👤 ログイン中：**{st.session_state.get('admin_name','Admin')}**"
    )

    scope = st.sidebar.radio(
        "表示範囲",
        ["このパスワードのグループだけ", "全グループ"],
        index=0,
    )
    group_filter = None
    if scope.startswith("この"):
        # group_id は現状セッションから取得できないので、今は None (=全グループ)
        # 将来、URL パラメータや secrets から学校IDを受け取る設計にする。
        group_filter = None

    page = st.sidebar.radio(
        "ページ",
        ["Dashboard", "Heatmap", "相談・チケット", "設定"],
    )

    if page == "Dashboard":
        page_dashboard(group_filter)
    elif page == "Heatmap":
        page_heatmap(group_filter)
    elif page == "相談・チケット":
        page_consult(group_filter)
    else:
        page_settings()


if __name__ == "__main__":
    main()
