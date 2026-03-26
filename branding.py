import html

BRAND_NAME = "SIGL"
BRAND_PAGE_TITLE = BRAND_NAME
BRAND_PAGE_ICON = "📟"
BRAND_REPORT_SLUG = "sigl"

_BOARD_CSS = """
@font-face{
  font-family:'SIGL Segment';
  src:local('DSEG7 Classic'),local('DS-Digital'),local('Digital-7'),local('JetBrains Mono'),local('Consolas');
}
html,body{
  margin:0;
  padding:0;
  background:transparent;
  font-family:'Pretendard',system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
}
*{box-sizing:border-box}
.sigl-board{
  --sigl-accent:#A5B4FC;
  --sigl-accent-soft:rgba(165,180,252,.18);
  --sigl-accent-strong:rgba(165,180,252,.36);
  position:relative;
  overflow:hidden;
  margin:0;
  border:1px solid rgba(148,163,184,.16);
  border-radius:22px;
  background:
    linear-gradient(180deg,rgba(2,5,9,.995),rgba(6,9,14,.992)),
    radial-gradient(circle at top right,rgba(165,180,252,.12),transparent 34%),
    radial-gradient(circle at bottom left,rgba(34,197,94,.08),transparent 26%);
  box-shadow:0 24px 60px rgba(2,6,23,.34),inset 0 1px 0 rgba(255,255,255,.04);
}
.sigl-board::before{
  content:"";
  position:absolute;
  inset:0;
  pointer-events:none;
  opacity:.18;
  background:
    radial-gradient(circle at 1px 1px,rgba(255,255,255,.17) .8px,transparent .9px) 0 0/8px 8px,
    radial-gradient(circle at 1px 1px,rgba(255,255,255,.03) .8px,transparent .9px) 4px 4px/8px 8px;
}
.sigl-board::after{
  content:"";
  position:absolute;
  inset:0;
  pointer-events:none;
  opacity:.08;
  background:repeating-linear-gradient(180deg,rgba(255,255,255,.72) 0 1px,transparent 1px 4px);
}
.sigl-board--bull{
  --sigl-accent:#63D9A2;
  --sigl-accent-soft:rgba(99,217,162,.18);
  --sigl-accent-strong:rgba(99,217,162,.36);
}
.sigl-board--bear{
  --sigl-accent:#FF8F96;
  --sigl-accent-soft:rgba(255,143,150,.18);
  --sigl-accent-strong:rgba(255,143,150,.36);
}
.sigl-board--neutral{
  --sigl-accent:#F6C35E;
  --sigl-accent-soft:rgba(246,195,94,.18);
  --sigl-accent-strong:rgba(246,195,94,.34);
}
.sigl-board--scanner{
  --sigl-accent:#7DD3FC;
  --sigl-accent-soft:rgba(125,211,252,.18);
  --sigl-accent-strong:rgba(125,211,252,.34);
}
.sigl-board-glow{
  position:absolute;
  inset:-24% -8% auto -8%;
  height:50%;
  pointer-events:none;
  background:radial-gradient(circle at center,rgba(255,255,255,.1),transparent 58%);
  filter:blur(46px);
  opacity:.72;
}
.sigl-board-sweep{
  position:absolute;
  inset:-24% auto -20% -36%;
  width:32%;
  pointer-events:none;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.05),rgba(255,255,255,.16),rgba(255,255,255,.05),transparent);
  transform:skewX(-18deg);
  mix-blend-mode:screen;
  animation:siglSweep 5.8s linear infinite;
}
.sigl-topbar{
  position:relative;
  z-index:2;
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  flex-wrap:wrap;
  padding:11px 15px;
  border-bottom:1px solid rgba(148,163,184,.12);
  background:linear-gradient(180deg,rgba(10,14,21,.96),rgba(6,9,14,.92));
}
.sigl-topbar-brand{
  display:flex;
  align-items:center;
  gap:12px;
  flex-wrap:wrap;
}
.sigl-topbar-badge,
.sigl-topbar-copy,
.sigl-rail-chip,
.sigl-section-title,
.sigl-section-copy,
.sigl-metric-label,
.sigl-focus-kicker,
.sigl-meta-chip,
.sigl-lane-key,
.sigl-lane-time{
  font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace;
  text-transform:uppercase;
}
.sigl-topbar-badge{
  color:var(--sigl-accent);
  font-size:.69rem;
  font-weight:800;
  letter-spacing:.18em;
  text-shadow:0 0 8px rgba(255,255,255,.08);
}
.sigl-topbar-copy{
  color:#64748B;
  font-size:.67rem;
  font-weight:800;
  letter-spacing:.16em;
}
.sigl-rail-cluster{
  display:flex;
  align-items:center;
  gap:8px;
  flex-wrap:wrap;
}
.sigl-rail-chip{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding:7px 10px;
  border-radius:999px;
  border:1px solid rgba(148,163,184,.12);
  background:linear-gradient(180deg,rgba(13,17,25,.96),rgba(8,11,18,.92));
  color:#CBD5E1;
  font-size:.7rem;
  font-weight:800;
  letter-spacing:.12em;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.04);
}
.sigl-rail-chip strong{
  color:#F8FAFC;
  font-size:.78rem;
  font-weight:800;
}
.sigl-pulse{
  width:9px;
  height:9px;
  border-radius:999px;
  background:var(--sigl-accent);
  box-shadow:0 0 12px var(--sigl-accent),0 0 24px rgba(255,255,255,.12);
  animation:siglPulse 1.6s ease-in-out infinite;
}
.sigl-main{
  position:relative;
  z-index:2;
  display:grid;
  gap:12px;
  padding:14px;
}
.sigl-summary-panel,
.sigl-lanes-panel{
  position:relative;
  border:1px solid rgba(148,163,184,.14);
  border-radius:18px;
  background:linear-gradient(180deg,rgba(8,11,17,.97),rgba(6,9,14,.93));
  box-shadow:inset 0 1px 0 rgba(255,255,255,.03);
}
.sigl-summary-panel{
  padding:14px;
  overflow:hidden;
}
.sigl-summary-panel::before,
.sigl-lanes-panel::before{
  content:"";
  position:absolute;
  inset:0 0 auto 0;
  height:2px;
  background:linear-gradient(90deg,transparent,var(--sigl-accent),transparent);
  opacity:.52;
}
.sigl-summary-stack{
  display:grid;
  gap:12px;
}
.sigl-brand-line{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap:12px;
  flex-wrap:wrap;
}
.sigl-brand-banner{
  display:inline-flex;
  align-items:center;
  padding:12px 14px;
  border-radius:14px;
  border:1px solid rgba(226,232,240,.1);
  border-bottom-color:var(--sigl-accent-strong);
  background:linear-gradient(180deg,#111722,#090D14);
  color:#F8FAFC;
  font-size:1.92rem;
  font-weight:800;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.05),0 0 24px rgba(255,255,255,.04);
}
.sigl-brand-copy{
  max-width:46ch;
  color:#94A3B8;
  font-size:.78rem;
  line-height:1.58;
}
.sigl-focus-strip{
  display:grid;
  gap:12px;
  padding:13px 14px;
  border-radius:16px;
  border:1px solid rgba(148,163,184,.13);
  background:
    linear-gradient(180deg,rgba(11,15,23,.98),rgba(7,10,15,.92)),
    radial-gradient(circle at top right,rgba(255,255,255,.04),transparent 34%);
}
.sigl-focus-main{
  display:flex;
  align-items:flex-end;
  justify-content:space-between;
  gap:12px;
  flex-wrap:wrap;
}
.sigl-focus-block{
  display:grid;
  gap:6px;
}
.sigl-focus-kicker{
  margin:0;
  color:#64748B;
  font-size:.66rem;
  font-weight:800;
  letter-spacing:.18em;
}
.sigl-focus-ticker{
  color:var(--sigl-accent);
  font-size:2.35rem;
  font-weight:800;
  line-height:1;
}
.sigl-focus-price-row{
  display:flex;
  align-items:center;
  gap:10px;
  flex-wrap:wrap;
}
.sigl-focus-price{
  color:#F8FAFC;
  font-size:1.08rem;
  font-weight:800;
}
.sigl-change{
  display:inline-flex;
  align-items:center;
  min-height:32px;
  padding:6px 10px;
  border-radius:999px;
  font-size:.78rem;
  font-weight:800;
  letter-spacing:.1em;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.04),0 0 18px rgba(255,255,255,.03);
}
.sigl-change--bull{
  color:#B8F1D5;
  background:linear-gradient(180deg,rgba(7,30,21,.98),rgba(6,20,16,.92));
  border:1px solid rgba(99,217,162,.26);
}
.sigl-change--bear{
  color:#FFD2D7;
  background:linear-gradient(180deg,rgba(33,14,18,.98),rgba(21,10,14,.92));
  border:1px solid rgba(255,143,150,.26);
}
.sigl-change--neutral{
  color:#F8DE9A;
  background:linear-gradient(180deg,rgba(33,25,10,.96),rgba(18,14,8,.92));
  border:1px solid rgba(246,195,94,.24);
}
.sigl-metric-strip{
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  gap:10px;
}
.sigl-metric-card{
  position:relative;
  padding:10px 11px;
  border-radius:12px;
  border:1px solid rgba(148,163,184,.12);
  background:linear-gradient(180deg,rgba(13,17,25,.98),rgba(8,11,18,.92));
  box-shadow:inset 0 1px 0 rgba(255,255,255,.03);
}
.sigl-metric-card::before{
  content:"";
  position:absolute;
  inset:0 auto auto 0;
  width:100%;
  height:2px;
  background:linear-gradient(90deg,var(--sigl-accent),transparent);
  opacity:.56;
}
.sigl-metric-label{
  margin:0 0 6px;
  color:#64748B;
  font-size:.62rem;
  font-weight:800;
  letter-spacing:.18em;
}
.sigl-metric-value{
  margin:0;
  color:#F8FAFC;
  font-size:.95rem;
  font-weight:800;
  line-height:1.2;
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
}
.sigl-metric-value--accent{color:var(--sigl-accent)}
.sigl-pill{
  display:inline-flex;
  align-items:center;
  gap:8px;
  min-height:32px;
  padding:6px 10px;
  border-radius:999px;
  border:1px solid rgba(148,163,184,.16);
  background:linear-gradient(180deg,rgba(15,19,28,.96),rgba(10,13,20,.9));
  font-size:.78rem;
  font-weight:800;
  line-height:1.2;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.03);
}
.sigl-pill--bull{
  color:#B8F1D5;
  background:linear-gradient(180deg,rgba(7,30,21,.98),rgba(6,20,16,.92));
  border-color:rgba(99,217,162,.26);
}
.sigl-pill--bear{
  color:#FFD2D7;
  background:linear-gradient(180deg,rgba(33,14,18,.98),rgba(21,10,14,.92));
  border-color:rgba(255,143,150,.26);
}
.sigl-pill--neutral{
  color:#F8DE9A;
  background:linear-gradient(180deg,rgba(33,25,10,.96),rgba(18,14,8,.92));
  border-color:rgba(246,195,94,.24);
}
.sigl-pill--scanner{
  color:#D6F2FF;
  background:linear-gradient(180deg,rgba(8,25,35,.96),rgba(8,18,26,.92));
  border-color:rgba(125,211,252,.24);
}
.sigl-flow-row{
  display:grid;
  gap:9px;
}
.sigl-flow-head{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  flex-wrap:wrap;
}
.sigl-section-title{
  color:#E2E8F0;
  font-size:.72rem;
  font-weight:800;
  letter-spacing:.18em;
}
.sigl-section-copy{
  color:#64748B;
  font-size:.66rem;
  font-weight:800;
  letter-spacing:.16em;
}
.sigl-flow-bar{
  display:flex;
  flex-wrap:wrap;
  gap:8px;
}
.sigl-flow-chip{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding:8px 10px;
  border-radius:999px;
  border:1px solid rgba(148,163,184,.16);
  background:linear-gradient(180deg,rgba(15,19,28,.96),rgba(10,13,20,.9));
  box-shadow:inset 0 1px 0 rgba(255,255,255,.03);
  font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace;
}
.sigl-flow-chip--bull{
  color:#B8F1D5;
  background:linear-gradient(180deg,rgba(7,30,21,.98),rgba(6,20,16,.92));
  border-color:rgba(99,217,162,.26);
}
.sigl-flow-chip--bear{
  color:#FFD2D7;
  background:linear-gradient(180deg,rgba(33,14,18,.98),rgba(21,10,14,.92));
  border-color:rgba(255,143,150,.26);
}
.sigl-flow-chip--neutral{
  color:#F8DE9A;
  background:linear-gradient(180deg,rgba(33,25,10,.96),rgba(18,14,8,.92));
  border-color:rgba(246,195,94,.24);
}
.sigl-flow-chip--combo{
  box-shadow:inset 0 1px 0 rgba(255,255,255,.03),0 0 18px rgba(255,255,255,.05);
}
.sigl-flow-icon,
.sigl-flow-date{
  font-size:.69rem;
  font-weight:800;
}
.sigl-flow-text{
  font-size:.73rem;
  font-weight:800;
  letter-spacing:.04em;
}
.sigl-meta-bar{
  display:flex;
  flex-wrap:wrap;
  gap:8px;
}
.sigl-meta-chip{
  display:inline-flex;
  align-items:center;
  gap:8px;
  min-height:30px;
  padding:6px 10px;
  border-radius:999px;
  border:1px solid rgba(148,163,184,.14);
  background:linear-gradient(180deg,rgba(12,16,24,.98),rgba(8,11,18,.92));
  color:#CBD5E1;
  font-size:.7rem;
  font-weight:800;
  letter-spacing:.14em;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.03);
}
.sigl-meta-chip--bull{border-color:rgba(99,217,162,.24);color:#B8F1D5}
.sigl-meta-chip--bear{border-color:rgba(255,143,150,.24);color:#FFD2D7}
.sigl-meta-chip--neutral{border-color:rgba(246,195,94,.22);color:#F8DE9A}
.sigl-meta-chip--scanner{border-color:rgba(125,211,252,.22);color:#D6F2FF}
.sigl-meta-chip strong{
  color:#F8FAFC;
  font-size:.76rem;
  font-weight:800;
  letter-spacing:0;
}
.sigl-summary{
  margin:0;
  color:#94A3B8;
  font-size:.77rem;
  line-height:1.58;
}
.sigl-lanes-panel{
  padding:12px;
  display:grid;
  gap:10px;
}
.sigl-lanes-head{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  flex-wrap:wrap;
}
.sigl-lane-list{
  display:grid;
  gap:8px;
}
.sigl-lane{
  --sigl-row-accent:rgba(246,195,94,.78);
  position:relative;
  overflow:hidden;
  border-radius:12px;
  border:1px solid rgba(148,163,184,.11);
  background:linear-gradient(180deg,rgba(12,16,24,.98),rgba(8,11,18,.93));
  box-shadow:inset 0 1px 0 rgba(255,255,255,.03);
}
.sigl-lane::before{
  content:"";
  position:absolute;
  inset:0 auto 0 0;
  width:3px;
  background:var(--sigl-row-accent);
  box-shadow:0 0 12px var(--sigl-row-accent);
}
.sigl-lane::after{
  content:"";
  position:absolute;
  inset:0;
  background:linear-gradient(90deg,rgba(255,255,255,.04),transparent 24%);
  opacity:.28;
}
.sigl-lane--bull{--sigl-row-accent:rgba(99,217,162,.82)}
.sigl-lane--bear{--sigl-row-accent:rgba(255,143,150,.82)}
.sigl-lane--neutral,
.sigl-lane--scanner{--sigl-row-accent:rgba(246,195,94,.78)}
.sigl-lane--fresh{animation:siglLaneFlash .9s ease both}
.sigl-lane-window{
  overflow:hidden;
}
.sigl-lane-track{
  display:flex;
  width:max-content;
  animation:siglLaneMarquee 15s linear infinite;
  will-change:transform;
}
.sigl-lane-group{
  display:inline-flex;
  align-items:center;
  gap:10px;
  min-width:max-content;
  padding:11px 22px 11px 14px;
  color:#D8E2EC;
  text-transform:uppercase;
  font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace;
  text-shadow:0 0 7px currentColor,0 0 16px rgba(255,255,255,.08);
}
.sigl-lane-time{
  color:#94A3B8;
  font-size:.72rem;
  font-weight:800;
  letter-spacing:.16em;
}
.sigl-led{
  font-family:'SIGL Segment','JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace !important;
  letter-spacing:.16em;
  text-transform:uppercase;
  text-shadow:0 0 10px currentColor,0 0 22px rgba(255,255,255,.08);
}
.sigl-led--tight{letter-spacing:.12em}
.sigl-led--soft{text-shadow:0 0 8px currentColor,0 0 16px rgba(255,255,255,.06)}
.sigl-lane-chip{
  display:inline-flex;
  align-items:center;
  min-height:32px;
  padding:6px 10px;
  border-radius:999px;
  border:1px solid rgba(148,163,184,.14);
  background:linear-gradient(180deg,rgba(13,17,25,.96),rgba(8,11,18,.92));
  box-shadow:inset 0 1px 0 rgba(255,255,255,.03);
}
.sigl-lane-chip--ticker{
  color:var(--sigl-accent);
  font-size:.88rem;
  font-weight:800;
}
.sigl-lane-field{
  display:inline-flex;
  align-items:center;
  gap:8px;
}
.sigl-lane-key{
  color:#64748B;
  font-size:.67rem;
  font-weight:800;
  letter-spacing:.16em;
}
.sigl-lane-value{
  color:#F8FAFC;
  font-size:.79rem;
  font-weight:800;
}
.sigl-lane-value--bull{color:#63D9A2}
.sigl-lane-value--bear{color:#FF8F96}
.sigl-lane-value--neutral{color:#F6C35E}
.sigl-lane-badge{
  display:inline-flex;
  align-items:center;
  min-height:32px;
  padding:6px 10px;
  border-radius:999px;
  border:1px solid rgba(148,163,184,.16);
  background:linear-gradient(180deg,rgba(15,19,28,.96),rgba(10,13,20,.9));
  font-size:.74rem;
  font-weight:800;
  letter-spacing:.08em;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.03),0 0 14px rgba(255,255,255,.03);
}
.sigl-lane-badge--bull{
  color:#B8F1D5;
  background:linear-gradient(180deg,rgba(7,30,21,.98),rgba(6,20,16,.92));
  border-color:rgba(99,217,162,.26);
}
.sigl-lane-badge--bear{
  color:#FFD2D7;
  background:linear-gradient(180deg,rgba(33,14,18,.98),rgba(21,10,14,.92));
  border-color:rgba(255,143,150,.26);
}
.sigl-lane-badge--neutral{
  color:#F8DE9A;
  background:linear-gradient(180deg,rgba(33,25,10,.96),rgba(18,14,8,.92));
  border-color:rgba(246,195,94,.24);
}
.sigl-lane-badge--scanner{
  color:#D6F2FF;
  background:linear-gradient(180deg,rgba(8,25,35,.96),rgba(8,18,26,.92));
  border-color:rgba(125,211,252,.24);
}
.sigl-lane-badge--ghost{
  box-shadow:inset 0 1px 0 rgba(255,255,255,.03),0 0 16px rgba(255,255,255,.06);
}
.sigl-board--compact .sigl-brand-copy,
.sigl-board--compact .sigl-summary,
.sigl-board--compact .sigl-flow-row,
.sigl-board--compact .sigl-meta-bar{
  display:none;
}
.sigl-board--compact .sigl-focus-ticker{font-size:1.88rem}
.sigl-board--compact .sigl-metric-strip{grid-template-columns:repeat(2,minmax(0,1fr))}
.sigl-board--compact .sigl-lane:nth-child(n+4){display:none}
@keyframes siglLaneMarquee{
  from{transform:translateX(0)}
  to{transform:translateX(-50%)}
}
@keyframes siglPulse{
  0%,100%{opacity:.42;transform:scale(.92)}
  50%{opacity:1;transform:scale(1.14)}
}
@keyframes siglSweep{
  0%{transform:translateX(0) skewX(-18deg);opacity:0}
  10%{opacity:.18}
  48%{opacity:.24}
  72%{opacity:.06}
  100%{transform:translateX(440%) skewX(-18deg);opacity:0}
}
@keyframes siglLaneFlash{
  0%{filter:brightness(2.1);opacity:.2}
  55%{filter:brightness(1.18);opacity:1}
  100%{filter:brightness(1);opacity:1}
}
@media (max-width:980px){
  .sigl-metric-strip{grid-template-columns:repeat(2,minmax(0,1fr))}
}
@media (max-width:760px){
  .sigl-topbar{padding:10px 12px}
  .sigl-brand-banner{font-size:1.55rem}
  .sigl-brand-copy,
  .sigl-summary{display:none}
  .sigl-focus-ticker{font-size:1.9rem}
  .sigl-focus-main{align-items:flex-start}
  .sigl-metric-strip{grid-template-columns:repeat(2,minmax(0,1fr))}
  .sigl-lane-group{padding:10px 18px 10px 14px}
  .sigl-flow-chip:nth-child(n+4),
  .sigl-meta-chip:nth-child(n+4),
  .sigl-lane:nth-child(n+5){display:none}
}
@media (prefers-reduced-motion: reduce){
  .sigl-board-sweep,
  .sigl-lane--fresh,
  .sigl-pulse{
    animation:none;
  }
  .sigl-lane-track{
    animation-duration:40s !important;
  }
}
"""

