# app.py — With You.（学校導入版フル）
# 生徒UIは現状維持。「今日を伝える」「相談する」だけFirestoreへ送信（匿名）。
# 学校導入側（ADMIN）に、週報・クラス集計・相談トリアージ・設定を追加。
# 学術的な観点：
#   - Δ変化率ベースのリスクスコア（自殺念慮リスクの簡易予測）
#   - 相談〜対応完了までの Lead Time 計測（早期介入）
#   - 気分・睡眠の変動性（EMAライクな日次集計）
#   - 匿名集団データからの学級レベル推定
#   - CBTワークの構造化（臨床モデル準拠）
#   - EBPM 用の指標（拾い上げ率・Lead Time・回復指標の土台）

from __future__ import annotations
from datetime import datetime, timezone, timedelta, date
from typing import Dict, Tuple, List, Optional, Any
import streamlit as st
import pandas as pd
import altair as alt
import hashlib, hmac, unicodedata, re, json, os, time

# ================== ページ設定 ==================
st.set_page_config(page_title="With You.", page_icon="🌙", layout="centered", initial_sidebar_state="collapsed")

# ================== Firestore 接続 ==================
FIRESTORE_ENABLED = True
try:
    from google.cloud import firestore
    import google.oauth2.service_account as service_account

    @st.cache_resource(show_spinner=False)
    def firestore_client():
        creds = service_account.Credentials.from_service_account_info(st.secrets["FIREBASE_SERVICE_ACCOUNT"])
        return firestore.Client(project=st.secrets["FIREBASE_SERVICE_ACCOUNT"]["project_id"], credentials=creds)
    DB = firestore_client()
except Exception:
    FIRESTORE_ENABLED = False
    DB = None

# ================== 運営パスワード ==================
ADMIN_MASTER_CODE = (
    st.secrets.get("ADMIN_MASTER_CODE")
    or os.environ.get("ADMIN_MASTER_CODE")
    or "uneiairi0931"   # 既定
)

# ================== アプリ秘密鍵（HMAC用） ==================
APP_SECRET = st.secrets.get("APP_SECRET") or os.environ.get("APP_SECRET") or "dev-app-secret-change-me"

# ================== ユーティリティ ==================
def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

def hmac_sha256_hex(secret: str, data: str) -> str:
    return hmac.new(secret.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).hexdigest()

def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

HANDLE_ALLOWED_RE = re.compile(r"^[a-z0-9_\-\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]+$")  # 英数_-, ひらがな/カタカナ/漢字
def normalize_handle(s: str) -> str:
    s = (s or "").strip()
    s = unicodedata.normalize("NFKC", s)
    s = s.lower()
    return s

def validate_handle(raw: str) -> Tuple[bool, str]:
    n = normalize_handle(raw)
    if len(n) < 4 or len(n) > 12:
        return False, "4〜12文字で入力してください。"
    if not HANDLE_ALLOWED_RE.match(n):
        return False, "使えるのは、英数字・ひらがな・カタカナ・漢字と「_」「-」です。"
    return True, n

def group_id_from_password(group_password: str) -> str:
    pw = unicodedata.normalize("NFKC", (group_password or "").strip())
    return hmac_sha256_hex(APP_SECRET, f"grp:{pw}")

def user_key(group_id: str, handle_norm: str) -> str:
    return sha256_hex(f"{group_id}:{handle_norm}")

def db_create_user(group_id: str, handle_norm: str) -> Tuple[bool, str]:
    """先着専有：存在すれば失敗。"""
    if not FIRESTORE_ENABLED or DB is None:
        return False, "Firestore未接続です。"
    ref = DB.collection("groups").document(group_id).collection("users").document(handle_norm)
    try:
        ref.create({
            "user_key": user_key(group_id, handle_norm),
            "created_at": datetime.now(timezone.utc),
            "last_login_at": datetime.now(timezone.utc),
        })
        return True, ""
    except Exception:
        return False, "この名前はもう使われています。他の名前にしてください。"

def db_user_exists(group_id: str, handle_norm: str) -> bool:
    if not FIRESTORE_ENABLED or DB is None:
        return False
    ref = DB.collection("groups").document(group_id).collection("users").document(handle_norm)
    doc = ref.get()
    return doc.exists

def db_touch_login(group_id: str, handle_norm: str):
    if not FIRESTORE_ENABLED or DB is None:
        return
    ref = DB.collection("groups").document(group_id).collection("users").document(handle_norm)
    try:
        ref.set({"last_login_at": datetime.now(timezone.utc)}, merge=True)
    except Exception:
        pass

def safe_db_add(coll: str, payload: dict) -> bool:
    if not FIRESTORE_ENABLED or DB is None:
        return False
    try:
        DB.collection(coll).add(payload)
        return True
    except Exception:
        return False

# ===============（学校側）集計・補助ユーティリティ =================
@st.cache_data(show_spinner=False, ttl=60)
def fetch_rows_cached(coll: str, gid: Optional[str], days: int = 60) -> List[dict]:
    """過去days日のデータを取得（ts降順）。インデックスが無くても動くフォールバック実装。"""
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
    rows = [d.to_dict() | {"_id": d.id} for d in docs]
    out = []
    for r in rows:
        ts = r.get("ts")
        if isinstance(ts, datetime):
            if ts >= since:
                out.append(r)
        else:
            out.append(r)  # tsが無い/型不明なら通す
    return out

def payload_series(v: dict, key: str, default=None):
    if not isinstance(v, dict): return default
    return (v.get("payload", {}) or {}).get(key, default)

def week_ranges(n_weeks: int = 2) -> List[Tuple[datetime, datetime]]:
    """直近n_weeks区間（各7日）の [start,end) を新→旧の順で返す。"""
    end = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    out = []
    for _ in range(n_weeks):
        s = end - timedelta(days=7)
        out.append((s, end))
        end = s
    return out  # [今週, 先週, …]

def classify_priority_by_message(msg: str) -> str:
    """超簡易な優先度分類（学校トリアージMVP）。高リスク語彙を含める。"""
    if not msg: return "low"
    text = msg.lower()
    hi_kw = ["死にたい","自殺","消えたい","暴力","虐待","いじめ","希死","殺"]
    mid_kw = ["眠れない","吐き気","食欲","しんどい","助けて","不安","落ち込"]
    for k in hi_kw:
        if k in text: return "urgent"
    for k in mid_kw:
        if k in text: return "medium"
    return "low"

# ------- 学術寄り：簡易リスクスコア / 変動性 / Lead Time 指標 -------

def mood_numeric(m: Optional[str]) -> int:
    """🙂=0, 😐=1, 😟=2 のようにスコア化（EMA的な変動を見るため）。"""
    if m == "😟": return 2
    if m == "😐": return 1
    return 0

