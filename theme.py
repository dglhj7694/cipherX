FONT_IMPORT_URL = "https://hangeul.pstatic.net/hangeul_static/css/nanum-square-round.css"
FONT_STACK = "'NanumSquareRound','Malgun Gothic','Apple SD Gothic Neo',sans-serif"
PLOTLY_FONT_FAMILY = "NanumSquareRound, Malgun Gothic, Apple SD Gothic Neo, sans-serif"


def _css_vars(scope=":root"):
    return f"""
{scope}{{
  --sigl-bg-app:#0B1020;
  --sigl-bg-soft:#0F172A;
  --sigl-bg-elevated:#162033;
  --sigl-surface-1:#131C2D;
  --sigl-surface-2:#182235;
  --sigl-surface-3:#1D2840;
  --sigl-border-soft:rgba(148,163,184,.16);
  --sigl-border-strong:rgba(148,163,184,.26);
  --sigl-text-strong:#F8FAFC;
  --sigl-text:#E2E8F0;
  --sigl-text-muted:#94A3B8;
  --sigl-accent:#8EA4FF;
  --sigl-success:#63D9A2;
  --sigl-danger:#FF8F96;
  --sigl-warning:#F6C35E;
  --sigl-info:#7DD3FC;
  --sigl-radius-sm:12px;
  --sigl-radius-md:16px;
  --sigl-radius-lg:20px;
  --sigl-shadow-sm:0 12px 28px rgba(2,6,23,.18);
  --sigl-shadow-md:0 20px 44px rgba(2,6,23,.24);
  --sigl-space-1:8px;
  --sigl-space-2:12px;
  --sigl-space-3:16px;
  --sigl-space-4:20px;
  --sigl-space-5:24px;
}}
"""


