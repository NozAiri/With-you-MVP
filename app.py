# app.py — Sora（呼吸=安全×没入 / CBT=3タップ）
# 依存: streamlit, pandas, numpy (音ON時のみ)
from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path
import time, uuid, json, io
import pandas as pd
import streamlit as st

# ---------------- 基本設定 ----------------
st.set_page_config(page_title="Sora — しんどい夜の2分ノート", page_icon="🌙", layout="centered")
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
CBT_CSV   = DATA_DIR / "entries_cbt.csv"
BREATH_CSV= DATA_DIR / "entries_breath.csv"
TRACK_CSV = DATA_DIR / "study_blocks.csv"

# ---------------- 状態 ----------------
if "view" not in st.session_state: st.session_state.view = "HOME"
if "first_breath_done" not in st.session_state: st.session_state.first_breath_done = False
if "breath_runs" not in st.session_state: st.session_state.breath_runs = 0
if "breathing_active" not in st.session_state: st.session_state.breathing_active = False
if "breathing_stop" not in st.session_state: st.session_state.breathing_stop = False
if "pattern_mode" not in st.session_state: st.session_state.pattern_mode = "soft"   # soft(吸4-吐6)→calm(吸5-止2-吐6)
if "rest_until" not in st.session_state: st.session_state.rest_until = None

# ---------------- スタイル ----------------
st.markdown("""
<style>
:root{
  --text:#201b2b; --muted:#6f6a80; --glass:rgba(255,255,255,.92); --brd:rgba(185,170,255,.28);
  --a:#ffd3e6; --b:#f2ecff; --c:#e6fbff; --btn:#7b6cff;
}
.stApp{ background:linear-gradient(180deg,#fffefd 0%,#fff7fb 25%,#f6f1ff 55%,#eefbff 100%); }
.block-container{ max-width:920px; padding-top:.8rem; padding-bottom:1.6rem }
h1,h2,h3{ color:var(--text); letter-spacing:.2px }
.small{ color:var(--muted); font-size:.92rem }
.card{ background:var(--glass); border:1px solid var(--brd); border-radius:20px; padding:16px; margin:10px 0 14px;
       box-shadow:0 18px 36px rgba(50,40,90,.14); backdrop-filter:blur(6px); }
.tile-grid{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }
@media(max-width:680px){ .tile-grid{ grid-template-columns:1fr; } }
.tile .stButton>button{ min-height:120px; border-radius:18px; text-align:left; padding:18px; font-weight:900;
  background:linear-gradient(155deg,#ffe8f4,#fff3fb); color:#2a2731; border:1px solid #f5e8ff;
  box-shadow:0 14px 28px rgba(60,45,90,.12) }
.tile.alt .stButton>button{ background:linear-gradient(155deg,#e9f4ff,#f6fbff) }
.cta .stButton>button{
  width:100%; padding:12px 14px; border-radius:999px; border:1px solid #eadfff;
  background:linear-gradient(180deg,#a89bff,#7b6cff); color:#fff; font-weight:900; font-size:1.02rem;
  box-shadow:0 16px 30px rgba(123,108,255,.28);
}
.phase{ display:inline-block; padding:.25rem .85rem; border-radius:999px; font-weight:800;
  background:rgba(123,108,255,.12); color:#5d55ff; border:1px solid rgba(123,108,255,.32); }
.circle-wrap{ display:flex; justify-content:center; align-items:center; height:280px; }
.breath-circle{ width:180px; height:180px; border-radius:50%; background:radial-gradient(circle at 50% 40%, #fff, #f2ebff);
  border:2px solid #e7dcff; box-shadow:0 0 80px 10px rgba(123,108,255,.16) inset, 0 18px 48px rgba(30,20,70,.18);
  transition: transform .8s ease-in-out;
}
.count{ font-size:44px; font-weight:900; text-align:center; color:#2f2a3b; margin-top:6px; }
.pills .stButton>button{ background:#fff; color:#2a2731; border:1px solid #eadfff; border-radius:999px; padding:8px 12px; font-weight:800; box-shadow:none }
.emoji{ font-size:26px; line-height:1; }
.grid4{ display:grid; grid-template-columns:repeat(4,1fr); gap:8px; }
.grid3{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; }
.tag{ border-radius:999px; border:1px solid #e6e0ff; padding:.42rem .65rem; background:#fff; font-weight:700; text-align:center; }
.result-line{ padding:.6rem .8rem; border-left:5px solid #d9d2ff; background:#fff; border-radius:10px; }
.color-dot{ width:18px; height:18px; border-radius:50%; display:inline-block; border:1px solid #ddd; margin-right:6px; vertical-align:middle;}
</style>
""", unsafe_allow_html=True)

