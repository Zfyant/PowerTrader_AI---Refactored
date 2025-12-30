"""
[src/core/trader.py]
--------------------
The 'Trader' module is the execution engine of PowerTrader.
It is responsible for:
1. Managing the connection to the Robinhood API (via src/api/robinhood.py).
2. Tracking account state (holdings, buying power, PnL).
3. Executing buy/sell orders based on signals.
4. Implementing risk management (trailing stops, DCA limits).
5. Persisting trade history and status to the Hub (JSON/JSONL files).

Refactoring Note:
- This replaces the monolithic `pt_trader.py`.
- API signing logic has been moved to `src/api/robinhood.py`.
- Logic is now class-based (Trader class) rather than global script.
"""

import json
import time
import traceback
import os
import math
from typing import Dict, List, Any, Optional

from colorama import Fore, Style, init

from src.api.robinhood import RobinhoodClient
from src.utils.file_manager import FileManager

# Initialize colorama
init(autoreset=True)

class Trader:
    """
    The main execution class for trading logic.
    
    **Strategy Overview:**
    The Trader operates on a continuous loop (`run` method) that:
    1.  **Monitors**: Checks current prices and account status.
    2.  **Protects**: Checks if any positions have hit their Trailing Stop conditions.
    3.  **Accumulates**: Checks if any positions have triggered a Dollar Cost Average (DCA) buy signal (Hard drop or Neural trigger).
    4.  **Enters**: Checks if any new coins have valid Neural Entry signals.
    
    **Key Concepts:**
    -   **DCA (Dollar Cost Averaging)**: We buy more of a coin as it drops to lower the average cost basis.
        -   Levels: -2.5%, -5.0%, -10.0%, etc.
        -   Limits: Max 2 DCA buys per 24h window per coin.
    -   **Trailing Stop**: Once a coin is in profit (> 2.5% or 5.0%), we activate a "Trailing Stop".
        -   If price rises, the stop price follows it up (Trail Gap: 0.5%).
        -   If price falls below the stop price, we SELL immediately to lock in profits.
    """
    def __init__(self):
        """
        Initializes the Trader, loads configuration, and restores state.
        """
        self.rh_client = RobinhoodClient()
        
        # Paths
        self.hub_data_dir = os.path.join(FileManager.BASE_DIR, "hub_data")
        os.makedirs(self.hub_data_dir, exist_ok=True)
        
        self.trader_status_path = os.path.join(self.hub_data_dir, "trader_status.json")
        self.trade_history_path = os.path.join(self.hub_data_dir, "trade_history.jsonl")
        self.pnl_ledger_path = os.path.join(self.hub_data_dir, "pnl_ledger.json")
        self.account_value_history_path = os.path.join(self.hub_data_dir, "account_value_history.jsonl")

        # Configuration
        self.crypto_symbols = ['BTC', 'ETH', 'XRP', 'BNB', 'DOGE'] # Default, should load from settings
        self.dca_levels = [-2.5, -5.0, -10.0, -20.0, -30.0, -40.0, -50.0]
        
        self.trailing_gap_pct = 0.5
        self.pm_start_pct_no_dca = 5.0
        self.pm_start_pct_with_dca = 2.5
        
        self.max_dca_buys_per_24h = 2
        self.dca_window_seconds = 24 * 60 * 60
        
        # State
        self.dca_levels_triggered: Dict[str, List[int]] = {}
        self.trailing_pm = {}
        self.cost_basis = {}
        self._dca_buy_ts = {}
        self._dca_last_sell_ts = {}
        
        self._last_good_bid_ask = {}
        self._last_good_account_snapshot = {}
        
        # Initialize
        self._load_gui_settings()
        self._seed_dca_window_from_history()
        
        try:
            print("Initializing Trader...")
            self.cost_basis = self.calculate_cost_basis()
            self.initialize_dca_levels()
        except Exception as e:
            print(f"Initialization Warning: {e}")

    def _load_gui_settings(self):
        """Loads coins list from gui_settings.json if available."""
        try:
            settings_path = os.path.join(FileManager.BASE_DIR, "gui_settings.json")
            if os.path.isfile(settings_path):
                data = FileManager.load_json(settings_path)
                coins = data.get("coins", [])
                if coins:
                    self.crypto_symbols = [str(c).strip().upper() for c in coins if str(c).strip()]
        except Exception:
            pass

    def calculate_cost_basis(self):
        """
        Calculates the average cost basis for all current holdings.
        
        **Method:**
        It fetches all 'filled' buy orders from Robinhood and matches them against the
        current held quantity (FIFO-ish logic, but effectively Weighted Average for simple scenarios).
        
        Returns:
            dict: Map of symbol -> average cost (float).
        """
        try:
            holdings = self.rh_client.get_holdings()
            if not holdings or "results" not in holdings:
                return {}

            active_assets = {holding["asset_code"] for holding in holdings.get("results", [])}
            current_quantities = {
                holding["asset_code"]: float(holding["total_quantity"])
                for holding in holdings.get("results", [])
            }

            cost_basis = {}

            for asset_code in active_assets:
                # Fetch orders for this asset
                orders_data = self.rh_client.get_orders(f"{asset_code}-USD")
                if not orders_data or "results" not in orders_data:
                    continue

                # Filter and sort buy orders (newest first)
                buy_orders = [
                    order for order in orders_data["results"]
                    if order["side"] == "buy" and order["state"] == "filled"
                ]
                buy_orders.sort(key=lambda x: x["created_at"], reverse=True)

                remaining_quantity = current_quantities[asset_code]
                total_cost = 0.0

                for order in buy_orders:
                    for execution in order.get("executions", []):
                        quantity = float(execution["quantity"])
                        price = float(execution["effective_price"])

                        if remaining_quantity <= 0:
                            break

                        if quantity > remaining_quantity:
                            total_cost += remaining_quantity * price
                            remaining_quantity = 0
                        else:
                            total_cost += quantity * price
                            remaining_quantity -= quantity

                    if remaining_quantity <= 0:
                        break

                if current_quantities[asset_code] > 0:
                    cost_basis[asset_code] = total_cost / current_quantities[asset_code]
                else:
                    cost_basis[asset_code] = 0.0

            return cost_basis
        except Exception as e:
            print(f"Error calculating cost basis: {e}")
            return {}

    def initialize_dca_levels(self):
        """
        Reconstructs the DCA (Dollar Cost Averaging) state from order history.
        
        **Why?**
        If the bot restarts, it needs to know how many DCA buys it has already performed
        for a current position so it doesn't re-buy the same level or exceed limits.
        
        **Logic:**
        1. Find the timestamp of the LAST SELL for a coin.
        2. Count all BUYS that happened *after* that timestamp.
        3. The count corresponds to the DCA stage (0 = Initial, 1 = First DCA, etc.).
        """
        try:
            holdings = self.rh_client.get_holdings()
            if not holdings or "results" not in holdings:
                return

            for holding in holdings.get("results", []):
                symbol = holding["asset_code"]
                full_symbol = f"{symbol}-USD"
                
                orders_data = self.rh_client.get_orders(full_symbol)
                if not orders_data or "results" not in orders_data:
                    continue
                
                filled_orders = [
                    o for o in orders_data["results"] 
                    if o["state"] == "filled" and o["side"] in ["buy", "sell"]
                ]
                if not filled_orders:
                    continue
                    
                filled_orders.sort(key=lambda x: x["created_at"])
                
                # Find last sell
                last_sell_time = None
                for order in reversed(filled_orders):
                    if order["side"] == "sell":
                        last_sell_time = order["created_at"]
                        break
                
                # Filter buys after last sell
                relevant_buys = []
                if last_sell_time:
                    relevant_buys = [o for o in filled_orders if o["side"] == "buy" and o["created_at"] > last_sell_time]
                else:
                    relevant_buys = [o for o in filled_orders if o["side"] == "buy"]
                
                if not relevant_buys:
                    self.dca_levels_triggered[symbol] = []
                    continue
                    
                relevant_buys.sort(key=lambda x: x["created_at"])
                
                # Count DCA buys (buys after the first initial entry)
                dca_count = max(0, len(relevant_buys) - 1)
                self.dca_levels_triggered[symbol] = list(range(dca_count))
                
        except Exception as e:
            print(f"Error initializing DCA levels: {e}")

    def _seed_dca_window_from_history(self):
        """
        Loads recent DCA history from disk to enforce rate limits across restarts.
        
        The rule is: **Max 2 DCA buys per 24 hours per coin.**
        To enforce this after a restart, we must read the `trade_history.jsonl` log
        and rebuild the list of recent buy timestamps.
        """
        try:
            if not os.path.isfile(self.trade_history_path):
                return
                
            now = time.time()
            cutoff = now - self.dca_window_seconds
            
            self._dca_buy_ts = {}
            self._dca_last_sell_ts = {}
            
            with open(self.trade_history_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    try:
                        obj = json.loads(line)
                        ts = float(obj.get("ts", 0))
                        side = str(obj.get("side", "")).lower()
                        tag = obj.get("tag", "")
                        sym = str(obj.get("symbol", "")).upper().split("-")[0]
                        
                        if side == "sell":
                            if ts > self._dca_last_sell_ts.get(sym, 0):
                                self._dca_last_sell_ts[sym] = ts
                        elif side == "buy" and tag == "DCA":
                            self._dca_buy_ts.setdefault(sym, []).append(ts)
                    except:
                        continue
            
            # Prune
            for sym, times in list(self._dca_buy_ts.items()):
                last_sell = self._dca_last_sell_ts.get(sym, 0)
                valid = [t for t in times if t > last_sell and t >= cutoff]
                self._dca_buy_ts[sym] = sorted(valid)
                
        except Exception as e:
            print(f"Error seeding DCA history: {e}")

    def _check_dca_limit(self, symbol: str) -> bool:
        """
        Checks if a coin is allowed to DCA right now.
        
        Returns:
            bool: True if under the 24h limit, False otherwise.
        """
        sym = symbol.upper()
        now = time.time()
        cutoff = now - self.dca_window_seconds
        last_sell = self._dca_last_sell_ts.get(sym, 0)
        
        history = self._dca_buy_ts.get(sym, [])
        valid = [t for t in history if t > last_sell and t >= cutoff]
        self._dca_buy_ts[sym] = valid
        
        return len(valid) < self.max_dca_buys_per_24h

    def _record_dca_buy(self, symbol: str):
        sym = symbol.upper()
        self._dca_buy_ts.setdefault(sym, []).append(time.time())

    def _record_trade(self, side, symbol, qty, price, tag=None, order_id=None, cost_basis=None):
        ts = time.time()
        entry = {
            "ts": ts,
            "side": side,
            "symbol": symbol,
            "qty": qty,
            "price": price,
            "tag": tag,
            "order_id": order_id,
            "avg_cost_basis": cost_basis
        }
        
        # Calculate PnL for sells
        realized_usd = None
        if side == "sell" and cost_basis and price:
            realized_usd = (price - cost_basis) * qty
            entry["realized_profit_usd"] = realized_usd
            
            # Update Ledger
            try:
                if os.path.exists(self.pnl_ledger_path):
                    ledger = FileManager.load_json(self.pnl_ledger_path)
                else:
                    ledger = {}
                current_total = float(ledger.get("total_realized_profit_usd", 0))
                ledger["total_realized_profit_usd"] = current_total + realized_usd
                ledger["last_updated_ts"] = ts
                FileManager.save_json(self.pnl_ledger_path, ledger)
            except Exception as e:
                print(f"Error updating ledger: {e}")
            
            # Reset DCA history for this coin
            base_sym = symbol.split("-")[0]
            self._dca_last_sell_ts[base_sym] = ts
            self._dca_buy_ts[base_sym] = []
            
        FileManager.append_jsonl(self.trade_history_path, entry)

    def _read_long_dca_signal(self, symbol: str) -> int:
        try:
            val = FileManager.read_text(symbol, "long_dca_signal.txt")
            return int(float(val)) if val else 0
        except Exception:
            return 0

    def _read_short_dca_signal(self, symbol: str) -> int:
        try:
            val = FileManager.read_text(symbol, "short_dca_signal.txt")
            return int(float(val)) if val else 0
        except Exception:
            return 0

    @staticmethod
    def _fmt_price(price: float) -> str:
        try:
            p = float(price)
        except Exception:
            return "N/A"
        if p == 0: return "0"
        ap = abs(p)
        if ap >= 1.0:
            decimals = 2
        else:
            decimals = int(-math.floor(math.log10(ap))) + 3
            decimals = max(2, min(12, decimals))
        s = f"{p:.{decimals}f}"
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s

    def place_buy_order(self, symbol: str, amount_in_usd: float, tag: str = None) -> Any:
        """
        Executes a MARKET BUY order via the Robinhood API.
        
        Handles precision issues automatically (retrying with fewer decimals if needed).
        
        Args:
            symbol (str): e.g. "BTC"
            amount_in_usd (float): Dollar value to buy.
            tag (str): Reason for buy (e.g. "DCA", "InitialEntry").
        """
        # Get current price
        try:
            rh_sym = f"{symbol}-USD"
            price = self.rh_client.get_current_price(rh_sym)
            if not price: return None
            
            qty = amount_in_usd / price
            
            max_retries = 5
            retries = 0
            
            while retries < max_retries:
                retries += 1
                try:
                    # Default precision to 8 decimals initially
                    rounded_quantity = round(qty, 8)
                    
                    response = self.rh_client.place_order(
                        symbol=rh_sym,
                        side="buy",
                        quantity=f"{rounded_quantity:.8f}",
                        type="market"
                    )
                    
                    if response and "id" in response:
                        self._record_trade("buy", symbol, rounded_quantity, price, tag=tag, order_id=response["id"])
                        print(f"{Fore.GREEN}BUY ORDER PLACED: {symbol} ${amount_in_usd:.2f} ({rounded_quantity}){Style.RESET_ALL}")
                        return response
                    elif response and "detail" in response:
                        # Handle precision error
                        detail = response["detail"]
                        if "has too much precision" in detail:
                             try:
                                nearest_value = detail.split("nearest ")[1].split(" ")[0]
                                decimal_places = len(nearest_value.split(".")[1].rstrip("0"))
                                qty = round(qty, decimal_places)
                                continue # Retry with new precision
                             except:
                                 pass
                        print(f"{Fore.RED}Buy Failed: {response}{Style.RESET_ALL}")
                        return None
                    else:
                        print(f"{Fore.RED}Buy Failed: {response}{Style.RESET_ALL}")
                        return None

                except Exception as e:
                    print(f"{Fore.RED}Buy Error: {e}{Style.RESET_ALL}")
                    return None
            return None
        except Exception as e:
            print(f"{Fore.RED}Buy Error: {e}{Style.RESET_ALL}")
            return None

    def place_sell_order(self, symbol: str, qty: float, tag: str = None, cost_basis: float = None) -> Any:
        """
        Executes a MARKET SELL order.
        """
        try:
            rh_sym = f"{symbol}-USD"
            price = self.rh_client.get_current_price(rh_sym) # Estimate
            
            # Precision handling
            qty = float(f"{qty:.8f}")
            
            response = self.rh_client.place_order(
                symbol=rh_sym,
                side="sell",
                quantity=str(qty),
                type="market"
            )
            
            if response and "id" in response:
                self._record_trade("sell", symbol, qty, price, tag=tag, order_id=response["id"], cost_basis=cost_basis)
                print(f"{Fore.RED}SELL ORDER PLACED: {symbol} ({qty}){Style.RESET_ALL}")
                return response
            else:
                print(f"{Fore.RED}Sell Failed: {response}{Style.RESET_ALL}")
                return None
        except Exception as e:
            print(f"{Fore.RED}Sell Error: {e}{Style.RESET_ALL}")
            return None

    def manage_trades(self):
        """
        The Core Logic Loop for Trading.
        
        Steps:
        1.  **Fetch Data**: Gets Account Buying Power and Holdings from API.
        2.  **Snapshot**: Calculates total account value (Liquidity + Equity).
        3.  **Process Coins**: Iterates through each tracked coin to:
            a.  Calculate PnL (Profit and Loss).
            b.  **Check Trailing Stop** (Priority 1): If profit > threshold and then drops, SELL.
            c.  **Check DCA** (Priority 2): If loss > threshold (Hard or Neural), BUY.
            d.  **Check Entry** (Priority 3): If no position, check Neural Signal for INITIAL BUY.
        4.  **Publish Status**: Writes `trader_status.json` for the UI to read.
        """
        self._load_gui_settings()
        
        # 1. Fetch Data
        try:
            account = self.rh_client.get_account()
            holdings = self.rh_client.get_holdings()
        except Exception as e:
            print(f"API Error fetching account/holdings: {e}")
            return
        
        # 2. Get Prices for ALL tracked coins (held + configured)
        symbols_to_track = set(self.crypto_symbols)
        held_assets = []
        if holdings and "results" in holdings:
            for h in holdings["results"]:
                code = h["asset_code"]
                if code != "USDC":
                    symbols_to_track.add(code)
                    held_assets.append(h)
        
        current_prices = {}
        for sym in symbols_to_track:
            full_sym = f"{sym}-USD"
            try:
                # We need bid/ask. Using get_quote which returns dict.
                quote = self.rh_client.get_quote(full_sym)
                current_prices[full_sym] = {
                    "ask": float(quote["ask_inclusive_of_buy_spread"]),
                    "bid": float(quote["bid_inclusive_of_sell_spread"])
                }
                self._last_good_bid_ask[full_sym] = current_prices[full_sym]
            except:
                # Fallback to last known
                if full_sym in self._last_good_bid_ask:
                    current_prices[full_sym] = self._last_good_bid_ask[full_sym]
                else:
                    pass 

        # 3. Account Snapshot & Robustness
        snapshot_ok = True
        try:
            buying_power = float(account.get("buying_power", 0))
        except:
            buying_power = 0.0
            snapshot_ok = False
            
        holdings_buy_value = 0.0
        holdings_sell_value = 0.0
        
        # Calculate holdings values using current prices
        for h in held_assets:
            sym = h["asset_code"]
            qty = float(h["total_quantity"])
            full_sym = f"{sym}-USD"
            
            if full_sym in current_prices:
                bp = current_prices[full_sym]["ask"]
                sp = current_prices[full_sym]["bid"]
                if bp <= 0 or sp <= 0:
                    snapshot_ok = False
                holdings_buy_value += qty * bp
                holdings_sell_value += qty * sp
            else:
                snapshot_ok = False
        
        total_account_value = buying_power + holdings_sell_value
        percent_in_trade = (holdings_sell_value / total_account_value * 100) if total_account_value > 0 else 0.0
        
        if not snapshot_ok or total_account_value <= 0:
            # Fallback
            last = self._last_good_account_snapshot
            if last.get("total_account_value"):
                total_account_value = last["total_account_value"]
                buying_power = last.get("buying_power", buying_power)
                holdings_sell_value = last.get("holdings_sell_value", holdings_sell_value)
                percent_in_trade = last.get("percent_in_trade", percent_in_trade)
        else:
            self._last_good_account_snapshot = {
                "total_account_value": total_account_value,
                "buying_power": buying_power,
                "holdings_sell_value": holdings_sell_value,
                "percent_in_trade": percent_in_trade
            }

        # 4. Process Coins (Positions & Signals)
        positions = {}
        trades_made = False
        
        # Combine held assets and tracked symbols
        all_symbols = sorted(list(symbols_to_track))
        
        for sym in all_symbols:
            full_sym = f"{sym}-USD"
            if full_sym not in current_prices:
                continue
                
            ask = current_prices[full_sym]["ask"]
            bid = current_prices[full_sym]["bid"]
            
            # Holding Status
            quantity = 0.0
            for h in held_assets:
                if h["asset_code"] == sym:
                    quantity = float(h["total_quantity"])
                    break
            
            cost_basis = self.cost_basis.get(sym, 0.0)
            
            # PnL
            pnl_pct_buy = 0.0
            pnl_pct_sell = 0.0
            if quantity > 0 and cost_basis > 0:
                pnl_pct_buy = ((ask - cost_basis) / cost_basis) * 100
                pnl_pct_sell = ((bid - cost_basis) / cost_basis) * 100
            
            # --- Trailing Stop Logic (SELL) ---
            trail_status = "OFF"
            trail_line = 0.0
            trail_peak = 0.0
            dist_to_trail = 0.0
            
            if quantity > 0 and cost_basis > 0:
                # Determine start threshold
                is_in_dca = len(self.dca_levels_triggered.get(sym, [])) > 0
                start_threshold = self.pm_start_pct_with_dca if is_in_dca else self.pm_start_pct_no_dca
                
                base_pm_line = cost_basis * (1.0 + (start_threshold / 100.0))
                
                # Get/Init State
                if sym not in self.trailing_pm:
                    self.trailing_pm[sym] = {
                        "active": False,
                        "line": base_pm_line,
                        "peak": 0.0,
                        "was_above": False
                    }
                
                t_state = self.trailing_pm[sym]
                
                # Ensure line isn't below baseline
                if t_state["line"] < base_pm_line:
                    t_state["line"] = base_pm_line
                
                # Check activation
                above_now = bid >= t_state["line"]
                
                if not t_state["active"] and above_now:
                    t_state["active"] = True
                    t_state["peak"] = bid
                
                if t_state["active"]:
                    if bid > t_state["peak"]:
                        t_state["peak"] = bid
                    
                    new_line = t_state["peak"] * (1.0 - self.trailing_gap_pct/100.0)
                    if new_line < base_pm_line: new_line = base_pm_line
                    if new_line > t_state["line"]: t_state["line"] = new_line
                    
                    # SELL SIGNAL
                    if t_state["was_above"] and bid < t_state["line"]:
                        print(f"{Fore.MAGENTA}{sym} Trailing Stop Hit! PnL: {pnl_pct_sell:.2f}%{Style.RESET_ALL}")
                        self.place_sell_order(sym, quantity, tag="TrailingStop", cost_basis=cost_basis)
                        self.trailing_pm.pop(sym, None)
                        self.dca_levels_triggered[sym] = []
                        self._dca_last_sell_ts[sym] = time.time()
                        self._dca_buy_ts[sym] = []
                        trades_made = True
                        continue # Done with this coin
                
                t_state["was_above"] = above_now
                
                trail_status = "ON" if (t_state["active"] or above_now) else "OFF"
                trail_line = t_state["line"]
                trail_peak = t_state["peak"]
                if trail_line > 0:
                    dist_to_trail = ((bid - trail_line) / trail_line) * 100.0

            # --- DCA Logic (Buy) ---
            dca_triggered_stages = len(self.dca_levels_triggered.get(sym, []))
            next_dca_display = ""
            dca_line_price = 0.0
            dca_line_source = "N/A"
            dca_line_pct = 0.0
            
            if quantity > 0 and cost_basis > 0:
                current_stage = dca_triggered_stages
                hard_level = self.dca_levels[current_stage] if current_stage < len(self.dca_levels) else self.dca_levels[-1]
                
                # Display info
                if current_stage < 4:
                    neural_next = current_stage + 4
                    next_dca_display = f"{hard_level:.2f}% / N{neural_next}"
                else:
                    next_dca_display = f"{hard_level:.2f}%"
                
                # Calculate Lines
                hard_line_price = cost_basis * (1.0 + (hard_level / 100.0))
                dca_line_price = hard_line_price
                dca_line_source = "HARD"
                
                # Check Logic
                hard_hit = pnl_pct_buy <= hard_level
                
                neural_hit = False
                neural_level_now = 0
                neural_level_needed = 0
                
                if current_stage < 4:
                    neural_level_needed = current_stage + 4
                    neural_level_now = self._read_long_dca_signal(sym)
                    neural_hit = (pnl_pct_buy < 0) and (neural_level_now >= neural_level_needed)
                    
                    if neural_hit:
                        dca_line_source = f"NEURAL N{neural_level_needed}"
                        # If neural hits, it effectively pulls the trigger line UP to current price
                        if ask > dca_line_price:
                            dca_line_price = ask

                dca_line_pct = pnl_pct_buy
                
                if (hard_hit or neural_hit) and self._check_dca_limit(sym):
                    # DCA BUY
                    reason = f"HARD {hard_level}%" if hard_hit else f"NEURAL N{neural_level_now}"
                    print(f"{Fore.YELLOW}{sym} DCA Triggered (Stage {current_stage+1}) via {reason}{Style.RESET_ALL}")
                    
                    # DCA Amount Logic
                    value_usd = quantity * bid
                    dca_amount = value_usd * 2.0
                    
                    if dca_amount > buying_power:
                        print(f"  Insufficient BP for DCA (${dca_amount:.2f} > ${buying_power:.2f})")
                    else:
                        resp = self.place_buy_order(sym, dca_amount, tag="DCA")
                        if resp:
                            self.dca_levels_triggered.setdefault(sym, []).append(current_stage)
                            self._record_dca_buy(sym)
                            trades_made = True

            # --- Initial Buy Logic ---
            if quantity <= 0.0001:
                long_sig = self._read_long_dca_signal(sym)
                short_sig = self._read_short_dca_signal(sym)
                
                if long_sig >= 3 and short_sig == 0:
                    allocation = 25.0
                    if buying_power >= allocation:
                         print(f"{Fore.GREEN}{sym} Initial Entry Signal (L:{long_sig} S:{short_sig}){Style.RESET_ALL}")
                         resp = self.place_buy_order(sym, allocation, tag="InitialEntry")
                         if resp:
                             self.dca_levels_triggered[sym] = [] # Reset DCA
                             self._dca_last_sell_ts[sym] = 0 
                             self.trailing_pm.pop(sym, None)
                             trades_made = True

            # --- Build Position Status ---
            positions[sym] = {
                "quantity": quantity,
                "avg_cost_basis": cost_basis,
                "current_buy_price": ask,
                "current_sell_price": bid,
                "gain_loss_pct_buy": pnl_pct_buy,
                "gain_loss_pct_sell": pnl_pct_sell,
                "value_usd": quantity * bid,
                "dca_triggered_stages": dca_triggered_stages,
                "next_dca_display": next_dca_display,
                "dca_line_price": dca_line_price,
                "dca_line_source": dca_line_source,
                "dca_line_pct": dca_line_pct,
                "trail_active": (trail_status == "ON"),
                "trail_line": trail_line,
                "trail_peak": trail_peak,
                "dist_to_trail_pct": dist_to_trail
            }
            
            # Write current price file (legacy support)
            try:
                # Need coin folder
                folder = FileManager.get_coin_folder(sym)
                with open(os.path.join(folder, f"{sym}_current_price.txt"), 'w') as f:
                    f.write(str(ask))
            except: pass

        # 5. Save Status
        status = {
            "timestamp": time.time(),
            "account": {
                "total_account_value": total_account_value,
                "buying_power": buying_power,
                "holdings_sell_value": holdings_sell_value,
                "holdings_buy_value": holdings_buy_value,
                "percent_in_trade": percent_in_trade,
                "pm_start_pct_no_dca": self.pm_start_pct_no_dca,
                "pm_start_pct_with_dca": self.pm_start_pct_with_dca,
                "trailing_gap_pct": self.trailing_gap_pct
            },
            "positions": positions
        }
        FileManager.save_json(self.trader_status_path, status)
        FileManager.append_jsonl(self.account_value_history_path, {"ts": time.time(), "total_account_value": total_account_value})
        
        if trades_made:
            print("Trades made, recalculating cost basis...")
            self.cost_basis = self.calculate_cost_basis()
            self.initialize_dca_levels()

    def run(self):
        print("Starting Trader Loop...")
        while True:
            try:
                self.manage_trades()
            except Exception as e:
                print(f"Error in Trader Loop: {e}")
                traceback.print_exc()
            
            # Sleep to avoid rate limits
            time.sleep(10)
