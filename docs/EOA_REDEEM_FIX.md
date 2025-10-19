# EOA 模式 Redeem 完整修复

## 问题描述

使用 EOA 模式 (signature_type = 0) 时，redeem 交易失败：

```
execution reverted - SafeMath: subtraction overflow
```

## 根本原因

虽然修复了余额查询逻辑，但 **redeem 交易执行方式**仍然有问题：

### 问题链条

1. ✅ **余额查询**: 从 EOA 地址查询 → 查到余额
2. ❌ **交易执行**: 通过 ProxyFactory 执行 → 试图从 Proxy Wallet redeem
3. ❌ **结果**: Proxy Wallet 没有 token → SafeMath overflow

### 代码分析

```python
# web3_client.redeem_position() 的实现
def redeem_position(self, condition_id, amounts, neg_risk=True):
    # ... 
    # 总是通过 ProxyFactory 执行！
    txn_data = self.proxy_factory.functions.proxy([proxy_txn]).build_transaction({
        "from": self.account.address,  # EOA 签名
        ...
    })
```

**问题**: 
- 从 EOA 签名（`from: EOA`）
- 通过 ProxyFactory 执行
- ProxyFactory 调用 NegRiskAdapter
- NegRiskAdapter 试图从 **Proxy Wallet** 转移 token
- 但 token 在 **EOA** 地址！

## 完整解决方案

### 核心思路

根据 `signature_type` 使用不同的交易执行方式：

| signature_type | 余额位置 | 执行方式 |
|----------------|----------|----------|
| **0** (EOA) | EOA 地址 | 直接调用合约 |
| **1** (Proxy) | Proxy Wallet | 通过 ProxyFactory |
| **2** (Safe) | Proxy Wallet | 通过 ProxyFactory |

### 实现步骤

#### 1. 余额查询（已修复）

```python
# claim_rewards 方法
if self.signature_type == 0:
    wallet_address = self.web3_client.account.address  # EOA
else:
    wallet_address = self.web3_client.exchange.functions.getPolyProxyWalletAddress(
        self.web3_client.account.address
    ).call()  # Proxy

balance = self.web3_client.get_token_balance(token_id, wallet_address)
```

#### 2. Redeem 执行（新增修复）

```python
# claim_rewards 方法
if self.signature_type == 0:
    # EOA mode - redeem directly
    self._redeem_position_eoa(condition_id, amounts, neg_risk)
else:
    # Proxy mode - use ProxyFactory
    self.web3_client.redeem_position(condition_id, amounts, neg_risk)
```

#### 3. EOA 直接 Redeem 方法

```python
def _redeem_position_eoa(self, condition_id, amounts, neg_risk=True):
    """直接从 EOA 调用合约 redeem（不通过 ProxyFactory）"""
    
    # Convert to wei
    amounts_wei = [int(amount * 1e6) for amount in amounts]
    
    if neg_risk:
        # 直接调用 NegRiskAdapter.redeemPositions
        txn = self.web3_client.neg_risk_adapter.functions.redeemPositions(
            condition_id,
            amounts_wei
        ).build_transaction({
            "from": self.web3_client.account.address,  # 从 EOA 执行
            "nonce": nonce,
            "gasPrice": int(1.05 * gas_price),
            "gas": 500000,
        })
    else:
        # 直接调用 ConditionalTokens.redeemPositions
        txn = self.web3_client.conditional_tokens.functions.redeemPositions(
            usdc_address,
            bytes(32),
            condition_id,
            [1, 2]
        ).build_transaction({
            "from": self.web3_client.account.address,  # 从 EOA 执行
            "nonce": nonce,
            "gasPrice": int(1.05 * gas_price),
            "gas": 500000,
        })
    
    # 签名并发送
    signed_txn = self.web3_client.account.sign_transaction(txn)
    tx_hash = self.web3_client.w3.eth.send_raw_transaction(signed_txn.raw_transaction).hex()
    
    # 等待确认
    receipt = self.web3_client.w3.eth.wait_for_transaction_receipt(tx_hash)
```

#### 4. Approval 授权（同样需要分开）

