# app.py
# Streamlit app: device_id(localStorage) + password 認証でユーザーを分離するサンプルフルコード
#
# 使い方:
# 1) Firestore を使う場合:
#    - Google Cloud サービスアカウント JSON をダウンロードして、
#      環境変数 GOOGLE_APPLICATION_CREDENTIALS を設定するか、
#      下の SERVICE_ACCOUNT_PATH にそのパスを指定してください。
#    - または Firestore を使いたくない場合は save_entry/load_entries を
#      ローカルファイルや st.session_state に差し替えてください（コメント参照）。
#
# 2) 実行:
#    pip install streamlit google-cloud-firestore
#    streamlit run app.py

from __future__ import annotations
import streamlit as st
import hashlib, time, json
from datetime import datetime
from typing import Optional, List, Dict

# Firestore の使用をコメントアウトしてローカルに切り替え可能
USE_FIRESTORE = True

# --- Firestore 設定（必要に応じてパスを指定） ---
SERVICE_ACCOUNT_PATH = "path/to/service_account.json"  # ← 必要なら書き換え
FIRESTORE_PROJECT_ID = None  # None の場合 JSON の project_id を使います

if USE_FIRESTORE:
    try:
        from google.cloud import firestore
        import google.oauth2.service_account as service_account
    except Exception as e:
        st.error("Firestore を使う設定になっていますが google-cloud-firestore ライブラリが見つかりません。\n\n`pip install google-cloud-firestore` を実行してください。")
        st.stop()

# ----------------- ヘルパー -----------------
def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def now_ts() -> float:
    return time.time()

def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

# ----------------- Firestore 用ラッパー -----------------
if USE_FIRESTORE:
    def get_firestore_client():
        # 優先順: 環境変数 GOOGLE_APPLICATION_CREDENTIALS がセットされていればそれを使う
        import os
        if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            cred = None
            client = firestore.Client(project=FIRESTORE_PROJECT_ID) if FIRESTORE_PROJECT_ID else firestore.Client()
        else:
            # 直接 SERVICE_ACCOUNT_PATH を指定して認証
            try:
                creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_PATH)
                client = firestore.Client(project=FIRESTORE_PROJECT_ID or None, credentials=creds)
            except Exception as e:
                st.error("Firestore 認証に失敗しました。環境変数 GOOGLE_APPLICATION_CREDENTIALS を設定するか SERVICE_ACCOUNT_PATH を修正してください。\n\n" + str(e))
                st.stop()
        return client

    fs_client = get_firestore_client()

    def save_entry(user_doc_id: str, entry: Dict):
        """ユーザー配下にエントリを保存（Firestore）"""
        col = fs_client.collection("users").document(user_doc_id).collection("entries")
        col.add(entry)

    def load_entries(user_doc_id: str) -> List[Dict]:
        col = fs_client.collection("users").document(user_doc_id).collection("entries")
        docs = col.order_by("ts", direction=firestore.Query.DESCENDING).stream()
        out = []
        for d in docs:
            data = d.to_dict()
            data["_id"] = d.id
            out.append(data)
        return out

    def ensure_user_meta(user_doc_id: str, meta: Dict):
        doc_ref = fs_client.collection("users").document(user_doc_id)
        doc = doc_ref.get()
        if not doc.exists:
            doc_ref.set(meta)
        else:
            # 既存の場合は名前だけアップデートする等
            doc_ref.set(meta, merge=True)

else:
    # ローカルモック: st.session_state に保存（簡易デバッグ用）
    def save_entry(user_doc_id: str, entry: Dict):
        db = st.session_state.setdefault("_local_db", {})
        user_list = db.setdefault(user_doc_id, [])
        user_list.append(entry)
        st.session_state["_local_db"] = db

    def load_entries(user_doc_id: str) -> List[Dict]:
        db = st.session_state.get("_local_db", {})
        return list(sorted(db.get(user_doc_id, []), key=lambda e: e["ts"], reverse=True))

    def ensure_user_meta(user_doc_id: str, meta: Dict):
        db = st.session_state.setdefault("_local_meta", {})
        if user_doc_id not in db:
            db[user_doc_id] = meta
        else:
            db[user_doc_id].update(meta)
        st.session_state["_local_meta"] = db

# ----------------- device_id を取得するための仕組み -----------------
# 流れ：
# 1) 最初に device_id クエリパラメータが無ければ JS を利用して localStorage の device_id を生成して
#    現在の URL に ?device_id=xxx を付けてリダイレクトする（ブラウザで一度だけ実行）
# 2) 以降 Streamlit は st.experimental_get_query_params() で device_id を受け取る

DEVICE_JS = """
<script>
(function(){
  try {
    const KEY = "withyou_device_id_v1";
    let id = localStorage.getItem(KEY);
    if (!id) {
      // UUIDv4 生成
      id = ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
      );
      localStorage.setItem(KEY, id);
    }
    // 現在の URL に device_id クエリを付ける（ページをリダイレクト）
    const params = new URLSearchParams(window.location.search);
    if (params.get("device_id") !== id) {
      params.set("device_id", id);
      const base = window.location.pathname;
      const newUrl = base + "?" + params.toString();
      window.location.href = newUrl;
    } else {
      // 既にある場合はそのまま
    }
  } catch (e) {
    console.error(e);
  }
})();
</script>
"""

