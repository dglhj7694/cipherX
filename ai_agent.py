import google.generativeai as genai
import streamlit as st
from config import *
from utils import _cs_str


def build_prompt_text(dc, meta):
    m = meta
    recent = dc.tail(60)
    prices = ", ".join([f"'{d.strftime('%m/%d')}:{r['Close']:.2f}'" for d, r in recent.iterrows()])
    vr = m['volume'] / max(m['avg_volume'], 1)

    price_block = (
        f"[A. Price]\n{prices}\n\n"
        f"Last=${m['price']:.2f} ({m['price_change_pct']:+.2f}%)\n"
        f"Volume={m['volume']:,.0f} ({vr:.1f}x)\n"
        f"ATR=${m['atr']:.2f} ({m['atr_pct']:.1f}%)\n"
    )

    ma_line = f"MA50=${m['ma50']:.2f}, MA200=${m['ma200']:.2f}" if m['ma50'] > 0 else "MA=N/A"
    vp_line = f"POC=${m['vp_poc']:.2f}, VAH=${m['vp_vah']:.2f}, VAL=${m['vp_val']:.2f}" if m['vp_poc'] > 0 else "VP=N/A"
    bb_line = f"BB_Up=${m.get('bb_up', 0):.2f}, BB_Low=${m.get('bb_low', 0):.2f}" if m.get('bb_up', 0) > 0 else ""
    smart_money_line = (
        f"SmartMoney: CMF={m['cmf']:.3f}, OBV={m.get('obv_trend', 'N/A')}, "
        f"OBV_Slope={m.get('obv_slope', 0):+.2f}, PriceSlope5={m.get('price_slope_5', 0):+.2%}, "
        f"Vol20={m.get('volume_ratio_20', 1):.2f}x, "
        f"BearDiv={'Y' if m.get('smart_money_bearish_div') else 'N'}, "
        f"BullDiv={'Y' if m.get('smart_money_bullish_div') else 'N'}"
    )
    structure_line = (
        f"Structure: BB%B={m.get('percent_b', .5):.2f}, {bb_line}\n"
        f"  {vp_line}\n"
        f"  LongRR={m.get('vp_long_rr', 1):.2f}, ShortRR={m.get('vp_short_rr', 1):.2f}\n"
        f"  {ma_line}"
    )
    indicator_block = (
        f"[B. Indicators]\n"
        f"Momentum: RSI={m['rsi']:.1f}, MFI={m['mfi']:.1f}, WT={m['wt1']:.1f}, "
        f"StK={m['stochk']:.1f}, SlK={m.get('slowk', 50):.1f}\n"
        f"Trend: ADX={m['adx']:.1f}, MACD_H={m['macd_hist']:.4f}, "
        f"UTBot={m.get('utbot_dir', 0)}, Hull={'up' if m.get('hma_rising') else 'down'}, "
        f"SqMom={m.get('squeeze_mom', 0):.3f}\n"
        f"{smart_money_line}\n"
        f"{structure_line}\n"
        f"RelativeStrength: RS={m['rs_ratio']:.3f}\n"
    )

    signal_lines = []
    for ir, row in dc.tail(20).iterrows():
        date_label = ir.strftime('%m/%d')
        day_signals = []
        for key, cfg in SIGNAL_REGISTRY.items():
            if row.get(key, False):
                day_signals.append(f"{cfg['dir']}:{cfg['kor']}")
        for key, cfg in COMBINED_SCAN_REGISTRY.items():
            if row.get(key, False):
                day_signals.append(f"{cfg['dir']}:{cfg['kor']}[T{cfg['tier']}]")
        if day_signals:
            signal_lines.append(f"  {date_label}: {', '.join(day_signals)}")
    signal_block = "[C. Signals]\n" + ("\n".join(signal_lines[-15:]) if signal_lines else "  (none)")

    committee = m.get('committee', {})
    committee_lines = []
    for name in COMMITTEE_NAMES:
        data = committee.get(name, {})
        icon = COMMITTEE_ICONS.get(name, '')
        committee_lines.append(
            f"    {icon}{name}: vote={data.get('vote', '?')} "
            f"score={data.get('score', 0):+.0f} conviction={data.get('conviction', 0):.0f}%"
        )
    buy_layers = ', '.join(f"{k}:{v:.1f}" for k, v in m['buy_layers'].items() if v > 0)
    sell_layers = ', '.join(f"{k}:{v:.1f}" for k, v in m['sell_layers'].items() if v > 0)
    contrast = m.get('contrast_notes', '') or 'None'
    review_block = (
        f"[D. Engine Review]\n"
        f"  Context={m.get('context_label', 'default')}\n"
        f"  Committees:\n" + "\n".join(committee_lines) + "\n"
        f"  ES={m.get('ensemble_score', 0):+.1f} (B{m.get('buy_agree', 0)}:S{m.get('sell_agree', 0)})\n"
        f"  Synergy={m.get('reversal_synergy', 0):+.1f} | Prediction={m.get('prediction_boost', 0):+.1f}\n"
        f"  Veto={m.get('veto_flags', 'none') or 'none'}\n"
        f"  Judgment={m['judgment']} ({m['confidence']:.0f}%)\n"
        f"  Reason={m.get('judgment_reason', '')}\n"
        f"  Detail={m.get('judgment_detail', '')}\n"
        f"  Action={m.get('action_label', '')}\n"
        f"  Contrast={contrast}\n"
        f"  BlowoffTop={'Y' if m.get('blowoff_top_hard') else 'N'}\n"
        f"  [10L] BUY={m['buy_total']:.1f} ({m['buy_active']}/10) [{buy_layers}] "
        f"SELL={m['sell_total']:.1f} ({m['sell_active']}/10) [{sell_layers}]\n"
        f"  Leading={m['leading_verdict']} | Lagging={m['lagging_verdict']}\n"
    )
    if m['combined_scans']:
        review_block += f"  CS={_cs_str(m['combined_scans'])}\n"

    return f"{price_block}\n{indicator_block}\n{signal_block}\n{review_block}"


