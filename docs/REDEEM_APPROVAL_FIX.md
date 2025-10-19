# Redeem 授权问题修复

## 问题描述

调用 redeem 接口时，交易在区块链上执行失败，错误信息：

```
execution reverted - ERC1155: need operator approval for 3rd party transfers.
```

**示例交易**: https://web3.ouchyi.bid/zh-hans/explorer/polygon/tx/0x291b6d7ffdb29fa05e434d94b747455145dcbf1e2cef75d0b41ee9a29be3e370

## 根本原因

### ERC1155 授权机制

1. **ConditionalTokens 是 ERC1155 合约**: Polymarket 的头寸代币是 ERC1155 标准的代币
2. **需要授权第三方操作**: 当通过 `NegRiskAdapter` 合约来 redeem 头寸时，实际上是让该合约代表您操作您的 ERC1155 代币
3. **缺少 setApprovalForAll**: 如果没有事先授权，合约就无法操作您的代币，导致交易回滚

### Redeem 流程

```
用户调用 redeem
  ↓
通过 ProxyWallet 调用 NegRiskAdapter.redeemPositions()
  ↓
NegRiskAdapter 尝试转移用户的 ERC1155 代币
  ↓
❌ 失败: 用户没有授权 NegRiskAdapter 操作他的代币
```

### 正确流程

```
1. 检查授权状态
   ConditionalTokens.isApprovedForAll(proxyWallet, NegRiskAdapter)
   ↓
2. 如果未授权，发送授权交易
   ConditionalTokens.setApprovalForAll(NegRiskAdapter, true)
   ↓
3. 等待授权交易确认
   ↓
4. 执行 redeem 操作
   NegRiskAdapter.redeemPositions()
```

## 解决方案

### 1. 添加授权检查

在 `claim_rewards` 方法中，添加授权检查：

```python
def claim_rewards(self, condition_id: str, amounts: List[float]) -> Dict[str, Any]:
    # ... existing code ...
    
    # Check and set approval if needed
    logger.info("Checking ERC1155 approval status...")
    self._ensure_conditional_tokens_approval(neg_risk=neg_risk)
    
    # Redeem positions
    self.web3_client.redeem_position(...)
```

### 2. 实现自动授权

新增 `_ensure_conditional_tokens_approval` 方法：

```python
def _ensure_conditional_tokens_approval(self, neg_risk: bool = True):
    """
    Ensure ConditionalTokens contract is approved for the adapter.
    
    Steps:
    1. Get proxy wallet address
    2. Check if already approved
    3. If not approved, send approval transaction
    4. Wait for confirmation
    """
    from web3 import Web3
    
    # Get the operator address
    operator = (
        self.web3_client.neg_risk_adapter_address if neg_risk 
        else self.web3_client.exchange_address
    )
    
    # Get proxy wallet address
    proxy_address = self.web3_client.proxy_factory.functions.getProxyWallet(
        self.web3_client.account.address
    ).call()
    
    # Check if already approved
    is_approved = self.web3_client.conditional_tokens.functions.isApprovedForAll(
        Web3.to_checksum_address(proxy_address),
        Web3.to_checksum_address(operator)
    ).call()
    
    if is_approved:
        logger.info("Already approved, skipping approval transaction")
        return
    
    # Send approval transaction
    logger.info("Not approved yet, sending approval transaction...")
    
    # Encode setApprovalForAll call
    approval_data = self.web3_client.conditional_tokens.encode_abi(
        abi_element_identifier="setApprovalForAll",
        args=[Web3.to_checksum_address(operator), True]
    )
    
    # Create proxy transaction
    proxy_txn = {
        "typeCode": 1,
        "to": self.web3_client.conditional_tokens_address,
        "value": 0,
        "data": approval_data,
    }
    
    # Build and send transaction
    nonce = self.web3_client.w3.eth.get_transaction_count(
        self.web3_client.account.address
    )
    
    txn_data = self.web3_client.proxy_factory.functions.proxy([proxy_txn]).build_transaction({
        "nonce": nonce,
        "gasPrice": int(1.05 * self.web3_client.w3.eth.gas_price),
        "gas": 500000,
        "from": self.web3_client.account.address,
    })
    
    signed_txn = self.web3_client.account.sign_transaction(txn_data)
    tx_hash = self.web3_client.w3.eth.send_raw_transaction(
        signed_txn.raw_transaction
    ).hex()
    
    logger.info(f"Approval transaction sent: {tx_hash}")
    
    # Wait for confirmation
    receipt = self.web3_client.w3.eth.wait_for_transaction_receipt(tx_hash)
    
    if receipt['status'] == 1:
        logger.info("Approval transaction confirmed successfully")
    else:
        raise Exception(f"Approval transaction failed: {tx_hash}")
```

## 技术细节

### 合约地址

#### Polygon Mainnet (Chain ID: 137)

| 合约 | 地址 | 说明 |
|------|------|------|
| ConditionalTokens | `0x4D97DCd97eC945f40cF65F87097ACe5EA0476045` | ERC1155 代币合约 |
| NegRiskAdapter | `0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296` | Neg Risk 市场适配器 |
| CTFExchange | `0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E` | 标准市场交易所 |
| ProxyWalletFactory | `0xaB45c5A4B0c941a2F231C04C3f49182e1A254052` | 代理钱包工厂 |

