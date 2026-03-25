import html

BRAND_NAME = "SIGL"
BRAND_PAGE_TITLE = BRAND_NAME
BRAND_PAGE_ICON = "📶"
BRAND_REPORT_SLUG = "sigl"

_BOARD_CSS = """
html,body{margin:0;padding:0;background:transparent;font-family:'Pretendard',system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
*{box-sizing:border-box}
.sigl-board{--sigl-accent:#A5B4FC;--sigl-accent-soft:rgba(165,180,252,.18);--sigl-accent-strong:rgba(165,180,252,.34);
background:
linear-gradient(180deg,rgba(4,7,12,.98),rgba(11,14,20,.98)),
radial-gradient(circle at top right,rgba(165,180,252,.08),transparent 34%);
border:1px solid rgba(148,163,184,.16);border-radius:18px;overflow:hidden;position:relative;margin:0;
box-shadow:0 18px 42px rgba(2,6,23,.34)}
.sigl-board:before{content:"";position:absolute;inset:0;background:
linear-gradient(90deg,transparent 0,transparent calc(100% - 1px),rgba(148,163,184,.04) calc(100% - 1px)),
linear-gradient(0deg,transparent 0,transparent calc(100% - 1px),rgba(148,163,184,.04) calc(100% - 1px));
background-size:28px 28px;pointer-events:none;opacity:.55}
.sigl-board--bull{--sigl-accent:#63D9A2;--sigl-accent-soft:rgba(99,217,162,.18);--sigl-accent-strong:rgba(99,217,162,.34)}
.sigl-board--bear{--sigl-accent:#FF8F96;--sigl-accent-soft:rgba(255,143,150,.16);--sigl-accent-strong:rgba(255,143,150,.34)}
.sigl-board--neutral{--sigl-accent:#F6C35E;--sigl-accent-soft:rgba(246,195,94,.16);--sigl-accent-strong:rgba(246,195,94,.32)}
.sigl-board--scanner{--sigl-accent:#7DD3FC;--sigl-accent-soft:rgba(125,211,252,.16);--sigl-accent-strong:rgba(125,211,252,.32)}
.sigl-board-shell{position:relative;display:grid;grid-template-columns:minmax(240px,300px) 1fr;gap:14px;padding:16px}
.sigl-code-panel,.sigl-data-panel{position:relative;z-index:1}
.sigl-code-panel{display:flex;flex-direction:column;justify-content:space-between;gap:12px;
background:linear-gradient(180deg,rgba(9,12,18,.96),rgba(7,10,15,.9));border:1px solid rgba(148,163,184,.14);
border-radius:14px;padding:14px;box-shadow:inset 0 1px 0 rgba(248,250,252,.04)}
.sigl-kicker{margin:0;color:var(--sigl-accent);font-size:.72rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase}
.sigl-code-row{display:grid;grid-template-columns:repeat(4,minmax(42px,1fr));gap:8px}
.sigl-code-cell{display:grid;place-items:center;min-height:62px;border-radius:12px;
background:linear-gradient(180deg,#151A24,#0B0E14);border:1px solid rgba(226,232,240,.10);border-bottom-color:var(--sigl-accent-strong);
color:#F8FAFC;font-family:'JetBrains Mono','SFMono-Regular',Consolas,monospace;font-size:2rem;font-weight:800;letter-spacing:.08em;
box-shadow:inset 0 1px 0 rgba(248,250,252,.03)}
.sigl-code-cell--accent{color:var(--sigl-accent);text-shadow:0 0 16px rgba(255,255,255,.04)}
.sigl-board-summary{margin:0;color:#94A3B8;font-size:.82rem;line-height:1.55;max-width:30ch}
.sigl-data-panel{background:linear-gradient(180deg,rgba(9,12,18,.94),rgba(7,10,15,.86));border:1px solid rgba(148,163,184,.14);
border-radius:14px;padding:12px}
.sigl-tile-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.sigl-tile{background:linear-gradient(180deg,rgba(15,19,28,.96),rgba(10,13,20,.88));border:1px solid rgba(148,163,184,.12);
border-radius:12px;padding:10px 12px;min-height:74px;display:flex;flex-direction:column;justify-content:center}
.sigl-tile-label{margin:0 0 6px;color:#64748B;font-size:.66rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase}
.sigl-tile-value{margin:0;color:#F8FAFC;font-size:1.08rem;font-weight:800;line-height:1.2;
font-family:'JetBrains Mono','SFMono-Regular',Consolas,monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sigl-tape{position:relative;z-index:1;border-top:1px solid rgba(148,163,184,.12);background:rgba(7,10,15,.92);overflow:hidden}
.sigl-tape-track{display:flex;gap:26px;width:max-content;padding:10px 0;animation:siglMarquee 30s linear infinite}
.sigl-tape-item{display:inline-flex;align-items:center;gap:10px;color:#CBD5E1;font-size:.78rem;font-weight:700;letter-spacing:.04em;white-space:nowrap}
.sigl-tape-dot{width:7px;height:7px;border-radius:999px;background:var(--sigl-accent);box-shadow:0 0 10px var(--sigl-accent)}
.sigl-board--compact .sigl-board-shell{grid-template-columns:1fr;padding:12px;gap:10px}
.sigl-board--compact .sigl-code-panel,.sigl-board--compact .sigl-data-panel{padding:10px}
.sigl-board--compact .sigl-code-cell{min-height:48px;font-size:1.35rem}
.sigl-board--compact .sigl-board-summary{display:none}
.sigl-board--compact .sigl-tile-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.sigl-board--compact .sigl-tile{min-height:62px;padding:9px 10px}
.sigl-board--compact .sigl-tile-value{font-size:.92rem}
.sigl-board--compact .sigl-tape-track{gap:18px;padding:8px 0;animation-duration:24s}
@keyframes siglMarquee{from{transform:translateX(0)}to{transform:translateX(-50%)}}
@media (max-width:900px){
  .sigl-board-shell{grid-template-columns:1fr}
  .sigl-tile-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .sigl-code-cell{min-height:54px;font-size:1.55rem}
}
"""

INITIAL_MESSAGE_CONTENT = (
    f"{BRAND_PAGE_ICON} **{BRAND_NAME}**\n"
    "티커를 입력하거나 사이드바의 **스캐너**에서 여러 종목을 먼저 살펴보세요."
)

_BOARD_FIELDS = (
    ("MODE", "mode"),
    ("FOCUS", "focus"),
    ("ES", "es"),
    ("JUDG", "judgment"),
    ("CTX", "context"),
    ("PERIOD", "period"),
)


def _esc(value, fallback="--"):
    text = str(value).strip() if value is not None else ""
    return html.escape(text or fallback)


def _build_code_cells(brand_code):
    letters = list((brand_code or BRAND_NAME).upper())[:4]
    if len(letters) < 4:
        letters.extend([""] * (4 - len(letters)))
    cells = []
    for idx, letter in enumerate(letters):
        accent = " sigl-code-cell--accent" if idx in (0, len(letters) - 1) else ""
        cells.append(f"<span class='sigl-code-cell{accent}'>{_esc(letter, '&nbsp;')}</span>")
    return "".join(cells)


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
        clean_items = [BRAND_NAME, "SIGNAL DESK", "READY"]
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
                <p class="sigl-kicker">{mode} DESK</p>
                <div class="sigl-code-row">{_build_code_cells(payload.get("brand_code"))}</div>
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
