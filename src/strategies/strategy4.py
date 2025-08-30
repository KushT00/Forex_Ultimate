import sys
import os
import json
import numpy as np
import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime, timedelta

# Add src to sys.path (for VS Code "Run File" mode)
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
log_dir = os.path.join(src_dir, "logs")
os.makedirs(log_dir, exist_ok=True)  # ensure log folder exists
sys.path.insert(0, src_dir)

from data.fetcher import get_data


def load_existing_signals(log_file):
    """Load existing signals from log file to track what's already been logged"""
    if os.path.exists(log_file):
        try:
            with open(log_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    return []


def save_new_signal(log_file, new_signal):
    """Append new signal to existing log file"""
    existing_signals = load_existing_signals(log_file)
    existing_signals.append(new_signal)
    
    with open(log_file, "w") as f:
        json.dump(existing_signals, f, indent=4)


def supertrend_rsi_strategy(symbol: str, timeframe: int,
                            atr_period: int = 10, factor: float = 3.0, rsi_period: int = 14,
                            days: int = 1):
    """
    Optimized Supertrend Strategy with RSI-based close signals.
    Now only returns the latest signal if it's new.

    Returns:
        dict or None: The latest strategy signal if it's new, otherwise None.
    """

    try:
        # How many candles do we need for X days
        # Roughly: candles_per_day = (24*60)/timeframe_in_minutes
        timeframe_minutes = {
            mt5.TIMEFRAME_M1: 1,
            mt5.TIMEFRAME_M5: 5,
            mt5.TIMEFRAME_M15: 15,
            mt5.TIMEFRAME_M30: 30,
            mt5.TIMEFRAME_H1: 60,
        }.get(timeframe, 15)  # default 15 min

        candles_needed = int((24 * 60 / timeframe_minutes) * days) + atr_period + rsi_period + 20
        df = get_data(symbol, timeframe, 0, candles_needed)

        if df.empty or len(df) < atr_period + rsi_period:
            return {"signal": "NO_DATA", "reason": "Insufficient candles"}

        # --- ATR ---
        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(atr_period).mean()

        # --- Supertrend ---
        hl2 = (high + low) / 2
        upperband = hl2 + (factor * atr)
        lowerband = hl2 - (factor * atr)

        supertrend = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(index=df.index, dtype=int)

        supertrend.iloc[0] = hl2.iloc[0]
        direction.iloc[0] = 1

        for i in range(1, len(df)):
            if close.iloc[i] > supertrend.iloc[i - 1]:
                supertrend.iloc[i] = max(lowerband.iloc[i], supertrend.iloc[i - 1])
                direction.iloc[i] = 1
            else:
                supertrend.iloc[i] = min(upperband.iloc[i], supertrend.iloc[i - 1])
                direction.iloc[i] = -1

        df["supertrend"] = supertrend
        df["direction"] = direction

        # --- RSI ---
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(rsi_period).mean()
        loss = -delta.where(delta < 0, 0).rolling(rsi_period).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))

        # --- Check only the latest candle for new signals ---
        if len(df) < 2:
            return None
            
        last = df.iloc[-1]  # Latest candle
        prev = df.iloc[-2]  # Previous candle

        signal_data = None

        # Updated signal names: BUY instead of CALL_SHORT, SELL instead of PUT_SHORT
        if prev["direction"] <= 0 and last["direction"] > 0:
            signal_data = {
                "strategy": "Supertrend+RSI",
                "signal": "BUY",
                "reason": "Trend changed to UP",
            }

        elif prev["direction"] >= 0 and last["direction"] < 0:
            signal_data = {
                "strategy": "Supertrend+RSI",
                "signal": "SELL",
                "reason": "Trend changed to DOWN",
            }

        elif prev["rsi"] > 70 and last["rsi"] < 70:
            signal_data = {
                "strategy": "Supertrend+RSI",
                "signal": "CLOSE",
                "reason": f"RSI crossed below 70 - RSI: {last['rsi']:.2f}",
            }

        elif prev["rsi"] < 30 and last["rsi"] > 30:
            signal_data = {
                "strategy": "Supertrend+RSI",
                "signal": "CLOSE",
                "reason": f"RSI crossed above 30 - RSI: {last['rsi']:.2f}",
            }

        if signal_data:
            # Add details
            signal_data.update({
                "entry_price": float(last["close"]),
                "rsi_value": float(last["rsi"]),
                "timestamp": str(last["time"]),
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            return signal_data

        return None

    except Exception as e:
        return {"signal": "ERROR", "reason": f"Strategy error: {str(e)}"}


def check_if_signal_already_logged(log_file, new_signal):
    """Check if this exact signal (same timestamp) is already logged"""
    if not new_signal or new_signal.get("signal") in ["NO_DATA", "ERROR"]:
        return True
        
    existing_signals = load_existing_signals(log_file)
    
    for existing in existing_signals:
        if (existing.get("timestamp") == new_signal.get("timestamp") and 
            existing.get("signal") == new_signal.get("signal")):
            return True
    
    return False


if __name__ == "__main__":
    log_file = os.path.join(log_dir, "strategy4.json")
    
    # Get the latest signal
    result = supertrend_rsi_strategy("XAUUSD", mt5.TIMEFRAME_M15)
    
    if result and not check_if_signal_already_logged(log_file, result):
        # Only save if we have a new signal
        save_new_signal(log_file, result)
        print(f"New signal generated and logged: {result['signal']} - {result['reason']}")
        print(f"Signal details: Price: {result['entry_price']}, RSI: {result['rsi_value']:.2f}, Time: {result['timestamp']}")
    else:
        if result and result.get("signal") in ["NO_DATA", "ERROR"]:
            print(f"Strategy issue: {result['reason']}")
        else:
            print("No new signals generated or signal already exists in log.")
    
    # Show total signals in log
    all_signals = load_existing_signals(log_file)
    print(f"Total signals in log: {len(all_signals)}")