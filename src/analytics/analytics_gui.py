import curses
import time
from dataclasses import dataclass
from typing import List, Dict, Any
import os
import subprocess
import tempfile
import platform
import json
import sys # Added for sys.argv

@dataclass
class TradeDisplay:
    id: int
    strategy: str
    signal: str
    entry_price: float
    current_price: float # For open trades, this could be the last known price or entry for display
    pnl: float
    status: str # OPEN/CLOSED
    timestamp: str

class AnalyticsGUI:
    def __init__(self, analysis_data: Dict[str, Any]):
        self.analysis_data = analysis_data
        self.trades: List[TradeDisplay] = []
        self.running = True
        self.total_pnl = 0.0
        self.open_trades_count = 0
        self.closed_trades_count = 0

        self._process_analysis_data()

    def _process_analysis_data(self):
        trade_id_counter = 1
        for strategy, data in self.analysis_data.items():
            if "closed_trades" in data:
                for trade_info in data["closed_trades"]:
                    pnl = trade_info.get("pnl", 0.0)
                    self.trades.append(TradeDisplay(
                        id=trade_id_counter,
                        strategy=strategy,
                        signal=trade_info.get("signal", "N/A"),
                        entry_price=trade_info.get("entry_price", 0.0),
                        current_price=trade_info.get("closing_price", trade_info.get("entry_price", 0.0)),
                        pnl=pnl,
                        status='CLOSED',
                        timestamp=trade_info.get("closure_timestamp", "N/A")
                    ))
                    self.total_pnl += pnl
                    self.closed_trades_count += 1
                    trade_id_counter += 1
            if "ongoing_trades" in data:
                for trade_info in data["ongoing_trades"]:
                    self.trades.append(TradeDisplay(
                        id=trade_id_counter,
                        strategy=strategy,
                        signal=trade_info.get("signal", "N/A"),
                        entry_price=trade_info.get("entry_price", 0.0),
                        current_price=trade_info.get("entry_price", 0.0), # For ongoing, current price is same as entry for display
                        pnl=0.0, # PnL for ongoing trades is dynamic and not from initial analysis
                        status='OPEN',
                        timestamp=trade_info.get("initiation_timestamp", "N/A")
                    ))
                    self.open_trades_count += 1
                    trade_id_counter += 1

    def draw_header(self, stdscr):
        height, width = stdscr.getmaxyx()
        title = "AI Trade Analysis Terminal"
        stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD | curses.color_pair(1))

        stats = f"Open Trades: {self.open_trades_count} | Closed Trades: {self.closed_trades_count} | Total P&L: ${self.total_pnl:.2f}"
        stdscr.addstr(1, 2, stats, curses.color_pair(2))
        stdscr.addstr(2, 0, "-" * width, curses.color_pair(3))
        return 3

    def draw_trades_table(self, stdscr, start_row):
        height, width = stdscr.getmaxyx()
        headers = f"{'ID':<4} {'STRATEGY':<12} {'SIGNAL':<8} {'ENTRY':<10} {'CURRENT':<10} {'P&L':<12} {'STATUS':<8} {'TIMESTAMP':<10}"
        stdscr.addstr(start_row, 2, headers, curses.A_BOLD | curses.color_pair(4))
        stdscr.addstr(start_row + 1, 2, "-" * min(len(headers), width - 4), curses.color_pair(3))

        row = start_row + 2
        for trade in reversed(self.trades):
            if row >= height - 1:
                break
            
            if trade.pnl > 0:
                color = curses.color_pair(5)
            elif trade.pnl < 0:
                color = curses.color_pair(6)
            else:
                color = curses.color_pair(7)

            trade_row = f"{trade.id:<4} {trade.strategy:<12} {trade.signal:<8} {trade.entry_price:<10.4f} {trade.current_price:<10.4f} ${trade.pnl:<11.2f} {trade.status:<8} {trade.timestamp:<10}"
            try:
                stdscr.addstr(row, 2, trade_row[:width-4], color)
            except curses.error:
                pass
            row += 1

    def draw_footer(self, stdscr):
        height, width = stdscr.getmaxyx()
        footer = "Press 'q' to quit"
        try:
            stdscr.addstr(height - 1, 2, footer, curses.color_pair(2))
        except curses.error:
            pass

    def main_loop(self, stdscr):
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLACK)
        
        curses.curs_set(0)
        stdscr.nodelay(1)
        stdscr.timeout(100)

        while self.running:
            try:
                stdscr.clear()
                start_row = self.draw_header(stdscr)
                self.draw_trades_table(stdscr, start_row + 1)
                self.draw_footer(stdscr)
                stdscr.refresh()
                
                key = stdscr.getch()
                if key == ord('q') or key == ord('Q'):
                    self.running = False
            except KeyboardInterrupt:
                self.running = False
            except curses.error:
                pass

def run_curses_gui(analysis_data_json: str):
    analysis_data = json.loads(analysis_data_json)
    gui = AnalyticsGUI(analysis_data)
    try:
        curses.wrapper(gui.main_loop)
    except KeyboardInterrupt:
        pass
    finally:
        print("\nAI Trade Analysis session ended.")
        input("Press Enter to close this terminal...")


def create_popup_window(analysis_data_json: str):
    # This code will be executed in a new process, so we pass data via command-line argument
    current_file_path = os.path.abspath(__file__)

    try:
        system = platform.system().lower()
        
        if system == 'windows':
            cmd = f'start "AI Trade Analysis" cmd /k "python {current_file_path} \"{analysis_data_json}\""'
            subprocess.Popen(cmd, shell=True)
            
        elif system == 'darwin':  # macOS
            script = f'''
            tell application "Terminal"
                do script "python {current_file_path} '{analysis_data_json}'"
                activate
            end tell
            '''
            subprocess.Popen(['osascript', '-e', script])
            
        else:  # Linux and others
            terminals = ['gnome-terminal', 'xterm', 'konsole', 'xfce4-terminal']
            launched = False
            
            for terminal in terminals:
                try:
                    if terminal == 'gnome-terminal':
                        subprocess.Popen([terminal, '--', 'python3', current_file_path, analysis_data_json])
                    else:
                        subprocess.Popen([terminal, '-e', f'python3 {current_file_path} {analysis_data_json}'])
                    launched = True
                    break
                except FileNotFoundError:
                    continue
            
            if not launched:
                print("Could not find a suitable terminal emulator.")
                print(f"Please run manually: python3 {current_file_path} '{analysis_data_json}'")
                return
        
        print("AI Trade Analysis Terminal launched in new window!")
        
    except Exception as e:
        print(f"Error launching window: {e}")
        print("Falling back to current terminal...")
        run_curses_gui(analysis_data_json)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        analysis_data_json_arg = sys.argv[1]
        run_curses_gui(analysis_data_json_arg)
    else:
        print("Error: No analysis data provided. This script should be launched by analytics_agent.py.")