INITIAL_MESSAGE_CONTENT = (
    f"{BRAND_PAGE_ICON} **[ {BRAND_NAME} ]**\n"
    "Select target ticker from the sidebar or type one like `NVDA` to begin."
)


def _esc(value, fallback="--"):
    text = str(value).strip() if value is not None else ""
    return html.escape(text or fallback)


def _tone_class(value, fallback="neutral"):
    tone = str(value or fallback).strip().lower()
    return tone if tone in {"bull", "bear", "neutral", "scanner"} else fallback


def _signal_tone(value, fallback="neutral"):
    text = str(value or "").strip().lower()
    if any(token in text for token in ("buy", "bull", "up", "strong_buy", "long")):
        return "bull"
    if any(token in text for token in ("sell", "bear", "down", "strong_sell", "short")):
        return "bear"
    return fallback


def _change_tone(value, fallback="neutral"):
    text = str(value or "").strip().lower()
    if text in {"up", "bull", "positive"}:
        return "bull"
    if text in {"down", "bear", "negative"}:
        return "bear"
    return fallback


def _placeholder_history_rows():
    return [
        {
            "time": "--:--",
            "ticker": "WAIT",
            "price": "--",
            "change": "--",
            "change_tone": "flat",
            "signal": "IDLE",
            "recent": "STANDBY",
            "recent_tone": "neutral",
            "tone": "neutral",
            "fresh": idx == 0,
        }
        for idx in range(5)
    ]