# ---------------- ユーティリティ ----------------
def now_ts(): return datetime.now().isoformat(timespec="seconds")
def _load_csv(p: Path) -> pd.DataFrame:
    if p.exists():
        try: return pd.read_csv(p)
        except Exception: return pd.DataFrame()
    return pd.DataFrame()
def _append_csv_safe(p: Path, row: dict) -> bool:
    try:
        df = _load_csv(p)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        df.to_csv(p, index=False)
        return True
    except Exception:
        return False

# ---------------- 音（任意ON） ----------------
def gen_tone(freq=220.0, sec=0.35, sr=22050):
    try:
        import numpy as np, soundfile as sf  # soundfile が無ければ fallback
        t = np.linspace(0, sec, int(sr*sec), False)
        wave = 0.2*np.sin(2*np.pi*freq*t)*np.hanning(len(t))
        buf = io.BytesIO()
        sf.write(buf, wave, sr, format="WAV")
        return buf.getvalue()
    except Exception:
        return None

if "tones" not in st.session_state:
    st.session_state.tones = {
        "inhale": gen_tone(220, .35) or b"",
        "hold":   gen_tone(180, .25) or b"",
        "exhale": gen_tone(150, .35) or b"",
    }

# ====================== 画面 ======================

def view_home():
    st.markdown("### 🌙 Sora — しんどい夜の2分ノート")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**言葉の前に、息をひとつ。** 迷わず “呼吸で落ち着く → 感情を整える → 今日の一歩” へ。説明なしでも直感で使えるUIです。", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="tile-grid">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="tile">', unsafe_allow_html=True)
        if st.button("🌬 呼吸で落ち着く（約1–3分）", use_container_width=True):
            st.session_state.view = "BREATH"
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="tile alt">', unsafe_allow_html=True)
        if st.button("📓 感情整理（3タップ）", use_container_width=True):
            st.session_state.view = "CBT"
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="card cta">', unsafe_allow_html=True)
        if st.button("📚 記録を見る / エクスポート", use_container_width=True): st.session_state.view = "HISTORY"
        st.markdown("</div>", unsafe_allow_html=True)

