import html

from theme import build_brand_theme_css


BRAND_NAME = "SIGL"
BRAND_PAGE_TITLE = BRAND_NAME
BRAND_PAGE_ICON = "📡"
BRAND_REPORT_SLUG = "sigl"

INITIAL_MESSAGE_CONTENT = (
    f"{BRAND_PAGE_ICON} **{BRAND_NAME}**\n"
    "분석할 티커를 입력해 주세요."
)


def _esc(value, fallback="--"):
    text = str(value).strip() if value is not None else ""
    return html.escape(text or fallback)


def build_brand_board(payload, compact=False):
    brand_code = _esc(payload.get("brand_code"), BRAND_NAME)

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <style>{build_brand_theme_css()}</style>
</head>
<body>
  <div class="sigl-brand-shell">
    <div class="sigl-brand-lockup">
      <div class="sigl-brand-logo" aria-hidden="true">
        <svg viewBox="0 0 64 64">
          <defs>
            <linearGradient id="siglGlow" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#A9B7FF"></stop>
              <stop offset="100%" stop-color="#5D7BFF"></stop>
            </linearGradient>
          </defs>
          <rect x="6" y="6" width="52" height="52" rx="16" fill="rgba(255,255,255,0.03)" stroke="rgba(142,164,255,0.26)"></rect>
          <circle cx="24" cy="32" r="4.5" fill="url(#siglGlow)"></circle>
          <path d="M28 32c7-11 15-14 24-14" fill="none" stroke="url(#siglGlow)" stroke-width="3.5" stroke-linecap="round"></path>
          <path d="M28 32c8-4 15-5 24-5" fill="none" stroke="rgba(169,183,255,0.74)" stroke-width="3" stroke-linecap="round"></path>
          <path d="M28 32c7 4 15 9 24 14" fill="none" stroke="rgba(125,211,252,0.74)" stroke-width="3" stroke-linecap="round"></path>
        </svg>
      </div>
      <div class="sigl-brand-mark">
        <p class="sigl-brand-name">{brand_code}</p>
      </div>
    </div>
  </div>
</body>
</html>"""