def _placeholder_recent_signals():
    return [{"icon": "*", "label": "AWAITING SIGNAL", "date": "--/--", "dir": "neutral", "is_combined": False}]


def _build_flow_chips(items):
    active_items = list(items or [])[:4] or _placeholder_recent_signals()
    chips = []
    for item in active_items:
        tone = _signal_tone(item.get("dir"))
        combo_class = " sigl-flow-chip--combo" if item.get("is_combined") else ""
        chips.append(
            f"""
            <span class="sigl-flow-chip sigl-flow-chip--{tone}{combo_class}">
                <span class="sigl-flow-icon">{_esc(item.get("icon"), "*")}</span>
                <span class="sigl-flow-text">{_esc(item.get("label"), "AWAITING SIGNAL")}</span>
                <span class="sigl-flow-date sigl-led sigl-led--soft">{_esc(item.get("date"), "--/--")}</span>
            </span>
            """
        )
    return "".join(chips)


def _build_meta_chips(summary):
    summary = summary or {}
    items = []

    buy = summary.get("buy_agree")
    sell = summary.get("sell_agree")
    items.append({
        "label": "B:S",
        "value": f"{buy if buy is not None else '--'}:{sell if sell is not None else '--'}",
        "tone": "neutral",
        "segment": True,
    })

    veto = str(summary.get("veto_flags") or "").strip()
    if veto:
        items.append({"label": "RISK", "value": veto, "tone": "bear", "segment": False})
    else:
        combined_scans = list(summary.get("combined_scans") or [])
        for scan in combined_scans[:2]:
            scan_label = scan.get("kor") or scan.get("label") or scan.get("name") or "COMBO READY"
            scan_icon = scan.get("icon") or "*"
            items.append({
                "label": "STACK",
                "value": f"{scan_icon} {scan_label}",
                "tone": _signal_tone(scan.get("dir")),
                "segment": False,
            })
        if len(items) < 3:
            lead = str(summary.get("leading_verdict") or "").strip()
            if lead:
                items.append({"label": "LEAD", "value": lead, "tone": "neutral", "segment": False})
        if len(items) < 4:
            lag = str(summary.get("lagging_verdict") or "").strip()
            if lag:
                items.append({"label": "LAG", "value": lag, "tone": "neutral", "segment": False})

    chips = []
    for item in items[:4]:
        tone = _tone_class(item.get("tone"))
        value = _esc(item.get("value"), "STANDBY")
        if item.get("segment"):
            value = f"<strong class='sigl-led sigl-led--soft'>{value}</strong>"
        else:
            value = f"<strong>{value}</strong>"
        chips.append(
            f"""
            <span class="sigl-meta-chip sigl-meta-chip--{tone}">
                {html.escape(str(item.get("label") or "STACK"))}
                {value}
            </span>
            """
        )
    return "".join(chips)


