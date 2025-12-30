import sys
import os

# Add project root to path
# Assumes this script is in tools/ directory, so root is one level up.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

import traceback

try:
    print(f"Verifying imports from root: {project_root}")
    import src.config.settings
    import src.utils.file_manager
    import src.api.robinhood
    import src.api.kucoin
    import src.core.neural
    import src.core.thinker
    import src.core.trader
    import src.core.trainer
    import src.ui.styles.theme
    import src.ui.data
    import src.ui.components.tiles
    import src.ui.components.chart
    import src.ui.components.account_history
    import src.ui.app
    import main
    print("✅ All imports successful!")
except Exception as e:
    print(f"❌ Import failed: {e}")
    traceback.print_exc()
    sys.exit(1)
