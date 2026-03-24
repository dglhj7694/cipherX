# Workspace Organization (2026-03-24)

## 1) Current Runtime (used by `app.py`)
- `app.py` (main Streamlit entrypoint)
- `engine.py` (signal engine)
- `indicators.py` (indicator calculations)
- `config.py` (signal/scan registry constants)
- `utils.py` (utility + cache helpers)
- `chart.py` (chart builder)
- `ui.py` (analysis UI renderer)
- `ai_agent.py` (AI prompt builders)
- `company_details.py` (company profile UI section)
- `sectors.py` (scanner sector groups)

## 2) Archived / Utility files moved out of root
- `legacy/apps/app_v15.py`
- `tools/refactor/split_refactor.py`
- `tools/refactor/split_refactor_v15.py`
- `tools/maintenance/clean_emojis.py`
- `tools/maintenance/revert_emojis.py`
- `tools/maintenance/scrub_details.py`
- `tests/manual/test_signal_flip.py`

## 3) Recommended run command
```powershell
streamlit run app.py
```

Manual signal-flip check:
```powershell
python tests/manual/test_signal_flip.py
```

## 4) Next cleanup candidates (optional)
- Keep a single app entry (`app.py`) and freeze old versions only under `legacy/`.
- Add a small smoke test for import/runtime sanity.
