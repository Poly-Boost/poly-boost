"""Test logging configuration."""

import logging
from poly_boost.core.logger import setup_logger
from poly_boost.core.config_loader import load_config

def main():
    # Load configuration
    config = load_config("config.yaml")

    # Configure logging
    log_config = config.get('logging', {})
    log_dir = log_config.get('log_dir', 'logs')
    log_filename = log_config.get('log_filename')
    log_level_str = log_config.get('level', 'INFO')
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Setup logger
    log = setup_logger(log_dir=log_dir, log_filename=log_filename, level=log_level)

    # Test logging
    log.debug("This is a DEBUG message")
    log.info("This is an INFO message")
    log.warning("This is a WARNING message")
    log.error("This is an ERROR message")

    print("\nLogging test completed!")
    print(f"Log directory: {log_dir}")
    print(f"Log filename: {log_filename or 'date-based (YYYY-MM-DD)'}.log")

if __name__ == "__main__":
    main()
