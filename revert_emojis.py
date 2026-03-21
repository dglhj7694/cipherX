import re

with open(r'c:\cipher\cipherX\engine.py', 'r', encoding='utf-8') as f:
    res = f.read()

res = res.replace('"STRONG BUY"', '"강력매수 🟢🟢🟢"')
res = res.replace('"STRONG SELL"', '"강력매도 🔴🔴🔴"')
res = res.replace(',"BUY"', ',"매수 🟢🟢"')
res = res.replace(',"SELL"', ',"매도 🔴🔴"')
res = res.replace('"WATCH BUY"', '"단기매수 관찰 🟡🟢"')
res = res.replace('"WATCH SELL"', '"단기매도 관찰 🟡🔴"')
res = res.replace('"NEUTRAL"', '"중립/관망 ⚪"')
res = res.replace('"MIXED"', '"관망/대기 🟠"')

with open(r'c:\cipher\cipherX\engine.py', 'w', encoding='utf-8') as f:
    f.write(res)
print('Reverted emojis in engine.py')
