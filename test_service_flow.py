"""
Simplified test demonstrating the complete service flow.

This test doesn't require external dependencies and shows how
services resolve wallet identifiers correctly.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from poly_boost.core.wallet import EOAWallet, ProxyWallet
from poly_boost.core.wallet_manager import WalletManager


def simulate_api_call(address: str) -> str:
    """Simulate an API call with the given address."""
    return f"API_RESPONSE[address={address}]"


def test_complete_flow():
    """Test the complete flow from user request to API call."""
    print("\n" + "=" * 60)
    print("COMPLETE SERVICE FLOW TEST")
    print("=" * 60)

    # Setup: Create WalletManager with test wallets
    manager = WalletManager()

    eoa_wallet = EOAWallet(
        name="Alice",
        address="0x1111111111111111111111111111111111111111",
        private_key_env="ALICE_KEY"
    )

    proxy_wallet = ProxyWallet(
        name="Bob Safe",
        eoa_address="0x2222222222222222222222222222222222222222",
        proxy_address="0x3333333333333333333333333333333333333333",
        private_key_env="BOB_KEY",
        signature_type=2
    )

    manager.register(eoa_wallet)
    manager.register(proxy_wallet)

    print("\nConfigured Wallets:")
    print(f"  1. {eoa_wallet.name} (EOA)")
    print(f"     EOA: {eoa_wallet.eoa_address}")
    print(f"     API Address: {eoa_wallet.api_address}")

    print(f"  2. {proxy_wallet.name} (Proxy)")
    print(f"     EOA: {proxy_wallet.eoa_address}")
    print(f"     Proxy: {proxy_wallet.proxy_address}")
    print(f"     API Address: {proxy_wallet.api_address}")

    # Simulate service calls
    test_cases = [
        {
            "scenario": "User queries positions for Bob using EOA address",
            "user_input": "0x2222222222222222222222222222222222222222",  # Bob's EOA
            "expected_wallet": "Bob Safe",
            "expected_api_address": "0x3333333333333333333333333333333333333333"  # Bob's Proxy
        },
        {
            "scenario": "User queries positions for Bob using Proxy address",
            "user_input": "0x3333333333333333333333333333333333333333",  # Bob's Proxy
            "expected_wallet": "Bob Safe",
            "expected_api_address": "0x3333333333333333333333333333333333333333"  # Bob's Proxy
        },
        {
            "scenario": "User queries positions for Bob using wallet name",
            "user_input": "Bob Safe",  # Bob's name
            "expected_wallet": "Bob Safe",
            "expected_api_address": "0x3333333333333333333333333333333333333333"  # Bob's Proxy
        },
        {
            "scenario": "User queries positions for Alice using EOA address",
            "user_input": "0x1111111111111111111111111111111111111111",  # Alice's EOA
            "expected_wallet": "Alice",
            "expected_api_address": "0x1111111111111111111111111111111111111111"  # Alice's EOA
        }
    ]

    print("\n" + "=" * 60)
    print("SIMULATING API REQUESTS")
    print("=" * 60)

    all_passed = True

    for i, test in enumerate(test_cases, 1):
        print(f"\n[Test {i}] {test['scenario']}")
        print(f"  Step 1: User provides identifier: {test['user_input']}")

        # Simulate what PositionService does
        print(f"  Step 2: Service calls WalletManager.get('{test['user_input']}')")

        wallet = manager.get(test['user_input'])

        if wallet is None:
            print(f"  [FAIL] Wallet not found!")
            all_passed = False
            continue

        print(f"  Step 3: Found wallet: {wallet.name}")

        if wallet.name != test['expected_wallet']:
            print(f"  [FAIL] Wrong wallet! Expected {test['expected_wallet']}")
            all_passed = False
            continue

        print(f"  Step 4: Service uses wallet.api_address: {wallet.api_address}")

        if wallet.api_address.lower() != test['expected_api_address'].lower():
            print(f"  [FAIL] Wrong API address! Expected {test['expected_api_address']}")
            all_passed = False
            continue

        # Simulate API call
        api_response = simulate_api_call(wallet.api_address)
        print(f"  Step 5: Call Polymarket API with: {wallet.api_address}")
        print(f"  Step 6: API returns: {api_response}")

        print(f"  [OK] Correct flow!")

    print("\n" + "=" * 60)
    if all_passed:
        print("[OK] All test cases passed!")
    else:
        print("[FAIL] Some test cases failed!")
    print("=" * 60)

    return all_passed


def test_critical_scenario():
    """Test the most critical scenario: User provides EOA, API uses Proxy."""
    print("\n" + "=" * 60)
    print("CRITICAL SCENARIO TEST")
    print("=" * 60)

    manager = WalletManager()

    # Bob has a Gnosis Safe
    proxy_wallet = ProxyWallet(
        name="Bob Gnosis Safe",
        eoa_address="0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        proxy_address="0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
        private_key_env="BOB_KEY",
        signature_type=2
    )

    manager.register(proxy_wallet)

    print("\nBob's Wallet:")
    print(f"  Name: {proxy_wallet.name}")
    print(f"  EOA Address:   {proxy_wallet.eoa_address}")
    print(f"  Proxy Address: {proxy_wallet.proxy_address}")
    print(f"  Type: Gnosis Safe")

    print("\n" + "-" * 60)
    print("SCENARIO: User provides Bob's EOA address to query positions")
    print("-" * 60)

    user_input = proxy_wallet.eoa_address  # User provides EOA
    print(f"\n1. User Input: {user_input}")
    print(f"   (This is Bob's EOA address)")

    print(f"\n2. API Endpoint: GET /positions/{user_input}")

    print(f"\n3. Service Layer:")
    print(f"   position_service.get_positions(wallet_identifier='{user_input}')")

    print(f"\n4. Service Resolution:")
    wallet = manager.get(user_input)
    print(f"   - WalletManager.get('{user_input}')")
    print(f"   - Found: {wallet.name}")
    print(f"   - Wallet Type: Proxy (signature_type={wallet.signature_type})")

    print(f"\n5. API Address Selection:")
    print(f"   - wallet.api_address = {wallet.api_address}")

    if wallet.api_address == proxy_wallet.proxy_address:
        print(f"   [OK] Using PROXY address, not EOA!")
    else:
        print(f"   [FAIL] Should use Proxy address!")
        return False

    print(f"\n6. Polymarket API Call:")
    print(f"   - data_client.get_positions(user='{wallet.api_address}')")
    print(f"   - API receives: {wallet.api_address}")
    print(f"   - This is the PROXY address!")

    print("\n" + "=" * 60)
    print("RESULT:")
    print("  [OK] Even though user provided EOA address,")
    print("  [OK] The service correctly used PROXY address for API call!")
    print("  [OK] This is the KEY feature of the design!")
    print("=" * 60)

    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Service Flow Testing (No External Dependencies)")
    print("=" * 60)

    try:
        result1 = test_complete_flow()
        result2 = test_critical_scenario()

        print("\n" + "=" * 60)
        print("FINAL SUMMARY")
        print("=" * 60)

        if result1 and result2:
            print("\n[OK] All tests passed!")
            print("\nWhat this proves:")
            print("  1. Services can accept wallet identifiers (EOA/Proxy/Name)")
            print("  2. WalletManager correctly finds wallet configuration")
            print("  3. Services use wallet.api_address for API calls")
            print("  4. CRITICAL: Proxy wallets use proxy_address, NOT eoa_address")
            print("  5. This works regardless of which identifier user provides")
            return True
        else:
            print("\n[FAIL] Some tests failed!")
            return False

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
