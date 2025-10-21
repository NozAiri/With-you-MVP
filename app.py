# app.py — Sora（明るい星空UI／安全呼吸／やさしい感情整理／自由ジャーナル／一日の振り返り／Study Tracker）
from __future__ import annotations
from datetime import datetime, date, timedelta
from pathlib import Path
import time, uuid, json, io
import pandas as pd
import streamlit as st

# ======================= 基本設定 =======================
st.set_page_config(page_title="Sora — しんどい夜の2分ノート", page_icon="🌙", layout="centered")
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)

# CSV 保存先
CSV_BREATH   = DATA_DIR/"breath.csv"
CSV_FEEL     = DATA_DIR/"feel.csv"
CSV_JOURNAL  = DATA_DIR/"journal.csv"
CSV_DAY      = DATA_DIR/"day.csv"
CSV_STUDY    = DATA_DIR/"study.csv"
CSV_SUBJECTS = DATA_DIR/"subjects.csv"

# セッション状態
if "view" not in st.session_state: st.session_state.view = "HOME"
if "first_breath" not in st.session_state: st.session_state.first_breath = False
if "breath_active" not in st.session_state: st.session_state.breath_active = False
if "breath_stop" not in st.session_state: st.session_state.breath_stop = False
if "auto_guide" not in st.session_state: st.session_state.auto_guide = "soft"  # soft: 吸4-吐6 / calm: 吸5-止2-吐6
if "breath_runs" not in st.session_state: st.session_state.breath_runs = 0
if "rest_until" not in st.session_state: st.session_state.rest_until = None
if "em" not in st.session_state: st.session_state.em = {}
if "tg" not in st.session_state: st.session_state.tg = set()

# 科目リストとメモ（初期値）
if "subjects" not in st.session_state:
    if CSV_SUBJECTS.exists():
        try:
            _sdf = pd.read_csv(CSV_SUBJECTS)
            st.session_state.subjects = _sdf["subject"].dropna().unique().tolist() or ["国語","数学","英語"]
            st.session_state.subject_notes = {r["subject"]: r.get("note","") for _,r in _sdf.iterrows()}
        except Exception:
            st.session_state.subjects = ["国語","数学","英語"]
            st.session_state.subject_notes = {}
    else:
        st.session_state.subjects = ["国語","数学","英語"]
        st.session_state.subject_notes = {}
if "study_last_saved" not in st.session_state:
    st.session_state.study_last_saved = None

# ======================= スタイル（明るい星空） =======================
st.markdown("""
<style>
:root{
  --text:#1f1a2b; --muted:#6f6a80; --glass:rgba(255,255,255,.93); --brd:rgba(185,170,255,.28);
}
.stApp{
  background: radial-gradient(1200px 600px at 20% -10%, #fff7fb 0%, #f7f1ff 45%, #ecf9ff 100%);
  position:relative; overflow:hidden;
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
}
@keyframes twinkle{
  0%,100%{opacity:.7; transform:translateY(0)}
  50%{opacity:1; transform:translateY(-2px)}
}
.block-container{ max-width:920px; padding-top:.8rem; padding-bottom:1.6rem }
h1,h2,h3{ color:var(--text); letter-spacing:.2px }
.small{ color:var(--muted); font-size:.92rem }
.card{ background:var(--glass); border:1px solid var(--brd); border-radius:20px; padding:16px; margin:10px 0 14px;
       box-shadow:0 18px 36px rgba(50,40,90,.14); backdrop-filter:blur(6px); }
.row{ display:grid; grid-template-columns:1fr 1fr; gap:14px }
@media(max-width:720px){ .row{ grid-template-columns:1fr } }
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
.emoji{ font-size:26px }
</style>
""", unsafe_allow_html=True)

# ======================= ユーティリティ =======================
def now_ts() -> str:
    return datetime.now().isoformat(timespec="seconds")

def load_csv(p: Path) -> pd.DataFrame:
    if not p.exists(): return pd.DataFrame()
    try: return pd.read_csv(p)
    except: return pd.DataFrame()

def append_csv(p: Path, row: dict) -> bool:
    try:
        df = load_csv(p); df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        df.to_csv(p, index=False); return True
    except: return False

def week_range(d: date | None = None):
    d = d or date.today()
    start = d - timedelta(days=d.weekday())   # 月曜
    end = start + timedelta(days=6)           # 日曜
    return start, end

