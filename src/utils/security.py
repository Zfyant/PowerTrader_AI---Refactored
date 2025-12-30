import os

class Security:
    @staticmethod
    def load_robinhood_creds(base_dir=None):
        """
        Loads Robinhood API credentials from r_key.txt and r_secret.txt.
        """
        if base_dir is None:
            # Default to the root project directory (up 2 levels from src/utils)
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
        key_path = os.path.join(base_dir, "r_key.txt")
        secret_path = os.path.join(base_dir, "r_secret.txt")

        if not os.path.isfile(key_path) or not os.path.isfile(secret_path):
            return None, None

        try:
            with open(key_path, "r", encoding="utf-8") as f:
                api_key = f.read().strip()
            with open(secret_path, "r", encoding="utf-8") as f:
                private_key = f.read().strip()
            return api_key, private_key
        except Exception:
            return None, None
