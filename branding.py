import html

BRAND_NAME = "SIGL"
BRAND_PAGE_TITLE = BRAND_NAME
BRAND_PAGE_ICON = "📶"
BRAND_REPORT_SLUG = "sigl"

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
    return f"""
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
    """