# ======================= ヘッダー（戻る常設） =======================
def header(title: str):
    cols = st.columns([1,6])
    with cols[0]:
        if st.button("← ホームへ", use_container_width=True):
            st.session_state.view = "HOME"
            st.stop()
    with cols[1]:
        st.markdown(f"### {title}")

# ======================= HOME =======================
def view_home():
    st.markdown("## 🌙 Sora — しんどい夜の2分ノート")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("**言葉の前に、息をひとつ。** 迷わず “呼吸で落ち着く → 感情を整える → 今日を書いておく” へ。説明いらずのやさしいUI。")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="row">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="tile">', unsafe_allow_html=True)
        if st.button("🌬 呼吸で落ち着く（1–3分）", use_container_width=True): st.session_state.view = "BREATH"
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="tile alt">', unsafe_allow_html=True)
        if st.button("📝 自由ジャーナル", use_container_width=True): st.session_state.view = "JOURNAL"
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="tile alt">', unsafe_allow_html=True)
        if st.button("🙂 感情を整える（3ステップ）", use_container_width=True): st.session_state.view = "FEEL"
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="tile">', unsafe_allow_html=True)
        if st.button("📅 一日の振り返り", use_container_width=True): st.session_state.view = "DAY"
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="tile alt">', unsafe_allow_html=True)
    if st.button("📚 Study Tracker", use_container_width=True): st.session_state.view = "STUDY"
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card cta">', unsafe_allow_html=True)
    if st.button("📦 記録を見る / エクスポート", use_container_width=True): st.session_state.view = "HISTORY"
    st.markdown('</div>', unsafe_allow_html=True)

