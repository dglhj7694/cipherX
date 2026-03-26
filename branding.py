import html

from theme import build_brand_theme_css


BRAND_NAME = "SIGL"
BRAND_PAGE_TITLE = BRAND_NAME
BRAND_PAGE_ICON = "📶"
BRAND_REPORT_SLUG = "sigl"

INITIAL_MESSAGE_CONTENT = (
    f"{BRAND_PAGE_ICON} **$SIGL (Signal)**\n"
    "분석할 티커를 입력해 주세요."
)


def _esc(value, fallback="--"):
    text = str(value).strip() if value is not None else ""
    return html.escape(text or fallback)


def build_brand_board(payload, compact=False):
    del compact
    brand_code = _esc(payload.get("brand_code"), BRAND_NAME)

    return f"""
<style>{build_brand_theme_css()}</style>
<div class="sigl-html-block sigl-brand-root">
  <div class="sigl-brand-shell">
    <div class="sigl-brand-lockup">
      <div class="sigl-brand-logo" aria-hidden="true">
        <svg viewBox="0 0 64 64">
          <defs>
            <linearGradient id="siglFrame" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#8EA4FF"></stop>
              <stop offset="100%" stop-color="rgba(93,123,255,0.55)"></stop>
            </linearGradient>
            <linearGradient id="siglGuide" x1="0%" y1="50%" x2="100%" y2="50%">
              <stop offset="0%" stop-color="#A9B7FF"></stop>
              <stop offset="100%" stop-color="#5D7BFF"></stop>
            </linearGradient>
            <linearGradient id="siglBull" x1="0%" y1="100%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#22C55E"></stop>
              <stop offset="100%" stop-color="#86EFAC"></stop>
            </linearGradient>
            <linearGradient id="siglBear" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#FB7185"></stop>
              <stop offset="100%" stop-color="#F87171"></stop>
            </linearGradient>
            <filter id="siglBlueGlow" x="-50%" y="-50%" width="200%" height="200%">
              <feDropShadow dx="0" dy="0" stdDeviation="2.2" flood-color="#5D7BFF" flood-opacity="0.34"></feDropShadow>
            </filter>
          </defs>
          <rect x="6" y="6" width="52" height="52" rx="16" fill="rgba(255,255,255,0.03)" stroke="url(#siglFrame)"></rect>
          <path d="M14 32h36" fill="none" stroke="url(#siglGuide)" stroke-width="2.4" stroke-linecap="round" opacity="0.95"></path>
          <path d="M16 40l10-8 8 3 14-14" fill="none" stroke="url(#siglBull)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" filter="url(#siglBlueGlow)"></path>
          <path d="M16 23l10 6 7-2 15 11" fill="none" stroke="url(#siglBear)" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round" opacity="0.96"></path>
          <circle cx="16" cy="40" r="3.4" fill="#22C55E"></circle>
          <circle cx="16" cy="23" r="3" fill="#FB7185"></circle>
          <path d="M48 21v9l6-6" fill="none" stroke="#86EFAC" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"></path>
        </svg>
      </div>
      <div class="sigl-brand-mark" style="min-width:220px;">
        <p class="sigl-brand-name" style="font-size:62px;line-height:0.92;"><span class="sigl-brand-prefix">$</span><span class="sigl-brand-word">{brand_code}</span></p>
        <p class="sigl-brand-sub" style="font-size:11px;line-height:1.05;">(Signal)</p>
      </div>
    </div>
  </div>
</div>"""