def _build_lane_group(row):
    signal_tone = _signal_tone(row.get("signal"), _tone_class(row.get("tone"), "neutral"))
    change_tone = _change_tone(row.get("change_tone"))
    recent_tone = _signal_tone(row.get("recent_tone"))
    return f"""
    <div class="sigl-lane-group">
        <span class="sigl-lane-time sigl-led sigl-led--soft">{_esc(row.get("time"), "--:--")}</span>
        <span class="sigl-lane-chip sigl-lane-chip--ticker sigl-led">{_esc(row.get("ticker"), "WAIT")}</span>
        <span class="sigl-lane-field">
            <span class="sigl-lane-key">PX</span>
            <span class="sigl-lane-value sigl-led sigl-led--tight">{_esc(row.get("price"), "--")}</span>
        </span>
        <span class="sigl-lane-field">
            <span class="sigl-lane-key">D1</span>
            <span class="sigl-lane-value sigl-lane-value--{change_tone}">{_esc(row.get("change"), "--")}</span>
        </span>
        <span class="sigl-lane-badge sigl-lane-badge--{signal_tone}">{_esc(row.get("signal"), "IDLE")}</span>
        <span class="sigl-lane-key">RECENT</span>
        <span class="sigl-lane-badge sigl-lane-badge--{recent_tone} sigl-lane-badge--ghost">{_esc(row.get("recent"), "STANDBY")}</span>
    </div>
    """