```python
def _ensure_conditional_tokens_approval(self, neg_risk=True):
    # 获取地址
    if self.signature_type == 0:
        wallet_address = self.web3_client.account.address
    else:
        wallet_address = get_proxy_address(...)
    
    # 检查授权
    is_approved = conditional_tokens.isApprovedForAll(wallet_address, operator)
    
    if not is_approved:
        if self.signature_type == 0:
            # EOA mode - 直接调用 setApprovalForAll
            txn = conditional_tokens.functions.setApprovalForAll(
                operator,
                True
            ).build_transaction({
                "from": account.address,
                ...
            })
        else:
            # Proxy mode - 通过 ProxyFactory
            txn = proxy_factory.functions.proxy([approval_txn]).build_transaction(...)
        
        # 发送交易
        ...
```

## 交易执行流程对比

### EOA 模式（修复后）

```
1. 查询余额: EOA 地址 → 10.5 token ✅
2. 检查授权: EOA 授权给 NegRiskAdapter ✅
3. 执行 Redeem:
   EOA 签名 → 直接调用 NegRiskAdapter.redeemPositions()
   → NegRiskAdapter 从 EOA 转移 token ✅
   → 返回 USDC 到 EOA ✅
```

### Proxy 模式

```
1. 查询余额: Proxy Wallet 地址 → 10.5 token ✅
2. 检查授权: Proxy Wallet 授权给 NegRiskAdapter ✅
3. 执行 Redeem:
   EOA 签名 → ProxyFactory.proxy()
   → Proxy Wallet 调用 NegRiskAdapter.redeemPositions()
   → NegRiskAdapter 从 Proxy Wallet 转移 token ✅
   → 返回 USDC 到 Proxy Wallet ✅
```

## 关键合约方法

### NegRiskAdapter.redeemPositions (Neg Risk 市场)

```solidity
function redeemPositions(
    bytes32 conditionId,
    uint256[] calldata amounts  // [outcome1_amount, outcome2_amount]
) external
```

**功能**: 
- 从 `msg.sender` 转移 conditional tokens
- 返回 collateral (USDC) 到 `msg.sender`

### ConditionalTokens.redeemPositions (标准市场)

```solidity
function redeemPositions(
    IERC20 collateralToken,
    bytes32 parentCollectionId,
    bytes32 conditionId,
    uint256[] calldata indexSets
) external
```

**功能**:
- 从 `msg.sender` 转移 conditional tokens
- 返回 collateral 到 `msg.sender`

## 修复验证

### 后端日志

重启 API 后，redeem 时应该看到：

#### EOA 模式
```
INFO - Signature type: 0, wallet address: 0x1234... (EOA)
INFO - Token 0 (ID: 123456): balance = 10.5
INFO - Final amounts (after balance query): [10.5, 0.0]
INFO - Checking approval for EOA wallet: 0x1234...
INFO - EOA mode: redeeming directly from EOA address
INFO - Starting EOA direct redeem...
INFO - Amounts in wei: [10500000, 0]
INFO - Using NegRiskAdapter at 0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296
INFO - EOA redeem transaction sent: 0xabc...
INFO - EOA redeem transaction confirmed: 0xabc...
INFO - Rewards claimed successfully
```

#### Proxy 模式
```
INFO - Signature type: 1, wallet address: 0x5678... (Proxy)
INFO - Token 0 (ID: 123456): balance = 10.5
INFO - Final amounts (after balance query): [10.5, 0.0]
INFO - Checking approval for Proxy wallet: 0x5678...
INFO - Proxy mode: redeeming through ProxyFactory
INFO - Txn hash: 0xdef...
INFO - Done!
INFO - Rewards claimed successfully
```

### 区块链浏览器

成功的交易应该显示：

#### EOA 模式
- **From**: Your EOA address
- **To**: NegRiskAdapter contract
- **Method**: redeemPositions
- **ERC1155 Transfer**: Token 从 EOA → 0x000...000
- **ERC20 Transfer**: USDC 从 contract → EOA

#### Proxy 模式
- **From**: Your EOA address
- **To**: ProxyFactory contract
- **Method**: proxy
- **Internal Txns**: ProxyFactory → NegRiskAdapter
- **ERC1155 Transfer**: Token 从 Proxy Wallet → 0x000...000
- **ERC20 Transfer**: USDC 从 contract → Proxy Wallet

## 配置要求

### EOA 配置