def build_app_theme_css():
    return f"""<style>
@import url('{FONT_IMPORT_URL}');
{_css_vars()}
html,body,[class*="css"]{{
  font-family:{FONT_STACK}!important;
  color:var(--sigl-text)!important;
}}
html,body{{
  overflow-x:hidden!important;
}}
*,*::before,*::after{{
  box-sizing:border-box;
}}
body{{
  background:var(--sigl-bg-app);
}}
.stApp{{
  background:
    radial-gradient(circle at top left, rgba(142,164,255,.10), transparent 28%),
    linear-gradient(180deg, #0B1020 0%, #0E1425 100%);
  overflow-x:hidden!important;
}}
div[data-testid="stAppViewContainer"],
div[data-testid="stAppViewContainer"] > .main,
section[data-testid="stMain"],
section.main,
main,
section.main > div,
section[data-testid="stMain"] > div,
div[data-testid="stMainBlockContainer"]{{
  background:linear-gradient(180deg, #0B1020 0%, #0E1425 100%)!important;
  min-width:0!important;
  overflow-x:hidden!important;
}}
div[data-testid="stVerticalBlock"],
div[data-testid="stHorizontalBlock"],
div[data-testid="column"],
.element-container{{
  min-width:0!important;
}}
p,li,span,div{{
  color:inherit;
}}
h1,h2,h3,h4,h5,h6{{
  color:var(--sigl-text-strong)!important;
  font-weight:800!important;
  letter-spacing:-.02em;
}}
.block-container{{
  max-width:1440px;
  padding-top:1rem!important;
  padding-bottom:1rem!important;
}}
header{{
  background:transparent!important;
}}
section[data-testid="stSidebar"]{{
  --sigl-sidebar-control-h:46px;
  --sigl-sidebar-control-radius:15px;
  --sigl-sidebar-gap:12px;
  background:
    linear-gradient(180deg, rgba(142,164,255,.05), rgba(142,164,255,0) 24%),
    linear-gradient(180deg, #0D1424 0%, #0B1120 100%)!important;
  border-right:1px solid var(--sigl-border-soft)!important;
}}
section[data-testid="stSidebar"] > div{{
  background:transparent!important;
}}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"]{{
  padding-top:.35rem!important;
}}
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]{{
  padding:0 .45rem 1rem!important;
}}
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]{{
  gap:var(--sigl-sidebar-gap)!important;
}}
section[data-testid="stSidebar"] div[data-testid="stElementContainer"]{{
  margin:0!important;
}}
section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]{{
  gap:8px!important;
  align-items:stretch!important;
}}
section[data-testid="stSidebar"] hr{{
  margin:4px 0 6px!important;
  border-color:rgba(148,163,184,.12)!important;
}}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] label p{{
  color:var(--sigl-text)!important;
}}
section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"]{{
  margin-bottom:8px!important;
}}
section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] p{{
  color:var(--sigl-text-muted)!important;
  font-size:.72rem!important;
  font-weight:800!important;
  letter-spacing:.08em!important;
  text-transform:uppercase!important;
}}
section[data-testid="stSidebar"] p[data-testid="stCaption"]{{
  color:var(--sigl-text-muted)!important;
  font-size:.74rem!important;
  line-height:1.45!important;
}}
.sigl-sidebar-control-label{{
  color:var(--sigl-text-muted);
  font-size:.72rem;
  font-weight:800;
  letter-spacing:.08em;
  text-transform:uppercase;
  margin:0 0 8px;
}}
.sigl-sidebar-choice-anchor{{
  width:0;
  height:0;
  overflow:hidden;
}}
.sigl-sidebar-control-spacer{{
  min-height:var(--sigl-sidebar-control-h);
}}
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.sigl-sidebar-choice-anchor){{
  gap:8px!important;
  padding:6px!important;
  border:1px solid rgba(148,163,184,.12)!important;
  border-radius:16px!important;
  background:linear-gradient(180deg, rgba(19,28,45,.72), rgba(15,23,42,.56))!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.03)!important;
}}
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.sigl-sidebar-choice-anchor) > div[data-testid="stHorizontalBlock"]{{
  gap:8px!important;
}}
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.sigl-sidebar-choice-anchor) div.stButton{{
  height:100%!important;
}}
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.sigl-sidebar-choice-anchor) div.stButton>button{{
  position:relative!important;
  min-height:var(--sigl-sidebar-control-h)!important;
  border-radius:calc(var(--sigl-sidebar-control-radius) - 1px)!important;
  border:1px solid rgba(148,163,184,.12)!important;
  background:linear-gradient(180deg, rgba(255,255,255,.035), rgba(255,255,255,.015))!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.03)!important;
  overflow:hidden!important;
  justify-content:center!important;
  transition:
    transform .18s ease,
    border-color .18s ease,
    background .18s ease,
    box-shadow .18s ease!important;
}}
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.sigl-sidebar-choice-anchor) div.stButton>button::before{{
  content:"";
  position:absolute;
  inset:auto auto 9px 10px;
  width:8px;
  height:8px;
  border-radius:999px;
  background:rgba(148,163,184,.42);
  opacity:.92;
  transition:
    transform .18s ease,
    background .18s ease,
    box-shadow .18s ease,
    opacity .18s ease!important;
}}
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.sigl-sidebar-choice-anchor) div.stButton>button::after{{
  content:"";
  position:absolute;
  inset:0;
  border-radius:inherit;
  background:radial-gradient(circle at center, rgba(142,164,255,.18), rgba(142,164,255,0) 62%);
  opacity:0;
  transform:scale(.76);
  pointer-events:none;
  transition:opacity .2s ease, transform .2s ease!important;
}}
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.sigl-sidebar-choice-anchor) div.stButton>button span,
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.sigl-sidebar-choice-anchor) div.stButton>button p,
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.sigl-sidebar-choice-anchor) div.stButton>button div{{
  color:var(--sigl-text)!important;
  font-size:.84rem!important;
  font-weight:800!important;
}}
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.sigl-sidebar-choice-anchor) div.stButton>button:hover{{
  transform:translateY(-1px)!important;
  border-color:rgba(142,164,255,.22)!important;
  background:linear-gradient(180deg, rgba(142,164,255,.10), rgba(142,164,255,.04))!important;
  box-shadow:0 10px 20px rgba(2,6,23,.16)!important;
}}
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.sigl-sidebar-choice-anchor) div.stButton>button[kind="primary"]{{
  transform:translateY(-1px)!important;
  border-color:rgba(142,164,255,.34)!important;
  background:linear-gradient(180deg, rgba(142,164,255,.18), rgba(93,123,255,.08))!important;
  box-shadow:
    0 10px 22px rgba(93,123,255,.18)!important,
    inset 0 0 0 1px rgba(142,164,255,.14)!important;
}}
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.sigl-sidebar-choice-anchor) div.stButton>button[kind="primary"]::before{{
  background:var(--sigl-success)!important;
  box-shadow:
    0 0 0 4px rgba(99,217,162,.12),
    0 0 14px rgba(99,217,162,.26)!important;
  transform:scale(1.12)!important;
}}
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.sigl-sidebar-choice-anchor) div.stButton>button[kind="primary"]::after{{
  opacity:1!important;
  transform:scale(1)!important;
}}
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.sigl-sidebar-choice-anchor) div.stButton>button[kind="primary"] span,
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.sigl-sidebar-choice-anchor) div.stButton>button[kind="primary"] p,
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.sigl-sidebar-choice-anchor) div.stButton>button[kind="primary"] div{{
  color:var(--sigl-text-strong)!important;
}}
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.sigl-sidebar-choice-anchor) div.stButton>button:active{{
  transform:scale(.985)!important;
}}
div[data-baseweb="select"]>div,
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
textarea{{
  background:rgba(15,23,42,.76)!important;
  border:1px solid var(--sigl-border-soft)!important;
  color:var(--sigl-text-strong)!important;
  border-radius:14px!important;
  transition:
    border-color .18s ease,
    box-shadow .18s ease,
    background .18s ease,
    transform .18s ease!important;
}}
div[data-baseweb="select"]{{
  position:relative;
}}
div[data-baseweb="select"]>div{{
  position:relative;
  isolation:isolate;
  overflow:hidden;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.04),
    0 8px 18px rgba(2,6,23,.08)!important;
}}
div[data-baseweb="select"]>div::before{{
  content:"";
  position:absolute;
  inset:auto auto 11px 12px;
  width:8px;
  height:8px;
  border-radius:999px;
  background:rgba(148,163,184,.42);
  box-shadow:none;
  opacity:.92;
  pointer-events:none;
  transition:
    transform .18s ease,
    background .18s ease,
    box-shadow .18s ease,
    opacity .18s ease!important;
}}
div[data-baseweb="select"]>div::after{{
  content:"";
  position:absolute;
  inset:0;
  pointer-events:none;
  border-radius:inherit;
  background:
    linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,0) 42%),
    radial-gradient(circle at center, rgba(142,164,255,.16), rgba(142,164,255,0) 62%);
  opacity:0;
  transform:scale(.78);
  transition:opacity .2s ease, transform .2s ease!important;
}}
div[data-baseweb="select"]>div:hover,
div[data-testid="stTextInput"] input:hover,
div[data-testid="stNumberInput"] input:hover,
textarea:hover{{
  background:rgba(15,23,42,.84)!important;
  border-color:rgba(148,163,184,.22)!important;
}}
div[data-baseweb="select"]>div:hover{{
  transform:translateY(-1px)!important;
  box-shadow:
    0 12px 22px rgba(2,6,23,.16),
    inset 0 1px 0 rgba(255,255,255,.05)!important;
}}
div[data-baseweb="select"]>div:hover::after{{
  opacity:1;
  transform:scale(1);
}}
div[data-baseweb="select"]>div:focus-within,
div[data-testid="stTextInput"] input:focus,
div[data-testid="stTextInput"] input:focus-visible,
div[data-testid="stNumberInput"] input:focus,
div[data-testid="stNumberInput"] input:focus-visible,
textarea:focus,
textarea:focus-visible{{
  background:rgba(15,23,42,.88)!important;
  border-color:rgba(142,164,255,.34)!important;
  box-shadow:
    0 0 0 3px rgba(142,164,255,.10),
    0 10px 20px rgba(2,6,23,.12)!important;
  outline:none!important;
}}
div[data-baseweb="select"]>div:focus-within,
div[data-baseweb="select"]>div[aria-expanded="true"],
div[data-baseweb="select"] [aria-expanded="true"]{{
  transform:translateY(1px)!important;
  background:
    linear-gradient(180deg, rgba(99,217,162,.12), rgba(99,217,162,.03)),
    rgba(15,23,42,.90)!important;
  border-color:rgba(99,217,162,.30)!important;
  box-shadow:
    0 0 0 3px rgba(99,217,162,.10),
    0 14px 24px rgba(2,6,23,.16),
    inset 0 1px 0 rgba(255,255,255,.05)!important;
}}
div[data-baseweb="select"]>div:focus-within::before,
div[data-baseweb="select"]>div[aria-expanded="true"]::before,
div[data-baseweb="select"] [aria-expanded="true"]::before{{
  background:var(--sigl-success)!important;
  box-shadow:
    0 0 0 4px rgba(99,217,162,.12),
    0 0 14px rgba(99,217,162,.26)!important;
  transform:scale(1.12)!important;
}}
div[data-baseweb="select"]>div:focus-within::after,
div[data-baseweb="select"]>div[aria-expanded="true"]::after,
div[data-baseweb="select"] [aria-expanded="true"]::after{{
  opacity:1;
  transform:scale(1)!important;
}}
div[data-baseweb="select"] span,
div[data-baseweb="select"] input,
div[data-baseweb="select"] div{{
  color:var(--sigl-text)!important;
}}
div[data-baseweb="select"] svg{{
  transition:transform .18s ease, color .18s ease!important;
}}
div[data-baseweb="select"]>div[aria-expanded="true"] svg,
div[data-baseweb="select"] [aria-expanded="true"] svg{{
  transform:rotate(180deg);
  color:#B8F1D5!important;
}}
div[data-baseweb="select"] input::placeholder{{
  color:var(--sigl-text-muted)!important;
  opacity:1!important;
}}
section[data-testid="stSidebar"] div[data-baseweb="select"]>div,
section[data-testid="stSidebar"] div[data-testid="stTextInput"] input,
section[data-testid="stSidebar"] div[data-testid="stNumberInput"] input,
section[data-testid="stSidebar"] textarea{{
  min-height:var(--sigl-sidebar-control-h)!important;
  border-radius:var(--sigl-sidebar-control-radius)!important;
}}
section[data-testid="stSidebar"] div[data-baseweb="select"]>div{{
  padding-left:14px!important;
  padding-right:10px!important;
}}
section[data-testid="stSidebar"] div[data-baseweb="select"] span,
section[data-testid="stSidebar"] div[data-baseweb="select"] input,
section[data-testid="stSidebar"] div[data-baseweb="select"] div,
section[data-testid="stSidebar"] div[data-testid="stTextInput"] input,
section[data-testid="stSidebar"] div[data-testid="stNumberInput"] input,
section[data-testid="stSidebar"] textarea{{
  font-size:.84rem!important;
  font-weight:700!important;
}}
section[data-testid="stSidebar"] div[data-testid="stTextInput"] input,
section[data-testid="stSidebar"] div[data-testid="stNumberInput"] input,
section[data-testid="stSidebar"] textarea{{
  padding-left:14px!important;
  padding-right:14px!important;
}}
section[data-testid="stSidebar"] div[data-testid="stTextInput"] input::placeholder,
section[data-testid="stSidebar"] div[data-testid="stNumberInput"] input::placeholder,
section[data-testid="stSidebar"] textarea::placeholder{{
  color:var(--sigl-text-muted)!important;
  opacity:1!important;
}}
section[data-testid="stSidebar"] div[data-testid="stMultiSelect"] [data-baseweb="tag"]{{
  min-height:28px!important;
  padding:0 10px!important;
}}
div[data-baseweb="popover"]{{
  z-index:999!important;
}}
div[data-baseweb="popover"] > div,
div[data-baseweb="popover"] [data-baseweb="menu"]{{
  background:
    linear-gradient(180deg, rgba(142,164,255,.06), rgba(142,164,255,0) 26%),
    linear-gradient(180deg, rgba(19,28,45,.98), rgba(15,23,42,.94))!important;
  border:1px solid rgba(148,163,184,.14)!important;
  border-radius:16px!important;
  box-shadow:
    0 22px 44px rgba(2,6,23,.28),
    inset 0 1px 0 rgba(255,255,255,.04)!important;
  backdrop-filter:blur(14px);
  overflow:auto!important;
}}
div[data-baseweb="popover"] ul,
div[data-baseweb="popover"] ol{{
  margin:0!important;
  padding:0!important;
  background:transparent!important;
}}
div[data-baseweb="popover"] [role="listbox"]{{
  padding:6px 0!important;
  border-radius:16px!important;
  border:none!important;
  background:transparent!important;
  box-shadow:none!important;
}}
div[data-baseweb="popover"] [role="option"]{{
  margin:0!important;
  padding:10px 14px!important;
  min-height:auto!important;
  border-radius:0!important;
  border:none!important;
  background:transparent!important;
  color:var(--sigl-text)!important;
  line-height:1.35!important;
  white-space:nowrap!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
  transition:
    background .16s ease,
    color .16s ease!important;
}}
div[data-baseweb="popover"] [role="option"] > div,
div[data-baseweb="popover"] [role="option"] span,
div[data-baseweb="popover"] [role="option"] p{{
  min-width:0!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
  white-space:nowrap!important;
  line-height:1.25!important;
}}
div[data-baseweb="popover"] [role="option"]:hover{{
  background:linear-gradient(180deg, rgba(142,164,255,.10), rgba(142,164,255,.04))!important;
}}
div[data-baseweb="popover"] [role="option"][aria-selected="true"]{{
  background:linear-gradient(180deg, rgba(99,217,162,.16), rgba(99,217,162,.06))!important;
  color:var(--sigl-text-strong)!important;
}}
div[data-testid="stMultiSelect"] [data-baseweb="tag"]{{
  background:rgba(142,164,255,.12)!important;
  border:1px solid rgba(142,164,255,.22)!important;
  border-radius:999px!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.04)!important;
  transition:
    transform .18s ease,
    border-color .18s ease,
    background .18s ease,
    box-shadow .18s ease!important;
}}
div[data-testid="stMultiSelect"] [data-baseweb="tag"]:hover{{
  transform:translateY(-1px);
  background:rgba(142,164,255,.18)!important;
  border-color:rgba(166,183,255,.34)!important;
  box-shadow:
    0 10px 18px rgba(2,6,23,.12),
    inset 0 1px 0 rgba(255,255,255,.05)!important;
}}
div[data-testid="stMultiSelect"] [data-baseweb="tag"] span,
div[data-testid="stMultiSelect"] [data-baseweb="tag"] div{{
  color:#D6DFFF!important;
  font-weight:700!important;
}}
div[data-testid="stRadio"] label p,
div[data-testid="stMarkdownContainer"] p,
div[data-testid="stMarkdownContainer"] li{{
  color:var(--sigl-text)!important;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"]{{
  margin:0!important;
  width:100%!important;
  max-width:none!important;
  min-width:0!important;
}}
section[data-testid="stSidebar"] div.row-widget.stRadio{{
  width:100%!important;
  max-width:none!important;
  min-width:0!important;
}}
section[data-testid="stSidebar"] div.row-widget.stRadio > div,
section[data-testid="stSidebar"] div.row-widget.stRadio > div > div,
section[data-testid="stSidebar"] div[data-testid="stRadio"] > div,
section[data-testid="stSidebar"] div[data-testid="stRadio"] > div > div{{
  width:100%!important;
  max-width:none!important;
  min-width:0!important;
}}
section[data-testid="stSidebar"] div.row-widget.stRadio > div{{
  display:block!important;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] > label{{
  display:block!important;
  margin:0 0 8px!important;
  width:100%!important;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] > label p{{
  color:var(--sigl-text-muted)!important;
  font-size:.72rem!important;
  font-weight:800!important;
  letter-spacing:.08em!important;
  text-transform:uppercase!important;
}}
section[data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"],
section[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"]{{
  display:grid!important;
  grid-template-columns:repeat(2, minmax(0, 1fr))!important;
  gap:8px!important;
  padding:6px!important;
  width:100%!important;
  max-width:none!important;
  min-width:0!important;
  box-sizing:border-box!important;
  border:1px solid rgba(148,163,184,.12)!important;
  border-radius:16px!important;
  background:linear-gradient(180deg, rgba(19,28,45,.72), rgba(15,23,42,.56))!important;
}}
section[data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] > label[data-baseweb="radio"],
section[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]{{
  position:relative!important;
  display:flex!important;
  align-items:stretch!important;
  justify-content:center!important;
  min-height:var(--sigl-sidebar-control-h)!important;
  margin:0!important;
  border-radius:calc(var(--sigl-sidebar-control-radius) - 1px)!important;
  border:1px solid rgba(148,163,184,.12)!important;
  background:linear-gradient(180deg, rgba(255,255,255,.035), rgba(255,255,255,.015))!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.03)!important;
  overflow:hidden!important;
  cursor:pointer!important;
  width:100%!important;
  transition:transform .18s ease, border-color .18s ease, background .18s ease, box-shadow .18s ease!important;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]:hover{{
  transform:translateY(-1px)!important;
  border-color:rgba(142,164,255,.22)!important;
  background:linear-gradient(180deg, rgba(142,164,255,.10), rgba(142,164,255,.04))!important;
  box-shadow:0 10px 20px rgba(2,6,23,.16)!important;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]::before{{
  content:"";
  position:absolute;
  inset:auto auto 9px 10px;
  width:8px;
  height:8px;
  border-radius:999px;
  background:rgba(148,163,184,.42);
  box-shadow:none;
  transition:transform .2s ease, background .2s ease, box-shadow .2s ease, opacity .2s ease!important;
  opacity:.9;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]::after{{
  content:"";
  position:absolute;
  inset:0;
  border-radius:inherit;
  background:radial-gradient(circle at center, rgba(142,164,255,.18), rgba(142,164,255,0) 62%);
  opacity:0;
  transform:scale(.74);
  pointer-events:none;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"] > div:first-child{{
  position:absolute!important;
  inset:0!important;
  opacity:0!important;
  width:100%!important;
  height:100%!important;
  margin:0!important;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"] > div:last-child{{
  display:flex!important;
  align-items:center!important;
  justify-content:center!important;
  width:100%!important;
  min-height:var(--sigl-sidebar-control-h)!important;
  padding:10px 14px 10px 24px!important;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"] > div:last-child p{{
  width:100%!important;
  margin:0!important;
  color:var(--sigl-text)!important;
  font-size:.84rem!important;
  font-weight:800!important;
  text-align:center!important;
  letter-spacing:-.01em!important;
  transition:color .18s ease!important;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked){{
  transform:translateY(-1px)!important;
  border-color:rgba(142,164,255,.34)!important;
  background:linear-gradient(180deg, rgba(142,164,255,.18), rgba(93,123,255,.08))!important;
  box-shadow:
    0 10px 22px rgba(93,123,255,.18)!important,
    inset 0 0 0 1px rgba(142,164,255,.14)!important;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked)::before{{
  background:var(--sigl-success)!important;
  box-shadow:
    0 0 0 4px rgba(99,217,162,.12),
    0 0 14px rgba(99,217,162,.26)!important;
  transform:scale(1.12)!important;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked)::after{{
  opacity:1!important;
  transform:scale(1)!important;
  animation:sigl-radio-pulse .42s ease-out 1!important;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked) > div:last-child p{{
  color:var(--sigl-text-strong)!important;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]:active{{
  transform:scale(.985)!important;
}}
/* Streamlit versions can render sidebar radios without stable stRadio wrappers. */
section[data-testid="stSidebar"] [role="radiogroup"]{{
  display:grid!important;
  grid-template-columns:repeat(2, minmax(0, 1fr))!important;
  gap:8px!important;
  width:100%!important;
  max-width:none!important;
  min-width:0!important;
  box-sizing:border-box!important;
  align-items:stretch!important;
  justify-items:stretch!important;
}}
section[data-testid="stSidebar"] [role="radiogroup"] > label,
section[data-testid="stSidebar"] [role="radiogroup"] > label[data-baseweb="radio"]{{
  width:100%!important;
  max-width:none!important;
  min-width:0!important;
  justify-self:stretch!important;
}}
section[data-testid="stSidebar"] [role="radiogroup"] > label > div:last-child,
section[data-testid="stSidebar"] [role="radiogroup"] > label[data-baseweb="radio"] > div:last-child{{
  width:100%!important;
}}
div[data-testid="stTabs"] [role="tab"]{{
  position:relative!important;
  overflow:hidden!important;
  flex:0 0 auto!important;
  scroll-snap-align:start!important;
  color:var(--sigl-text-muted)!important;
  font-weight:800!important;
  letter-spacing:-.01em!important;
  border:1px solid rgba(148,163,184,.08)!important;
  border-radius:14px!important;
  background:linear-gradient(180deg, rgba(255,255,255,.02), rgba(255,255,255,0))!important;
  min-height:46px!important;
  padding:.7rem 1.05rem!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.03)!important;
  transition:
    transform .18s ease,
    background .18s ease,
    border-color .18s ease,
    color .18s ease,
    box-shadow .18s ease!important;
}}
div[data-testid="stTabs"] [role="tab"]::before{{
  content:"";
  position:absolute;
  inset:0;
  border-radius:inherit;
  pointer-events:none;
  background:linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,0) 42%);
  opacity:.55;
}}
div[data-testid="stTabs"] [role="tab"]::after{{
  content:"";
  position:absolute;
  left:14px;
  right:14px;
  bottom:7px;
  height:2px;
  border-radius:999px;
  background:linear-gradient(90deg, rgba(124,147,255,0), rgba(124,147,255,.92), rgba(124,147,255,0));
  opacity:0;
  transform:scaleX(.62);
  transition:opacity .18s ease, transform .18s ease;
}}
div[data-testid="stTabs"] [role="tab"]:hover{{
  color:var(--sigl-text)!important;
  transform:translateY(-1px);
  border-color:rgba(148,163,184,.18)!important;
  background:linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.01))!important;
  box-shadow:
    0 10px 18px rgba(2,6,23,.12),
    inset 0 1px 0 rgba(255,255,255,.04)!important;
}}
div[data-testid="stTabs"] [role="tab"]:focus-visible{{
  outline:none!important;
  border-color:rgba(142,164,255,.30)!important;
  box-shadow:
    0 0 0 3px rgba(142,164,255,.10),
    inset 0 1px 0 rgba(255,255,255,.04)!important;
}}
div[data-testid="stTabs"] [role="tab"][aria-selected="true"]{{
  color:var(--sigl-text-strong)!important;
  transform:translateY(-1px);
  background:
    linear-gradient(180deg, rgba(255,255,255,.08), rgba(255,255,255,0) 36%),
    linear-gradient(180deg, rgba(142,164,255,.18), rgba(93,123,255,.10))!important;
  border-color:rgba(142,164,255,.30)!important;
  box-shadow:
    0 12px 24px rgba(93,123,255,.16),
    inset 0 1px 0 rgba(255,255,255,.06)!important;
}}
div[data-testid="stTabs"] [role="tab"][aria-selected="true"]::after{{
  opacity:1;
  transform:scaleX(1);
}}
div[data-testid="stTabs"] [role="tablist"]{{
  position:relative!important;
  isolation:isolate;
  flex-wrap:nowrap!important;
  gap:8px!important;
  padding:8px!important;
  border:1px solid rgba(148,163,184,.14)!important;
  border-radius:18px!important;
  background:
    linear-gradient(180deg, rgba(255,255,255,.03), rgba(255,255,255,0) 26%),
    linear-gradient(180deg, rgba(19,28,45,.96), rgba(15,23,42,.88))!important;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.03),
    0 10px 22px rgba(2,6,23,.12)!important;
  margin-bottom:14px!important;
  overflow-x:auto!important;
  overflow-y:hidden!important;
  scrollbar-width:none;
  scroll-snap-type:x proximity;
}}
div[data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar{{
  display:none;
}}
div[data-testid="stTabs"] [role="tabpanel"]{{
  position:relative;
  min-width:0!important;
  padding-top:10px!important;
  animation:sigl-tab-panel-in .24s ease;
}}
div.stButton>button,
div[data-testid="stFormSubmitButton"] button{{
  position:relative!important;
  overflow:hidden!important;
  border-radius:16px!important;
  font-weight:800!important;
  letter-spacing:-.01em!important;
  min-height:46px!important;
  border:1px solid rgba(148,163,184,.22)!important;
  background:
    linear-gradient(180deg, rgba(255,255,255,.035), rgba(255,255,255,0) 28%),
    linear-gradient(180deg, rgba(29,40,64,.96), rgba(22,32,51,.92))!important;
  color:var(--sigl-text-strong)!important;
  box-shadow:
    0 10px 22px rgba(2,6,23,.16),
    inset 0 1px 0 rgba(255,255,255,.04)!important;
  transition:
    transform .18s ease,
    box-shadow .18s ease,
    border-color .18s ease,
    background .18s ease!important;
}}
div.stButton>button::before,
div[data-testid="stFormSubmitButton"] button::before{{
  content:"";
  position:absolute;
  inset:0;
  border-radius:inherit;
  pointer-events:none;
  background:linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,0) 42%);
  opacity:.65;
}}
div.stButton>button:hover,
div[data-testid="stFormSubmitButton"] button:hover{{
  transform:translateY(-1px);
  border-color:rgba(142,164,255,.26)!important;
  box-shadow:
    0 14px 28px rgba(2,6,23,.22),
    inset 0 1px 0 rgba(255,255,255,.06)!important;
}}
div.stButton>button:active,
div[data-testid="stFormSubmitButton"] button:active{{
  transform:translateY(0) scale(.988)!important;
  box-shadow:
    0 8px 16px rgba(2,6,23,.16),
    inset 0 1px 0 rgba(255,255,255,.04)!important;
}}
div.stButton>button[kind="primary"],
div[data-testid="stFormSubmitButton"] button[kind="primary"]{{
  background:
    linear-gradient(180deg, rgba(255,255,255,.08), rgba(255,255,255,0) 34%),
    linear-gradient(135deg, #7C93FF, #5D7BFF)!important;
  color:white!important;
  border:1px solid rgba(142,164,255,.26)!important;
  box-shadow:
    0 14px 28px rgba(93,123,255,.20),
    inset 0 1px 0 rgba(255,255,255,.08)!important;
}}
div.stButton>button[kind="primary"]:hover,
div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover{{
  border-color:rgba(166,183,255,.40)!important;
  box-shadow:
    0 18px 34px rgba(93,123,255,.24),
    inset 0 1px 0 rgba(255,255,255,.10)!important;
}}
div.stButton>button[kind="secondary"],
div[data-testid="stFormSubmitButton"] button[kind="secondary"],
div.stButton>button:not([kind="primary"]),
div[data-testid="stFormSubmitButton"] button:not([kind="primary"]){{
  background:
    linear-gradient(180deg, rgba(255,255,255,.03), rgba(255,255,255,0) 24%),
    linear-gradient(180deg, rgba(19,28,45,.96), rgba(15,23,42,.90))!important;
  color:var(--sigl-text-strong)!important;
  border:1px solid rgba(148,163,184,.20)!important;
}}
section[data-testid="stSidebar"] div.stButton,
section[data-testid="stSidebar"] div[data-testid="stFormSubmitButton"],
section[data-testid="stSidebar"] div[data-testid="stDownloadButton"]{{
  width:100%!important;
}}
section[data-testid="stSidebar"] div.stButton>button,
section[data-testid="stSidebar"] div[data-testid="stFormSubmitButton"] button,
section[data-testid="stSidebar"] div[data-testid="stDownloadButton"] button{{
  min-height:var(--sigl-sidebar-control-h)!important;
  border-radius:var(--sigl-sidebar-control-radius)!important;
  padding:.78rem .95rem!important;
  justify-content:center!important;
}}
section[data-testid="stSidebar"] div.stButton>button span,
section[data-testid="stSidebar"] div.stButton>button p,
section[data-testid="stSidebar"] div.stButton>button div,
section[data-testid="stSidebar"] div[data-testid="stFormSubmitButton"] button span,
section[data-testid="stSidebar"] div[data-testid="stFormSubmitButton"] button p,
section[data-testid="stSidebar"] div[data-testid="stFormSubmitButton"] button div,
section[data-testid="stSidebar"] div[data-testid="stDownloadButton"] button span,
section[data-testid="stSidebar"] div[data-testid="stDownloadButton"] button p,
section[data-testid="stSidebar"] div[data-testid="stDownloadButton"] button div{{
  font-size:.83rem!important;
  font-weight:800!important;
  letter-spacing:-.01em!important;
  line-height:1.2!important;
}}
section[data-testid="stSidebar"] div.stButton>button:disabled,
section[data-testid="stSidebar"] div[data-testid="stFormSubmitButton"] button:disabled,
section[data-testid="stSidebar"] div[data-testid="stDownloadButton"] button:disabled{{
  opacity:.58!important;
  transform:none!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.02)!important;
}}
div[data-testid="stExpander"]{{
  background:linear-gradient(180deg, rgba(19,28,45,.96), rgba(15,23,42,.90))!important;
  border:1px solid var(--sigl-border-soft)!important;
  border-radius:16px!important;
  overflow:hidden!important;
}}
div[data-testid="stExpander"] details,
div[data-testid="stExpander"] summary,
div[data-testid="stExpander"] summary > div,
div[data-testid="stExpander"] summary > div > div{{
  background:transparent!important;
}}
div[data-testid="stExpander"] div[data-testid="stExpanderDetails"]{{
  background:linear-gradient(180deg, rgba(19,28,45,.92), rgba(15,23,42,.84))!important;
  border-top:1px solid var(--sigl-border-soft)!important;
}}
div[data-testid="stToastContainer"]{{
  top:4.75rem!important;
}}
div[data-testid="stToast"]{{
  background:linear-gradient(180deg, rgba(19,28,45,.98), rgba(15,23,42,.94))!important;
  border:1px solid rgba(142,164,255,.24)!important;
  border-radius:16px!important;
  box-shadow:var(--sigl-shadow-md)!important;
}}
div[data-testid="stChatMessage"]{{
  background:linear-gradient(180deg, rgba(19,28,45,.96), rgba(15,23,42,.90));
  border:1px solid var(--sigl-border-soft);
  border-radius:18px;
  padding:16px 18px;
  box-shadow:var(--sigl-shadow-sm);
}}
div[data-testid="stForm"]{{
  margin:16px 0 18px!important;
  padding:18px!important;
  border:1px solid var(--sigl-border-soft)!important;
  border-radius:18px!important;
  background:linear-gradient(180deg, rgba(19,28,45,.98), rgba(15,23,42,.94))!important;
  box-shadow:var(--sigl-shadow-sm)!important;
}}
div[data-testid="stForm"] > div{{
  border:none!important;
  background:transparent!important;
}}
div[data-testid="stForm"] [data-baseweb="base-input"],
div[data-testid="stForm"] [data-baseweb="input"]{{
  background:transparent!important;
  border:none!important;
  box-shadow:none!important;
}}
div[data-testid="stForm"] div[data-testid="stTextInput"] input{{
  min-height:54px!important;
  padding-left:14px!important;
  border-radius:16px!important;
  background:rgba(11,16,32,.74)!important;
  color:var(--sigl-text-strong)!important;
  transition:
    border-color .18s ease,
    box-shadow .18s ease,
    background .18s ease!important;
}}
div[data-testid="stForm"] div[data-testid="stTextInput"] input::placeholder{{
  color:#7F91AF!important;
  opacity:1!important;
}}
div[data-testid="stForm"] div[data-testid="stTextInput"] input:hover{{
  background:rgba(11,16,32,.82)!important;
  border-color:rgba(148,163,184,.22)!important;
}}
div[data-testid="stForm"] div[data-testid="stTextInput"] input:focus,
div[data-testid="stForm"] div[data-testid="stTextInput"] input:focus-visible{{
  background:rgba(11,16,32,.88)!important;
  border-color:rgba(142,164,255,.36)!important;
  box-shadow:
    0 0 0 3px rgba(142,164,255,.10),
    0 12px 22px rgba(2,6,23,.14)!important;
}}
div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] button{{
  min-height:54px!important;
}}
div[data-testid="stForm"] div[data-testid="stHorizontalBlock"]{{
  align-items:end!important;
}}
div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div{{
  min-width:0!important;
}}
div[data-testid="stBottom"],
div[data-testid="stBottom"] > div,
div.stChatFloatingInputContainer,
div.stChatFloatingInputContainer > div,
div[data-testid="stBottomBlockContainer"]{{
  background:transparent!important;
  box-shadow:none!important;
  padding-top:6px!important;
  padding-bottom:4px!important;
}}
div[data-testid="stBottomBlockContainer"] > div{{
  background:transparent!important;
}}
div[data-testid="stChatInput"]{{
  margin:0 auto 10px!important;
  max-width:980px;
  padding:0!important;
  border:none!important;
  border-radius:0!important;
  background:transparent!important;
  box-shadow:none!important;
}}
div[data-testid="stChatInput"] > div{{
  background:transparent!important;
  border:none!important;
}}
div[data-testid="stChatInput"] > div > div,
div[data-testid="stChatInput"] > div > div > div{{
  background:transparent!important;
  border:none!important;
  box-shadow:none!important;
}}
div[data-testid="stChatInput"] form,
div[data-testid="stChatInput"] [data-baseweb="textarea"],
div[data-testid="stChatInput"] [data-baseweb="base-input"]{{
  background:transparent!important;
  border:none!important;
  box-shadow:none!important;
}}
div[data-testid="stChatInput"] [data-baseweb="textarea"] > div,
div[data-testid="stChatInput"] [data-baseweb="base-input"] > div{{
  background:transparent!important;
  border:none!important;
  box-shadow:none!important;
}}
div[data-testid="stChatInput"] textarea{{
  background:rgba(15,23,42,.92)!important;
  border:1px solid rgba(148,163,184,.14)!important;
  border-radius:16px!important;
  color:var(--sigl-text-strong)!important;
  box-shadow:none!important;
  padding:1rem 3.2rem 1rem 1rem!important;
  min-height:58px!important;
  transition:
    border-color .18s ease,
    box-shadow .18s ease,
    background .18s ease!important;
}}
div[data-testid="stChatInput"] textarea::placeholder{{
  color:var(--sigl-text-muted)!important;
  opacity:1!important;
}}
div[data-testid="stChatInput"] textarea:hover{{
  background:rgba(15,23,42,.96)!important;
  border-color:rgba(148,163,184,.22)!important;
}}
div[data-testid="stChatInput"] textarea:focus,
div[data-testid="stChatInput"] textarea:focus-visible{{
  background:rgba(15,23,42,.98)!important;
  border-color:rgba(142,164,255,.36)!important;
  box-shadow:
    0 0 0 3px rgba(142,164,255,.10),
    0 14px 26px rgba(2,6,23,.14)!important;
}}
div[data-testid="stChatInput"] button{{
  background:linear-gradient(135deg, #7C93FF, #5D7BFF)!important;
  border:none!important;
  border-radius:14px!important;
  color:white!important;
  box-shadow:0 10px 20px rgba(93,123,255,.22)!important;
}}
div[data-testid="stChatInput"] button:hover{{
  transform:translateY(-1px);
}}
div[data-testid="stChatInput"] button svg{{
  fill:white!important;
}}
div[data-testid="stMetricValue"]{{
  color:var(--sigl-text-strong)!important;
}}
@keyframes sigl-radio-pulse{{
  0%{{opacity:.18;transform:scale(.74)}}
  55%{{opacity:.9;transform:scale(1.02)}}
  100%{{opacity:1;transform:scale(1)}}
}}
@keyframes sigl-tab-panel-in{{
  0%{{opacity:.65;transform:translateY(3px)}}
  100%{{opacity:1;transform:translateY(0)}}
}}
::-webkit-scrollbar{{width:8px;height:8px}}
::-webkit-scrollbar-track{{background:#0B1020}}
::-webkit-scrollbar-thumb{{background:#22304A;border-radius:999px}}

.sigl-page-head{{
  display:flex;
  justify-content:space-between;
  align-items:flex-end;
  gap:16px;
  flex-wrap:wrap;
  margin:0 0 14px;
}}
.sigl-page-head__eyebrow{{
  margin:0 0 6px;
  color:var(--sigl-accent);
  font-size:.75rem;
  font-weight:800;
  letter-spacing:.08em;
  text-transform:uppercase;
}}
.sigl-page-head__title{{
  margin:0;
  color:var(--sigl-text-strong);
  font-size:1.28rem;
  font-weight:900;
  line-height:1.25;
  overflow-wrap:anywhere;
}}
.sigl-page-head__copy{{
  margin:6px 0 0;
  color:var(--sigl-text-muted);
  font-size:.88rem;
}}
.sigl-page-banner{{
  margin:0 0 18px;
  padding:20px 22px;
}}
.sigl-page-banner__grid{{
  display:flex;
  justify-content:space-between;
  align-items:flex-start;
  gap:18px;
  flex-wrap:wrap;
}}
.sigl-page-banner__grid > div:first-child{{
  flex:1 1 320px;
  min-width:0;
}}
.sigl-page-banner__copy{{
  margin:10px 0 0;
  color:var(--sigl-text-muted);
  font-size:.92rem;
  line-height:1.7;
  max-width:760px;
}}
.sigl-page-banner__meta{{
  display:flex;
  gap:8px;
  flex-wrap:wrap;
  align-items:center;
  justify-content:flex-end;
  min-width:0;
}}
.sigl-html-block{{
  width:100%;
  max-width:100%;
  min-width:0;
}}
.sigl-section-shell{{
  margin:18px 0 12px;
}}
.sigl-section-shell--tight{{
  margin-top:12px;
}}
.sigl-empty-card{{
  margin:14px 0 18px;
  padding:20px 22px;
}}
.sigl-empty-card__title{{
  margin:0;
  color:var(--sigl-text-strong);
  font-size:1.08rem;
  font-weight:900;
}}
.sigl-empty-card__copy{{
  margin:8px 0 0;
  color:var(--sigl-text-muted);
  font-size:.9rem;
  line-height:1.7;
}}
.sigl-quick-grid{{
  display:grid;
  grid-template-columns:repeat(auto-fit, minmax(120px, 1fr));
  gap:12px;
}}
.sigl-flow-note{{
  margin:8px 0 0;
  color:var(--sigl-text-muted);
  font-size:.82rem;
  line-height:1.6;
}}
.sigl-card{{
  background:linear-gradient(180deg, rgba(19,28,45,.98), rgba(15,23,42,.92));
  border:1px solid var(--sigl-border-soft);
  border-radius:var(--sigl-radius-md);
  padding:16px 18px;
  box-shadow:var(--sigl-shadow-sm);
  min-width:0;
}}
.sigl-card--accent{{
  background:
    linear-gradient(180deg, rgba(142,164,255,.10), rgba(142,164,255,0) 34%),
    linear-gradient(180deg, rgba(19,28,45,.98), rgba(15,23,42,.92));
  border-color:rgba(142,164,255,.24);
}}
.sigl-card--positive{{
  background:
    linear-gradient(180deg, rgba(99,217,162,.10), rgba(99,217,162,0) 34%),
    linear-gradient(180deg, rgba(19,28,45,.98), rgba(15,23,42,.92));
  border-color:rgba(99,217,162,.24);
}}
.sigl-card--negative{{
  background:
    linear-gradient(180deg, rgba(255,143,150,.10), rgba(255,143,150,0) 34%),
    linear-gradient(180deg, rgba(19,28,45,.98), rgba(15,23,42,.92));
  border-color:rgba(255,143,150,.24);
}}
.sigl-card--warning{{
  background:
    linear-gradient(180deg, rgba(246,195,94,.10), rgba(246,195,94,0) 34%),
    linear-gradient(180deg, rgba(19,28,45,.98), rgba(15,23,42,.92));
  border-color:rgba(246,195,94,.24);
}}
.sigl-section-head{{
  display:flex;
  justify-content:space-between;
  align-items:flex-end;
  gap:12px;
  flex-wrap:wrap;
  margin:0 0 12px;
}}
.sigl-section-head > div:first-child{{
  flex:1 1 260px;
  min-width:0;
}}
.sigl-section-title{{
  margin:0;
  color:var(--sigl-text-strong);
  font-size:1.02rem;
  font-weight:800;
}}
.sigl-section-copy{{
  margin:0;
  color:var(--sigl-text-muted);
  font-size:.8rem;
}}
.sigl-grid{{
  display:grid;
  gap:12px;
  align-items:start;
}}
.sigl-grid--2{{grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr))}}
.sigl-grid--3{{grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr))}}
.sigl-grid--4{{grid-template-columns:repeat(auto-fit,minmax(min(100%,160px),1fr))}}
.sigl-grid--5{{grid-template-columns:repeat(auto-fit,minmax(min(100%,160px),1fr))}}
.sigl-grid > *{{
  min-width:0;
}}
.sigl-inline{{
  display:flex;
  gap:8px;
  flex-wrap:wrap;
  align-items:center;
  min-width:0;
}}
.sigl-stack-gap{{
  height:6px;
}}
.sigl-stack-gap--lg{{
  height:12px;
}}
.sigl-composer-head{{
  display:flex;
  justify-content:space-between;
  align-items:flex-start;
  gap:14px;
  flex-wrap:wrap;
  margin:0 0 14px;
}}
.sigl-composer-title{{
  margin:0;
  color:var(--sigl-text-strong);
  font-size:1.02rem;
  font-weight:900;
}}
.sigl-composer-copy{{
  margin:5px 0 0;
  color:var(--sigl-text-muted);
  font-size:.82rem;
  line-height:1.6;
}}
.sigl-composer-tools{{
  display:flex;
  gap:8px;
  flex-wrap:wrap;
  align-items:center;
}}
.sigl-composer-tool{{
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding:6px 11px;
  border-radius:999px;
  border:1px solid rgba(148,163,184,.16);
  background:rgba(255,255,255,.04);
  color:var(--sigl-text);
  font-size:.74rem;
  font-weight:800;
}}
.sigl-composer-meta{{
  display:flex;
  gap:8px;
  flex-wrap:wrap;
  align-items:center;
  margin-top:12px;
}}
.sigl-composer-meta--scanner{{
  gap:6px;
  margin:2px 0 10px;
}}
.sigl-composer-meta--scanner .sigl-badge{{
  padding:5px 10px;
  font-size:.72rem;
  font-weight:750;
}}
.sigl-composer-note{{
  margin-top:12px;
  color:var(--sigl-text-muted);
  font-size:.8rem;
  line-height:1.6;
}}
.sigl-badge{{
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding:6px 11px;
  border-radius:999px;
  font-size:.74rem;
  font-weight:800;
  line-height:1;
  border:1px solid rgba(148,163,184,.16);
  background:rgba(148,163,184,.10);
  color:var(--sigl-text);
}}
.sigl-badge--accent{{background:rgba(142,164,255,.14);border-color:rgba(142,164,255,.26);color:#D6DFFF}}
.sigl-badge--positive{{background:rgba(99,217,162,.14);border-color:rgba(99,217,162,.28);color:#C9F8E0}}
.sigl-badge--negative{{background:rgba(255,143,150,.14);border-color:rgba(255,143,150,.28);color:#FFD6DB}}
.sigl-badge--warning{{background:rgba(246,195,94,.14);border-color:rgba(246,195,94,.28);color:#FBE7B1}}
.sigl-badge--muted{{background:rgba(148,163,184,.10);border-color:rgba(148,163,184,.18);color:var(--sigl-text-muted)}}
.sigl-chip-row{{
  display:flex;
  gap:8px;
  flex-wrap:wrap;
  margin-top:12px;
  align-items:flex-start;
}}
.sigl-chip{{
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding:7px 11px;
  border-radius:999px;
  font-size:.76rem;
  font-weight:700;
  border:1px solid rgba(148,163,184,.14);
  background:rgba(255,255,255,.03);
  color:var(--sigl-text);
}}
.sigl-note{{
  margin-top:12px;
  padding:13px 14px;
  border-radius:14px;
  border:1px solid rgba(142,164,255,.18);
  background:rgba(142,164,255,.08);
  color:var(--sigl-text);
  line-height:1.6;
}}
.sigl-summary{{
  color:var(--sigl-text-muted);
  font-size:.86rem;
  line-height:1.65;
}}
.sigl-price-header{{
  display:grid;
  gap:14px;
}}
.sigl-price-top{{
  display:flex;
  justify-content:space-between;
  gap:16px;
  flex-wrap:wrap;
}}
.sigl-price-top > div:first-child{{
  flex:1 1 320px;
  min-width:0;
}}
.sigl-price-meta{{
  margin:0;
  color:var(--sigl-text-muted);
  font-size:.8rem;
}}
.sigl-price-value{{
  margin:8px 0 0;
  color:var(--sigl-text-strong);
  font-size:2.15rem;
  font-weight:900;
  letter-spacing:-.03em;
  overflow-wrap:anywhere;
}}
.sigl-price-change--up{{color:var(--sigl-success)!important}}
.sigl-price-change--down{{color:var(--sigl-danger)!important}}
.sigl-price-change--flat{{color:var(--sigl-warning)!important}}
.sigl-focus-stack{{
  display:grid;
  gap:10px;
  min-width:0;
}}
.sigl-metric-card{{
  background:rgba(255,255,255,.03);
  border:1px solid rgba(148,163,184,.14);
  border-radius:14px;
  padding:14px 15px;
  min-height:112px;
  min-width:0;
  width:100%;
  max-width:100%;
}}
.sigl-metric-card--summary{{
  min-height:104px;
}}
.sigl-metric-card--positive{{
  border-color:rgba(99,217,162,.24);
  background:
    linear-gradient(180deg, rgba(99,217,162,.10), rgba(99,217,162,0) 34%),
    rgba(255,255,255,.03);
}}
.sigl-metric-card--negative{{
  border-color:rgba(255,143,150,.24);
  background:
    linear-gradient(180deg, rgba(255,143,150,.10), rgba(255,143,150,0) 34%),
    rgba(255,255,255,.03);
}}
.sigl-metric-card--accent{{
  border-color:rgba(142,164,255,.24);
  background:
    linear-gradient(180deg, rgba(142,164,255,.10), rgba(142,164,255,0) 34%),
    rgba(255,255,255,.03);
}}
.sigl-metric-label{{
  margin:0 0 6px;
  color:var(--sigl-text-muted);
  font-size:.74rem;
  font-weight:800;
}}
.sigl-metric-value{{
  margin:0;
  color:var(--sigl-text-strong);
  font-size:1.42rem;
  font-weight:900;
  line-height:1.15;
}}
.sigl-metric-sub{{
  margin:6px 0 0;
  color:var(--sigl-text);
  font-size:.8rem;
  line-height:1.55;
}}
.sigl-progress{{
  margin-top:10px;
  height:7px;
  border-radius:999px;
  overflow:hidden;
  background:rgba(148,163,184,.14);
}}
.sigl-progress__fill{{
  height:100%;
  width:var(--fill,0%);
  background:var(--tone,var(--sigl-accent));
  border-radius:999px;
}}
.sigl-committee-card{{
  background:rgba(255,255,255,.03);
  border:1px solid rgba(148,163,184,.14);
  border-left:3px solid var(--tone,var(--sigl-accent));
  border-radius:14px;
  padding:13px 14px;
  min-width:0;
  width:100%;
  max-width:100%;
}}
.sigl-committee-name{{
  margin:0 0 4px;
  color:var(--sigl-text-muted);
  font-size:.72rem;
  font-weight:800;
}}
.sigl-committee-score{{
  margin:0;
  color:var(--tone,var(--sigl-accent));
  font-size:1.2rem;
  font-weight:900;
}}
.sigl-committee-foot{{
  margin:8px 0 0;
  color:var(--sigl-text-muted);
  font-size:.72rem;
}}
.sigl-bar-split{{
  position:relative;
  height:14px;
  border-radius:999px;
  overflow:hidden;
  background:rgba(148,163,184,.14);
}}
.sigl-bar-split__buy,
.sigl-bar-split__sell{{
  position:absolute;
  top:0;
  bottom:0;
}}
.sigl-bar-split__buy{{right:50%;width:var(--buy,0%);background:linear-gradient(90deg,#237650,var(--sigl-success))}}
.sigl-bar-split__sell{{left:50%;width:var(--sell,0%);background:linear-gradient(90deg,var(--sigl-danger),#8A4B54)}}
.sigl-bar-split__center{{position:absolute;left:50%;top:0;bottom:0;width:1px;background:rgba(226,232,240,.55)}}
.sigl-layer-board{{
  display:grid;
  gap:10px;
}}
.sigl-layer-row{{
  display:grid;
  grid-template-columns:62px 1fr 62px;
  gap:10px;
  align-items:center;
}}
.sigl-layer-score--buy{{text-align:right;color:var(--sigl-success);font-weight:800}}
.sigl-layer-score--sell{{text-align:left;color:var(--sigl-danger);font-weight:800}}
.sigl-layer-track{{
  position:relative;
  height:30px;
  border-radius:12px;
  overflow:hidden;
  border:1px solid rgba(148,163,184,.16);
  background:linear-gradient(90deg,rgba(99,217,162,.08),rgba(148,163,184,.04),rgba(255,143,150,.08));
  min-width:0;
}}
.sigl-layer-fill--buy,
.sigl-layer-fill--sell{{
  position:absolute;
  top:4px;
  bottom:4px;
}}
.sigl-layer-fill--buy{{left:var(--buy-left,50%);width:var(--buy-width,0%);background:linear-gradient(90deg,#237650,var(--sigl-success));border-radius:8px 0 0 8px}}
.sigl-layer-fill--sell{{left:50%;width:var(--sell-width,0%);background:linear-gradient(90deg,var(--sigl-danger),#8A4B54);border-radius:0 8px 8px 0}}
.sigl-layer-center{{position:absolute;left:50%;top:0;bottom:0;width:1px;background:rgba(226,232,240,.52)}}
.sigl-layer-label{{
  position:absolute;
  left:50%;
  top:50%;
  transform:translate(-50%,-50%);
  padding:3px 9px;
  border-radius:999px;
  background:rgba(11,16,32,.86);
  border:1px solid rgba(148,163,184,.18);
  color:var(--sigl-text);
  font-size:.72rem;
  font-weight:800;
  max-width:calc(100% - 14px);
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
}}
.sigl-result-summary{{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(min(100%,180px),1fr));
  gap:12px;
  margin-bottom:14px;
}}
.sigl-result-card{{
  background:linear-gradient(180deg, rgba(19,28,45,.98), rgba(15,23,42,.92));
  border:1px solid var(--sigl-border-soft);
  border-radius:16px;
  padding:16px 18px;
  box-shadow:var(--sigl-shadow-sm);
  margin:8px 0;
  width:100%;
  max-width:100%;
}}
.sigl-result-head{{
  display:flex;
  justify-content:space-between;
  align-items:flex-start;
  gap:12px;
  flex-wrap:wrap;
}}
.sigl-result-head > div:first-child{{
  flex:1 1 260px;
  min-width:0;
}}
.sigl-result-title{{
  margin:0;
  color:var(--sigl-text-strong);
  font-size:1.12rem;
  font-weight:900;
}}
.sigl-result-copy{{
  margin:5px 0 0;
  color:var(--sigl-text-muted);
  font-size:.8rem;
}}
.sigl-result-tags{{
  display:flex;
  gap:8px;
  flex-wrap:wrap;
  justify-content:flex-end;
  min-width:0;
  align-items:flex-start;
}}
.sigl-code-list{{
  display:flex;
  gap:8px;
  flex-wrap:wrap;
  max-height:120px;
  overflow:auto;
  align-items:flex-start;
  max-width:100%;
}}
.sigl-code-chip{{
  display:inline-flex;
  align-items:center;
  padding:6px 10px;
  border-radius:999px;
  border:1px solid rgba(148,163,184,.14);
  background:rgba(255,255,255,.03);
  color:var(--sigl-text);
  font-size:.76rem;
  font-weight:800;
  max-width:100%;
  overflow-wrap:anywhere;
  word-break:break-word;
}}
.sigl-empty{{
  color:var(--sigl-text-muted);
  font-size:.82rem;
}}
.sigl-scanner-scope{{
  position:relative;
  overflow:hidden;
  isolation:isolate;
  background:
    radial-gradient(110% 88% at 50% 0%, rgba(142,164,255,.12), rgba(142,164,255,0) 52%),
    linear-gradient(180deg, rgba(142,164,255,.08), rgba(142,164,255,0) 34%),
    linear-gradient(180deg, rgba(19,28,45,.98), rgba(15,23,42,.92));
  border-color:rgba(142,164,255,.24);
  box-shadow:
    0 20px 44px rgba(4,8,18,.22),
    inset 0 1px 0 rgba(255,255,255,.04);
}}
.sigl-scanner-scope::before{{
  content:"";
  position:absolute;
  inset:0;
  pointer-events:none;
  background:
    linear-gradient(110deg, rgba(255,255,255,.08), rgba(255,255,255,0) 26%),
    radial-gradient(62% 34% at 50% -6%, rgba(188,200,255,.12), rgba(188,200,255,0) 72%);
  opacity:.78;
}}
.sigl-scanner-scope > *{{
  position:relative;
  z-index:1;
}}
.sigl-scanner-scope__meta{{
  margin-left:auto;
  justify-content:flex-end;
}}
.sigl-scanner-scope__sectors{{
  margin-top:2px;
}}
.sigl-scanner-scope__sectors .sigl-badge{{
  box-shadow:inset 0 1px 0 rgba(255,255,255,.05);
}}
.sigl-scanner-scope__codes{{
  margin-top:14px;
  padding-top:14px;
  max-height:138px;
  border-top:1px solid rgba(148,163,184,.14);
}}
.sigl-scanner-scope__codes .sigl-code-chip{{
  background:linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.02));
  border-color:rgba(148,163,184,.18);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.05);
  transition:transform .18s ease, border-color .18s ease, background .18s ease;
}}
.sigl-scanner-scope__codes .sigl-code-chip:hover{{
  transform:translateY(-1px);
  border-color:rgba(142,164,255,.28);
  background:linear-gradient(180deg, rgba(142,164,255,.10), rgba(255,255,255,.03));
}}
.sigl-sector-picker-anchor{{
  width:0;
  height:0;
  overflow:hidden;
}}
div[data-testid="stVerticalBlock"]:has(.sigl-sector-picker-anchor){{
  gap:10px!important;
  padding:10px!important;
  border:1px solid rgba(148,163,184,.12);
  border-radius:18px;
  background:linear-gradient(180deg, rgba(19,28,45,.76), rgba(15,23,42,.58));
  box-shadow:inset 0 1px 0 rgba(255,255,255,.03);
}}
div[data-testid="stVerticalBlock"]:has(.sigl-sector-picker-anchor) > div[data-testid="stHorizontalBlock"]{{
  gap:8px!important;
}}
div[data-testid="stVerticalBlock"]:has(.sigl-sector-picker-anchor) div.stButton{{
  height:100%;
}}
div[data-testid="stVerticalBlock"]:has(.sigl-sector-picker-anchor) div.stButton>button{{
  position:relative;
  min-height:52px!important;
  border-radius:15px!important;
  border:1px solid rgba(148,163,184,.14)!important;
  background:linear-gradient(180deg, rgba(255,255,255,.035), rgba(255,255,255,.015))!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.03)!important;
  overflow:hidden!important;
  transition:
    transform .18s ease,
    border-color .18s ease,
    background .18s ease,
    box-shadow .18s ease!important;
}}
div[data-testid="stVerticalBlock"]:has(.sigl-sector-picker-anchor) div.stButton>button::before{{
  content:"";
  position:absolute;
  inset:auto auto 11px 12px;
  width:8px;
  height:8px;
  border-radius:999px;
  background:rgba(148,163,184,.42);
  opacity:.92;
  transition:
    transform .18s ease,
    background .18s ease,
    box-shadow .18s ease,
    opacity .18s ease!important;
}}
div[data-testid="stVerticalBlock"]:has(.sigl-sector-picker-anchor) div.stButton>button::after{{
  content:"";
  position:absolute;
  inset:0;
  border-radius:inherit;
  background:radial-gradient(circle at center, rgba(142,164,255,.18), rgba(142,164,255,0) 62%);
  opacity:0;
  transform:scale(.76);
  pointer-events:none;
  transition:opacity .2s ease, transform .2s ease!important;
}}
div[data-testid="stVerticalBlock"]:has(.sigl-sector-picker-anchor) div.stButton>button span,
div[data-testid="stVerticalBlock"]:has(.sigl-sector-picker-anchor) div.stButton>button p,
div[data-testid="stVerticalBlock"]:has(.sigl-sector-picker-anchor) div.stButton>button div{{
  color:var(--sigl-text)!important;
  font-weight:800!important;
}}
div[data-testid="stVerticalBlock"]:has(.sigl-sector-picker-anchor) div.stButton>button:hover{{
  transform:translateY(-1px)!important;
  border-color:rgba(142,164,255,.22)!important;
  background:linear-gradient(180deg, rgba(142,164,255,.10), rgba(142,164,255,.04))!important;
  box-shadow:0 10px 20px rgba(2,6,23,.16)!important;
}}
div[data-testid="stVerticalBlock"]:has(.sigl-sector-picker-anchor) div.stButton>button[kind="primary"]{{
  transform:translateY(1px)!important;
  border-color:rgba(99,217,162,.32)!important;
  background:
    linear-gradient(180deg, rgba(99,217,162,.18), rgba(18,163,98,.08))!important;
  box-shadow:
    0 10px 22px rgba(10,36,24,.18)!important,
    inset 0 0 0 1px rgba(99,217,162,.14)!important,
    inset 0 10px 18px rgba(99,217,162,.05)!important;
}}
div[data-testid="stVerticalBlock"]:has(.sigl-sector-picker-anchor) div.stButton>button[kind="primary"]::before{{
  background:var(--sigl-success)!important;
  box-shadow:
    0 0 0 4px rgba(99,217,162,.12),
    0 0 14px rgba(99,217,162,.26)!important;
  transform:scale(1.12)!important;
}}
div[data-testid="stVerticalBlock"]:has(.sigl-sector-picker-anchor) div.stButton>button[kind="primary"]::after{{
  opacity:1!important;
  transform:scale(1)!important;
  background:radial-gradient(circle at center, rgba(99,217,162,.18), rgba(99,217,162,0) 62%)!important;
}}
div[data-testid="stVerticalBlock"]:has(.sigl-sector-picker-anchor) div.stButton>button[kind="primary"] span,
div[data-testid="stVerticalBlock"]:has(.sigl-sector-picker-anchor) div.stButton>button[kind="primary"] p,
div[data-testid="stVerticalBlock"]:has(.sigl-sector-picker-anchor) div.stButton>button[kind="primary"] div{{
  color:var(--sigl-text-strong)!important;
}}
div[data-testid="stVerticalBlock"]:has(.sigl-sector-picker-anchor) div.stButton>button:active{{
  transform:scale(.985)!important;
}}
.sigl-note,
.sigl-summary,
.sigl-section-copy,
.sigl-result-copy,
.sigl-committee-name,
.sigl-committee-foot,
.sigl-price-meta{{
  overflow-wrap:anywhere;
  word-break:keep-all;
}}
.analysis-nav{{
  background:linear-gradient(180deg, rgba(19,28,45,.98), rgba(15,23,42,.92));
  border:1px solid var(--sigl-border-soft);
  border-radius:16px;
  padding:14px 16px;
  margin:0 0 14px;
  box-shadow:var(--sigl-shadow-sm);
}}
.analysis-nav-meta{{
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:12px;
  flex-wrap:wrap;
  margin-bottom:10px;
}}
.analysis-nav-title{{color:var(--sigl-text-strong);font-weight:800;font-size:1rem}}
.analysis-nav-sub{{color:var(--sigl-text-muted);font-size:.78rem}}
.analysis-nav-chip{{
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding:5px 10px;
  border-radius:999px;
  background:rgba(142,164,255,.12);
  border:1px solid rgba(142,164,255,.24);
  color:#D6DFFF;
  font-size:.74rem;
  font-weight:800;
}}
.sigl-page-banner,
.sigl-card,
.sigl-metric-card,
.sigl-committee-card,
.sigl-result-card,
.analysis-nav,
div[data-testid="stChatMessage"],
div[data-testid="stExpander"]{{
  position:relative;
  isolation:isolate;
  overflow:hidden;
  transition:
    transform .22s ease,
    box-shadow .22s ease,
    background .22s ease!important;
}}
.sigl-page-banner::after,
.sigl-card::after,
.sigl-metric-card::after,
.sigl-committee-card::after,
.sigl-result-card::after,
.analysis-nav::after,
div[data-testid="stChatMessage"]::after,
div[data-testid="stExpander"]::after{{
  content:"";
  position:absolute;
  inset:0;
  pointer-events:none;
  background:linear-gradient(112deg, rgba(255,255,255,0) 18%, rgba(255,255,255,.08) 48%, rgba(255,255,255,0) 78%);
  opacity:0;
  transform:translate3d(-14%, 0, 0);
  transition:opacity .22s ease, transform .32s ease;
}}
.sigl-page-banner:hover,
.sigl-card:hover,
.sigl-metric-card:hover,
.sigl-committee-card:hover,
.sigl-result-card:hover,
.analysis-nav:hover,
div[data-testid="stChatMessage"]:hover,
div[data-testid="stExpander"]:hover{{
  transform:translateY(-2px);
  box-shadow:
    0 18px 34px rgba(2,6,23,.20),
    inset 0 1px 0 rgba(255,255,255,.04)!important;
}}
.sigl-page-banner:hover::after,
.sigl-card:hover::after,
.sigl-metric-card:hover::after,
.sigl-committee-card:hover::after,
.sigl-result-card:hover::after,
.analysis-nav:hover::after,
div[data-testid="stChatMessage"]:hover::after,
div[data-testid="stExpander"]:hover::after{{
  opacity:1;
  transform:translate3d(0, 0, 0);
}}
.sigl-page-banner:focus-within,
.sigl-card:focus-within,
.sigl-metric-card:focus-within,
.sigl-committee-card:focus-within,
.sigl-result-card:focus-within,
.analysis-nav:focus-within,
div[data-testid="stChatMessage"]:focus-within,
div[data-testid="stExpander"]:focus-within{{
  box-shadow:
    0 16px 30px rgba(2,6,23,.18),
    0 0 0 1px rgba(142,164,255,.18),
    inset 0 1px 0 rgba(255,255,255,.04)!important;
}}
.sigl-badge,
.sigl-chip,
.sigl-composer-tool,
.analysis-nav-chip,
.sigl-code-chip{{
  transition:
    transform .18s ease,
    border-color .18s ease,
    box-shadow .18s ease,
    background .18s ease;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.04);
}}
.sigl-badge:hover,
.sigl-chip:hover,
.sigl-composer-tool:hover,
.analysis-nav-chip:hover,
.sigl-code-chip:hover{{
  transform:translateY(-1px);
  box-shadow:
    0 10px 18px rgba(2,6,23,.12),
    inset 0 1px 0 rgba(255,255,255,.06);
}}
.sigl-progress,
.sigl-bar-split,
.sigl-layer-track{{
  transition:border-color .18s ease, box-shadow .18s ease;
}}
.sigl-progress__fill,
.sigl-bar-split__buy,
.sigl-bar-split__sell,
.sigl-layer-fill--buy,
.sigl-layer-fill--sell{{
  transition:
    width .45s cubic-bezier(.22,.61,.36,1),
    left .45s cubic-bezier(.22,.61,.36,1),
    box-shadow .18s ease;
}}
.sigl-progress:hover,
.sigl-bar-split:hover,
.sigl-layer-track:hover{{
  box-shadow:inset 0 1px 0 rgba(255,255,255,.04);
}}
.sigl-progress:hover .sigl-progress__fill,
.sigl-bar-split:hover .sigl-bar-split__buy,
.sigl-bar-split:hover .sigl-bar-split__sell,
.sigl-layer-track:hover .sigl-layer-fill--buy,
.sigl-layer-track:hover .sigl-layer-fill--sell{{
  box-shadow:0 0 14px rgba(226,232,240,.12);
}}
div[data-testid="stCaptionContainer"] p,
div[data-testid="stCaptionContainer"] span,
p[data-testid="stCaption"]{{
  color:#CBD5E1!important;
  font-size:.8rem!important;
  font-weight:600!important;
  line-height:1.58!important;
}}
.prompt-caption{{color:var(--sigl-text-muted);font-size:.76rem;font-weight:700;margin-bottom:8px}}
.soft-note{{color:var(--sigl-text-muted);font-size:.8rem;line-height:1.6;margin-top:10px}}
@media (max-width: 980px){{
  .sigl-page-banner__meta{{justify-content:flex-start}}
  .sigl-result-tags{{justify-content:flex-start}}
  .sigl-price-top,
  .sigl-result-head,
  .sigl-page-head{{align-items:flex-start}}
  .sigl-scanner-scope__meta{{margin-left:0;justify-content:flex-start}}
  .sigl-grid--5{{grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr))}}
  .sigl-layer-row{{grid-template-columns:54px 1fr 54px;gap:8px}}
  .sigl-layer-track{{height:28px}}
  .sigl-layer-label{{font-size:.68rem;padding:3px 7px}}
}}
@media (max-width: 640px){{
  section[data-testid="stSidebar"]{{
    --sigl-sidebar-control-h:44px;
    --sigl-sidebar-gap:10px;
  }}
  section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]{{
    padding-left:.2rem!important;
    padding-right:.2rem!important;
  }}
  section[data-testid="stSidebar"] [role="radiogroup"]{{
    grid-template-columns:repeat(2, minmax(0, 1fr))!important;
  }}
  section[data-testid="stSidebar"] div.stButton>button,
  section[data-testid="stSidebar"] div[data-testid="stFormSubmitButton"] button,
  section[data-testid="stSidebar"] div[data-testid="stDownloadButton"] button{{
    padding:.72rem .88rem!important;
  }}
  div[data-testid="stTabs"] [role="tablist"]{{
    gap:6px!important;
    padding:6px!important;
  }}
  div[data-testid="stTabs"] [role="tab"]{{
    min-height:42px!important;
    padding:.62rem .92rem!important;
    border-radius:13px!important;
  }}
  .sigl-grid--2,
  .sigl-grid--3,
  .sigl-grid--4,
  .sigl-grid--5,
  .sigl-result-summary{{grid-template-columns:1fr}}
  .block-container{{padding-left:1rem!important;padding-right:1rem!important}}
  .sigl-page-banner{{padding:18px 16px}}
  .sigl-empty-card{{padding:18px 16px}}
  .sigl-page-banner__meta{{justify-content:flex-start}}
  .sigl-scanner-scope__codes{{max-height:none}}
  .sigl-price-value{{font-size:1.8rem}}
  .sigl-layer-row{{grid-template-columns:46px 1fr 46px;gap:6px}}
  .sigl-layer-track{{height:26px}}
  .sigl-layer-label{{font-size:.64rem;padding:2px 6px}}
  .sigl-card{{padding:14px 14px}}
  .sigl-metric-card,
  .sigl-committee-card{{padding:13px 13px}}
  div[data-testid="stForm"] div[data-testid="stHorizontalBlock"]{{
    flex-direction:column!important;
    align-items:stretch!important;
    gap:10px!important;
  }}
  div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div{{
    width:100%!important;
  }}
  div[data-testid="stChatInput"]{{max-width:none}}
}}
@media (prefers-reduced-motion: reduce){{
  div[data-testid="stTabs"] [role="tab"],
  div[data-baseweb="select"]>div,
  div[data-baseweb="select"]>div::before,
  div[data-baseweb="select"]>div::after,
  div[data-baseweb="select"] svg,
  div[data-baseweb="popover"] [role="option"],
  div[data-baseweb="popover"] [role="option"]::before,
  div[data-testid="stTextInput"] input,
  div[data-testid="stNumberInput"] input,
  textarea,
  div.stButton>button,
  div[data-testid="stFormSubmitButton"] button,
  div[data-testid="stChatInput"] button,
  div[data-testid="stMultiSelect"] [data-baseweb="tag"],
  .sigl-page-banner,
  .sigl-card,
  .sigl-metric-card,
  .sigl-committee-card,
  .sigl-result-card,
  .analysis-nav,
  div[data-testid="stChatMessage"],
  div[data-testid="stExpander"],
  .sigl-badge,
  .sigl-chip,
  .sigl-composer-tool,
  .analysis-nav-chip,
  .sigl-code-chip,
  .sigl-progress__fill,
  .sigl-bar-split__buy,
  .sigl-bar-split__sell,
  .sigl-layer-fill--buy,
  .sigl-layer-fill--sell{{
    transition:none!important;
    transform:none!important;
  }}
  div[data-testid="stTabs"] [role="tabpanel"]{{
    animation:none!important;
  }}
  div[data-testid="stTabs"] [role="tab"]::before,
  div[data-testid="stTabs"] [role="tab"]::after{{
    transition:none!important;
  }}
  div.stButton>button::before,
  div[data-testid="stFormSubmitButton"] button::before{{
    opacity:.35!important;
    transition:none!important;
  }}
  .sigl-page-banner::after,
  .sigl-card::after,
  .sigl-metric-card::after,
  .sigl-committee-card::after,
  .sigl-result-card::after,
  .analysis-nav::after,
  div[data-testid="stChatMessage"]::after,
  div[data-testid="stExpander"]::after{{
    opacity:0!important;
    transition:none!important;
  }}
  section[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"],
  section[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]::before,
  section[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]::after{{
    animation:none!important;
    transition:none!important;
  }}
  div[data-testid="stVerticalBlock"]:has(.sigl-sector-picker-anchor) div.stButton>button,
  div[data-testid="stVerticalBlock"]:has(.sigl-sector-picker-anchor) div.stButton>button::before,
  div[data-testid="stVerticalBlock"]:has(.sigl-sector-picker-anchor) div.stButton>button::after{{
    animation:none!important;
    transition:none!important;
  }}
  .sigl-scanner-scope__codes .sigl-code-chip{{
    transition:none!important;
    transform:none!important;
  }}
}}
</style>"""


