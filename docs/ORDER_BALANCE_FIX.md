# Order Service 余额查询修复

## 问题描述

在调用 `sell_position_market` 和 `sell_position_limit` 时，如果不指定 `amount` 参数（意图卖出所有持仓），获取的余额为 0。

## 根本原因

### 问题代码

```python
# order_service.py - sell_position_market()
if amount is None:
    balance = self.web3_client.get_token_balance(token_id)
    # ↑ 没有传递 address 参数！
    amount = balance
```

### web3_client 的默认行为

```python
# web3_client.py - get_token_balance()
def get_token_balance(self, token_id: str, address: EthAddress | None = None) -> float:
    if address is None:
        # 默认查询 Proxy Wallet 地址
        address = self.exchange.functions.getPolyProxyWalletAddress(
            self.account.address
        ).call()
    balance_res = self.conditional_tokens.functions.balanceOf(address, int(token_id)).call()
    return float(balance_res / 1e6)
```

**问题**: 
- 用户使用 **EOA 模式** (signature_type = 0)
- Token 在 **EOA 地址**
- 但 `get_token_balance()` 默认查询 **Proxy Wallet 地址**
- 结果: 返回 0

## 解决方案

### 1. 添加 `_get_wallet_address()` 辅助方法

```python
class OrderService:
    def _get_wallet_address(self) -> str:
        """
        Get the correct wallet address based on signature_type.
        
        Returns:
            Wallet address (EOA or Proxy Wallet)
        """
        if self.signature_type == 0:
            # EOA wallet - use account address directly
            return self.web3_client.account.address
        else:
            # Proxy wallet (type 1) or Gnosis Safe (type 2)
            return self.web3_client.exchange.functions.getPolyProxyWalletAddress(
                self.web3_client.account.address
            ).call()
```

### 2. 修复 `sell_position_market()`

```python
def sell_position_market(self, token_id, amount=None, order_type=OrderType.FOK):
    if amount is None:
        # 使用辅助方法获取正确的地址
        wallet_address = self._get_wallet_address()
        balance = self.web3_client.get_token_balance(token_id, wallet_address)
        amount = balance
        logger.info(f"Selling all available balance: {amount} from {wallet_address}")
```

### 3. 修复 `sell_position_limit()`

```python
def sell_position_limit(self, token_id, price, amount=None, order_type=OrderType.GTC):
    if amount is None:
        # 使用辅助方法获取正确的地址
        wallet_address = self._get_wallet_address()
        balance = self.web3_client.get_token_balance(token_id, wallet_address)
        amount = balance
        logger.info(f"Selling all available balance: {amount} from {wallet_address}")
```

### 4. 优化 `claim_rewards()` 和 `_ensure_conditional_tokens_approval()`

也使用 `_get_wallet_address()` 辅助方法，减少重复代码：

```python
def claim_rewards(...):
    # 简化代码
    wallet_address = self._get_wallet_address()
    logger.info(f"Signature type: {self.signature_type}, wallet address: {wallet_address}")
    
    # 查询余额
    balance = self.web3_client.get_token_balance(token_id, wallet_address)

def _ensure_conditional_tokens_approval(...):
    # 简化代码
    wallet_address = self._get_wallet_address()
    wallet_type = "EOA" if self.signature_type == 0 else "Proxy"
    logger.info(f"Checking approval for {wallet_type} wallet: {wallet_address}")
```

## 修复的方法清单

| 方法 | 问题 | 修复 |
|------|------|------|
| `sell_position_market()` | 余额查询不传 address | ✅ 使用 `_get_wallet_address()` |
| `sell_position_limit()` | 余额查询不传 address | ✅ 使用 `_get_wallet_address()` |
| `claim_rewards()` | 重复的地址获取逻辑 | ✅ 使用 `_get_wallet_address()` |
| `_ensure_conditional_tokens_approval()` | 重复的地址获取逻辑 | ✅ 使用 `_get_wallet_address()` |

## 日志输出

### 修复前

```
INFO - Creating market sell order: token_id=123456, amount=0.0, order_type=FOK
ERROR - Amount must be greater than 0
```

### 修复后（EOA 模式）

```
INFO - Selling all available balance: 10.5 from 0x1234567890abcdef...
INFO - Creating market sell order: token_id=123456, amount=10.5, order_type=FOK
INFO - Market sell order executed: ...
```

### 修复后（Proxy 模式）