def sleep_numeric(hours: Optional[float], qual: Optional[str]) -> int:
    """
    睡眠のリスクスコア：
      - 時間 <5h or 質「浅い」 → 2
      - 5〜6h or 「ふつう」     → 1
      - それ以外              → 0
    """
    score = 0
    try:
        h = float(hours or 0)
    except Exception:
        h = 0
    if h < 5: score += 2
    elif h < 6: score += 1
    if qual == "浅い": score += 2
    elif qual == "ふつう": score += 1
    return min(score, 3)

def body_numeric(body_list: Optional[List[str]]) -> int:
    """体調項目（なし以外があれば1）。"""
    if not body_list: return 0
    return 1 if any(b and b != "なし" for b in body_list) else 0

def consult_numeric(priority: str) -> int:
    """相談優先度スコア。自殺念慮関連語彙を含む urgent を最重視。"""
    if priority == "urgent": return 4
    if priority == "medium": return 2
    if priority == "low": return 1
    return 0

def compute_risk_index(share_rows: List[dict], cons_rows: List[dict]) -> float:
    """
    集団レベルのリスク指数（0〜100目安）。
    - 気分・睡眠・体調（school_share）
    - 自由記述の優先度（consult_msgs）
    をルールベースで合成。
    本格的な自殺念慮予測モデルは Cloud Functions 側で拡張予定。
    """
    if not share_rows and not cons_rows:
        return 0.0

    total_person_days = max(1, len(share_rows))
    score = 0

    # 非言語シグナル（EMA的指標）
    for r in share_rows:
        p = r.get("payload", {}) or {}
        score += mood_numeric(p.get("mood"))
        score += sleep_numeric(p.get("sleep_hours"), p.get("sleep_quality"))
        score += body_numeric(p.get("body"))

    # 言語相談
    for c in cons_rows:
        pr = classify_priority_by_message(c.get("message", ""))
        score += consult_numeric(pr)

    # 正規化：1日あたりおおよそ 0〜10 程度になるように
    idx = (score / (total_person_days * 10)) * 100
    return float(round(min(max(idx, 0.0), 100.0), 1))

def compute_daily_ema(df_share: pd.DataFrame) -> pd.DataFrame:
    """
    日次×EMA的指標。
    - mood_numeric の平均
    - sleep_hours の平均
    - 気分スコアの 7日ローリング分散（変動性）
    """
    if df_share.empty:
        return pd.DataFrame()
    df = df_share.copy()
    df["day"] = df["ts"].dt.tz_convert(None).dt.date
    df["mood_score"] = df["mood"].map(mood_numeric)
    df_agg = df.groupby("day").agg(
        mood_score=("mood_score", "mean"),
        sleep_avg=("sleep_hours", "mean"),
        n=("mood", "count")
    ).reset_index()
    df_agg = df_agg.sort_values("day")
    df_agg["mood_var_7d"] = df_agg["mood_score"].rolling(window=7, min_periods=3).var()
    return df_agg

def compute_leadtime_metrics(gid_filter: Optional[str], days: int = 60) -> Dict[str, Any]:
    """
    相談→チケット→対応完了までのリードタイムを測る。
    tickets コレクション：
        created_at: 相談検知時刻
        closed_at:  対応完了時刻（運営タブでボタン押下）
    """
    if not FIRESTORE_ENABLED or DB is None:
        return {"n_closed": 0, "avg_days": None}
    since = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        q = DB.collection("tickets").where("created_at", ">=", since)
        if gid_filter:
            q = q.where("group_id", "==", gid_filter)
        docs = list(q.stream())
    except Exception:
        docs = []

    deltas = []
    for d in docs:
        r = d.to_dict()
        st_at = r.get("created_at")
        ed_at = r.get("closed_at")
        if isinstance(st_at, datetime) and isinstance(ed_at, datetime) and ed_at >= st_at:
            deltas.append((ed_at - st_at).total_seconds() / 86400.0)

    if not deltas:
        return {"n_closed": 0, "avg_days": None}

    avg_days = round(sum(deltas) / len(deltas), 2)
    return {"n_closed": len(deltas), "avg_days": avg_days}

# ================== 状態 ==================
st.session_state.setdefault("auth_ok", False)
st.session_state.setdefault("mode", "LOGIN")  # "REGISTER" / "LOGIN"
st.session_state.setdefault("group_pw", "")
st.session_state.setdefault("handle_raw", "")
st.session_state.setdefault("group_id", "")
st.session_state.setdefault("handle_norm", "")
st.session_state.setdefault("user_disp", "")  # 表示用
st.session_state.setdefault("view", "HOME")   # 画面
st.session_state.setdefault("flash_msg", "")  # 再描画時の一時メッセージ
st.session_state.setdefault("role", "user")   # "user" or "admin"

# ローカルログ（端末保存）
st.session_state.setdefault("_local_logs", {"note":[], "breath":[], "study":[]})

# ================== スタイル ==================
def inject_css():
    st.markdown("""
<style>
:root{
  --text:#182742; --muted:#63728a; --panel:#ffffffee; --panel-brd:#e1e9ff; --shadow:0 14px 34px rgba(40,80,160,.12);
  --grad:
    radial-gradient(1400px 600px at -10% -10%, #e8f1ff 0%, rgba(232,241,255,0) 60%),
    radial-gradient(1200px 500px at 110% -10%, #ffeef6 0%, rgba(255,238,246,0) 60%),
    radial-gradient(1200px 500px at 50% 110%, #e9fff7 0%, rgba(233,255,247,0) 60%),
    linear-gradient(180deg, #f9fbff 0%, #eef5ff 100%);
}
html, body, .stApp{ background:var(--grad); color:var(--text); }
.block-container{ max-width:980px; padding-top:1rem; padding-bottom:2rem }
.card{ background:var(--panel); border:1px solid var(--panel-brd); border-radius:22px; padding:18px; box-shadow:var(--shadow); }
.item{ background:#fff; border:1px solid #e3e8ff; border-radius:18px; padding:16px; box-shadow:var(--shadow) }
.tip{ color:#6a7d9e; font-size:.92rem; }
.top-tabs{
  position: sticky; top: 0; z-index: 50;
  background: rgba(250,253,255,.85); backdrop-filter:saturate(160%) blur(8px);
  border:1px solid #dfe6ff; border-radius:16px; box-shadow:0 12px 24px rgba(70,120,200,.12);
  padding:6px 8px; margin-bottom:14px;
}
.top-tabs .stButton>button{
  width:100%; height:40px; border-radius:12px; font-weight:800;
  background:#f6f9ff; border:1px solid #e1eaff; color:#2b4772;
}
.top-tabs .active .stButton>button{ background:#eaf3ff; border-bottom:3px solid #5EA3FF }
.bigbtn{ margin-bottom:12px; }
.bigbtn .stButton>button{
  width:100%; text-align:left; border-radius:22px; border:1px solid #dfe6ff; box-shadow:var(--shadow);
  padding:18px 18px 16px; white-space:pre-wrap; line-height:1.35;
  background:linear-gradient(135deg,#ffffff 0%,#eef5ff 100%); color:#132748; font-weight:600;
}
.bigbtn .stButton>button::first-line{ font-weight:900; font-size:1.06rem; color:#0f2545; }
.cbt-card{ background:#fff; border:1px solid #e3e8ff; border-radius:18px; padding:18px 18px 14px; box-shadow:0 6px 20px rgba(31,59,179,0.06); margin-bottom:14px; }
.cbt-heading{ font-weight:900; font-size:1.05rem; color:#1b2440; margin:0 0 6px 0;}
.cbt-sub{ color:#63728a; font-size:0.92rem; margin:-2px 0 10px 0;}
.meta{ color:#6a7d9e; font-size:.86rem; margin-bottom:.3rem}
.ok-chip{ display:inline-block; background:#eefaf1; color:#147a3d; border:1px solid #cfeedd; border-radius:999px; padding:.2rem .6rem; font-size:.82rem }
.breath-spot{
  width:260px;height:260px;border-radius:999px;
  background:radial-gradient(circle at 50% 40%, #f7fbff, #e8f2ff 60%, #eef8ff 100%);
  border:1px solid #dbe9ff;
  box-shadow:0 18px 36px rgba(90,140,190,.14), inset 0 -10px 25px rgba(120,150,200,.15);
}
.small{font-size:.9rem;color:#5b6a85}
.badge{display:inline-block;border:1px solid #dbe3ff;border-radius:999px;padding:.15rem .5rem;margin-left:.4rem}
</style>
""", unsafe_allow_html=True)
inject_css()

