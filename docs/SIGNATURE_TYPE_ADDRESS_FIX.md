# Signature Type 地址选择修复

## 问题描述

查询余额时返回 0，因为使用了错误的钱包地址。

**根本原因**: 代码固定使用 Proxy Wallet 地址查询余额，但用户使用的是 EOA (signature_type = 0)，token 实际在 EOA 地址中。

## Signature Type 说明

Polymarket 支持三种钱包类型：

| signature_type | 钱包类型 | 说明 |
|----------------|----------|------|
| **0** | EOA Wallet | Externally Owned Account，直接由私钥控制的账户 |
| **1** | Proxy Wallet | 通过 ProxyFactory 创建的代理钱包 |
| **2** | Gnosis Safe | Gnosis Safe 多签钱包（也是代理钱包） |

## Token 持有地址

根据 signature_type，Token 的实际持有地址不同：

```
signature_type = 0 (EOA):
  Token 在 → EOA 地址 (account.address)
  
signature_type = 1 或 2 (Proxy/Safe):
  Token 在 → Proxy Wallet 地址 (通过 getPolyProxyWalletAddress 获取)
```

## 修复方案

### 1. OrderService 添加 signature_type 参数

```python
class OrderService:
    def __init__(
        self,
        clob_client: PolymarketClobClient,
        web3_client: PolymarketWeb3Client,
        signature_type: int = 2  # 新增参数
    ):
        self.clob_client = clob_client
        self.web3_client = web3_client
        self.signature_type = signature_type  # 保存配置
```

### 2. claim_rewards 根据 signature_type 选择地址

```python
def claim_rewards(...):
    # 根据 signature_type 选择正确的地址
    if self.signature_type == 0:
        # EOA wallet - 使用账户地址
        wallet_address = self.web3_client.account.address
        logger.info(f"Using EOA wallet address: {wallet_address}")
    else:
        # Proxy wallet (type 1) or Gnosis Safe (type 2)
        wallet_address = self.web3_client.exchange.functions.getPolyProxyWalletAddress(
            self.web3_client.account.address
        ).call()
        logger.info(f"Using Proxy wallet address: {wallet_address}")
    
    # 使用正确的地址查询余额
    balance = self.web3_client.get_token_balance(
        token_id=token_id,
        address=wallet_address  # ← 使用正确的地址
    )
```

### 3. _ensure_conditional_tokens_approval 同样修改

授权检查也需要使用正确的地址：

```python
def _ensure_conditional_tokens_approval(self, neg_risk: bool = True):
    # 根据 signature_type 获取地址
    if self.signature_type == 0:
        wallet_address = self.web3_client.account.address
        logger.info(f"Checking approval for EOA wallet: {wallet_address}")
    else:
        wallet_address = self.web3_client.exchange.functions.getPolyProxyWalletAddress(
            self.web3_client.account.address
        ).call()
        logger.info(f"Checking approval for Proxy wallet: {wallet_address}")
    
    # 检查授权状态
    is_approved = self.web3_client.conditional_tokens.functions.isApprovedForAll(
        Web3.to_checksum_address(wallet_address),  # ← 使用正确的地址
        Web3.to_checksum_address(operator)
    ).call()
```

### 4. dependencies.py 传递 signature_type

```python
# 从配置读取 signature_type
signature_type = wallet_config.get('signature_type', 2)

# 传递给 OrderService
_order_service = OrderService(_clob_client, _web3_client, signature_type)
```

## 配置示例

### EOA Wallet (signature_type = 0)

```yaml
user_wallets:
  - name: "MyEOAWallet"
    address: "0x1234..."              # EOA 地址
    proxy_address: "0x1234..."        # 与 address 相同
    private_key_env: "MY_PRIVATE_KEY"
    signature_type: 0                 # ← EOA 模式
```

**Token 位置**: 直接在 `0x1234...` 地址

### Proxy Wallet (signature_type = 1)

```yaml
user_wallets:
  - name: "MyProxyWallet"
    address: "0x1234..."              # EOA 地址
    proxy_address: "0x5678..."        # Proxy 地址
    private_key_env: "MY_PRIVATE_KEY"
    signature_type: 1                 # ← Proxy 模式
```

**Token 位置**: 在 Proxy Wallet `0x5678...` 地址（通过 `getPolyProxyWalletAddress` 计算）

## 地址获取逻辑

### EOA 模式 (signature_type = 0)

```python
wallet_address = web3_client.account.address
# 直接使用 EOA 地址，不需要计算
```

### Proxy 模式 (signature_type = 1 or 2)

```python
wallet_address = web3_client.exchange.functions.getPolyProxyWalletAddress(
    web3_client.account.address
).call()
# 通过合约计算 Proxy 地址
```

## 日志示例

### EOA 模式日志

