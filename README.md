# Tower-Lite FX (Virtual Advisory System)

A modular, open-ended Forex research & advisory platform inspired by HFT/prop desks.
It **does not execute trades**; it simulates signals, virtual fills, risk, and PnL.
Manager Agent is your chat interface that coordinates Trader, Risk, and (optional) News Agents.

## Quick Start (dev)
- Create a venv, then: `pip install -r requirements.txt`
- Copy `configs/example.config.yaml` to `configs/config.yaml` and edit.
- Run a quick smoke test: `python scripts/run_smoke.py`
- Start API for the Manager: `uvicorn tower_lite_fx.api.app:app --reload`

## Modules
See `docs/ARCHITECTURE.md` (or this README sections) for an overview.
