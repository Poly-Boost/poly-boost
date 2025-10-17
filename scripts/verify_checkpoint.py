"""验证检查点数据"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from poly_boost.core.config_loader import load_config
from poly_boost.core.database_handler import DatabaseHandler
from poly_boost.core.models import WalletCheckpoint

def verify_checkpoint():
    """验证检查点数据"""
    config = load_config("config.yaml")
    db_url = config['database']['url']

    DatabaseHandler.initialize_database(db_url)

    # 查询所有检查点
    checkpoints = WalletCheckpoint.select()

    print(f"数据库中共有 {len(checkpoints)} 个检查点:")
    for cp in checkpoints:
        print(f"  钱包: {cp.wallet_address}")
        print(f"  最后同步时间: {cp.last_synced_timestamp}")
        print(f"  更新时间: {cp.updated_at}")
        print()

if __name__ == "__main__":
    verify_checkpoint()