```
INFO - Claiming rewards for condition_id=0x123...
INFO - Using EOA wallet address: 0x1234567890abcdef...
INFO - Signature type: 0, wallet address: 0x1234567890abcdef...
INFO - Token IDs provided: ['123456', '789012']
INFO - Querying actual token balances from chain...
INFO - Token 0 (ID: 123456): balance = 10.5
INFO - Token 1 (ID: 789012): balance = 0.0
INFO - Final amounts (after balance query): [10.5, 0.0]
INFO - Checking approval for EOA wallet: 0x1234567890abcdef...
INFO - Redeeming with amounts: [10.5, 0.0]
```

### Proxy 模式日志

```
INFO - Claiming rewards for condition_id=0x123...
INFO - Using Proxy wallet address: 0xabcdef1234567890...
INFO - Signature type: 1, wallet address: 0xabcdef1234567890...
INFO - Token IDs provided: ['123456', '789012']
INFO - Querying actual token balances from chain...
INFO - Token 0 (ID: 123456): balance = 10.5
INFO - Token 1 (ID: 789012): balance = 0.0
INFO - Final amounts (after balance query): [10.5, 0.0]
INFO - Checking approval for Proxy wallet: 0xabcdef1234567890...
INFO - Redeeming with amounts: [10.5, 0.0]
```

## 验证方法

### 手动检查余额

```python
from polymarket_apis.clients.web3_client import PolymarketWeb3Client

web3_client = PolymarketWeb3Client(private_key="...", chain_id=137)

# EOA 地址
eoa_address = web3_client.account.address
print(f"EOA address: {eoa_address}")

# Proxy 地址
proxy_address = web3_client.exchange.functions.getPolyProxyWalletAddress(eoa_address).call()
print(f"Proxy address: {proxy_address}")

# 查询 EOA 余额
token_id = "123456789"
eoa_balance = web3_client.get_token_balance(token_id, eoa_address)
print(f"EOA balance: {eoa_balance}")

# 查询 Proxy 余额
proxy_balance = web3_client.get_token_balance(token_id, proxy_address)
print(f"Proxy balance: {proxy_balance}")
```

### 在 Polygonscan 查看

1. 打开 https://polygonscan.com/
2. 搜索您的地址（EOA 或 Proxy）
3. 切换到 **ERC-1155 Token Txns** 标签
4. 查看 Token 余额

## 常见问题

### Q1: 如何知道我使用的是哪种模式？

**A**: 查看 `config/config.yaml` 中的 `signature_type`：
- `0` = EOA
- `1` = Proxy
- `2` = Gnosis Safe

### Q2: Token 在 EOA 还是 Proxy？

**A**: 取决于您如何购买的：
- 通过 Polymarket 官方网站购买 → Proxy Wallet
- 通过自定义脚本直接购买 → 可能在 EOA
- 查看区块链浏览器确认

### Q3: 如果 Token 在错误的地址怎么办？

**A**: 需要将 Token 转移到正确的地址：

```python
# 如果 Token 在 EOA，需要 redeem 也从 EOA
# 或者转移到 Proxy Wallet
web3_client.conditional_tokens.functions.safeTransferFrom(
    from_address,  # EOA
    to_address,    # Proxy
    token_id,
    amount,
    b""
).transact()
```

### Q4: Proxy Wallet 地址怎么计算？

**A**: 通过 `CTFExchange.getPolyProxyWalletAddress()` 确定性计算：
- 输入：EOA 地址
- 输出：对应的 Proxy Wallet 地址
- 每个 EOA 只有一个固定的 Proxy Wallet

## 技术细节

### Proxy Wallet 系统

Polymarket 使用代理钱包系统的优势：
1. **Gas 优化**: 批量操作更省 gas
2. **授权管理**: 统一管理授权
3. **安全性**: 分离控制权和资产
4. **兼容性**: 支持元交易（meta-transaction）

### 地址关系

```
EOA Address (0x1234...)
    ↓ (确定性计算)
Proxy Wallet Address (0x5678...)
    ↓ (持有)
ERC1155 Tokens
```

## 更新日志

**2025-10-19**:
- ✅ 识别余额查询返回 0 的根本原因
- ✅ 添加 signature_type 参数支持
- ✅ 根据 signature_type 动态选择钱包地址
- ✅ 更新余额查询逻辑
- ✅ 更新授权检查逻辑
- ✅ 添加详细日志输出

## 相关文档

- [REDEEM_BALANCE_FIX.md](./REDEEM_BALANCE_FIX.md) - 余额查询修复
- [REDEEM_APPROVAL_FIX.md](./REDEEM_APPROVAL_FIX.md) - 授权问题修复
- Polymarket Proxy Wallet 文档

## 总结

通过根据 `signature_type` 动态选择正确的钱包地址，确保：
- ✅ EOA 模式查询 EOA 地址的余额
- ✅ Proxy 模式查询 Proxy 地址的余额
- ✅ 授权检查使用正确的地址
- ✅ Redeem 操作使用正确的地址

**现在应该能正确查询到余额并成功 redeem！** 🎉