def build_brand_theme_css():
    return f"""
@import url('{FONT_IMPORT_URL}');
{_css_vars()}
html,body{{
  margin:0;
  padding:0;
  background:transparent;
  font-family:{FONT_STACK};
  color:var(--sigl-text);
}}
*{{box-sizing:border-box}}
.sigl-brand-root{{
  width:100%;
  max-width:100%;
}}
.sigl-brand-shell{{
  position:relative;
  min-height:124px;
  padding:18px 22px;
  background:linear-gradient(180deg, rgba(11,16,32,.98) 0%, rgba(14,20,37,.95) 100%);
  border:1px solid rgba(148,163,184,.18);
  border-radius:22px;
  box-shadow:0 16px 36px rgba(8,15,30,.26);
  width:100%;
  max-width:100%;
  min-width:0;
  overflow:hidden;
}}
.sigl-brand-shell::before{{
  content:"";
  position:absolute;
  inset:0;
  background:
    linear-gradient(180deg, rgba(255,255,255,.025), rgba(255,255,255,0) 22%, rgba(255,255,255,.018) 78%, rgba(255,255,255,.03) 100%),
    repeating-linear-gradient(90deg, rgba(148,163,184,.045) 0 1px, transparent 1px 42px),
    repeating-linear-gradient(180deg, rgba(148,163,184,.028) 0 1px, transparent 1px 20px);
  opacity:.36;
  animation:sigl-scanline-drift 16s linear infinite;
  pointer-events:none;
}}
.sigl-brand-shell::after{{
  content:"";
  position:absolute;
  inset:-10% -4%;
  background:
    radial-gradient(circle at 50% 50%, rgba(255,216,120,.16) 0%, rgba(255,216,120,.08) 18%, rgba(255,216,120,0) 44%),
    radial-gradient(circle at 50% 50%, rgba(255,244,208,.10) 0%, rgba(255,244,208,0) 28%);
  opacity:0;
  transform:scale(.96);
  filter:blur(18px);
  animation:sigl-header-jackpot-haze 10.8s linear infinite;
  pointer-events:none;
}}
.sigl-brand-shell > .sigl-brand-bar::before{{
  content:"";
  position:absolute;
  inset:-12px;
  border-radius:18px;
  border:1px solid rgba(255,255,255,.04);
  pointer-events:none;
}}
.sigl-brand-shell--compact{{
  min-height:108px;
}}
.sigl-brand-bar{{
  position:relative;
  z-index:1;
  display:flex;
  align-items:center;
  justify-content:center;
  width:100%;
  min-height:84px;
}}
.sigl-brand-lockup{{
  position:relative;
  z-index:1;
  display:flex;
  justify-content:center;
  width:min(100%, 520px);
  min-width:0;
}}
.sigl-brand-lockup::before{{
  content:none;
}}
.sigl-brand-wordmark{{
  display:flex;
  flex-direction:column;
  justify-content:center;
  align-items:center;
  gap:6px;
  min-width:0;
  text-align:center;
  position:relative;
  z-index:1;
}}
.sigl-brand-title{{
  display:inline-flex;
  align-items:baseline;
  gap:.05em;
  font-size:clamp(2.18rem, 5vw, 3.35rem);
  line-height:.94;
  font-weight:900;
  letter-spacing:.04em;
  text-transform:uppercase;
  text-shadow:none;
  position:relative;
}}
.sigl-brand-title__jackpot{{
  position:absolute;
  left:0;
  top:0;
  display:inline-flex;
  align-items:baseline;
  gap:.05em;
  opacity:0;
  pointer-events:none;
  z-index:3;
  animation:sigl-jackpot-burst 10.8s linear infinite;
}}
.sigl-brand-title__jackpot-mark{{
  color:#FFE08B;
  text-shadow:
    0 0 12px rgba(255,214,102,.34),
    0 0 28px rgba(255,214,102,.24),
    0 0 56px rgba(255,214,102,.12);
}}
.sigl-brand-title__jackpot-letters{{
  display:inline-flex;
  align-items:baseline;
  gap:.05em;
}}
.sigl-brand-title__jackpot-letters span{{
  display:inline-block;
  color:#FFF4C9;
  text-shadow:
    0 0 12px rgba(255,214,102,.40),
    0 0 28px rgba(255,214,102,.28),
    0 0 62px rgba(255,214,102,.16);
}}
.sigl-brand-title__mark{{
  display:inline-block;
  color:#9CF7C5;
  text-shadow:
    0 0 10px rgba(72,245,162,.26),
    0 0 24px rgba(72,245,162,.18);
  transform-origin:50% 72%;
  will-change:transform, text-shadow, color;
  animation:sigl-dollar-pop 3.2s cubic-bezier(.23,.88,.33,1) infinite;
}}
.sigl-brand-title__letters{{
  position:relative;
  display:inline-flex;
  align-items:baseline;
  gap:.05em;
  padding:.02em .04em;
}}
.sigl-brand-title__letters::before,
.sigl-brand-title__letters::after{{
  content:"";
  position:absolute;
  inset:-.36em -.28em -.24em;
  pointer-events:none;
  filter:blur(20px);
  opacity:.46;
}}
.sigl-brand-title__letters::before{{
  background:
    radial-gradient(circle at 11% 56%, rgba(255,88,102,.38), transparent 18%),
    radial-gradient(circle at 60% 50%, rgba(255,88,102,.30), transparent 20%);
  animation:sigl-bloom-red 7.3s steps(1,end) infinite;
}}
.sigl-brand-title__letters::after{{
  background:
    radial-gradient(circle at 34% 48%, rgba(72,245,162,.34), transparent 16%),
    radial-gradient(circle at 92% 44%, rgba(72,245,162,.36), transparent 20%);
  animation:sigl-bloom-green 8.1s steps(1,end) infinite;
}}
.sigl-brand-letter{{
  position:relative;
  display:inline-block;
  color:#FCFDFF;
  text-shadow:
    0 0 8px rgba(248,250,252,.12),
    0 0 20px rgba(255,255,255,.07);
  will-change:text-shadow, color, opacity;
}}
.sigl-brand-letter::after{{
  content:attr(data-char);
  position:absolute;
  inset:0;
  color:var(--glow-color);
  opacity:.0;
  pointer-events:none;
  mix-blend-mode:screen;
  filter:blur(.6px);
}}
.sigl-brand-letter--red{{
  --glow-color:#FF5866;
  animation:sigl-neon-red 7.2s steps(1,end) infinite;
}}
.sigl-brand-letter--red::after{{
  animation:sigl-neon-red-ghost 7.2s steps(1,end) infinite;
}}
.sigl-brand-letter--green{{
  --glow-color:#48F5A2;
  animation:sigl-neon-green 8.4s steps(1,end) infinite;
}}
.sigl-brand-letter--green::after{{
  animation:sigl-neon-green-ghost 8.4s steps(1,end) infinite;
}}
.sigl-brand-letter--s{{
  animation-delay:-.9s;
}}
.sigl-brand-letter--s::after{{
  animation-delay:-.9s;
}}
.sigl-brand-letter--i{{
  animation-delay:-2.6s;
}}
.sigl-brand-letter--i::after{{
  animation-delay:-2.6s;
}}
.sigl-brand-letter--g{{
  animation-delay:-1.4s;
}}
.sigl-brand-letter--g::after{{
  animation-delay:-1.4s;
}}
.sigl-brand-letter--n{{
  animation-delay:-3.2s;
}}
.sigl-brand-letter--n::after{{
  animation-delay:-3.2s;
}}
.sigl-brand-subtitle{{
  position:relative;
  padding-right:14px;
  color:#8E9AAF;
  font-size:.74rem;
  font-weight:800;
  letter-spacing:.2em;
  line-height:1;
}}
.sigl-brand-subtitle::after{{
  content:"";
  position:absolute;
  right:0;
  top:50%;
  width:6px;
  height:6px;
  border-radius:50%;
  background:rgba(255,143,150,.92);
  box-shadow:0 0 12px rgba(255,143,150,.28);
  transform:translateY(-50%);
  animation:sigl-subtitle-dot-jackpot 10.8s linear infinite;
}}
.sigl-brand-shell--compact .sigl-brand-bar{{
  min-height:70px;
}}
.sigl-brand-shell--compact .sigl-brand-lockup{{
  width:min(100%, 460px);
}}
.sigl-brand-shell--compact .sigl-brand-title{{
  font-size:clamp(1.9rem, 4.4vw, 2.9rem);
}}
.sigl-brand-shell--compact .sigl-brand-subtitle{{
  font-size:.68rem;
  letter-spacing:.18em;
}}
@keyframes sigl-neon-red{{
  0%, 5%, 11%, 18%, 31%, 38%, 55%, 63%, 79%, 100%{{
    color:#FFF4F6;
    text-shadow:
      0 0 8px rgba(248,250,252,.12),
      0 0 18px rgba(255,88,102,.14);
  }}
  6%, 10.8%, 20.2%, 30.8%, 40.2%, 55%, 65.2%, 78.4%{{
    color:#FFEDEF;
    text-shadow:
      0 0 8px rgba(255,255,255,.50),
      0 0 16px rgba(255,88,102,.62),
      0 0 34px rgba(255,88,102,.38),
      0 0 64px rgba(255,88,102,.20);
  }}
  8%, 22.2%, 42.2%, 58.4%{{
    color:#FFFFFF;
    text-shadow:
      0 0 10px rgba(255,255,255,.68),
      0 0 20px rgba(255,88,102,.86),
      0 0 44px rgba(255,88,102,.52),
      0 0 82px rgba(255,88,102,.26);
  }}
}}
@keyframes sigl-neon-red-ghost{{
  0%, 5%, 11%, 18%, 31%, 38%, 55%, 63%, 79%, 100%{{opacity:.04}}
  6%, 10.8%, 20.2%, 30.8%, 40.2%, 55%, 65.2%, 78.4%{{opacity:.22}}
  8%, 22.2%, 42.2%, 58.4%{{opacity:.36}}
}}
@keyframes sigl-neon-green{{
  0%, 7%, 12%, 24%, 36%, 43%, 60%, 69%, 82%, 100%{{
    color:#F4FFF9;
    text-shadow:
      0 0 8px rgba(248,250,252,.12),
      0 0 18px rgba(72,245,162,.14);
  }}
  8%, 13.8%, 26.2%, 38.2%, 45.2%, 62.2%, 71.2%, 83.6%{{
    color:#EAFFF4;
    text-shadow:
      0 0 8px rgba(255,255,255,.48),
      0 0 16px rgba(72,245,162,.60),
      0 0 34px rgba(72,245,162,.38),
      0 0 64px rgba(72,245,162,.20);
  }}
  10%, 28.2%, 48.2%, 73.2%{{
    color:#FFFFFF;
    text-shadow:
      0 0 10px rgba(255,255,255,.66),
      0 0 20px rgba(72,245,162,.84),
      0 0 44px rgba(72,245,162,.50),
      0 0 82px rgba(72,245,162,.24);
  }}
}}
@keyframes sigl-neon-green-ghost{{
  0%, 7%, 12%, 24%, 36%, 43%, 60%, 69%, 82%, 100%{{opacity:.04}}
  8%, 13.8%, 26.2%, 38.2%, 45.2%, 62.2%, 71.2%, 83.6%{{opacity:.22}}
  10%, 28.2%, 48.2%, 73.2%{{opacity:.34}}
}}
@keyframes sigl-bloom-red{{
  0%, 14%, 27%, 42%, 58%, 71%, 100%{{opacity:.16;transform:translateY(0) scale(1)}}
  7%, 20%, 35%, 50%, 66%, 84%{{opacity:.30;transform:translateY(-1px) scale(1.04)}}
  11%, 24%, 39%, 63%{{opacity:.44;transform:translateY(0) scale(1.08)}}
}}
@keyframes sigl-bloom-green{{
  0%, 16%, 29%, 46%, 59%, 76%, 100%{{opacity:.14;transform:translateY(0) scale(1)}}
  9%, 21%, 37%, 52%, 68%, 88%{{opacity:.28;transform:translateY(1px) scale(1.05)}}
  13%, 25%, 41%, 73%{{opacity:.40;transform:translateY(0) scale(1.09)}}
}}
@keyframes sigl-dollar-pop{{
  0%, 16%, 24%, 42%, 52%, 100%{{
    color:#9CF7C5;
    transform:translateY(0) scale(1);
    text-shadow:
      0 0 10px rgba(72,245,162,.24),
      0 0 22px rgba(72,245,162,.16);
  }}
  18%{{
    color:#DFFFF0;
    transform:translateY(-3px) scale(1.06);
    text-shadow:
      0 0 10px rgba(255,255,255,.32),
      0 0 18px rgba(72,245,162,.78),
      0 0 36px rgba(72,245,162,.48),
      0 0 64px rgba(72,245,162,.26);
  }}
  21%{{
    color:#BBF1D2;
    transform:translateY(1px) scale(.98);
    text-shadow:
      0 0 10px rgba(72,245,162,.34),
      0 0 20px rgba(72,245,162,.20);
  }}
  46%{{
    color:#D7FFEA;
    transform:translateY(-2px) scale(1.04);
    text-shadow:
      0 0 10px rgba(255,255,255,.24),
      0 0 18px rgba(72,245,162,.72),
      0 0 34px rgba(72,245,162,.44),
      0 0 60px rgba(72,245,162,.24);
  }}
  49%{{
    color:#A6EEC4;
    transform:translateY(0) scale(1);
    text-shadow:
      0 0 10px rgba(72,245,162,.26),
      0 0 22px rgba(72,245,162,.16);
  }}
}}
@keyframes sigl-jackpot-burst{{
  0%, 73%, 100%{{
    opacity:0;
    transform:scale(1);
  }}
  74.2%{{
    opacity:.28;
    transform:scale(1.012);
  }}
  75.4%{{
    opacity:1;
    transform:scale(1.035);
  }}
  76.2%{{
    opacity:.52;
    transform:scale(1.014);
  }}
  77.1%{{
    opacity:1;
    transform:scale(1.028);
  }}
  78.2%{{
    opacity:.72;
    transform:scale(1.016);
  }}
  79.2%{{
    opacity:0;
    transform:scale(1);
  }}
}}
@keyframes sigl-scanline-drift{{
  0%{{transform:translate3d(0,0,0)}}
  100%{{transform:translate3d(0,14px,0)}}
}}
@keyframes sigl-header-jackpot-haze{{
  0%, 73%, 100%{{
    opacity:0;
    transform:scale(.96);
  }}
  74.2%{{
    opacity:.18;
    transform:scale(1);
  }}
  75.4%{{
    opacity:.42;
    transform:scale(1.04);
  }}
  76.2%{{
    opacity:.28;
    transform:scale(1.015);
  }}
  77.1%{{
    opacity:.36;
    transform:scale(1.03);
  }}
  78.2%{{
    opacity:.14;
    transform:scale(1.01);
  }}
  79.2%{{
    opacity:0;
    transform:scale(.98);
  }}
}}
@keyframes sigl-subtitle-dot-jackpot{{
  0%, 73%, 100%{{
    background:rgba(255,143,150,.92);
    box-shadow:0 0 12px rgba(255,143,150,.28);
  }}
  74.2%{{
    background:rgba(137,255,188,.96);
    box-shadow:
      0 0 10px rgba(72,245,162,.46),
      0 0 18px rgba(72,245,162,.22);
  }}
  75.4%{{
    background:#DFFFF0;
    box-shadow:
      0 0 10px rgba(255,255,255,.34),
      0 0 18px rgba(72,245,162,.78),
      0 0 34px rgba(72,245,162,.34);
  }}
  76.2%{{
    background:rgba(168,255,206,.98);
    box-shadow:
      0 0 10px rgba(72,245,162,.54),
      0 0 22px rgba(72,245,162,.26);
  }}
  77.1%{{
    background:#F1FFF7;
    box-shadow:
      0 0 10px rgba(255,255,255,.30),
      0 0 18px rgba(72,245,162,.72),
      0 0 30px rgba(72,245,162,.30);
  }}
  78.2%{{
    background:rgba(183,255,217,.96);
    box-shadow:
      0 0 10px rgba(72,245,162,.42),
      0 0 18px rgba(72,245,162,.20);
  }}
  79.2%{{
    background:rgba(255,143,150,.92);
    box-shadow:0 0 12px rgba(255,143,150,.28);
  }}
}}
@media (max-width: 920px){{
  .sigl-brand-shell{{min-height:116px;padding:16px 18px}}
  .sigl-brand-bar{{min-height:78px}}
  .sigl-brand-lockup{{width:min(100%, 470px)}}
  .sigl-brand-title{{font-size:clamp(1.95rem, 5.6vw, 3rem)}}
}}
@media (max-width: 640px){{
  .sigl-brand-shell{{min-height:100px;padding:14px 16px;border-radius:18px}}
  .sigl-brand-bar{{min-height:64px;justify-content:center}}
  .sigl-brand-lockup{{width:100%}}
  .sigl-brand-wordmark{{gap:4px}}
  .sigl-brand-title{{font-size:clamp(1.72rem, 10vw, 2.22rem);letter-spacing:.09em}}
  .sigl-brand-subtitle{{font-size:.64rem;letter-spacing:.14em;padding-right:10px}}
  .sigl-brand-subtitle::after{{width:5px;height:5px}}
}}
@media (prefers-reduced-motion: reduce){{
  .sigl-brand-shell::before,
  .sigl-brand-shell::after,
  .sigl-brand-title__jackpot,
  .sigl-brand-title__mark,
  .sigl-brand-title__letters::before,
  .sigl-brand-title__letters::after,
  .sigl-brand-letter,
  .sigl-brand-letter::after{{
    animation:none!important;
  }}
}}
"""


