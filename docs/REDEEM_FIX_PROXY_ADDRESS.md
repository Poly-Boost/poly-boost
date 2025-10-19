# Redeem 修复 - Proxy Address 获取方法

## 问题

```
Failed to claim rewards: ("The function 'getProxyWallet' was not found in this ", "contract's abi.")
```

## 原因

`ProxyWalletFactory` 合约的 ABI 中没有 `getProxyWallet` 函数。

## 解决方案

使用正确的方法获取 proxy wallet 地址：

### 错误的方法 ❌

```python
# ProxyWalletFactory 没有这个函数
proxy_address = self.web3_client.proxy_factory.functions.getProxyWallet(
    self.web3_client.account.address
).call()
```

### 正确的方法 ✅

```python
# 使用 CTFExchange 合约的方法
proxy_address = self.web3_client.exchange.functions.getPolyProxyWalletAddress(
    self.web3_client.account.address
).call()
```

## 技术细节

### CTFExchange.getPolyProxyWalletAddress()

- **合约**: CTFExchange (0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E)
- **函数签名**: `getPolyProxyWalletAddress(address user) returns (address)`
- **功能**: 返回用户的 Polymarket 代理钱包地址
- **计算方式**: 基于用户 EOA 地址确定性计算 proxy wallet 地址

### 代理钱包系统

Polymarket 使用代理钱包系统：

1. **EOA (Externally Owned Account)**: 用户的私钥控制的账户
2. **Proxy Wallet**: 为每个 EOA 自动创建的代理合约钱包
3. **确定性地址**: 给定 EOA 地址，proxy wallet 地址是确定的

### 地址计算

```
Proxy Wallet Address = getPolyProxyWalletAddress(EOA Address)
```

这个函数内部使用 CREATE2 或类似机制来计算确定性地址。

## 修复代码

```python
def _ensure_conditional_tokens_approval(self, neg_risk: bool = True):
    """Ensure ConditionalTokens contract is approved for the adapter."""
    from web3 import Web3
    
    # Get operator address
    operator = (
        self.web3_client.neg_risk_adapter_address if neg_risk 
        else self.web3_client.exchange_address
    )
    
    # ✅ 正确方法: 使用 exchange 合约获取 proxy wallet 地址
    proxy_address = self.web3_client.exchange.functions.getPolyProxyWalletAddress(
        self.web3_client.account.address
    ).call()
    
    logger.info(f"Checking approval for proxy wallet: {proxy_address}")
    logger.info(f"Operator: {operator}")
    
    # Check if already approved
    is_approved = self.web3_client.conditional_tokens.functions.isApprovedForAll(
        Web3.to_checksum_address(proxy_address),
        Web3.to_checksum_address(operator)
    ).call()
    
    # ... rest of the code
```

## 其他获取方式

### 方法 1: 通过 Exchange (推荐)

```python
proxy_address = web3_client.exchange.functions.getPolyProxyWalletAddress(
    eoa_address
).call()
```

### 方法 2: 通过 Neg Risk Exchange

```python
proxy_address = web3_client.neg_risk_exchange.functions.getPolyProxyWalletAddress(
    eoa_address
).call()
```

### 方法 3: 计算 CREATE2 地址 (高级)

如果知道工厂合约和盐值，可以手动计算：

```python
from web3 import Web3
from eth_utils import keccak

def compute_proxy_address(factory_address, eoa_address, salt):
    """计算 CREATE2 代理地址"""
    # 这需要知道确切的初始化代码和盐值
    # 通常不推荐手动计算
    pass
```

## 验证

可以通过以下方式验证 proxy wallet 地址：

```python
# 获取 proxy wallet 地址
proxy_address = exchange.functions.getPolyProxyWalletAddress(eoa_address).call()

# 检查该地址是否有代码 (已部署)
code = w3.eth.get_code(proxy_address)
if code != b'':
    print(f"Proxy wallet deployed at: {proxy_address}")
else:
    print(f"Proxy wallet not yet deployed: {proxy_address}")
```

## 相关合约

| 合约 | 地址 | 方法 |
|------|------|------|
| CTFExchange | 0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E | getPolyProxyWalletAddress() |
| NegRiskCtfExchange | 0xC5d563A36AE78145C45a50134d48A1215220f80a | getPolyProxyWalletAddress() |
| ProxyWalletFactory | 0xaB45c5A4B0c941a2F231C04C3f49182e1A254052 | (无 getProxyWallet) |

## 更新日志

**2025-10-19**:
- ✅ 修复 proxy address 获取方法
- ✅ 使用 `exchange.getPolyProxyWalletAddress()` 代替错误的方法
- ✅ 添加技术说明文档

## 参考

- Polymarket 合约文档
- EIP-1167: Minimal Proxy Contract
- CREATE2 地址计算
