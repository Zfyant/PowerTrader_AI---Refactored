"""
src/api/robinhood.py

Robinhood Crypto API Client.
This module handles all communication with the Robinhood Crypto Trading API, including:
1.  Request Signing (Ed25519).
2.  Market Data Retrieval (Quotes, Prices).
3.  Account Management (Holdings, Buying Power).
4.  Order Execution (Place Order, Cancel Order).

References:
- Robinhood Crypto API Documentation
"""

import time
import base64
import uuid
import json
import requests
from nacl.signing import SigningKey
from src.utils.security import Security

class RobinhoodClient:
    """
    A secure client for the Robinhood Crypto API.
    
    Handles the cryptographic signing of requests required by Robinhood's security protocol.
    It expects credentials (API Key and Base64 Private Key) to be available via the Security manager.
    
    Attributes:
        BASE_URL (str): The production API endpoint.
        api_key (str): The public API key.
        private_key (SigningKey): The loaded Ed25519 signing key.
        session (requests.Session): Persistent HTTP session for keep-alive.
    """
    BASE_URL = "https://trading.robinhood.com"

    def __init__(self, api_key=None, private_key_b64=None):
        """
        Initialize the Robinhood Client.
        
        Args:
            api_key: Optional explicit API key.
            private_key_b64: Optional explicit private key (Base64 string).
            
        Raises:
            ValueError: If credentials cannot be found or the private key is invalid.
        """
        if not api_key or not private_key_b64:
            api_key, private_key_b64 = Security.load_robinhood_creds()
        
        if not api_key or not private_key_b64:
            raise ValueError("Robinhood credentials not found or invalid.")

        self.api_key = api_key
        try:
            raw_private = base64.b64decode(private_key_b64)
            self.private_key = SigningKey(raw_private)
        except Exception as e:
            raise ValueError(f"Invalid Private Key: {e}")

        self.session = requests.Session()
        self.timeout = 10

    def _get_timestamp(self) -> int:
        """Return current Unix timestamp."""
        return int(time.time())

    def _get_headers(self, method: str, path: str, body: str, timestamp: int) -> dict:
        """
        Construct the signed headers required for authentication.
        
        The signature is generated over: {API_KEY}{TIMESTAMP}{PATH}{METHOD}{BODY}
        using the Ed25519 private key.
        """
        method = method.upper()
        body = body or ""
        message = f"{self.api_key}{timestamp}{path}{method}{body}"
        signed = self.private_key.sign(message.encode("utf-8"))
        signature_b64 = base64.b64encode(signed.signature).decode("utf-8")

        return {
            "x-api-key": self.api_key,
            "x-timestamp": str(timestamp),
            "x-signature": signature_b64,
            "Content-Type": "application/json",
        }

    def request(self, method: str, endpoint: str, body: str = "") -> dict:
        """
        Execute a signed API request.
        
        Args:
            method: HTTP method ("GET", "POST", etc.)
            endpoint: API endpoint path (e.g., "/api/v1/crypto/holdings/")
            body: Request body string (for POST requests).
            
        Returns:
            dict: The parsed JSON response.
            
        Raises:
            RuntimeError: If the API returns a 4xx or 5xx status code.
        """
        url = f"{self.BASE_URL}{endpoint}"
        ts = self._get_timestamp()
        headers = self._get_headers(method, endpoint, body, ts)

        response = self.session.request(
            method=method.upper(),
            url=url,
            headers=headers,
            data=body or None,
            timeout=self.timeout
        )

        if response.status_code >= 400:
            raise RuntimeError(f"Robinhood API Error {response.status_code}: {response.text}")
        
        return response.json()

    def get_account(self) -> dict:
        """
        Retrieve account information.
        
        Useful fields in response:
        - buying_power: Available cash for trading.
        - account_number: The account identifier.
        """
        return self.request("GET", "/api/v1/crypto/trading/accounts/")

    def get_trading_pairs(self) -> dict:
        """
        Retrieve a list of all available crypto trading pairs.
        """
        return self.request("GET", "/api/v1/crypto/trading/trading_pairs/")

    def get_quote(self, symbol: str) -> dict:
        """
        Get the current best bid and ask for a specific symbol.
        
        Args:
            symbol: The trading pair symbol (e.g., "BTC-USD").
            
        Returns:
            dict: Contains 'bid_inclusive_of_sell_spread', 'ask_inclusive_of_buy_spread', etc.
        """
        symbol = symbol.upper()
        path = f"/api/v1/crypto/marketdata/best_bid_ask/?symbol={symbol}"
        data = self.request("GET", path)
        
        if not data or "results" not in data or not data["results"]:
            raise RuntimeError(f"No quote data found for {symbol}")
            
        return data["results"][0]

    def get_current_price(self, symbol: str) -> float:
        """
        Get the current ASK price for a symbol (e.g. 'BTC-USD').
        
        This is typically used as the 'Buy Price'.
        """
        symbol = symbol.upper()
        path = f"/api/v1/crypto/marketdata/best_bid_ask/?symbol={symbol}"
        data = self.request("GET", path)
        
        if not data or "results" not in data or not data["results"]:
             raise RuntimeError(f"No price data found for {symbol}")
             
        return float(data["results"][0]["ask_inclusive_of_buy_spread"])

    def get_holdings(self) -> dict:
        """
        Retrieve all crypto holdings for the account.
        """
        return self.request("GET", "/api/v1/crypto/holdings/")

    def get_orders(self, symbol: str = None) -> dict:
        """
        Retrieve recent order history.
        
        Note: The API returns a paginated list. This method fetches the first page.
        """
        # Legacy code calls /api/v1/crypto/trading/orders/ without params.
        return self.request("GET", "/api/v1/crypto/trading/orders/")

    def place_order(self, symbol: str, side: str, quantity: str, price: str = None, type: str = "market") -> dict:
        """
        Place a Buy or Sell order.
        
        Args:
            symbol: Trading pair (e.g., "BTC-USD").
            side: "buy" or "sell".
            quantity: Amount of asset to trade (as string to preserve precision).
            price: Limit price (required if type="limit").
            type: "market" or "limit".
            
        Returns:
            dict: The order confirmation details.
        """
        path = "/api/v1/crypto/trading/orders/"
        payload = {
            "client_order_id": str(uuid.uuid4()),
            "side": side.lower(),
            "symbol": symbol.upper(),
            "type": type.lower(),
            "quantity": str(quantity)
        }
        if price:
            payload["price"] = str(price)
            
        return self.request("POST", path, body=json.dumps(payload))
