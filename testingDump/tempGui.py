#!/usr/bin/env python3
import os
import sys
import subprocess
import tempfile
import platform

# Main GUI code that will run in the popup window
MAIN_CODE = '''
import curses
import random
import time
import threading
from datetime import datetime
from dataclasses import dataclass
from typing import List

@dataclass
class Trade:
    id: int
    pair: str
    action: str  # BUY/SELL
    entry_price: float
    current_price: float
    lot_size: float
    pnl: float
    status: str  # OPEN/CLOSED
    timestamp: str

class ForexTerminalGUI:
    def __init__(self):
        self.trades: List[Trade] = []
        self.running = True
        self.total_pnl = 0.0
        self.trade_counter = 1
        self.pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CAD', 'USD/CHF']
        self.pair_prices = {
            'EUR/USD': 1.0950,
            'GBP/USD': 1.2650,
            'USD/JPY': 148.50,
            'AUD/USD': 0.6580,
            'USD/CAD': 1.3720,
            'USD/CHF': 0.8850
        }
        
    def generate_random_trade(self):
        """Generate a random trade entry"""
        pair = random.choice(self.pairs)
        action = random.choice(['BUY', 'SELL'])
        entry_price = self.pair_prices[pair] * random.uniform(0.998, 1.002)
        lot_size = random.uniform(0.1, 2.0)
        
        trade = Trade(
            id=self.trade_counter,
            pair=pair,
            action=action,
            entry_price=entry_price,
            current_price=entry_price,
            lot_size=round(lot_size, 2),
            pnl=0.0,
            status='OPEN',
            timestamp=datetime.now().strftime('%H:%M:%S')
        )
        
        self.trades.append(trade)
        self.trade_counter += 1
        
        # Keep only last 15 trades for performance
        if len(self.trades) > 15:
            closed_trade = self.trades.pop(0)
            if closed_trade.status == 'OPEN':
                self.total_pnl += closed_trade.pnl

    def update_prices(self):
        """Update current prices and calculate PnL"""
        for trade in self.trades:
            if trade.status == 'OPEN':
                # Simulate price movement
                volatility = random.uniform(-0.001, 0.001)
                trade.current_price += trade.current_price * volatility
                
                # Calculate PnL
                if trade.action == 'BUY':
                    trade.pnl = (trade.current_price - trade.entry_price) * trade.lot_size * 100000
                else:
                    trade.pnl = (trade.entry_price - trade.current_price) * trade.lot_size * 100000
                
                # Randomly close some trades
                if random.random() < 0.05:  # 5% chance to close
                    trade.status = 'CLOSED'
                    self.total_pnl += trade.pnl

    def trading_engine(self):
        """Background thread for trade generation and updates"""
        while self.running:
            # Generate new trade occasionally
            if random.random() < 0.3:  # 30% chance
                self.generate_random_trade()
            
            # Update prices
            self.update_prices()
            
            time.sleep(0.5)  # Update every 500ms

    def draw_header(self, stdscr):
        """Draw the header section"""
        height, width = stdscr.getmaxyx()
        
        # Title
        title = "FOREX ALGO TRADING TERMINAL"
        stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD | curses.color_pair(1))
        
        # Statistics
        open_trades = sum(1 for t in self.trades if t.status == 'OPEN')
        closed_trades = sum(1 for t in self.trades if t.status == 'CLOSED')
        current_pnl = sum(t.pnl for t in self.trades if t.status == 'OPEN')
        
        stats = f"Open: {open_trades} | Closed: {closed_trades} | Current P&L: ${current_pnl:.2f} | Total P&L: ${self.total_pnl:.2f}"
        stdscr.addstr(1, 2, stats, curses.color_pair(2))
        
        # Separator
        stdscr.addstr(2, 0, "-" * width, curses.color_pair(3))
        
        return 3

    def draw_trades_table(self, stdscr, start_row):
        """Draw the trades table"""
        height, width = stdscr.getmaxyx()
        
        # Table headers
        headers = f"{'ID':<4} {'PAIR':<8} {'ACTION':<6} {'ENTRY':<8} {'CURRENT':<8} {'LOT':<6} {'P&L':<10} {'STATUS':<8} {'TIME':<8}"
        stdscr.addstr(start_row, 2, headers, curses.A_BOLD | curses.color_pair(4))
        
        # Separator
        stdscr.addstr(start_row + 1, 2, "-" * min(len(headers), width - 4), curses.color_pair(3))
        
        # Trade rows
        row = start_row + 2
        for trade in reversed(self.trades[-10:]):  # Show last 10 trades
            if row >= height - 1:
                break
                
            # Color based on PnL
            if trade.pnl > 0:
                color = curses.color_pair(5)  # Green
            elif trade.pnl < 0:
                color = curses.color_pair(6)  # Red
            else:
                color = curses.color_pair(7)  # White
            
            trade_row = f"{trade.id:<4} {trade.pair:<8} {trade.action:<6} {trade.entry_price:<8.4f} {trade.current_price:<8.4f} {trade.lot_size:<6.2f} ${trade.pnl:<9.2f} {trade.status:<8} {trade.timestamp:<8}"
            
            try:
                stdscr.addstr(row, 2, trade_row[:width-4], color)
            except curses.error:
                pass  # Ignore if we can't write to screen
                
            row += 1

    def draw_footer(self, stdscr):
        """Draw the footer with controls"""
        height, width = stdscr.getmaxyx()
        footer = "Press 'q' to quit | Auto-trading active..."
        try:
            stdscr.addstr(height - 1, 2, footer, curses.color_pair(2))
        except curses.error:
            pass

    def main_loop(self, stdscr):
        """Main display loop"""
        # Initialize colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)    # Title
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Stats
        curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)    # Separators
        curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLACK)   # Headers
        curses.init_pair(5, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Profit
        curses.init_pair(6, curses.COLOR_RED, curses.COLOR_BLACK)     # Loss
        curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLACK)   # Neutral
        
        # Configure curses
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(1)   # Non-blocking input
        stdscr.timeout(100) # Refresh every 100ms
        
        # Start trading engine
        trading_thread = threading.Thread(target=self.trading_engine, daemon=True)
        trading_thread.start()
        
        while self.running:
            try:
                stdscr.clear()
                
                # Draw interface
                start_row = self.draw_header(stdscr)
                self.draw_trades_table(stdscr, start_row + 1)
                self.draw_footer(stdscr)
                
                stdscr.refresh()
                
                # Check for quit
                key = stdscr.getch()
                if key == ord('q') or key == ord('Q'):
                    self.running = False
                    
            except KeyboardInterrupt:
                self.running = False
            except curses.error:
                pass  # Ignore drawing errors

def run_gui():
    """Entry point for the GUI"""
    gui = ForexTerminalGUI()
    try:
        curses.wrapper(gui.main_loop)
    except KeyboardInterrupt:
        pass
    finally:
        print("\\nTrading session ended.")
        print(f"Final Total P&L: ${gui.total_pnl:.2f}")
        input("Press Enter to close...")

if __name__ == "__main__":
    run_gui()
'''

