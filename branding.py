import html

BRAND_NAME = "SIGL"
BRAND_PAGE_TITLE = BRAND_NAME
BRAND_PAGE_ICON = "📶"
BRAND_REPORT_SLUG = "sigl"

_BOARD_CSS = """
html,body{margin:0;padding:0;background:transparent;font-family:'Pretendard',system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
*{box-sizing:border-box}
.sigl-board{--sigl-accent:#A5B4FC;--sigl-accent-soft:rgba(165,180,252,.16);--sigl-accent-strong:rgba(165,180,252,.34);
background:
linear-gradient(180deg,rgba(3,6,10,.992),rgba(8,11,16,.992)),
radial-gradient(circle at top right,rgba(165,180,252,.08),transparent 35%);
border:1px solid rgba(148,163,184,.16);border-radius:20px;overflow:hidden;position:relative;margin:0;
box-shadow:0 20px 48px rgba(2,6,23,.34)}
.sigl-board:before{content:"";position:absolute;inset:0;background:
linear-gradient(90deg,transparent 0,transparent calc(100% - 1px),rgba(148,163,184,.036) calc(100% - 1px)),
linear-gradient(0deg,transparent 0,transparent calc(100% - 1px),rgba(148,163,184,.036) calc(100% - 1px));
background-size:22px 22px;pointer-events:none;opacity:.55}
.sigl-board:after{content:"";position:absolute;inset:0 auto auto 0;height:1px;width:100%;
background:linear-gradient(90deg,rgba(255,255,255,0),var(--sigl-accent),rgba(255,255,255,0));opacity:.72}
.sigl-board--bull{--sigl-accent:#63D9A2;--sigl-accent-soft:rgba(99,217,162,.15);--sigl-accent-strong:rgba(99,217,162,.34)}
.sigl-board--bear{--sigl-accent:#FF8F96;--sigl-accent-soft:rgba(255,143,150,.15);--sigl-accent-strong:rgba(255,143,150,.34)}
.sigl-board--neutral{--sigl-accent:#F6C35E;--sigl-accent-soft:rgba(246,195,94,.15);--sigl-accent-strong:rgba(246,195,94,.32)}
.sigl-board--scanner{--sigl-accent:#7DD3FC;--sigl-accent-soft:rgba(125,211,252,.15);--sigl-accent-strong:rgba(125,211,252,.32)}
.sigl-topbar{position:relative;z-index:1;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;
padding:10px 15px;border-bottom:1px solid rgba(148,163,184,.12);
background:linear-gradient(180deg,rgba(10,14,21,.96),rgba(6,9,14,.9))}
.sigl-topbar-item{color:#94A3B8;font-size:.67rem;font-weight:800;letter-spacing:.16em;text-transform:uppercase;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace}
.sigl-topbar-item--accent{color:var(--sigl-accent)}
.sigl-board-shell{position:relative;z-index:1;display:grid;grid-template-columns:minmax(320px,390px) 1fr;gap:12px;padding:14px}
.sigl-code-panel,.sigl-data-panel{position:relative}
.sigl-code-panel{display:grid;gap:12px;align-content:start;
background:linear-gradient(180deg,rgba(8,11,17,.98),rgba(6,9,14,.94));border:1px solid rgba(148,163,184,.14);
border-radius:14px;padding:14px;box-shadow:inset 0 1px 0 rgba(248,250,252,.03)}
.sigl-terminal-line{display:flex;align-items:center;gap:9px;flex-wrap:wrap;color:#CBD5E1;font-size:.76rem;font-weight:700;
letter-spacing:.08em;text-transform:uppercase;font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace}
.sigl-terminal-sep{color:#475569}
.sigl-pulse{width:8px;height:8px;border-radius:999px;background:var(--sigl-accent);box-shadow:0 0 14px var(--sigl-accent);animation:siglPulse 2.8s ease-in-out infinite}
.sigl-brand-row{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;flex-wrap:wrap}
.sigl-brand-banner{display:inline-flex;align-items:center;padding:12px 14px;border-radius:12px;
background:linear-gradient(180deg,#111722,#090D14);border:1px solid rgba(226,232,240,.10);border-bottom-color:var(--sigl-accent-strong);
color:#F8FAFC;font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace;font-size:2rem;font-weight:800;letter-spacing:.18em;
box-shadow:inset 0 1px 0 rgba(248,250,252,.03)}
.sigl-brand-qual{color:var(--sigl-accent);font-size:.74rem;font-weight:800;letter-spacing:.18em;text-transform:uppercase;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace}
.sigl-mini-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.sigl-mini-cell{background:linear-gradient(180deg,rgba(13,17,25,.98),rgba(8,11,18,.92));border:1px solid rgba(148,163,184,.10);
border-radius:10px;padding:9px 10px}
.sigl-mini-label{margin:0 0 5px;color:#64748B;font-size:.6rem;font-weight:800;letter-spacing:.16em;text-transform:uppercase;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace}
.sigl-mini-value{margin:0;color:#E2E8F0;font-size:.83rem;font-weight:800;line-height:1.2;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace}
.sigl-ladder{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:7px}
.sigl-ladder-bar{display:block;height:7px;width:calc(var(--w,1) * 100%);border-radius:999px;
background:linear-gradient(90deg,var(--sigl-accent),rgba(255,255,255,.14));box-shadow:0 0 12px rgba(255,255,255,.03)}
.sigl-board-summary{margin:0;color:#94A3B8;font-size:.79rem;line-height:1.58;max-width:34ch}
.sigl-data-panel{background:linear-gradient(180deg,rgba(8,11,17,.96),rgba(6,9,14,.9));border:1px solid rgba(148,163,184,.14);
border-radius:14px;padding:12px}
.sigl-panel-heading{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;
padding:1px 1px 10px;border-bottom:1px solid rgba(148,163,184,.10)}
.sigl-panel-title{color:#E2E8F0;font-size:.72rem;font-weight:800;letter-spacing:.18em;text-transform:uppercase;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace}
.sigl-panel-copy{color:var(--sigl-accent);font-size:.68rem;font-weight:800;letter-spacing:.18em;text-transform:uppercase;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace}
.sigl-tile-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;padding-top:10px}
.sigl-tile{position:relative;background:linear-gradient(180deg,rgba(13,17,25,.98),rgba(8,11,18,.92));
border:1px solid rgba(148,163,184,.12);border-radius:11px;padding:11px 12px;min-height:76px;display:flex;flex-direction:column;justify-content:center;
box-shadow:inset 0 1px 0 rgba(248,250,252,.02)}
.sigl-tile:before{content:"";position:absolute;inset:0 auto auto 0;height:2px;width:100%;
background:linear-gradient(90deg,var(--sigl-accent),rgba(255,255,255,0));opacity:.5}
.sigl-tile-label{margin:0 0 6px;color:#64748B;font-size:.64rem;font-weight:800;letter-spacing:.16em;text-transform:uppercase;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace}
.sigl-tile-value{margin:0;color:#F8FAFC;font-size:1.02rem;font-weight:800;line-height:1.18;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sigl-tape{position:relative;z-index:1;display:grid;grid-template-columns:auto 1fr;align-items:center;
border-top:1px solid rgba(148,163,184,.12);background:rgba(5,8,13,.98)}
.sigl-tape-label{padding:10px 14px;border-right:1px solid rgba(148,163,184,.12);color:var(--sigl-accent);font-size:.68rem;font-weight:800;
letter-spacing:.18em;text-transform:uppercase;font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace;
background:linear-gradient(180deg,rgba(10,14,21,.96),rgba(7,10,15,.92))}
.sigl-tape-window{overflow:hidden}
.sigl-tape-track{display:flex;gap:24px;width:max-content;padding:9px 0;animation:siglMarquee 30s linear infinite}
.sigl-tape-item{display:inline-flex;align-items:center;gap:9px;color:#CBD5E1;font-size:.76rem;font-weight:700;letter-spacing:.08em;white-space:nowrap;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace;text-transform:uppercase}
.sigl-tape-dot{width:7px;height:7px;border-radius:999px;background:var(--sigl-accent);box-shadow:0 0 10px var(--sigl-accent)}
.sigl-board--compact .sigl-topbar{display:none}
.sigl-board--compact .sigl-board-shell{grid-template-columns:1fr;padding:12px;gap:10px}
.sigl-board--compact .sigl-code-panel,.sigl-board--compact .sigl-data-panel{padding:10px}
.sigl-board--compact .sigl-brand-banner{font-size:1.3rem;padding:10px 12px}
.sigl-board--compact .sigl-brand-qual,.sigl-board--compact .sigl-mini-grid,.sigl-board--compact .sigl-ladder,.sigl-board--compact .sigl-board-summary{display:none}
.sigl-board--compact .sigl-tile-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;padding-top:8px}
.sigl-board--compact .sigl-tile{min-height:60px;padding:9px 10px}
.sigl-board--compact .sigl-tile-value{font-size:.9rem}
.sigl-board--compact .sigl-terminal-line{font-size:.7rem;gap:8px}
.sigl-board--compact .sigl-tape{grid-template-columns:1fr}
.sigl-board--compact .sigl-tape-label{display:none}
.sigl-board--compact .sigl-tape-track{gap:18px;padding:8px 0;animation-duration:24s}
@keyframes siglMarquee{from{transform:translateX(0)}to{transform:translateX(-50%)}}
@keyframes siglPulse{0%,100%{opacity:.42;transform:scale(.92)}50%{opacity:1;transform:scale(1.06)}}
@media (max-width:980px){
  .sigl-board-shell{grid-template-columns:1fr}
}
@media (max-width:900px){
  .sigl-topbar{gap:8px;padding:9px 12px}
  .sigl-brand-banner{font-size:1.55rem}
  .sigl-mini-grid,.sigl-tile-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .sigl-tape{grid-template-columns:1fr}
  .sigl-tape-label{display:none}
}
"""

