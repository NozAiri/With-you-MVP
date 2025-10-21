# app.py — Sora 本番版（セーフモードUIなし・白画面対策）
# 端末ローカル保存のみ（/data/*.csv）。専門用語なし、UIは明るい星空、戻るボタン常設。

from datetime import datetime, date, timedelta
from pathlib import Path
import time, uuid, json, io
import pandas as pd
import streamlit as st

# ================== 基本設定（1回だけ） ==================
st.set_page_config(page_title="Sora — しんどい夜の2分ノート", page_icon="🌙", layout="centered")

# ================== データ保存まわり ==================
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
CSV_BREATH       = DATA_DIR/"breath.csv"
CSV_FEEL         = DATA_DIR/"feel.csv"
CSV_JOURNAL      = DATA_DIR/"journal.csv"
CSV_DAY          = DATA_DIR/"day.csv"
CSV_STUDY        = DATA_DIR/"study.csv"
CSV_SUBJECTS     = DATA_DIR/"subjects.csv"
CSV_STUDY_GOALS  = DATA_DIR/"study_goals.csv"

def now_ts() -> str:
    return datetime.now().isoformat(timespec="seconds")

def load_csv(p: Path) -> pd.DataFrame:
    if not p.exists(): return pd.DataFrame()
    try: return pd.read_csv(p)
    except Exception: return pd.DataFrame()

def save_csv(p: Path, df: pd.DataFrame) -> bool:
    try: df.to_csv(p, index=False); return True
    except Exception: return False

def append_csv(p: Path, row: dict) -> bool:
    df = load_csv(p)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    return save_csv(p, df)

def week_range(d: date | None = None):
    d = d or date.today()
    start = d - timedelta(days=d.weekday())   # 月曜
    end = start + timedelta(days=6)           # 日曜
    return start, end

# ================== セッション状態 ==================
ss = st.session_state
ss.setdefault("view", "HOME")
ss.setdefault("first_breath", False)
ss.setdefault("breath_active", False)
ss.setdefault("breath_stop", False)
ss.setdefault("auto_guide", "soft")   # "soft"=吸4吐6 / "calm"=吸5止2吐6
ss.setdefault("breath_runs", 0)
ss.setdefault("rest_until", None)
ss.setdefault("em", {})               # 感情選択： {ラベル: 強さ1〜5}
ss.setdefault("tg", set())            # きっかけ選択： set

# 科目・目標（壊れCSVでも落ちない）
try:
    if "subjects" not in ss:
        if CSV_SUBJECTS.exists():
            _s = pd.read_csv(CSV_SUBJECTS)
            ss["subjects"] = _s["subject"].dropna().unique().tolist() or ["国語","数学","英語"]
            ss["subject_notes"] = {r["subject"]: r.get("note","") for _,r in _s.iterrows()}
        else:
            ss["subjects"] = ["国語","数学","英語"]
            ss["subject_notes"] = {}
except Exception:
    ss["subjects"] = ["国語","数学","英語"]
    ss["subject_notes"] = {}

try:
    if "daily_goal" not in ss:
        if CSV_STUDY_GOALS.exists():
            _g = pd.read_csv(CSV_STUDY_GOALS)
            dg = _g[_g["key"]=="daily_goal"]
            ss["daily_goal"] = int(dg["value"].iloc[0]) if not dg.empty else 30
            ss["weekly_subject_goals"] = {r["subject"]: int(r["value"]) for _,r in _g[_g["key"]=="weekly"].iterrows()}
        else:
            ss["daily_goal"] = 30
            ss["weekly_subject_goals"] = {}
except Exception:
    ss["daily_goal"] = 30
    ss["weekly_subject_goals"] = {}

