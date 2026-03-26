import html

from theme import build_brand_theme_css


BRAND_NAME = "SIGL"
BRAND_PAGE_TITLE = BRAND_NAME
BRAND_PAGE_ICON = "📟"
BRAND_REPORT_SLUG = "sigl"

INITIAL_MESSAGE_CONTENT = (
    f"{BRAND_PAGE_ICON} **{BRAND_NAME}**\n"
    "분석할 티커를 입력하세요."
)


def _esc(value, fallback="--"):
    text = str(value).strip() if value is not None else ""
    return html.escape(text or fallback)


def _tone_variant(value):
    text = str(value or "").upper()
    if "BUY" in text:
        return "positive"
    if "SELL" in text:
        return "negative"
    if "WATCH" in text or "HOLD" in text or "NEUTRAL" in text:
        return "warning"
    return "accent"


def _chip(label, value, tone="accent"):
    label_html = _esc(label, "")
    value_html = _esc(value)
    return f"<span class='sigl-brand-chip sigl-brand-chip--{tone}'>{label_html} <strong>{value_html}</strong></span>"


def build_brand_board(payload, compact=False):
    brand_code = _esc(payload.get("brand_code"), BRAND_NAME)
    mode = _esc(payload.get("mode"), "ANALYSIS")
    focus = _esc(payload.get("focus"), "WAIT")
    context = _esc(payload.get("context"), "STANDBY")
    summary = _esc(payload.get("summary"), "차분한 다크 SaaS 톤으로 정리된 시그널 분석 화면입니다.")
    system_status = _esc(payload.get("system_status"), "READY")
    judgment = _esc(payload.get("judgment"), "IDLE")
    period = _esc(payload.get("period"), "--")
    recent_label = _esc(payload.get("recent_label"), "STANDBY")
    analysis_count = _esc(payload.get("analysis_count"), "00")

    chips = "".join([
        _chip("Mode", mode, "accent"),
        _chip("Status", system_status, _tone_variant(judgment)),
        _chip("Signal", judgment, _tone_variant(judgment)),
        _chip("Span", period, "warning"),
    ])

    compact_copy = "현재 포커스 종목과 상태를 단순하고 명확하게 보여주는 SIGL 헤더입니다."
    full_copy = "시장 단말기 연출보다 정보 구조와 읽기 흐름에 집중한 SIGL 분석 작업공간입니다."
    copy = compact_copy if compact else full_copy

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <style>{build_brand_theme_css()}</style>
</head>
<body>
  <div class="sigl-brand-shell">
    <div class="sigl-brand-top">
      <div class="sigl-brand-mark">
        <p class="sigl-brand-eyebrow">SIGL Market Intelligence</p>
        <p class="sigl-brand-name">{brand_code}</p>
        <p class="sigl-brand-copy">{copy}</p>
      </div>
      <div class="sigl-brand-chip-row">
        {chips}
      </div>
    </div>
    <div class="sigl-brand-main">
      <div class="sigl-brand-card">
        <p class="sigl-brand-label">Current Focus</p>
        <p class="sigl-brand-focus">{focus}</p>
        <p class="sigl-brand-summary">{summary}</p>
      </div>
      <div class="sigl-brand-grid">
        <div class="sigl-brand-mini">
          <p class="sigl-brand-label">Context</p>
          <p class="sigl-brand-mini-value">{context}</p>
        </div>
        <div class="sigl-brand-mini">
          <p class="sigl-brand-label">Recent Signal</p>
          <p class="sigl-brand-mini-value">{recent_label}</p>
        </div>
        <div class="sigl-brand-mini">
          <p class="sigl-brand-label">System Status</p>
          <p class="sigl-brand-mini-value">{system_status}</p>
        </div>
        <div class="sigl-brand-mini">
          <p class="sigl-brand-label">Analysis Count</p>
          <p class="sigl-brand-mini-value">{analysis_count}</p>
        </div>
      </div>
    </div>
  </div>
</body>
</html>"""