def build_ai_prompt(ticker, phist, fund):
    return f"""
You are a veteran Wall Street analyst reviewing CipherX V14.2.
Write the entire report in Korean.

System context:
- CipherX V14.2 uses 5 committees: Trend, Momentum, Money, Structure, Leading
- It also uses context-aware weighting, veto logic, reversal synergy, prediction boost, and auto-generated reasons
- The input already contains smart-money divergence, RR (VAH/POC/VAL), and blow-off-top warnings

Non-negotiable rules:
1. Verify the system instead of echoing it.
2. If the system is bullish, actively search for bearish counter-evidence.
3. If the system is bearish, actively search for bullish counter-evidence.
4. You must include smart money interpretation using OBV, CMF, and volume.
5. You must include structure / risk-reward interpretation using VP levels (POC/VAH/VAL) and RR.
6. If low-volume breakout, money divergence, poor RR, or blow-off-top risk exists, mention it explicitly.
7. Add a section titled exactly `Contrast Analysis`.
8. In `Contrast Analysis`, provide exactly 2 devil's-advocate points.
9. At least one of the 2 points must reference either smart money divergence or RR / structure compression.
10. Do not restate the same bullish thesis inside `Contrast Analysis`.

Input data:
[{ticker}]
{phist}
[Fundamentals]
{fund}

Required output format:

### 1. Market Summary
- Summarize the latest tape, price behavior, and flow in 3-4 sentences.

### 2. Committee Audit
- Audit the committee votes, veto logic, ensemble score, and judgment quality.

### 3. Smart Money And Flow
- Explain OBV, CMF, volume quality, divergence, and whether money is confirming or fading price.

### 4. Structure And Risk/Reward
- Explain support/resistance, VP levels, upside/downside space, and whether RR is attractive.

### 5. Contrast Analysis
- Point 1
- Point 2

### 6. Scenario Plan
- Bullish scenario with trigger and target
- Base scenario
- Bearish scenario with invalidation and target
- Entry / stop / risk note

### Conclusion
- Final judgment in 2 sentences
- Include a simple grade (A-F)
"""
