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

def rsi_divergence_strategy(symbol: str, timeframe: int, rsi_period: int = 14, lookback: int = 10):
    """
    RSI Divergence Strategy for 5-minute timeframe
    
    Parameters:
        symbol (str): Forex symbol (e.g., "XAUUSD", "EURUSD")
        timeframe (int): MT5 timeframe constant
        rsi_period (int): RSI calculation period
        lookback (int): Number of candles to look back for divergence
    
    Returns:
        dict: Strategy signals and analysis
    """
    try:
        # Get data for analysis (need enough data for RSI and divergence detection)
        df = get_data(symbol, timeframe, 0, rsi_period + lookback + 10)
        
        if df.empty or len(df) < rsi_period + lookback:
            return {"signal": "NO_DATA", "reason": "Insufficient data for analysis"}
        
        # Calculate RSI on entire dataset for better accuracy
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period, min_periods=1).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Fill any remaining NaN values with the first valid RSI value
        if df['rsi'].isna().any():
            first_valid_rsi = df['rsi'].dropna().iloc[0]
            df['rsi'] = df['rsi'].fillna(first_valid_rsi)
        
        # Get recent data for divergence analysis
        recent_data = df.tail(lookback + 5)
        
        if len(recent_data) < 5:
            return {"signal": "NO_SIGNAL", "reason": "Not enough recent data for divergence analysis"}
        
        # Find peaks and troughs in price and RSI
        price_peaks = []
        price_troughs = []
        rsi_peaks = []
        rsi_troughs = []
        
        for i in range(2, len(recent_data) - 2):
            # Price peaks (higher highs)
            if (recent_data['high'].iloc[i] > recent_data['high'].iloc[i-1] and 
                recent_data['high'].iloc[i] > recent_data['high'].iloc[i-2] and
                recent_data['high'].iloc[i] > recent_data['high'].iloc[i+1] and
                recent_data['high'].iloc[i] > recent_data['high'].iloc[i+2]):
                price_peaks.append((i, recent_data['high'].iloc[i]))
            
            # Price troughs (lower lows)
            if (recent_data['low'].iloc[i] < recent_data['low'].iloc[i-1] and 
                recent_data['low'].iloc[i] < recent_data['low'].iloc[i-2] and
                recent_data['low'].iloc[i] < recent_data['low'].iloc[i+1] and
                recent_data['low'].iloc[i] < recent_data['low'].iloc[i+2]):
                price_troughs.append((i, recent_data['low'].iloc[i]))
            
            # RSI peaks
            if (recent_data['rsi'].iloc[i] > recent_data['rsi'].iloc[i-1] and 
                recent_data['rsi'].iloc[i] > recent_data['rsi'].iloc[i-2] and
                recent_data['rsi'].iloc[i] > recent_data['rsi'].iloc[i+1] and
                recent_data['rsi'].iloc[i] > recent_data['rsi'].iloc[i+2]):
                rsi_peaks.append((i, recent_data['rsi'].iloc[i]))
            
            # RSI troughs
            if (recent_data['rsi'].iloc[i] < recent_data['rsi'].iloc[i-1] and 
                recent_data['rsi'].iloc[i] < recent_data['rsi'].iloc[i-2] and
                recent_data['rsi'].iloc[i] < recent_data['rsi'].iloc[i+1] and
                recent_data['rsi'].iloc[i] < recent_data['rsi'].iloc[i+2]):
                rsi_troughs.append((i, recent_data['rsi'].iloc[i]))
        
        # Check for divergences
        if len(price_peaks) >= 2 and len(rsi_peaks) >= 2:
            # Bearish divergence: Price makes higher highs, RSI makes lower highs
            if (price_peaks[-1][1] > price_peaks[-2][1] and 
                rsi_peaks[-1][1] < rsi_peaks[-2][1]):
                return {
                    "signal": "SELL",
                    "reason": "Bearish RSI divergence detected - Price higher highs, RSI lower highs",
                    "entry_price": recent_data['close'].iloc[-1],
                    "rsi_value": recent_data['rsi'].iloc[-1],
                    "timestamp": recent_data.index[-1]
                }
        
        if len(price_troughs) >= 2 and len(rsi_troughs) >= 2:
            # Bullish divergence: Price makes lower lows, RSI makes higher lows
            if (price_troughs[-1][1] < price_troughs[-2][1] and 
                rsi_troughs[-1][1] > rsi_troughs[-2][1]):
                return {
                    "signal": "BUY",
                    "reason": "Bullish RSI divergence detected - Price lower lows, RSI higher lows",
                    "entry_price": recent_data['close'].iloc[-1],
                    "rsi_value": recent_data['rsi'].iloc[-1],
                    "timestamp": recent_data.index[-1]
                }
        
        # Check for overbought/oversold conditions
        current_rsi = recent_data['rsi'].iloc[-1]
        if current_rsi > 70:
            return {
                "signal": "SELL",
                "reason": f"Overbought condition - RSI: {current_rsi:.2f}",
                "entry_price": recent_data['close'].iloc[-1],
                "rsi_value": current_rsi,
                "timestamp": recent_data.index[-1]
            }
        elif current_rsi < 30:
            return {
                "signal": "BUY",
                "reason": f"Oversold condition - RSI: {current_rsi:.2f}",
                "entry_price": recent_data['close'].iloc[-1],
                "rsi_value": current_rsi,
                "timestamp": recent_data.index[-1]
            }
        
        # No clear signal
        return {
            "signal": "HOLD",
            "reason": f"No divergence or extreme RSI - Current RSI: {current_rsi:.2f}",
            "rsi_value": current_rsi,
            "timestamp": recent_data.index[-1]
        }
            
    except Exception as e:
        return {"signal": "ERROR", "reason": f"Strategy error: {str(e)}"}

# Example usage for testing
if __name__ == "__main__":
    # Test the strategy
    result = rsi_divergence_strategy("EURUSD", mt5.TIMEFRAME_M5)
    print("Strategy Result:", result)
