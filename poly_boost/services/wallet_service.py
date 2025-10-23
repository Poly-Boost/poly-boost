"""
Wallet management service.

Provides functionality for managing and querying wallet information.
Note: This service is now primarily a wrapper around WalletManager.
Consider using WalletManager directly in most cases.
"""

from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
import logging

from py_clob_client.client import ClobClient

from poly_boost.core.wallet import Wallet
from poly_boost.core.wallet_manager import WalletManager


logger = logging.getLogger(__name__)


class WalletService:
    """
    Service for managing wallet information.

    Note: This service is now a thin wrapper around WalletManager.
    For new code, consider using WalletManager directly.
    """

    def __init__(
        self,
        clob_client: ClobClient,
        wallet_manager: Optional[WalletManager] = None
    ):
        """
        Initialize wallet service.

        Args:
            clob_client: Polymarket CLOB client instance
            wallet_manager: Optional WalletManager instance
        """
        self.clob_client = clob_client
        self.wallet_manager = wallet_manager or WalletManager()

    def register_wallet(self, wallet: Wallet) -> str:
        """
        Register a wallet for management.

        Args:
            wallet: Wallet instance

        Returns:
            Wallet api_address
        """
        self.wallet_manager.register(wallet)
        return wallet.api_address

    def get_wallet_info(self, wallet_address: str) -> Dict[str, Any]:
        """
        Get information about a wallet.

        Args:
            wallet_address: Wallet address (api_address or eoa_address)

        Returns:
            Wallet information dictionary
        """
        wallet = self.wallet_manager.get(wallet_address)

        if wallet is None:
            # Return info for unmanaged wallet
            return {
                "address": wallet_address,
                "name": "Unknown",
                "is_managed": False
            }

        # Import ProxyWallet for type checking
        from poly_boost.core.wallet import ProxyWallet

        info = {
            "address": wallet.api_address,
            "eoa_address": wallet.eoa_address,
            "name": wallet.name,
            "signature_type": wallet.signature_type,
            "is_managed": True,
            "is_tradable": wallet.requires_private_key
        }

        # Add proxy_address if it's a proxy wallet
        if isinstance(wallet, ProxyWallet):
            info["proxy_address"] = wallet.proxy_address

        return info

    def get_balance(self, wallet: Union[Wallet, str]) -> Decimal:
        """
        Get USDC balance for a wallet.

        Args:
            wallet: Wallet instance or wallet address string

        Returns:
            USDC balance

        Raises:
            Exception: If balance query fails
        """
        try:
            # Support both Wallet objects and address strings
            if isinstance(wallet, Wallet):
                address = wallet.api_address
                wallet_name = wallet.name
            else:
                address = wallet
                wallet_name = address

            # TODO: Implement using clob_client
            # balance = self.clob_client.get_balance(address)
            logger.info(f"Fetching balance for wallet: {wallet_name} ({address})")

            # Placeholder
            return Decimal("0")
        except Exception as e:
            logger.error(f"Failed to fetch balance: {e}")
            raise

    def list_managed_wallets(self) -> List[Dict[str, Any]]:
        """
        List all managed wallets.

        Returns:
            List of wallet information dictionaries
        """
        return [
            self.get_wallet_info(wallet.api_address)
            for wallet in self.wallet_manager.list_all()
        ]
