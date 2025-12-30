# Project Architecture

**Root Directory:** `\garagesteve1155\PowerTrader_AI-main`
**Total Files:** 55
**Total Directories:** 18
**Text Files Analyzed:** 54

## File Type Distribution
```
File Type Distribution:

🐍 .py       ████████████  27 (50.0%)
📄 .txt      ███████       16 (29.6%)
📝 .md       ████          9 (16.7%)
📊 .json                   1 ( 1.9%)
🖥️ .bat                    1 ( 1.9%)

Total files analyzed: 54
```

## Directory Structure
```
PowerTrader_AI-main/
├── 📁 BNB/
│   ├── 📄 alerts_version.txt (12.0B) - Stores the last alert version timestamp
│   ├── 📄 futures_long_onoff.txt (3.0B) - Toggle state for Long trades (1=On, 0=Off)
│   └── 📄 futures_short_onoff.txt (3.0B) - Toggle state for Short trades (1=On, 0=Off)
├── 📁 DOGE/
│   ├── 📄 alerts_version.txt (12.0B) - Stores the last alert version timestamp
│   ├── 📄 futures_long_onoff.txt (3.0B) - Toggle state for Long trades (1=On, 0=Off)
│   └── 📄 futures_short_onoff.txt (3.0B) - Toggle state for Short trades (1=On, 0=Off)
├── 📁 ETH/
│   ├── 📄 alerts_version.txt (12.0B) - Stores the last alert version timestamp
│   ├── 📄 futures_long_onoff.txt (3.0B) - Toggle state for Long trades (1=On, 0=Off)
│   └── 📄 futures_short_onoff.txt (3.0B) - Toggle state for Short trades (1=On, 0=Off)
├── 📁 XRP/
│   ├── 📄 alerts_version.txt (12.0B) - Stores the last alert version timestamp
│   ├── 📄 futures_long_onoff.txt (3.0B) - Toggle state for Long trades (1=On, 0=Off)
│   └── 📄 futures_short_onoff.txt (3.0B) - Toggle state for Short trades (1=On, 0=Off)
├── 📁 docs/ - Documentation & Archives
│   ├── 📝 LINE_COUNT.md (3.8KB) - Output report from the line_counter.py tool
│   ├── 📝 README_v1.md (7.4KB) - Archived previous version of the README
│   ├── 📝 REFACTOR_HANDOVER_GUIDE.md (5.4KB) - Start Here. Comprehensive guide explaining the refactor <<<<<<
│   ├── 📝 REFACTOR_STRATEGY.md (2.4KB) - Initial planning document for the modular refactor
│   └── 📝 ROADMAP.md (3.2KB) - Development progress, completed tasks, and future plans
├── 📁 hub_data/
│   └── 📊 runner_ready.json (133.0B) - Signal file indicating modules are active
├── 📁 image/
│   └── 📁 ARCHITECTURE_2/
├── 📁 src/
│   ├── 📁 api/ - External Integrations
│   │   ├── 🐍 __init__.py (0.0B)
│   │   ├── 🐍 kucoin.py (3.4KB) - Wrapper for KuCoin API (Market data fetching)
│   │   └── 🐍 robinhood.py (7.1KB) - Wrapper for Robinhood Crypto API (Order execution, Signing)
│   ├── 📁 config/ - Configuration
│   │   ├── 🐍 __init__.py (0.0B)
│   │   └── 🐍 settings.py (2.2KB) - Global constants, file paths, and default settings
│   ├── 📁 core/ - Business Logic
│   │   ├── 🐍 __init__.py (0.0B)
│   │   ├── 🐍 neural.py (9.2KB) - Math core for pattern matching (cosine similarity, normalization)
│   │   ├── 🐍 thinker.py (21.8KB) - Signal Generator. Monitors market, rebuilds bounds ("Purple Area"), detects patterns
│   │   ├── 🐍 trader.py (32.2KB) - Execution Engine. Handles buying, selling, DCA logic, and trailing stops
│   │   └── 🐍 trainer.py (12.2KB) - Learning Engine. Analyzes history to create "Neural Memories" (patterns)
│   ├── 📁 ui/ - User Interface
│   │   ├── 📁 components/ - Reusable widgets
│   │   │   ├── 🐍 account_history.py (8.3KB) - Profit/Loss visualization
│   │   │   ├── 🐍 chart.py (17.3KB) - Candlestick chart with indicators
│   │   │   ├── 🐍 layout.py (2.3KB) - Helper for grid layouts
│   │   │   └── 🐍 tiles.py (8.3KB) - Dashboard tiles (Neural Signals, Status)
│   │   ├── 📁 styles/ - Visual themes
│   │   │   └── 🐍 theme.py (321.0B) - Colors and fonts (Dark Mode)
│   │   ├── 🐍 __init__.py (0.0B)
│   │   ├── 🐍 app.py (15.2KB) - Main GUI. Tkinter application container
│   │   └── 🐍 data.py (4.0KB) - Data fetching layer for the UI (caching, threading)
│   ├── 📁 utils/ - Helpers
│   │   ├── 🐍 __init__.py (0.0B)
│   │   ├── 🐍 file_manager.py (11.3KB) - Handles all file I/O (Atomic writes, JSON/Text helpers)
│   │   └── 🐍 security.py (958.0B) - Encryption/Decryption for API keys
│   └── 🐍 __init__.py (0.0B)
├── 📁 tests/ - Testing
│   └── 🐍 test_neural.py (2.7KB) - Unit tests for the NeuralEngine logic
├── 📁 tools/ - Developer Utilities
│   ├── 🐍 test_runtime_init.py (1.6KB) - Verifies that all classes can instantiate without error
│   └── 🐍 verify_imports.py (887.0B) - Checks that all imports in the codebase resolve correctly
├── 📄 alerts_version.txt (12.0B) - (Legacy) Stores the last alert version timestamp
├── 📄 futures_long_onoff.txt (3.0B) - (Legacy) Toggle state for Long trades (1=On, 0=Off)
├── 📄 futures_short_onoff.txt (3.0B) - (Legacy) Toggle state for Short trades (1=On, 0=Off)
├── 📄 LICENSE (11.1KB) - MIT License
├── 🐍 line_counter.py (11.7KB) - Scans the project to count lines of code and file types
├── 🐍 main.py (2.3KB) - Entry Point. Launches the GUI (app.py) and background threads (Trader, Thinker)
├── 📝 README.md (10.1KB) - Main project documentation
└── 📄 requirements.txt (70.0B) - Python dependencies list
```
