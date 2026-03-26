import html

BRAND_NAME = "SIGL"
BRAND_PAGE_TITLE = BRAND_NAME
BRAND_PAGE_ICON = "📶"
BRAND_REPORT_SLUG = "sigl"

_BOARD_CSS = """
@font-face{
  font-family:'SIGL Segment';
  src:local('DSEG7 Classic'),local('DS-Digital'),local('DS-DIGI'),local('Digital-7'),local('Consolas');
}
html,body{margin:0;padding:0;background:transparent;font-family:'Pretendard',system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
*{box-sizing:border-box}
.sigl-board{--sigl-accent:#A5B4FC;--sigl-accent-soft:rgba(165,180,252,.18);--sigl-accent-strong:rgba(165,180,252,.36);
position:relative;overflow:hidden;border:1px solid rgba(148,163,184,.16);border-radius:22px;margin:0;
background:
linear-gradient(180deg,rgba(2,5,10,.992),rgba(7,10,15,.992)),
radial-gradient(circle at top right,rgba(165,180,252,.09),transparent 36%),
radial-gradient(circle at bottom left,rgba(22,163,74,.05),transparent 28%);
box-shadow:0 22px 54px rgba(2,6,23,.38),inset 0 1px 0 rgba(255,255,255,.04)}
.sigl-board:before{content:"";position:absolute;inset:0;pointer-events:none;opacity:.22;
background:
radial-gradient(circle at 1px 1px,rgba(255,255,255,.18) .7px,transparent .8px) 0 0/7px 7px,
radial-gradient(circle at 1px 1px,rgba(255,255,255,.04) .7px,transparent .8px) 3px 3px/7px 7px}
.sigl-board:after{content:"";position:absolute;inset:0;pointer-events:none;opacity:.09;
background:repeating-linear-gradient(180deg,rgba(255,255,255,.8) 0 1px,transparent 1px 4px)}
.sigl-board--bull{--sigl-accent:#63D9A2;--sigl-accent-soft:rgba(99,217,162,.18);--sigl-accent-strong:rgba(99,217,162,.36)}
.sigl-board--bear{--sigl-accent:#FF8F96;--sigl-accent-soft:rgba(255,143,150,.18);--sigl-accent-strong:rgba(255,143,150,.36)}
.sigl-board--neutral{--sigl-accent:#F6C35E;--sigl-accent-soft:rgba(246,195,94,.18);--sigl-accent-strong:rgba(246,195,94,.34)}
.sigl-board--scanner{--sigl-accent:#7DD3FC;--sigl-accent-soft:rgba(125,211,252,.18);--sigl-accent-strong:rgba(125,211,252,.34)}
.sigl-board-glow{position:absolute;inset:-26% -8% auto -8%;height:48%;pointer-events:none;
background:radial-gradient(circle at center,rgba(255,255,255,.08),transparent 58%);filter:blur(44px);opacity:.65}
.sigl-board-sweep{position:absolute;inset:-18% auto -18% -34%;width:34%;pointer-events:none;
background:linear-gradient(90deg,transparent,rgba(255,255,255,.06),rgba(255,255,255,.14),rgba(255,255,255,.06),transparent);
mix-blend-mode:screen;transform:skewX(-18deg);animation:siglSweep 8.2s linear infinite}
.sigl-topbar{position:relative;z-index:2;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;
padding:11px 15px;border-bottom:1px solid rgba(148,163,184,.12);
background:linear-gradient(180deg,rgba(10,14,21,.95),rgba(6,9,14,.92))}
.sigl-topbar-brand{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.sigl-topbar-badge{color:var(--sigl-accent);font-size:.69rem;font-weight:800;letter-spacing:.18em;text-transform:uppercase;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace;text-shadow:0 0 8px rgba(255,255,255,.08)}
.sigl-topbar-copy{color:#64748B;font-size:.67rem;font-weight:800;letter-spacing:.16em;text-transform:uppercase;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace}
.sigl-rail-cluster{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.sigl-rail-chip{display:inline-flex;align-items:center;gap:8px;padding:7px 10px;border-radius:999px;
background:linear-gradient(180deg,rgba(13,17,25,.96),rgba(8,11,18,.92));border:1px solid rgba(148,163,184,.12);
color:#CBD5E1;font-size:.7rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace;box-shadow:inset 0 1px 0 rgba(255,255,255,.04)}
.sigl-rail-chip strong{color:#F8FAFC;font-size:.78rem;font-weight:800}
.sigl-pulse{width:9px;height:9px;border-radius:999px;background:var(--sigl-accent);box-shadow:0 0 12px var(--sigl-accent),0 0 26px rgba(255,255,255,.12);animation:siglPulse 1.55s ease-in-out infinite}
.sigl-board-shell{position:relative;z-index:2;display:grid;grid-template-columns:minmax(0,1.18fr) minmax(340px,.92fr);gap:12px;padding:14px}
.sigl-log-panel,.sigl-data-panel{position:relative;background:linear-gradient(180deg,rgba(8,11,17,.97),rgba(6,9,14,.93));
border:1px solid rgba(148,163,184,.14);border-radius:16px;box-shadow:inset 0 1px 0 rgba(255,255,255,.03)}
.sigl-log-panel{padding:12px}
.sigl-data-panel{padding:12px;display:grid;gap:12px}
.sigl-section-head{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;padding:0 1px 10px;border-bottom:1px solid rgba(148,163,184,.10)}
.sigl-section-title{color:#E2E8F0;font-size:.73rem;font-weight:800;letter-spacing:.18em;text-transform:uppercase;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace}
.sigl-section-copy{color:var(--sigl-accent);font-size:.67rem;font-weight:800;letter-spacing:.18em;text-transform:uppercase;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace}
.sigl-led{font-family:'SIGL Segment','JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace!important;
letter-spacing:.16em;text-transform:uppercase;text-shadow:0 0 10px currentColor,0 0 22px rgba(255,255,255,.08)}
.sigl-led--tight{letter-spacing:.12em}
.sigl-led--soft{text-shadow:0 0 8px currentColor,0 0 16px rgba(255,255,255,.06)}
.sigl-log-head,.sigl-log-row{display:grid;grid-template-columns:64px 96px minmax(0,1fr) 78px minmax(0,1.05fr);gap:10px;align-items:center}
.sigl-log-head{padding:10px 10px 8px;color:#64748B;font-size:.61rem;font-weight:800;letter-spacing:.18em;text-transform:uppercase;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace}
.sigl-log-wall{display:grid;gap:8px;padding-top:8px}
.sigl-log-row{padding:10px;border-radius:12px;background:linear-gradient(180deg,rgba(12,16,24,.98),rgba(8,11,18,.93));
border:1px solid rgba(148,163,184,.11);box-shadow:inset 0 1px 0 rgba(255,255,255,.03);position:relative;overflow:hidden}
.sigl-log-row:before{content:"";position:absolute;inset:0 auto 0 0;width:3px;background:var(--sigl-row-accent,rgba(246,195,94,.75))}
.sigl-log-row:after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(255,255,255,.04),transparent 28%);opacity:.32}
.sigl-log-row--bull{--sigl-row-accent:rgba(99,217,162,.82)}
.sigl-log-row--bear{--sigl-row-accent:rgba(255,143,150,.82)}
.sigl-log-row--neutral,.sigl-log-row--scanner{--sigl-row-accent:rgba(246,195,94,.78)}
.sigl-log-row--fresh{animation:siglLogFlash .82s ease both}
.sigl-log-value,.sigl-log-text{min-width:0}
.sigl-log-value{color:#F8FAFC;font-size:.82rem;font-weight:800}
.sigl-log-value--ticker,.sigl-log-value--es{color:var(--sigl-accent)}
.sigl-log-text{color:#CBD5E1;font-size:.77rem;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace}
.sigl-log-context{color:#94A3B8}
.sigl-brand-row{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;flex-wrap:wrap}
.sigl-brand-banner{display:inline-flex;align-items:center;padding:12px 14px;border-radius:14px;
background:linear-gradient(180deg,#111722,#090D14);border:1px solid rgba(226,232,240,.10);border-bottom-color:var(--sigl-accent-strong);
color:#F8FAFC;font-size:1.95rem;font-weight:800;box-shadow:inset 0 1px 0 rgba(255,255,255,.04),0 0 22px rgba(255,255,255,.04)}
.sigl-brand-copy{max-width:26ch;color:#94A3B8;font-size:.78rem;line-height:1.55}
.sigl-focus-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
.sigl-focus-card{position:relative;padding:10px 11px;border-radius:12px;background:linear-gradient(180deg,rgba(13,17,25,.98),rgba(8,11,18,.92));
border:1px solid rgba(148,163,184,.12);box-shadow:inset 0 1px 0 rgba(255,255,255,.03)}
.sigl-focus-card:before{content:"";position:absolute;inset:0 auto auto 0;height:2px;width:100%;
background:linear-gradient(90deg,var(--sigl-accent),rgba(255,255,255,0));opacity:.54}
.sigl-focus-label{margin:0 0 6px;color:#64748B;font-size:.62rem;font-weight:800;letter-spacing:.18em;text-transform:uppercase;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace}
.sigl-focus-value{margin:0;color:#F8FAFC;font-size:.98rem;font-weight:800;line-height:1.18;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sigl-focus-value--accent{color:var(--sigl-accent)}
.sigl-subpanel{padding:11px;border-radius:14px;background:linear-gradient(180deg,rgba(10,14,21,.94),rgba(7,10,15,.9));
border:1px solid rgba(148,163,184,.12);box-shadow:inset 0 1px 0 rgba(255,255,255,.03)}
.sigl-subhead{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:9px}
.sigl-subtitle{color:#E2E8F0;font-size:.68rem;font-weight:800;letter-spacing:.18em;text-transform:uppercase;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace}
.sigl-subcopy{color:#64748B;font-size:.64rem;font-weight:800;letter-spacing:.16em;text-transform:uppercase;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace}
.sigl-signal-tags{display:flex;flex-wrap:wrap;gap:8px}
.sigl-signal-chip{display:inline-flex;align-items:center;gap:8px;padding:8px 10px;border-radius:999px;
border:1px solid rgba(148,163,184,.16);background:linear-gradient(180deg,rgba(15,19,28,.96),rgba(10,13,20,.9));
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace;box-shadow:inset 0 1px 0 rgba(255,255,255,.03)}
.sigl-signal-chip--bull{color:#B8F1D5;background:linear-gradient(180deg,rgba(7,30,21,.98),rgba(6,20,16,.92));border-color:rgba(99,217,162,.26)}
.sigl-signal-chip--bear{color:#FFD2D7;background:linear-gradient(180deg,rgba(33,14,18,.98),rgba(21,10,14,.92));border-color:rgba(255,143,150,.26)}
.sigl-signal-chip--neutral{color:#F8DE9A;background:linear-gradient(180deg,rgba(33,25,10,.96),rgba(18,14,8,.92));border-color:rgba(246,195,94,.24)}
.sigl-signal-chip--combo{box-shadow:inset 0 1px 0 rgba(255,255,255,.03),0 0 16px rgba(255,255,255,.04)}
.sigl-signal-icon,.sigl-signal-date{font-size:.7rem;font-weight:800}
.sigl-signal-label{font-size:.74rem;font-weight:800;letter-spacing:.04em}
.sigl-stack-grid{display:grid;gap:8px}
.sigl-stack-row{display:grid;grid-template-columns:72px minmax(0,1fr);gap:10px;align-items:center;padding:9px 10px;border-radius:11px;
background:linear-gradient(180deg,rgba(12,16,24,.98),rgba(8,11,18,.92));border:1px solid rgba(148,163,184,.11);box-shadow:inset 0 1px 0 rgba(255,255,255,.03)}
.sigl-stack-row--bull{border-color:rgba(99,217,162,.18)}
.sigl-stack-row--bear{border-color:rgba(255,143,150,.18)}
.sigl-stack-row--neutral{border-color:rgba(246,195,94,.16)}
.sigl-stack-label{color:#64748B;font-size:.64rem;font-weight:800;letter-spacing:.18em;text-transform:uppercase;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace}
.sigl-stack-value{min-width:0;color:#E2E8F0;font-size:.78rem;font-weight:800;line-height:1.35;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sigl-summary{margin:0;color:#94A3B8;font-size:.77rem;line-height:1.58}
.sigl-tape{position:relative;z-index:2;display:grid;grid-template-columns:auto 1fr;align-items:center;
border-top:1px solid rgba(148,163,184,.12);background:rgba(4,7,12,.98)}
.sigl-tape-label{padding:11px 14px;border-right:1px solid rgba(148,163,184,.12);color:var(--sigl-accent);font-size:.68rem;font-weight:800;
letter-spacing:.18em;text-transform:uppercase;font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace;
text-shadow:0 0 9px rgba(255,255,255,.09)}
.sigl-tape-window{overflow:hidden}
.sigl-tape-track{display:flex;gap:24px;width:max-content;padding:10px 0;animation:siglMarquee 24s linear infinite}
.sigl-tape-item{display:inline-flex;align-items:center;gap:9px;color:#CBD5E1;font-size:.76rem;font-weight:800;letter-spacing:.08em;white-space:nowrap;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace;text-transform:uppercase;
text-shadow:0 0 8px currentColor,0 0 18px rgba(255,255,255,.10)}
.sigl-tape-dot{width:7px;height:7px;border-radius:999px;background:var(--sigl-accent);box-shadow:0 0 12px var(--sigl-accent)}
.sigl-board--compact .sigl-board-shell{grid-template-columns:1fr;padding:12px}
.sigl-board--compact .sigl-topbar{padding:10px 12px}
.sigl-board--compact .sigl-brand-copy,.sigl-board--compact .sigl-summary,.sigl-board--compact .sigl-stack-grid,.sigl-board--compact .sigl-subpanel:last-of-type{display:none}
.sigl-board--compact .sigl-log-head{display:none}
.sigl-board--compact .sigl-log-row,.sigl-board--compact .sigl-log-head{grid-template-columns:56px 84px minmax(0,1fr)}
.sigl-board--compact .sigl-log-text:nth-child(4),.sigl-board--compact .sigl-log-text:nth-child(5){display:none}
.sigl-board--compact .sigl-log-row .sigl-log-value--es,.sigl-board--compact .sigl-log-row .sigl-log-context{display:none}
.sigl-board--compact .sigl-tape{grid-template-columns:1fr}
.sigl-board--compact .sigl-tape-label{display:none}
@keyframes siglMarquee{from{transform:translateX(0)}to{transform:translateX(-50%)}}
@keyframes siglPulse{0%,100%{opacity:.38;transform:scale(.92)}50%{opacity:1;transform:scale(1.12)}}
@keyframes siglSweep{0%{transform:translateX(0) skewX(-18deg);opacity:0}10%{opacity:.18}45%{opacity:.22}70%{opacity:.06}100%{transform:translateX(430%) skewX(-18deg);opacity:0}}
@keyframes siglLogFlash{0%{filter:brightness(1.95);transform:translateY(6px);opacity:.18}55%{filter:brightness(1.18);opacity:1}100%{filter:brightness(1);transform:translateY(0);opacity:1}}
@media (max-width:1120px){
  .sigl-board-shell{grid-template-columns:1fr}
}
@media (max-width:760px){
  .sigl-topbar{padding:10px 12px}
  .sigl-rail-chip{padding:7px 9px}
  .sigl-brand-banner{font-size:1.55rem}
  .sigl-focus-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .sigl-log-head,.sigl-log-row{grid-template-columns:58px 82px minmax(0,1fr) 68px}
  .sigl-log-context{display:none}
  .sigl-tape{grid-template-columns:1fr}
  .sigl-tape-label{display:none}
}
@media (prefers-reduced-motion: reduce){
  .sigl-board-sweep,.sigl-log-row--fresh,.sigl-pulse{animation:none}
  .sigl-tape-track{animation-duration:42s}
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


def _direction_tone(value, fallback="neutral"):
    text = str(value or "").strip().lower()
    if "buy" in text or text == "bull":
        return "bull"
    if "sell" in text or text == "bear":
        return "bear"
    return fallback


def _placeholder_history_rows():
    return [
        {"time": "--:--", "ticker": "WAIT", "signal": "IDLE", "es": "--", "context": "STANDBY", "tone": "neutral", "fresh": idx == 0}
        for idx in range(6)
    ]


def _placeholder_recent_signals():
    return [{"icon": "•", "label": "AWAITING SIGNAL", "date": "--/--", "dir": "neutral", "is_combined": False}]


def _build_history_rows(rows):
    active_rows = list(rows or [])[:8] or _placeholder_history_rows()
    row_html = []
    for idx, row in enumerate(active_rows):
        tone = _tone_class(row.get("tone"))
        fresh_class = " sigl-log-row--fresh" if idx == 0 and row.get("fresh", True) else ""
        row_html.append(
            f"""
            <div class="sigl-log-row sigl-log-row--{tone}{fresh_class}">
                <div class="sigl-log-value sigl-led sigl-led--soft">{_esc(row.get("time"), "--:--")}</div>
                <div class="sigl-log-value sigl-log-value--ticker sigl-led">{_esc(row.get("ticker"), "WAIT")}</div>
                <div class="sigl-log-text">{_esc(row.get("signal"), "IDLE")}</div>
                <div class="sigl-log-value sigl-log-value--es sigl-led sigl-led--tight">{_esc(row.get("es"), "--")}</div>
                <div class="sigl-log-text sigl-log-context">{_esc(row.get("context"), "STANDBY")}</div>
            </div>
            """
        )
    return "".join(row_html)


def _build_recent_signal_tags(items):
    active_items = list(items or [])[:5] or _placeholder_recent_signals()
    tags = []
    for item in active_items:
        tone = _direction_tone(item.get("dir"))
        combo_class = " sigl-signal-chip--combo" if item.get("is_combined") else ""
        tags.append(
            f"""
            <span class="sigl-signal-chip sigl-signal-chip--{tone}{combo_class}">
                <span class="sigl-signal-icon">{_esc(item.get("icon"), "•")}</span>
                <span class="sigl-signal-label">{_esc(item.get("label"), "AWAITING SIGNAL")}</span>
                <span class="sigl-signal-date sigl-led sigl-led--soft">{_esc(item.get("date"), "--/--")}</span>
            </span>
            """
        )
    return "".join(tags)


def _build_stack_rows(summary):
    summary = summary or {}
    rows = []
    buy = summary.get("buy_agree")
    sell = summary.get("sell_agree")
    rows.append({
        "label": "B:S",
        "value": f"{buy if buy is not None else '--'}:{sell if sell is not None else '--'}",
        "tone": "neutral",
        "segment": True,
    })

    for scan in list(summary.get("combined_scans") or [])[:2]:
        scan_label = scan.get("kor") or scan.get("label") or scan.get("name") or "COMBO READY"
        scan_icon = scan.get("icon") or "•"
        rows.append({
            "label": "COMBO",
            "value": f"{scan_icon} {scan_label}",
            "tone": _direction_tone(scan.get("dir")),
            "segment": False,
        })

    veto = str(summary.get("veto_flags") or "").strip()
    if veto:
        rows.append({"label": "RISK", "value": veto, "tone": "bear", "segment": False})
    else:
        lead = str(summary.get("leading_verdict") or "").strip()
        lag = str(summary.get("lagging_verdict") or "").strip()
        if lead:
            rows.append({"label": "LEAD", "value": lead, "tone": "neutral", "segment": False})
        if lag:
            rows.append({"label": "LAG", "value": lag, "tone": "neutral", "segment": False})

    if not rows:
        rows = [{"label": "STACK", "value": "STANDBY", "tone": "neutral", "segment": False}]

    html_rows = []
    for row in rows[:5]:
        tone = _tone_class(row.get("tone"))
        value_class = "sigl-stack-value sigl-led sigl-led--soft" if row.get("segment") else "sigl-stack-value"
        html_rows.append(
            f"""
            <div class="sigl-stack-row sigl-stack-row--{tone}">
                <div class="sigl-stack-label">{_esc(row.get("label"), "STACK")}</div>
                <div class="{value_class}">{_esc(row.get("value"), "STANDBY")}</div>
            </div>
            """
        )
    return "".join(html_rows)


def _build_marquee(items):
    clean_items = [str(item).strip() for item in (items or []) if str(item).strip()]
    if not clean_items:
        clean_items = [f"[ {BRAND_NAME} ] READY", "TARGET WAIT", "ES --", "SIGNAL IDLE"]
    repeated = clean_items + clean_items
    return "".join(
        f"<span class='sigl-tape-item'><span class='sigl-tape-dot'></span>{html.escape(item)}</span>"
        for item in repeated
    )


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
    signal = _esc(payload.get("judgment"), "IDLE")
    es_value = _esc(payload.get("es"), "--")
    context = _esc(payload.get("context"), "STANDBY")
    summary = _esc(payload.get("summary"), "")
    summary_html = f"<p class='sigl-summary'>{summary}</p>" if summary else ""
    analysis_count = _format_log_count(payload.get("analysis_count"))

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
                <span class="sigl-topbar-copy">LED LOGBOARD ROUTE</span>
            </div>
            <div class="sigl-rail-cluster">
                <span class="sigl-rail-chip">MODE <strong>{mode}</strong></span>
                <span class="sigl-rail-chip"><span class="sigl-pulse"></span>STATUS <strong>{system_status}</strong></span>
                <span class="sigl-rail-chip">FEED <strong>{feed_status}</strong></span>
                <span class="sigl-rail-chip">LOG <strong class="sigl-led sigl-led--tight">{analysis_count}</strong></span>
            </div>
        </div>
        <div class="sigl-board-shell">
            <div class="sigl-log-panel">
                <div class="sigl-section-head">
                    <span class="sigl-section-title">Analysis Logboard</span>
                    <span class="sigl-section-copy">Signal Ingress Ledger</span>
                </div>
                <div class="sigl-log-head">
                    <div>Time</div>
                    <div>Ticker</div>
                    <div>Signal</div>
                    <div>ES</div>
                    <div>CTX</div>
                </div>
                <div class="sigl-log-wall">{_build_history_rows(payload.get("history_rows"))}</div>
            </div>
            <div class="sigl-data-panel">
                <div class="sigl-brand-row">
                    <div class="sigl-brand-banner sigl-led">[ {brand_code} ]</div>
                    <div class="sigl-brand-copy">Signal infrastructure that keeps logging disciplined market reads into the board.</div>
                </div>
                <div class="sigl-focus-grid">
                    <div class="sigl-focus-card">
                        <p class="sigl-focus-label">Target</p>
                        <p class="sigl-focus-value sigl-focus-value--accent sigl-led">{focus}</p>
                    </div>
                    <div class="sigl-focus-card">
                        <p class="sigl-focus-label">Signal</p>
                        <p class="sigl-focus-value">{signal}</p>
                    </div>
                    <div class="sigl-focus-card">
                        <p class="sigl-focus-label">ES</p>
                        <p class="sigl-focus-value sigl-focus-value--accent sigl-led sigl-led--tight">{es_value}</p>
                    </div>
                    <div class="sigl-focus-card">
                        <p class="sigl-focus-label">CTX</p>
                        <p class="sigl-focus-value">{context}</p>
                    </div>
                </div>
                <div class="sigl-subpanel">
                    <div class="sigl-subhead">
                        <span class="sigl-subtitle">Recent Sigs</span>
                        <span class="sigl-subcopy">Latest Signal Flow</span>
                    </div>
                    <div class="sigl-signal-tags">{_build_recent_signal_tags(payload.get("focus_recent_signals"))}</div>
                </div>
                <div class="sigl-subpanel">
                    <div class="sigl-subhead">
                        <span class="sigl-subtitle">Stack</span>
                        <span class="sigl-subcopy">{mode} Field Summary</span>
                    </div>
                    <div class="sigl-stack-grid">{_build_stack_rows(payload.get("focus_stack_summary"))}</div>
                </div>
                {summary_html}
            </div>
        </div>
        <div class="sigl-tape">
            <div class="sigl-tape-label">Ticker</div>
            <div class="sigl-tape-window">
                <div class="sigl-tape-track">{_build_marquee(payload.get("marquee_items"))}</div>
            </div>
        </div>
    </div>
</body>
</html>"""
