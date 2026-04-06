import html
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


def _brand_escape(value):
    return html.escape(str(value or ""))


def _brand_strategy_entry_text(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    if number != number:
        return ""
    return f"{number:.2f}"


def _brand_strategy_status_text(value):
    return {
        "ACTIVE": "성립",
        "CONFIRMING": "확인 진행",
        "TRIGGER_WAIT": "트리거 대기",
        "READY": "준비",
        "INTEREST": "관심",
        "WATCH": "준비",
        "WEAK_WATCH": "관심",
        "INVALID": "무효",
    }.get(str(value or "").upper(), "")


def build_brand_board(payload, compact=False):
    payload = payload or {}
    shell_class = "sigl-brand-shell sigl-brand-shell--compact" if compact else "sigl-brand-shell"
    us_market_time = _brand_us_market_time_text()
    focus = _brand_escape(payload.get("focus", "WAIT"))
    judgment = _brand_escape(payload.get("judgment", "IDLE"))
    recent = _brand_escape(payload.get("recent_label", "STANDBY"))
    summary = _brand_escape(payload.get("summary", ""))
    stack = payload.get("focus_stack_summary") or {}
    top_strategy = stack.get("top_strategy") if isinstance(stack.get("top_strategy"), dict) else {}
    strategy_text = ""
    if top_strategy.get("label"):
        entry_price_text = _brand_strategy_entry_text(top_strategy.get("entry_price"))
        status_text = _brand_strategy_status_text(top_strategy.get("status"))
        status_suffix = f" / 상태 {status_text}" if status_text else ""
        entry_suffix = f" / 진입가 {entry_price_text}" if entry_price_text else ""
        strategy_text = (
            f"{_brand_escape(top_strategy.get('label'))} {_brand_escape(top_strategy.get('score'))}"
            f"{_brand_escape(status_suffix)}{_brand_escape(entry_suffix)} / 충돌 {_brand_escape(stack.get('strategy_conflict_level', 'LOW'))}"
        )
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
    <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:{'10px' if compact else '14px'};align-items:center;color:#E2E8F0;font-size:{'.72rem' if compact else '.78rem'}">
      <span style="padding:6px 10px;border-radius:999px;border:1px solid rgba(148,163,184,.22);background:rgba(15,23,42,.55)">FOCUS {focus}</span>
      <span style="padding:6px 10px;border-radius:999px;border:1px solid rgba(148,163,184,.22);background:rgba(15,23,42,.55)">SIGNAL {judgment}</span>
      <span style="padding:6px 10px;border-radius:999px;border:1px solid rgba(148,163,184,.22);background:rgba(15,23,42,.55)">RECENT {recent}</span>
      {f"<span style=\"padding:6px 10px;border-radius:999px;border:1px solid rgba(99,217,162,.28);background:rgba(15,23,42,.55)\">STRATEGY {strategy_text}</span>" if strategy_text else ""}
    </div>
    {f"<div style=\"margin-top:10px;color:#94A3B8;font-size:{'.72rem' if compact else '.76rem'};line-height:1.45\">{summary}</div>" if summary else ""}
  </div>
</div>"""
