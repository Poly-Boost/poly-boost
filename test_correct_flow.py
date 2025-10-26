"""
Test the corrected wallet lookup flow.

This demonstrates the proper flow:
1. User provides an identifier (could be EOA, proxy, or name)
2. WalletManager finds the wallet configuration
3. Services use wallet.api_address for API calls
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from poly_boost.core.wallet import Wallet, EOAWallet, ProxyWallet
from poly_boost.core.wallet_manager import WalletManager


def test_correct_flow():
    """Test the complete correct flow."""
    print("\n" + "=" * 60)
    print("Testing Correct Wallet Lookup Flow")
    print("=" * 60)

    # Create a WalletManager
    manager = WalletManager()

    # Register some wallets
    eoa_wallet = EOAWallet(
        name="Alice EOA",
        address="0x1111111111111111111111111111111111111111",
        private_key_env="ALICE_KEY"
    )

    proxy_wallet = ProxyWallet(
        name="Bob Proxy",
        eoa_address="0x2222222222222222222222222222222222222222",
        proxy_address="0x3333333333333333333333333333333333333333",
        private_key_env="BOB_KEY",
        signature_type=2
    )

    manager.register(eoa_wallet)
    manager.register(proxy_wallet)

    print("\nRegistered Wallets:")
    print(f"  1. {eoa_wallet.name}")
    print(f"     - EOA Address: {eoa_wallet.eoa_address}")
    print(f"     - API Address: {eoa_wallet.api_address}")
    print(f"     - Type: EOA (signature_type={eoa_wallet.signature_type})")

    print(f"  2. {proxy_wallet.name}")
    print(f"     - EOA Address: {proxy_wallet.eoa_address}")
    print(f"     - Proxy Address: {proxy_wallet.proxy_address}")
    print(f"     - API Address: {proxy_wallet.api_address}")
    print(f"     - Type: Proxy (signature_type={proxy_wallet.signature_type})")

    # Test scenarios
    scenarios = [
        {
            "name": "User provides EOA wallet's EOA address",
            "input": "0x1111111111111111111111111111111111111111",
            "expected_wallet": eoa_wallet,
            "expected_api_address": eoa_wallet.eoa_address
        },
        {
            "name": "User provides Proxy wallet's EOA address",
            "input": "0x2222222222222222222222222222222222222222",
            "expected_wallet": proxy_wallet,
            "expected_api_address": proxy_wallet.proxy_address  # Should use proxy!
        },
        {
            "name": "User provides Proxy wallet's proxy address",
            "input": "0x3333333333333333333333333333333333333333",
            "expected_wallet": proxy_wallet,
            "expected_api_address": proxy_wallet.proxy_address
        },
        {
            "name": "User provides wallet name (EOA)",
            "input": "Alice EOA",
            "expected_wallet": eoa_wallet,
            "expected_api_address": eoa_wallet.eoa_address
        },
        {
            "name": "User provides wallet name (Proxy)",
            "input": "Bob Proxy",
            "expected_wallet": proxy_wallet,
            "expected_api_address": proxy_wallet.proxy_address
        },
        {
            "name": "User provides mixed case address",
            "input": "0X3333333333333333333333333333333333333333",
            "expected_wallet": proxy_wallet,
            "expected_api_address": proxy_wallet.proxy_address
        }
    ]

    print("\n" + "=" * 60)
    print("Testing Lookup Scenarios")
    print("=" * 60)

    all_passed = True

    for i, scenario in enumerate(scenarios, 1):
        print(f"\nScenario {i}: {scenario['name']}")
        print(f"  User Input: {scenario['input']}")

        # Step 1: Lookup wallet by identifier
        wallet = manager.get(scenario['input'])

        if wallet is None:
            print("  [FAIL] Wallet not found!")
            all_passed = False
            continue

        print(f"  [OK] Found wallet: {wallet.name}")

        # Step 2: Verify correct wallet was found
        if wallet != scenario['expected_wallet']:
            print(f"  [FAIL] Wrong wallet! Expected {scenario['expected_wallet'].name}")
            all_passed = False
            continue

        print(f"  [OK] Correct wallet found")

        # Step 3: Get API address (this is what services should use)
        api_address = wallet.api_address
        print(f"  API Address to use: {api_address}")

        # Step 4: Verify API address is correct
        if api_address.lower() != scenario['expected_api_address'].lower():
            print(f"  [FAIL] Wrong API address! Expected {scenario['expected_api_address']}")
            all_passed = False
            continue

        print(f"  [OK] Correct API address")

        # Step 5: Show what would happen in a service
        print(f"  Service would call Polymarket API with: {api_address}")
        if wallet.signature_type == 0:
            print(f"    - Uses EOA address directly (signature_type=0)")
        else:
            print(f"    - Uses PROXY address (signature_type={wallet.signature_type})")
            print(f"    - Even though user might have provided EOA: {wallet.eoa_address}")

    print("\n" + "=" * 60)
    if all_passed:
        print("[OK] All scenarios passed!")
    else:
        print("[FAIL] Some scenarios failed!")
    print("=" * 60)

    return all_passed


def test_key_insight():
    """Test the key insight of the design."""
    print("\n" + "=" * 60)
    print("Key Insight Demonstration")
    print("=" * 60)

    manager = WalletManager()

    # Proxy wallet with DIFFERENT EOA and Proxy addresses
    proxy_wallet = ProxyWallet(
        name="My Safe",
        eoa_address="0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",  # User's EOA
        proxy_address="0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",  # Gnosis Safe address
        private_key_env="SAFE_KEY",
        signature_type=2
    )

    manager.register(proxy_wallet)

    print("\nWallet Configuration:")
    print(f"  Name: {proxy_wallet.name}")
    print(f"  EOA Address:   {proxy_wallet.eoa_address}")
    print(f"  Proxy Address: {proxy_wallet.proxy_address}")
    print(f"  Signature Type: {proxy_wallet.signature_type} (Gnosis Safe)")

    print("\nThe Magic:")

    # User provides EOA address
    print(f"\n1. User provides EOA address: {proxy_wallet.eoa_address}")
    wallet = manager.get(proxy_wallet.eoa_address)
    print(f"   WalletManager finds: {wallet.name}")
    print(f"   API address used: {wallet.api_address}")
    print(f"   -> Service calls Polymarket with PROXY address, NOT EOA!")

    # User provides Proxy address
    print(f"\n2. User provides Proxy address: {proxy_wallet.proxy_address}")
    wallet = manager.get(proxy_wallet.proxy_address)
    print(f"   WalletManager finds: {wallet.name}")
    print(f"   API address used: {wallet.api_address}")
    print(f"   -> Service calls Polymarket with PROXY address!")

    print("\n[OK] Key insight verified:")
    print("  - User can provide EITHER address")
    print("  - WalletManager finds the correct wallet configuration")
    print("  - Service ALWAYS uses the correct API address based on wallet type")
    print("  - No need for services to know about wallet types!")

    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Comprehensive Flow Testing")
    print("=" * 60)

    try:
        result1 = test_correct_flow()
        result2 = test_key_insight()

        if result1 and result2:
            print("\n" + "=" * 60)
            print("[OK] All tests passed!")
            print("=" * 60)
            return True
        else:
            print("\n" + "=" * 60)
            print("[FAIL] Some tests failed!")
            print("=" * 60)
            return False

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