INITIAL_MESSAGE_CONTENT = (
    f"{BRAND_PAGE_ICON} **[ {BRAND_NAME} ]**\n"
    "Select target ticker from the sidebar or type one like `NVDA` to begin."
)

_BOARD_FIELDS = (
    ("MODE", "mode"),
    ("TARGET", "focus"),
    ("ES", "es"),
    ("SIGNAL", "judgment"),
    ("CTX", "context"),
    ("SPAN", "period"),
)


def _esc(value, fallback="--"):
    text = str(value).strip() if value is not None else ""
    return html.escape(text or fallback)


def _build_metric_tiles(payload):
    tiles = []
    for label, key in _BOARD_FIELDS:
        tiles.append(
            f"""
            <div class="sigl-tile">
                <p class="sigl-tile-label">{label}</p>
                <p class="sigl-tile-value">{_esc(payload.get(key))}</p>
            </div>
            """
        )
    return "".join(tiles)


def _build_signal_ladder():
    widths = (0.98, 0.82, 0.66, 0.88, 0.58)
    return "".join(
        f"<span class='sigl-ladder-bar' style='--w:{width}'></span>"
        for width in widths
    )


def _build_marquee(items):
    clean_items = [str(item).strip() for item in (items or []) if str(item).strip()]
    if not clean_items:
        clean_items = [f"[ {BRAND_NAME} ] READY", "TARGET WAIT", "ES --", "SIGNAL IDLE"]
    repeated = clean_items + clean_items
    return "".join(
        f"<span class='sigl-tape-item'><span class='sigl-tape-dot'></span>{html.escape(item)}</span>"
        for item in repeated
    )