# ----------------- Streamlit UI / ロジック -----------------
st.set_page_config(page_title="WithYou — device+password login", page_icon="🌙", layout="centered")
st.title("WithYou — 入室 (device + password)")

# 1) device_id がクエリに無ければ JS で生成して再ロードさせる（このコンポーネントは一時的）
query_params = st.experimental_get_query_params()
device_id = query_params.get("device_id", [None])[0]

if not device_id:
    st.info("ブラウザの識別子を準備しています。ページが自動でリロードされます。")
    st.components.v1.html(DEVICE_JS)
    st.stop()

# （オプション）device_id の短縮表示
short_device = device_id[:8] + "…" if device_id else "—"

st.sidebar.markdown(f"**Device ID:** `{short_device}`")
st.sidebar.caption("※端末ごとに一意のID（ブラウザの localStorage）を利用しています。")

# ログインフォーム
with st.form("login_form"):
    st.subheader("入室情報")
    display_name = st.text_input("表示名（任意）", value=st.session_state.get("display_name",""))
    password = st.text_input("入室パスワード", type="password", placeholder="例: my-secret-code")
    remember_name = st.checkbox("この端末で表示名を保存する", value=True)
    col1, col2 = st.columns([1,1])
    with col1:
        submit = st.form_submit_button("入室する")
    with col2:
        regen = st.form_submit_button("端末IDを再作成（この端末のみ）")

# 端末IDを再作成（localStorage を強制再生成したい場合）
if regen:
    # 再生成するには JS で localStorage をクリアしてリダイレクトする
    regen_js = """
    <script>
      localStorage.removeItem("withyou_device_id_v1");
      // リロードして新しい device_id を作らせる
      location.reload();
    </script>
    """
    st.components.v1.html(regen_js)
    st.stop()

if submit:
    if not password:
        st.warning("パスワードを入力してください。")
        st.stop()

    # ユーザー識別子を作成（device_id + password のハッシュ）
    # -> 同一端末 + 同一パスワード なら同じIDになり、複数回入室できる
    # -> 別端末で同じパスワードを入力しても device_id が違うので別ID（他人の記録閲覧不可）
    user_doc_id = sha256_hex(device_id + ":" + password)

    # オプションで表示名保存
    if remember_name and display_name:
        st.session_state["display_name"] = display_name

    # ユーザーのメタ情報を Firestore に保存（初回だけ）
    meta = {
        "display_name": display_name or "匿名",
        "created_at": now_iso(),
        "device_short": short_device,
        # device_id をそのまま保存するかは運用で判断（プライバシー）
        # "device_id_hash": sha256_hex(device_id)
    }
    ensure_user_meta(user_doc_id, meta)

    # セッションにログイン情報を保持
    st.session_state["user_doc_id"] = user_doc_id
    st.session_state["logged_in"] = True
    st.experimental_rerun()

# ログイン済みならメイン画面
if st.session_state.get("logged_in"):
    user_doc_id = st.session_state["user_doc_id"]
    st.success("入室しました。")
    st.write("表示名:", st.session_state.get("display_name","匿名"))
    st.write("あなたの端末識別子（短縮）:", short_device)

    # 新しいエントリを書く UI
    st.markdown("---")
    st.subheader("日記／メモを残す")
    with st.form("entry_form"):
        title = st.text_input("タイトル（任意）", "")
        body = st.text_area("内容", "")
        save_btn = st.form_submit_button("保存する")
    if save_btn:
        if not body.strip():
            st.warning("内容を入力してください。")
        else:
            entry = {
                "title": title,
                "body": body,
                "ts": now_ts(),
                "created_at": now_iso(),
                "device_short": short_device,
            }
            save_entry(user_doc_id, entry)
            st.success("保存しました。")
            st.experimental_rerun()

    # 保存済みエントリを表示
    st.markdown("---")
    st.subheader("あなたの保存データ（最新順）")
    try:
        entries = load_entries(user_doc_id)
        if not entries:
            st.info("まだ記録がありません。上のフォームから保存できます。")
        else:
            for e in entries:
                ts = datetime.utcfromtimestamp(e["ts"]).strftime("%Y-%m-%d %H:%M:%S UTC") if "ts" in e else e.get("created_at", "")
                with st.expander(f"{e.get('title','(無題)')} — {ts}", expanded=False):
                    st.write(e.get("body",""))
    except Exception as e:
        st.error("データの読み込み中にエラーが発生しました: " + str(e))

    # ログアウト（セッションのみ解除、端末側 device_id は残る）
    if st.button("ログアウト（このブラウザのセッションからのみ）"):
        for k in ["user_doc_id","logged_in"]:
            if k in st.session_state: del st.session_state[k]
        st.success("ログアウトしました。ページをリロードしています。")
        st.experimental_rerun()

    # オプション: 他の端末で同じパスワードを使っても別ユーザーになる旨を説明
    st.info("注意：同じパスワードでも別の端末で入室すると別ユーザーとして扱われます（端末ID が異なるため）。")

else:
    st.info("入室してください（まだログインしていません）。")
    # ログインフォームが上にあるのでここでは何もしない
    pass
