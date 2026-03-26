# SIGL Brand Guide

## Core Identity
- Canonical syntax: `[ SIGL ]`
- Hidden meaning: `Signal`
- Tone: premium signal terminal, LED logboard, disciplined and alive
- Rule: no visible version text on user-facing surfaces

## Header System
- The main header is a LED logboard, not a marketing hero.
- Structure:
  - top rail with `MODE`, `STATUS`, `FEED`, and analysis log count
  - left log wall filled by recent analyzed tickers
  - right terminal fields for the current focus ticker
  - bottom ticker strip that keeps moving through recent board items
- The sidebar acts only as a control panel and does not render the brand board.

## Data Rules
- `history_rows` comes from real `analysis` messages in session history.
- Each log row uses `TIME / TICKER / SIGNAL / ES / CTX`.
- `focus_recent_signals` comes from `meta.recent_signals` when available.
- `focus_stack_summary` prioritizes:
  - `B:S` agreement
  - top combined scans
  - veto flags
  - lead/lag verdict fallback
- The ticker strip prefers:
  - recent analysis log summaries
  - current focus recent signals
  - scanner results as fallback

## Visual Rules
- Base typography stays mono for labels and data.
- Ticker codes and key numbers use a segmented LED-style treatment.
- The board uses:
  - dot-matrix texture
  - CRT scanline overlay
  - subtle bloom on key text
  - afterimage on ticker strip text
- Motion includes:
  - strong pulse on the status dot
  - slow sweep light across the board
  - one-time flash on the newest log row
  - continuous ticker movement
- `prefers-reduced-motion` keeps the board readable and reduces the stronger effects.
