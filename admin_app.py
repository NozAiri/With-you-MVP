# admin_app.py — With You. School Admin Dashboard
# 生徒向けアプリとは分離した、学校向けのダッシュボード専用アプリです。
# Firestore のコレクション構造（school_share / consult_msgs / tickets）は
# 既存アプリと同じものを前提にしています。

from __future__ import annotations
from datetime import datetime, timezone, timedelta, date
from typing import Dict, Tuple, List, Optional, Any
import streamlit as st
import pandas as pd
import altair as alt
import hashlib, hmac, unicodedata, re, json, os, time

# ================== ページ設定 ==================
st.set_page_config(
    page_title="With You. School Admin",
    page_icon="🌙",
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

# ================== 運営パスワード ==================
ADMIN_MASTER_CODE = (
    st.secrets.get("ADMIN_MASTER_CODE")
    or os.environ.get("ADMIN_MASTER_CODE")
    or "uneiairi0931"  # 既定
)

# ================== アプリ秘密鍵（HMAC用） ==================
APP_SECRET = (
    st.secrets.get("APP_SECRET") or os.environ.get("APP_SECRET") or "dev-app-secret"
)

# ================== ユーティリティ ==================
def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def hmac_sha256_hex(secret: str, data: str) -> str:
    return hmac.new(secret.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).hexdigest()


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def group_id_from_password(group_password: str) -> str:
    """既存アプリと同じロジックで、パスワードから group_id を生成。"""
    pw = unicodedata.normalize("NFKC", (group_password or "").strip())
    return hmac_sha256_hex(APP_SECRET, f"grp:{pw}")


@st.cache_data(show_spinner=False, ttl=60)
def fetch_rows_cached(coll: str, gid: Optional[str], days: int = 60) -> List[dict]:
    """school_share / consult_msgs から直近 days 日のデータを取得。"""
    if not FIRESTORE_ENABLED or DB is None:
        return []
    q = DB.collection(coll)
    if gid:
        q = q.where("group_id", "==", gid)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        docs = list(q.order_by("ts", direction="DESCENDING").limit(2000).stream())
    except Exception:
        docs = list(q.limit(2000).stream())
    rows: List[dict] = []
    for d in docs:
        r = d.to_dict()
        ts = r.get("ts")
        if isinstance(ts, datetime):
            if ts >= since:
                rows.append(r)
        else:
            rows.append(r)
    return rows


def payload_series(v: dict, key: str, default=None):
    if not isinstance(v, dict):
        return default
    return (v.get("payload", {}) or {}).get(key, default)


def week_ranges(n_weeks: int = 2) -> List[Tuple[datetime, datetime]]:
    """直近 n_weeks 区間（各 7 日）の [start, end) を新→旧の順で返す。"""
    end = (
        datetime.now(timezone.utc)
        .replace(hour=0, minute=0, second=0, microsecond=0)
        + timedelta(days=1)
    )
    out: List[Tuple[datetime, datetime]] = []
    for _ in range(n_weeks):
        s = end - timedelta(days=7)
        out.append((s, end))
        end = s
    return out  # [今週, 先週, …]


def classify_priority_by_message(msg: str) -> str:
    """超簡易トリアージ。既存アプリと同じロジック。"""
    if not msg:
        return "low"
    text = msg.lower()
    hi_kw = ["死にたい", "自殺", "消えたい", "暴力", "虐待", "いじめ", "つらい", "希死", "殺"]
    mid_kw = ["眠れない", "吐き気", "食欲", "しんどい", "助けて", "不安", "落ち込"]
    for k in hi_kw:
        if k in text:
            return "urgent"
    for k in mid_kw:
        if k in text:
            return "medium"
    return "low"


# ================== セッション状態 ==================
st.session_state.setdefault("admin_authed", False)
st.session_state.setdefault("admin_name", "")
st.session_state.setdefault("nav", "dashboard")  # dashboard / heatmap / tickets / reports
st.session_state.setdefault("gid_mode", "all")  # all / pw
st.session_state.setdefault("gid_pw", "")
st.session_state.setdefault("gid", None)

# ================== スタイル ==================
def inject_css():
    st.markdown(
        """
<style>
html, body, .stApp{
  background: radial-gradient(circle at 0% 0%, #12264c, #050b18 60%, #040713 100%);
  color:#f5f7ff;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "SF Pro Text", "Hiragino Sans", "Noto Sans JP", sans-serif;
}

/* 上部ヘッダ＆ビューコンテナも同じ色で塗る */
[data-testid="stAppViewContainer"]{
  background: transparent;
}
[data-testid="stHeader"]{
  background: transparent;
}

/* メインコンテナの余白を少し上に詰める */
.block-container{
  padding-top:0.5rem;
  padding-bottom:1.5rem;
  max-width:1180px;
}

/* （以下は前回渡したスタイルをそのまま続けてOK） */
section[data-testid="stSidebar"]{
  background: linear-gradient(180deg,#071427 0%,#050b18 100%);
  border-right:1px solid rgba(255,255,255,0.05);
}
...
</style>
""",
        unsafe_allow_html=True,
    )


inject_css()

# ================== ログイン ==================
def admin_login() -> bool:
    if st.session_state["admin_authed"]:
        return True

    st.sidebar.markdown(
        '<div class="sidebar-logo">🌙 With You.<br><span>School Admin</span></div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("---")
    st.sidebar.write("**運営ログイン**")

    pw = st.sidebar.text_input("運営パスワード", type="password")
    name = st.sidebar.text_input("お名前（任意）", placeholder="例：担任 山田")

    if st.sidebar.button("ログイン", type="primary"):
        entered = unicodedata.normalize("NFKC", (pw or "").strip())
        master = unicodedata.normalize("NFKC", (ADMIN_MASTER_CODE or "").strip())
        if entered == master:
            st.session_state["admin_authed"] = True
            st.session_state["admin_name"] = name.strip() or "School Admin"
            st.rerun()
        else:
            st.sidebar.error("パスワードが違います。")

    st.title("With You. School Admin")
    st.write("左のサイドバーから運営パスワードを入力してください。")
    if not FIRESTORE_ENABLED:
        st.error("Firestore に接続できません。st.secrets を確認してください。")

    return False


# ================== サイドバー ナビ ==================
def sidebar_nav():
    st.sidebar.markdown(
        '<div class="sidebar-logo">🌙 With You.<br><span>School Admin</span></div>',
        unsafe_allow_html=True,
    )

    if st.sidebar.button("ログアウト", key="logout", use_container_width=True):
        st.session_state["admin_authed"] = False
        st.session_state["admin_name"] = ""
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown('<div class="nav-section-title">OVERVIEW</div>', unsafe_allow_html=True)

    def nav_btn(page_key: str, label: str, icon: str):
        active = st.session_state["nav"] == page_key
        cls = "nav-item-active" if active else "nav-item"
        st.sidebar.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
        if st.sidebar.button(f"{icon}  {label}", key=f"nav_{page_key}"):
            st.session_state["nav"] = page_key
            st.rerun()
        st.sidebar.markdown("</div>", unsafe_allow_html=True)

    nav_btn("dashboard", "Dashboard", "📊")
    nav_btn("heatmap", "Heatmap", "🌡️")
    nav_btn("tickets", "相談・チケット", "🕊")
    nav_btn("reports", "レポート / 設定", "📁")

    st.sidebar.markdown("---")
    st.sidebar.markdown('<div class="nav-section-title">SCOPE</div>', unsafe_allow_html=True)

    mode = st.sidebar.radio(
        "表示範囲",
        ["学校全体（全グループ）", "特定のパスワードのグループ"],
        key="gid_mode_radio",
    )
    st.session_state["gid_mode"] = "all" if mode.startswith("学校全体") else "pw"

    if st.session_state["gid_mode"] == "pw":
        pw = st.sidebar.text_input("対象グループのパスワード", key="scope_pw", type="password")
        if pw:
            st.session_state["gid_pw"] = pw
            st.session_state["gid"] = group_id_from_password(pw)
            st.sidebar.caption("このパスワードのグループのみ集計します。")
    else:
        st.session_state["gid_pw"] = ""
        st.session_state["gid"] = None

    if st.sidebar.checkbox("Firestore 接続状況を表示", value=False):
        st.sidebar.caption(
            "Firestore: " + ("✅ 接続済み" if FIRESTORE_ENABLED else "⚠️ 未接続")
        )


def current_gid_filter() -> Optional[str]:
    return st.session_state.get("gid") if st.session_state.get("gid_mode") == "pw" else None


# ================== ページ: Dashboard ==================
def page_dashboard():
    gid = current_gid_filter()
    rows_share = fetch_rows_cached("school_share", gid, days=30)
    rows_cons = fetch_rows_cached("consult_msgs", gid, days=30)

    admin_name = st.session_state.get("admin_name", "School Admin")
    st.markdown(
        f"""
<div class="main-header">
  <div class="main-title-block">
    <div class="main-title">Dashboard</div>
    <div class="main-sub">生徒の「いま」の状態を、データでそっと見守るための画面です。</div>
  </div>
  <div class="profile-chip">
    <div class="profile-avatar"></div>
    <div>
      <div style="font-size:0.78rem;opacity:0.7">Signed in as</div>
      <div style="font-weight:600">{admin_name}</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    df_share = pd.DataFrame(rows_share) if rows_share else pd.DataFrame()
    df_cons = pd.DataFrame(rows_cons) if rows_cons else pd.DataFrame()

    mood_score = None
    coverage_rate = None
    sleep_ok_rate = None

    if not df_share.empty and "payload" in df_share:
        mood_map = {"😟": 1, "😐": 3, "🙂": 4}
        df_share["mood_val"] = df_share["payload"].apply(
            lambda p: mood_map.get((p or {}).get("mood"), 3)
        )
        mood_score = round(df_share["mood_val"].mean(), 1)

        # 「今日を伝える」が届いている日数 / 30 日
        if "ts" in df_share:
            df_share["date"] = df_share["ts"].apply(
                lambda x: x.astimezone().date() if isinstance(x, datetime) else None
            )
            days_with_data = df_share["date"].nunique()
            coverage_rate = round((days_with_data / 30) * 100, 1)

        def sleep_ok(p):
            try:
                h = float((p or {}).get("sleep_hours", 0))
            except Exception:
                return 0
            return 1 if 6 <= h <= 9 else 0

        df_share["sleep_ok"] = df_share["payload"].apply(sleep_ok)
        sleep_ok_rate = round(df_share["sleep_ok"].mean() * 100, 1)

    urgent = medium = low = 0
    if not df_cons.empty:
        df_cons["priority"] = df_cons["message"].apply(classify_priority_by_message)
        urgent = int((df_cons["priority"] == "urgent").sum())
        medium = int((df_cons["priority"] == "medium").sum())
        low = int((df_cons["priority"] == "low").sum())

    st.markdown('<div class="kpi-row">', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
        st.markdown('<div class="kpi-title">Mood score</div>', unsafe_allow_html=True)
        val = f"{mood_score:.1f}" if mood_score is not None else "--"
        st.markdown(
            f"""
<div class="kpi-main">
  <div class="kpi-value">{val}</div>
  <div class="kpi-unit">/ 5.0</div>
</div>
<div class="kpi-sub">直近30日間の平均。🙂 が多いほどスコアが高くなります。</div>
<div class="kpi-tag">🧠 心のコンディション</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
        st.markdown('<div class="kpi-title">Coverage</div>', unsafe_allow_html=True)
        val = f"{coverage_rate:.1f}%" if coverage_rate is not None else "--"
        st.markdown(
            f"""
<div class="kpi-main">
  <div class="kpi-value">{val}</div>
</div>
<div class="kpi-sub">30日間のうち、「今日を伝える」が届いた日の割合です。</div>
<div class="kpi-tag">🌙 観察のカバー率</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
        st.markdown('<div class="kpi-title">Consultation signal</div>', unsafe_allow_html=True)
        total_cons = urgent + medium + low
        val = f"{total_cons} 件"
        st.markdown(
            f"""
<div class="kpi-main">
  <div class="kpi-value">{val}</div>
</div>
<div class="kpi-sub">直近30日間の相談メッセージ数（匿名を含む）。</div>
<div class="kpi-tag">🚨 緊急 {urgent} / 中 {medium} / 低 {low}</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        """
<div class="panel" style="margin-top:0.4rem">
  <div class="panel-title">Daily mood trend</div>
  <div class="panel-sub">「今日を伝える」から集計した、日ごとの低気分の割合です。</div>
</div>
""",
        unsafe_allow_html=True,
    )

    if rows_share:
        df = pd.DataFrame(
            [
                {
                    "ts": r.get("ts"),
                    "mood": payload_series(r, "mood"),
                }
                for r in rows_share
                if isinstance(r.get("ts"), datetime)
            ]
        )
        if not df.empty:
            df["date"] = df["ts"].dt.tz_convert(None).dt.date
            df["is_low"] = (df["mood"] == "😟").astype(int)
            agg = (
                df.groupby("date")
                .agg(records=("mood", "count"), low=("is_low", "sum"))
                .reset_index()
            )
            agg["low_rate"] = (agg["low"] / agg["records"] * 100).round(1)
            agg = agg.sort_values("date")

            chart = (
                alt.Chart(agg)
                .mark_area(interpolate="monotone", opacity=0.7)
                .encode(
                    x=alt.X("date:T", title="日付"),
                    y=alt.Y("low_rate:Q", title="低気分率(%)"),
                    tooltip=["date:T", "low_rate:Q", "records:Q"],
                )
                .properties(height=260)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.caption("グラフを表示できるデータがまだありません。")
    else:
        st.caption("グラフを表示できるデータがまだありません。")


# ================== ページ: Heatmap ==================
def page_heatmap():
    gid = current_gid_filter()
    rows_share = fetch_rows_cached("school_share", gid, days=45)

    st.markdown(
        """
<div class="main-header">
  <div class="main-title-block">
    <div class="main-title">Heatmap</div>
    <div class="main-sub">クラスやグループごとの傾向を、匿名のまま俯瞰できます。</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    if not rows_share:
        st.caption("まだデータがありません。")
        return

    df = pd.DataFrame(
        [
            {
                "ts": r.get("ts"),
                "group_id": r.get("group_id", ""),
                "mood": payload_series(r, "mood"),
                "sleep": payload_series(r, "sleep_hours", None),
                "body": payload_series(r, "body", []),
            }
            for r in rows_share
            if isinstance(r.get("ts"), datetime)
        ]
    )
    if df.empty:
        st.caption("まだデータがありません。")
        return

    df["date"] = df["ts"].dt.tz_convert(None).dt.date
    df["body_any"] = df["body"].apply(
        lambda xs: int(any((xs or []) and (b != "なし" for b in xs)))
    )
    agg = (
        df.groupby(["group_id", "date"])
        .agg(
            n=("mood", "count"),
            low=("mood", lambda x: (x == "😟").sum()),
            body_any=("body_any", "sum"),
            sleep_avg=("sleep", "mean"),
        )
        .reset_index()
    )
    agg["low_rate"] = (agg["low"] / agg["n"] * 100).round(1)
    agg["body_rate"] = (agg["body_any"] / agg["n"] * 100).round(1)

    st.markdown(
        """
<div class="panel" style="margin-bottom:0.9rem">
  <div class="panel-title">低気分率ヒートマップ</div>
  <div class="panel-sub">色が濃いほど「😟」の割合が高い日です。個人は特定できません。</div>
</div>
""",
        unsafe_allow_html=True,
    )

    heat = agg.pivot_table(index="group_id", columns="date", values="low_rate")
    st.dataframe(heat, use_container_width=True)

    st.markdown(
        """
<div class="panel" style="margin-top:0.9rem">
  <div class="panel-title">クラス別の平均睡眠時間</div>
  <div class="panel-sub">直近45日間の平均です。</div>
</div>
""",
        unsafe_allow_html=True,
    )

    sleep = agg.groupby("group_id")["sleep_avg"].mean().reset_index().dropna()
    if not sleep.empty:
        chart = (
            alt.Chart(sleep)
            .mark_bar()
            .encode(
                x=alt.X("group_id:N", title="グループ（=パスワードごとの単位）"),
                y=alt.Y("sleep_avg:Q", title="平均睡眠時間 (h)"),
                tooltip=["group_id:N", "sleep_avg:Q"],
            )
            .properties(height=260)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.caption("睡眠データが不足しています。")


# ================== ページ: Tickets ==================
def page_tickets():
    gid = current_gid_filter()
    rows_cons = fetch_rows_cached("consult_msgs", gid, days=60)

    st.markdown(
        """
<div class="main-header">
  <div class="main-title-block">
    <div class="main-title">相談・チケット</div>
    <div class="main-sub">匿名相談をトリアージし、教職員間で共有しやすい形に整理します。</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    if not rows_cons:
        st.caption("相談データがまだありません。")
        return

    df = pd.DataFrame(
        [
            {
                "時刻": r.get("ts"),
                "匿名": r.get("anonymous", True),
                "宛先": r.get("intent", ""),
                "内容": r.get("message", ""),
                "トピック": ",".join(r.get("topics", []) or []),
                "group_id": r.get("group_id", ""),
                "handle": r.get("handle", ""),
            }
            for r in rows_cons
            if isinstance(r.get("ts"), datetime)
        ]
    )
    if df.empty:
        st.caption("相談データがまだありません。")
        return

    df["優先度"] = df["内容"].apply(classify_priority_by_message)
    df = df.sort_values("時刻", ascending=False)

    st.markdown(
        """
<div class="panel" style="margin-bottom:0.9rem">
  <div class="panel-title">相談一覧（直近60日）</div>
  <div class="panel-sub">左ほど新しい相談です。個人名は表示されません。</div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.dataframe(
        df[
            [
                "時刻",
                "優先度",
                "宛先",
                "トピック",
                "内容",
                "匿名",
                "group_id",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")
    st.markdown("##### 優先度別 件数")

    cnt = df.groupby("優先度").size().reset_index(name="件数")
    st.dataframe(cnt, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("##### チケット化（教職員向け ToDo）")

    st.caption(
        "MVP として、相談 1 件を 1 つのチケットとして tickets コレクションに起票します。"
    )

    if not FIRESTORE_ENABLED:
        st.error("Firestore 未接続のため、チケットを起票できません。")
        return

    if st.button("最新 50 件をチケット起票（重複はスキップ）", type="primary"):
        okn = 0
        for _, row in df.head(50).iterrows():
            rid = hmac_sha256_hex(
                APP_SECRET, f"{row['時刻']}_ticket_{row['group_id']}_{row['handle']}"
            )
            q = (
                DB.collection("tickets")
                .where("rid", "==", rid)
                .limit(1)
                .stream()
            )
            if any(True for _ in q):
                continue
            DB.collection("tickets").add(
                {
                    "rid": rid,
                    "created_at": datetime.now(timezone.utc),
                    "group_id": row["group_id"],
                    "priority": row["優先度"],
                    "status": "open",
                    "intent": row["宛先"],
                    "topics": row["トピック"].split(",") if row["トピック"] else [],
                    "note_head": (
                        row["内容"][:120] + "..."
                        if isinstance(row["内容"], str) and len(row["内容"]) > 120
                        else row["内容"]
                    ),
                }
            )
            okn += 1
        st.success(f"チケットを {okn} 件起票しました。")

    st.markdown("##### 既存チケット")

    try:
        docs = (
            DB.collection("tickets")
            .order_by("created_at", direction="DESCENDING")
            .limit(100)
            .stream()
            if FIRESTORE_ENABLED
            else []
        )
        rows = [d.to_dict() for d in docs]
    except Exception:
        rows = []

    if rows:
        tdf = pd.DataFrame(
            [
                {
                    "作成": r.get("created_at"),
                    "優先度": r.get("priority", ""),
                    "状態": r.get("status", ""),
                    "宛先": r.get("intent", ""),
                    "要約": r.get("note_head", ""),
                    "group_id": r.get("group_id", ""),
                }
                for r in rows
            ]
        )
        st.dataframe(tdf, use_container_width=True, hide_index=True)
    else:
        st.caption("まだチケットがありません。")


# ================== ページ: Reports / 設定 ==================
def page_reports():
    gid = current_gid_filter()
    rows_share = fetch_rows_cached("school_share", gid, days=90)
    rows_cons = fetch_rows_cached("consult_msgs", gid, days=90)

    st.markdown(
        """
<div class="main-header">
  <div class="main-title-block">
    <div class="main-title">レポート / 設定</div>
    <div class="main-sub">週報の作成や、外部共有用の CSV エクスポートができます。</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
<div class="panel">
  <div class="panel-title">エクスポート</div>
  <div class="panel-sub">個人名は含まず、group_id と匿名データのみを出力します。</div>
</div>
""",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        if rows_share:
            df = pd.DataFrame(rows_share)
            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "📄 今日を伝える（school_share）CSV",
                data=csv,
                file_name=f"school_share_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
        else:
            st.caption("school_share のデータがありません。")

    with col2:
        if rows_cons:
            df = pd.DataFrame(rows_cons)
            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "📄 相談データ（consult_msgs）CSV",
                data=csv,
                file_name=f"consult_msgs_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
        else:
            st.caption("consult_msgs のデータがありません。")

    st.markdown("---")
    st.markdown(
        """
<div class="panel">
  <div class="panel-title">週報テンプレート（テキスト）</div>
  <div class="panel-sub">直近1週間のサマリーを自動で文章化します。コピーして学校内で共有できます。</div>
</div>
""",
        unsafe_allow_html=True,
    )

    gid_label = "学校全体" if gid is None else "指定グループ"
    this_week, last_week = week_ranges(2)

    def in_range(ts: datetime, r: Tuple[datetime, datetime]) -> bool:
        return isinstance(ts, datetime) and (r[0] <= ts < r[1])

    share_this = [r for r in rows_share if in_range(r.get("ts"), this_week)]
    share_last = [r for r in rows_share if in_range(r.get("ts"), last_week)]
    cons_this = [r for r in rows_cons if in_range(r.get("ts"), this_week)]

    def summary_block(rows_share_inner, rows_cons_inner):
        if not rows_share_inner:
            return None

        df = pd.DataFrame(
            [
                {
                    "ts": r.get("ts"),
                    "mood": payload_series(r, "mood"),
                    "sleep": payload_series(r, "sleep_hours", None),
                }
                for r in rows_share_inner
                if isinstance(r.get("ts"), datetime)
            ]
        )
        if df.empty:
            return None

        df["is_low"] = (df["mood"] == "😟").astype(int)
        low_rate = (df["is_low"].sum() / len(df) * 100) if len(df) else 0.0
        sleep_vals = df["sleep"].dropna().astype(float)
        avg_sleep = sleep_vals.mean() if not sleep_vals.empty else None

        pr_counts = {"urgent": 0, "medium": 0, "low": 0}
        for c in rows_cons_inner:
            pr = classify_priority_by_message(c.get("message", ""))
            pr_counts[pr] = pr_counts.get(pr, 0) + 1

        return {
            "low_rate": round(low_rate, 1),
            "avg_sleep": round(avg_sleep, 1) if avg_sleep is not None else None,
            "cons_urgent": pr_counts["urgent"],
            "cons_medium": pr_counts["medium"],
            "cons_low": pr_counts["low"],
            "n": len(df),
        }

    cur = summary_block(share_this, cons_this)
    prev = summary_block(share_last, [])

    if cur is None:
        st.caption("週報を作成するには、対象期間のデータが必要です。")
        return

    def d(a, b):
        if a is None or b is None:
            return None
        return round(a - b, 1)

    low_diff = d(cur["low_rate"], prev["low_rate"] if prev else None)
    sleep_diff = (
        d(cur["avg_sleep"], prev["avg_sleep"] if prev else None)
        if cur["avg_sleep"] is not None and prev
        else None
    )

    lines: List[str] = []
    lines.append(f"【{gid_label} 週報サマリー】")
    lines.append("")
    lines.append(
        f"- 対象期間：{this_week[0].astimezone().date()} 〜 {this_week[1].astimezone().date() - timedelta(days=1)}"
    )
    lines.append(f"- データ件数：{cur['n']} 件")
    lines.append(
        f"- 低気分（😟）の割合：{cur['low_rate']:.1f}%"
        + (f"（先週比 {low_diff:+.1f}pt）" if low_diff is not None else "")
    )
    if cur["avg_sleep"] is not None:
        lines.append(
            f"- 睡眠時間の平均：{cur['avg_sleep']:.1f}時間"
            + (f"（先週比 {sleep_diff:+.1f}h）" if sleep_diff is not None else "")
        )
    lines.append(
        f"- 相談件数：緊急 {cur['cons_urgent']} / 中 {cur['cons_medium']} / 低 {cur['cons_low']}"
    )
    lines.append("")
    lines.append("※ すべて匿名化されたデータであり、個人は特定されません。")

    txt = "\n".join(lines)
    st.text_area("週報テキスト（コピーしてお使いください）", txt, height=220)

    st.markdown("---")
    st.markdown(
        '<div class="small-muted">この画面の設定はブラウザを閉じるとリセットされます。恒常的な設定が必要な場合は、今後のバージョンで実装予定です。</div>',
        unsafe_allow_html=True,
    )


# ================== ルーター ==================
def main():
    if not admin_login():
        return

    sidebar_nav()

    page = st.session_state.get("nav", "dashboard")
    if page == "dashboard":
        page_dashboard()
    elif page == "heatmap":
        page_heatmap()
    elif page == "tickets":
        page_tickets()
    elif page == "reports":
        page_reports()
    else:
        page_dashboard()


if __name__ == "__main__":
    main()
