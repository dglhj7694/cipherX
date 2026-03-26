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
linear-gradient(180deg,rgba(4,7,12,.985),rgba(10,13,19,.985)),
radial-gradient(circle at top right,rgba(165,180,252,.08),transparent 34%);
border:1px solid rgba(148,163,184,.16);border-radius:18px;overflow:hidden;position:relative;margin:0;
box-shadow:0 18px 42px rgba(2,6,23,.34)}
.sigl-board:before{content:"";position:absolute;inset:0;background:
linear-gradient(90deg,transparent 0,transparent calc(100% - 1px),rgba(148,163,184,.038) calc(100% - 1px)),
linear-gradient(0deg,transparent 0,transparent calc(100% - 1px),rgba(148,163,184,.038) calc(100% - 1px));
background-size:24px 24px;pointer-events:none;opacity:.55}
.sigl-board--bull{--sigl-accent:#63D9A2;--sigl-accent-soft:rgba(99,217,162,.15);--sigl-accent-strong:rgba(99,217,162,.34)}
.sigl-board--bear{--sigl-accent:#FF8F96;--sigl-accent-soft:rgba(255,143,150,.15);--sigl-accent-strong:rgba(255,143,150,.34)}
.sigl-board--neutral{--sigl-accent:#F6C35E;--sigl-accent-soft:rgba(246,195,94,.15);--sigl-accent-strong:rgba(246,195,94,.32)}
.sigl-board--scanner{--sigl-accent:#7DD3FC;--sigl-accent-soft:rgba(125,211,252,.15);--sigl-accent-strong:rgba(125,211,252,.32)}
.sigl-board-shell{position:relative;display:grid;grid-template-columns:minmax(270px,340px) 1fr;gap:12px;padding:14px}
.sigl-code-panel,.sigl-data-panel{position:relative;z-index:1}
.sigl-code-panel{display:flex;flex-direction:column;gap:12px;justify-content:space-between;
background:linear-gradient(180deg,rgba(8,11,17,.97),rgba(7,10,15,.92));border:1px solid rgba(148,163,184,.14);
border-radius:14px;padding:14px;box-shadow:inset 0 1px 0 rgba(248,250,252,.03)}
.sigl-code-top{display:grid;gap:10px}
.sigl-kicker{margin:0;color:var(--sigl-accent);font-size:.68rem;font-weight:800;letter-spacing:.18em;text-transform:uppercase;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace}
.sigl-terminal-line{display:flex;align-items:center;gap:9px;flex-wrap:wrap;color:#CBD5E1;font-size:.76rem;font-weight:700;
letter-spacing:.08em;text-transform:uppercase;font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace}
.sigl-terminal-sep{color:#475569}
.sigl-pulse{width:8px;height:8px;border-radius:999px;background:var(--sigl-accent);box-shadow:0 0 14px var(--sigl-accent);animation:siglPulse 2.8s ease-in-out infinite}
.sigl-brand-banner{display:inline-flex;align-items:center;gap:10px;align-self:flex-start;padding:12px 14px;border-radius:12px;
background:linear-gradient(180deg,#111722,#090D14);border:1px solid rgba(226,232,240,.10);border-bottom-color:var(--sigl-accent-strong);
color:#F8FAFC;font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace;font-size:1.9rem;font-weight:800;letter-spacing:.18em;
box-shadow:inset 0 1px 0 rgba(248,250,252,.03)}
.sigl-brand-bracket{color:var(--sigl-accent)}
.sigl-board-summary{margin:0;color:#94A3B8;font-size:.79rem;line-height:1.58;max-width:34ch}
.sigl-data-panel{background:linear-gradient(180deg,rgba(8,11,17,.95),rgba(7,10,15,.88));border:1px solid rgba(148,163,184,.14);
border-radius:14px;padding:11px}
.sigl-tile-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}
.sigl-tile{background:linear-gradient(180deg,rgba(13,17,25,.98),rgba(8,11,18,.92));border:1px solid rgba(148,163,184,.12);
border-radius:12px;padding:10px 11px;min-height:72px;display:flex;flex-direction:column;justify-content:center;box-shadow:inset 0 1px 0 rgba(248,250,252,.02)}
.sigl-tile-label{margin:0 0 6px;color:#64748B;font-size:.64rem;font-weight:800;letter-spacing:.16em;text-transform:uppercase;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace}
.sigl-tile-value{margin:0;color:#F8FAFC;font-size:1rem;font-weight:800;line-height:1.18;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sigl-tape{position:relative;z-index:1;border-top:1px solid rgba(148,163,184,.12);background:rgba(6,9,14,.96);overflow:hidden}
.sigl-tape-track{display:flex;gap:24px;width:max-content;padding:9px 0;animation:siglMarquee 30s linear infinite}
.sigl-tape-item{display:inline-flex;align-items:center;gap:9px;color:#CBD5E1;font-size:.76rem;font-weight:700;letter-spacing:.08em;white-space:nowrap;
font-family:'JetBrains Mono','IBM Plex Mono','SFMono-Regular',Consolas,monospace;text-transform:uppercase}
.sigl-tape-dot{width:7px;height:7px;border-radius:999px;background:var(--sigl-accent);box-shadow:0 0 10px var(--sigl-accent)}
.sigl-board--compact .sigl-board-shell{grid-template-columns:1fr;padding:12px;gap:10px}
.sigl-board--compact .sigl-code-panel,.sigl-board--compact .sigl-data-panel{padding:10px}
.sigl-board--compact .sigl-brand-banner{font-size:1.35rem;padding:10px 12px}
.sigl-board--compact .sigl-board-summary{display:none}
.sigl-board--compact .sigl-tile-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.sigl-board--compact .sigl-tile{min-height:60px;padding:9px 10px}
.sigl-board--compact .sigl-tile-value{font-size:.91rem}
.sigl-board--compact .sigl-terminal-line{font-size:.7rem;gap:8px}
.sigl-board--compact .sigl-tape-track{gap:18px;padding:8px 0;animation-duration:24s}
@keyframes siglMarquee{from{transform:translateX(0)}to{transform:translateX(-50%)}}
@keyframes siglPulse{0%,100%{opacity:.42;transform:scale(.92)}50%{opacity:1;transform:scale(1.06)}}
@media (max-width:900px){
  .sigl-board-shell{grid-template-columns:1fr}
  .sigl-tile-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .sigl-brand-banner{font-size:1.55rem}
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
        <div class="sigl-board-shell">
            <div class="sigl-code-panel">
                <div class="sigl-code-top">
                    <p class="sigl-kicker">{mode} DESK</p>
                    <div class="sigl-terminal-line">
                        <span class="sigl-pulse"></span>
                        <span>STATUS: {system_status}</span>
                        <span class="sigl-terminal-sep">|</span>
                        <span>FEED: {feed_status}</span>
                    </div>
                </div>
                <div class="sigl-brand-banner">
                    <span class="sigl-brand-bracket">[</span>
                    <span>{brand_code}</span>
                    <span class="sigl-brand-bracket">]</span>
                </div>
                {summary_html}
            </div>
            <div class="sigl-data-panel">
                <div class="sigl-tile-grid">{_build_metric_tiles(payload)}</div>
            </div>
        </div>
        <div class="sigl-tape">
            <div class="sigl-tape-track">{_build_marquee(payload.get("marquee_items"))}</div>
        </div>
    </div>
</body>
</html>"""
