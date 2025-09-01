import time
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import sys
import os
import threading
from concurrent.futures import ThreadPoolExecutor
import logging
import json
from logging.handlers import RotatingFileHandler

# Add src to path for imports - more robust path handling
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(src_dir)

# Add both src and project root to path
sys.path.insert(0, src_dir)
sys.path.insert(0, project_root)

from strategies.strategy1 import moving_average_crossover_strategy
from strategies.strategy2 import rsi_divergence_strategy
from strategies.strategy4 import supertrend_rsi_strategy

def setup_logging():
    """Setup logging with rotation to keep only last 100 entries"""
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(src_dir, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Configure logging with rotation
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler(
                os.path.join(logs_dir, 'trading_system.log'), 
                maxBytes=1024*1024,  # 1MB per file
                backupCount=5,        # Keep 5 backup files
                encoding='utf-8'
            ),
            logging.StreamHandler()
        ]
    )
    
    # Reduce noise from schedule library
    logging.getLogger('schedule').setLevel(logging.WARNING)
    
    # Add custom log rotation to keep only last 100 entries
    def rotate_logs():
        log_file = os.path.join(logs_dir, 'trading_system.log')
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Keep only the last 100 log entries
                if len(lines) > 100:
                    with open(log_file, 'w', encoding='utf-8') as f:
                        f.writelines(lines[-100:])
                    logging.info(f"Log rotated: Kept last 100 entries, removed {len(lines) - 100} old entries")
            except Exception as e:
                logging.error(f"Log rotation failed: {str(e)}")
    
    # Rotate logs every hour
    def schedule_log_rotation():
        while True:
            time.sleep(3600)  # Wait 1 hour
            rotate_logs()
    
    # Start log rotation in background thread
    rotation_thread = threading.Thread(target=schedule_log_rotation, daemon=True)
    rotation_thread.start()
    
    return logs_dir