# ================== スタイル（明るい星空＋読みやすい文字） ==================
st.markdown("""
<style>
:root{ --text:#1c1630; --muted:#6b6780; --glass:rgba(255,255,255,.96); --brd:rgba(185,170,255,.28); }
.stApp{
  background: radial-gradient(1200px 600px at 20% -10%, #fff7fb 0%, #f7f1ff 45%, #ecf9ff 100%);
  position:relative; overflow-x:hidden;
}
.stApp::before{
  content:""; position:absolute; inset:-20% -10% auto -10%; height:160%;
  background:
    radial-gradient(2px 2px at 10% 20%, #ffffffaa 30%, transparent 70%),
    radial-gradient(2px 2px at 40% 10%, #ffffff88 30%, transparent 70%),
    radial-gradient(2px 2px at 70% 30%, #ffffffaa 30%, transparent 70%),
    radial-gradient(1.6px 1.6px at 85% 60%, #ffffff77 40%, transparent 60%),
    radial-gradient(1.8px 1.8px at 25% 70%, #ffffff99 40%, transparent 60%);
  animation: twinkle 6s ease-in-out infinite;
  pointer-events:none;
}
@keyframes twinkle{ 0%,100%{opacity:.7; transform:translateY(0)} 50%{opacity:1; transform:translateY(-2px)} }
.block-container{ max-width:980px; padding-top:1rem; padding-bottom:1.6rem }
h1,h2,h3{ color:var(--text); letter-spacing:.2px }
.small{ color:var(--muted); font-size:.92rem }
.card{ background:var(--glass); border:1px solid var(--brd); border-radius:20px; padding:16px; margin:10px 0 14px;
       box-shadow:0 18px 36px rgba(50,40,90,.14); backdrop-filter:blur(6px); }
.row{ display:grid; grid-template-columns:1fr 1fr; gap:14px }
@media(max-width:780px){ .row{ grid-template-columns:1fr } }
.tile .stButton>button{
  width:100%; min-height:120px; border-radius:18px; text-align:left; padding:18px; font-weight:900;
  background:linear-gradient(155deg,#ffe8f4,#fff3fb); color:#2a2731; border:1px solid #f5e8ff;
  box-shadow:0 14px 28px rgba(60,45,90,.12)
}
.tile.alt .stButton>button{ background:linear-gradient(155deg,#e9f4ff,#f6fbff) }
.cta .stButton>button{
  width:100%; padding:12px 14px; border-radius:999px; border:1px solid #eadfff;
  background:linear-gradient(180deg,#a89bff,#7b6cff); color:#fff; font-weight:900; font-size:1.02rem;
  box-shadow:0 16px 30px rgba(123,108,255,.28);
}
.phase{ display:inline-block; padding:.25rem .85rem; border-radius:999px; font-weight:800;
  background:rgba(123,108,255,.12); color:#5d55ff; border:1px solid rgba(123,108,255,.32); }
.center{ text-align:center }
.circle-wrap{ display:flex; justify-content:center; align-items:center; height:280px; }
.breath-circle{
  width:180px; height:180px; border-radius:50%; background:radial-gradient(circle at 50% 40%, #fff, #f2ebff);
  border:2px solid #e7dcff; box-shadow:0 0 80px 10px rgba(123,108,255,.16) inset, 0 18px 48px rgba(30,20,70,.18);
  transition: transform .8s ease-in-out;
}
.count{ font-size:44px; font-weight:900; text-align:center; color:#2f2a3b; margin-top:6px; }
.badge{ display:inline-block; padding:.35rem .7rem; border-radius:999px; border:1px solid #e6e0ff; background:#fff; font-weight:800 }
.progress-wrap{ display:flex; align-items:center; gap:10px }
.progress-bar{ flex:1; height:12px; border-radius:999px; background:#f1ecff; position:relative; overflow:hidden; border:1px solid #e3dcff}
.progress-bar > div{ position:absolute; left:0; top:0; bottom:0; width:0%; background:linear-gradient(90deg,#a89bff,#7b6cff)}
</style>
""", unsafe_allow_html=True)

# ================== 共通UI ==================
def header(title: str):
    cols = st.columns([1,7])
    with cols[0]:
        if st.button("← ホームへ", use_container_width=True):
            ss.view = "HOME"
            st.stop()
    with cols[1]:
        st.markdown(f"### {title}")

