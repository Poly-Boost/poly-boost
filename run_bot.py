"""
Telegram Bot launcher script.

Run with: python run_bot.py
"""

import sys
from pathlib import Path

# Ensure the project root is in sys.path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    from poly_boost.bot.main import main
    main()
