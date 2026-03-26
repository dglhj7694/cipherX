import html

from theme import build_brand_theme_css


BRAND_NAME = "SIGL"
BRAND_PAGE_TITLE = BRAND_NAME
BRAND_PAGE_ICON = "assets/sigl_symbol.svg"
BRAND_REPORT_SLUG = "sigl"

INITIAL_MESSAGE_CONTENT = (
    "**$SIGL (Signal)**\n"
    "\ubd84\uc11d\ud560 \ud2f0\ucee4\ub97c \uc785\ub825\ud574 \uc8fc\uc138\uc694."
)


def _esc(value, fallback="--"):
    text = str(value).strip() if value is not None else ""
    return html.escape(text or fallback)


def build_brand_symbol():
    return """
<svg viewBox="0 0 96 96" role="img" aria-hidden="true">
  <defs>
    <linearGradient id="siglRing" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#F1F5F9" stop-opacity="0.95"></stop>
      <stop offset="100%" stop-color="#8EA4FF" stop-opacity="0.58"></stop>
    </linearGradient>
    <linearGradient id="siglRed" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#F04A5D"></stop>
      <stop offset="100%" stop-color="#BA2036"></stop>
    </linearGradient>
    <linearGradient id="siglGreen" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#22C55E"></stop>
      <stop offset="100%" stop-color="#86EFAC"></stop>
    </linearGradient>
    <filter id="siglGlow" x="-40%" y="-40%" width="180%" height="180%">
      <feDropShadow dx="0" dy="0" stdDeviation="2.4" flood-color="#22C55E" flood-opacity="0.28"></feDropShadow>
    </filter>
    <clipPath id="siglClip">
      <circle cx="48" cy="48" r="43"></circle>
    </clipPath>
  </defs>
  <circle cx="48" cy="48" r="43" fill="#0B0F17"></circle>
  <g clip-path="url(#siglClip)">
    <path d="M54 3
             C77 6 92 24 92 48
             C92 71 77 89 52 93
             C61 80 68 65 73 49
             C77 37 83 25 92 15
             C84 8 71 4 54 3Z"
          fill="url(#siglRed)"
          opacity="0.98"></path>
  </g>
  <circle cx="48" cy="48" r="43" fill="none" stroke="url(#siglRing)" stroke-width="2.4"></circle>

  <path d="M18 42
           C20 29 31 18 45 18
           C50 18 55 20 60 23
           L65 17
           L71 22
           L69 31
           C73 34 76 39 77 44
           C71 42 65 43 60 46
           L55 49
           C49 53 41 55 33 55
           H24
           C19 53 16 48 18 42Z"
        fill="#F8FAFC"></path>
  <path d="M51 29l5 2-7 2z"
        fill="#0B0F17"
        opacity="0.95"></path>
  <path d="M46 44l8-2 6-4"
        fill="none"
        stroke="#0B0F17"
        stroke-width="2.6"
        stroke-linecap="round"
        stroke-linejoin="round"
        opacity="0.95"></path>

  <path d="M77 64
           C75 54 67 46 55 46
           C47 46 39 49 33 55
           L26 50
           L19 54
           L22 63
           C18 67 16 72 16 77
           C22 74 29 73 36 75
           L44 79
           C51 83 60 84 69 82
           L78 79
           C83 77 86 73 88 68
           C83 68 79 66 77 64Z"
        fill="#EEF2F7"></path>
  <path d="M25 53l8-5 8 5"
        fill="none"
        stroke="url(#siglGreen)"
        stroke-width="4.4"
        stroke-linecap="round"
        stroke-linejoin="round"></path>
  <path d="M63 52l8-5 8 5"
        fill="none"
        stroke="url(#siglGreen)"
        stroke-width="4.4"
        stroke-linecap="round"
        stroke-linejoin="round"></path>
  <path d="M31 60l11-9 8 4 15-18"
        fill="none"
        stroke="url(#siglGreen)"
        stroke-width="5"
        stroke-linecap="round"
        stroke-linejoin="round"
        filter="url(#siglGlow)"></path>
  <circle cx="31" cy="60" r="3.6" fill="#22C55E"></circle>
</svg>
"""


def build_brand_wordmark(brand_code):
    safe_brand = _esc(brand_code, BRAND_NAME)
    return f"""
<div class="sigl-brand-wordmark" aria-label="${safe_brand} Signal">
  <div class="sigl-brand-name">
    <span class="sigl-brand-prefix">$</span><span class="sigl-brand-word">{safe_brand}</span><span class="sigl-brand-cursor" aria-hidden="true"></span>
  </div>
  <div class="sigl-brand-sub">(Signal)</div>
</div>
"""


def build_brand_board(payload, compact=False):
    del compact
    brand_code = payload.get("brand_code") or BRAND_NAME

    return f"""
<style>{build_brand_theme_css()}</style>
<div class="sigl-html-block sigl-brand-root">
  <div class="sigl-brand-shell">
    <div class="sigl-brand-left">
      <div class="sigl-brand-logo">
        {build_brand_symbol()}
      </div>
    </div>
    <div class="sigl-brand-center">
      {build_brand_wordmark(brand_code)}
    </div>
    <div class="sigl-brand-spacer" aria-hidden="true"></div>
  </div>
</div>"""
