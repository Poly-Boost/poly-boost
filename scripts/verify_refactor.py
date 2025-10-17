"""
Verification script to test that all refactored components work.

Run with: python scripts/verify_refactor.py
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def test_core_imports():
    """Test core module imports."""
    print("Testing core module imports...")
    try:
        from poly_boost.core.config_loader import load_config
        from poly_boost.core.wallet_monitor import WalletMonitor
        from poly_boost.core.copy_trader import CopyTrader
        from poly_boost.core.in_memory_activity_queue import InMemoryActivityQueue
        print("✓ Core imports: OK")
        return True
    except Exception as e:
        print(f"✗ Core imports failed: {e}")
        return False


def test_services_imports():
    """Test services layer imports."""
    print("Testing services layer imports...")
    try:
        from poly_boost.services.position_service import PositionService
        from poly_boost.services.trading_service import TradingService
        from poly_boost.services.wallet_service import WalletService
        print("✓ Services imports: OK")
        return True
    except Exception as e:
        print(f"✗ Services imports failed: {e}")
        return False


def test_api_imports():
    """Test FastAPI imports."""
    print("Testing FastAPI imports...")
    try:
        from poly_boost.api.main import app
        from poly_boost.api.routes import positions, trading, wallets
        print("✓ FastAPI imports: OK")
        return True
    except Exception as e:
        print(f"✗ FastAPI imports failed: {e}")
        return False


def test_bot_imports():
    """Test Telegram bot imports."""
    print("Testing Telegram bot imports...")
    try:
        from poly_boost.bot.keyboards import get_main_menu_keyboard
        from poly_boost.bot.handlers.position_handler import show_positions_menu
        from poly_boost.bot.handlers.trading_handler import show_trading_menu
        print("✓ Telegram bot imports: OK")
        return True
    except Exception as e:
        print(f"✗ Telegram bot imports failed: {e}")
        return False


def test_cli_import():
    """Test CLI import."""
    print("Testing CLI import...")
    try:
        from poly_boost import cli
        print("✓ CLI import: OK")
        return True
    except Exception as e:
        print(f"✗ CLI import failed: {e}")
        return False


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Polymarket Copy Trading Bot - Refactoring Verification")
    print("=" * 60)
    print()

    results = []

    # Run all tests
    results.append(("Core", test_core_imports()))
    results.append(("Services", test_services_imports()))
    results.append(("FastAPI", test_api_imports()))
    results.append(("Telegram Bot", test_bot_imports()))
    results.append(("CLI", test_cli_import()))

    # Summary
    print()
    print("=" * 60)
    print("Summary:")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:20} {status}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("✓ All verification tests passed!")
        print()
        print("Next steps:")
        print("1. Install dependencies: uv sync")
        print("2. Configure: config/config.yaml")
        print("3. Run CLI: python run_cli.py")
        print("4. Run API: python run_api.py")
        print("5. Run Bot: python run_bot.py")
        return 0
    else:
        print("✗ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
