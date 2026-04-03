from datetime import datetime
from zoneinfo import ZoneInfo

from theme import build_brand_theme_css


BRAND_NAME = "SIGN"
BRAND_PAGE_TITLE = BRAND_NAME
BRAND_REPORT_SLUG = "sign"
BRAND_PAGE_ICON = None

INITIAL_MESSAGE_CONTENT = (
    "\ubd84\uc11d\ud560 \ud2f0\ucee4\ub97c \uc785\ub825\ud574 \uc8fc\uc138\uc694."
)


def _brand_us_market_time_text():
    try:
        now_et = datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        return ""
    return now_et.strftime("%Y-%m-%d %H:%M ET")


def build_brand_board(payload, compact=False):
    del payload
    shell_class = "sigl-brand-shell sigl-brand-shell--compact" if compact else "sigl-brand-shell"
    us_market_time = _brand_us_market_time_text()
    return f"""
<style>{build_brand_theme_css()}</style>
<div class="sigl-html-block sigl-brand-root">
  <div class="{shell_class}">
    <div class="sigl-brand-bar">
      <div class="sigl-brand-clock" aria-label="US market time">
        <span class="sigl-brand-clock__label">US MARKET TIME</span>
        <span class="sigl-brand-clock__value">{us_market_time}</span>
      </div>
      <div class="sigl-brand-lockup">
        <div class="sigl-brand-wordmark" aria-label="$SIGN (Signal)">
          <div class="sigl-brand-title">
            <span class="sigl-brand-title__jackpot" aria-hidden="true">
              <span class="sigl-brand-title__jackpot-mark">$</span>
              <span class="sigl-brand-title__jackpot-letters">
                <span>S</span><span>I</span><span>G</span><span>N</span>
              </span>
            </span>
            <span class="sigl-brand-title__mark">$</span>
            <span class="sigl-brand-title__letters" aria-hidden="true">
              <span class="sigl-brand-letter sigl-brand-letter--red sigl-brand-letter--s" data-char="S">S</span>
              <span class="sigl-brand-letter sigl-brand-letter--green sigl-brand-letter--i" data-char="I">I</span>
              <span class="sigl-brand-letter sigl-brand-letter--red sigl-brand-letter--g" data-char="G">G</span>
              <span class="sigl-brand-letter sigl-brand-letter--green sigl-brand-letter--n" data-char="N">N</span>
            </span>
          </div>
          <div class="sigl-brand-subtitle">(Signal)</div>
        </div>
      </div>
    </div>
  </div>
</div>"""
