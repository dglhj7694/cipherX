import html

BRAND_NAME = "Aroven"
BRAND_VERSION = "V14.2"
BRAND_PAGE_TITLE = f"{BRAND_NAME} {BRAND_VERSION}"
BRAND_PAGE_ICON = "🧭"
BRAND_TAGLINE = "Clarity before conviction"
BRAND_REPORT_SLUG = "aroven"

INITIAL_MESSAGE_CONTENT = (
    f"{BRAND_PAGE_ICON} **{BRAND_PAGE_TITLE}**\n"
    "티커를 입력하거나 사이드바의 **스캐너**에서 여러 종목을 먼저 살펴보세요."
)


def _brand_mark_svg():
    return """
    <svg viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <defs>
            <linearGradient id="aroven-ring" x1="18" y1="18" x2="78" y2="78" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stop-color="#E2E8F0" />
                <stop offset="100%" stop-color="#7DD3FC" />
            </linearGradient>
            <linearGradient id="aroven-needle" x1="48" y1="18" x2="48" y2="78" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stop-color="#F6C35E" />
                <stop offset="100%" stop-color="#63D9A2" />
            </linearGradient>
        </defs>
        <circle cx="48" cy="48" r="26" stroke="url(#aroven-ring)" stroke-width="4" opacity="0.92" />
        <circle cx="48" cy="48" r="18" stroke="#22314A" stroke-width="1.5" opacity="0.9" />
        <path d="M48 18L58 47L48 78L38 47L48 18Z" fill="url(#aroven-needle)" />
        <path d="M48 18L62 33" stroke="#F8FAFC" stroke-width="2" stroke-linecap="round" opacity="0.78" />
        <path d="M48 78L34 63" stroke="#0F172A" stroke-width="2" stroke-linecap="round" opacity="0.48" />
        <circle cx="48" cy="48" r="5" fill="#F8FAFC" />
        <circle cx="67" cy="29" r="3" fill="#F6C35E" />
    </svg>
    """


def build_brand_lockup(subtitle=BRAND_TAGLINE, compact=False, kicker=None):
    wrapper_class = "brand-lockup brand-lockup-compact" if compact else "brand-lockup"
    kicker_html = f"<p class='brand-kicker'>{html.escape(kicker)}</p>" if kicker else ""
    subtitle_html = f"<p class='brand-tagline'>{html.escape(subtitle)}</p>" if subtitle else ""
    return f"""
    <div class="{wrapper_class}">
        <div class="brand-mark">{_brand_mark_svg()}</div>
        <div class="brand-copy">
            {kicker_html}
            <div class="brand-name-row">
                <p class="brand-wordmark">Aro<span class="brand-accent">v</span>en</p>
                <span class="brand-version">{BRAND_VERSION}</span>
            </div>
            {subtitle_html}
        </div>
    </div>
    """


def build_brand_hero(mode_label, summary, chips=None):
    chips = chips or []
    chips_html = "".join(
        f"<span class='brand-chip'>{html.escape(chip)}</span>"
        for chip in chips
    )
    return f"""
    <div class="brand-hero fade-up">
        {build_brand_lockup(BRAND_TAGLINE, compact=False, kicker=mode_label)}
        <p class="brand-summary">{html.escape(summary)}</p>
        <div class="brand-chip-row">{chips_html}</div>
    </div>
    """
