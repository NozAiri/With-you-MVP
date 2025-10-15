# app.py — Sora 2分ノート（Supabase保存／多人数同時／白ボタン廃止・文字ラベル）

from datetime import datetime, date
from pathlib import Path
from typing import Optional, List, Tuple
import pandas as pd
import streamlit as st
import bcrypt
from supabase import create_client, Client

# ---------------- Page config ----------------
st.set_page_config(
    page_title="Sora — しんどい夜の2分ノート",
    page_icon="🌙",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------- Theme ----------------
PINK = "#FBDDD3"
NAVY = "#19114B"

# ---------------- CSS（白四角排除／文字ラベル前提） ----------------
def inject_css():
    css = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;600;700;900&display=swap');

:root {{
  --bg:{NAVY};
  --text:#FFFFFF;
  --muted:rgba(255,255,255,.78);
  --pink:{PINK};
  --panel:#221A63;
  --line:rgba(251,221,211,.55);
  --ink:#0f0f23;
}}

html, body, .stApp {{ background:var(--bg); }}
* {{ font-family:"Zen Maru Gothic", system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }}
.block-container {{ max-width:980px; padding: 1rem 1rem 2.2rem; }}
h1,h2,h3,p,li,label,.stMarkdown,.stTextInput,.stTextArea {{ color:var(--text); }}
small {{ color:var(--muted); }}

/* 余計な空白削除 */
.stMarkdown p:empty, .stMarkdown div:empty {{ display:none !important; }}
section.main > div:empty {{ display:none !important; }}

/* 入力 */
textarea, .stTextArea textarea,
.stTextInput input {{
  background: var(--ink) !important;
  color:#f0eeff !important;
  border:1px solid #3a3d66 !important;
  border-radius:14px !important;
}}

/* カード */
.card {{
  background: var(--panel);
  border: 2px solid var(--line);
  border-radius: 22px;
  padding: 16px 18px;
  box-shadow: 0 18px 40px rgba(0,0,0,.22);
  margin-bottom: 14px;
}}

/* multiselect を“ピル”風に */
.stMultiSelect > div > div {{ background: rgba(0,0,0,.10); border: 1px solid rgba(255,255,255,.18); border-radius: 16px; }}
.stMultiSelect [data-baseweb="tag"] {{ background: linear-gradient(180deg,#ffbcd2,#ff99bc); color:#3a2144; border-radius: 999px; font-weight: 900; }}
.stMultiSelect [data-baseweb="tag"] span {{ color:#3a2144; }}

/* スライダー文字色 */
[data-baseweb="slider"] * {{ color:var(--text) !important; }}

/* Sticky Navbar */
.navbar {{
  position: sticky; top: 0; z-index: 1000;
  background: rgba(25,17,75,.82); backdrop-filter: blur(10px);
  margin: 0 0 10px 0; padding: 10px 12px;
  border-bottom: 1px solid rgba(255,255,255,.08);
}}
.navbar .stRadio [role="radiogroup"] {{ gap: 8px; flex-wrap: wrap; }}
.navbar label {{ background:#fff; color:#1b1742; border:1px solid rgba(0,0,0,.06); border-radius:12px; padding:8px 10px; font-weight:800; }}
.navbar input:checked + div label {{ background:#F4F4FF; border:2px solid #8A84FF; }}

/* CTA／通常ボタン（白四角は使わない。必ず文字ラベルで） */
.stButton > button {{
  background: rgba(0,0,0,.10) !important;
  color:#ffffff !important;
  border:1px solid rgba(255,255,255,.18) !important;
  border-radius:14px !important;
  padding:10px 14px !important;
  font-weight:800 !important;
  box-shadow: 0 8px 18px rgba(0,0,0,.18) !important;
}}
.cta-primary .stButton > button {{
  width:100%; border-radius:999px; padding:12px 16px !important;
  background:#FFFFFF !important; color:#18123F !important; font-weight:900; border:0 !important; box-shadow:0 14px 26px rgba(0,0,0,.22) !important;
}}
.cta-ghost .stButton > button {{
  width:100%; border-radius:999px; padding:12px 16px !important;
  background:transparent !important; color:#FFFFFF !important; border:2px solid var(--line) !important; font-weight:900; box-shadow:none !important;
}}

/* HERO */
.hero {{ border: 2px solid var(--line); border-radius: 24px; padding: 22px; background: linear-gradient(180deg, rgba(255,255,255,.02), rgba(0,0,0,.06)); margin-bottom: 16px; }}
.hero .topline {{ text-align:center; font-weight:900; font-size:1.08rem; letter-spacing:.06em; color: var(--pink); margin-bottom: 10px; }}
.hero .maincopy {{ text-align:center; font-weight:900; font-size:1.8rem; line-height:1.35; margin:.2rem 0 .9rem; }}
.hero .maincopy .big3 {{ font-size:3rem; color:#fff; display:inline-block; transform:translateY(.04em); }}

/* レスポンシブ */
@media (max-width: 640px) {{
  .block-container {{ padding-left:1rem; padding-right:1rem; }}
  .hero .maincopy {{ font-size:1.6rem; }}
  .hero .maincopy .big3 {{ font-size:2.6rem; }}
}}
</style>
"""
    st.markdown(css, unsafe_allow_html=True)

inject_css()

# ---------------- Supabase ----------------
@st.cache_resource
def get_sb() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    client = create_client(url, key)
    # 初回だけテーブルを用意（存在すれば無視される）
    try:
        client.rpc("noop").execute()  # 接続確認（失敗しても続行）
    except Exception:
        pass
    # users
    client.postgrest.rpc  # ダミー参照でimport警告回避
    client.table("users").select("*").limit(1).execute() if table_exists(client, "users") else create_schema(client)
    return client

def table_exists(sb: Client, name: str) -> bool:
    try:
        sb.table(name).select("*").limit(1).execute()
        return True
    except Exception:
        return False

def create_schema(sb: Client):
    # SQLを一括実行
    sql = """
    create table if not exists users (
      email text primary key,
      password_hash text not null,
      created_at timestamptz default now()
    );
    create table if not exists cbt_entries (
      id uuid primary key default gen_random_uuid(),
      user_email text not null references users(email) on delete cascade,
      ts timestamptz not null default now(),
      emotions text,
      trigger_tags text,
      trigger_free text,
      fact text,
      alt text,
      bw boolean, catastrophe boolean, fortune boolean, emotion boolean, decide boolean,
      distress_before int, prob_before int,
      rephrase text, prob_after int, distress_after int
    );
    create table if not exists daily_reflections (
      id uuid primary key default gen_random_uuid(),
      user_email text not null references users(email) on delete cascade,
      date date not null,
      ts_saved timestamptz not null default now(),
      small_win text, self_message text, note_for_tomorrow text,
      loneliness int
    );
    """
    sb.postgrest.from_("pg_temp").select().execute()  # no-op
    sb.rpc("exec_sql", {"sql": sql}).execute() if has_exec_sql(sb) else run_sql_fallback(sb, sql)

def has_exec_sql(sb: Client) -> bool:
    try:
        sb.rpc("exec_sql", {"sql": "select 1"}).execute()
        return True
    except Exception:
        return False

def run_sql_fallback(sb: Client, sql: str):
    # Community Cloud等でRPC未設定なら、すでに作成済として続行
    pass

sb = get_sb()

# ---------------- 認証（アプリ内：メール＋パスワード） ----------------
def auth_widget() -> Optional[str]:
    """ログイン済みならメールを返す。未ログインならログイン/登録フォームを表示して停止。"""
    if st.session_state.get("user_email"):
        return st.session_state["user_email"]

    st.markdown("### 🔐 ログイン / 新規登録")
    tab_login, tab_signup = st.tabs(["ログイン", "新規登録"])

    with tab_signup:
        se = st.text_input("メールアドレス（新規）", key="signup_email")
        sp = st.text_input("パスワード（新規）", type="password", key="signup_pw")
        if st.button("新規登録を作成"):
            if se and sp:
                pw_hash = bcrypt.hashpw(sp.encode(), bcrypt.gensalt()).decode()
                # 既存チェック
                r = sb.table("users").select("email").eq("email", se).execute()
                if r.data:
                    st.error("そのメールは既に登録されています。ログインしてください。")
                else:
                    sb.table("users").insert({"email": se, "password_hash": pw_hash}).execute()
                    st.success("登録しました。続けてログインしてください。")
            else:
                st.warning("メールとパスワードを入力してください。")

    with tab_login:
        le = st.text_input("メールアドレス", key="login_email")
        lp = st.text_input("パスワード", type="password", key="login_pw")
        if st.button("ログイン"):
            if le and lp:
                r = sb.table("users").select("password_hash").eq("email", le).execute()
                if not r.data:
                    st.error("登録が見つかりません。新規登録してください。")
                else:
                    ok = bcrypt.checkpw(lp.encode(), r.data[0]["password_hash"].encode())
                    if ok:
                        st.session_state["user_email"] = le
                        st.experimental_rerun()
                    else:
                        st.error("パスワードが違います。")
            else:
                st.warning("メールとパスワードを入力してください。")

    st.stop()

def sign_out_button():
    if st.button("🔓 ログアウト"):
        st.session_state.pop("user_email", None)
        st.experimental_rerun()

# ---------------- Data helpers（DB版） ----------------
def db_insert(table: str, row: dict, user_email: str):
    row = {**row, "user_email": user_email}
    sb.table(table).insert(row).execute()

def db_select(table: str, user_email: str) -> pd.DataFrame:
    order_col = "ts" if table == "cbt_entries" else "ts_saved"
    r = sb.table(table).select("*").eq("user_email", user_email).order(order_col, desc=True).execute()
    return pd.DataFrame(r.data)

# ---------------- セッション初期値 ----------------
def ensure_cbt_defaults():
    if "cbt" not in st.session_state or not isinstance(st.session_state.cbt, dict):
        st.session_state.cbt = {}
    cbt = st.session_state.cbt
    cbt.setdefault("emotions", [])
    cbt.setdefault("trigger_tags", [])
    cbt.setdefault("trigger_free","")
    cbt.setdefault("fact","")
    cbt.setdefault("alt","")
    checks = cbt.setdefault("checks", {})
    for k in ["bw","catastrophe","fortune","emotion","decide"]:
        checks.setdefault(k, False)
    cbt.setdefault("distress_before",5)
    cbt.setdefault("prob_before",50)
    cbt.setdefault("rephrase","")
    cbt.setdefault("prob_after",40)
    cbt.setdefault("distress_after",4)

def ensure_reflection_defaults():
    if "reflection" not in st.session_state or not isinstance(st.session_state.reflection, dict):
        st.session_state.reflection = {}
    r = st.session_state.reflection
    r.setdefault("today_small_win","")
    r.setdefault("self_message","")
    r.setdefault("note_for_tomorrow","")
    r.setdefault("loneliness",5)
    d = r.get("date", date.today())
    if isinstance(d, str):
        try: d = date.fromisoformat(d)
        except Exception: d = date.today()
    r["date"] = d

st.session_state.setdefault("view","INTRO")
st.session_state.setdefault("cbt_step", 1)
st.session_state.setdefault("cbt_guided", True)
ensure_cbt_defaults(); ensure_reflection_defaults()

# ---------------- ヘルパー ----------------
def vibrate(ms=8):
    st.markdown("<script>try{{navigator.vibrate&&navigator.vibrate({ms})}}catch(e){{}}</script>", unsafe_allow_html=True)

def support(distress: Optional[int]=None, lonely: Optional[int]=None):
    def card(emoji: str, text: str, sub: Optional[str]=None):
        st.markdown(
            f"""
<div class="card" style="margin-top:6px;margin-bottom:8px">
  <div style="font-weight:900; color:var(--pink)">{emoji} {text}</div>
  {f"<div class='small' style='margin-top:2px; color:var(--muted)'>{sub}</div>" if sub else ""}
</div>
            """,
            unsafe_allow_html=True,
        )
    if distress is not None and distress >= 7:
        card("🫶","ここでは、がんばらなくて大丈夫です。","ご自身のペースで進めていただければ十分です。")
    elif lonely is not None and lonely >= 7:
        card("🤝","この瞬間、ひとりではありません。","深呼吸をひとつして、ゆっくり進めましょう。")
    else:
        card("🌟","ここまで入力いただけて十分です。","空欄があっても大丈夫です。")

# ---------------- ナビ ----------------
def top_nav(user_email: str):
    st.markdown('<div class="navbar">', unsafe_allow_html=True)
    left, right = st.columns([4,1])
    with left:
        keys = ["INTRO","HOME","CBT","REFLECT","HISTORY","EXPORT"]
        labels = {
            "INTRO":   "👋 はじめに",
            "HOME":    "🏠 ホーム",
            "CBT":     "📓 2分ノート",
            "REFLECT": "📝 1日のふり返り",
            "HISTORY": "📚 記録を見る",
            "EXPORT":  "⬇️ エクスポート・設定",
        }
        current = st.session_state.get("view","INTRO")
        idx = keys.index(current) if current in keys else 0
        choice = st.radio("移動先", options=keys, index=idx,
                          format_func=lambda k: labels[k], horizontal=True,
                          label_visibility="collapsed", key="nav_radio")
        st.session_state.view = choice
    with right:
        st.caption(f"👤 {user_email}")
        sign_out_button()
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- セレクタ（multiselect＝安定・白ボタンなし） ----------------
EMOJIS: List[Tuple[str,str]] = [
    ("😟","不安"),("😡","怒り"),("😢","悲しみ"),("😔","落ち込み"),
    ("😤","イライラ"),("😴","疲れ"),("🙂","安心"),("🤷‍♀️","戸惑い"),
]
TRIGGER_DEFS: List[Tuple[str,str]] = [
    ("⏱️","さっきの出来事"),
    ("🧠","浮かんだ一言"),
    ("🤝","人との関係"),
    ("🫀","体のサイン"),
    ("🌀","うまく言えない"),
]
LABEL_TO_VALUE = {
    "⏱️ さっきの出来事":"time",
    "🧠 浮かんだ一言":"thought_line",
    "🤝 人との関係":"relationship",
    "🫀 体のサイン":"body",
    "🌀 うまく言えない":"unknown",
}
VALUE_TO_LABEL = {v:k for k,v in LABEL_TO_VALUE.items()}

def emoji_selector(selected: List[str]) -> List[str]:
    options = [f"{e} {t}" for e,t in EMOJIS]
    default_labels = [f"{e} {t}" for e,t in EMOJIS if e in selected]
    picked = st.multiselect("いまの気持ち（複数選択可）", options=options, default=default_labels, help="後から外せます")
    out = [p.split(" ",1)[0] for p in picked]
    st.caption(f"選択中：{' '.join(out) if out else '（未選択）'}")
    return out

def trigger_selector(selected_values: List[str]) -> List[str]:
    options = list(LABEL_TO_VALUE.keys())
    defaults = [VALUE_TO_LABEL[v] for v in selected_values if v in VALUE_TO_LABEL]
    picked = st.multiselect("近かった“きっかけ”（複数選択可）", options=options, default=defaults)
    return [LABEL_TO_VALUE[p] for p in picked]

# ---------------- INTRO ----------------
def view_intro(user_email: str):
    top_nav(user_email)
    st.markdown("""
<div class="hero">
  <div class="topline">夜、考えすぎてしんどくなるときに。</div>
  <div class="maincopy">
    たった <span class="big3">3</span> ステップで<br>
    気持ちを整理して、少し落ち着こう。
  </div>
  <div class="what" style="margin-top:10px">
    <div class="title">これは何？</div>
    <div>しんどい夜に、短時間で“見方”を整えるノート。<br>
    正解探しではなく、気持ちを整える時間を届けます。</div>
  </div>
</div>
""", unsafe_allow_html=True)

    cta1, cta2 = st.columns([3,2])
    with cta1:
        st.markdown('<div class="cta-primary">', unsafe_allow_html=True)
        if st.button("① 今すぐはじめる（約2分）"):
            st.session_state.view="CBT"; st.session_state.cbt_step=1; st.session_state.cbt_guided=True
        st.markdown('</div>', unsafe_allow_html=True)
    with cta2:
        st.markdown('<div class="cta-ghost">', unsafe_allow_html=True)
        if st.button("ホームを見る"):
            st.session_state.view="HOME"
        st.markdown('</div>', unsafe_allow_html=True)

# ---------------- HOME ----------------
def view_home(user_email: str):
    top_nav(user_email)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 本日、どのように進めますか？")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("📓 2分ノートへ（3ステップ）"):
            st.session_state.view="CBT"; st.session_state.cbt_step=1; st.session_state.cbt_guided=True
    with c2:
        if st.button("📝 1日のふり返りへ（短く記録）"):
            st.session_state.view="REFLECT"
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- CBT ----------------
def _cbt_step_header():
    total = 3; step = st.session_state.cbt_step
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write(f"**2分ノート｜現在 {step} / {total}**")
    st.progress(step/total)
    left, right = st.columns(2)
    with left:
        st.session_state.cbt_guided = st.toggle("かんたんガイド（順番に表示）", value=st.session_state.cbt_guided)
    with right:
        st.caption("オフ＝全項目を一括表示")
    st.markdown('</div>', unsafe_allow_html=True)

def _cbt_step1():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("① いまの気持ちをえらぶ")
    st.session_state.cbt["emotions"] = emoji_selector(st.session_state.cbt.get("emotions", []))
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("しんどさ・確からしさ（ざっくりでOK）")
    cols = st.columns(2)
    with cols[0]:
        st.session_state.cbt["distress_before"] = st.slider("いまのしんどさ（0〜10）", 0, 10, int(st.session_state.cbt.get("distress_before",5)))
    with cols[1]:
        st.session_state.cbt["prob_before"] = st.slider("この考えの“ありえそう度”（%）", 0, 100, int(st.session_state.cbt.get("prob_before",50)))
    support(distress=st.session_state.cbt["distress_before"])
    st.markdown('</div>', unsafe_allow_html=True)

def _cbt_step2():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("② きっかけをえらぶ（近いものでOK）")
    st.session_state.cbt["trigger_tags"] = trigger_selector(st.session_state.cbt.get("trigger_tags", []))
    st.session_state.cbt["trigger_free"] = st.text_area(
        "任意の一言（なくてOK）",
        value=st.session_state.cbt.get("trigger_free",""),
        placeholder="例）返信がまだ／『また失敗する』と浮かんだ など",
        height=72
    )
    st.markdown('</div>', unsafe_allow_html=True)

def _cbt_step3():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("③ 見方の仮置き（短くでOK）")
    st.caption("左＝いまの見方／右＝ほかの見方（片方だけでもOK）")
    cols2 = st.columns(2)
    with cols2[0]:
        st.session_state.cbt["fact"] = st.text_area("いまの見方", value=st.session_state.cbt.get("fact",""),
                                                   placeholder="例）返事が遅い＝嫌われたかも など", height=108)
    with cols2[1]:
        st.session_state.cbt["alt"] = st.text_area("ほかの見方（別の説明・例外）", value=st.session_state.cbt.get("alt",""),
                                                  placeholder="例）移動中かも／前も夜に返ってきた など", height=108)
    st.subheader("視界をひろげる小さなチェック")
    st.caption("当てはまるものだけ軽くオンに。合わなければスルーでOK。")
    g = st.session_state.cbt.setdefault("checks", {})
    c1,c2 = st.columns(2)
    with c1:
        g["bw"] = st.checkbox("0/100で考えていたかも", value=bool(g.get("bw", False)))
        g["fortune"] = st.checkbox("先の展開を一つに決めていたかも", value=bool(g.get("fortune", False)))
        g["decide"] = st.checkbox("決めつけてしまっていたかも", value=bool(g.get("decide", False)))
    with c2:
        g["catastrophe"] = st.checkbox("最悪の状態を想定していたかも", value=bool
