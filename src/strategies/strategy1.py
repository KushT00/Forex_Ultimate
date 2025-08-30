import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os
import json

# Add the src directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
log_dir = os.path.join(src_dir, "logs")
os.makedirs(log_dir, exist_ok=True)  # ensure logs folder exists
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


def check_if_signal_already_logged(log_file, new_signal):
    """Check if this exact signal (same timestamp) is already logged"""
    if not new_signal or new_signal.get("signal") in ["NO_DATA", "ERROR", "HOLD"]:
        return True
        
    existing_signals = load_existing_signals(log_file)
    
    for existing in existing_signals:
        if (existing.get("timestamp") == new_signal.get("timestamp") and 
            existing.get("signal") == new_signal.get("signal")):
            return True
    
    return False


def moving_average_crossover_strategy(symbol: str, timeframe: int, fast_period: int = 10, slow_period: int = 20):
    """
    Moving Average Crossover Strategy for 5-minute timeframe
    
    Parameters:
        symbol (str): Forex symbol (e.g., "XAUUSD", "EURUSD")
        timeframe (int): MT5 timeframe constant
        fast_period (int): Fast moving average period
        slow_period (int): Slow moving average period
    
    Returns:
        dict: Strategy signals and analysis
    """
    try:
        # Get data for analysis (need enough data for moving averages)
        df = get_data(symbol, timeframe, 0, slow_period + 10)
        
        if df.empty or len(df) < slow_period:
            return {"signal": "NO_DATA", "reason": "Insufficient data for analysis"}
        
        # Calculate moving averages
        df['fast_ma'] = df['close'].rolling(window=fast_period).mean()
        df['slow_ma'] = df['close'].rolling(window=slow_period).mean()
        
        # Get current and previous values
        current_fast = df['fast_ma'].iloc[-1]
        current_slow = df['slow_ma'].iloc[-1]
        prev_fast = df['fast_ma'].iloc[-2]
        prev_slow = df['slow_ma'].iloc[-2]
        
        # Check for crossover signals
        if pd.isna(current_fast) or pd.isna(current_slow) or pd.isna(prev_fast) or pd.isna(prev_slow):
            return {"signal": "NO_SIGNAL", "reason": "Moving averages not calculated yet"}
        
        # Bullish crossover: fast MA crosses above slow MA
        if prev_fast <= prev_slow and current_fast > current_slow:
            return {
                "strategy": "MA_Crossover",
                "signal": "BUY",
                "reason": f"Bullish MA crossover - Fast MA ({current_fast:.5f}) crossed above Slow MA ({current_slow:.5f})",
                "entry_price": float(df['close'].iloc[-1]),
                "fast_ma": float(current_fast),
                "slow_ma": float(current_slow),
                "timestamp": str(df.index[-1]),
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # Bearish crossover: fast MA crosses below slow MA
        elif prev_fast >= prev_slow and current_fast < current_slow:
            return {
                "strategy": "MA_Crossover",
                "signal": "SELL",
                "reason": f"Bearish MA crossover - Fast MA ({current_fast:.5f}) crossed below Slow MA ({current_slow:.5f})",
                "entry_price": float(df['close'].iloc[-1]),
                "fast_ma": float(current_fast),
                "slow_ma": float(current_slow),
                "timestamp": str(df.index[-1]),
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # No crossover
        else:
            trend = "BULLISH" if current_fast > current_slow else "BEARISH"
            return {
                "signal": "HOLD",
                "reason": f"No crossover - {trend} trend continues",
                "fast_ma": float(current_fast),
                "slow_ma": float(current_slow),
                "timestamp": str(df.index[-1])
            }
            
    except Exception as e:
        return {"signal": "ERROR", "reason": f"Strategy error: {str(e)}"}


# Example usage for testing
if __name__ == "__main__":
    log_file = os.path.join(log_dir, "strategy1.json")
    
    # Test the strategy
    result = moving_average_crossover_strategy("XAUUSD", mt5.TIMEFRAME_M5)
    print("Strategy Result:", result)
    
    # Only log if it's a BUY or SELL signal and not already logged
    if result and result.get("signal") in ["BUY", "SELL"] and not check_if_signal_already_logged(log_file, result):
        save_new_signal(log_file, result)
        print(f"New signal generated and logged: {result['signal']} - {result['reason']}")
        print(f"Signal details: Price: {result['entry_price']}, Fast MA: {result['fast_ma']:.5f}, Slow MA: {result['slow_ma']:.5f}")
    else:
        if result and result.get("signal") in ["NO_DATA", "ERROR"]:
            print(f"Strategy issue: {result['reason']}")
        elif result and result.get("signal") == "HOLD":
            print("No crossover detected - holding current position")
        else:
            print("No new signals generated or signal already exists in log.")
    
    # Show total signals in log
    all_signals = load_existing_signals(log_file)
    print(f"Total signals in log: {len(all_signals)}")