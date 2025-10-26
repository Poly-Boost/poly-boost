"""
Test script for order and activity API endpoints.

This script tests the newly implemented endpoints:
- GET /orders/{wallet}/history - Get trade history
- GET /activity/{wallet} - Get activity summary
- GET /activity/{wallet}/list - Get activity list
"""

import requests
import sys
from typing import Dict, Any

# API base URL
BASE_URL = "http://localhost:8000"

# Test wallet address - replace with a valid wallet address from your config
# You can get this from your config.yaml wallets section
TEST_WALLET_ADDRESS = "your_wallet_address_here"


def test_endpoint(endpoint: str, params: Dict[str, Any] = None) -> None:
    """Test an API endpoint and print the response."""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n{'='*80}")
    print(f"Testing: {endpoint}")
    print(f"URL: {url}")
    if params:
        print(f"Params: {params}")
    print(f"{'='*80}")

    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Response Type: {type(data)}")

            if isinstance(data, list):
                print(f"Number of items: {len(data)}")
                if len(data) > 0:
                    print(f"\nFirst item:")
                    print_dict(data[0], indent=2)
            elif isinstance(data, dict):
                print(f"\nResponse:")
                print_dict(data, indent=2)

            print(f"\n✓ Test PASSED")
        else:
            print(f"Error: {response.text}")
            print(f"\n✗ Test FAILED")

    except requests.exceptions.ConnectionError:
        print(f"✗ Connection Error: Could not connect to {BASE_URL}")
        print(f"   Make sure the API server is running:")
        print(f"   cd /path/to/poly-boost && python -m poly_boost.api.main")
    except Exception as e:
        print(f"✗ Error: {e}")
        print(f"\n✗ Test FAILED")


def print_dict(d: Dict[str, Any], indent: int = 0) -> None:
    """Pretty print a dictionary with indentation."""
    for key, value in list(d.items())[:5]:  # Show first 5 keys
        if isinstance(value, dict):
            print(f"{' ' * indent}{key}:")
            print_dict(value, indent + 2)
        elif isinstance(value, list):
            print(f"{' ' * indent}{key}: [{len(value)} items]")
        else:
            # Truncate long values
            str_value = str(value)
            if len(str_value) > 50:
                str_value = str_value[:50] + "..."
            print(f"{' ' * indent}{key}: {str_value}")

    if len(d) > 5:
        print(f"{' ' * indent}... ({len(d) - 5} more fields)")


def main():
    """Run all endpoint tests."""
    print("=" * 80)
    print("API Endpoint Tests for Orders and Activity")
    print("=" * 80)

    # Check if wallet address is set
    if TEST_WALLET_ADDRESS == "your_wallet_address_here":
        print("\n⚠️  WARNING: Please update TEST_WALLET_ADDRESS in this script")
        print("   You can find wallet addresses in your config.yaml file\n")

        # Try to get wallet list
        try:
            response = requests.get(f"{BASE_URL}/wallets/", timeout=10)
            if response.status_code == 200:
                wallets = response.json()
                if wallets:
                    global TEST_WALLET_ADDRESS
                    TEST_WALLET_ADDRESS = wallets[0]['address']
                    print(f"✓ Using first wallet from config: {TEST_WALLET_ADDRESS}\n")
        except Exception as e:
            print(f"Could not fetch wallets: {e}")
            sys.exit(1)

    # Test 1: Get active orders (existing endpoint)
    test_endpoint(f"/orders/{TEST_WALLET_ADDRESS}")

    # Test 2: Get trade history (new endpoint)
    test_endpoint(f"/orders/{TEST_WALLET_ADDRESS}/history")

    # Test 3: Get activity summary (new endpoint)
    test_endpoint(f"/activity/{TEST_WALLET_ADDRESS}")

    # Test 4: Get activity list (new endpoint)
    test_endpoint(f"/activity/{TEST_WALLET_ADDRESS}/list", params={"limit": 10})

    # Test 5: Get activity list with filters
    test_endpoint(
        f"/activity/{TEST_WALLET_ADDRESS}/list",
        params={
            "limit": 5,
            "activity_type": "TRADE",
            "sort_direction": "DESC"
        }
    )

    print("\n" + "=" * 80)
    print("All tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