COMPANY_DETAILS_THEME_OVERRIDES = f"""
@import url('{FONT_IMPORT_URL}');
{_css_vars()}
html, body, [class*="css"] {{
  font-family:{FONT_STACK} !important;
}}
[data-testid="stVerticalBlockBorderWrapper"] {{
  background:
    linear-gradient(180deg, rgba(142,164,255,.07), rgba(142,164,255,0) 26%),
    linear-gradient(180deg, rgba(19,28,45,.98), rgba(15,23,42,.92)) !important;
  border:1px solid var(--sigl-border-soft) !important;
  border-radius:20px !important;
  box-shadow:var(--sigl-shadow-sm) !important;
}}
[data-testid="stVerticalBlockBorderWrapper"] > div {{
  padding:26px 28px !important;
}}
.s-title {{
  color:var(--sigl-text-strong) !important;
  border-bottom:1px solid var(--sigl-border-soft) !important;
}}
.s-title .s-num {{
  background:rgba(142,164,255,.14) !important;
  border-color:rgba(142,164,255,.24) !important;
  color:#D6DFFF !important;
}}
.note-box,
.spotlight-card,
.hero-card,
.signal-card,
.invest-card,
.invest-metric,
.cluster-card,
.score-pillar,
.metric-rail-card,
.target-mini-card,
.consensus-step,
.range-legend-item,
.ownership-row,
.compact-chip,
.coverage-pill,
.nav-chip,
.n-item,
.meta-item,
.cd-chip,
.opt-box,
.story-card,
.consensus-corridor,
.consensus-corridor__stat {{
  background:linear-gradient(180deg, rgba(19,28,45,.98), rgba(15,23,42,.92)) !important;
  border:1px solid var(--sigl-border-soft) !important;
  border-radius:16px !important;
  box-shadow:none !important;
}}
.note-box,
.hero-card,
.invest-card,
.insight-shell {{
  background:
    linear-gradient(180deg, rgba(142,164,255,.08), rgba(142,164,255,0) 34%),
    linear-gradient(180deg, rgba(19,28,45,.98), rgba(15,23,42,.92)) !important;
  border-color:rgba(142,164,255,.20) !important;
}}
.hero-kicker,
.invest-kicker,
.section-pill,
.nav-chip b {{
  color:#D6DFFF !important;
}}
.spotlight-card,
.hero-card,
.signal-card,
.invest-card,
.invest-metric,
.cluster-card,
.score-pillar,
.metric-rail-card,
.target-mini-card,
.consensus-step,
.range-legend-item,
.ownership-row,
.compact-chip,
.n-item,
.meta-item,
.cd-chip,
.opt-box,
.story-card,
.insight-shell,
.consensus-corridor,
.consensus-corridor__stat {{
  position:relative;
  isolation:isolate;
  overflow:hidden;
  transition:
    transform .22s ease,
    box-shadow .22s ease,
    background .22s ease,
    border-color .22s ease !important;
}}
.spotlight-card::after,
.hero-card::after,
.signal-card::after,
.invest-card::after,
.invest-metric::after,
.cluster-card::after,
.score-pillar::after,
.metric-rail-card::after,
.target-mini-card::after,
.consensus-step::after,
.range-legend-item::after,
.ownership-row::after,
.compact-chip::after,
.n-item::after,
.meta-item::after,
.cd-chip::after,
.opt-box::after,
.story-card::after,
.insight-shell::after,
.consensus-corridor::after,
.consensus-corridor__stat::after {{
  content:"";
  position:absolute;
  inset:0;
  pointer-events:none;
  background:linear-gradient(112deg, rgba(255,255,255,0) 18%, rgba(255,255,255,.08) 48%, rgba(255,255,255,0) 78%);
  opacity:0;
  transform:translate3d(-14%, 0, 0);
  transition:opacity .22s ease, transform .32s ease;
}}
.spotlight-card:hover,
.hero-card:hover,
.signal-card:hover,
.invest-card:hover,
.invest-metric:hover,
.cluster-card:hover,
.score-pillar:hover,
.metric-rail-card:hover,
.target-mini-card:hover,
.consensus-step:hover,
.range-legend-item:hover,
.ownership-row:hover,
.compact-chip:hover,
.n-item:hover,
.meta-item:hover,
.cd-chip:hover,
.opt-box:hover,
.story-card:hover,
.insight-shell:hover,
.consensus-corridor:hover,
.consensus-corridor__stat:hover {{
  transform:translateY(-2px);
  box-shadow:
    0 18px 34px rgba(2,6,23,.20),
    inset 0 1px 0 rgba(255,255,255,.04) !important;
}}
.spotlight-card:hover::after,
.hero-card:hover::after,
.signal-card:hover::after,
.invest-card:hover::after,
.invest-metric:hover::after,
.cluster-card:hover::after,
.score-pillar:hover::after,
.metric-rail-card:hover::after,
.target-mini-card:hover::after,
.consensus-step:hover::after,
.range-legend-item:hover::after,
.ownership-row:hover::after,
.compact-chip:hover::after,
.n-item:hover::after,
.meta-item:hover::after,
.cd-chip:hover::after,
.opt-box:hover::after,
.story-card:hover::after,
.insight-shell:hover::after,
.consensus-corridor:hover::after,
.consensus-corridor__stat:hover::after {{
  opacity:1;
  transform:translate3d(0, 0, 0);
}}
.spotlight-card:focus-within,
.hero-card:focus-within,
.signal-card:focus-within,
.invest-card:focus-within,
.invest-metric:focus-within,
.cluster-card:focus-within,
.score-pillar:focus-within,
.metric-rail-card:focus-within,
.target-mini-card:focus-within,
.consensus-step:focus-within,
.range-legend-item:focus-within,
.ownership-row:focus-within,
.compact-chip:focus-within,
.n-item:focus-within,
.meta-item:focus-within,
.cd-chip:focus-within,
.opt-box:focus-within,
.story-card:focus-within,
.insight-shell:focus-within,
.consensus-corridor:focus-within,
.consensus-corridor__stat:focus-within {{
  box-shadow:
    0 16px 30px rgba(2,6,23,.18),
    0 0 0 1px rgba(142,164,255,.18),
    inset 0 1px 0 rgba(255,255,255,.04) !important;
}}
.hero-copy,
.invest-copy,
.section-lead,
.signal-sub,
.spotlight-sub,
.range-legend-sub,
.target-mini-sub,
.cluster-sub,
.n-meta,
.note-box,
.m-label,
.spotlight-label,
.signal-label,
.meta-label,
.cd-chip-label {{
  color:var(--sigl-text-muted) !important;
}}
.m-value,
.spotlight-value,
.signal-value,
.meta-value,
.cd-chip-value,
.hero-headline,
.invest-title,
.cluster-title,
.range-legend-value,
.target-mini-value,
.score-pillar-value {{
  color:var(--sigl-text-strong) !important;
}}
@media (max-width: 640px) {{
  [data-testid="stVerticalBlockBorderWrapper"] > div {{
    padding:18px 18px !important;
  }}
}}
"""
