"""
Database initialization script.

Creates all necessary database tables for the Telegram bot.
Run this script before starting the bot for the first time.

Usage:
    python -m poly_boost.scripts.init_db
"""

import os
import logging
from peewee import SqliteDatabase
from playhouse.postgres_ext import PostgresqlExtDatabase

from poly_boost.core.models import db, Trade, WalletCheckpoint
from poly_boost.models.user_wallet import UserWallet


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Initialize database and create all tables."""
    try:
        # Get database configuration from environment
        db_url = os.environ.get("DATABASE_URL")

        if db_url:
            # Use PostgreSQL
            logger.info("Connecting to PostgreSQL database...")
            database = PostgresqlExtDatabase(db_url)
        else:
            # Fallback to SQLite for local development
            logger.info("Using SQLite database for development...")
            database = SqliteDatabase('poly_boost.db')

        # Initialize database connection
        db.initialize(database)
        logger.info("Database connection initialized")

        # Create tables
        with db:
            logger.info("Creating database tables...")

            # Create core tables
            db.create_tables([Trade, WalletCheckpoint], safe=True)
            logger.info("Created core tables: Trade, WalletCheckpoint")

            # Create user wallet table
            db.create_tables([UserWallet], safe=True)
            logger.info("Created user wallet table: UserWallet")

            logger.info("✅ All database tables created successfully!")

            # Verify tables exist
            logger.info("\nVerifying tables...")
            tables = database.get_tables()
            logger.info(f"Tables in database: {tables}")

    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
