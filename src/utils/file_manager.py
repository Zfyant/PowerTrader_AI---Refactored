import os
import json
from typing import Any, Dict

class FileManager:
    """
    Centralized handler for all file system operations in PowerTrader AI.

    This class provides static utility methods to:
    1.  **Resolve Paths**: Determine correct directory paths for specific coins (e.g., mapping "BTC" to root or subfolder).
    2.  **Read/Write Text**: safe wrappers for file I/O with encoding handling.
    3.  **Read/Write JSON**: Utilities for structured data persistence.
    4.  **Atomic Writes**: Preventing data corruption during asynchronous reads/writes.
    5.  **Hub Directory Management**: Locating the shared data directory for inter-process communication.

    Attributes:
        BASE_DIR (str): The root directory of the application, dynamically resolved relative to this file.
    """
    
    # Resolve project root (assuming this file is in src/utils/)
    # src/utils/ -> src/ -> root
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    @staticmethod
    def get_coin_folder(sym: str) -> str:
        """
        Get the absolute path for a specific coin's data directory.

        Legacy convention: 'BTC' data is stored in the project root, while other coins
        get their own subdirectories (e.g., ./ETH, ./XRP).

        Args:
            sym (str): The cryptocurrency symbol (e.g., "BTC", "ETH").

        Returns:
            str: Absolute path to the coin's directory.
        """
        sym = sym.upper()
        # "main folder is BTC folder" convention from legacy code
        return FileManager.BASE_DIR if sym == 'BTC' else os.path.join(FileManager.BASE_DIR, sym)

    @staticmethod
    def ensure_coin_directory(sym: str):
        """
        Ensure the directory for a specific coin exists.

        Args:
            sym (str): The cryptocurrency symbol.
        """
        folder = FileManager.get_coin_folder(sym)
        try:
            os.makedirs(folder, exist_ok=True)
        except Exception:
            pass

    # Alias for compatibility with older code calls
    ensure_coin_folder = ensure_coin_directory

    @staticmethod
    def read_text(path_or_sym, filename=None) -> str:
        """
        Read text content from a file safely.

        Supports two calling conventions:
        1.  `read_text("path/to/file.txt")` - Absolute or relative path.
        2.  `read_text("BTC", "signal.txt")` - Coin symbol and filename.

        Args:
            path_or_sym (str): Either a full path or a coin symbol.
            filename (str, optional): The filename if `path_or_sym` is a symbol.

        Returns:
            str: The file content, or empty string if file not found.
        """
        if filename is None:
            path = path_or_sym
        else:
            folder = FileManager.get_coin_folder(path_or_sym)
            path = os.path.join(folder, filename)
            
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except FileNotFoundError:
            return ""

    @staticmethod
    def write_text(path_or_sym, filename_or_content, content=None):
        """
        Write text content to a file.

        Supports two calling conventions:
        1.  `write_text("path/to/file.txt", "content")`
        2.  `write_text("BTC", "signal.txt", "content")`

        Args:
            path_or_sym (str): Full path or coin symbol.
            filename_or_content (str): Filename (if symbol used) or Content (if path used).
            content (str, optional): Content (if symbol used).
        """
        if content is None:
            path = path_or_sym
            text = filename_or_content
        else:
            folder = FileManager.get_coin_folder(path_or_sym)
            path = os.path.join(folder, filename_or_content)
            text = content
            
        try:
            # Ensure dir exists if full path provided
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w+", encoding="utf-8") as f:
                f.write(str(text))
        except Exception as e:
            # Silently fail or log? Legacy code often swallows errors
            pass

    @staticmethod
    def load_json(path: str) -> Dict[str, Any]:
        """
        Load a JSON file safely.

        Args:
            path (str): Absolute path to the JSON file.

        Returns:
            dict: The parsed JSON data, or an empty dict if not found or invalid.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    @staticmethod
    def save_json(path: str, data: Any):
        """
        Save data to a JSON file.

        Args:
            path (str): Absolute path to the destination file.
            data (Any): Serializable data (dict, list, etc.).
        """
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass

    @staticmethod
    def get_hub_dir() -> str:
        """
        Get the directory used for shared 'hub' data.

        Returns:
            str: Path to the hub data directory.
        """
        return os.environ.get("POWERTRADER_HUB_DIR") or os.path.join(FileManager.BASE_DIR, "hub_data")

    @staticmethod
    def get_runner_ready_path() -> str:
        """
        Get the path to the 'runner_ready.json' status file.

        This file is used to signal that the core logic loops are active.

        Returns:
            str: Absolute path to `runner_ready.json`.
        """
        return os.path.join(FileManager.get_hub_dir(), "runner_ready.json")

    @staticmethod
    def append_jsonl(path: str, data: Any):
        """
        Append a record to a JSON Lines (.jsonl) file.

        Useful for logs or trade history where we want to append without rewriting the whole file.

        Args:
            path (str): Absolute path to the file.
            data (Any): Data to append (will be serialized to a single line JSON).
        """
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data) + "\n")
        except Exception:
            pass

    @staticmethod
    def atomic_write_json(path: str, data: Any):
        """
        Write JSON data atomically to prevent partial reads.

        Writes to a `.tmp` file first, then uses `os.replace` to swap it in.
        This is critical for files shared between the Trainer/Thinker threads and the GUI,
        preventing the GUI from crashing due to reading a half-written file.

        Args:
            path (str): Target file path.
            data (Any): Data to serialize.
        """
        try:
            dir_name = os.path.dirname(path)
            os.makedirs(dir_name, exist_ok=True)

            # Create temp file in same directory
            temp_path = path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
                f.flush()
                os.fsync(f.fileno()) # Ensure write to disk

            # Atomic rename
            os.replace(temp_path, path)
        except Exception as e:
            # Fallback to standard save if atomic fails
            FileManager.save_json(path, data)

class MemoryManager:
    """
    Manager for Neural Memory persistence and caching.

    The 'Memory' system involves storing patterns (memories) and their associated weights.
    These are stored in multiple text files per timeframe (memories, weights, high_weights, low_weights).
    
    This class:
    1.  **Caches Data**: Keeps loaded memories in RAM (`_cache`) to avoid constant disk reads during training.
    2.  **Manages 'Dirty' State**: Only writes back to disk if changes have been made.
    3.  **Parses Legacy Formats**: Handles the specific text-based list formats used by the original AI core.

    Attributes:
        _cache (dict): A class-level dictionary storing loaded memory data keyed by `{symbol}_{timeframe}`.
    """
    _cache = {}

    @staticmethod
    def load_memory(sym: str, tf_choice: str) -> Dict[str, Any]:
        """
        Load memory files for a specific coin and timeframe.

        Checks the cache first. If missing, reads from disk.

        Args:
            sym (str): Coin symbol.
            tf_choice (str): Timeframe string (e.g., "1hour").

        Returns:
            dict: A dictionary containing lists for 'memory_list', 'weight_list', etc., and a 'dirty' flag.
        """
        cache_key = f"{sym}_{tf_choice}"
        if cache_key in MemoryManager._cache:
            return MemoryManager._cache[cache_key]

        data = {
            "memory_list": [],
            "weight_list": [],
            "high_weight_list": [],
            "low_weight_list": [],
            "dirty": False,
        }

        # Helper to read and parse list-like strings
        def _parse_list(filename, sep='~'):
            raw = FileManager.read_text(sym, filename)
            if not raw: return []
            # Legacy cleanup: remove quotes, brackets, etc.
            clean = raw.replace("'", "").replace(',', '').replace('"', '').replace(']', '').replace('[', '')
            return clean.split(sep) if sep == '~' else clean.split(' ')

        data["memory_list"] = _parse_list(f"memories_{tf_choice}.txt", '~')
        data["weight_list"] = _parse_list(f"memory_weights_{tf_choice}.txt", ' ')
        data["high_weight_list"] = _parse_list(f"memory_weights_high_{tf_choice}.txt", ' ')      
        data["low_weight_list"] = _parse_list(f"memory_weights_low_{tf_choice}.txt", ' ')        

        MemoryManager._cache[cache_key] = data
        return data

    @staticmethod
    def flush_memory(sym: str, tf_choice: str, force: bool = False):
        """
        Write memory data back to disk.

        Only writes if the 'dirty' flag is set or `force` is True.
        
        IMPORTANT: This method reconstructs the string representation of Python lists
        (e.g., "['val1', 'val2']") to maintain exact compatibility with the legacy file format.

        Args:
            sym (str): Coin symbol.
            tf_choice (str): Timeframe string.
            force (bool): If True, write even if 'dirty' is False.
        """
        cache_key = f"{sym}_{tf_choice}"
        if cache_key not in MemoryManager._cache:
            return

        data = MemoryManager._cache[cache_key]
        if not data.get("dirty") and not force:
            return

        # Helper to format and save
        def _save_list(filename, lst, sep='~'):
            # Legacy format reconstruction:
            # The original code used `file.write(str(weight_list))`.
            # This writes the Python string representation of the list, e.g., "['1.0', '1.0']".
            # We must replicate this behavior so other tools/legacy scripts can still read the files.
            content = str(lst)
            FileManager.write_text(sym, filename, content)

        _save_list(f"memories_{tf_choice}.txt", data["memory_list"])
        _save_list(f"memory_weights_{tf_choice}.txt", data["weight_list"])
        _save_list(f"memory_weights_high_{tf_choice}.txt", data["high_weight_list"])
        _save_list(f"memory_weights_low_{tf_choice}.txt", data["low_weight_list"])

        data["dirty"] = False
