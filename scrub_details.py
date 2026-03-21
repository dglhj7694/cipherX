import re

with open(r'c:\cipher\cipherX\company_details.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Emoji scrubs
reps = {
    "🌱 1단계 : ": "[STAGE 1] ",
    "🚀 2단계 : ": "[STAGE 2] ",
    "📈 3단계 : ": "[STAGE 3] ",
    "💪 4단계 : ": "[STAGE 4] ",
    "💰 5단계 : ": "[STAGE 5] ",
    "⏸️ 6단계 : ": "[STAGE 6] ",
    "📉 7단계 : ": "[STAGE 7] ",
    "🔧 8단계 : ": "[STAGE 8] ",
    "✅": "[PASS]",
    "⚠️": "[WARN]",
    "❌": "[FAIL]",
    "🚀": "[SURGE]",
    "📈": "[UP]",
    "📉": "[DOWN]",
    "➡️": "[FLAT]",
    "🔥": "[HOT]",
    "🐌": "[SLOW]",
    "💰": "[CASH]",
    "📊 ": "",
    "📡 ": "",
    "🏢 ": "",
    "💵 ": "",
    "📌": "[SYS]",
    "1️⃣ ": "01 ",
    "2️⃣ ": "02 ",
    "3️⃣ ": "03 ",
    "4️⃣ ": "04 ",
    "5️⃣ ": "05 ",
    "6️⃣ ": "06 ",
    "7️⃣ ": "07 ",
    "8️⃣ ": "08 "
}

for k, v in reps.items():
    text = text.replace(k, v)

# 2. Fix _traffic_light and _score_dot_row
search_traffic = '''def _traffic_light(status):
    m = {"green": "🟢", "yellow": "🟡", "red": "🔴", "blue": "🔵", "gray": "⚪"}
    return m.get(status, "⚪")'''

replace_traffic = '''def _traffic_light(status):
    return "■"'''

text = text.replace(search_traffic, replace_traffic)

search_dot_row = '''def _score_dot_row(items):
    cells = ""
    for name, color in items:
        cells += (f'<div style="display:inline-flex;flex-direction:column;align-items:center; min-width:60px;padding:6px 4px">'
                  f'<span style="font-size:1.2rem">{_traffic_light(color)}</span>'
                  f'<span style="font-size:.75rem;font-weight:700;color:#c9d1d9;margin-top:4px; text-align:center;line-height:1.2">{name}</span></div>')
    return f'<div style="display:flex;flex-wrap:wrap;justify-content:center;gap:4px;margin:12px 0">{cells}</div>\''''

replace_dot_row = '''def _score_dot_row(items):
    cells = ""
    colors_map = {"green": "#00E676", "yellow": "#FFC107", "red": "#FF1744", "blue": "#2196F3", "gray": "#8b949e"}
    for name, color in items:
        c_code = colors_map.get(color, "#8b949e")
        cells += (f'<div style="display:inline-flex;flex-direction:column;align-items:center; min-width:60px;padding:6px 4px">'
                  f'<span style="font-size:1.4rem;color:{c_code}">■</span>'
                  f'<span style="font-size:.75rem;font-weight:700;color:#94a3b8;margin-top:2px; text-align:center;line-height:1.2">{name}</span></div>')
    return f'<div style="display:flex;flex-wrap:wrap;justify-content:center;gap:4px;margin:12px 0">{cells}</div>\''''

text = text.replace(search_dot_row, replace_dot_row)

with open(r'c:\cipher\cipherX\company_details.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Scrubbed emojis and updated traffic lights in company_details.py")
