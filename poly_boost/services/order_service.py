"""
Order management service.

Provides functionality for creating and executing orders on Polymarket,
including market orders, limit orders, and reward claiming.
"""

from typing import Optional, Dict, Any, List
from decimal import Decimal
import logging

from polymarket_apis.clients.clob_client import PolymarketClobClient
from polymarket_apis.clients.web3_client import PolymarketWeb3Client
from polymarket_apis.types.clob_types import OrderArgs, MarketOrderArgs, OrderType


logger = logging.getLogger(__name__)


class OrderService:
    """Service for managing and executing orders."""

    def __init__(
        self,
        clob_client: PolymarketClobClient,
        web3_client: PolymarketWeb3Client,
        signature_type: int = 2,
        wallet_address: Optional[str] = None
    ):
        """
        Initialize order service.

        Args:
            clob_client: Polymarket CLOB client instance
            web3_client: Polymarket Web3 client instance
            signature_type: Wallet type (0=EOA, 1=Proxy, 2=Gnosis Safe)
            wallet_address: Wallet address to use for operations (EOA or Proxy)
                          If not provided, will be determined from signature_type
        """
        self.clob_client = clob_client
        self.web3_client = web3_client
        self.signature_type = signature_type
        self._wallet_address = wallet_address

    def _get_wallet_address(self) -> str:
        """
        Get the correct wallet address based on configuration.
        
        Returns:
            Wallet address (EOA or Proxy Wallet)
        """
        # If wallet_address was provided during initialization, use it
        if self._wallet_address:
            return self._wallet_address
        
        # Otherwise, determine from signature_type (fallback for backward compatibility)
        if self.signature_type == 0:
            # EOA wallet - use account address directly
            return self.web3_client.account.address
        else:
            # Proxy wallet (type 1) or Gnosis Safe (type 2)
            # Query from chain (less efficient)
            return self.web3_client.exchange.functions.getPolyProxyWalletAddress(
                self.web3_client.account.address
            ).call()

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
                # Get wallet address based on signature_type
                wallet_address = self._get_wallet_address()
                balance = self.web3_client.get_token_balance(token_id, wallet_address)
                amount = balance
                logger.info(f"Selling all available balance: {amount} from {wallet_address}")
            
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
                # Get wallet address based on signature_type
                wallet_address = self._get_wallet_address()
                balance = self.web3_client.get_token_balance(token_id, wallet_address)
                amount = balance
                logger.info(f"Selling all available balance: {amount} from {wallet_address}")
            
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

    def claim_rewards(
        self, 
        condition_id: str, 
        amounts: List[float],
        token_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Claim rewards by redeeming positions.

        Args:
            condition_id: Condition ID of the resolved market
            amounts: List of amounts to redeem [outcome1_amount, outcome2_amount]
                    If None or 0, will query actual balance from chain
            token_ids: Optional list of token IDs for balance query

        Returns:
            Transaction result

        Raises:
            Exception: If redemption fails
        """
        try:
            logger.info(
                f"Claiming rewards for condition_id={condition_id}, "
                f"requested amounts={amounts}, token_ids={token_ids}"
            )

            # Get the correct wallet address based on signature_type
            from web3 import Web3
            wallet_address = self._get_wallet_address()
            logger.info(f"Signature type: {self.signature_type}, wallet address: {wallet_address}")
            
            # Query actual balances if token_ids provided
            actual_amounts = []
            if token_ids and any(token_ids):  # Check if token_ids is not None and has non-None values
                logger.info(f"Token IDs provided: {token_ids}")
                logger.info("Querying actual token balances from chain...")
                
                for i, token_id in enumerate(token_ids):
                    if token_id:
                        try:
                            # Query balance from the correct wallet address
                            balance = self.web3_client.get_token_balance(
                                token_id=token_id,
                                address=wallet_address
                            )
                            logger.info(f"Token {i} (ID: {token_id}): balance = {balance}")
                            actual_amounts.append(balance)
                        except Exception as e:
                            logger.error(f"Failed to query balance for token {token_id}: {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                            # Use requested amount as fallback
                            actual_amounts.append(amounts[i] if i < len(amounts) else 0)
                    else:
                        # No token_id for this position
                        logger.info(f"Token {i}: no token_id, using requested amount {amounts[i] if i < len(amounts) else 0}")
                        actual_amounts.append(amounts[i] if i < len(amounts) else 0)
                
                # Use actual balances instead of requested amounts
                logger.info(f"Final amounts (after balance query): {actual_amounts}")
                amounts = actual_amounts
            else:
                logger.warning(
                    f"No valid token_ids provided (got: {token_ids}), using requested amounts: {amounts}. "
                    "This may fail if amounts exceed actual balance."
                )

            # Determine if it's a neg risk market
            # Try to get neg risk status from a token in this market
            # For simplicity, we'll default to True (most markets are neg risk)
            neg_risk = True

            # Check and set approval if needed
            logger.info("Checking ERC1155 approval status...")
            self._ensure_conditional_tokens_approval(neg_risk=neg_risk)

            # Redeem positions with actual amounts
            logger.info(f"Redeeming with amounts: {amounts}")
            
            # Use different redeem method based on signature_type
            if self.signature_type == 0:
                # EOA mode - redeem directly without proxy
                logger.info("EOA mode: redeeming directly from EOA address")
                self._redeem_position_eoa(condition_id, amounts, neg_risk)
            else:
                # Proxy mode - use ProxyFactory
                logger.info("Proxy mode: redeeming through ProxyFactory")
                self.web3_client.redeem_position(
                    condition_id=condition_id,
                    amounts=amounts,
                    neg_risk=neg_risk
                )

            logger.info("Rewards claimed successfully")

            return {
                "status": "success",
                "condition_id": condition_id,
                "amounts": amounts,
                "message": "Rewards claimed successfully"
            }

        except Exception as e:
            logger.error(f"Failed to claim rewards: {e}")
            raise

    def _redeem_position_eoa(
        self,
        condition_id: str,
        amounts: List[float],
        neg_risk: bool = True
    ):
        """
        Redeem position directly from EOA (without ProxyFactory).
        
        Args:
            condition_id: Condition ID of the market
            amounts: Amounts to redeem [outcome1, outcome2]
            neg_risk: Whether it's a neg risk market
        """
        from web3 import Web3
        
        logger.info("Starting EOA direct redeem...")
        
        # Convert amounts to wei (6 decimals for USDC)
        amounts_wei = [int(amount * 1e6) for amount in amounts]
        logger.info(f"Amounts in wei: {amounts_wei}")
        
        # Get nonce
        nonce = self.web3_client.w3.eth.get_transaction_count(
            self.web3_client.account.address
        )
        
        # Choose the right contract and method
        if neg_risk:
            # NegRiskAdapter.redeemPositions
            contract = self.web3_client.neg_risk_adapter
            contract_address = self.web3_client.neg_risk_adapter_address
            logger.info(f"Using NegRiskAdapter at {contract_address}")
            
            # Build transaction
            txn = contract.functions.redeemPositions(
                condition_id,
                amounts_wei
            ).build_transaction({
                "from": self.web3_client.account.address,
                "nonce": nonce,
                "gasPrice": int(1.05 * self.web3_client.w3.eth.gas_price),
                "gas": 500000,
            })
        else:
            # ConditionalTokens.redeemPositions
            contract = self.web3_client.conditional_tokens
            contract_address = self.web3_client.conditional_tokens_address
            logger.info(f"Using ConditionalTokens at {contract_address}")
            
            # Build transaction
            txn = contract.functions.redeemPositions(
                Web3.to_checksum_address(self.web3_client.usdc_address),
                bytes(32),  # parentCollectionId = 0x00...00
                condition_id,
                [1, 2]  # indexSets for binary market
            ).build_transaction({
                "from": self.web3_client.account.address,
                "nonce": nonce,
                "gasPrice": int(1.05 * self.web3_client.w3.eth.gas_price),
                "gas": 500000,
            })
        
        # Sign and send transaction
        signed_txn = self.web3_client.account.sign_transaction(txn)
        tx_hash = self.web3_client.w3.eth.send_raw_transaction(
            signed_txn.raw_transaction
        ).hex()
        
        logger.info(f"EOA redeem transaction sent: {tx_hash}")
        
        # Wait for confirmation
        receipt = self.web3_client.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt['status'] == 1:
            logger.info(f"EOA redeem transaction confirmed: {tx_hash}")
        else:
            raise Exception(f"EOA redeem transaction failed: {tx_hash}")
    
    def _ensure_conditional_tokens_approval(self, neg_risk: bool = True):
        """
        Ensure ConditionalTokens contract is approved for the adapter.

        Args:
            neg_risk: Whether to approve for neg risk adapter or standard exchange
        """
        from web3 import Web3
        
        # Get the operator address based on neg_risk
        operator = (
            self.web3_client.neg_risk_adapter_address if neg_risk 
            else self.web3_client.exchange_address
        )
        
        # Get the correct wallet address based on signature_type
        wallet_address = self._get_wallet_address()
        wallet_type = "EOA" if self.signature_type == 0 else "Proxy"
        logger.info(f"Checking approval for {wallet_type} wallet: {wallet_address}")
        logger.info(f"Operator: {operator}")
        
        # Check if already approved
        is_approved = self.web3_client.conditional_tokens.functions.isApprovedForAll(
            Web3.to_checksum_address(wallet_address),
            Web3.to_checksum_address(operator)
        ).call()
        
        if is_approved:
            logger.info("Already approved, skipping approval transaction")
            return
        
        logger.info("Not approved yet, sending approval transaction...")
        
        # Get nonce
        nonce = self.web3_client.w3.eth.get_transaction_count(
            self.web3_client.account.address
        )
        
        if self.signature_type == 0:
            # EOA mode - call setApprovalForAll directly
            logger.info("EOA mode: sending approval directly")
            txn = self.web3_client.conditional_tokens.functions.setApprovalForAll(
                Web3.to_checksum_address(operator),
                True
            ).build_transaction({
                "from": self.web3_client.account.address,
                "nonce": nonce,
                "gasPrice": int(1.05 * self.web3_client.w3.eth.gas_price),
                "gas": 100000,
            })
        else:
            # Proxy mode - use ProxyFactory
            logger.info("Proxy mode: sending approval through ProxyFactory")
            
            # Encode the setApprovalForAll call
            approval_data = self.web3_client.conditional_tokens.encode_abi(
                abi_element_identifier="setApprovalForAll",
                args=[Web3.to_checksum_address(operator), True]
            )
            
            # Create proxy transaction
            proxy_txn = {
                "typeCode": 1,
                "to": self.web3_client.conditional_tokens_address,
                "value": 0,
                "data": approval_data,
            }
            
            # Build transaction through proxy factory
            txn = self.web3_client.proxy_factory.functions.proxy([proxy_txn]).build_transaction({
                "nonce": nonce,
                "gasPrice": int(1.05 * self.web3_client.w3.eth.gas_price),
                "gas": 500000,
                "from": self.web3_client.account.address,
            })
        
        # Sign and send
        signed_txn = self.web3_client.account.sign_transaction(txn)
        tx_hash = self.web3_client.w3.eth.send_raw_transaction(
            signed_txn.raw_transaction
        ).hex()
        
        logger.info(f"Approval transaction sent: {tx_hash}")
        
        # Wait for confirmation
        receipt = self.web3_client.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt['status'] == 1:
            logger.info("Approval transaction confirmed successfully")
        else:
            raise Exception(f"Approval transaction failed: {tx_hash}")

    def get_orders(
        self,
        order_id: Optional[str] = None,
        condition_id: Optional[str] = None,
        token_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get active orders.

        Args:
            order_id: Filter by order ID
            condition_id: Filter by condition ID
            token_id: Filter by token ID

        Returns:
            List of active orders

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

            return [order.model_dump() for order in orders]

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
