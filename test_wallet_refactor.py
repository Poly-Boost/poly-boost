"""
Test script for wallet refactoring.

This script tests the new wallet abstraction layer without requiring
external dependencies.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from poly_boost.core.wallet import Wallet, EOAWallet, ProxyWallet, ReadOnlyWallet
from poly_boost.core.wallet_manager import WalletManager


def test_eoa_wallet():
    """Test EOA wallet creation and properties."""
    print("\n=== Testing EOA Wallet ===")

    wallet = EOAWallet(
        name="Test EOA",
        address="0x1234567890123456789012345678901234567890",
        private_key_env="TEST_PRIVATE_KEY"
    )

    print(f"Wallet: {wallet}")
    print(f"  Name: {wallet.name}")
    print(f"  API Address: {wallet.api_address}")
    print(f"  EOA Address: {wallet.eoa_address}")
    print(f"  Signature Type: {wallet.signature_type}")
    print(f"  Requires Private Key: {wallet.requires_private_key}")

    # For EOA, api_address should equal eoa_address
    assert wallet.api_address == wallet.eoa_address
    assert wallet.signature_type == 0

    print("[OK] EOA Wallet test passed")


def test_proxy_wallet():
    """Test Proxy wallet creation and properties."""
    print("\n=== Testing Proxy Wallet ===")

    wallet = ProxyWallet(
        name="Test Proxy",
        eoa_address="0x1111111111111111111111111111111111111111",
        proxy_address="0x2222222222222222222222222222222222222222",
        private_key_env="TEST_PRIVATE_KEY",
        signature_type=2
    )

    print(f"Wallet: {wallet}")
    print(f"  Name: {wallet.name}")
    print(f"  API Address: {wallet.api_address}")
    print(f"  EOA Address: {wallet.eoa_address}")
    print(f"  Proxy Address: {wallet.proxy_address}")
    print(f"  Signature Type: {wallet.signature_type}")
    print(f"  Requires Private Key: {wallet.requires_private_key}")

    # For Proxy, api_address should equal proxy_address
    assert wallet.api_address == wallet.proxy_address
    assert wallet.signature_type == 2

    print("[OK] Proxy Wallet test passed")


def test_readonly_wallet():
    """Test ReadOnly wallet creation and properties."""
    print("\n=== Testing ReadOnly Wallet ===")

    wallet = ReadOnlyWallet(
        name="Watched Trader",
        address="0x3333333333333333333333333333333333333333"
    )

    print(f"Wallet: {wallet}")
    print(f"  Name: {wallet.name}")
    print(f"  API Address: {wallet.api_address}")
    print(f"  Signature Type: {wallet.signature_type}")
    print(f"  Requires Private Key: {wallet.requires_private_key}")

    assert wallet.signature_type == -1
    assert not wallet.requires_private_key
    assert wallet.get_private_key() is None

    print("[OK] ReadOnly Wallet test passed")


def test_wallet_manager():
    """Test WalletManager registration and lookup."""
    print("\n=== Testing WalletManager ===")

    manager = WalletManager()

    # Create test wallets
    eoa_wallet = EOAWallet(
        name="EOA Wallet",
        address="0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        private_key_env="EOA_KEY"
    )

    proxy_wallet = ProxyWallet(
        name="Proxy Wallet",
        eoa_address="0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
        proxy_address="0xCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
        private_key_env="PROXY_KEY",
        signature_type=2
    )

    readonly_wallet = ReadOnlyWallet(
        name="Watched Wallet",
        address="0xDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD"
    )

    # Register wallets
    manager.register(eoa_wallet)
    manager.register(proxy_wallet)
    manager.register(readonly_wallet)

    print(f"Registered {len(manager.list_all())} wallets")
    print(f"  Tradable: {len(manager.list_tradable())}")
    print(f"  ReadOnly: {len(manager.list_readonly())}")

    # Test lookup by api_address
    print("\nTesting lookups:")

    # Lookup EOA by its address
    found = manager.get(eoa_wallet.api_address)
    assert found is eoa_wallet
    print(f"[OK] Found EOA wallet by api_address")

    # Lookup Proxy by its proxy_address (api_address)
    found = manager.get(proxy_wallet.api_address)
    assert found is proxy_wallet
    print(f"[OK] Found Proxy wallet by api_address (proxy_address)")

    # Lookup Proxy by its eoa_address
    found = manager.get(proxy_wallet.eoa_address)
    assert found is proxy_wallet
    print(f"[OK] Found Proxy wallet by eoa_address")

    # Test case-insensitive lookup
    found = manager.get(eoa_wallet.api_address.upper())
    assert found is eoa_wallet
    print(f"[OK] Case-insensitive lookup works")

    # Test get_or_raise
    found = manager.get_or_raise(proxy_wallet.api_address)
    assert found is proxy_wallet
    print(f"[OK] get_or_raise works")

    # Test exception on not found
    try:
        manager.get_or_raise("0xNONEXISTENT")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"[OK] get_or_raise raises ValueError correctly: {e}")

    print("[OK] WalletManager test passed")


def test_wallet_manager_from_config():
    """Test WalletManager.from_config()."""
    print("\n=== Testing WalletManager.from_config ===")

    config = {
        "user_wallets": [
            {
                "name": "My EOA",
                "address": "0x1111111111111111111111111111111111111111",
                "signature_type": 0,
                "private_key_env": "MY_EOA_KEY"
            },
            {
                "name": "My Proxy",
                "address": "0x2222222222222222222222222222222222222222",
                "proxy_address": "0x3333333333333333333333333333333333333333",
                "signature_type": 2,
                "private_key_env": "MY_PROXY_KEY"
            }
        ],
        "watch_wallets": [
            {
                "name": "Trader to Watch",
                "address": "0x4444444444444444444444444444444444444444"
            }
        ]
    }

    manager = WalletManager.from_config(config)

    print(f"Loaded {len(manager.list_all())} wallets from config")
    print(f"  Tradable: {len(manager.list_tradable())}")
    print(f"  ReadOnly: {len(manager.list_readonly())}")

    # Verify EOA wallet
    eoa = manager.get_by_name("My EOA")
    assert eoa is not None
    assert isinstance(eoa, EOAWallet)
    assert eoa.signature_type == 0
    print(f"[OK] EOA wallet loaded correctly")

    # Verify Proxy wallet
    proxy = manager.get_by_name("My Proxy")
    assert proxy is not None
    assert isinstance(proxy, ProxyWallet)
    assert proxy.signature_type == 2
    assert proxy.proxy_address.lower() == "0x3333333333333333333333333333333333333333"
    print(f"[OK] Proxy wallet loaded correctly")

    # Verify ReadOnly wallet
    readonly = manager.get_by_name("Trader to Watch")
    assert readonly is not None
    assert isinstance(readonly, ReadOnlyWallet)
    assert not readonly.requires_private_key
    print(f"[OK] ReadOnly wallet loaded correctly")

    print("[OK] WalletManager.from_config test passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Wallet Refactoring")
    print("=" * 60)

    try:
        test_eoa_wallet()
        test_proxy_wallet()
        test_readonly_wallet()
        test_wallet_manager()
        test_wallet_manager_from_config()

        print("\n" + "=" * 60)
        print("[OK] All tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        raise


if __name__ == "__main__":
    main()
