import MetaTrader5 as mt5
import pandas as pd



# General function to fetch data
def get_data(symbol: str, timeframe: int, start_pos: int, count: int) -> pd.DataFrame:
    if not mt5.initialize():
        raise RuntimeError("MT5 initialization failed (data/Fetcher)")
    """
    Fetches OHLCV data from MT5.

    Parameters:
        symbol (str): The symbol to fetch (e.g., "XAUUSD", "BTCUSD").
        timeframe (int): MT5 timeframe constant (e.g., mt5.TIMEFRAME_H1).
        start_pos (int): The starting position (0 = most recent candle).
        count (int): Number of candles to fetch.

    Returns:
        pd.DataFrame: OHLCV data with datetime index.
    """
    prices = mt5.copy_rates_from_pos(symbol, timeframe, start_pos, count)

    if prices is None or len(prices) == 0:
        raise ValueError(f"Failed to fetch data for {symbol} on timeframe {timeframe}")

    df = pd.DataFrame(prices)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.drop(columns=['spread', 'real_volume'], inplace=True)
    return df


def get_symbol_info(symbol):
    return mt5.symbol_info(symbol)._asdict()