# ======================= 呼吸（安全×没入） =======================
def view_breath():
    header("🌬 呼吸で落ち着く")

    # 連続3回で休憩
    if st.session_state.rest_until and datetime.now() < st.session_state.rest_until:
        left = int((st.session_state.rest_until - datetime.now()).total_seconds())
        st.info(f"少し休憩しよう（過換気予防）。{left} 秒後に再開できます。")
        return
    if st.session_state.breath_runs >= 3:
        st.session_state.rest_until = datetime.now() + timedelta(seconds=30)
        st.session_state.breath_runs = 0

    # 初回は90秒固定、以降は選択
    first = not st.session_state.first_breath
    length = 90 if first else st.radio("時間（固定プリセット）", [60,90,180], index=1, horizontal=True)

    # ガイド2種（やさしめ→落ち着きに自動）
    mode = st.session_state.auto_guide  # soft: 吸4-吐6, calm: 吸5-止2-吐6（止め2秒固定）
    guide_name = "吸4・吐6（やさしめ）" if mode=="soft" else "吸5・止2・吐6（落ち着き）"
    with st.expander("ガイド（自動で切り替わります）", expanded=False):
        st.caption(f"いま: **{guide_name}**")

    silent = st.toggle("言葉を最小にする（“いっしょに息を / ここにいていい”）", value=True)
    sound  = st.toggle("そっと効果音を添える（環境によっては無音）", value=False)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    # シーケンス（止めは2秒固定）
    seq = [("吸う",4),("吐く",6)] if mode=="soft" else [("吸う",5),("止める",2),("吐く",6)]

    # UI部品
    phase = st.empty(); circle = st.empty(); count = st.empty(); bar = st.progress(0)

    # ボタン
    c1,c2 = st.columns(2)
    start = c1.button("開始", use_container_width=True, disabled=st.session_state.breath_active)
    stopb = c2.button("× 停止", use_container_width=True)
    if stopb: st.session_state.breath_stop = True

    # 簡易トーン（依存が無ければ自動で無音）
    def tone(kind:str):
        if not sound: return
        try:
            import numpy as np, soundfile as sf
            sr=22050; sec=0.25 if kind!="吸う" else 0.35
            f=220 if kind=="吸う" else (180 if kind=="止める" else 150)
            t=np.linspace(0,sec,int(sr*sec),False)
            w=0.15*np.sin(2*np.pi*f*t)*np.hanning(len(t))
            buf=io.BytesIO(); sf.write(buf,w,sr,format="WAV"); st.audio(buf.getvalue(), format="audio/wav")
        except Exception:
            pass

    if start or st.session_state.breath_active:
        st.session_state.breath_active = True
        st.session_state.breath_stop = False
        st.session_state.first_breath = True

        base = sum(t for _,t in seq)
        cycles = max(1, length // base)
        remain = length - cycles*base
        total_ticks = cycles*base + remain
        tick = 0

        if silent:
            st.markdown('<div class="center small">いっしょに息を / ここにいていい</div>', unsafe_allow_html=True)

        for _ in range(cycles):
            for name,sec in seq:
                if st.session_state.breath_stop: break
                phase.markdown(f"<span class='phase'>{name}</span>", unsafe_allow_html=True)
                tone(name)
                for s in range(sec,0,-1):
                    if st.session_state.breath_stop: break
                    scale = 1.12 if name=="吸う" else (1.0 if name=="止める" else 0.88)
                    circle.markdown(f"<div class='circle-wrap'><div class='breath-circle' style='transform:scale({scale});'></div></div>", unsafe_allow_html=True)
                    count.markdown(f"<div class='count'>{s}</div>", unsafe_allow_html=True)
                    tick += 1; bar.progress(min(int(tick/total_ticks*100),100))
                    time.sleep(1)
            if st.session_state.breath_stop: break

        # 余り秒（静かに）
        for r in range(remain,0,-1):
            if st.session_state.breath_stop: break
            circle.markdown(f"<div class='circle-wrap'><div class='breath-circle' style='transform:scale(0.88);'></div></div>", unsafe_allow_html=True)
            count.markdown(f"<div class='count'>{r}</div>", unsafe_allow_html=True)
            tick += 1; bar.progress(min(int(tick/total_ticks*100),100)); time.sleep(1)

        st.session_state.breath_active = False

        if st.session_state.breath_stop:
            phase.markdown("<span class='phase'>停止しました</span>", unsafe_allow_html=True)
            st.session_state.breath_stop = False
        else:
            phase.markdown("<span class='phase'>完了</span>", unsafe_allow_html=True)
            st.caption("ここまで来たあなたは十分えらい。")

            # 主観チェック → 自動で calm へ
            feel = st.radio("いまの感じ（任意）", ["変わらない","少し落ち着いた","かなり落ち着いた"], index=1, horizontal=True)
            st.session_state.breath_runs += 1
            if feel=="かなり落ち着いた" and st.session_state.auto_guide=="soft":
                st.session_state.auto_guide = "calm"

            # 1分タスク（自由）＋ メモ
            task = st.text_input("1分タスク（任意）", placeholder="例：水を一口 / 窓を少し開ける / 手首を冷水10秒 / 姿勢を1ミリ")
            note = st.text_input("メモ（任意・非共有）", placeholder="例：胸のつかえが少し軽い")
            if st.button("💾 保存", type="primary"):
                row = {"id":str(uuid.uuid4())[:8],"ts":now_ts(),"sec":length,"guide":st.session_state.auto_guide,
                       "task":task,"note":note}
                append_csv(CSV_BREATH,row); st.success("保存しました。")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown('<div class="card cta">', unsafe_allow_html=True)
    if st.button("← ホームへ戻る", use_container_width=True):
        st.session_state.view = "HOME"
    st.markdown("</div>", unsafe_allow_html=True)

# ======================= 感情を整える（専門用語なし） =======================
EMOJIS = [("怒り","😠"),("かなしい","😢"),("ふあん","😟"),("罪悪感","😔"),("はずかしい","😳"),
          ("あせり","😣"),("たいくつ","😐"),("ほっとする","🙂"),("うれしい","😊")]
TRIGGERS = ["今日の出来事","友だち","家族","部活","クラス","先生","SNS","勉強","宿題","体調","お金","将来"]

def view_feel():
    header("🙂 感情を整える（3ステップ）")

    # ① いまの感情
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("**いまの感情は？**（複数OK）")
    em = st.session_state.em
    cols = st.columns(3)
    for i,(label,emoji) in enumerate(EMOJIS):
        with cols[i%3]:
            on = st.toggle(f"{emoji} {label}", value=label in em)
            if on:
                em[label] = st.slider(f"{label} の強さ",1,5, em.get(label,3), key=f"lv_{label}")
            else:
                em.pop(label, None)
    st.markdown('</div>', unsafe_allow_html=True)

    # ② きっかけ
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("**きっかけはどれに近い？**（複数OK）")
    tg = st.session_state.tg
    tcols = st.columns(3)
    for i,t in enumerate(TRIGGERS):
        with tcols[i%3]:
            if st.checkbox(t, value=(t in tg)): tg.add(t)
            else: tg.discard(t)
    free = st.text_input("一言メモ（任意）", placeholder="例：LINEの返事がこなかった")
    st.markdown('</div>', unsafe_allow_html=True)

    # ③ やさしい見かた（ヒント）→ 自分の言葉
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("**やさしい見かたのヒント**（そのままでもOK）")
    hint = st.selectbox("しっくりくるもの", [
        "全部ダメだと思った → “いまの一つがむずかしいだけ”かも",
        "先の心配でいっぱい → “まず今日の5分”からでOK",
        "相手の気持ちを決めつけた → “本当のところは分からない”かも",
        "自分ばかり悪いと思った → “環境やタイミングの影響”もあるかも",
        "良かった点を忘れている → “できた一つ”を足してバランスに",
    ], index=1)
    alt = st.text_area("自分の言葉で置き換える（任意）", value=hint, height=80)
    st.markdown('</div>', unsafe_allow_html=True)

    # 今日の一歩（自由記入）
    st.markdown('<div class="card">', unsafe_allow_html=True)
    step = st.text_input("今日の一歩（1〜3分で終わること・自由記入）",
                         placeholder="例：タイマー1分だけ机に向かう / スタンプだけ送る / 外の光を5分あびる")
    st.markdown('</div>', unsafe_allow_html=True)

    c1,c2 = st.columns(2)
    with c1:
        if st.button("💾 保存して要約を見る", type="primary", use_container_width=True):
            row = {"id":str(uuid.uuid4())[:8],"ts":now_ts(),
                   "emotions":json.dumps(st.session_state.em,ensure_ascii=False),
                   "triggers":json.dumps(list(st.session_state.tg),ensure_ascii=False),
                   "free":free,"reframe":alt,"step":step}
            append_csv(CSV_FEEL,row); st.session_state["last_feel"]=row; st.success("保存しました。")
    with c2:
        if st.button("入力をクリア", use_container_width=True):
            st.session_state.em={}; st.session_state.tg=set(); st.experimental_rerun()

    if st.session_state.get("last_feel"):
        r = st.session_state["last_feel"]
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.write("**要約**（1スクロール）")
        emo_txt = "・".join([f"{k}×{v}" for k,v in json.loads(r["emotions"]).items()]) if r["emotions"] else "—"
        tri_txt = "・".join(json.loads(r["triggers"])) if r["triggers"] else "—"
        st.markdown(f"- 気持ち：{emo_txt}")
        st.markdown(f"- きっかけ：{tri_txt} / {r.get('free','')}")
        st.markdown(f"- やさしい見かた：{r.get('reframe','')}")
        st.markdown(f"- 今日の一歩：{r.get('step','')}")
        st.markdown('</div>', unsafe_allow_html=True)

# ======================= 自由ジャーナル =======================
def view_journal():
    header("📝 自由ジャーナル")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    txt = st.text_area("思ったことをそのまま書いてOK（保存は端末のみ・共有なし）", height=240,
                       placeholder="例：いまの気持ち、もやもや、気づいたこと、だれにも見せない自分の言葉。")
    if st.button("💾 保存", type="primary"):
        row={"id":str(uuid.uuid4())[:8],"ts":now_ts(),"text":txt}
        append_csv(CSV_JOURNAL,row); st.success("保存しました。")
    st.markdown('</div>', unsafe_allow_html=True)

# ======================= 一日の振り返り =======================
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

    # 最近の記録
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("**最近の記録**")
    df = load_csv(CSV_DAY)
    if df.empty:
        st.caption("まだ記録がありません。")
    else:
        try:
            df["ts"] = pd.to_datetime(df["ts"])
            df = df.sort_values("ts", ascending=False)
        except: pass
        for _,r in df.head(10).iterrows():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"**🕒 {r.get('ts','')}**")
            st.markdown(f"- 気分：{r.get('mood','')}")
            st.markdown(f"- 今日：{r.get('today','')}")
            st.markdown(f"- 明日：{r.get('tomorrow','')}")
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ======================= Study Tracker（科目×時間×メモ） =======================
def view_study():
    header("📚 Study Tracker（科目×時間×メモ）")

    # ---------- 科目管理 ----------
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("**科目の追加/並べ替え/メモ**")
    colA, colB = st.columns([2,1])
    with colA:
        new_subj = st.text_input("科目を追加", placeholder="例：小論 / 過去問 / 面接 / 実技 など")
        if st.button("＋ 追加"):
            name = new_subj.strip()
            if name and name not in st.session_state.subjects:
                st.session_state.subjects.append(name)
                st.session_state.subject_notes.setdefault(name, "")
                _df = pd.DataFrame([{"subject": s, "note": st.session_state.subject_notes.get(s,"")} for s in st.session_state.subjects])
                _df.to_csv(CSV_SUBJECTS, index=False)
                st.success(f"「{name}」を追加しました。")
    with colB:
        if st.session_state.subjects:
            up_subj = st.selectbox("上に移動", st.session_state.subjects)
            if st.button("▲ 上へ"):
                idx = st.session_state.subjects.index(up_subj)
                if idx>0:
                    st.session_state.subjects[idx-1], st.session_state.subjects[idx] = st.session_state.subjects[idx], st.session_state.subjects[idx-1]
                    _df = pd.DataFrame([{"subject": s, "note": st.session_state.subject_notes.get(s,"")} for s in st.session_state.subjects])
                    _df.to_csv(CSV_SUBJECTS, index=False)

    if st.session_state.subjects:
        tabs = st.tabs(st.session_state.subjects)
        for i, s in enumerate(st.session_state.subjects):
            with tabs[i]:
                txt = st.text_area(f"「{s}」のメモ", value=st.session_state.subject_notes.get(s,""),
                                   placeholder="例：関数文章題のコツ／英単語は朝が楽 など", height=90, key=f"note_{s}")
                if st.button(f"💾 {s} のメモを保存", key=f"save_{s}"):
                    st.session_state.subject_notes[s] = txt
                    _df = pd.DataFrame([{"subject": ss, "note": st.session_state.subject_notes.get(ss,"")} for ss in st.session_state.subjects])
                    _df.to_csv(CSV_SUBJECTS, index=False)
                    st.success("保存しました。")
    st.markdown('</div>', unsafe_allow_html=True)

    # ---------- 記録する ----------
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("**学習ブロックを記録**（あとからメモ可）")
    col1, col2 = st.columns(2)
    with col1:
        subject = st.selectbox("科目", st.session_state.subjects)
        minutes = st.select_slider("時間（分）", options=[5,10,15,20,25,30,45,60,75,90], value=15)
    with col2:
        feel = st.radio("手触り", ["😌 集中できた","😕 難航した","😫 しんどい"], horizontal=False, index=0)
        note = st.text_input("メモ（任意）", placeholder="例：例題→教科書の順が合う／夜より朝が楽 など")

    if st.button("🧭 記録する", type="primary"):
        row = {
            "id": str(uuid.uuid4())[:8], "ts": now_ts(),
            "date": datetime.now().date().isoformat(), "subject": subject,
            "minutes": int(minutes), "blocks15": max(1, round(int(minutes)/15)), "feel": feel, "note": note
        }
        append_csv(CSV_STUDY, row)
        st.session_state.study_last_saved = row
        st.success("記録しました。")
    st.markdown('</div>', unsafe_allow_html=True)

    # ---------- 週ビュー（可視化） ----------
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("**今週のまとめ**（月曜はじまり）")
    df = load_csv(CSV_STUDY)
    if df.empty:
        st.caption("まだ記録がありません。")
    else:
        try:
            df["date"] = pd.to_datetime(df["date"]).dt.date
        except: pass
        ws, we = week_range()
        mask = (df["date"] >= ws) & (df["date"] <= we)
        w = df[mask].copy()
        if w.empty:
            st.caption("今週の記録はありません。")
        else:
            agg = w.groupby("subject", as_index=False)["minutes"].sum().sort_values("minutes", ascending=False)
            total = int(w["minutes"].sum())
            st.markdown(f"今週の合計：**{total} 分**")
            st.dataframe(agg.rename(columns={"subject":"科目","minutes":"合計（分）"}), use_container_width=True, hide_index=True)

            # 棒グラフ（matplotlib が無ければ表示スキップ）
            try:
                import matplotlib.pyplot as plt
                fig = plt.figure(figsize=(6,3.2))
                plt.bar(agg["subject"], agg["minutes"])
                plt.title("科目別 合計分（今週）")
                plt.ylabel("分")
                plt.xticks(rotation=15, ha="right")
                st.pyplot(fig)
            except Exception:
                pass

            # 手触りの分布
            feel_counts = w.groupby("feel")["id"].count().reset_index().rename(columns={"id":"件数"})
            st.caption("手触りの分布（件数）")
            st.dataframe(feel_counts, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ---------- エクスポート ----------
    st.markdown('<div class="card">', unsafe_allow_html=True)
    full = load_csv(CSV_STUDY)
    if not full.empty:
        csv = full.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Study Tracker（CSV）をダウンロード", data=csv, file_name="study.csv", mime="text/csv")
    st.markdown('</div>', unsafe_allow_html=True)

# ======================= 記録 / エクスポート =======================
def view_history():
    header("📦 記録とエクスポート")

    # 1) 感情整理
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 感情の記録")
    df = load_csv(CSV_FEEL)
    if df.empty:
        st.caption("まだ記録がありません。")
    else:
        try: df["ts"]=pd.to_datetime(df["ts"]); df=df.sort_values("ts", ascending=False)
        except: pass
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

    # 2) 呼吸
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 呼吸の記録")
    bd = load_csv(CSV_BREATH)
    if bd.empty:
        st.caption("まだ記録がありません。")
    else:
        try: bd["ts"]=pd.to_datetime(bd["ts"]); bd=bd.sort_values("ts", ascending=False)
        except: pass
        st.dataframe(bd.rename(columns={"ts":"日時","sec":"時間（秒）","guide":"ガイド","task":"1分タスク","note":"メモ"}),
                     use_container_width=True, hide_index=True)
        csv2 = bd.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ 呼吸（CSV）", data=csv2, file_name="breath.csv", mime="text/csv")
    st.markdown('</div>', unsafe_allow_html=True)

    # 3) ジャーナル
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 自由ジャーナル")
    jd = load_csv(CSV_JOURNAL)
    if jd.empty:
        st.caption("まだ記録がありません。")
    else:
        try: jd["ts"]=pd.to_datetime(jd["ts"]); jd=jd.sort_values("ts", ascending=False)
        except: pass
        for _,r in jd.head(20).iterrows():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"**🕒 {r.get('ts','')}**")
            st.markdown(r.get("text",""))
            st.markdown('</div>', unsafe_allow_html=True)
        csv3 = jd.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ ジャーナル（CSV）", data=csv3, file_name="journal.csv", mime="text/csv")
    st.markdown('</div>', unsafe_allow_html=True)

    # 4) 一日の振り返り
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 一日の振り返り")
    dd = load_csv(CSV_DAY)
    if dd.empty:
        st.caption("まだ記録がありません。")
    else:
        try: dd["ts"]=pd.to_datetime(dd["ts"]); dd=dd.sort_values("ts", ascending=False)
        except: pass
        st.dataframe(dd.rename(columns={"ts":"日時","mood":"気分","today":"今日","tomorrow":"明日したいこと"}),
                     use_container_width=True, hide_index=True)
        csv4 = dd.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ 一日の振り返り（CSV）", data=csv4, file_name="day.csv", mime="text/csv")
    st.markdown('</div>', unsafe_allow_html=True)

    # 5) Study
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### Study Tracker")
    sd = load_csv(CSV_STUDY)
    if sd.empty:
        st.caption("まだ記録がありません。")
    else:
        st.dataframe(sd, use_container_width=True, hide_index=True)
        csv5 = sd.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Study（CSV）", data=csv5, file_name="study.csv", mime="text/csv")
    st.markdown('</div>', unsafe_allow_html=True)

# ======================= ルーティング =======================
if   st.session_state.view == "HOME":    view_home()
elif st.session_state.view == "BREATH":  view_breath()
elif st.session_state.view == "FEEL":    view_feel()
elif st.session_state.view == "JOURNAL": view_journal()
elif st.session_state.view == "DAY":     view_day()
elif st.session_state.view == "STUDY":   view_study()
elif st.session_state.view == "HISTORY": view_history()
else:                                    view_home()