# ---------- 呼吸（安全×没入） ----------
def view_breath():
    st.markdown("### 🌬 呼吸で落ち着く")

    # 自動休憩（3連続後）
    if st.session_state.rest_until and datetime.now() < st.session_state.rest_until:
        left = int((st.session_state.rest_until - datetime.now()).total_seconds())
        st.info(f"少し休憩しよう（過換気予防）。{left} 秒後に再開できます。")
        if st.button("← ホームへ"): st.session_state.view = "HOME"
        return
    if st.session_state.breath_runs >= 3:
        st.session_state.rest_until = datetime.now() + timedelta(seconds=30)
        st.session_state.breath_runs = 0

    # 初回は 90 秒固定、設定UIは出さない
    first = not st.session_state.first_breath_done
    total_sec = 90 if first else st.radio("時間（固定プリセット）", [60,90,180], index=1, horizontal=True)

    # ガイド2種（初期は“soft”=吸4-吐6、安定すれば“calm”=吸5-止2-吐6へ自動移行）
    mode = st.session_state.pattern_mode
    guide_name = "吸4・吐6（やさしめ）" if mode=="soft" else "吸5・止2・吐6（落ち着き）"
    with st.expander("ガイド（自動）", expanded=False):
        st.caption(f"現在: **{guide_name}**（*自動で切替*）")
        st.caption("・“soft” は不安が高いとき向け（止めなし） / “calm” はより落ち着く（止め2秒固定）")

    # “言葉はいらない”モード
    colA, colB, colC = st.columns([1,1,1])
    with colA: silent_ui = st.toggle("言葉はいらない", value=True)
    with colB: sound_on = st.toggle("音をそっと添える", value=False)
    with colC:
        st.caption("× 停止はいつでもワンタップ")
    st.markdown('<div class="card">', unsafe_allow_html=True)

    # セーフティ：止めは最大2秒に固定
    if mode=="soft":   seq = [("吸う",4), ("吐く",6)]
    else:              seq = [("吸う",5), ("止める",2), ("吐く",6)]

    # サークルとカウント
    phase_box = st.empty(); circle_box = st.empty(); count_box = st.empty(); bar = st.progress(0)
    stop_area = st.empty()

    # 初回固定表示
    if first: st.caption("初回は 90秒 / “やさしめ” ガイドで自動スタートします。設定は不要です。")

    # 実行ボタン
    go, stop = st.columns(2)
    with go:
        start = st.button("開始", use_container_width=True, disabled=st.session_state.breathing_active)
    with stop:
        if st.button("× 停止", use_container_width=True):
            st.session_state.breathing_stop = True

    # ループ
    if start or st.session_state.breathing_active:
        st.session_state.breathing_active = True
        st.session_state.breathing_stop = False
        st.session_state.first_breath_done = True

        # 吸止吐の合計をできるだけ total_sec に合わせる（最後に微調整）
        cycle_len = sum(t for _,t in seq)
        cycles = max(1, total_sec // cycle_len)
        remain = total_sec - cycles*cycle_len
        # 余りは吐きに足さない（一定）→余りは最後の静止扱いにせず、そのままカウントだけ進行
        total_ticks = cycles*cycle_len + remain
        tick = 0

        if silent_ui:
            st.markdown("<div style='text-align:center' class='small'>いっしょに息を / ここにいていい</div>", unsafe_allow_html=True)

        for c in range(cycles):
            for name, sec in seq:
                if st.session_state.breathing_stop: break
                phase_box.markdown(f"<span class='phase'>{name}</span>", unsafe_allow_html=True)
                if sound_on and st.session_state.tones.get("inhale") is not None:
                    key = "inhale" if name=="吸う" else ("exhale" if name=="吐く" else "hold")
                    st.audio(st.session_state.tones.get(key,b""), format="audio/wav", start_time=0)
                for s in range(sec,0,-1):
                    if st.session_state.breathing_stop: break
                    scale = 1.12 if name=="吸う" else (1.0 if name=="止める" else 0.88)
                    circle_box.markdown(f"<div class='circle-wrap'><div class='breath-circle' style='transform:scale({scale});'></div></div>", unsafe_allow_html=True)
                    count_box.markdown(f"<div class='count'>{s}</div>", unsafe_allow_html=True)
                    tick += 1; bar.progress(min(int(tick/total_ticks*100),100))
                    time.sleep(1)
            if st.session_state.breathing_stop: break

        # 余り秒（静かに）— UIは吐き終わりサイズでキープ
        for r in range(remain,0,-1):
            if st.session_state.breathing_stop: break
            circle_box.markdown(f"<div class='circle-wrap'><div class='breath-circle' style='transform:scale(0.88);'></div></div>", unsafe_allow_html=True)
            count_box.markdown(f"<div class='count'>{r}</div>", unsafe_allow_html=True)
            tick += 1; bar.progress(min(int(tick/total_ticks*100),100))
            time.sleep(1)

        st.session_state.breathing_active = False

        # 途中停止
        if st.session_state.breathing_stop:
            phase_box.markdown(f"<span class='phase'>停止しました</span>", unsafe_allow_html=True)
            st.session_state.breathing_stop = False
            st.stop()

        # 完了
        phase_box.markdown(f"<span class='phase'>完了</span>", unsafe_allow_html=True)
        count_box.markdown("<div class='count' style='font-size:22px'>ここまで来たあなたは十分えらい。</div>", unsafe_allow_html=True)

        # 自動切替ロジック（主観安定で calm へ）
        st.session_state.breath_runs += 1
        stable = st.radio("いまの感じ（任意）", ["そのまま","少し落ちついた","かなり落ちついた"], index=1, horizontal=True)
        if stable=="かなり落ちついた" and st.session_state.pattern_mode=="soft":
            st.session_state.pattern_mode = "calm"

        # 1分タスク + 今日の色
        st.markdown("</div>", unsafe_allow_html=True)  # card
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**1分タスク（1つだけ）**")
        c1,c2,c3,c4 = st.columns(4)
        if c1.button("水を一口"): task="水を一口"
        elif c2.button("窓を少し開ける"): task="窓を少し開ける"
        elif c3.button("手首を冷水10秒"): task="手首を冷水10秒"
        elif c4.button("姿勢を1ミリ"): task="姿勢を1ミリ"
        else: task=""
        st.markdown('<div class="grid4">', unsafe_allow_html=True)
        colors = {
            "月白": "#edf2ff", "薄桜":"#ffe9f2", "朝霧":"#e9f7ff", "藤":"#efe8ff",
            "薄桃":"#ffdfe8", "空":"#e6f4ff", "若草":"#eaffea", "杏":"#fff1e0",
        }
        choose = st.radio("今日の色（任意）", list(colors.keys()), horizontal=True, index=0,
                          format_func=lambda k: f"  {k}  ")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown(f"<span class='color-dot' style='background:{colors[choose]}'></span> {choose}", unsafe_allow_html=True)

        # 保存
        note = st.text_input("メモ（任意・非共有）", placeholder="例：胸のつかえが少し軽い")
        if st.button("💾 保存", type="primary"):
            row = {
                "id": str(uuid.uuid4())[:8], "ts": now_ts(),
                "total_sec": total_sec, "mode": st.session_state.pattern_mode,
                "task": task, "color": choose, "note": note
            }
            ok = _append_csv_safe(BREATH_CSV, row)
            (st.success if ok else st.warning)("保存しました。" if ok else "一時保存のみ（CSV書込失敗）")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    if st.button("← ホームへ戻る", use_container_width=True):
        st.session_state.view = "HOME"
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- CBT（3タップで負のループを切る） ----------
EMOJIS = [("怒","😠"),("悲","😢"),("不安","😟"),("罪","😔"),("恥","😳"),("焦","😣"),("退屈","😐"),("安心","🙂"),("嬉","😊")]
TRIGGERS = ["家族","友達","恋愛","いじめ","SNS","勉強","宿題","部活","先生","体調","お金","将来"]
PATTERNS = ["全か無か","先読み不安","心の読み過ぎ","レッテル貼り","拡大解釈/過小評価","感情的決めつけ","過度の自己責任"]
REAPPRAISAL = {
    "全か無か":"「全部ダメ」ではなく“いま難しい1つ”かも",
    "先読み不安":"未来の確定はできない。小さく様子見してからでOK",
    "心の読み過ぎ":"相手の頭の中は推測。確かめる/時間を置く手も",
    "レッテル貼り":"1場面=あなた全体ではない",
    "拡大解釈/過小評価":"うまくいった点も1つ入れてバランスに",
    "感情的決めつけ":"“感じた”=“事実”ではない。事実を1つ",
    "過度の自己責任":"要因は複数。環境/タイミングの影響も",
}
SELF_COMP = ["こう感じるのは自然","いまはつらい。わたしに優しく","いまは休むのが最善","助けを求めるのは勇気"]
ACTIONS = ["課題の“1問だけ”","友達にスタンプだけ","5分だけ外の光","水を飲む","机上を30秒だけ"]
VALUES  = ["挑戦","健康","友情","学び","誠実","優しさ"]

def view_cbt():
    st.markdown("### 📓 感情整理（3タップ）")
    st.caption("**ボタンを選ぶだけ**。文章は任意です。")

    # 1) いまの気持ち（複数可） + 強さ（長押しの代わりに濃淡スライダ）
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("**① いまの気持ち（複数可）**")
    em_selected = st.session_state.get("em_selected", {})
    cols = st.columns(3)
    for i,(name,emo) in enumerate(EMOJIS):
        with cols[i%3]:
            picked = st.toggle(f"{emo} {name}", value=(name in em_selected))
            intens = em_selected.get(name,3)
            if picked:
                em_selected[name] = st.slider(f"{name} の強さ",1,5,intens,key=f"int_{name}")
            else:
                em_selected.pop(name, None)
    st.session_state.em_selected = em_selected
    st.markdown('</div>', unsafe_allow_html=True)

    # 2) きっかけ（チップ+自由1行）
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("**② きっかけ（複数可）**")
    tri_selected = st.session_state.get("tri_selected", set())
    tri_cols = st.columns(3)
    for i,t in enumerate(TRIGGERS):
        with tri_cols[i%3]:
            if st.checkbox(t, value=(t in tri_selected)): tri_selected.add(t)
            else: tri_selected.discard(t)
    st.session_state.tri_selected = tri_selected
    tri_free = st.text_input("…を書く（任意・1行）", placeholder="例：LINEの既読がつかない")
    st.markdown('</div>', unsafe_allow_html=True)

    # 3) 自動“考えのパターン”提案 → 再評価テンプレ
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("**③ 考えのパターン → 優しい捉え直し**")
    pattern = st.selectbox("当てはまりそうなもの", PATTERNS, index=1)
    st.info(REAPPRAISAL.get(pattern,""), icon="💡")
    alt = st.text_area("捉え直し（そのままでもOK）", value=REAPPRAISAL.get(pattern,""), height=72)
    st.markdown('</div>', unsafe_allow_html=True)

    # 4) セルフ・コンパッション
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("**④ セルフ・コンパッション**")
    comp = st.radio("一言を選ぶ", SELF_COMP, horizontal=True, index=1)
    st.markdown('</div>', unsafe_allow_html=True)

    # 5) 今日の一歩（行動活性） + 価値タグ
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("**⑤ 今日の一歩（1〜3分）**")
    act_col = st.columns(5)
    preset_pick = ""
    for i,a in enumerate(ACTIONS):
        if act_col[i].button(a): preset_pick = a
    act = st.text_input("内容（編集可）", value=preset_pick)
    minutes = st.slider("目安（分）",1,3,1)
    val = st.radio("価値タグ", VALUES, horizontal=True, index=0)
    st.markdown('</div>', unsafe_allow_html=True)

    # 追加：良いことの振り返り（任意）
    with st.expander("＋ 良いことの振り返り（任意）", expanded=False):
        g_today = st.text_input("今日うれしかった1つ", placeholder="例：朝日を浴びた")
        g_act   = st.text_input("やれた1つ", placeholder="例：英単語を10個だけ見た")
        g_self  = st.text_input("自分にかける一言", placeholder="例：よくやってる")

    # 保存 & 結果1スクロール
    c1,c2 = st.columns(2)
    with c1:
        if st.button("💾 保存して結果を見る", type="primary", use_container_width=True):
            row = {
                "id": str(uuid.uuid4())[:8], "ts": now_ts(),
                "emotions": json.dumps(st.session_state.em_selected, ensure_ascii=False),
                "triggers": json.dumps(list(st.session_state.tri_selected), ensure_ascii=False),
                "trigger_free": tri_free,
                "pattern": pattern, "alt": alt, "self_comp": comp,
                "action": act, "minutes": minutes, "value": val,
                "g_today": g_today, "g_act": g_act, "g_self": g_self,
            }
            ok = _append_csv_safe(CBT_CSV, row)
            st.session_state["last_saved"] = row
            (st.success if ok else st.warning)("保存しました。" if ok else "一時保存のみ（CSV書込失敗）")
    with c2:
        if st.button("🧼 入力をクリア", use_container_width=True):
            for k in ["em_selected","tri_selected"]: st.session_state[k]= {} if k=="em_selected" else set()
            st.experimental_rerun()

    if st.session_state.get("last_saved"):
        r = st.session_state["last_saved"]
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**結果**")
        emo_txt = "・".join([f"{e}{'🔴🟠🟡🟢🔵'[int(v)-1]}" for e,v in json.loads(r["emotions"]).items()]) if r["emotions"] else "—"
        tri_txt = "・".join(json.loads(r["triggers"])) if r["triggers"] else "—"
        st.markdown(f"<div class='result-line'>気持ちの色：{emo_txt}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='result-line'>きっかけ：{tri_txt}  / {r.get('trigger_free','')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='result-line'>捉え直し：{r.get('alt','')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='result-line'>今日の一歩：{r.get('action','')}（{r.get('minutes',1)}分） / 価値：{r.get('value','')}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    if st.button("← ホームへ戻る", use_container_width=True):
        st.session_state.view = "HOME"
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- 記録 / エクスポート ----------
def view_history():
    st.markdown("### 📚 記録とエクスポート")

    # CBT
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 感情整理の記録")
    df = _load_csv(CBT_CSV)
    if df.empty:
        st.caption("まだ記録がありません。")
    else:
        try: df["ts"]=pd.to_datetime(df["ts"]); df=df.sort_values("ts", ascending=False)
        except: pass
        for _,r in df.head(25).iterrows():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"**🕒 {r.get('ts','')}**")
            emo = r.get("emotions",""); tri = r.get("triggers","")
            st.caption(f"気持ち：{emo}")
            st.caption(f"きっかけ：{tri} / {r.get('trigger_free','')}")
            st.markdown(f"**捉え直し**：{r.get('alt','')}")
            if r.get("action"): st.markdown(f"**今日の一歩**：{r.get('action','')}（{int(r.get('minutes',1))}分） / 価値：{r.get('value','')}")
            if r.get("g_today") or r.get("g_act") or r.get("g_self"):
                st.caption(f"Good：{r.get('g_today','')} / Did：{r.get('g_act','')} / Self：{r.get('g_self','')}")
            st.markdown('</div>', unsafe_allow_html=True)
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ 感情整理（CSV）", data=csv, file_name="entries_cbt.csv", mime="text/csv")
    st.markdown('</div>', unsafe_allow_html=True)

    # 呼吸
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 呼吸の記録")
    bd = _load_csv(BREATH_CSV)
    if bd.empty:
        st.caption("まだ記録がありません。")
    else:
        try: bd["ts"]=pd.to_datetime(bd["ts"]); bd=bd.sort_values("ts", ascending=False)
        except: pass
        st.dataframe(bd.rename(columns={"ts":"日時","total_sec":"時間（秒）","mode":"ガイド","task":"1分タスク","color":"今日の色","note":"メモ"}),
                     use_container_width=True, hide_index=True)
        csv2 = bd.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ 呼吸（CSV）", data=csv2, file_name="entries_breath.csv", mime="text/csv")
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("← ホームへ戻る"): st.session_state.view = "HOME"

# ====================== ルーティング ======================
if st.session_state.view == "HOME":      view_home()
elif st.session_state.view == "BREATH":  view_breath()
elif st.session_state.view == "CBT":     view_cbt()
else:                                    view_history()
