# SIGL Brand Guide

## Core Identity
- Canonical syntax: `[ SIGL ]`
- Hidden meaning: `Signal`
- Read order: ticker code first, meaning second
- Tone: terminal-like, sharp, premium, restrained
- Rule: no visible version text on user-facing surfaces

## Header System
- The header should feel like a premium trading terminal, not a marketing hero.
- Structure:
  - left: `[ SIGL ]` banner
  - top line: `STATUS: ... | FEED: ...` with one slow pulse indicator
  - right: six terminal tiles for `MODE`, `TARGET`, `ES`, `SIGNAL`, `CTX`, `SPAN`
  - bottom: scrolling ticker strip
- Sidebar uses the same system in a compact mini-board layout.

## Data Rules
- Tiles must be backed by real app state when available.
- Analysis defaults:
  - `TARGET WAIT`
  - `ES --`
  - `SIGNAL IDLE`
  - `CTX STANDBY`
  - `SPAN 6M`
- The ticker strip should prefer:
  - recent analyzed tickers from app history
  - current scan results
  - branded placeholders only as a final fallback

## Copy Voice
- Keep the terminal voice strong in chrome, status text, and short action labels.
- Preferred phrases:
  - `READING THE TAPE`
  - `DATA FEED ESTABLISHED`
  - `SIGNAL READY`
  - `QUANT AUDIT`
- Keep long-form Korean analysis explanations readable and mostly unchanged.

## Visual Rules
- Use mono typography for brand syntax, tiles, status line, and ticker tape.
- Motion stays restrained:
  - slow pulse indicator
  - continuous marquee strip
- Avoid fake exchange claims such as `LIVE_NASDAQ`.
- Avoid alternate brand syntaxes such as `$SIGL`, `SIGL:US`, or `SIGL.PRO`.
