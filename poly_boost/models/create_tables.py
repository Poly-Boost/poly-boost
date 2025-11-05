"""
Database table creation script.

Run this script to create all database tables for the Telegram bot.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from peewee import SqliteDatabase, PostgresqlDatabase
from poly_boost.models.user_wallet import UserWallet

# Load environment variables
load_dotenv()


def create_database():
    """Create database connection from DATABASE_URL environment variable."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError(
            "DATABASE_URL environment variable not set. "
            "Please set it in .env file. "
            "Example: DATABASE_URL=sqlite:///polyboost_bot.db"
        )

    if database_url.startswith("sqlite:///"):
        # SQLite database
        db_path = database_url.replace("sqlite:///", "")
        print(f"Using SQLite database: {db_path}")
        return SqliteDatabase(db_path)

    elif database_url.startswith("postgresql://"):
        # PostgreSQL database
        # Format: postgresql://user:password@host:port/database
        import re
        match = re.match(
            r"postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)",
            database_url
        )
        if not match:
            raise ValueError(f"Invalid PostgreSQL URL format: {database_url}")

        user, password, host, port, database = match.groups()
        print(f"Using PostgreSQL database: {host}:{port}/{database}")

        return PostgresqlDatabase(
            database,
            user=user,
            password=password,
            host=host,
            port=int(port)
        )

    else:
        raise ValueError(
            f"Unsupported database URL format: {database_url}. "
            "Supported: sqlite:/// or postgresql://"
        )


def create_tables(database):
    """Create all tables in the database."""
    print("\n=== Creating Tables ===\n")

    # Bind models to database
    database.bind([UserWallet])

    # Create tables
    database.create_tables([UserWallet], safe=True)

    print(f"✓ Table 'user_wallets' created successfully")

    # Verify table creation
    if database.table_exists("user_wallets"):
        print(f"✓ Table 'user_wallets' verified")
    else:
        print(f"✗ Table 'user_wallets' verification failed")

    print("\n=== Database Setup Complete ===\n")


def main():
    """Main execution function."""
    try:
        print("\n=== Telegram Bot Database Setup ===\n")

        # Create database connection
        database = create_database()

        # Create tables
        create_tables(database)

        print("Database setup completed successfully!")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