### 授权范围

- **isApprovedForAll**: 检查是否已授权
  - `owner`: Proxy Wallet 地址
  - `operator`: NegRiskAdapter 或 CTFExchange 地址

- **setApprovalForAll**: 设置授权
  - `operator`: 要授权的合约地址
  - `approved`: true/false

### Gas 消耗

- **Approval 交易**: 约 50,000 - 100,000 gas
- **Redeem 交易**: 约 200,000 - 500,000 gas (取决于市场类型)

## 执行流程

### 首次 Redeem

```
1. 用户调用 /orders/rewards/claim
   ↓
2. OrderService.claim_rewards()
   ↓
3. _ensure_conditional_tokens_approval()
   - 检查授权状态 ❌ 未授权
   - 发送 setApprovalForAll 交易
   - 等待交易确认 ✅
   ↓
4. web3_client.redeem_position()
   - 发送 redeem 交易
   - 等待交易确认 ✅
   ↓
5. 返回成功结果
```

### 后续 Redeem (已授权)

```
1. 用户调用 /orders/rewards/claim
   ↓
2. OrderService.claim_rewards()
   ↓
3. _ensure_conditional_tokens_approval()
   - 检查授权状态 ✅ 已授权
   - 跳过授权步骤
   ↓
4. web3_client.redeem_position()
   - 发送 redeem 交易
   - 等待交易确认 ✅
   ↓
5. 返回成功结果
```

## 日志示例

### 首次调用 (需要授权)

```
INFO - Claiming rewards for condition_id=0x123..., amounts=[10.0, 0]
INFO - Checking ERC1155 approval status...
INFO - Checking approval for proxy wallet: 0xABC...
INFO - Operator: 0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296
INFO - Not approved yet, sending approval transaction...
INFO - Approval transaction sent: 0xdef456...
INFO - Approval transaction confirmed successfully
INFO - Redeem transaction sent: 0x789abc...
INFO - Rewards claimed successfully
```

### 后续调用 (已授权)

```
INFO - Claiming rewards for condition_id=0x456..., amounts=[5.0, 0]
INFO - Checking ERC1155 approval status...
INFO - Checking approval for proxy wallet: 0xABC...
INFO - Operator: 0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296
INFO - Already approved, skipping approval transaction
INFO - Redeem transaction sent: 0x123def...
INFO - Rewards claimed successfully
```

## 优化说明

### 1. 智能检查

- 每次 redeem 前都会检查授权状态
- 只有未授权时才发送授权交易
- 已授权时直接跳过，节省 gas

### 2. 一次授权，永久有效

- `setApprovalForAll` 授权是**永久性**的
- 首次授权后，后续所有 redeem 操作都无需再次授权
- 除非用户主动撤销授权

### 3. 自动化处理

- 用户无需手动授权
- 完全透明的自动化流程
- 友好的日志提示

## API 使用

### Redeem 接口

```http
POST /orders/rewards/claim
Content-Type: application/json

{
  "condition_id": "0x1234567890abcdef...",
  "amounts": [10.0, 0]
}
```

### 响应

**成功 (首次)**:
```json
{
  "status": "success",
  "condition_id": "0x1234...",
  "amounts": [10.0, 0],
  "message": "Rewards claimed successfully"
}
```

**注意**: 首次调用会多花费一些时间和 gas 用于授权交易。

## 故障排查

### 问题: 授权交易失败

**可能原因**:
1. Gas 价格太低
2. 网络拥堵
3. Nonce 冲突

**解决方案**:
- 等待几分钟后重试
- 检查钱包余额是否足够支付 gas

### 问题: Redeem 交易仍然失败

**可能原因**:
1. 授权交易还未确认
2. 市场尚未解决
3. 头寸数量不足

**解决方案**:
- 等待授权交易确认后再次尝试
- 检查市场状态
- 检查头寸余额

### 问题: 如何撤销授权

如果出于安全考虑想撤销授权，需要手动调用：

```python
# 撤销授权
self.web3_client.conditional_tokens.functions.setApprovalForAll(
    operator_address,
    False  # 设置为 False
).transact()
```

## 安全考虑

### 授权的影响

- ✅ **安全**: 只授权官方的 Polymarket 合约
- ✅ **可控**: 随时可以撤销授权
- ✅ **必要**: Redeem 操作必需的步骤

### 授权的风险

- ⚠️ **授权范围**: 授权合约可以操作您的**所有** ERC1155 代币（在该合约中）
- ⚠️ **合约风险**: 如果合约有漏洞，可能影响您的代币
- ✅ **Polymarket 官方**: 我们只授权 Polymarket 官方合约，已经过审计

## 相关资源

- **Polygon 浏览器**: https://polygonscan.com/
- **ConditionalTokens 合约**: https://polygonscan.com/address/0x4D97DCd97eC945f40cF65F87097ACe5EA0476045
- **NegRiskAdapter 合约**: https://polygonscan.com/address/0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296
- **ERC1155 标准**: https://eips.ethereum.org/EIPS/eip-1155

## 更新日志

**2025-10-19**:
- ✅ 识别 redeem 失败的根本原因
- ✅ 实现自动授权检查和处理
- ✅ 添加详细的日志记录
- ✅ 优化用户体验（自动化）
- ✅ 创建完整的技术文档