```
INFO - Selling all available balance: 10.5 from 0xabcdef1234567890...
INFO - Creating market sell order: token_id=123456, amount=10.5, order_type=FOK
INFO - Market sell order executed: ...
```

## 代码优化

### 优化前

每个方法都有重复的地址获取逻辑：

```python
# claim_rewards()
if self.signature_type == 0:
    wallet_address = self.web3_client.account.address
    logger.info(f"Using EOA wallet address: {wallet_address}")
else:
    wallet_address = self.web3_client.exchange.functions.getPolyProxyWalletAddress(
        self.web3_client.account.address
    ).call()
    logger.info(f"Using Proxy wallet address: {wallet_address}")

# _ensure_conditional_tokens_approval()
if self.signature_type == 0:
    wallet_address = self.web3_client.account.address
    logger.info(f"Checking approval for EOA wallet: {wallet_address}")
else:
    wallet_address = self.web3_client.exchange.functions.getPolyProxyWalletAddress(
        self.web3_client.account.address
    ).call()
    logger.info(f"Checking approval for Proxy wallet: {wallet_address}")
```

### 优化后

统一使用 `_get_wallet_address()` 辅助方法：

```python
# 所有方法
wallet_address = self._get_wallet_address()
```

**代码更简洁，更易维护！**

## 使用场景

### 场景 1: 市价卖出所有持仓

```python
# 不指定 amount，自动查询余额并卖出所有
order_service.sell_position_market(token_id="123456")

# 后端日志:
# INFO - Selling all available balance: 10.5 from 0x1234...
# INFO - Market sell order executed
```

### 场景 2: 限价卖出所有持仓

```python
# 不指定 amount，自动查询余额并挂单
order_service.sell_position_limit(token_id="123456", price=0.65)

# 后端日志:
# INFO - Selling all available balance: 10.5 from 0x1234...
# INFO - Limit sell order created
```

### 场景 3: 指定数量卖出

```python
# 指定 amount，不查询余额
order_service.sell_position_market(token_id="123456", amount=5.0)

# 后端日志:
# INFO - Creating market sell order: token_id=123456, amount=5.0
```

## 验证方法

### 1. 检查配置

```yaml
user_wallets:
  - signature_type: 0  # 确认是 0 (EOA)
```

### 2. 测试余额查询

```python
from polymarket_apis.clients.web3_client import PolymarketWeb3Client

client = PolymarketWeb3Client(private_key="...", chain_id=137)

# EOA 地址
eoa_address = client.account.address

# 查询余额
token_id = "123456789"
balance = client.get_token_balance(token_id, eoa_address)
print(f"EOA balance: {balance}")  # 应该 > 0
```

### 3. 测试卖出

```bash
# 启动 API
python run_api.py

# 调用 API (不指定 amount)
POST /orders/sell/market
{
  "token_id": "123456789"
}

# 查看日志，应该看到:
# INFO - Selling all available balance: X.X from 0x...
```

## 相关修复

这个修复与以下修复配套：

1. **[SIGNATURE_TYPE_ADDRESS_FIX.md](./SIGNATURE_TYPE_ADDRESS_FIX.md)**: 地址选择逻辑
2. **[EOA_REDEEM_FIX.md](./EOA_REDEEM_FIX.md)**: EOA 模式 redeem
3. **[REDEEM_BALANCE_FIX.md](./REDEEM_BALANCE_FIX.md)**: Redeem 余额查询

## 更新日志

**2025-10-20**:
- ✅ 识别 `sell_position_market` 和 `sell_position_limit` 余额查询问题
- ✅ 添加 `_get_wallet_address()` 辅助方法
- ✅ 修复 `sell_position_market()` 余额查询
- ✅ 修复 `sell_position_limit()` 余额查询
- ✅ 优化 `claim_rewards()` 地址获取逻辑
- ✅ 优化 `_ensure_conditional_tokens_approval()` 地址获取逻辑
- ✅ 添加详细日志输出

## 总结

通过添加 `_get_wallet_address()` 辅助方法，统一了地址获取逻辑：

- ✅ **EOA 模式**: 查询 EOA 地址余额
- ✅ **Proxy 模式**: 查询 Proxy Wallet 余额
- ✅ **代码简洁**: 消除重复代码
- ✅ **易于维护**: 统一的地址获取逻辑

**现在所有 order 方法都能正确查询余额了！** 🎉