# ================== ナビ ==================
def get_sections():
    base = [
        ("HOME",   "🏠 ホーム"),
        ("SHARE",  "🏫 今日を伝える"),
        ("SESSION","🌙 リラックス"),
        ("NOTE",   "📝 ノート"),
        ("STUDY",  "📚 Study Tracker"),
        ("REVIEW", "📒 ふりかえり"),
        ("CONSULT","🕊 相談"),
    ]
    if st.session_state.get("role") == "admin":
        base.append(("ADMIN", "🛠 運営"))
    return base

def top_tabs():
    if st.session_state.view == "HOME": return
    active = st.session_state.view
    st.markdown('<div class="top-tabs">', unsafe_allow_html=True)
    sections = get_sections()
    cols = st.columns(len(sections))
    for i, (key, label) in enumerate(sections):
        with cols[i]:
            cls = "active" if key == active else ""
            st.markdown(f"<div class='{cls}'>", unsafe_allow_html=True)
            if st.button(label, key=f"tab_{key}"):
                st.session_state.view = key; st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def status_bar():
    if st.session_state.get("flash_msg"):
        st.toast(st.session_state["flash_msg"])
        st.markdown(
            f"<div class='card' style='padding:10px 12px; margin-bottom:10px; border-left:6px solid #69c27a'><b>{st.session_state['flash_msg']}</b></div>",
            unsafe_allow_html=True,
        )
        st.session_state["flash_msg"] = ""

    gid = st.session_state.get("group_id", "")
    handle = st.session_state.get("handle_norm", "")
    disp = st.session_state.get("user_disp", "")
    role = st.session_state.get("role","user")
    fs = "接続済み" if FIRESTORE_ENABLED else "未接続"
    st.markdown('<div class="card" style="padding:8px 12px; margin-bottom:10px">', unsafe_allow_html=True)
    st.markdown(f"<div class='tip'>ログイン中：{disp or handle or '—'} / ロール：{role} / データ共有：{fs}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ================== ログイン / 登録 ==================
def login_register_ui() -> bool:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🌙 With You")
    st.caption("気持ちを整える、やさしいノート。")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("はじめての人（登録）", use_container_width=True, key="btn_reg"):
            st.session_state.mode = "REGISTER"
    with c2:
        if st.button("前に登録した人（ログイン）", use_container_width=True, key="btn_login"):
            st.session_state.mode = "LOGIN"

    st.divider()
    st.markdown("**ご自由にパスワードを設定ください**")
    group_pw = st.text_input("パスワード", key="inp_group_pw", label_visibility="collapsed", placeholder="例：sakura2025")
    st.markdown("**ご自身のニックネーム（4〜12文字）**")
    st.caption("同じ名前は1人だけ使えます（先着）。英数字・ひらがな・カタカナ・漢字と _ - が使えます。")
    handle_raw = st.text_input("自分だけの名前", key="inp_handle", label_visibility="collapsed", placeholder="例：mika / ねこ_3 / sora")

    err = ""
    ok_handle, handle_norm = validate_handle(handle_raw)
    if (group_pw or "").strip() == "":
        err = "パスワードを入力してください。"
    elif not ok_handle:
        err = handle_norm  # エラーメッセージ

    mode = st.session_state.mode
    btn_label = "登録してはじめる" if mode == "REGISTER" else "入る"
    disabled = (err != "")
    if st.button(btn_label, type="primary", use_container_width=True, disabled=disabled, key="btn_go"):
        gid = group_id_from_password(group_pw)
        st.session_state.group_id = gid
        st.session_state.handle_norm = handle_norm
        st.session_state.user_disp = handle_norm

        # 管理者判定（normalize して完全一致）
        entered = unicodedata.normalize("NFKC", group_pw or "").strip()
        master  = unicodedata.normalize("NFKC", ADMIN_MASTER_CODE or "").strip()
        st.session_state.role = "admin" if entered == master else "user"

        if mode == "REGISTER":
            ok, msg = db_create_user(gid, handle_norm)
            if not ok:
                st.error(msg); st.stop()
            st.session_state.auth_ok = True
            st.session_state.view = "HOME"
            st.session_state.flash_msg = "登録が完了しました。ようこそ！"
            st.rerun()
        else:
            if not db_user_exists(gid, handle_norm):
                st.error("まだ登録がありません。「はじめての人（登録）」から設定してください。"); st.stop()
            db_touch_login(gid, handle_norm)
            st.session_state.auth_ok = True
            st.session_state.view = "HOME"
            st.session_state.flash_msg = "ログインしました。"
            st.rerun()

    if err:
        st.caption(f"⚠️ {err}")

    st.markdown("</div>", unsafe_allow_html=True)
    return False

def logout_btn():
    with st.sidebar:
        if st.button("🚪 ログアウト", key="logout_btn"):
            keep = {"mode": st.session_state.get("mode","LOGIN")}
            st.session_state.clear()
            st.session_state.update(keep)
            st.rerun()

# ================== HOME / 機能UI ==================
def home_intro():
    st.markdown("""
<div class="card" style="margin-bottom:12px">
  <div style="font-weight:900; font-size:1.05rem; margin-bottom:.3rem">🌙 With You</div>
  <div style="color:#3a4a6a; line-height:1.65; white-space:pre-wrap">
気持ちを整理したい日も、誰かに話したい日も。
With You は、あなたの心のそばにある、小さなツールボックスです。

今の自分に合うカードを選んで、少しずつ整える時間をつくってみてください。

🔒 「今日を伝える」と「相談する」だけが運営に届きます。
それ以外の記録は、すべてあなたの端末だけに残ります。
  </div>
</div>
""", unsafe_allow_html=True)

def big_button(title: str, sub: str, to_view: str, key: str, emoji: str):
    label = f"{emoji} {title}\n{sub}"
    st.markdown('<div class="bigbtn">', unsafe_allow_html=True)
    if st.button(label, key=f"home_{key}"):
        st.session_state.view = to_view; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def view_home():
    home_intro()
    big_button("今日を伝える", "今日の体調や気分を先生・学校に共有します。", "SHARE", "share", "🏫")
    c1, c2 = st.columns(2)
    with c1: big_button("リラックス", "90秒の呼吸で、いまを落ち着ける。", "SESSION", "session", "🌙")
    with c2: big_button("心を整えるノート", "感じたことを言葉にして、今の自分を整理します。", "NOTE", "note", "📝")
    c3, c4 = st.columns(2)
    with c3: big_button("Study Tracker", "学習時間を見える化。", "STUDY", "study", "📚")
    with c4: big_button("ふりかえり", "この端末に残した記録をまとめて確認。", "REVIEW", "review", "📒")
    big_button("相談する", "匿名OK。困りごとがあれば短くでも。", "CONSULT", "consult", "🕊")

# ----- リラックス（呼吸） -----
BREATH_PATTERN = (5, 2, 6)  # 5-2-6

def breathing_animation(total_sec: int = 90):
    """円は1つのみ。カウントダウンは円の下。実行終了時に rerun してボタン復帰。"""
    st.session_state["_breath_running"] = True

    inhale, hold, exhale = BREATH_PATTERN
    cycle = inhale + hold + exhale
    cycles = max(1, round(total_sec / cycle))

    circle_area = st.empty()
    phase_area = st.empty()
    countdown_area = st.empty()
    stop_area = st.empty()

    # 円（1つだけ）
    circle_area.markdown(
        """
<div style="display:flex;justify-content:center;align-items:center;padding:8px 0 6px">
  <div class="breath-spot" style="width:260px;height:260px"></div>
</div>
""",
        unsafe_allow_html=True,
    )

    def set_countdown(sec: int, label: str = ""):
        countdown_area.markdown(
            f"""
<div style="text-align:center;font-size:1.05rem;color:#3a4a6a;">
  {label} のこり <b>{sec}</b> 秒
</div>
""",
            unsafe_allow_html=True,
        )

    # 停止ボタン
    with stop_area.container():
        cols = st.columns([1, 1, 1])
        with cols[1]:
            st.button(
                "⏹ 停止する",
                key="breath_stop_btn",
                on_click=lambda: st.session_state.update({"_breath_stop": True}),
                use_container_width=True,
            )

    try:
        for _ in range(cycles):
            for label, seconds in [("吸ってください", inhale), ("止めてください", hold), ("吐いてください", exhale)]:
                if seconds <= 0:
                    continue
                phase_area.markdown(f"**{label}**")
                for remain in range(seconds, 0, -1):
                    if st.session_state.get("_breath_stop") or st.session_state.view != "SESSION":
                        return
                    set_countdown(remain, label)
                    time.sleep(1)
    finally:
        phase_area.empty(); countdown_area.empty(); stop_area.empty(); circle_area.empty()
        st.session_state["_breath_running"] = False
        st.session_state["_breath_stop"] = False
        st.session_state["_breath_finished"] = True
        st.rerun()

def view_session():
    st.markdown("### 🌙 リラックス（呼吸）")
    st.caption("円が大きくなったら吸って、小さくなったら吐きます。途中で停止・ページ移動できます。")

    total_seconds = 90
    inhale, hold, exhale = BREATH_PATTERN

    running = st.session_state.get("_breath_running", False)
    finished = st.session_state.pop("_breath_finished", False)
    if finished:
        st.success("お疲れさまでした。ありがとうございます。")

    if not running:
        cols = st.columns([1, 1, 1])
        with cols[1]:
            if st.button("🫁 はじめる（90秒）", key="breath_start", type="primary", use_container_width=True):
                st.session_state["_breath_stop"] = False
                st.session_state["_breath_running"] = True
                st.rerun()
    else:
        breathing_animation(total_seconds)

    st.caption(f"パターン：{inhale}-{hold}-{exhale}／合計 {total_seconds} 秒")

    st.divider()
    after = st.slider("いまの気分（1 とてもつらい / 10 とても楽）", 1, 10, 5, key="breath_mood_after")

    if st.button("💾 端末に保存（このセッション内）", type="primary", key="breath_save"):
        st.session_state["_local_logs"]["breath"].append({
            "ts": now_iso(), "pattern": "5-2-6", "mood_after": int(after), "sec": total_seconds
        })
        st.success("保存しました。（運営には共有されません）")

# ----- ノート（ローカル保存） -----
MOODS = [
    {"emoji":"😢","label":"悲しい","key":"sad"},
    {"emoji":"😠","label":"イライラ","key":"anger"},
    {"emoji":"😟","label":"不安","key":"anx"},
    {"emoji":"😔","label":"さみしい","key":"lonely"},
    {"emoji":"😩","label":"しんどい","key":"tired"},
    {"emoji":"😕","label":"モヤモヤ","key":"confuse"},
]

def cbt_intro_block():
    st.markdown("""
<div class="cbt-card">
  <div class="cbt-heading">このワークについて</div>
  <div class="cbt-sub" style="white-space:pre-wrap">
このノートは、認知行動療法（CBT）という考え方をもとにしています。
「気持ち」と「考え方」を整理することで、
今感じている不安やしんどさを感じたとき、その心が少し軽くなることを目指しています。
自分のペースで、思いつくことを自由に書いてみてください。
  </div>
</div>
""", unsafe_allow_html=True)

def cbt_intro():
    return cbt_intro_block()

def mood_radio() -> Dict[str, Any]:
    st.markdown('<div class="cbt-card">', unsafe_allow_html=True)
    st.markdown('<div class="cbt-heading">🌤 Step 1：今の気持ちは？</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for i, m in enumerate(MOODS):
        with cols[i % 4]:
            if st.button(f"{m['emoji']} {m['label']}", key=f"cbt_btn_mood_{m['key']}"):
                st.session_state["cbt_mood_key"] = m["key"]
                st.session_state["cbt_mood_label"] = m["label"]
                st.session_state["cbt_mood_emoji"] = m["emoji"]
    sel = st.session_state.get("cbt_mood_label", "未選択")
    st.write(f"選択中：**{st.session_state.get('cbt_mood_emoji','')} {sel}**")
    intensity = st.slider("今の強さ（0〜100）", 0, 100, 60, key="cbt_intensity")
    st.markdown("</div>", unsafe_allow_html=True)
    return {
        "key": st.session_state.get("cbt_mood_key"),
        "label": st.session_state.get("cbt_mood_label"),
        "emoji": st.session_state.get("cbt_mood_emoji"),
        "intensity": intensity
    }

def text_card(title: str, subtext: str, key: str, height=120, placeholder="ここに書いてみてね") -> str:
    st.markdown('<div class="cbt-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="cbt-heading">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cbt-sub">{subtext}</div>', unsafe_allow_html=True)
    val = st.text_area("", height=height, key=key, placeholder=placeholder, label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)
    return val

ACTION_CATEGORIES_EMOJI = { "身体": "🫧","環境": "🌤","リズム": "⏯️","つながり": "💬" }
ACTION_CATEGORIES = {
    "身体": ["顔や手を洗う","深呼吸をする","肩を回す","シャワーを浴びる"],
    "環境": ["窓を開けて外の空気を感じる","カーテンを開けて部屋を明るくする","空をながめる"],
    "リズム": ["水を飲む","温かい飲み物を飲む","立ち上がって少し歩く","外を少し歩く"],
    "つながり": ["スタンプを送る","「ありがとう」を書く","家族や友達に一言だけ話す"],
}
def _flat_action_options_emoji():
    order = ["身体","環境","リズム","つながり"]
    seen, disp, vals = set(), [], []
    for cat in order:
        for a in ACTION_CATEGORIES.get(cat, []):
            if a in seen: continue
            seen.add(a); disp.append(f"{ACTION_CATEGORIES_EMOJI[cat]} {a}"); vals.append(a)
    return disp, vals

def action_picker(mood_key: Optional[str]):
    st.markdown('<div class="cbt-card">', unsafe_allow_html=True)
    st.markdown('<div class="cbt-heading">🌸 Step 6：今できそうなことは？</div>', unsafe_allow_html=True)
    st.markdown('<div class="cbt-sub">ぴったりを1つだけ。選ばなくてもOKだよ。</div>', unsafe_allow_html=True)
    disp, vals = _flat_action_options_emoji()
    options_disp = disp + ["— 選ばない —"]
    key_pick = f"act_pick_single_{(mood_key or 'default').strip().lower()}"
    sel_disp = st.selectbox("小さな行動（任意）", options=options_disp, index=len(options_disp)-1, key=key_pick)
    chosen = "" if sel_disp == "— 選ばない —" else vals[disp.index(sel_disp)]
    custom_key = f"act_custom_single_{(mood_key or 'default').strip().lower()}"
    custom = st.text_input("＋ 自分の言葉で書く（任意）", key=custom_key, placeholder="例：窓を開けて深呼吸する").strip()
    st.markdown("</div>", unsafe_allow_html=True)
    if custom: return "", custom
    return (chosen or ""), ""

def view_note():
    st.markdown("### 📝 心を整えるノート")
    cbt_intro()

    mood = mood_radio()
    trigger_text   = text_card("🫧 Step 2：その気持ちは、どんなことがきっかけだった？", "「○○があったからかも」「なんとなく○○って思ったから」など自由に。", "cbt_trigger")
    auto_thought   = text_card("💭 Step 3：そのとき、頭の中でどんな言葉がよぎった？", "心の中でつぶやいた言葉やイメージをそのまま書いてOK。", "cbt_auto")
    reason_for     = text_card("🔎 Step 4：そう思った理由は？", "心の中の“根拠”を書いてみよう。", "cbt_for", height=100)
    reason_against = text_card("🔍 Step 5：そうでもないかもと思う理由はある？", "「でも、こういう面もあるかも」も書いてみよう。", "cbt_against", height=100)
    alt_perspective= text_card("🌱 Step 6：もし友だちが同じことを感じていたら、なんて声をかける？", "自分のことじゃなく“友だち”のこととして考えてみよう。", "cbt_alt")
    act_suggested, act_custom = action_picker(mood.get("key"))
    reflection     = text_card("🌙 Step 7：今日の日記", "気づいたこと・気持ちの変化・これからのことなど自由に。", "cbt_reflect", height=120)

    if st.button("💾 記録（この端末）", type="primary", key="cbt_save"):
        doc = {
            "ts": now_iso(),
            "mood": mood,
            "trigger": (trigger_text or "").strip(),
            "auto": (auto_thought or "").strip(),
            "reason_for": (reason_for or "").strip(),
            "reason_against": (reason_against or "").strip(),
            "alt_perspective": (alt_perspective or "").strip(),
            "action": {"suggested": act_suggested, "custom": act_custom},
            "diary": (reflection or "").strip(),
        }
        st.session_state["_local_logs"]["note"].append(doc)
        st.success("保存しました。（運営には共有されません）")
        st.download_button(
            "⬇️ この記録をダウンロード（JSON）",
            data=json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name=f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            key=f"dl_note_{len(st.session_state['_local_logs']['note'])}"
        )

# ----- 今日を伝える（Firestoreに匿名共有） -----
def view_share():
    st.markdown("### 🏫 今日を伝える（匿名）")
    mood = st.radio("気分", ["🙂","😐","😟"], index=1, horizontal=True, key="share_mood")
    body_opts = ["頭痛","腹痛","吐き気","食欲低下","だるさ","その他","なし"]
    body = st.multiselect("体調（当てはまるもの）", body_opts, default=["なし"], key="share_body")
    if "なし" in body and len(body) > 1:
        body = [b for b in body if b != "なし"]
    c1, c2 = st.columns(2)
    with c1: sleep_h = st.number_input("睡眠時間（h）", min_value=0.0, max_value=24.0, value=6.0, step=0.5, key="share_sleep_h")
    with c2: sleep_q = st.radio("睡眠の質", ["ぐっすり","ふつう","浅い"], index=1, horizontal=True, key="share_sleep_q")

    disabled = not FIRESTORE_ENABLED
    label = "📨 先生に送る" if FIRESTORE_ENABLED else "📨 送信（未接続）"
        # 送信ボタン
        # 送信ボタン
    if st.button(label, type="primary", disabled=disabled, key="share_send"):
        gid = st.session_state.get("group_id", "")
        hdl = st.session_state.get("handle_norm", "")

        # ---- 追加：管理画面用フラグ ----
        low_mood = (mood == "😟")
        short_sleep = (float(sleep_h) < 5)
        body_any = any(b != "なし" for b in body)

        ok = safe_db_add("school_share", {
            "ts": datetime.now(timezone.utc),
            "group_id": gid,
            "handle": hdl,
            "user_key": user_key(gid, hdl) if (gid and hdl) else "",

            # 元のpayloadはそのまま
            "payload": {
                "mood": mood,
                "body": body,
                "sleep_hours": float(sleep_h),
                "sleep_quality": sleep_q
            },

            # ---- 新規追加：管理画面向けデータ ----
            "flags": {
                "low_mood": low_mood,
                "short_sleep": short_sleep,
                "body_any": body_any,
            },

            "anonymous": True
        })

        if ok:
            st.session_state.flash_msg = "「今日を伝える」を送信しました。ありがとうございます。"
            st.rerun()
        else:
            st.error("送信できませんでした。")



# ----- 相談（Firestoreに匿名送信） -----
CONSULT_TOPICS = ["体調","勉強","人間関係","家庭","進路","いじめ","メンタルの不調","その他"]
def view_consult():
    st.markdown("### 🕊 相談（匿名OK）")
    st.caption("誰にも言いにくいことでも大丈夫。お名前は空欄のまま送れます。")
    to_whom = st.radio("相談先", ["カウンセラーに相談したい","先生に伝えたい"], horizontal=True, key="c_to")
    topics  = st.multiselect("内容（当てはまるもの）", CONSULT_TOPICS, default=[], key="c_topics")
    anonymous = st.checkbox("匿名で送る", value=True, key="c_anon")
    name = "" if anonymous else st.text_input("お名前（任意）", value="", key="c_name")
    msg = st.text_area("ご相談内容", height=220, value="", key="c_msg")

    disabled = not FIRESTORE_ENABLED or (msg.strip()=="")
    label = "🕊 送信する" if FIRESTORE_ENABLED else "🕊 送信（未接続）"
    if st.button(label, type="primary", disabled=disabled, key="c_send"):
        gid = st.session_state.get("group_id","")
        hdl = st.session_state.get("handle_norm","")
        priority = classify_priority_by_message(msg.strip())

payload = {
    "ts": datetime.now(timezone.utc),
    "group_id": gid,
    "handle": hdl,
    "user_key": user_key(gid, hdl) if (gid and hdl) else "",
    "message": msg.strip(),
    "topics": topics,
    "intent": "counselor" if to_whom.startswith("カウンセラー") else "teacher",
    "anonymous": bool(anonymous),
    "name": name.strip() if (not anonymous and name) else "",

    # ---- 追加：管理画面が使う相談優先度 ----
    "priority": priority
}

ok = safe_db_add("consult_msgs", payload)

        if ok:
            st.session_state.flash_msg = "相談を送信しました。ありがとうございます。"
            for k in ["c_topics","c_msg","c_name","c_anon","c_to"]:
                if k in st.session_state: del st.session_state[k]
            st.rerun()
        else:
            st.error("送信できませんでした。")

# ----- Study（ローカル保存） -----
def view_study():
    st.markdown("### 📚 Study Tracker")
    subjects_default = ["国語","数学","英語","理科","社会","音楽","美術","情報","その他"]
    subj = st.selectbox("科目", subjects_default, index=0, key="study_subj")
    add  = st.text_input("＋ 自分の科目を追加（Enter）", key="study_add")
    if add.strip(): subj = add.strip()
    mins = st.number_input("学習時間（分）", 1, 600, 30, 5, key="study_min")
    mood = st.selectbox("状況", ["順調","難航","しんどい","集中","だるい","眠い","その他"], index=0, key="study_mood")
    memo = st.text_input("メモ（任意）", key="study_memo")
    if st.button("💾 記録（端末）", type="primary", key="study_save"):
        rec = {"ts": now_iso(), "subject": subj, "minutes": int(mins), "mood": mood, "memo": memo}
        st.session_state["_local_logs"]["study"].append(rec)
        st.success("保存しました。（運営には共有されません）")

# ----- ふりかえり（ローカル） -----
def view_review():
    st.markdown("### 📒 ふりかえり（このセッションの履歴）")
    logs = st.session_state["_local_logs"]
    if any(len(v)>0 for v in logs.values()):
        all_json = json.dumps(logs, ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button("⬇️ このセッションの全記録（JSON）", data=all_json,
                           file_name=f"withyou_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                           mime="application/json", key="review_dl_all")
    tabs = st.tabs(["ノート","呼吸","Study"])
    with tabs[0]:
        notes = list(reversed(logs["note"]))
        if not notes: st.caption("まだ記録がありません。")
        else:
            for r in notes:
                st.markdown(f"""
<div class="item">
  <div class="meta">{r['ts']}</div>
  <div style="font-weight:900; color:#24466e; margin-bottom:.2rem">{r['mood'].get('emoji','')} {r['mood'].get('label','')}</div>
  <div style="white-space:pre-wrap; margin-bottom:.3rem">きっかけ：{r.get('trigger','')}</div>
  <div style="white-space:pre-wrap; margin-bottom:.3rem">よぎった言葉：{r.get('auto','')}</div>
  <div style="white-space:pre-wrap; margin-bottom:.3rem">日記：{r.get('diary','')}</div>
</div>
""", unsafe_allow_html=True)
    with tabs[1]:
        breaths = list(reversed(logs["breath"]))
        if not breaths: st.caption("まだ記録がありません。")
        else:
            for r in breaths:
                st.markdown(f"""
<div class="item">
  <div class="meta">{r['ts']}</div>
  <div>パターン：{r.get('pattern','5-2-6')} / 実施：{r.get('sec',90)}秒</div>
  <div>終了時の気分：{r.get('mood_after','')}</div>
</div>
""", unsafe_allow_html=True)
    with tabs[2]:
        studies = list(reversed(logs["study"]))
        if not studies: st.caption("まだ記録がありません。")
        else:
            df = pd.DataFrame(studies)
            pie_agg = df.groupby("subject")["minutes"].sum().reset_index().sort_values("minutes", ascending=False)
            if not pie_agg.empty:
                pie = (alt.Chart(pie_agg).mark_arc(innerRadius=60).encode(
                        theta=alt.Theta(field="minutes", type="quantitative"),
                        color=alt.Color(field="subject", type="nominal", legend=alt.Legend(title="科目")),
                        tooltip=[alt.Tooltip("subject:N", title="科目"), alt.Tooltip("minutes:Q", title="合計分")]
                    ).properties(width=340, height=340))
                st.altair_chart(pie, use_container_width=False)
            for _, r in df.sort_values("ts", ascending=False).iterrows():
                st.markdown(f"""
<div class="item">
  <div class="meta">{r['ts']}</div>
  <div style="font-weight:900">{r['subject']}</div>
  <div>分：{int(r['minutes'])} / 状況：{r.get('mood','')}</div>
  <div style="white-space:pre-wrap; color:#3b4f71; margin-top:.3rem">{r.get('memo','')}</div>
</div>
""", unsafe_allow_html=True)

# ================== 運営（ADMIN） — 学校導入ダッシュボード ==================
def view_admin():
    st.markdown("### 🛠 運営ダッシュボード")
    if not FIRESTORE_ENABLED:
        st.error("Firestore未接続です。st.secretsの設定を確認してください。")
        return

    scope = st.radio("表示範囲", ["このパスワードのグループだけ", "全グループ"], horizontal=True, key="adm_scope")
    gid_filter = st.session_state.get("group_id","") if scope.startswith("この") else None

    tabs = st.tabs(["📅 週報サマリー", "🏫 クラス/学年（匿名）", "🕊 相談・チケット", "⚙️ 設定"])

    # ---------- 週報サマリー ----------
    with tabs[0]:
        rows_share = fetch_rows_cached("school_share", gid_filter, days=60)
        rows_cons  = fetch_rows_cached("consult_msgs", gid_filter, days=60)

        ranges = week_ranges(2)  # [(今週s,e), (先週s,e)]
        def in_range(ts: datetime, r: Tuple[datetime, datetime]) -> bool:
            return isinstance(ts, datetime) and (r[0] <= ts < r[1])

        def summarize(rng: Tuple[datetime, datetime]) -> dict:
            share = [r for r in rows_share if in_range(r.get("ts"), rng)]
            cons  = [r for r in rows_cons  if in_range(r.get("ts"), rng)]

            total = len(share)
            low_mood = sum(1 for r in share if payload_series(r, "mood") == "😟")
            body_any = sum(1 for r in share if any((payload_series(r, "body", []) or []) and (b!="なし" for b in payload_series(r,"body",[]))))
            sleep_vals = [float(payload_series(r,"sleep_hours",0.0) or 0.0) for r in share if isinstance(payload_series(r,"sleep_hours",None),(int,float))]
            avg_sleep = round(sum(sleep_vals)/len(sleep_vals),1) if sleep_vals else None

            pr_counts = {"urgent":0,"medium":0,"low":0}
            for c in cons:
                pr = classify_priority_by_message(c.get("message",""))
                pr_counts[pr] = pr_counts.get(pr,0)+1

            # リスク指数（0-100）：自殺念慮リスク含む構造的シグナル
            risk_index = compute_risk_index(share, cons)

            return {
                "records": total,
                "low_mood_rate": (low_mood/total*100) if total else 0.0,
                "body_any_rate": (body_any/total*100) if total else 0.0,
                "avg_sleep": avg_sleep,
                "consult_total": len(cons),
                "pr_urgent": pr_counts["urgent"],
                "pr_medium": pr_counts["medium"],
                "pr_low": pr_counts["low"],
                "risk_index": risk_index,
            }

        cur = summarize(ranges[0])
        prev = summarize(ranges[1])

        def delta(a, b):
            if b is None or a is None: return None
            return round(a-b,1)

        st.markdown("#### 今週の要点（自動要約）")
        bullet = []
        if cur["low_mood_rate"] is not None:
            d = delta(cur["low_mood_rate"], prev["low_mood_rate"])
            if d is not None:
                trend = "増加" if d>0 else "減少"
                bullet.append(f"低気分の割合：{cur['low_mood_rate']:.1f}%（先週比 {d:+.1f}pt {trend}）")
        if cur["avg_sleep"] is not None and prev["avg_sleep"] is not None:
            d = delta(cur["avg_sleep"], prev["avg_sleep"])
            trend = "短い" if d<0 else "長い"
            bullet.append(f"平均睡眠：{cur['avg_sleep']:.1f}h（先週比 {d:+.1f}h、今週の方が{trend}傾向）")
        bullet.append(f"相談件数：{cur['consult_total']}（緊急 {cur['pr_urgent']} / 中 {cur['pr_medium']} / 低 {cur['pr_low']}）")

        d_risk = delta(cur["risk_index"], prev["risk_index"])
        if d_risk is not None:
            trend = "上昇" if d_risk>0 else "低下"
            bullet.append(f"推定リスク指数：{cur['risk_index']:.1f}（先週比 {d_risk:+.1f}pt {trend}）")

        # Lead Time（対応までの日数）
        lt = compute_leadtime_metrics(gid_filter, days=60)
        if lt["n_closed"] > 0 and lt["avg_days"] is not None:
            bullet.append(f"対応完了チケット {lt['n_closed']} 件の平均リードタイム：{lt['avg_days']} 日")

        if bullet:
            st.markdown("- " + "\n- ".join(bullet))
        else:
            st.caption("直近2週間のデータが不足しています。")

        # 日次低気分率＋EMA的変動指標
        def day_df(rows):
            data = []
            for r in rows:
                ts = r.get("ts")
                if not isinstance(ts, datetime): continue
                p = r.get("payload",{}) or {}
                data.append({
                    "ts": ts,
                    "mood": p.get("mood"),
                    "sleep_hours": p.get("sleep_hours"),
                })
            if not data: return pd.DataFrame()
            df = pd.DataFrame(data)
            df["day"] = df["ts"].dt.tz_convert(None).dt.date
            df["low"] = (df["mood"]=="😟").astype(int)
            agg = df.groupby("day").agg(records=("mood","count"), low=("low","sum")).reset_index()
            agg["low_rate"] = (agg["low"]/agg["records"]*100).round(1)
            return df, agg

        raw_df, daily = (pd.DataFrame(), pd.DataFrame())
        if rows_share:
            raw_df, daily = day_df(rows_share)

        if not daily.empty:
            ch = alt.Chart(daily).mark_line().encode(
                x=alt.X("day:T", title="日付"),
                y=alt.Y("low_rate:Q", title="低気分率(%)"),
                tooltip=["day:T","low_rate:Q","records:Q"]
            ).properties(height=260)
            st.altair_chart(ch, use_container_width=True)
        else:
            st.caption("低気分率のグラフ表示できるデータがまだありません。")

        st.divider()
        st.markdown("#### EMA的な変動（気分・睡眠）")

        if not raw_df.empty:
            ema = compute_daily_ema(raw_df)
            if not ema.empty:
                c1, c2 = st.columns(2)
                with c1:
                    ch1 = alt.Chart(ema).mark_line().encode(
                        x=alt.X("day:T", title="日付"),
                        y=alt.Y("mood_score:Q", title="平均気分スコア(0=良〜2=低)")
                    ).properties(height=220)
                    st.altair_chart(ch1, use_container_width=True)
                with c2:
                    ch2 = alt.Chart(ema).mark_line().encode(
                        x=alt.X("day:T", title="日付"),
                        y=alt.Y("mood_var_7d:Q", title="7日間の気分変動(分散)")
                    ).properties(height=220)
                    st.altair_chart(ch2, use_container_width=True)
            else:
                st.caption("変動指標を計算できるだけのデータがまだありません。")
        else:
            st.caption("EMA的指標を計算するデータがまだありません。")

    # ---------- クラス/学年（匿名） ----------
    with tabs[1]:
        st.markdown("#### クラス/学年の傾向（匿名・個人名なし）")
        rows_share = fetch_rows_cached("school_share", gid_filter, days=30)
        if rows_share:
            df = pd.DataFrame([{
                "ts": r.get("ts"),
                "class_id": r.get("group_id",""),
                "mood": payload_series(r,"mood"),
                "sleep": payload_series(r,"sleep_hours", None),
                "body_any": int(any((payload_series(r,"body",[]) or []) and (b!="なし" for b in payload_series(r,"body",[]))))
            } for r in rows_share if isinstance(r.get("ts"), datetime)])
            if df.empty:
                st.caption("データがありません。")
            else:
                df["date"] = df["ts"].dt.tz_convert(None).dt.date
                agg = df.groupby(["class_id","date"]).agg(
                    n=("mood","count"),
                    low=("mood", lambda x: (x=="😟").sum()),
                    body_any=("body_any","sum"),
                    sleep_avg=("sleep", "mean")
                ).reset_index()
                agg["low_rate"] = (agg["low"]/agg["n"]*100).round(1)
                agg["body_rate"] = (agg["body_any"]/agg["n"]*100).round(1)

                st.caption("低気分率ヒートマップ（濃い＝割合高）")
                heat = agg.pivot_table(index="class_id", columns="date", values="low_rate")
                st.dataframe(heat.fillna(""), use_container_width=True)

                st.caption("クラス別の平均睡眠（直近30日）")
                sleep = agg.groupby("class_id")["sleep_avg"].mean().reset_index().dropna()
                if not sleep.empty:
                    bar = alt.Chart(sleep).mark_bar().encode(
                        x=alt.X("class_id:N", title="クラス（=group_id相当）"),
                        y=alt.Y("sleep_avg:Q", title="平均睡眠(h)")
                    ).properties(height=260)
                    st.altair_chart(bar, use_container_width=True)
        else:
            st.caption("データがありません。")

    # ---------- 相談・チケット ----------
    with tabs[2]:
        st.markdown("#### 相談（匿名） → チケット化して分担")
        rows_cons  = fetch_rows_cached("consult_msgs", gid_filter, days=60)
        if rows_cons:
            df = pd.DataFrame([{
                "id": r.get("_id",""),
                "時刻": r.get("ts"),
                "匿名": r.get("anonymous", True),
                "宛先": r.get("intent",""),
                "内容": r.get("message",""),
                "優先度": classify_priority_by_message(r.get("message","")),
                "トピック": ",".join(r.get("topics",[]) or []),
                "group_id": r.get("group_id",""),
                "handle": r.get("handle","")
            } for r in rows_cons if isinstance(r.get("ts"), datetime)])
            df = df.sort_values("時刻", ascending=False)
            st.dataframe(df.drop(columns=["id","group_id","handle"]), use_container_width=True, hide_index=True)

            st.divider()
            st.caption("⚡ 優先度別 件数")
            cnt = df.groupby("優先度").size().reset_index(name="件数")
            st.dataframe(cnt, use_container_width=True, hide_index=True)

            st.divider()
            st.caption("チケット起票（MVP：相談1件→1チケット）")
            if st.button("最新50件を一括でチケット起票（重複防止付き）", key="mk_tickets", type="primary"):
                okn = 0
                for _, row in df.head(50).iterrows():
                    rid = hmac_sha256_hex(APP_SECRET, f"{row['時刻']}_ticket_{row['handle']}")
                    q = DB.collection("tickets").where("rid","==",rid).limit(1).stream()
                    exists = any(True for _ in q)
                    if exists: continue
                    DB.collection("tickets").add({
                        "rid": rid,
                        "created_at": row["時刻"] if isinstance(row["時刻"], datetime) else datetime.now(timezone.utc),
                        "group_id": row["group_id"],
                        "priority": row["優先度"],
                        "status": "open",
                        "intent": row["宛先"],
                        "topics": row["トピック"].split(",") if row["トピック"] else [],
                        "note_head": (row["内容"][:120] + "...") if isinstance(row["内容"], str) and len(row["内容"])>120 else row["内容"],
                    })
                    okn += 1
                st.success(f"チケット起票：{okn}件")
        else:
            st.caption("相談データがありません。")

        st.divider()
        st.markdown("#### チケット一覧（直近100）")
        try:
            docs = list(DB.collection("tickets").order_by("created_at", direction="DESCENDING").limit(100).stream()) if FIRESTORE_ENABLED else []
            rows = [{"id": d.id, **d.to_dict()} for d in docs]
        except Exception:
            rows = []
        if rows:
            tdf = pd.DataFrame([{
                "id": r.get("id"),
                "作成": r.get("created_at"),
                "優先度": r.get("priority",""),
                "状態": r.get("status",""),
                "宛先": r.get("intent",""),
                "要約": r.get("note_head",""),
            } for r in rows])
            st.dataframe(tdf.drop(columns=["id"]), use_container_width=True, hide_index=True)

            st.caption("対応完了にしたいチケットを選んでください。")
            open_ids = [r["id"] for r in rows if r.get("status") != "closed"]
            if open_ids:
                sel_id = st.selectbox("チケットID（内部用）", options=["選択しない"]+open_ids, key="ticket_close_sel")
                if sel_id != "選択しない":
                    if st.button("✅ 対応完了として記録", key="ticket_close_btn"):
                        try:
                            DB.collection("tickets").document(sel_id).set({
                                "status": "closed",
                                "closed_at": datetime.now(timezone.utc),
                            }, merge=True)
                            st.success("対応完了として記録しました。（Lead Time 指標に反映されます）")
                            st.rerun()
                        except Exception as e:
                            st.error(f"更新に失敗しました: {e}")
            else:
                st.caption("未対応のチケットはありません。")
        else:
            st.caption("チケットがありません。")

    # ---------- 設定 ----------
    with tabs[3]:
        st.caption("既定は“個人名なし・匿名統計のみ”。ここではアラート閾値や週報の曜日を調整します（MVP：セッション内設定）。")
        st.session_state.setdefault("_adm_alert_delta", 25)
        st.session_state.setdefault("_adm_weekday", "金")
        col1, col2 = st.columns(2)
        with col1:
            st.session_state["_adm_alert_delta"] = st.slider("変化率アラート閾値（％）", 10, 60, st.session_state["_adm_alert_delta"], 1)
        with col2:
            st.session_state["_adm_weekday"] = st.selectbox("週報の作成曜日", ["月","火","水","木","金"], index=["月","火","水","木","金"].index(st.session_state["_adm_weekday"]))
        st.markdown(f"<div class='small'>現在値：変化率 {st.session_state['_adm_alert_delta']}％ / 週報 {st.session_state['_adm_weekday']}曜</div>", unsafe_allow_html=True)
        st.markdown("<div class='small'>※ 将来的には、ここで介入内容（例：HRでの呼吸ワーク実施など）も記録し、EBPMとしての因果推定に活用します。</div>", unsafe_allow_html=True)

# ================== ルーター ==================
def main_router():
    v = st.session_state.view
    if v == "HOME":     view_home()
    elif v == "SHARE":  view_share()
    elif v == "SESSION":view_session()
    elif v == "NOTE":   view_note()
    elif v == "STUDY":  view_study()
    elif v == "REVIEW": view_review()
    elif v == "CONSULT":view_consult()
    elif v == "ADMIN":  view_admin()
    else:               view_home()
    return None

# ================== アプリ起動 ==================
if st.session_state.get("auth_ok", False):
    logout_btn()
    status_bar()
    top_tabs()
    main_router()
else:
    login_register_ui()
