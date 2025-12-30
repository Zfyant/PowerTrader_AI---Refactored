import os

class Config:
    """
    Central Configuration for PowerTrader AI.

    This class defines global constants, default settings, and file paths used across the application.
    It serves as a single source of truth for configuration, replacing scattered magic strings.

    Attributes:
        BASE_DIR (str): The absolute path to the project root.
        LOGS_DIR (str): Directory for application logs.
        DEFAULT_COINS (list): Default list of cryptocurrency symbols to track.
        DEFAULT_SETTINGS (dict): Comprehensive default configuration dictionary compatible with legacy logic.
        VERBOSE (bool): Flag to enable detailed debug logging.
    """

    # Base Paths
    # Resolves to: PowerTrader_AI-main/
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    LOGS_DIR = os.path.join(BASE_DIR, "logs")
    
    # Trading Settings
    DEFAULT_COINS = ["BTC", "ETH", "XRP", "BNB", "DOGE"]
    
    # Legacy Settings (derived from pt_hub.py defaults)
    # These values are used to populate `settings.json` if it doesn't exist.
    DEFAULT_SETTINGS = {
        "main_neural_dir": BASE_DIR,
        "coins": DEFAULT_COINS,
        "default_timeframe": "1hour",
        "timeframes": [
            "1min", "5min", "15min", "30min",
            "1hour", "2hour", "4hour", "8hour", "12hour",
            "1day", "1week"
        ],
        "candles_limit": 120,               # Number of candles to fetch for analysis
        "ui_refresh_seconds": 1.0,          # GUI update frequency
        "chart_refresh_seconds": 10.0,      # Chart polling frequency
        "hub_data_dir": os.path.join(BASE_DIR, "hub_data"),
        "script_neural_runner2": "src/core/thinker.py", # Path to the 'Thinker' process script
        "script_neural_trainer": "src/core/trainer.py", # Path to the 'Trainer' process script
        "script_trader": "src/core/trader.py",          # Path to the 'Trader' process script
        "auto_start_scripts": False,        # Whether to auto-launch backend scripts on UI startup
    }
    
    # Speed / Debug
    VERBOSE = False

# Export DEFAULT_SETTINGS for compatibility with modules importing it directly
DEFAULT_SETTINGS = Config.DEFAULT_SETTINGS
