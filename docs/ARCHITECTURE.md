# ARCHITECTURE.md

## Overview

This project is an **algo-trading system** designed for executing and managing multiple trading strategies (e.g., Supertrend, Straddle, etc.) across different timeframes. The system is modular, scalable, and built around three core components:

1. **Strategies** – individual trading logic modules.
2. **Logging** – structured storage of trade signals and activity.
3. **Notifier** – real-time notifications (via WhatsApp/Telegram using Twilio).

## Folder Structure

```
project-root/
│
├── strategies/               # All trading strategies live here
│   ├── supertrend.py
│   ├── straddle.py
│   └── ...
│
├── logs/                     # Signal logs (auto-created dynamically)
│   ├── Supertrend/
│   │   ├── 5min.txt
│   │   ├── 15min.txt
│   │   └── ...
│   ├── Straddle/
│   │   ├── 30min.txt
│   │   └── ...
│   └── ...
│
├── notifier/                 # Notification utilities
│   └── notifier.py
│
├── scheduler/                # Orchestration layer
│   └── scheduler.py
│
├── utils/                    # Common helper functions (e.g., time, config mgmt)
│   └── file_utils.py
│
├── pyproject.toml            # Project dependencies & metadata
├── ARCHITECTURE.md           # This file
└── README.md                 # Project intro & usage guide
```

## Core Components

### 1. **Strategies**

* Each strategy is implemented as a Python function inside `strategies/`.
* Strategy functions take parameters such as:
  * `symbol`
  * `timeframe`
  * `capital`
* At the end of execution:
  * A signal (if generated) is logged into the respective log file.
  * The notifier function is called to push notifications.

**Example:**

```python
def supertrend(symbol, timeframe, capital):
    # trading logic...
    if signal_generated:
        log_signal("Supertrend", timeframe, signal_data)
        send_notification(signal_data)
```

### 2. **Logging**

* Signals are stored under the `logs/` folder.
* Folder names correspond to strategy names.
* Inside each strategy folder, signals are stored in `{timeframe}.txt`.

**Example:**

```
logs/Supertrend/5min.txt
logs/Supertrend/15min.txt
logs/Straddle/30min.txt
```

* Log format is structured (e.g., JSON lines or CSV-style text):

```
2025-08-30 09:15:00 | SYMBOL: NIFTY | SIGNAL: CALL SHORT | ENTRY: 20050
```

### 3. **Notifier**

* Located in `notifier/notifier.py`.
* Provides a `send_notification(signal_data)` function.
* Supports **WhatsApp/Telegram notifications** via Twilio.
* Called at the end of each strategy function after a signal is generated.

### 4. **Scheduler**

* `scheduler/scheduler.py` is responsible for running strategies at fixed intervals.
* Uses `APScheduler` or `cron` jobs to schedule execution.
* Dynamically calls strategies with specified parameters.

**Example:**

```python
schedule.every(5).minutes.do(supertrend, symbol="NIFTY", timeframe="5min", capital=100000)
```

## Execution Flow

1. **Scheduler** triggers a strategy at the defined interval.
2. **Strategy function** executes trading logic.
3. If a signal is generated:
   * **Log** is written under the respective `logs/strategy/timeframe.txt`.
   * **Notifier** is triggered to send real-time alerts.

## Future Improvements

* Add database (PostgreSQL / Supabase) instead of plain text logs for better querying.
* Central monitoring dashboard for signals & performance.
* Risk management module (stop-loss, portfolio allocation).
* Analytics on strategy performance.