def create_popup_window():
    """Create and launch the GUI in a new window"""
    
    # Create temporary file with the main code
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as temp_file:
        temp_file.write(MAIN_CODE)
        temp_file_path = temp_file.name
    
    try:
        system = platform.system().lower()
        
        if system == 'windows':
            # Windows: Create new cmd window
            cmd = f'start "Forex Trading Terminal" cmd /k "python {temp_file_path}"'
            subprocess.run(cmd, shell=True)
            
        elif system == 'darwin':  # macOS
            # macOS: Create new Terminal window
            script = f'''
            tell application "Terminal"
                do script "cd {os.path.dirname(temp_file_path)} && python {os.path.basename(temp_file_path)}"
                activate
            end tell
            '''
            subprocess.run(['osascript', '-e', script])
            
        else:  # Linux and others
            # Try different terminal emulators
            terminals = ['gnome-terminal', 'xterm', 'konsole', 'xfce4-terminal']
            launched = False
            
            for terminal in terminals:
                try:
                    if terminal == 'gnome-terminal':
                        subprocess.Popen([terminal, '--', 'python3', temp_file_path])
                    else:
                        subprocess.Popen([terminal, '-e', f'python3 {temp_file_path}'])
                    launched = True
                    break
                except FileNotFoundError:
                    continue
            
            if not launched:
                print("Could not find a suitable terminal emulator.")
                print(f"Please run manually: python3 {temp_file_path}")
                return
        
        print("Forex Trading Terminal launched in new window!")
        print("Close this window or press Ctrl+C to exit the launcher.")
        
        # Keep the launcher alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
            
    except Exception as e:
        print(f"Error launching window: {e}")
        print("Falling back to current terminal...")
        # Fallback: run in current terminal
        exec(MAIN_CODE)
        
    finally:
        # Cleanup temporary file
        try:
            os.unlink(temp_file_path)
        except:
            pass

def main():
    """Main launcher function"""
    print("Forex Algo Trading Terminal Launcher")
    print("=" * 40)
    
    choice = input("Launch in:\n1. New popup window (recommended)\n2. Current terminal\nChoose (1/2): ").strip()
    
    if choice == '2':
        # Run in current terminal
        exec(MAIN_CODE.replace('run_gui()', '''
gui = ForexTerminalGUI()
try:
    curses.wrapper(gui.main_loop)
except KeyboardInterrupt:
    pass
finally:
    print("\\nTrading session ended.")
    print(f"Final Total P&L: ${gui.total_pnl:.2f}")
'''))
    else:
        # Launch in new window
        create_popup_window()

if __name__ == "__main__":
    import time
    main()