# app.py — With You.（学校導入版・生徒側UI）【北欧メディテーション風 v3】
# 管理者側ダッシュボード（with-you-admin-ui）と連携する改良版
# 
# 【主な変更点 v3】
# 1. 🌿 北欧メディテーション風デザインへ全面刷新
# 2. 📚 Study Tracker機能を大幅強化（目標設定・進捗管理）
# 3. 🌬 呼吸ワークを白い息のような柔らかい表現に
# 4. 💬 言葉を「観察と許し」のトーンに変更
# 5. 🎨 色・動き・形すべてを北欧の静けさに統一

from __future__ import annotations
from datetime import datetime, timezone, timedelta, date
from typing import Dict, Tuple, List, Optional, Any
import streamlit as st
import pandas as pd
import altair as alt
import hashlib, hmac, unicodedata, re, json, os, time

# ================== ページ設定 ==================
st.set_page_config(
    page_title="With You.", 
    page_icon="🌿", 
    layout="centered", 
    initial_sidebar_state="collapsed"
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
            credentials=creds
        )
    DB = firestore_client()
except Exception:
    FIRESTORE_ENABLED = False
    DB = None

# ================== 運営パスワード ==================
ADMIN_MASTER_CODE = (
    st.secrets.get("ADMIN_MASTER_CODE")
    or os.environ.get("ADMIN_MASTER_CODE")
    or "uneiairi0931"
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

HANDLE_ALLOWED_RE = re.compile(r"^[a-z0-9_\-\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]+$")

def normalize_handle(s: str) -> str:
    s = (s or "").strip()
    s = unicodedata.normalize("NFKC", s)
    s = s.lower()
    return s

def validate_handle(raw: str) -> Tuple[bool, str]:
    n = normalize_handle(raw)
    if len(n) < 4 or len(n) > 12:
        return False, "4〜12文字で入力できます。"
    if not HANDLE_ALLOWED_RE.match(n):
        return False, "英数字・ひらがな・カタカナ・漢字と「_」「-」が使えます。"
    return True, n

def group_id_from_password(group_password: str) -> str:
    """グループパスワードからgroup_idを生成"""
    pw = unicodedata.normalize("NFKC", (group_password or "").strip())
    return hmac_sha256_hex(APP_SECRET, f"grp:{pw}")

def user_key(group_id: str, handle_norm: str) -> str:
    """ユーザー識別子（ハッシュ化）"""
    return sha256_hex(f"{group_id}:{handle_norm}")

# ================== クラス情報の抽出 ==================
def extract_class_info(group_password: str) -> Dict[str, str]:
    """
    グループパスワードからクラス情報を抽出
    例：「1年A組2025」→ grade="1", class_name="A"
    """
    pw = unicodedata.normalize("NFKC", (group_password or "").strip())
    match = re.search(r'(\d+)年([A-Za-zァ-ヶー]+)組', pw)
    
    if match:
        grade = match.group(1)
        class_name = match.group(2).upper()
        return {
            "grade": grade,
            "class_name": class_name,
            "class_id": f"{grade}年{class_name}組"
        }
    
    return {
        "grade": "不明",
        "class_name": "不明",
        "class_id": "クラス不明"
    }

# ================== データベース操作 ==================
def db_create_user(group_id: str, handle_norm: str, class_info: Dict[str, str]) -> Tuple[bool, str]:
    """先着専有：存在すれば失敗。クラス情報も保存"""
    if not FIRESTORE_ENABLED or DB is None:
        return False, "Firestore未接続です。"
    
    ref = DB.collection("groups").document(group_id).collection("users").document(handle_norm)
    try:
        ref.create({
            "user_key": user_key(group_id, handle_norm),
            "created_at": datetime.now(timezone.utc),
            "last_login_at": datetime.now(timezone.utc),
            "class_info": class_info,
        })
        return True, ""
    except Exception:
        return False, "この名前はすでに使われています。"

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

# ================== 気分の絵文字マッピング ==================
MOOD_EMOJI_MAP = {
    "😟": {"label": "つらい", "score": 2, "color": "#E3C9CF"},
    "😐": {"label": "ふつう", "score": 1, "color": "#CAD2BE"},
    "🙂": {"label": "まあまあ", "score": 0, "color": "#A7C7D9"},
}

def get_mood_label(emoji: str) -> str:
    """絵文字からラベルを取得"""
    return MOOD_EMOJI_MAP.get(emoji, {}).get("label", "不明")

# ================== リスク判定ロジック ==================
def classify_risk_level(message: str, mood: str, body: List[str], sleep_hours: float) -> str:
    """総合的なリスクレベルを判定"""
    if not message:
        message = ""
    
    text = message.lower()
    
    # 【最優先】自殺念慮・自傷・虐待関連のキーワード
    urgent_keywords = [
        "死にたい", "自殺", "消えたい", "死ぬ", "終わり",
        "暴力", "虐待", "いじめられ", "殴られ", "蹴られ",
        "希死", "自傷", "リストカット", "OD", "飛び降り"
    ]
    
    for kw in urgent_keywords:
        if kw in text:
            return "urgent"
    
    # 【中リスク】メンタル不調・身体症状
    medium_keywords = [
        "眠れない", "食べられない", "吐き気", "しんどい",
        "助けて", "不安", "落ち込", "つらい", "苦しい",
        "パニック", "過呼吸", "動悸"
    ]
    
    medium_count = sum(1 for kw in medium_keywords if kw in text)
    
    if mood == "😟" and body and any(b != "なし" for b in body):
        return "medium"
    
    if sleep_hours < 4.0:
        return "medium"
    
    if medium_count >= 2:
        return "medium"
    
    return "low"

# ================== 状態管理 ==================
st.session_state.setdefault("auth_ok", False)
st.session_state.setdefault("mode", "LOGIN")
st.session_state.setdefault("group_pw", "")
st.session_state.setdefault("handle_raw", "")
st.session_state.setdefault("group_id", "")
st.session_state.setdefault("handle_norm", "")
st.session_state.setdefault("user_disp", "")
st.session_state.setdefault("class_info", {})
st.session_state.setdefault("view", "HOME")
st.session_state.setdefault("flash_msg", "")
st.session_state.setdefault("role", "user")

# ローカルログ（端末保存）
st.session_state.setdefault("_local_logs", {"note":[], "breath":[], "study":[]})

# Study Tracker用の目標設定
st.session_state.setdefault("study_weekly_goal", 300)  # 週300分
st.session_state.setdefault("study_monthly_goal", 1200)  # 月1200分

# ================== スタイル【🌿 北欧メディテーション風 v3】 ==================
def inject_css():
    st.markdown("""
<style>
/* ================== 北欧メディテーション風 UI ==================
   静けさ × 温かみ × 自然のリズム
   配色：霧・湖・森・雪の自然光カラー
   動き：0.6〜0.9秒のゆっくりとしたフェード
   ================================================== */

:root {
  /* 北欧カラーパレット */
  --snow-white: #F6F7F5;
  --mist-gray: #ECEFEB;
  --nordic-blue: #E3E9F0;
  --winter-lake: #A7C7D9;
  --forest-green: #CAD2BE;
  --wood-pink: #E3C9CF;
  --deep-calm-blue: #6B7D8C;
  --moss-green: #8A9A5B;
  
  /* テキストカラー */
  --text-primary: #3D4A52;
  --text-secondary: #6B7D8C;
  --text-muted: #9AABB8;
  
  /* 極薄枠線 */
  --border-light: #DADFE3;
  
  /* 柔らかい影 */
  --shadow-soft: 0 2px 12px rgba(61, 74, 82, 0.06);
  --shadow-hover: 0 4px 20px rgba(61, 74, 82, 0.08);
}

/* ================== 全体背景（霧と光のグラデーション）================== */
html, body, .stApp {
  background: linear-gradient(
    165deg,
    var(--snow-white) 0%,
    var(--mist-gray) 35%,
    var(--nordic-blue) 70%,
    #E8EFF5 100%
  );
  color: var(--text-primary);
  min-height: 100vh;
  font-family: 'Noto Sans JP', -apple-system, BlinkMacSystemFont, sans-serif;
  font-weight: 400;
  line-height: 1.8;
}

/* かすかに漂う光粒子 */
html::before {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: 
    radial-gradient(circle at 20% 30%, rgba(167, 199, 217, 0.03) 0%, transparent 50%),
    radial-gradient(circle at 80% 70%, rgba(202, 210, 190, 0.03) 0%, transparent 50%);
  pointer-events: none;
  animation: breatheLight 10s ease-in-out infinite;
  z-index: 0;
}

@keyframes breatheLight {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 0.8; }
}

.block-container {
  max-width: 920px;
  padding-top: 1.5rem;
  padding-bottom: 3rem;
  position: relative;
  z-index: 1;
}

/* ================== カード系（木製家具のような柔らかさ）================== */
.card {
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid var(--border-light);
  border-radius: 24px;
  padding: 22px;
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(20px);
  transition: all 0.7s cubic-bezier(0.4, 0, 0.2, 1);
}

.card:hover {
  box-shadow: var(--shadow-hover);
  transform: translateY(-2px);
}

.item {
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid var(--border-light);
  border-radius: 20px;
  padding: 18px;
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(16px);
  margin-bottom: 14px;
  transition: all 0.6s ease;
}

.item:hover {
  box-shadow: var(--shadow-hover);
}

/* ================== テキストスタイル（静かな優しさ）================== */
.tip {
  color: var(--text-muted);
  font-size: 0.9rem;
  line-height: 1.7;
  font-weight: 300;
}

h1, h2, h3, h4, h5, h6 {
  color: var(--text-primary) !important;
  font-weight: 500;
  letter-spacing: 0.02em;
}

p, div, span, label {
  color: var(--text-primary);
}

.stMarkdown {
  color: var(--text-primary);
}

/* ================== トップタブ（最小限の主張）================== */
.top-tabs {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: saturate(180%) blur(20px);
  border: 1px solid var(--border-light);
  border-radius: 20px;
  box-shadow: var(--shadow-soft);
  padding: 8px 10px;
  margin-bottom: 18px;
}

.top-tabs .stButton > button {
  width: 100%;
  height: 40px;
  border-radius: 14px;
  font-weight: 500;
  font-size: 0.85rem;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  transition: all 0.6s ease;
}

.top-tabs .stButton > button:hover {
  background: rgba(167, 199, 217, 0.15);
  color: var(--deep-calm-blue);
}

.top-tabs .active .stButton > button {
  background: rgba(167, 199, 217, 0.25);
  color: var(--deep-calm-blue);
  font-weight: 600;
  box-shadow: inset 0 0 0 1px var(--winter-lake);
}

/* ================== ホーム大型カード（机の上の3つの道具）================== */
.bigbtn {
  margin-bottom: 16px;
}

.bigbtn .stButton > button {
  width: 100%;
  text-align: left;
  border-radius: 24px;
  border: 1px solid var(--border-light);
  box-shadow: var(--shadow-soft);
  padding: 24px 22px 20px;
  white-space: pre-wrap;
  line-height: 1.5;
  background: rgba(255, 255, 255, 0.7);
  color: var(--text-primary);
  font-weight: 500;
  transition: all 0.7s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(16px);
}

.bigbtn .stButton > button:hover {
  border-color: var(--winter-lake);
  box-shadow: var(--shadow-hover);
  transform: translateY(-3px);
  background: rgba(255, 255, 255, 0.85);
}

.bigbtn .stButton > button::first-line {
  font-weight: 600;
  font-size: 1.05rem;
  color: var(--deep-calm-blue);
}

/* ================== CBTカード（白紙ノートのような静けさ）================== */
.cbt-card {
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid var(--border-light);
  border-radius: 20px;
  padding: 20px 20px 16px;
  box-shadow: var(--shadow-soft);
  margin-bottom: 16px;
  backdrop-filter: blur(16px);
  transition: all 0.6s ease;
}

.cbt-card:hover {
  box-shadow: var(--shadow-hover);
}

.cbt-heading {
  font-weight: 600;
  font-size: 1rem;
  color: var(--deep-calm-blue);
  margin: 0 0 8px 0;
  letter-spacing: 0.02em;
}

.cbt-sub {
  color: var(--text-secondary);
  font-size: 0.88rem;
  margin: -2px 0 12px 0;
  line-height: 1.7;
  font-weight: 300;
}

/* ================== 呼吸ワーク円（白い息のような柔らかい光）================== */
.breath-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 30px 0;
  position: relative;
}

.breath-spot {
  width: 280px;
  height: 280px;
  border-radius: 999px;
  background: radial-gradient(
    circle at 50% 40%,
    rgba(255, 255, 255, 0.9) 0%,
    rgba(227, 233, 240, 0.7) 30%,
    rgba(202, 210, 190, 0.3) 70%,
    transparent 100%
  );
  border: 2px solid rgba(167, 199, 217, 0.3);
  box-shadow: 
    0 0 40px rgba(167, 199, 217, 0.2),
    inset 0 0 50px rgba(255, 255, 255, 0.5);
  position: relative;
  transition: all 1.2s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 呼吸フェーズ別（ゆっくり・柔らかく）*/
.breath-spot.inhale {
  transform: scale(1.25);
  border-color: rgba(167, 199, 217, 0.5);
  box-shadow: 
    0 0 60px rgba(167, 199, 217, 0.3),
    inset 0 0 60px rgba(255, 255, 255, 0.6);
}

.breath-spot.hold {
  transform: scale(1.25);
  border-color: rgba(202, 210, 190, 0.5);
  box-shadow: 
    0 0 50px rgba(202, 210, 190, 0.3),
    inset 0 0 55px rgba(255, 255, 255, 0.55);
}

.breath-spot.exhale {
  transform: scale(0.9);
  border-color: rgba(227, 201, 207, 0.4);
  box-shadow: 
    0 0 35px rgba(227, 201, 207, 0.25),
    inset 0 0 45px rgba(255, 255, 255, 0.5);
}

/* ================== Study Tracker専用スタイル ================== */
.study-goal-card {
  background: linear-gradient(135deg, rgba(167, 199, 217, 0.1) 0%, rgba(202, 210, 190, 0.1) 100%);
  border: 1px solid var(--border-light);
  border-radius: 20px;
  padding: 20px;
  margin-bottom: 16px;
  box-shadow: var(--shadow-soft);
}

.progress-bar-container {
  background: rgba(218, 223, 227, 0.3);
  border-radius: 12px;
  height: 12px;
  overflow: hidden;
  margin: 8px 0;
}

.progress-bar-fill {
  background: linear-gradient(90deg, var(--winter-lake) 0%, var(--deep-calm-blue) 100%);
  height: 100%;
  border-radius: 12px;
  transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 0 8px rgba(167, 199, 217, 0.4);
}

.study-stat {
  display: inline-block;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid var(--border-light);
  border-radius: 16px;
  margin: 4px 6px 4px 0;
  font-size: 0.9rem;
  color: var(--text-secondary);
  font-weight: 500;
}

/* ================== メタデータ・小テキスト ================== */
.meta {
  color: var(--text-muted);
  font-size: 0.82rem;
  margin-bottom: 0.3rem;
  font-weight: 300;
}

.small {
  font-size: 0.88rem;
  color: var(--text-secondary);
  font-weight: 300;
}

/* ================== Streamlitコンポーネントの調整 ================== */
/* 入力フィールド（下線のみ・枠なし）*/
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stNumberInput > div > div > input {
  background: transparent !important;
  border: none !important;
  border-bottom: 1px solid var(--border-light) !important;
  border-radius: 0 !important;
  color: var(--text-primary) !important;
  padding: 10px 4px !important;
  transition: all 0.6s ease !important;
  font-size: 15px !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus,
.stNumberInput > div > div > input:focus {
  border-bottom-color: var(--winter-lake) !important;
  box-shadow: 0 1px 0 0 var(--winter-lake) !important;
  background: rgba(167, 199, 217, 0.03) !important;
}

/* セレクトボックス */
.stSelectbox > div > div > select {
  background: rgba(255, 255, 255, 0.5) !important;
  border: 1px solid var(--border-light) !important;
  color: var(--text-primary) !important;
  border-radius: 14px !important;
  padding: 10px 14px !important;
  transition: all 0.6s ease !important;
}

.stSelectbox > div > div > select:focus {
  border-color: var(--winter-lake) !important;
  box-shadow: 0 0 0 2px rgba(167, 199, 217, 0.15) !important;
}

/* ボタン */
.stButton > button {
  background: rgba(167, 199, 217, 0.15);
  border: 1px solid var(--border-light);
  color: var(--deep-calm-blue);
  font-weight: 500;
  border-radius: 16px;
  padding: 10px 20px;
  transition: all 0.7s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: var(--shadow-soft);
}

.stButton > button:hover {
  background: rgba(167, 199, 217, 0.25);
  border-color: var(--winter-lake);
  box-shadow: var(--shadow-hover);
  transform: translateY(-2px);
}

/* プライマリボタン */
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, var(--winter-lake) 0%, var(--deep-calm-blue) 100%);
  border: none;
  color: white;
  box-shadow: var(--shadow-soft);
  font-weight: 600;
}

.stButton > button[kind="primary"]:hover {
  box-shadow: var(--shadow-hover);
  transform: translateY(-2px);
}

/* ラジオボタン */
.stRadio > div {
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid var(--border-light);
  border-radius: 14px;
  padding: 12px;
}

.stRadio > div > label {
  color: var(--text-primary) !important;
  font-weight: 500;
}

/* チェックボックス */
.stCheckbox > label {
  color: var(--text-primary) !important;
  font-weight: 500;
}

/* スライダー */
.stSlider > div > div > div {
  background: rgba(167, 199, 217, 0.25) !important;
}

.stSlider > div > div > div > div {
  background: var(--winter-lake) !important;
  box-shadow: 0 0 8px rgba(167, 199, 217, 0.4) !important;
}

/* セレクトボックス・ラベル */
.stSelectbox > label,
.stMultiSelect > label,
.stTextInput > label,
.stTextArea > label,
.stNumberInput > label {
  color: var(--text-secondary) !important;
  font-weight: 500;
  font-size: 0.9rem;
}

/* Multiselect */
.stMultiSelect > div > div {
  background: rgba(255, 255, 255, 0.5) !important;
  border: 1px solid var(--border-light) !important;
  border-radius: 14px !important;
}

.stMultiSelect span[data-baseweb="tag"] {
  background-color: rgba(167, 199, 217, 0.25) !important;
  border: 1px solid var(--winter-lake) !important;
  color: var(--deep-calm-blue) !important;
  border-radius: 10px !important;
}

/* Tabs */
.stTabs > div > div > div {
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid var(--border-light);
  border-radius: 14px;
}

.stTabs [data-baseweb="tab"] {
  color: var(--text-secondary);
  font-weight: 500;
}

.stTabs [aria-selected="true"] {
  color: var(--deep-calm-blue);
  border-bottom-color: var(--winter-lake);
}

/* Success/Error/Info メッセージ */
.stSuccess, .stError, .stWarning, .stInfo {
  background: rgba(255, 255, 255, 0.8) !important;
  border-radius: 14px !important;
  border-left: 4px solid var(--forest-green) !important;
  backdrop-filter: blur(16px) !important;
  color: var(--text-primary) !important;
}

.stError {
  border-left-color: var(--wood-pink) !important;
}

/* Divider */
hr {
  border-color: var(--border-light) !important;
}

/* ================== レスポンシブ調整 ================== */
@media (max-width: 768px) {
  .block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
  }
  
  .bigbtn .stButton > button {
    padding: 18px 16px 14px;
    font-size: 0.95rem;
  }
  
  .breath-spot {
    width: 240px;
    height: 240px;
  }
  
  .top-tabs .stButton > button {
    font-size: 0.75rem;
    height: 36px;
  }
}

/* ================== スクロールバー ================== */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: rgba(236, 239, 235, 0.5);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb {
  background: var(--winter-lake);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--deep-calm-blue);
}
</style>
""", unsafe_allow_html=True)

inject_css()

# ================== ナビゲーション ==================
def get_sections():
    return [
        ("HOME",   "🏡 ホーム"),
        ("SHARE",  "💬 今日を伝える"),
        ("SESSION","🌬 リラックス"),
        ("NOTE",   "📔 ノート"),
        ("STUDY",  "📚 Study Tracker"),
        ("REVIEW", "📋 ふりかえり"),
        ("CONSULT","🕊 相談"),
    ]

def top_tabs():
    if st.session_state.view == "HOME": 
        return
    
    active = st.session_state.view
    st.markdown('<div class="top-tabs">', unsafe_allow_html=True)
    sections = get_sections()
    cols = st.columns(len(sections))
    
    for i, (key, label) in enumerate(sections):
        with cols[i]:
            cls = "active" if key == active else ""
            st.markdown(f"<div class='{cls}'>", unsafe_allow_html=True)
            if st.button(label, key=f"tab_{key}"):
                st.session_state.view = key
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

def status_bar():
    if st.session_state.get("flash_msg"):
        st.toast(st.session_state["flash_msg"])
        st.markdown(
            f"<div class='card' style='padding:10px 12px; margin-bottom:10px; border-left:4px solid #CAD2BE'>"
            f"<b>{st.session_state['flash_msg']}</b></div>",
            unsafe_allow_html=True,
        )
        st.session_state["flash_msg"] = ""

    class_info = st.session_state.get("class_info", {})
    class_id = class_info.get("class_id", "—")
    handle = st.session_state.get("handle_norm", "")
    fs = "接続済み" if FIRESTORE_ENABLED else "未接続"
    
    st.markdown('<div class="card" style="padding:8px 12px; margin-bottom:10px">', unsafe_allow_html=True)
    st.markdown(
        f"<div class='tip'>ログイン中：{handle or '—'} / クラス：{class_id} / データ共有：{fs}</div>", 
        unsafe_allow_html=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ================== ログイン / 登録 ==================
def login_register_ui() -> bool:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🌿 With You")
    st.caption("気持ちを整える、やさしいノート")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("はじめての人", use_container_width=True, key="btn_reg"):
            st.session_state.mode = "REGISTER"
    with c2:
        if st.button("前に登録した人", use_container_width=True, key="btn_login"):
            st.session_state.mode = "LOGIN"

    st.divider()
    st.markdown("**クラスのパスワード**")
    st.caption("例：1年A組2025")
    group_pw = st.text_input(
        "パスワード", 
        key="inp_group_pw", 
        label_visibility="collapsed", 
        placeholder="ここに入力できます"
    )
    
    st.markdown("**あなたのニックネーム（4〜12文字）**")
    st.caption("英数字・ひらがな・カタカナ・漢字と _ - が使えます")
    handle_raw = st.text_input(
        "名前", 
        key="inp_handle", 
        label_visibility="collapsed", 
        placeholder="例：mika"
    )

    err = ""
    ok_handle, handle_norm = validate_handle(handle_raw)
    
    if (group_pw or "").strip() == "":
        err = "パスワードを入力できます。"
    elif not ok_handle:
        err = handle_norm

    mode = st.session_state.mode
    btn_label = "はじめる" if mode == "REGISTER" else "入る"
    disabled = (err != "")
    
    if st.button(btn_label, type="primary", use_container_width=True, disabled=disabled, key="btn_go"):
        gid = group_id_from_password(group_pw)
        class_info = extract_class_info(group_pw)
        
        st.session_state.group_id = gid
        st.session_state.handle_norm = handle_norm
        st.session_state.user_disp = handle_norm
        st.session_state.class_info = class_info
        st.session_state.group_pw = group_pw

        if mode == "REGISTER":
            ok, msg = db_create_user(gid, handle_norm, class_info)
            if not ok:
                st.error(msg)
                st.stop()
            
            st.session_state.auth_ok = True
            st.session_state.view = "HOME"
            st.session_state.flash_msg = f"{class_info['class_id']}へようこそ"
            st.rerun()
        else:
            if not db_user_exists(gid, handle_norm):
                st.error("まだ登録がありません。「はじめての人」から設定できます。")
                st.stop()
            
            db_touch_login(gid, handle_norm)
            st.session_state.auth_ok = True
            st.session_state.view = "HOME"
            st.session_state.flash_msg = "ログインしました"
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
    class_info = st.session_state.get("class_info", {})
    class_id = class_info.get("class_id", "")
    
    st.markdown(f"""
<div class="card" style="margin-bottom:18px">
  <div style="font-weight:500; font-size:1rem; margin-bottom:.5rem; color:var(--deep-calm-blue)">🌿 With You</div>
  <div style="color:var(--text-secondary); line-height:1.75; white-space:pre-wrap; font-weight:300;">
気持ちを整理したい日も、誰かに話したい日も。
With You は、あなたの心のそばにある、小さなツールボックスです。

いま、どのカードが自分に合いそうか、
ゆっくり選んでみてください。

🔒 「今日を伝える」と「相談する」だけが先生に届きます。
それ以外の記録は、すべてあなたの端末だけに残ります。

<div style="margin-top:1rem; padding:10px 14px; background:rgba(167, 199, 217, 0.12); border-radius:16px; border-left:3px solid #A7C7D9;">
  <b style="color:var(--deep-calm-blue); font-weight:500">あなたのクラス：{class_id}</b>
</div>
  </div>
</div>
""", unsafe_allow_html=True)

def big_button(title: str, sub: str, to_view: str, key: str, emoji: str):
    label = f"{emoji} {title}\n{sub}"
    st.markdown('<div class="bigbtn">', unsafe_allow_html=True)
    if st.button(label, key=f"home_{key}"):
        st.session_state.view = to_view
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def view_home():
    home_intro()
    
    # 大きなカード3つ（机の上の道具）
    big_button(
        "今日を伝える", 
        "今日の体調や気分を、静かに記録します", 
        "SHARE", "share", "💬"
    )
    
    c1, c2 = st.columns(2)
    with c1: 
        big_button(
            "リラックス", 
            "90秒の呼吸で、いまを落ち着ける", 
            "SESSION", "session", "🌬"
        )
    with c2: 
        big_button(
            "心を整えるノート", 
            "感じたことを、言葉にしてみる", 
            "NOTE", "note", "📔"
        )
    
    c3, c4 = st.columns(2)
    with c3: 
        big_button(
            "Study Tracker", 
            "学習の記録と、自分の成長を確かめる", 
            "STUDY", "study", "📚"
        )
    with c4: 
        big_button(
            "ふりかえり", 
            "この端末に残した記録を見返す", 
            "REVIEW", "review", "📋"
        )
    
    big_button(
        "相談する", 
        "話したいことがあれば、ここに書けます", 
        "CONSULT", "consult", "🕊"
    )

# ----- 今日を伝える -----
def view_share():
    st.markdown("### 💬 今日を伝える")
    st.caption("この情報は先生が見ることができます。個人は特定されません。")
    
    mood = st.radio(
        "いま、どんな感じですか？", 
        ["🙂","😐","😟"], 
        index=1, 
        horizontal=True, 
        key="share_mood",
        help="🙂=まあまあ / 😐=ふつう / 😟=つらい"
    )
    
    body_opts = ["頭痛","腹痛","吐き気","食欲低下","だるさ","その他","なし"]
    body = st.multiselect(
        "体調（当てはまるもの）", 
        body_opts, 
        default=["なし"], 
        key="share_body"
    )
    
    if "なし" in body and len(body) > 1:
        body = [b for b in body if b != "なし"]
    
    c1, c2 = st.columns(2)
    with c1: 
        sleep_h = st.number_input(
            "睡眠時間（時間）", 
            min_value=0.0, 
            max_value=24.0, 
            value=6.0, 
            step=0.5, 
            key="share_sleep_h"
        )
    with c2: 
        sleep_q = st.radio(
            "睡眠の質", 
            ["ぐっすり","ふつう","浅い"], 
            index=1, 
            horizontal=True, 
            key="share_sleep_q"
        )
    
    memo = st.text_area(
        "今日のようす（先生に伝えたいことがあれば）",
        height=100,
        placeholder="ここに書けます",
        key="share_memo"
    )

    disabled = not FIRESTORE_ENABLED
    label = "送る" if FIRESTORE_ENABLED else "送信（未接続）"
    
    if st.button(label, type="primary", disabled=disabled, key="share_send"):
        gid = st.session_state.get("group_id","")
        hdl = st.session_state.get("handle_norm","")
        class_info = st.session_state.get("class_info", {})
        
        risk_level = classify_risk_level(
            message=memo,
            mood=mood,
            body=body,
            sleep_hours=float(sleep_h)
        )
        
        payload = {
            "ts": datetime.now(timezone.utc),
            "group_id": gid,
            "handle": hdl,
            "user_key": user_key(gid, hdl) if (gid and hdl) else "",
            "class_info": class_info,
            "payload": {
                "mood": mood,
                "mood_label": get_mood_label(mood),
                "body": body,
                "sleep_hours": float(sleep_h),
                "sleep_quality": sleep_q,
                "memo": (memo or "").strip(),
            },
            "risk_level": risk_level,
            "anonymous": True
        }
        
        ok = safe_db_add("school_share", payload)
        
        if ok:
            st.session_state.flash_msg = "記録しました。ありがとうございます"
            st.rerun()
        else:
            st.error("送信できませんでした。")

# ----- 相談 -----
CONSULT_TOPICS = [
    "体調","勉強","人間関係","家庭","進路",
    "いじめ","メンタルの不調","その他"
]

def view_consult():
    st.markdown("### 🕊 相談")
    st.caption("話しにくいことでも、ここに書けます。お名前は空欄のままでも大丈夫です。")
    
    to_whom = st.radio(
        "相談先", 
        ["カウンセラーに相談したい","先生に伝えたい"], 
        horizontal=True, 
        key="c_to"
    )
    
    topics = st.multiselect(
        "内容（当てはまるもの）", 
        CONSULT_TOPICS, 
        default=[], 
        key="c_topics"
    )
    
    anonymous = st.checkbox("匿名で送る", value=True, key="c_anon")
    name = "" if anonymous else st.text_input("お名前（任意）", value="", key="c_name")
    
    msg = st.text_area(
        "相談内容", 
        height=220, 
        value="", 
        key="c_msg",
        placeholder="話したいことを、自由に書いてみてください"
    )

    disabled = not FIRESTORE_ENABLED or (msg.strip()=="")
    label = "送る" if FIRESTORE_ENABLED else "送信（未接続）"
    
    if st.button(label, type="primary", disabled=disabled, key="c_send"):
        gid = st.session_state.get("group_id","")
        hdl = st.session_state.get("handle_norm","")
        class_info = st.session_state.get("class_info", {})
        
        risk_level = classify_risk_level(
            message=msg,
            mood="😐",
            body=[],
            sleep_hours=6.0
        )
        
        payload = {
            "ts": datetime.now(timezone.utc),
            "group_id": gid,
            "handle": hdl,
            "user_key": user_key(gid, hdl) if (gid and hdl) else "",
            "class_info": class_info,
            "message": msg.strip(),
            "topics": topics,
            "intent": "counselor" if to_whom.startswith("カウンセラー") else "teacher",
            "anonymous": bool(anonymous),
            "name": name.strip() if (not anonymous and name) else "",
            "risk_level": risk_level,
        }
        
        ok = safe_db_add("consult_msgs", payload)
        
        if ok:
            st.session_state.flash_msg = "送信しました。ありがとうございます"
            for k in ["c_topics","c_msg","c_name","c_anon","c_to"]:
                if k in st.session_state: 
                    del st.session_state[k]
            st.rerun()
        else:
            st.error("送信できませんでした。")

# ----- リラックス（呼吸）-----
BREATH_PATTERN = (5, 2, 6)

def breathing_animation(total_sec: int = 90):
    """呼吸ワークのアニメーション（白い息のような柔らかい光）"""
    st.session_state["_breath_running"] = True

    inhale, hold, exhale = BREATH_PATTERN
    cycle = inhale + hold + exhale
    cycles = max(1, round(total_sec / cycle))

    circle_area = st.empty()
    phase_area = st.empty()
    countdown_area = st.empty()
    stop_area = st.empty()

    def render_circle(phase_class: str = ""):
        circle_area.markdown(
            f"""
<div class="breath-container">
  <div class="breath-spot {phase_class}"></div>
</div>
""",
            unsafe_allow_html=True,
        )

    def set_countdown(sec: int, label: str = ""):
        countdown_area.markdown(
            f"""
<div style="text-align:center;font-size:1rem;color:var(--text-secondary);margin-top:10px;font-weight:300;">
  {label} のこり <b style="color:var(--deep-calm-blue)">{sec}</b> 秒
</div>
""",
            unsafe_allow_html=True,
        )

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
            phases = [
                ("吸ってください", inhale, "inhale"), 
                ("止めてください", hold, "hold"), 
                ("吐いてください", exhale, "exhale")
            ]
            
            for label, seconds, phase_class in phases:
                if seconds <= 0:
                    continue
                
                render_circle(phase_class)
                phase_area.markdown(
                    f"<div style='text-align:center;font-size:1.15rem;font-weight:500;color:var(--deep-calm-blue);'>{label}</div>", 
                    unsafe_allow_html=True
                )
                
                for remain in range(seconds, 0, -1):
                    if st.session_state.get("_breath_stop") or st.session_state.view != "SESSION":
                        return
                    set_countdown(remain, label)
                    time.sleep(1)
    finally:
        phase_area.empty()
        countdown_area.empty()
        stop_area.empty()
        circle_area.empty()
        st.session_state["_breath_running"] = False
        st.session_state["_breath_stop"] = False
        st.session_state["_breath_finished"] = True
        st.rerun()

def view_session():
    st.markdown("### 🌬 リラックス（呼吸）")
    st.caption("円が大きくなったら吸って、小さくなったら吐きます。途中で停止できます。")

    total_seconds = 90
    inhale, hold, exhale = BREATH_PATTERN

    running = st.session_state.get("_breath_running", False)
    finished = st.session_state.pop("_breath_finished", False)
    
    if finished:
        st.success("お疲れさまでした")

    if not running:
        cols = st.columns([1, 1, 1])
        with cols[1]:
            if st.button(
                "🫁 はじめる（90秒）", 
                key="breath_start", 
                type="primary", 
                use_container_width=True
            ):
                st.session_state["_breath_stop"] = False
                st.session_state["_breath_running"] = True
                st.rerun()
    else:
        breathing_animation(total_seconds)

    st.caption(f"パターン：{inhale}-{hold}-{exhale}／合計 {total_seconds} 秒")

    st.divider()
    after = st.slider(
        "いまの気分（1 とてもつらい / 10 とても楽）", 
        1, 10, 5, 
        key="breath_mood_after"
    )

    if st.button("💾 端末に保存", type="primary", key="breath_save"):
        st.session_state["_local_logs"]["breath"].append({
            "ts": now_iso(), 
            "pattern": "5-2-6", 
            "mood_after": int(after), 
            "sec": total_seconds
        })
        st.success("保存しました")

# ----- ノート（CBT構造化ワーク） -----
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
気持ちと考え方を整理することで、
いま感じている不安やしんどさが、少し軽くなるかもしれません。

自分のペースで、思いつくことを書いてみてください。
  </div>
</div>
""", unsafe_allow_html=True)

def mood_radio() -> Dict[str, Any]:
    st.markdown('<div class="cbt-card">', unsafe_allow_html=True)
    st.markdown('<div class="cbt-heading">Step 1：いまの気持ち</div>', unsafe_allow_html=True)
    
    cols = st.columns(4)
    for i, m in enumerate(MOODS):
        with cols[i % 4]:
            if st.button(f"{m['emoji']} {m['label']}", key=f"cbt_btn_mood_{m['key']}"):
                st.session_state["cbt_mood_key"] = m["key"]
                st.session_state["cbt_mood_label"] = m["label"]
                st.session_state["cbt_mood_emoji"] = m["emoji"]
    
    sel = st.session_state.get("cbt_mood_label", "未選択")
    st.write(f"選択中：**{st.session_state.get('cbt_mood_emoji','')} {sel}**")
    
    intensity = st.slider("強さ（0〜100）", 0, 100, 60, key="cbt_intensity")
    st.markdown("</div>", unsafe_allow_html=True)
    
    return {
        "key": st.session_state.get("cbt_mood_key"),
        "label": st.session_state.get("cbt_mood_label"),
        "emoji": st.session_state.get("cbt_mood_emoji"),
        "intensity": intensity
    }

def text_card(title: str, subtext: str, key: str, height=120, placeholder="ここに書けます") -> str:
    st.markdown('<div class="cbt-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="cbt-heading">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cbt-sub">{subtext}</div>', unsafe_allow_html=True)
    val = st.text_area("", height=height, key=key, placeholder=placeholder, label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)
    return val

ACTION_CATEGORIES_EMOJI = { 
    "身体": "🫧",
    "環境": "🌤",
    "リズム": "⏯️",
    "つながり": "💬" 
}

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
            if a in seen: 
                continue
            seen.add(a)
            disp.append(f"{ACTION_CATEGORIES_EMOJI[cat]} {a}")
            vals.append(a)
    return disp, vals

def action_picker(mood_key: Optional[str]):
    st.markdown('<div class="cbt-card">', unsafe_allow_html=True)
    st.markdown('<div class="cbt-heading">Step 6：今できそうなこと</div>', unsafe_allow_html=True)
    st.markdown('<div class="cbt-sub">ぴったりを1つだけ。選ばなくても大丈夫です。</div>', unsafe_allow_html=True)
    
    disp, vals = _flat_action_options_emoji()
    options_disp = disp + ["— 選ばない —"]
    
    key_pick = f"act_pick_single_{(mood_key or 'default').strip().lower()}"
    sel_disp = st.selectbox(
        "小さな行動", 
        options=options_disp, 
        index=len(options_disp)-1, 
        key=key_pick
    )
    
    chosen = "" if sel_disp == "— 選ばない —" else vals[disp.index(sel_disp)]
    
    custom_key = f"act_custom_single_{(mood_key or 'default').strip().lower()}"
    custom = st.text_input(
        "自分の言葉で書く", 
        key=custom_key, 
        placeholder="例：窓を開けて深呼吸する"
    ).strip()
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    if custom: 
        return "", custom
    return (chosen or ""), ""

def view_note():
    st.markdown("### 📔 心を整えるノート")
    cbt_intro_block()

    mood = mood_radio()
    trigger_text = text_card(
        "Step 2：きっかけ", 
        "その気持ちは、どんなことがきっかけだったでしょうか。", 
        "cbt_trigger"
    )
    auto_thought = text_card(
        "Step 3：頭の中の言葉", 
        "そのとき、頭の中でどんな言葉がよぎりましたか。", 
        "cbt_auto"
    )
    reason_for = text_card(
        "Step 4：そう思った理由", 
        "心の中の「根拠」があれば、書いてみてください。", 
        "cbt_for", 
        height=100
    )
    reason_against = text_card(
        "Step 5：別の見方", 
        "そうでもないかも、と思う理由はありますか。", 
        "cbt_against", 
        height=100
    )
    alt_perspective = text_card(
        "Step 6：友だちだったら", 
        "もし友だちが同じことを感じていたら、なんて声をかけますか。", 
        "cbt_alt"
    )
    
    act_suggested, act_custom = action_picker(mood.get("key"))
    
    reflection = text_card(
        "Step 7：今日の日記", 
        "気づいたこと・これからのことなど、自由に。", 
        "cbt_reflect", 
        height=120
    )

    if st.button("💾 端末に保存", type="primary", key="cbt_save"):
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
        st.success("保存しました")
        
        st.download_button(
            "⬇️ この記録をダウンロード",
            data=json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name=f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            key=f"dl_note_{len(st.session_state['_local_logs']['note'])}"
        )

# ----- Study Tracker【強化版】 -----
def calculate_study_stats(studies: List[Dict]) -> Dict[str, Any]:
    """学習統計を計算"""
    if not studies:
        return {
            "total_minutes": 0,
            "weekly_minutes": 0,
            "monthly_minutes": 0,
            "by_subject": {},
            "weekly_progress": 0,
            "monthly_progress": 0
        }
    
    df = pd.DataFrame(studies)
    df['ts'] = pd.to_datetime(df['ts'])
    
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    total = df['minutes'].sum()
    weekly = df[df['ts'] >= week_ago]['minutes'].sum()
    monthly = df[df['ts'] >= month_ago]['minutes'].sum()
    
    by_subject = df.groupby('subject')['minutes'].sum().to_dict()
    
    weekly_goal = st.session_state.get("study_weekly_goal", 300)
    monthly_goal = st.session_state.get("study_monthly_goal", 1200)
    
    return {
        "total_minutes": int(total),
        "weekly_minutes": int(weekly),
        "monthly_minutes": int(monthly),
        "by_subject": by_subject,
        "weekly_progress": min(100, int((weekly / weekly_goal) * 100)) if weekly_goal > 0 else 0,
        "monthly_progress": min(100, int((monthly / monthly_goal) * 100)) if monthly_goal > 0 else 0,
    }

def view_study():
    st.markdown("### 📚 Study Tracker")
    st.caption("学習時間を記録して、自分の成長を確かめよう")
    
    # 目標設定セクション
    with st.expander("🎯 目標設定", expanded=False):
        st.markdown("**週間目標（分）**")
        weekly = st.number_input(
            "週間", 
            min_value=60, 
            max_value=3000, 
            value=st.session_state.get("study_weekly_goal", 300),
            step=30,
            key="weekly_goal_input",
            label_visibility="collapsed"
        )
        
        st.markdown("**月間目標（分）**")
        monthly = st.number_input(
            "月間", 
            min_value=240, 
            max_value=10000, 
            value=st.session_state.get("study_monthly_goal", 1200),
            step=60,
            key="monthly_goal_input",
            label_visibility="collapsed"
        )
        
        if st.button("目標を更新", key="update_goals"):
            st.session_state["study_weekly_goal"] = weekly
            st.session_state["study_monthly_goal"] = monthly
            st.success("目標を更新しました")
    
    # 進捗サマリー
    studies = st.session_state["_local_logs"]["study"]
    stats = calculate_study_stats(studies)
    
    if stats["total_minutes"] > 0:
        st.markdown('<div class="study-goal-card">', unsafe_allow_html=True)
        st.markdown("#### 📊 学習状況")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**今週の進捗**")
            st.markdown(f'<div class="progress-bar-container"><div class="progress-bar-fill" style="width:{stats["weekly_progress"]}%"></div></div>', unsafe_allow_html=True)
            st.caption(f"{stats['weekly_minutes']}分 / {st.session_state['study_weekly_goal']}分 ({stats['weekly_progress']}%)")
        
        with col2:
            st.markdown("**今月の進捗**")
            st.markdown(f'<div class="progress-bar-container"><div class="progress-bar-fill" style="width:{stats["monthly_progress"]}%"></div></div>', unsafe_allow_html=True)
            st.caption(f"{stats['monthly_minutes']}分 / {st.session_state['study_monthly_goal']}分 ({stats['monthly_progress']}%)")
        
        st.markdown("**科目別の累計時間**")
        for subj, mins in sorted(stats["by_subject"].items(), key=lambda x: x[1], reverse=True):
            hours = mins / 60
            st.markdown(f'<span class="study-stat">{subj}：{hours:.1f}時間</span>', unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        st.divider()
    
    # 学習記録入力
    st.markdown("#### ✏️ 新しい学習記録")
    
    subjects_default = ["国語","数学","英語","理科","社会","音楽","美術","情報","その他"]
    subj = st.selectbox("科目", subjects_default, index=0, key="study_subj")
    add = st.text_input("自分の科目を追加", key="study_add", placeholder="例：プログラミング")
    
    if add.strip(): 
        subj = add.strip()
    
    mins = st.number_input("学習時間（分）", 1, 600, 30, 5, key="study_min")
    
    col1, col2 = st.columns(2)
    with col1:
        understanding = st.selectbox(
            "理解度", 
            ["よくわかった","だいたいわかった","少し難しかった","よくわからなかった"],
            index=1,
            key="study_understanding"
        )
    with col2:
        concentration = st.selectbox(
            "集中度",
            ["とても集中できた","集中できた","普通","あまり集中できなかった"],
            index=1,
            key="study_concentration"
        )
    
    memo = st.text_area(
        "学習メモ・次回の課題", 
        key="study_memo",
        placeholder="例：問題集p.50-60を解いた。次回は公式の復習から始める。",
        height=80
    )
    
    if st.button("💾 記録する", type="primary", key="study_save"):
        rec = {
            "ts": now_iso(), 
            "subject": subj, 
            "minutes": int(mins),
            "understanding": understanding,
            "concentration": concentration,
            "memo": memo
        }
        st.session_state["_local_logs"]["study"].append(rec)
        st.success("記録しました")
        st.rerun()

# ----- ふりかえり -----
def view_review():
    st.markdown("### 📋 ふりかえり")
    st.caption("この端末に保存した記録を見返すことができます")
    
    logs = st.session_state["_local_logs"]
    
    if any(len(v)>0 for v in logs.values()):
        all_json = json.dumps(logs, ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button(
            "⬇️ すべての記録をダウンロード", 
            data=all_json,
            file_name=f"withyou_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json", 
            key="review_dl_all"
        )
    
    tabs = st.tabs(["ノート","呼吸","Study"])
    
    with tabs[0]:
        notes = list(reversed(logs["note"]))
        if not notes: 
            st.caption("まだ記録がありません")
        else:
            for r in notes:
                st.markdown(f"""
<div class="item">
  <div class="meta">{r['ts']}</div>
  <div style="font-weight:500; color:var(--deep-calm-blue); margin-bottom:.2rem">
    {r['mood'].get('emoji','')} {r['mood'].get('label','')}
  </div>
  <div style="white-space:pre-wrap; margin-bottom:.3rem; font-size:0.9rem">きっかけ：{r.get('trigger','')}</div>
  <div style="white-space:pre-wrap; margin-bottom:.3rem; font-size:0.9rem">頭の中の言葉：{r.get('auto','')}</div>
  <div style="white-space:pre-wrap; margin-bottom:.3rem; font-size:0.9rem">日記：{r.get('diary','')}</div>
</div>
""", unsafe_allow_html=True)
    
    with tabs[1]:
        breaths = list(reversed(logs["breath"]))
        if not breaths: 
            st.caption("まだ記録がありません")
        else:
            for r in breaths:
                st.markdown(f"""
<div class="item">
  <div class="meta">{r['ts']}</div>
  <div style="font-size:0.9rem">パターン：{r.get('pattern','5-2-6')} / 実施：{r.get('sec',90)}秒</div>
  <div style="font-size:0.9rem">終了時の気分：{r.get('mood_after','')}</div>
</div>
""", unsafe_allow_html=True)
    
    with tabs[2]:
        studies = list(reversed(logs["study"]))
        if not studies: 
            st.caption("まだ記録がありません")
        else:
            # 統計表示
            stats = calculate_study_stats(logs["study"])
            if stats["total_minutes"] > 0:
                st.markdown("#### 📊 学習統計")
                hours = stats["total_minutes"] / 60
                st.markdown(f'<div class="study-stat">累計学習時間：{hours:.1f}時間</div>', unsafe_allow_html=True)
                st.divider()
            
            # 記録一覧
            st.markdown("#### 📝 学習記録")
            for r in studies:
                st.markdown(f"""
<div class="item">
  <div class="meta">{r['ts']}</div>
  <div style="font-weight:600; color:var(--deep-calm-blue)">{r['subject']}</div>
  <div style="font-size:0.9rem; margin:4px 0">
    学習時間：{int(r['minutes'])}分 / 
    理解度：{r.get('understanding','')} / 
    集中度：{r.get('concentration','')}
  </div>
  <div style="white-space:pre-wrap; color:var(--text-secondary); margin-top:.3rem; font-size:0.88rem">{r.get('memo','')}</div>
</div>
""", unsafe_allow_html=True)

# ================== ルーター ==================
def main_router():
    v = st.session_state.view
    
    if v == "HOME":     
        view_home()
    elif v == "SHARE":  
        view_share()
    elif v == "SESSION":
        view_session()
    elif v == "NOTE":   
        view_note()
    elif v == "STUDY":  
        view_study()
    elif v == "REVIEW": 
        view_review()
    elif v == "CONSULT":
        view_consult()
    else:               
        view_home()

# ================== アプリ起動 ==================
if st.session_state.get("auth_ok", False):
    logout_btn()
    status_bar()
    top_tabs()
    main_router()
else:
    login_register_ui()