# ================== HOME ==================
def view_home():
    st.markdown("## 🌙 Sora — しんどい夜の2分ノート")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("**言葉の前に、息をひとつ。** 迷わず “呼吸で落ち着く → 感情を整える → 今日を書いておく → 勉強の進捗を見える化”。")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="row">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="tile">', unsafe_allow_html=True)
        if st.button("🌬 呼吸で落ち着く（1–3分）", use_container_width=True):
            ss.view = "BREATH"
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="tile alt">', unsafe_allow_html=True)
        if st.button("🙂 感情を整える（3ステップ）", use_container_width=True):
            ss.view = "FEEL"
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="row">', unsafe_allow_html=True)
    col3, col4 = st.columns(2)
    with col3:
        st.markdown('<div class="tile alt">', unsafe_allow_html=True)
        if st.button("📝 自由ジャーナル", use_container_width=True):
            ss.view = "JOURNAL"
        st.markdown('</div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="tile">', unsafe_allow_html=True)
        if st.button("📅 一日の振り返り", use_container_width=True):
            ss.view = "DAY"
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="tile alt">', unsafe_allow_html=True)
    if st.button("📚 Study Tracker（科目×時間×メモ×進捗）", use_container_width=True):
        ss.view = "STUDY"
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card cta">', unsafe_allow_html=True)
    if st.button("📦 記録を見る / エクスポート", use_container_width=True):
        ss.view = "HISTORY"
    st.markdown('</div>', unsafe_allow_html=True)