def _build_log_lanes(rows):
    active_rows = list(rows or [])[:5] or _placeholder_history_rows()
    durations = [14, 16, 18, 15, 17]
    delays = [0, -3, -6, -2, -5]
    lanes = []

    for idx, row in enumerate(active_rows):
        tone = _tone_class(row.get("tone"))
        fresh_class = " sigl-lane--fresh" if idx == 0 and row.get("fresh", True) else ""
        duration = durations[idx % len(durations)]
        delay = delays[idx % len(delays)]
        group_html = _build_lane_group(row)
        lanes.append(
            f"""
            <div class="sigl-lane sigl-lane--{tone}{fresh_class}">
                <div class="sigl-lane-window">
                    <div class="sigl-lane-track" style="animation-duration:{duration}s;animation-delay:{delay}s">
                        {group_html}
                        {group_html}
                    </div>
                </div>
            </div>
            """
        )
    return "".join(lanes)


def _format_log_count(value):
    try:
        return f"{int(value):02d}"
    except (TypeError, ValueError):
        return "00"


def build_brand_board(payload, compact=False):
    board_class = "sigl-board sigl-board--compact" if compact else "sigl-board"
    tone = _tone_class(payload.get("status_tone"))
    board_class += f" sigl-board--{tone}"

    mode = _esc(payload.get("mode"), "ANALYSIS")
    brand_code = _esc(payload.get("brand_code"), BRAND_NAME)
    system_status = _esc(payload.get("system_status"), "READY")
    feed_status = _esc(payload.get("feed_status"), "MARKET_SYNC")
    focus = _esc(payload.get("focus"), "WAIT")
    price = _esc(payload.get("price"), "--")
    change = _esc(payload.get("change"), "--")
    change_tone = _change_tone(payload.get("change_tone"))
    signal = _esc(payload.get("judgment"), "IDLE")
    signal_tone = _signal_tone(payload.get("judgment"), "neutral")
    recent_label = _esc(payload.get("recent_label"), "STANDBY")
    recent_tone = _signal_tone(payload.get("recent_tone"))
    context = _esc(payload.get("context"), "STANDBY")
    period = _esc(payload.get("period"), "6M")
    analysis_count = _format_log_count(payload.get("analysis_count"))
    summary = _esc(payload.get("summary"), "")
    summary_html = f"<p class='sigl-summary'>{summary}</p>" if summary else ""

    return f"""<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <style>{_BOARD_CSS}</style>
</head>
<body>
    <div class="{board_class}">
        <div class="sigl-board-glow"></div>
        <div class="sigl-board-sweep"></div>
        <div class="sigl-topbar">
            <div class="sigl-topbar-brand">
                <span class="sigl-topbar-badge">SIGL SIGNAL TERMINAL</span>
                <span class="sigl-topbar-copy">HTS / MTS LED LOGBOARD</span>
            </div>
            <div class="sigl-rail-cluster">
                <span class="sigl-rail-chip">MODE <strong>{mode}</strong></span>
                <span class="sigl-rail-chip"><span class="sigl-pulse"></span>STATUS <strong>{system_status}</strong></span>
                <span class="sigl-rail-chip">FEED <strong>{feed_status}</strong></span>
                <span class="sigl-rail-chip">LOG <strong class="sigl-led sigl-led--tight">{analysis_count}</strong></span>
            </div>
        </div>
        <div class="sigl-main">
            <div class="sigl-summary-panel">
                <div class="sigl-summary-stack">
                    <div class="sigl-brand-line">
                        <div class="sigl-brand-banner sigl-led">[ {brand_code} ]</div>
                        <div class="sigl-brand-copy">Signal infrastructure that keeps feeding structured reads into a glowing ticker board.</div>
                    </div>
                    <div class="sigl-focus-strip">
                        <div class="sigl-focus-main">
                            <div class="sigl-focus-block">
                                <p class="sigl-focus-kicker">Current Target</p>
                                <div class="sigl-focus-ticker sigl-led">{focus}</div>
                                <div class="sigl-focus-price-row">
                                    <span class="sigl-focus-price sigl-led sigl-led--soft">{price}</span>
                                    <span class="sigl-change sigl-change--{change_tone}">{change}</span>
                                </div>
                            </div>
                        </div>
                        <div class="sigl-metric-strip">
                            <div class="sigl-metric-card">
                                <p class="sigl-metric-label">Signal</p>
                                <p class="sigl-metric-value"><span class="sigl-pill sigl-pill--{signal_tone}">{signal}</span></p>
                            </div>
                            <div class="sigl-metric-card">
                                <p class="sigl-metric-label">Recent Signal</p>
                                <p class="sigl-metric-value"><span class="sigl-pill sigl-pill--{recent_tone}">{recent_label}</span></p>
                            </div>
                            <div class="sigl-metric-card">
                                <p class="sigl-metric-label">CTX</p>
                                <p class="sigl-metric-value">{context}</p>
                            </div>
                            <div class="sigl-metric-card">
                                <p class="sigl-metric-label">SPAN</p>
                                <p class="sigl-metric-value sigl-metric-value--accent sigl-led sigl-led--tight">{period}</p>
                            </div>
                        </div>
                    </div>
                    <div class="sigl-flow-row">
                        <div class="sigl-flow-head">
                            <span class="sigl-section-title">Recent Signal Flow</span>
                            <span class="sigl-section-copy">Current target terminal feed</span>
                        </div>
                        <div class="sigl-flow-bar">{_build_flow_chips(payload.get("focus_recent_signals"))}</div>
                    </div>
                    <div class="sigl-meta-bar">{_build_meta_chips(payload.get("focus_stack_summary"))}</div>
                    {summary_html}
                </div>
            </div>
            <div class="sigl-lanes-panel">
                <div class="sigl-lanes-head">
                    <span class="sigl-section-title">Analysis Logboard</span>
                    <span class="sigl-section-copy">Ticker / price / daily move / signal / recent signal</span>
                </div>
                <div class="sigl-lane-list">{_build_log_lanes(payload.get("history_rows"))}</div>
            </div>
        </div>
    </div>
</body>
</html>"""
