# PowerTrader AI - Refactor & Handover Guide

**Date:** December 30, 2025  
**Version:** 2.0 (Modular Architecture)

---

## 🚀 Introduction: From Monolith to Modules

Welcome to the new and improved **PowerTrader AI**. If you are used to the "Big 4" script files (`pt_hub.py`, `pt_trader.py`, `pt_thinker.py`, `pt_trainer.py`), this guide is your roadmap to the new system.

I have moved from a "script-based" architecture to a **Modular Object-Oriented Architecture** making the code way safer, easier to read, and much easier to expand without breaking things.

---

## 🗺️ The "Where Did It Go?" Map

If you are looking for specific logic, here is your quick translation table:

| Old File (Legacy) | New Home (Modular) | Primary Responsibility |
| :--- | :--- | :--- |
| **`pt_hub.py`** | **`src/ui/app.py`** | The main GUI window and application controller. |
| | `src/ui/components/` | Specific UI parts (Charts, Tiles, Account History). |
| **`pt_trader.py`** | **`src/core/trader.py`** | Execution engine (Buy/Sell, DCA, Trailing Stops). |
| | `src/api/robinhood.py` | Robinhood API connection and signing logic. |
| **`pt_thinker.py`** | **`src/core/thinker.py`** | Market analysis, pattern matching, signal generation. |
| **`pt_trainer.py`** | **`src/core/trainer.py`** | Machine Learning loop (Data fetching, Memory updates). |
| *Shared Logic* | `src/utils/file_manager.py` | Safe file reading/writing (prevents corruption). |
| *Shared Logic* | `src/utils/memory_manager.py` | Neural pattern matching logic (the "Brain"). |

---

## 🔍 Detailed Component Breakdown

### 1. The User Interface (`src/ui/`)
**Formerly `pt_hub.py`**

The UI is no longer a 2000-line script mixing data fetching with button clicks.
-   **`app.py`**: The main container. It initializes the window and runs the update loop.
-   **`components/chart.py`**: Handles the Matplotlib/Tkinter integration for price charts.
-   **`components/tiles.py`**: The small "Neural Signal" cards on the left side.
-   **`components/account_history.py`**: The PnL graph at the bottom right.

**Key Change:** The UI now runs in a "polling" mode. It doesn't block the trading logic. It reads `trader_status.json` and `hub_data/` files to update itself.

### 2. The Trader (`src/core/trader.py`)
**Formerly `pt_trader.py`**

This is the execution engine.
-   **Class-Based**: Logic is now encapsulated in the `Trader` class.
-   **API Separation**: All the messy crypto-signing and HTTP request code for Robinhood has been moved to `src/api/robinhood.py`. This keeps the trading logic clean.
-   **Safety**: Uses `FileManager` for all disk operations to prevent "half-written" files if the power goes out.

### 3. The Thinker (`src/core/thinker.py`)
**Formerly `pt_thinker.py`**

This is the decision maker.
-   **Pattern Matching**: The logic that compares current candles to historical "memories" is now centralized in `src/utils/memory_manager.py`. The Thinker just calls `NeuralEngine.find_match()`.
-   **State**: It maintains the state of the market in `self.states` and writes the results to `hub_data/` for the UI to see.

### 4. The Trainer (`src/core/trainer.py`)
**Formerly `pt_trainer.py`**

This is the learning system.
-   **On-Demand**: The UI now launches the Trainer in a background thread when you click "Train Model".
-   **Progress Tracking**: It writes its progress to `trainer_status.json`, so the UI can show a progress bar without freezing.

---

## 🛠️ Key Utilities (The "Glue")

### `src/utils/file_manager.py`
**Why?** In the old system, if two scripts tried to read/write `trades.json` at the same time, the file could get corrupted (blanked out).
**How?** The `FileManager` uses **Atomic Writes**. It writes to a temporary file first (e.g., `trades.json.tmp`) and then renames it to `trades.json` instantly. This guarantees data integrity.

### `src/utils/memory_manager.py`
**Why?** Pattern matching logic was duplicated in Trainer and Thinker.
**How?** The `NeuralEngine` class handles all the math for comparing candle patterns. If we want to change how we match patterns, we change it in one place.

---

## 📂 Directory Structure

```text
PowerTrader_AI/
├── main.py                 # <--- START HERE (The new entry point)
├── legacy_archive/         # The old pt_*.py files (for reference only)
├── hub_data/               # Live data shared between modules
├── logs/                   # System logs
├── src/
│   ├── api/                # Robinhood / KuCoin adapters
│   ├── config/             # Settings and constants
│   ├── core/               # The "Big 3" (Trader, Thinker, Trainer)
│   ├── ui/                 # All GUI code
│   │   ├── components/     # Reusable widgets
│   │   └── styles/         # Theme/Colors
│   └── utils/              # Helpers (Files, Math, Time)
```

---

## 🚦 How to Run

**Old Way:**
`python pt_hub.py`

**New Way:**
```bash
python main.py
```

This single command will:
1.  Initialize the environment.
2.  Launch the UI.
3.  (Future) Automatically spawn the background processes if configured.

---

## 📝 Developer Notes

-   **Docstrings**: Every file now has a header explaining what it does.
-   **Type Hinting**: Most functions now use Python type hints (e.g., `def calculate(price: float) -> bool:`) to make it obvious what data is being passed around.
-   **Imports**: We use absolute imports (e.g., `from src.core.trader import Trader`) to avoid confusion.

*Happy Trading!*