# ================== 呼吸ワーク ==================
def view_breath():
    header("🌬 呼吸で落ち着く")

    # セーフティ（3回連続→短い休憩）
    if ss.rest_until and datetime.now() < ss.rest_until:
        left = int((ss.rest_until - datetime.now()).total_seconds())
        st.info(f"少し休憩しよう（過換気予防）。{left} 秒後に再開できます。"); return
    if ss.breath_runs >= 3:
        ss.rest_until = datetime.now() + timedelta(seconds=30)
        ss.breath_runs = 0

    first = not ss.first_breath
    # 初回は90秒固定（UI非表示）/ 2回目以降は選択可
    length = 90 if first else st.radio("時間（固定プリセット）", [60,90,180], index=1, horizontal=True)

    mode = ss.auto_guide
    guide_name = "吸4・吐6（やさしめ）" if mode=="soft" else "吸5・止2・吐6（落ち着き）"
    with st.expander("ガイド（自動切替）", expanded=False):
        st.caption(f"いま: **{guide_name}**")

    silent = st.toggle("言葉を最小にする（“いっしょに息を / ここにいていい”）", value=True)
    enable_sound = st.toggle("そっと効果音を添える（無音でもOK）", value=False)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    seq = [("吸う",4),("吐く",6)] if mode=="soft" else [("吸う",5),("止める",2),("吐く",6)]
    phase = st.empty(); circle = st.empty(); count = st.empty(); bar = st.progress(0)
    c1,c2 = st.columns(2)
    start = c1.button("開始", use_container_width=True, disabled=ss.breath_active)
    stopb = c2.button("× 停止", use_container_width=True)
    if stopb: ss.breath_stop = True

    def tone(kind:str):
        if not enable_sound: return
        try:
            import numpy as np, soundfile as sf  # 無ければexceptへ
            sr=22050; sec=0.25 if kind!="吸う" else 0.35
            f=220 if kind=="吸う" else (180 if kind=="止める" else 150)
            t=np.linspace(0,sec,int(sr*sec),False)
            w=0.15*np.sin(2*np.pi*f*t)*np.hanning(len(t))
            buf=io.BytesIO(); sf.write(buf,w,sr,format="WAV"); st.audio(buf.getvalue(), format="audio/wav")
        except Exception:
            pass

    if start or ss.breath_active:
        ss.breath_active = True
        ss.breath_stop = False
        ss.first_breath = True

        base = sum(t for _,t in seq)
        cycles = max(1, length // base)
        remain = length - cycles*base
        total_ticks = cycles*base + remain
        tick = 0

        if silent:
            st.markdown('<div class="center small">いっしょに息を / ここにいていい</div>', unsafe_allow_html=True)

        for _ in range(cycles):
            for name,sec in seq:
                if ss.breath_stop: break
                phase.markdown(f"<span class='phase'>{name}</span>", unsafe_allow_html=True)
                tone(name)
                for s in range(sec,0,-1):
                    if ss.breath_stop: break
                    scale = 1.12 if name=="吸う" else (1.0 if name=="止める" else 0.88)
                    circle.markdown(
                        f"<div class='circle-wrap'><div class='breath-circle' style='transform:scale({scale});'></div></div>",
                        unsafe_allow_html=True
                    )
                    count.markdown(f"<div class='count'>{s}</div>", unsafe_allow_html=True)
                    tick += 1; bar.progress(min(int(tick/total_ticks*100),100))
                    time.sleep(1)
            if ss.breath_stop: break

        for r in range(remain,0,-1):
            if ss.breath_stop: break
            circle.markdown(f"<div class='circle-wrap'><div class='breath-circle' style='transform:scale(0.88);'></div></div>", unsafe_allow_html=True)
            count.markdown(f"<div class='count'>{r}</div>", unsafe_allow_html=True)
            tick += 1; bar.progress(min(int(tick/total_ticks*100),100)); time.sleep(1)

        ss.breath_active = False

        if ss.breath_stop:
            phase.markdown("<span class='phase'>停止しました</span>", unsafe_allow_html=True)
            ss.breath_stop = False
        else:
            phase.markdown("<span class='phase'>完了</span>", unsafe_allow_html=True)
            st.caption("ここまで来たあなたは十分えらい。")
            feel = st.radio("いまの感じ（任意）", ["変わらない","少し落ち着いた","かなり落ち着いた"], index=1, horizontal=True)
            ss.breath_runs += 1
            if feel=="かなり落ち着いた" and ss.auto_guide=="soft":
                ss.auto_guide = "calm"
            task = st.text_input("1分タスク（任意）", placeholder="例：水を一口 / 窓を少し開ける / 手首を冷水10秒 / 姿勢を1ミリ")
            note = st.text_input("メモ（任意・非共有）", placeholder="例：胸のつかえが少し軽い")
            if st.button("💾 保存", type="primary"):
                row = {"id":str(uuid.uuid4())[:8],"ts":now_ts(),"sec":length,"guide":ss.auto_guide,
                       "task":task,"note":note}
                append_csv(CSV_BREATH,row); st.success("保存しました。")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown('<div class="card cta">', unsafe_allow_html=True)
    if st.button("← ホームへ戻る", use_container_width=True):
        ss.view = "HOME"
    st.markdown("</div>", unsafe_allow_html=True)

# ================== 感情ワーク（絵文字→きっかけ→やさしい見かた→一歩） ==================
EMOJIS = [("怒り","😠"),("かなしい","😢"),("ふあん","😟"),("罪悪感","😔"),("はずかしい","😳"),
          ("あせり","😣"),("たいくつ","😐"),("ほっとする","🙂"),("うれしい","😊")]
TRIGGERS = ["今日の出来事","友だち","家族","部活","クラス","先生","SNS","勉強","宿題","体調","お金","将来"]

def view_feel():
    header("🙂 感情を整える（3ステップ）")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("**いまの気持ち**（えらんでください・複数OK）")
    em = ss.em
    cols = st.columns(3)
    for i,(label,emoji) in enumerate(EMOJIS):
        with cols[i%3]:
            on = st.toggle(f"{emoji} {label}", value=label in em, key=f"emo_{label}")
            if on:
                em[label] = st.slider(f"{label} の強さ",1,5, em.get(label,3), key=f"lv_{label}")
            else:
                em.pop(label, None)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("**きっかけに近いもの**（複数OK）")
    tg = ss.tg
    tcols = st.columns(3)
    for i,t in enumerate(TRIGGERS):
        with tcols[i%3]:
            if st.checkbox(t, value=(t in tg), key=f"tr_{t}"): tg.add(t)
            else: tg.discard(t)
    free = st.text_input("一言メモ（任意）", placeholder="例：LINEの返事がこなかった")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("**やさしい見かたのヒント**（じぶんの言葉でOK）")
    hint = st.selectbox("しっくりくるもの", [
        "全部ダメだと思った → “いまの一つがむずかしいだけ”かも",
        "先の心配でいっぱい → “まず今日の5分”からでOK",
        "相手の気持ちを決めつけた → “本当のところは分からない”かも",
        "自分ばかり悪いと思った → “環境やタイミングの影響”もあるかも",
        "良かった点を見落としてる → “できた一つ”を足してバランスに",
    ], index=1)
    alt = st.text_area("置きかえてみる（任意）", value=hint, height=90)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    step = st.text_input("今日の一歩（1〜3分で終わること・自由記入）",
                         placeholder="例：タイマー1分だけ机に向かう / スタンプだけ送る / 外の光を5分あびる")
    st.markdown('</div>', unsafe_allow_html=True)

    c1,c2 = st.columns(2)
    with c1:
        if st.button("💾 保存して要約を見る", type="primary", use_container_width=True):
            row = {"id":str(uuid.uuid4())[:8],"ts":now_ts(),
                   "emotions":json.dumps(ss.em,ensure_ascii=False),
                   "triggers":json.dumps(list(ss.tg),ensure_ascii=False),
                   "free":free,"reframe":alt,"step":step}
            append_csv(CSV_FEEL,row); ss["last_feel"]=row; st.success("保存しました。")
    with c2:
        if st.button("入力をクリア", use_container_width=True):
            ss.em={}; ss.tg=set(); st.experimental_rerun()

    if ss.get("last_feel"):
        r = ss["last_feel"]
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.write("**要約**（一画面）")
        emo_txt = "・".join([f"{k}×{v}" for k,v in json.loads(r["emotions"]).items()]) if r["emotions"] else "—"
        tri_txt = "・".join(json.loads(r["triggers"])) if r["triggers"] else "—"
        st.markdown(f"- 気持ち：{emo_txt}")
        st.markdown(f"- きっかけ：{tri_txt} / {r.get('free','')}")
        st.markdown(f"- やさしい見かた：{r.get('reframe','')}")
        st.markdown(f"- 今日の一歩：{r.get('step','')}")
        st.markdown('</div>', unsafe_allow_html=True)

# ================== 自由ジャーナル ==================
def view_journal():
    header("📝 自由ジャーナル")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    txt = st.text_area("思ったことをそのまま書いてOK（保存は端末のみ・共有なし）", height=260,
                       placeholder="例：いまの気持ち、もやもや、気づいたこと、だれにも見せない自分の言葉。")
    if st.button("💾 保存", type="primary"):
        row={"id":str(uuid.uuid4())[:8],"ts":now_ts(),"text":txt}
        append_csv(CSV_JOURNAL,row); st.success("保存しました。")
    st.markdown('</div>', unsafe_allow_html=True)

# ================== 一日の振り返り ==================
def view_day():
    header("📅 一日の振り返り")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    mood = st.slider("いまの気分（0=しんどい / 10=落ち着いている）", 0, 10, 5)
    today_note = st.text_area("今日の出来事（メモでOK）", height=120, placeholder="例：空がきれいだった／ご飯がおいしかった など")
    tomorrow = st.text_input("明日したいこと（1つ）", placeholder="例：朝に10分だけ英単語")
    if st.button("💾 保存", type="primary"):
        row={"id":str(uuid.uuid4())[:8],"ts":now_ts(),"mood":mood,"today":today_note,"tomorrow":tomorrow}
        append_csv(CSV_DAY,row); st.success("保存しました。")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("**最近の記録**")
    df = load_csv(CSV_DAY)
    if df.empty:
        st.caption("まだ記録がありません。")
    else:
        try: df["ts"] = pd.to_datetime(df["ts"]); df = df.sort_values("ts", ascending=False)
        except Exception: pass
        for _,r in df.head(10).iterrows():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"**🕒 {r.get('ts','')}**")
            st.markdown(f"- 気分：{r.get('mood','')}")
            st.markdown(f"- 今日：{r.get('today','')}")
            st.markdown(f"- 明日：{r.get('tomorrow','')}")
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ================== Study Tracker（科目×時間×メモ×進捗） ==================
def save_goals_to_csv():
    rows = [{"key":"daily_goal","subject":"","value":ss.daily_goal}]
    for s in ss.subjects:
        rows.append({"key":"weekly","subject":s,"value":int(ss.weekly_subject_goals.get(s,0))})
    pd.DataFrame(rows).to_csv(CSV_STUDY_GOALS, index=False)

