import base64
from pathlib import Path

from theme import build_brand_theme_css


BRAND_NAME = "SIGL"
BRAND_PAGE_TITLE = BRAND_NAME
BRAND_REPORT_SLUG = "sigl"

_ROOT = Path(__file__).resolve().parent
BRAND_LOGO_ASSET = _ROOT / "assets" / "logo.png"
BRAND_HEADER_ASSET = _ROOT / "assets" / "header.png"
BRAND_PAGE_ICON = str(BRAND_LOGO_ASSET)

INITIAL_MESSAGE_CONTENT = (
    "**$SIGL (Signal)**\n"
    "\ubd84\uc11d\ud560 \ud2f0\ucee4\ub97c \uc785\ub825\ud574 \uc8fc\uc138\uc694."
)


def _image_uri(path: Path):
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def build_brand_symbol():
    return (
        f'<img class="sigl-brand-logo-image" src="{_image_uri(BRAND_LOGO_ASSET)}" '
        f'alt="$SIGL logo" />'
    )


def build_brand_board(payload, compact=False):
    del payload, compact
    return f"""
<style>{build_brand_theme_css()}</style>
<div class="sigl-html-block sigl-brand-root">
  <div class="sigl-brand-shell">
    <img class="sigl-brand-banner" src="{_image_uri(BRAND_HEADER_ASSET)}" alt="$SIGL (Signal) brand header" />
  </div>
</div>"""
