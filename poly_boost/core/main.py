"""
Main entry point for Polymarket copy trading bot.

Initializes monitoring and copy trading components based on configuration.
"""

import logging
import signal
import sys
from typing import Optional

from poly_boost.core.client_factory import ClientFactory
from poly_boost.core.config_loader import load_config
from poly_boost.core.copy_trader import CopyTrader
from poly_boost.core.in_memory_activity_queue import InMemoryActivityQueue
from poly_boost.core.logger import setup_logger
from poly_boost.core.self_redeem_monitor import SelfRedeemMonitor
from poly_boost.core.wallet_manager import WalletManager
from poly_boost.core.wallet_monitor import WalletMonitor
from poly_boost.services.order_service import OrderService
from poly_boost.services.position_service import PositionService


def create_activity_queue(config: dict):
    """
    Create activity queue instance based on configuration.

    Args:
        config: Configuration dictionary

    Returns:
        ActivityQueue instance
    """
    queue_config = config.get('queue', {})
    queue_type = queue_config.get('type', 'memory')

    if queue_type == 'memory':
        memory_config = queue_config.get('memory', {})
        max_workers = memory_config.get('max_workers', 10)
        return InMemoryActivityQueue(max_workers=max_workers)
    elif queue_type == 'rabbitmq':
        # TODO: Implement RabbitMQ queue
        raise NotImplementedError("RabbitMQ queue not yet implemented")
    else:
        raise ValueError(f"Unsupported queue type: {queue_type}")


def main():
    """Program entry point."""
    client_factory: Optional[ClientFactory] = None
    self_redeem_monitor: Optional[SelfRedeemMonitor] = None

    try:
        # Load configuration
        config = load_config("config.yaml")

        # Configure logging
        log_config = config.get('logging', {})
        log_dir = log_config.get('log_dir', 'logs')
        log_filename = log_config.get('log_filename')  # Optional, None means use date format
        log_level_str = log_config.get('level', 'INFO')
        log_level = getattr(logging, log_level_str, logging.INFO)

        # Reinitialize logger
        log = setup_logger(log_dir=log_dir, log_filename=log_filename, level=log_level)
        log.info("Loading configuration file...")

        # Initialize wallet manager (loads user and watch wallets)
        wallet_manager = WalletManager.from_config(config)

        # Extract configuration
        monitoring_config = config['monitoring']
        wallets = monitoring_config['wallets']
        poll_interval = monitoring_config['poll_interval_seconds']
        batch_size = monitoring_config.get('batch_size', 500)
        api_config = config.get('polymarket_api', {})
        proxy = api_config.get('proxy')
        timeout = api_config.get('timeout', 30.0)
        verify_ssl = api_config.get('verify_ssl', True)

        # Extract Polygon RPC configuration
        polygon_rpc_config = config.get('polygon_rpc', {})

        # Initialize a single ClientFactory used across components
        client_factory = ClientFactory(api_config)

        # Optional self-redeem monitor
        auto_redeem_cfg = config.get('auto_redeem', {})
        if auto_redeem_cfg.get('enabled', True):
            log.info("Initializing self-redeem monitor...")
            # Use shared Data API client from factory
            data_client = client_factory.get_data_client()

            position_service = PositionService(
                clob_client=None,
                data_client=data_client,
                wallet_manager=wallet_manager,
            )

            def order_service_factory(wallet):
                return OrderService(
                    wallet=wallet,
                    clob_client=client_factory.get_clob_client(wallet),
                    web3_client=client_factory.get_web3_client(wallet),
                )

            self_redeem_monitor = SelfRedeemMonitor(
                wallet_manager=wallet_manager,
                position_svc=position_service,
                order_svc_factory=order_service_factory,
                cfg=config,
            )
            self_redeem_monitor.start()
        else:
            log.info("Self-redeem monitor disabled via configuration")

        # Create activity queue
        activity_queue = create_activity_queue(config)
        log.info(f"Activity queue created: {type(activity_queue).__name__}")

        # Initialize copy traders (if user wallets configured)
        copy_traders = []
        user_wallets = config.get('user_wallets', [])

        if user_wallets:
            log.info(f"Detected {len(user_wallets)} user wallet config(s), initializing copy traders...")

            for wallet_config in user_wallets:
                try:
                    trader = CopyTrader(
                        wallet_config=wallet_config,
                        activity_queue=activity_queue,
                        polygon_rpc_config=polygon_rpc_config,
                        verify_ssl=verify_ssl
                    )
                    copy_traders.append(trader)

                    # Start copy trading for each target wallet
                    for target_wallet in wallets:
                        trader.run(target_wallet)

                    log.info(f"Copy trader '{wallet_config['name']}' started")

                except Exception as e:
                    log.error(
                        f"Failed to initialize copy trader '{wallet_config.get('name', 'unknown')}': {e}",
                        exc_info=True
                    )
        else:
            log.info("No user wallets configured, running in monitoring mode only (activities will be printed by WalletMonitor)")

        # Create monitor
        monitor = WalletMonitor(
            wallets=wallets,
            poll_interval=poll_interval,
            activity_queue=activity_queue,
            batch_size=batch_size,
            # Unify HTTP/proxy settings via shared factory client
            data_client=client_factory.get_data_client(),
        )

        # Auto-redeem resource cleanup helper
        def cleanup_auto_redeem():
            nonlocal self_redeem_monitor, client_factory
            if self_redeem_monitor:
                self_redeem_monitor.stop()
                self_redeem_monitor = None
            if client_factory:
                client_factory.close()
                client_factory = None

        # Set up signal handler for graceful shutdown
        def signal_handler(sig, frame):
            log.info("Received exit signal, shutting down...")

            cleanup_auto_redeem()

            # Print copy trading statistics
            for trader in copy_traders:
                trader.print_stats()

            monitor.stop()
            if hasattr(activity_queue, 'shutdown'):
                activity_queue.shutdown()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start monitoring
        monitor.start()

        # Keep main thread running
        log.info("Monitoring running, press Ctrl+C to exit...")
        while True:
            signal.pause() if hasattr(signal, 'pause') else monitor.stop_event.wait(3600)

    except FileNotFoundError as e:
        if 'cleanup_auto_redeem' in locals():
            cleanup_auto_redeem()
        log.error(f"Configuration file error: {e}")
        sys.exit(1)
    except Exception as e:
        if 'cleanup_auto_redeem' in locals():
            cleanup_auto_redeem()
        log.error(f"Program startup failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