class MultiTimeframeScheduler:
    """Multi-threaded scheduler for different timeframe strategies"""
    
    def __init__(self, logs_dir: str):
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.running = True
        self.strategies = {}
        self.logs_dir = logs_dir
        self.trade_log_file = os.path.join(self.logs_dir, 'trade_log.json')
        
        # Create logs directory if it doesn't exist
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # Initialize trade log file if it doesn't exist
        if not os.path.exists(self.trade_log_file):
            with open(self.trade_log_file, 'w') as f:
                json.dump([], f)
    
    def log_trade(self, trade_data: dict):
        """Log trade data to JSON file"""
        try:
            # Read existing trades
            with open(self.trade_log_file, 'r') as f:
                trades = json.load(f)
            
            # Add new trade with timestamp
            trade_data['logged_at'] = datetime.now().isoformat()
            trades.append(trade_data)
            
            # Write back to file
            with open(self.trade_log_file, 'w') as f:
                json.dump(trades, f, indent=2)
                
            logging.info(f"Trade logged: {trade_data['signal']} for {trade_data['symbol']}")
            
        except Exception as e:
            logging.error(f"Failed to log trade: {str(e)}")
    
    def add_strategy(self, name: str, strategy_func, symbols: list, timeframe_minutes: int):
        """Add a strategy to the scheduler"""
        self.strategies[name] = {
            'function': strategy_func,
            'symbols': symbols,
            'timeframe': timeframe_minutes,
            'last_run': None
        }
        logging.info(f"Added strategy: {name} for {timeframe_minutes}min timeframe")
    
    def is_candle_closed(self, timeframe_minutes: int) -> bool:
        """Check if the current time is at a candle closure point"""
        now = datetime.now()
        minutes_since_midnight = now.hour * 60 + now.minute
        return minutes_since_midnight % timeframe_minutes == 0
    
    def get_next_candle_time(self, timeframe_minutes: int) -> datetime:
        """Get the next candle closure time"""
        now = datetime.now()
        minutes_since_midnight = now.hour * 60 + now.minute
        minutes_until_next = timeframe_minutes - (minutes_since_midnight % timeframe_minutes)
        
        if minutes_until_next == 0:
            minutes_until_next = timeframe_minutes
        
        return now + timedelta(minutes=minutes_until_next)
    
    def run_strategy_threaded(self, strategy_name: str):
        """Run a strategy in a separate thread"""
        try:
            logging.info(f"=== {strategy_name}: FUNCTION CALLED ===")
            
            strategy_info = self.strategies[strategy_name]
            strategy_func = strategy_info['function']
            symbols = strategy_info['symbols']
            timeframe = strategy_info['timeframe']
            
            logging.info(f"=== {strategy_name}: Checking candle closure for {timeframe}min timeframe ===")
            
            # Check if candle is closed before running strategy
            if not self.is_candle_closed(timeframe):
                logging.info(f"{strategy_name}: SKIPPING - {timeframe}-minute candle not closed yet")
                return
            
            logging.info(f"*** {strategy_name}: EXECUTING on {timeframe}-minute timeframe at {datetime.now()} ***")
            
            # Run strategy on all symbols
            for symbol in symbols:
                try:
                    result = strategy_func(symbol, self._get_mt5_timeframe(timeframe))
                    
                    # Prepare trade data for logging
                    trade_data = {
                        'strategy_name': strategy_name,
                        'symbol': symbol,
                        'timeframe_minutes': timeframe,
                        'candle_close_time': datetime.now().isoformat(),
                        'signal': result.get('signal', 'UNKNOWN'),
                        'reason': result.get('reason', 'No reason provided'),
                        'entry_price': result.get('entry_price', None),
                        'timestamp': result.get('timestamp', None)
                    }
                    
                    # Add strategy-specific data
                    if 'fast_ma' in result:
                        trade_data['fast_ma'] = result['fast_ma']
                        trade_data['slow_ma'] = result['slow_ma']
                    if 'rsi_value' in result:
                        trade_data['rsi_value'] = result['rsi_value']
                    
                    # Log the trade data
                    if result["signal"] in ["BUY", "SELL"]:
                        self.log_trade(trade_data)
                        logging.info(f"{strategy_name} - {symbol}: {result['signal']} - {result['reason']}")
                    elif result["signal"] == "HOLD":
                        logging.info(f"{strategy_name} - {symbol}: {result['signal']} - {result['reason']}")
                    else:
                        logging.warning(f"{strategy_name} - {symbol}: {result['signal']} - {result['reason']}")
                        
                except Exception as e:
                    logging.error(f"{strategy_name} - {symbol} Error: {str(e)}")
            
            # Update last run time
            self.strategies[strategy_name]['last_run'] = datetime.now()
            
        except Exception as e:
            logging.error(f"Strategy {strategy_name} execution error: {str(e)}")
    
    def _get_mt5_timeframe(self, minutes: int) -> int:
        """Convert minutes to MT5 timeframe constant"""
        timeframe_map = {
            1: mt5.TIMEFRAME_M1,
            5: mt5.TIMEFRAME_M5,
            15: mt5.TIMEFRAME_M15,
            30: mt5.TIMEFRAME_M30,  
            60: mt5.TIMEFRAME_H1,
            240: mt5.TIMEFRAME_H4,
            1440: mt5.TIMEFRAME_D1
        }
        return timeframe_map.get(minutes, mt5.TIMEFRAME_M5)
    
    def start_scheduler(self):
        """Start the multi-timeframe scheduler"""
        logging.info("Starting Multi-Timeframe Trading Scheduler...")
        
        # Calculate next execution times for each strategy
        for name, info in self.strategies.items():
            timeframe = info['timeframe']
            next_time = self.get_next_candle_time(timeframe)
            info['next_execution'] = next_time
            logging.info(f"{name}: Next execution at {next_time}")
        
        try:
            logging.info("=== MAIN LOOP STARTED ===")
            while self.running:
                current_time = datetime.now()
                
                # Check each strategy for execution
                for name, info in self.strategies.items():
                    if info['next_execution'] and current_time >= info['next_execution']:
                        logging.info(f"=== TRIGGERING {name} at {current_time} ===")
                        self.run_strategy_threaded(name)
                        
                        # Calculate next execution time
                        next_time = self.get_next_candle_time(info['timeframe'])
                        info['next_execution'] = next_time
                        logging.info(f"{name}: Next execution scheduled for {next_time}")
                
                time.sleep(1)
                
                # Log every 10 seconds to show the loop is running
                if current_time.second % 10 == 0:
                    logging.info(f"=== Scheduler loop running at {current_time} ===")
                        
        except KeyboardInterrupt:
            logging.info("Scheduler stopped by user")
        except Exception as e:
            logging.error(f"Scheduler error: {str(e)}")
        finally:
            self.executor.shutdown(wait=True)
            logging.info("Scheduler shutdown complete")
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        self.running = False
        logging.info("Stopping scheduler...")

def initialize_mt5():
    """Initialize MetaTrader5 connection"""
    if not mt5.initialize():
        logging.error("MT5 initialization failed")
        return False
    
    logging.info("MT5 initialized successfully")
    return True

def main():
    """Main function to run the multi-timeframe scheduler"""
    # Setup logging with rotation
    logs_dir = setup_logging()
    
    # Initialize MT5
    if not initialize_mt5():
        logging.error("Failed to initialize MT5. Exiting...")
        return
    
    # Create scheduler instance
    scheduler = MultiTimeframeScheduler(logs_dir)
    
    # Add strategies with different timeframes
    # Strategy 1: Moving Average Crossover - 5 minutes
    scheduler.add_strategy(
        "MA_Crossover_5min",
        moving_average_crossover_strategy,
        ["XAUUSD", "EURUSD", "GBPUSD"],
        5
    )
    
    # # Strategy 2: RSI Divergence - 15 minutes
    scheduler.add_strategy(
        "RSI_Divergence_15min",
        rsi_divergence_strategy,
        ["XAUUSD", "EURUSD", "GBPUSD"],
        15
    )
    
    # Strategy 4: Supertrend + RSI - 15 minutes
    scheduler.add_strategy(
        "Supertrend_RSI_15min",
        supertrend_rsi_strategy,
        ["XAUUSD", "EURUSD"],
        15
    )
    
    # scheduler.add_strategy(
    #     "RSI_Divergence_5min",
    #     rsi_divergence_strategy,
    #     [ "EURUSD"],
    #     5
    # )
    
    
    try:
        # Start the scheduler
        scheduler.start_scheduler()
    except KeyboardInterrupt:
        logging.info("Shutting down...")
    finally:
        scheduler.stop_scheduler()
        mt5.shutdown()
        logging.info("MT5 connection closed")

if __name__ == "__main__":
    main()
