# 🗺️ PowerTrader AI Refactoring Roadmap

This document outlines the step-by-step plan to transform the PowerTrader codebase from a monolithic script collection into a robust, modular, and scalable Python application.

---

## 🏁 Phase 1: Preparation & Safety (✅ Completed)
- [x] **Audit Codebase**: Analyze `pt_hub.py`, `pt_trainer.py`, `pt_thinker.py`, and `pt_trader.py`.
- [x] **Establish Directory Structure**: Create `src/` with `api`, `core`, `ui`, `utils`, `config`.
- [x] **Dependency Check**: Ensure all libraries are listed in `requirements.txt`.
- [x] **Backup Strategy**: Ensure original files are preserved until verification is complete.

## 🏗️ Phase 2: Core Infrastructure (✅ Completed)
- [x] **Configuration Management**: Create `src/config/settings.py` to handle globals.
- [x] **File I/O Abstraction**: Create `src/utils/file_manager.py` to handle all file reads/writes (crucial for the flat-file database system).
- [x] **API Clients**:
    - [x] `src/api/robinhood.py`: Encapsulate all Robinhood requests.
    - [x] `src/api/kucoin.py`: Encapsulate all Kucoin requests.

## 🧠 Phase 3: Logic Migration (✅ Completed)
- [x] **Thinker (Signal Generation)**:
    - [x] Migrate `pt_thinker.py` to `src/core/thinker.py`.
    - [x] Implement `ThinkerState` class.
    - [x] Implement "Neural" pattern matching logic.
    - [x] Implement "Gap Modifier" bounds rebuilding logic (Completed legacy parity).
- [x] **Trader (Execution)**:
    - [x] Create `src/core/trader.py`.
    - [x] Implement DCA logic and state tracking.
    - [x] Finalize `manage_trades` loop (Buy/Sell execution).
    - [x] Verify PnL calculation accuracy and Trailing Stop logic.
- [x] **Neural Engine**:
    - [x] Create `src/core/neural.py` to isolate math logic.
- [x] **Trainer (Learning)**:
    - [x] **[SEE REFACTOR_DEEP_DIVE.md]** Detailed breakdown of this complex task.
    - [x] Migrate `pt_trainer.py` to `src/core/trainer.py`.
    - [x] Isolate Pattern Matching Logic (`src/core/neural.py`).
    - [x] Integrate Neural Engine into Trainer Loop.
    - [x] Implement `TrainerState` class (Implicit in Trainer).
    - [x] Reconstruct the training loop (data gathering -> pattern finding).

## 🎨 Phase 4: UI & Entry Point (✅ Completed)
- [x] **Hub Migration**:
    - [x] Extract reusable UI components to `src/ui/components/` (`tiles.py`, `chart.py`).
    - [x] Create data handling layer `src/ui/data.py`.
    - [x] Create `src/ui/components/account_history.py`.
    - [x] Rebuild the main dashboard in `src/ui/app.py`.
    - [x] Connect UI to new `Thinker`, `Trader` (via threads) and `Trainer` (via manual control).
- [x] **Entry Point**:
    - [x] Create `main.py` as the single entry point.
    - [x] Ensure `main.py` can launch the UI and background threads.

## 🧹 Phase 5: Cleanup & Documentation (✅ Completed)
- [x] **Verification**: 
    - [x] Verify all modular imports (`verify_imports.py` success).
    - [x] Manual verification via dry run (Codebase static analysis clean).
- [x] **Documentation**: Add docstrings to all new classes (API, Core, UI, Utils).
- [x] **Archival**: Move `pt_*.py` files to `legacy_archive/` (✅ Completed).
- [x] **Final Polish**: Remove unused imports and debug prints.

