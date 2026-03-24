import re
import os

def clean_file(path, replacements):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        for ptrn, repl in replacements:
            if callable(repl):
                pass # not handling callables in this simple version
            else:
                content = re.sub(ptrn, repl, content)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Cleaned {path}")
    except Exception as e:
        print(f"Error cleaning {path}: {e}")

base_dir = r"c:\cipher\cipherX"

config_replacements = [
    (r"(_sig\([^,]+,\s*[a-zA-Z_]+,\s*)'[^']*'(\s*,)", r"\1''\2"),
    (r"('icon'\s*:\s*)'[^']*'", r"\1''"),
    (r"COMMITTEE_ICONS\s*=\s*\{[^\}]+\}", r"COMMITTEE_ICONS = {}"),
]
clean_file(os.path.join(base_dir, 'config.py'), config_replacements)

engine_replacements = [
    (r"강력매수 🟢🟢🟢", "STRONG BUY"),
    (r"강력매도 🔴🔴🔴", "STRONG SELL"),
    (r"매수 🟢🟢", "BUY"),
    (r"매도 🔴🔴", "SELL"),
    (r"단기매수 관찰 🟡🟢", "WATCH BUY"),
    (r"단기매도 관찰 🟡🔴", "WATCH SELL"),
    (r"중립/관망 ⚪", "NEUTRAL"),
    (r"관망/대기 🟠", "MIXED"),
]
clean_file(os.path.join(base_dir, 'engine.py'), engine_replacements)