def view_study():
    header("📚 Study Tracker（科目×時間×メモ×進捗）")

    # 目標
    st.markdown('<div class="card">', unsafe_allow_html=True)
    colg1, colg2 = st.columns([2,1])
    with colg1:
        st.write("**今日の勉強目標（分）**")
        ss.daily_goal = st.number_input("目標分（毎日）", min_value=0, max_value=600, value=int(ss.daily_goal), step=5)
    with colg2:
        if st.button("💾 目標を保存"): save_goals_to_csv(); st.success("目標を保存しました。")
    st.markdown('</div>', unsafe_allow_html=True)

    # 科目の管理
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("**科目の追加 / 並べ替え / 各科目メモ**")
    colA, colB = st.columns([2,1])
    with colA:
        new_subj = st.text_input("科目を追加", placeholder="例：小論 / 過去問 / 面接 / 実技 など")
        if st.button("＋ 追加"):
            name = new_subj.strip()
            if name and name not in ss.subjects:
                ss.subjects.append(name)
                ss.subject_notes.setdefault(name, "")
                ss.weekly_subject_goals.setdefault(name, 0)
                pd.DataFrame([{"subject": s, "note": ss.subject_notes.get(s,"")} for s in ss.subjects]).to_csv(CSV_SUBJECTS, index=False)
                save_goals_to_csv(); st.success(f"「{name}」を追加しました。")
    with colB:
        if ss.subjects:
            up_subj = st.selectbox("上に移動", ss.subjects)
            if st.button("▲ 上へ"):
                idx = ss.subjects.index(up_subj)
                if idx>0:
                    ss.subjects[idx-1], ss.subjects[idx] = ss.subjects[idx], ss.subjects[idx-1]
                    pd.DataFrame([{"subject": s, "note": ss.subject_notes.get(s,"")} for s in ss.subjects]).to_csv(CSV_SUBJECTS, index=False)

    if ss.subjects:
        tabs = st.tabs(ss.subjects)
        for i, s in enumerate(ss.subjects):
            with tabs[i]:
                c1,c2 = st.columns([3,1])
                with c1:
                    txt = st.text_area(f"「{s}」のメモ", value=ss.subject_notes.get(s,""),
                                       placeholder="例：関数文章題のコツ／英単語は朝が楽 など", height=90, key=f"note_{s}")
                with c2:
                    goal = st.number_input(f"今週の目標（分）  \n{s}", min_value=0, max_value=2000,
                                           value=int(ss.weekly_subject_goals.get(s,0)), step=5, key=f"goal_{s}")
                if st.button(f"💾 {s} を保存", key=f"save_{s}"):
                    ss.subject_notes[s] = txt
                    ss.weekly_subject_goals[s] = int(goal)
                    pd.DataFrame([{"subject": ssb, "note": ss.subject_notes.get(ssb,"")} for ssb in ss.subjects]).to_csv(CSV_SUBJECTS, index=False)
                    save_goals_to_csv(); st.success("保存しました。")
    st.markdown('</div>', unsafe_allow_html=True)

    # 記録
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("**学習ブロックを記録**（あとからメモ可）")
    col1, col2 = st.columns(2)
    with col1:
        subject = st.selectbox("科目", ss.subjects)
        minutes = st.select_slider("時間（分）", options=[5,10,15,20,25,30,45,60,75,90], value=15)
    with col2:
        feel = st.radio("手触り", ["😌 集中できた","😕 難航した","😫 しんどい"], horizontal=False, index=0)
        note = st.text_input("メモ（任意）", placeholder="例：例題→教科書の順が合う／夜より朝が楽 など")
    if st.button("🧭 記録する", type="primary"):
        row = {"id": str(uuid.uuid4())[:8], "ts": now_ts(), "date": datetime.now().date().isoformat(),
               "subject": subject, "minutes": int(minutes), "blocks15": max(1, round(int(minutes)/15)), "feel": feel, "note": note}
        append_csv(CSV_STUDY, row); st.success("記録しました。")
    st.markdown('</div>', unsafe_allow_html=True)

    # 可視化
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("**進捗と見える化**")
    df = load_csv(CSV_STUDY); today = datetime.now().date()
    if df.empty:
        st.caption("まだ記録がありません。")
    else:
        try: df["date"] = pd.to_datetime(df["date"]).dt.date
        except Exception: pass

        # 今日
        td = df[df["date"]==today].copy()
        total_today = int(td["minutes"].sum()) if not td.empty else 0
        goal = max(1, int(ss.daily_goal)); pct = min(100, int(total_today/goal*100))
        st.markdown("**今日の合計**")
        st.markdown(f"<div class='progress-wrap'><div class='progress-bar'><div style='width:{pct}%'></div></div><div>{total_today}/{goal}分</div></div>", unsafe_allow_html=True)

        # 今週
        ws,we = week_range()
        w = df[(df["date"]>=ws) & (df["date"]<=we)].copy()
        if w.empty:
            st.caption("今週の記録はまだありません。")
        else:
            agg = w.groupby("subject", as_index=False)["minutes"].sum().sort_values("minutes", ascending=False)
            st.dataframe(agg.rename(columns={"subject":"科目","minutes":"合計（分）"}), use_container_width=True, hide_index=True)
            for _,r in agg.iterrows():
                s = r["subject"]; done = int(r["minutes"]); g = int(ss.weekly_subject_goals.get(s,0))
                if g>0:
                    p = min(100, int(done/g*100))
                    st.markdown(f"・{s}：<div class='progress-wrap'><div class='progress-bar'><div style='width:{p}%'></div></div><div>{done}/{g}分</div></div>", unsafe_allow_html=True)

        # 直近14日
        last14 = pd.DataFrame({"date": [today - timedelta(days=i) for i in range(13,-1,-1)]})
        if not df.empty:
            daily = df.groupby("date", as_index=False)["minutes"].sum()
            last14 = last14.merge(daily, on="date", how="left").fillna({"minutes":0})
        try:
            import matplotlib.pyplot as plt  # あればグラフ、なければ表で代替
            fig2 = plt.figure(figsize=(6.5,3))
            plt.plot([d.strftime("%m/%d") for d in last14["date"]], last14["minutes"])
            plt.title("直近14日 合計分"); plt.ylabel("分"); plt.xticks(rotation=30, ha="right")
            st.pyplot(fig2)
        except Exception:
            st.dataframe(last14.rename(columns={"date":"日付","minutes":"分"}), use_container_width=True, hide_index=True)

        if not w.empty:
            feel_counts = w.groupby("feel")["subject"].count().reset_index().rename(columns={"subject":"件数"})
            st.caption("**手触りの分布（件数・今週）**")
            st.dataframe(feel_counts, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # エクスポート
    st.markdown('<div class="card">', unsafe_allow_html=True)
    full = load_csv(CSV_STUDY)
    if not full.empty:
        csv = full.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Study Tracker（CSV）をダウンロード", data=csv, file_name="study.csv", mime="text/csv")
    st.markdown('</div>', unsafe_allow_html=True)

# ================== 記録とエクスポート ==================
def view_history():
    header("📦 記録とエクスポート")

    # 感情
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 感情の記録")
    df = load_csv(CSV_FEEL)
    if df.empty: st.caption("まだ記録がありません。")
    else:
        try: df["ts"]=pd.to_datetime(df["ts"]); df=df.sort_values("ts", ascending=False)
        except Exception: pass
        for _,r in df.head(20).iterrows():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"**🕒 {r.get('ts','')}**")
            st.caption(f"気持ち：{r.get('emotions','')}")
            st.caption(f"きっかけ：{r.get('triggers','')} / {r.get('free','')}")
            st.markdown(f"**やさしい見かた**：{r.get('reframe','')}")
            if r.get("step"): st.markdown(f"**今日の一歩**：{r.get('step','')}")
            st.markdown('</div>', unsafe_allow_html=True)
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ 感情（CSV）", data=csv, file_name="feel.csv", mime="text/csv")
    st.markdown('</div>', unsafe_allow_html=True)

    # 呼吸
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 呼吸の記録")
    bd = load_csv(CSV_BREATH)
    if bd.empty: st.caption("まだ記録がありません。")
    else:
        try: bd["ts"]=pd.to_datetime(bd["ts"]); bd=bd.sort_values("ts", ascending=False)
        except Exception: pass
        st.dataframe(bd.rename(columns={"ts":"日時","sec":"時間（秒）","guide":"ガイド","task":"1分タスク","note":"メモ"}),
                     use_container_width=True, hide_index=True)
        csv2 = bd.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ 呼吸（CSV）", data=csv2, file_name="breath.csv", mime="text/csv")
    st.markdown('</div>', unsafe_allow_html=True)

    # ジャーナル
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 自由ジャーナル")
    jd = load_csv(CSV_JOURNAL)
    if jd.empty: st.caption("まだ記録がありません。")
    else:
        try: jd["ts"]=pd.to_datetime(jd["ts"]); jd=jd.sort_values("ts", ascending=False)
        except Exception: pass
        for _,r in jd.head(20).iterrows():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"**🕒 {r.get('ts','')}**"); st.markdown(r.get("text",""))
            st.markdown('</div>', unsafe_allow_html=True)
        csv3 = jd.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ ジャーナル（CSV）", data=csv3, file_name="journal.csv", mime="text/csv")
    st.markdown('</div>', unsafe_allow_html=True)

    # 一日の振り返り
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 一日の振り返り")
    dd = load_csv(CSV_DAY)
    if dd.empty: st.caption("まだ記録がありません。")
    else:
        try: dd["ts"]=pd.to_datetime(dd["ts"]); dd=dd.sort_values("ts", ascending=False)
        except Exception: pass
        st.dataframe(dd.rename(columns={"ts":"日時","mood":"気分","today":"今日","tomorrow":"明日したいこと"}),
                     use_container_width=True, hide_index=True)
        csv4 = dd.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ 一日の振り返り（CSV）", data=csv4, file_name="day.csv", mime="text/csv")
    st.markdown('</div>', unsafe_allow_html=True)

    # Study
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### Study Tracker")
    sd = load_csv(CSV_STUDY)
    if sd.empty: st.caption("まだ記録がありません。")
    else:
        st.dataframe(sd, use_container_width=True, hide_index=True)
        csv5 = sd.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Study（CSV）", data=csv5, file_name="study.csv", mime="text/csv")
    st.markdown('</div>', unsafe_allow_html=True)

# ================== ルーター ==================
try:
    if   ss.view == "HOME":    view_home()
    elif ss.view == "BREATH":  view_breath()
    elif ss.view == "FEEL":    view_feel()
    elif ss.view == "JOURNAL": view_journal()
    elif ss.view == "DAY":     view_day()
    elif ss.view == "STUDY":   view_study()
    elif ss.view == "HISTORY": view_history()
    else:                      view_home()
except Exception as e:
    # ここは“白画面にしない”ための最終ガード。セーフUIは出さず、エラーだけ表示。
    st.error("画面描画中に問題が発生しました。")
    import traceback as _tb
    st.code("".join(_tb.format_exception(e)), language="python")
