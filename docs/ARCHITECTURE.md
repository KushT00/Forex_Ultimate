# ARCHITECTURE.md

## Overview

This project is an **algorithmic trading framework** designed around modular **agents**. Each agent has a well-defined responsibility (strategy execution, signal logging, notification, supervision, etc.), enabling flexible scaling and maintainability.

The system can deploy multiple option-selling strategies simultaneously, monitor their outputs, log all signals, and optionally send real-time notifications (WhatsApp/Telegram via Twilio).

## Core Components

### 1. **Strategy Agents**

* Each trading strategy is encapsulated in its own **agent**.
* Example:
  * `strategy_supertrend.py`
  * `strategy_straddle.py`
  * `strategy_customN.py`
* Responsibilities:
  * Fetch market data.
  * Apply indicator logic.
  * Generate trade signals (BUY/SELL, entry price, time).
  * Pass signals to the **logging agent** and optionally trigger **notifier**.

### 2. **Logging Agent**

* Dedicated to recording all strategy outputs in a structured manner.
* Logs are stored under the `logs/` folder with sub-folders by **timeframe** or **strategy** (configurable).
* Example structure:

```
logs/
  ├── strategy1.txt
  ├── strategy2.txt
  ├── TF_30min/
  │     └── signals.txt
```

* Ensures every trade decision is auditable.
* Acts as the central "source of truth" for signals.

### 3. **Notification Agent**

* Handles trade alerts via **WhatsApp or Telegram**.
* Uses **Twilio API** for message delivery.
* Can work in two modes:
  1. **Direct trigger**: strategy agent calls `notifier.send(signal)` whenever a new signal is generated.
  2. **Watcher mode**: runs in the background, watches `logs/` for new entries, and pushes notifications.
* Parameters passed: `{symbol, entry_price, signal_type, timestamp}`.

### 4. **Supervisor Agent**

* (Optional, future-facing)
* Oversees multiple running strategy agents.
* Maintains a dashboard of active strategies, open signals, and system health.
* Could later integrate **risk management rules** (e.g., "don't open more than 3 positions at once").

### 5. **Configuration**

* A `pyproject.toml` (or `config.yaml`) file defines:
  * List of active strategies.
  * Timeframes.
  * Logging preferences (per-strategy / per-timeframe).
  * Notification settings (WhatsApp, Telegram, none).

## Folder Structure

```
project-root/
│
├── agents/                   # All agents live here
│   ├── strategy_agents/
│   │   ├── strategy_supertrend.py
│   │   ├── strategy_straddle.py
│   │   └── ...
│   ├── logging_agent.py
│   ├── notification_agent.py
│   └── supervisor_agent.py
│
├── logs/                     # Signal logs (auto-created dynamically)
│   ├── strategy1.txt
│   ├── strategy2.txt
│   ├── TF_30min/
│   │   └── signals.txt
│   └── ...
│
├── config/                   # Configuration files
│   ├── config.yaml
│   └── strategies_config.json
│
├── utils/                    # Common helper functions
│   └── file_utils.py
│
├── pyproject.toml            # Project dependencies & metadata
├── ARCHITECTURE.md           # This file
└── README.md                 # Project intro & usage guide
```

## Workflow

1. **Strategy Agent runs** → fetches data, applies logic.
2. If **signal is generated** →
   * Sent to **Logging Agent** → appended to proper file in `logs/`.
   * Sent to **Notification Agent** (if enabled) → user alert.
3. **Supervisor Agent** (optional) monitors all activity and enforces higher-level rules.

## Advantages of Agent-Based Design

* **Modularity** → easy to add/remove strategies.
* **Scalability** → each agent can run independently.
* **Flexibility** → notifications, logging, and supervision can evolve separately.
* **Maintainability** → clear separation of responsibilities.

## Future Improvements

* Add **Supervisor Agent** with real-time dashboard.
* Integrate database (PostgreSQL / Supabase) for better signal querying.
* Risk management module within Supervisor Agent.
* Performance analytics and strategy comparison tools.
* Multi-broker support through dedicated broker agents.