def build_brand_board(payload, compact=False):
    board_class = "sigl-board sigl-board--compact" if compact else "sigl-board"
    tone = str(payload.get("status_tone", "neutral")).strip().lower()
    if tone in {"bull", "bear", "neutral", "scanner"}:
        board_class += f" sigl-board--{tone}"

    mode = _esc(payload.get("mode"), "STANDBY")
    summary = _esc(payload.get("summary"), "")
    summary_html = f"<p class='sigl-board-summary'>{summary}</p>" if summary else ""
    brand_code = _esc(payload.get("brand_code"), BRAND_NAME)
    system_status = _esc(payload.get("system_status"), "READY")
    feed_status = _esc(payload.get("feed_status"), "MARKET_SYNC")

    return f"""<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <style>{_BOARD_CSS}</style>
</head>
<body>
    <div class="{board_class}">
        <div class="sigl-topbar">
            <span class="sigl-topbar-item sigl-topbar-item--accent">SIGL SIGNAL TERMINAL</span>
            <span class="sigl-topbar-item">DISCIPLINED MARKET READS</span>
            <span class="sigl-topbar-item">{mode} ROUTE</span>
        </div>
        <div class="sigl-board-shell">
            <div class="sigl-code-panel">
                <div class="sigl-terminal-line">
                    <span class="sigl-pulse"></span>
                    <span>STATUS: {system_status}</span>
                    <span class="sigl-terminal-sep">|</span>
                    <span>FEED: {feed_status}</span>
                </div>
                <div class="sigl-brand-row">
                    <div class="sigl-brand-banner">[ {brand_code} ]</div>
                    <div class="sigl-brand-qual">Signal Terminal</div>
                </div>
                <div class="sigl-mini-grid">
                    <div class="sigl-mini-cell">
                        <p class="sigl-mini-label">Board</p>
                        <p class="sigl-mini-value">SIGNAL_DESK</p>
                    </div>
                    <div class="sigl-mini-cell">
                        <p class="sigl-mini-label">Route</p>
                        <p class="sigl-mini-value">{mode}</p>
                    </div>
                </div>
                <div class="sigl-ladder">{_build_signal_ladder()}</div>
                {summary_html}
            </div>
            <div class="sigl-data-panel">
                <div class="sigl-panel-heading">
                    <span class="sigl-panel-title">Terminal Fields</span>
                    <span class="sigl-panel-copy">{mode} STACK</span>
                </div>
                <div class="sigl-tile-grid">{_build_metric_tiles(payload)}</div>
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