```yaml
user_wallets:
  - name: "MyEOAWallet"
    address: "0x1234567890abcdef..."       # EOA 地址
    proxy_address: "0x1234567890abcdef..." # 与 address 相同即可
    private_key_env: "MY_PRIVATE_KEY"
    signature_type: 0  # ← EOA 模式
```

### Proxy 配置

```yaml
user_wallets:
  - name: "MyProxyWallet"
    address: "0x1234567890abcdef..."       # EOA 地址
    proxy_address: "0xabcdef1234567890..." # Proxy Wallet 地址
    private_key_env: "MY_PRIVATE_KEY"
    signature_type: 1  # ← Proxy 模式
```

## Gas 消耗对比

| 操作 | EOA 模式 | Proxy 模式 |
|------|----------|------------|
| **Approval** | ~50,000 gas | ~100,000 gas |
| **Redeem** | ~200,000 gas | ~300,000 gas |
| **总计** | ~250,000 gas | ~400,000 gas |

**EOA 模式更省 gas**，因为没有 ProxyFactory 的额外开销。

## 故障排查

### 问题: 仍然报 SafeMath overflow

**检查清单**:
1. ✅ 重启了 API 服务器？
2. ✅ `signature_type` 配置正确？(0 = EOA)
3. ✅ Token 确实在 EOA 地址？
4. ✅ 日志显示 "EOA mode: redeeming directly"？

**调试命令**:
```python
# 检查 token 位置
from polymarket_apis.clients.web3_client import PolymarketWeb3Client

client = PolymarketWeb3Client(private_key="...", chain_id=137)

# EOA 余额
eoa_balance = client.get_token_balance(token_id, client.account.address)
print(f"EOA: {eoa_balance}")

# Proxy 余额
proxy_addr = client.exchange.functions.getPolyProxyWalletAddress(client.account.address).call()
proxy_balance = client.get_token_balance(token_id, proxy_addr)
print(f"Proxy: {proxy_balance}")
```

### 问题: Approval 失败

**可能原因**:
- Gas 不足
- Operator 地址错误
- 已经授权但状态未同步

**解决方案**:
- 增加 gas limit
- 等待几个区块后重试
- 检查日志中的 operator 地址

## 技术细节

### 为什么需要分开处理？

**ProxyFactory 的工作原理**:
1. EOA 签名交易，发送给 ProxyFactory
2. ProxyFactory 调用 Proxy Wallet 的 `proxy()` 方法
3. Proxy Wallet 以 **自己的身份** 调用目标合约
4. 目标合约看到的 `msg.sender` 是 **Proxy Wallet**

**EOA 直接调用**:
1. EOA 签名交易，直接发送给目标合约
2. 目标合约看到的 `msg.sender` 是 **EOA**

### msg.sender 对比

| 场景 | msg.sender | Token 位置 | 结果 |
|------|------------|------------|------|
| EOA 通过 Proxy | Proxy Wallet | EOA | ❌ Overflow |
| EOA 直接调用 | EOA | EOA | ✅ Success |
| Proxy 通过 Proxy | Proxy Wallet | Proxy Wallet | ✅ Success |

## 更新日志

**2025-10-19**:
- ✅ 识别 redeem 执行方式的问题
- ✅ 实现 EOA 直接 redeem 方法 `_redeem_position_eoa()`
- ✅ 根据 signature_type 选择执行方式
- ✅ 修复 approval 授权逻辑
- ✅ 添加详细日志输出
- ✅ 创建完整技术文档

## 相关文档

- [SIGNATURE_TYPE_ADDRESS_FIX.md](./SIGNATURE_TYPE_ADDRESS_FIX.md) - 地址选择修复
- [REDEEM_BALANCE_FIX.md](./REDEEM_BALANCE_FIX.md) - 余额查询修复
- [REDEEM_APPROVAL_FIX.md](./REDEEM_APPROVAL_FIX.md) - 授权问题修复

## 总结

**完整的修复包括三个部分**:

1. ✅ **余额查询**: 根据 signature_type 选择地址
2. ✅ **授权检查**: 根据 signature_type 选择地址和执行方式
3. ✅ **Redeem 执行**: 根据 signature_type 选择直接调用或通过 ProxyFactory

**现在 EOA 模式应该能正常 redeem 了！** 🎉
