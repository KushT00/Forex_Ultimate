import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add the src directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
sys.path.insert(0, src_dir)

from data.fetcher import get_data

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
                "signal": "BUY",
                "reason": f"Bullish MA crossover - Fast MA ({current_fast:.5f}) crossed above Slow MA ({current_slow:.5f})",
                "entry_price": df['close'].iloc[-1],
                "fast_ma": current_fast,
                "slow_ma": current_slow,
                "timestamp": df.index[-1]
            }
        
        # Bearish crossover: fast MA crosses below slow MA
        elif prev_fast >= prev_slow and current_fast < current_slow:
            return {
                "signal": "SELL",
                "reason": f"Bearish MA crossover - Fast MA ({current_fast:.5f}) crossed below Slow MA ({current_slow:.5f})",
                "entry_price": df['close'].iloc[-1],
                "fast_ma": current_fast,
                "slow_ma": current_slow,
                "timestamp": df.index[-1]
            }
        
        # No crossover
        else:
            trend = "BULLISH" if current_fast > current_slow else "BEARISH"
            return {
                "signal": "HOLD",
                "reason": f"No crossover - {trend} trend continues",
                "fast_ma": current_fast,
                "slow_ma": current_slow,
                "timestamp": df.index[-1]
            }
            
    except Exception as e:
        return {"signal": "ERROR", "reason": f"Strategy error: {str(e)}"}

# Example usage for testing
if __name__ == "__main__":
    # Test the strategy
    result = moving_average_crossover_strategy("XAUUSD", mt5.TIMEFRAME_M5)
    print("Strategy Result:", result)
