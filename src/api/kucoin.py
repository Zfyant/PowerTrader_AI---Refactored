from kucoin.client import Market
import logging

class KucoinClient:
    """
    A minimal wrapper for the Kucoin API to fetch market data.

    This class abstracts the `kucoin-python` library to provide a simple interface
    for fetching candlestick (kline) data required by the PowerTrader AI logic.
    
    It handles:
    1.  **Client Initialization**: Lazy loading of the Market client to avoid startup overhead or connection errors.
    2.  **Error Handling**: Catches and logs connection failures, preventing crashes in the main thread.
    3.  **Data Formatting**: Returns data in the specific string format expected by the legacy analysis modules.

    Attributes:
        market (Market): The underlying Kucoin Market client instance.
    """

    def __init__(self):
        """
        Initialize the KucoinClient wrapper.
        
        Does not establish a connection immediately; calls `_init_client` internally.
        """
        self._init_client()

    def _init_client(self):
        """
        Attempt to initialize the Kucoin Market client.

        Sets `self.market` to the client instance if successful, or `None` if it fails.
        Logs any errors to the standard logging output.
        """
        try:
            self.market = Market(url='https://api.kucoin.com')
        except Exception as e:
            logging.error(f"Failed to initialize Kucoin Market client: {e}")
            self.market = None

    def get_kline(self, symbol: str, timeframe: str) -> str:
        """
        Fetch historical candlestick (kline) data from Kucoin.

        This method retrieves OHLCV (Open, High, Low, Close, Volume) data for a specific
        cryptocurrency pair and timeframe.

        Args:
            symbol (str): The trading pair symbol (e.g., "BTC-USDT", though often passed as "BTC" 
                          and handled by the caller or default market logic).
            timeframe (str): The time interval for the candles (e.g., "1hour", "15min").
                             Must match Kucoin's supported timeframe strings.

        Returns:
            str: The raw string representation of the kline list.
                 Legacy compatibility note: The original codebase expects a string representation
                 of the list (e.g., "[['167...', '20000', ...], ...]") which it then parses manually.
                 This wrapper preserves that behavior to ensure compatibility with `pt_thinker.py` logic.

        Raises:
            RuntimeError: If the Kucoin client cannot be initialized.
            Exception: Propagates any API errors from the underlying `kucoin` library after logging.
        """
        if not self.market:
            self._init_client()
            if not self.market:
                raise RuntimeError("Kucoin client not initialized")
        
        # Kucoin API call
        # Legacy code passed timeframe like '1hour' which matches Kucoin SDK
        try:
            # The kucoin library returns a list of lists.
            # We convert it to a string because the legacy `pt_thinker` and `pt_trainer`
            # logic was built to parse raw text files or stringified lists.
            return str(self.market.get_kline(symbol, timeframe))
        except Exception as e:
            # If request fails, maybe client is stale?
            logging.error(f"Kucoin get_kline error: {e}")
            raise e
