"""
Order management service.

Provides functionality for creating and executing orders on Polymarket,
including market orders, limit orders, and reward claiming.
"""

from typing import Optional, Dict, Any, List
from decimal import Decimal, ROUND_DOWN
import logging

from polymarket_apis.clients.clob_client import PolymarketClobClient
from polymarket_apis.clients.web3_client import PolymarketWeb3Client
from polymarket_apis.types.clob_types import OrderArgs, MarketOrderArgs, OrderType

from poly_boost.core.wallet import Wallet


logger = logging.getLogger(__name__)


class OrderService:
    """Service for managing and executing orders."""

    def __init__(
        self,
        wallet: Wallet,
        clob_client: PolymarketClobClient,
        web3_client: PolymarketWeb3Client
    ):
        """
        Initialize order service.

        Args:
            wallet: Wallet instance (encapsulates address and signature type)
            clob_client: Polymarket CLOB client instance
            web3_client: Polymarket Web3 client instance
        """
        self.wallet = wallet
        self.clob_client = clob_client
        self.web3_client = web3_client

    def sell_position_market(
        self,
        token_id: str,
        amount: Optional[float] = None,
        order_type: OrderType = OrderType.FOK
    ) -> Dict[str, Any]:
        """
        Sell position at market price.

        Args:
            token_id: Token ID to sell
            amount: Amount to sell (None = sell all available)
            order_type: Order type (FOK or GTC)

        Returns:
            Order execution result

        Raises:
            Exception: If order execution fails
        """
        try:
            # Get current token balance if amount not specified
            if amount is None:
                # Use wallet's api_address (automatically correct for EOA/Proxy)
                balance = self.web3_client.get_token_balance(token_id, self.wallet.api_address)
                amount = balance
                logger.info(f"Selling all available balance: {amount} from {self.wallet.name}")
            
            if amount <= 0:
                raise ValueError("Amount must be greater than 0")

            logger.info(
                f"Creating market sell order: token_id={token_id}, "
                f"amount={amount}, order_type={order_type}"
            )

            # Create market order args
            market_order_args = MarketOrderArgs(
                token_id=token_id,
                amount=amount,
                side="SELL",
                order_type=order_type,
                price=0,  # Will be calculated by clob_client
                fee_rate_bps=0  # Will be resolved by clob_client
            )

            # Create and post market order
            response = self.clob_client.create_and_post_market_order(
                order_args=market_order_args,
                order_type=order_type
            )

            logger.info(f"Market sell order executed: {response}")

            return {
                "status": "success",
                "order_id": response.order_id if response else None,
                "token_id": token_id,
                "amount": amount,
                "side": "SELL",
                "order_type": "market",
                "response": response.model_dump() if response else None
            }

        except Exception as e:
            logger.error(f"Failed to execute market sell order: {e}")
            raise

    def sell_position_limit(
        self,
        token_id: str,
        price: float,
        amount: Optional[float] = None,
        order_type: OrderType = OrderType.GTC
    ) -> Dict[str, Any]:
        """
        Sell position with limit price.

        Args:
            token_id: Token ID to sell
            price: Limit price
            amount: Amount to sell (None = sell all available)
            order_type: Order type (GTC or GTD)

        Returns:
            Order creation result

        Raises:
            Exception: If order creation fails
        """
        try:
            # Get current token balance if amount not specified
            if amount is None:
                # Use wallet's api_address (automatically correct for EOA/Proxy)
                balance = self.web3_client.get_token_balance(token_id, self.wallet.api_address)
                amount = balance
                logger.info(f"Selling all available balance: {amount} from {self.wallet.name}")
            
            if amount <= 0:
                raise ValueError("Amount must be greater than 0")
            
            if not (0 < price < 1):
                raise ValueError("Price must be between 0 and 1")

            logger.info(
                f"Creating limit sell order: token_id={token_id}, "
                f"price={price}, amount={amount}, order_type={order_type}"
            )

            # Create order args
            order_args = OrderArgs(
                token_id=token_id,
                price=price,
                size=amount,
                side="SELL",
                fee_rate_bps=0  # Will be resolved by clob_client
            )

            # Create and post order
            response = self.clob_client.create_and_post_order(
                order_args=order_args,
                order_type=order_type
            )

            logger.info(f"Limit sell order created: {response}")

            return {
                "status": "success",
                "order_id": response.order_id if response else None,
                "token_id": token_id,
                "amount": amount,
                "price": price,
                "side": "SELL",
                "order_type": "limit",
                "response": response.model_dump() if response else None
            }

        except Exception as e:
            logger.error(f"Failed to create limit sell order: {e}")
            raise

    def buy_position_market(
        self,
        token_id: str,
        amount: float,
        order_type: OrderType = OrderType.FOK
    ) -> Dict[str, Any]:
        """
        Buy position at market price.

        Args:
            token_id: Token ID to buy
            amount: Amount to buy
            order_type: Order type (FOK or GTC)

        Returns:
            Order execution result

        Raises:
            Exception: If order execution fails
        """
        try:
            if amount <= 0:
                raise ValueError("Amount must be greater than 0")

            logger.info(
                f"Creating market buy order: token_id={token_id}, "
                f"amount={amount}, order_type={order_type}"
            )

            # Create market order args
            market_order_args = MarketOrderArgs(
                token_id=token_id,
                amount=amount,
                side="BUY",
                order_type=order_type,
                price=0,  # Will be calculated by clob_client
                fee_rate_bps=0  # Will be resolved by clob_client
            )

            # Create and post market order
            response = self.clob_client.create_and_post_market_order(
                order_args=market_order_args,
                order_type=order_type
            )

            logger.info(f"Market buy order executed: {response}")

            return {
                "status": "success",
                "order_id": response.order_id if response else None,
                "token_id": token_id,
                "amount": amount,
                "side": "BUY",
                "order_type": "market",
                "response": response.model_dump() if response else None
            }

        except Exception as e:
            logger.error(f"Failed to execute market buy order: {e}")
            raise

    def buy_position_limit(
        self,
        token_id: str,
        price: float,
        amount: float,
        order_type: OrderType = OrderType.GTC
    ) -> Dict[str, Any]:
        """
        Buy position with limit price.

        Args:
            token_id: Token ID to buy
            price: Limit price
            amount: Amount to buy
            order_type: Order type (GTC or GTD)

        Returns:
            Order creation result

        Raises:
            Exception: If order creation fails
        """
        try:
            if amount <= 0:
                raise ValueError("Amount must be greater than 0")
            
            if not (0 < price < 1):
                raise ValueError("Price must be between 0 and 1")

            logger.info(
                f"Creating limit buy order: token_id={token_id}, "
                f"price={price}, amount={amount}, order_type={order_type}"
            )

            # Create order args
            order_args = OrderArgs(
                token_id=token_id,
                price=price,
                size=amount,
                side="BUY",
                fee_rate_bps=0  # Will be resolved by clob_client
            )

            # Create and post order
            response = self.clob_client.create_and_post_order(
                order_args=order_args,
                order_type=order_type
            )

            logger.info(f"Limit buy order created: {response}")

            return {
                "status": "success",
                "order_id": response.order_id if response else None,
                "token_id": token_id,
                "amount": amount,
                "price": price,
                "side": "BUY",
                "order_type": "limit",
                "response": response.model_dump() if response else None
            }

        except Exception as e:
            logger.error(f"Failed to create limit buy order: {e}")
            raise

    def _get_token_balance_wei(self, token_id: str, address: str) -> int:
        """Return raw ERC1155 balance for ``token_id`` owned by ``address``."""

        balance_wei = self.web3_client.conditional_tokens.functions.balanceOf(
            self.web3_client.w3.to_checksum_address(address),
            int(token_id)
        ).call()
        return int(balance_wei)

    @staticmethod
    def _apply_safety_margin(balance_wei: int) -> int:
        """Shrink ``balance_wei`` slightly to avoid edge-case underflows."""

        if balance_wei <= 0:
            return 0

        margin = max(1, int(balance_wei * 0.00001))  # 0.001% or 1 wei
        safe_value = balance_wei - margin
        return safe_value if safe_value > 0 else 0

    @staticmethod
    def _to_wei(amount: float) -> int:
        """Convert a decimal USDC amount to on-chain integer units (6dp)."""

        if amount <= 0:
            return 0

        quantized = (Decimal(str(amount)) * Decimal("1000000")).quantize(
            Decimal("1"), rounding=ROUND_DOWN
        )
        return int(quantized)

    @staticmethod
    def _normalize_market_tokens(market: Any) -> List[Dict[str, Any]]:
        """Extract token metadata while preserving on-chain ordering."""

        raw_tokens: List[Any] = []
        if isinstance(market, dict):
            raw_tokens = market.get("tokens") or market.get("token_ids") or []
        else:
            raw_tokens = (
                getattr(market, "token_ids", None)
                or getattr(market, "tokens", None)
                or []
            )

        normalized: List[Dict[str, Any]] = []
        for token in raw_tokens:
            if isinstance(token, dict):
                token_id = token.get("token_id") or token.get("tokenId")
                outcome = token.get("outcome")
            else:
                token_id = getattr(token, "token_id", None) or getattr(token, "tokenId", None)
                outcome = getattr(token, "outcome", None)

            normalized.append({"id": token_id, "outcome": outcome})

        return normalized

    @staticmethod
    def _infer_neg_risk(market: Any) -> bool:
        """Infer whether the market is negative-risk. Defaults to True."""

        candidates = ("neg_risk", "negRisk", "negative_risk", "negativeRisk")

        for key in candidates:
            if isinstance(market, dict):
                value = market.get(key)
            else:
                value = getattr(market, key, None)

            if value is not None:
                return bool(value)

        return True

    def claim_rewards(
        self,
        condition_id: str,
        token_id: str,
        amount: float,
    ) -> Dict[str, Any]:
        """
        Claim rewards by redeeming positions.

        Args:
            condition_id: Condition ID of the resolved market
            token_id: Token ID to redeem
            amount: Requested amount to redeem

        Returns:
            Transaction result

        Raises:
            Exception: If redemption fails
        """
        try:
            if amount <= 0:
                raise ValueError("Amount must be greater than 0")

            # High-level flow:
            # 1. Resolve market metadata to understand outcome ordering.
            # 2. Read on-chain balances for each outcome owned by this wallet.
            # 3. Clamp requested amount to the available balance (with a safety margin).
            # 4. Redeem with the final amounts so the adapter never sees an over-withdrawal.

            logger.info(
                f"Claiming rewards for condition_id={condition_id}, "
                f"token_id={token_id}, requested amount={amount}"
            )

            # EOA wallet -> api_address already equals the EOA address
            wallet_address = self.wallet.api_address
            logger.info(
                f"Wallet: {self.wallet.name}, signature type: {self.wallet.signature_type}, "
                f"address: {wallet_address}"
            )

            market = self.clob_client.get_market(condition_id)
            # Polymarket SDK exposes tokens as token_ids on ClobMarket; fall back to dict shape.
            token_entries = self._normalize_market_tokens(market)

            if not token_entries:
                logger.warning(
                    "Market payload missing token metadata; using requested token only"
                )
                token_entries = [{"id": token_id, "outcome": None}]

            token_id_lower = token_id.lower()
            target_index = next(
                (idx for idx, entry in enumerate(token_entries)
                 if entry.get("id") and entry["id"].lower() == token_id_lower),
                None,
            )

            if target_index is None:
                # When the requested token isn't in metadata, treat it as slot 0 and continue.
                logger.warning(
                    "Token %s not found in market metadata; prepending fallback entry",
                    token_id,
                )
                token_entries.insert(0, {"id": token_id, "outcome": None})
                target_index = 0

            slot_count = max(len(token_entries), 2)
            resolved_token_ids: List[Optional[str]] = [
                token_entries[idx]["id"] if idx < len(token_entries) else None
                for idx in range(slot_count)
            ]

            requested_wei = self._to_wei(amount)
            if requested_wei <= 0:
                raise ValueError(f"No redeemable balance for token {token_id}")

            amounts_wei: List[int] = [0] * slot_count
            for idx, resolved_id in enumerate(resolved_token_ids):
                if not resolved_id:
                    continue

                # Pull raw ERC1155 balance for each outcome and shave a tiny margin to
                # avoid underflow if someone else redeems a few wei between read and tx.
                balance_wei = self._get_token_balance_wei(resolved_id, wallet_address)
                safe_balance_wei = self._apply_safety_margin(balance_wei)

                logger.info(
                    "Token slot %s (id=%s) balance=%s wei (safe=%s wei)",
                    idx,
                    resolved_id,
                    balance_wei,
                    safe_balance_wei,
                )

                if idx == target_index:
                    # Only redeem at most what we hold (after safety margin).
                    chosen_wei = min(requested_wei, safe_balance_wei)
                    if chosen_wei <= 0:
                        raise ValueError(
                            f"Requested redeem amount exceeds available balance for token {token_id}"
                        )
                    amounts_wei[idx] = chosen_wei
                elif safe_balance_wei > 0:
                    # Include the sibling outcome so NegRiskAdapter can burn pairs if needed.
                    amounts_wei[idx] = safe_balance_wei

            if not any(amounts_wei):
                raise ValueError(f"No redeemable balance detected for condition {condition_id}")

            # Neg-risk flag decides between adapter.redeemPositions and conditionalTokens.redeemPositions.
            neg_risk = self._infer_neg_risk(market)

            amounts = [wei / 1_000_000 for wei in amounts_wei]
            logger.info("Final redeem amounts (wei): %s", amounts_wei)
            logger.info("Final redeem amounts (USDC): %s", amounts)

            tx_hash = self.web3_client.redeem_position(
                condition_id=condition_id,
                amounts=amounts,
                neg_risk=neg_risk,
            )

            logger.info(f"Rewards claimed successfully. Transaction: {tx_hash}")

            return {
                "status": "success",
                "condition_id": condition_id,
                "amounts": amounts,
                "tx_hash": tx_hash,
                "message": "Rewards claimed successfully"
            }

        except Exception as e:
            logger.error(f"Failed to claim rewards: {e}")
            raise


    def get_orders(
        self,
        order_id: Optional[str] = None,
        condition_id: Optional[str] = None,
        token_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get active orders with market names.

        Args:
            order_id: Filter by order ID
            condition_id: Filter by condition ID
            token_id: Filter by token ID

        Returns:
            List of active orders with market_name field added

        Raises:
            Exception: If query fails
        """
        try:
            logger.info(
                f"Getting orders: order_id={order_id}, "
                f"condition_id={condition_id}, token_id={token_id}"
            )

            orders = self.clob_client.get_orders(
                order_id=order_id,
                condition_id=condition_id,
                token_id=token_id
            )

            # Convert to dict and enrich with market names
            orders_data = []
            market_cache = {}  # Cache to avoid duplicate API calls

            for order in orders:
                order_dict = order.model_dump()

                # Get market name from cache or API
                cond_id = order_dict.get('condition_id')
                if cond_id:
                    if cond_id not in market_cache:
                        try:
                            market = self.clob_client.get_market(cond_id)
                            market_cache[cond_id] = market.question
                            logger.debug(f"Fetched market name for {cond_id}: {market.question}")
                        except Exception as e:
                            logger.warning(f"Failed to fetch market name for {cond_id}: {e}")
                            market_cache[cond_id] = None

                    order_dict['market_name'] = market_cache[cond_id]
                else:
                    order_dict['market_name'] = None

                orders_data.append(order_dict)

            logger.info(f"Returned {len(orders_data)} orders with market names")
            return orders_data

        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            raise

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an active order.

        Args:
            order_id: Order ID to cancel

        Returns:
            Cancellation result

        Raises:
            Exception: If cancellation fails
        """
        try:
            logger.info(f"Cancelling order: {order_id}")

            response = self.clob_client.cancel_order(order_id)

            logger.info(f"Order cancelled: {response}")

            return {
                "status": "success",
                "order_id": order_id,
                "response": response.model_dump() if response else None
            }

        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            raise

    def cancel_all_orders(self) -> Dict[str, Any]:
        """
        Cancel all active orders.

        Returns:
            Cancellation result

        Raises:
            Exception: If cancellation fails
        """
        try:
            logger.info("Cancelling all orders")

            response = self.clob_client.cancel_all()

            logger.info(f"All orders cancelled: {response}")

            return {
                "status": "success",
                "response": response.model_dump() if response else None
            }

        except Exception as e:
            logger.error(f"Failed to cancel all orders: {e}")
            raise

    def get_trade_history(
        self,
        condition_id: Optional[str] = None,
        token_id: Optional[str] = None,
        trade_id: Optional[str] = None,
        before: Optional[Any] = None,
        after: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Get trade history for the wallet.

        Args:
            condition_id: Filter by condition ID
            token_id: Filter by token ID
            trade_id: Filter by specific trade ID
            before: Get trades before this timestamp (datetime object)
            after: Get trades after this timestamp (datetime object)

        Returns:
            List of trade records

        Raises:
            Exception: If query fails
        """
        try:
            logger.info(
                f"Getting trade history for wallet {self.wallet.name}: "
                f"condition_id={condition_id}, token_id={token_id}, trade_id={trade_id}"
            )

            trades = self.clob_client.get_trades(
                condition_id=condition_id,
                token_id=token_id,
                trade_id=trade_id,
                before=before,
                after=after
            )

            logger.info(f"Found {len(trades)} trades for {self.wallet.name}")

            return [trade.model_dump() for trade in trades]

        except Exception as e:
            logger.error(f"Failed to get trade history: {e}")
            raise
