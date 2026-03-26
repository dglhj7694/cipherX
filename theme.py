FONT_IMPORT_URL = "https://cdn.jsdelivr.net/gh/moonspam/NanumSquare@2.0/nanumsquare.css"
FONT_STACK = "'NanumSquare','Malgun Gothic','Apple SD Gothic Neo',sans-serif"
PLOTLY_FONT_FAMILY = "NanumSquare, Malgun Gothic, Apple SD Gothic Neo, sans-serif"


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
  background:
    linear-gradient(180deg, rgba(142,164,255,.05), rgba(142,164,255,0) 24%),
    linear-gradient(180deg, #0D1424 0%, #0B1120 100%)!important;
  border-right:1px solid var(--sigl-border-soft)!important;
}}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] label p{{
  color:var(--sigl-text)!important;
}}
div[data-baseweb="select"]>div,
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
textarea{{
  background:rgba(15,23,42,.76)!important;
  border:1px solid var(--sigl-border-soft)!important;
  color:var(--sigl-text-strong)!important;
  border-radius:14px!important;
}}
div[data-baseweb="select"] span,
div[data-baseweb="select"] input,
div[data-baseweb="select"] div{{
  color:var(--sigl-text)!important;
}}
div[data-testid="stMultiSelect"] [data-baseweb="tag"]{{
  background:rgba(142,164,255,.12)!important;
  border:1px solid rgba(142,164,255,.22)!important;
  border-radius:999px!important;
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
div[data-testid="stTabs"] button{{
  color:var(--sigl-text-muted)!important;
  font-weight:800!important;
  border-bottom:2px solid transparent!important;
  border-radius:0!important;
}}
div[data-testid="stTabs"] button[aria-selected="true"]{{
  color:var(--sigl-text-strong)!important;
  border-bottom-color:var(--sigl-accent)!important;
}}
div[data-testid="stTabs"] [role="tablist"]{{
  flex-wrap:wrap!important;
  gap:6px!important;
}}
div[data-testid="stTabs"] [role="tabpanel"]{{
  min-width:0!important;
}}
div.stButton>button{{
  border-radius:14px!important;
  font-weight:800!important;
  min-height:44px!important;
  transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease!important;
}}
div.stButton>button:hover{{
  transform:translateY(-1px);
}}
div.stButton>button[kind="primary"]{{
  background:linear-gradient(135deg, #7C93FF, #5D7BFF)!important;
  color:white!important;
  border:none!important;
  box-shadow:0 12px 24px rgba(93,123,255,.22)!important;
}}
div.stButton>button[kind="secondary"]{{
  background:linear-gradient(180deg, rgba(19,28,45,.96), rgba(15,23,42,.88))!important;
  color:var(--sigl-text)!important;
  border:1px solid var(--sigl-border-soft)!important;
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
}}
div[data-testid="stForm"] div[data-testid="stTextInput"] input::placeholder{{
  color:#7F91AF!important;
  opacity:1!important;
}}
div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] button{{
  min-height:54px!important;
  border-radius:16px!important;
}}
div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] button:not([kind="primary"]){{
  background:linear-gradient(180deg, rgba(29,40,64,.96), rgba(22,32,51,.92))!important;
  color:#F8FAFC!important;
  border:1px solid rgba(148,163,184,.24)!important;
  box-shadow:none!important;
}}
div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] button:not([kind="primary"]) span,
div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] button:not([kind="primary"]) p,
div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] button:not([kind="primary"]) div{{
  color:#F8FAFC!important;
  opacity:1!important;
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
}}
div[data-testid="stChatInput"] textarea::placeholder{{
  color:var(--sigl-text-muted)!important;
  opacity:1!important;
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
  .sigl-grid--5{{grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr))}}
  .sigl-layer-row{{grid-template-columns:54px 1fr 54px;gap:8px}}
  .sigl-layer-track{{height:28px}}
  .sigl-layer-label{{font-size:.68rem;padding:3px 7px}}
}}
@media (max-width: 640px){{
  .sigl-grid--2,
  .sigl-grid--3,
  .sigl-grid--4,
  .sigl-grid--5,
  .sigl-result-summary{{grid-template-columns:1fr}}
  .block-container{{padding-left:1rem!important;padding-right:1rem!important}}
  .sigl-page-banner{{padding:18px 16px}}
  .sigl-empty-card{{padding:18px 16px}}
  .sigl-page-banner__meta{{justify-content:flex-start}}
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
  display:flex;
  align-items:center;
  justify-content:flex-start;
  min-height:96px;
  padding:16px 22px;
  background:linear-gradient(180deg, rgba(19,28,45,.98), rgba(15,23,42,.92));
  border:1px solid var(--sigl-border-soft);
  border-radius:20px;
  box-shadow:var(--sigl-shadow-sm);
  width:100%;
  max-width:100%;
  min-width:0;
}}
.sigl-brand-lockup{{
  display:flex;
  align-items:center;
  gap:14px;
  min-width:0;
}}
.sigl-brand-logo{{
  width:48px;
  height:48px;
  display:flex;
  align-items:center;
  justify-content:center;
  flex:0 0 auto;
}}
.sigl-brand-logo svg{{
  width:48px;
  height:48px;
  display:block;
}}
.sigl-brand-mark{{display:flex;align-items:center;min-width:0}}
.sigl-brand-name{{
  margin:0;
  color:var(--sigl-text-strong);
  font-size:2.15rem;
  font-weight:900;
  letter-spacing:-.03em;
  overflow-wrap:anywhere;
}}
@media (max-width: 640px){{
  .sigl-brand-shell{{padding:14px 18px;min-height:88px}}
  .sigl-brand-logo,
  .sigl-brand-logo svg{{width:42px;height:42px}}
  .sigl-brand-name{{font-size:1.82rem}}
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
.opt-box {{
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
