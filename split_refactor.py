import os
import sys

app_path = r"c:\cipher\cipherX\app.py"
with open(app_path, "r", encoding="utf-8") as f:
    content = f.read()

def extract(start_str, end_str):
    start_idx = content.find(start_str)
    if start_idx == -1:
        print(f"Start string not found: {start_str}")
        return ""
    end_idx = content.find(end_str, start_idx)
    if end_idx == -1:
        print(f"End string not found: {end_str}")
        return ""
    return content[start_idx:end_idx].strip()

# We will build the new files

config_content = """import pandas as pd
import numpy as np
import streamlit as st

""" + extract("OB1,OB2,OS1", "def _recent(s,lb=3):")

utils_content = """import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import math, time, re

# Lazy import to avoid circular dependency
def _compute_cached(t, k):
    from engine import detect_all_signals
    from indicators import compute_indicators
    try:
        df = fetch_history(t)
        return detect_all_signals(compute_indicators(df)) if not df.empty else None
    except Exception as e:
        print(f"[ERR]{t}:{e}")
        return None

""" + extract("def _recent(s,lb=3):", "@st.cache_data(ttl=300,max_entries=50,show_spinner=False)\ndef _compute_cached") + """
def compute_and_cache(t,ts=None):
    ck=f"{t}_{ts}" if ts else f"{t}_{math.floor(time.time()/300)}";return _compute_cached(t,ck)
"""
# Note we replaced _compute_cached in utils_content. Let's just fix it manually.
utils_part = extract("def _recent(s,lb=3):", "def compute_rsi(s,p=14):")
# Remove the original _compute_cached from utils_part
utils_part = utils_part.split("@st.cache_data(ttl=300,max_entries=50,show_spinner=False)\ndef _compute_cached")[0]

utils_content = """import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import math, time, re

""" + utils_part + """
@st.cache_data(ttl=300,max_entries=50,show_spinner=False)
def _compute_cached(t,k):
    from engine import detect_all_signals
    from indicators import compute_indicators
    try:df=fetch_history(t);return detect_all_signals(compute_indicators(df)) if not df.empty else None
    except Exception as e:print(f"[ERR]{t}:{e}");return None
def compute_and_cache(t,ts=None):
    ck=f"{t}_{ts}" if ts else f"{t}_{math.floor(time.time()/300)}";return _compute_cached(t,ck)
"""

indicators_content = """import pandas as pd
import numpy as np

""" + extract("def compute_rsi(s,p=14):", "print(\"✅ Part 1/4 완료\")")

engine_content = """import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from config import *
from utils import _volf, _recent, _cd_dir, _cooldown, _vs, _sp, _spd, _sf

""" + extract("def det_123pb(h,l,c,adx,pdi,mdi):", "print(\"✅ Part 2/4 완료 — 139개 시그널 + 반전 인식 10-Layer\")")

chart_content = """import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from config import *
from utils import _sf

""" + extract("def _build_candle_hover(dc):", "def render_price_header(m):")

ui_content = """import streamlit as st
from chart import build_metadata, build_chart
from company_details import render_company_details
import json
from config import NUM_LAYERS

""" + extract("def render_price_header(m):", "print(\"✅ Part 3/4 완료\")")

ai_agent_content = """import google.generativeai as genai
import streamlit as st
import time
from config import SIGNAL_REGISTRY, COMBINED_SCAN_REGISTRY, NUM_LAYERS
from utils import _cs_str

""" + extract("def build_prompt_text(dc, meta):", "def analyze(ticker,chart_days=252,refresh=False):")

app_new_content = """import streamlit as st
import google.generativeai as genai
import time, json
from datetime import datetime
from st_copy_to_clipboard import st_copy_to_clipboard
from concurrent.futures import ThreadPoolExecutor, as_completed

# Extracted modules
from config import GEMINI_API_KEY
from utils import validate_ticker, _valid_fmt, _sf, fetch_fundamentals, compute_and_cache
from chart import build_chart, build_metadata
from ui import render_analysis
from ai_agent import build_prompt_text, build_ai_prompt
from sectors import SECTOR_GROUPS

st.set_page_config(page_title="CipherX V13.3", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")

""" + extract("def inject_css():", "OB1,OB2,OS1,OS2=53,60,-53,-60") + """

@st.cache_resource
def get_gemini_model():
    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel('gemini-2.5-flash')

""" + extract("def analyze(ticker,chart_days=252,refresh=False):", 'print("✅ V13.3 전체 완료!")') + '\nprint("✅ V13.3 전체 완료!")\n'

outputs = {
    "config.py": config_content,
    "utils.py": utils_content,
    "indicators.py": indicators_content,
    "engine.py": engine_content,
    "chart.py": chart_content,
    "ui.py": ui_content,
    "ai_agent.py": ai_agent_content,
    "app.py": app_new_content
}

for filename, text in outputs.items():
    with open(rf"c:\cipher\cipherX\{filename}", "w", encoding="utf-8") as f:
        f.write(text.strip() + "\n")

print("Splitting complete.")
