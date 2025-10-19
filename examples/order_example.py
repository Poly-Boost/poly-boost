"""
Order API 使用示例

展示如何使用 Order Service 进行交易操作。
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from polymarket_apis.clients.clob_client import PolymarketClobClient
from polymarket_apis.clients.web3_client import PolymarketWeb3Client
from polymarket_apis.types.clob_types import OrderType
from poly_boost.services.order_service import OrderService


def create_order_service():
    """创建 OrderService 实例"""
    # 从环境变量获取私钥
    private_key = os.getenv("MY_WALLET_PRIVATE_KEY")
    if not private_key:
        raise ValueError("请设置环境变量 MY_WALLET_PRIVATE_KEY")
    
    # 设置钱包地址
    proxy_address = os.getenv("MY_PROXY_ADDRESS")
    if not proxy_address:
        raise ValueError("请设置环境变量 MY_PROXY_ADDRESS")
    
    # 创建客户端
    clob_client = PolymarketClobClient(
        private_key=private_key,
        proxy_address=proxy_address,
        signature_type=2,  # Browser wallet proxy
        chain_id=137
    )
    
    web3_client = PolymarketWeb3Client(
        private_key=private_key,
        chain_id=137
    )
    
    return OrderService(clob_client, web3_client)


def example_market_sell(service: OrderService, token_id: str):
    """示例: 市价出售全部头寸"""
    print("\n=== 市价出售全部头寸 ===")
    try:
        result = service.sell_position_market(
            token_id=token_id,
            amount=None,  # None = 出售全部
            order_type=OrderType.FOK
        )
        print(f"成功: {result['status']}")
        print(f"订单ID: {result.get('order_id')}")
        print(f"数量: {result.get('amount')}")
    except Exception as e:
        print(f"错误: {e}")


def example_limit_sell(service: OrderService, token_id: str, price: float, amount: float):
    """示例: 限价出售头寸"""
    print("\n=== 限价出售头寸 ===")
    try:
        result = service.sell_position_limit(
            token_id=token_id,
            price=price,
            amount=amount,
            order_type=OrderType.GTC
        )
        print(f"成功: {result['status']}")
        print(f"订单ID: {result.get('order_id')}")
        print(f"价格: {result.get('price')}")
        print(f"数量: {result.get('amount')}")
    except Exception as e:
        print(f"错误: {e}")


def example_market_buy(service: OrderService, token_id: str, amount: float):
    """示例: 市价买入头寸"""
    print("\n=== 市价买入头寸 ===")
    try:
        result = service.buy_position_market(
            token_id=token_id,
            amount=amount,
            order_type=OrderType.FOK
        )
        print(f"成功: {result['status']}")
        print(f"订单ID: {result.get('order_id')}")
        print(f"数量: {result.get('amount')}")
    except Exception as e:
        print(f"错误: {e}")


def example_get_orders(service: OrderService, token_id: str = None):
    """示例: 查询活跃订单"""
    print("\n=== 查询活跃订单 ===")
    try:
        orders = service.get_orders(token_id=token_id)
        print(f"找到 {len(orders)} 个活跃订单")
        for order in orders[:5]:  # 只显示前5个
            print(f"  - 订单ID: {order.get('id')}")
            print(f"    Token: {order.get('asset_id')}")
            print(f"    价格: {order.get('price')}")
            print(f"    数量: {order.get('original_size')}")
    except Exception as e:
        print(f"错误: {e}")


def example_claim_rewards(service: OrderService, condition_id: str, amounts: list):
    """示例: 收获奖励"""
    print("\n=== 收获奖励 ===")
    try:
        result = service.claim_rewards(
            condition_id=condition_id,
            amounts=amounts
        )
        print(f"成功: {result['status']}")
        print(f"消息: {result.get('message')}")
    except Exception as e:
        print(f"错误: {e}")


def example_cancel_order(service: OrderService, order_id: str):
    """示例: 取消订单"""
    print("\n=== 取消订单 ===")
    try:
        result = service.cancel_order(order_id=order_id)
        print(f"成功: {result['status']}")
    except Exception as e:
        print(f"错误: {e}")


def main():
    """主函数"""
    print("Order Service 使用示例")
    print("=" * 50)
    
    # 创建服务实例
    try:
        service = create_order_service()
        print("✓ OrderService 初始化成功")
    except Exception as e:
        print(f"✗ 初始化失败: {e}")
        print("\n请确保设置以下环境变量:")
        print("  export MY_WALLET_PRIVATE_KEY='your_private_key'")
        print("  export MY_PROXY_ADDRESS='your_proxy_address'")
        return
    
    # 示例参数 (请替换为实际值)
    TOKEN_ID = "123456789"  # 替换为实际的 token ID
    CONDITION_ID = "0x1234..."  # 替换为实际的 condition ID
    
    # 运行示例
    # 注意: 取消注释以下代码行来执行实际操作
    
    # 1. 查询活跃订单
    example_get_orders(service, token_id=TOKEN_ID)
    
    # 2. 市价出售全部 (谨慎使用!)
    # example_market_sell(service, token_id=TOKEN_ID)
    
    # 3. 限价出售
    # example_limit_sell(service, token_id=TOKEN_ID, price=0.55, amount=10.0)
    
    # 4. 市价买入
    # example_market_buy(service, token_id=TOKEN_ID, amount=10.0)
    
    # 5. 收获奖励
    # example_claim_rewards(service, condition_id=CONDITION_ID, amounts=[10.0, 5.0])
    
    print("\n" + "=" * 50)
    print("示例完成!")


if __name__ == "__main__":
    main()
