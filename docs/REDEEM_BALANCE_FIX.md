# Redeem SafeMath Overflow 修复

## 问题描述

Redeem 交易失败,错误信息:

```
execution reverted - SafeMath: subtraction overflow
```

**交易详情**: https://web3.ouchyi.bid/zh-hans/explorer/polygon/tx/0x38fcf6f2c32123b07e8b73ee59100f66b8f18127fe0f82a1612e7084d3bc8768

## 根本原因

**SafeMath subtraction overflow** 发生在尝试执行 `a - b` 时 `b > a`，导致结果为负数（下溢）。

在 redeem 的场景中：
- 前端传递的 `amounts` 参数是从前端存储的 `position.size` 获取
- 但实际链上余额可能已经变化（被其他操作消耗）
- 当请求 redeem 的数量 > 实际余额时，合约会报 SafeMath 错误

### 错误的流程

```
前端: amounts = [position.size, 0]  // 例如 [10.0, 0]
  ↓
后端: 直接使用 amounts 调用 redeem
  ↓
合约: 尝试 balance - amounts[0]
      实际余额可能只有 8.0
      8.0 - 10.0 = ❌ Underflow!
```

## 解决方案

### 核心思路

**在 redeem 前查询链上实际余额，使用实际余额而不是前端传来的值**。

### 实现步骤

#### 1. 后端: 添加余额查询逻辑

```python
def claim_rewards(
    self, 
    condition_id: str, 
    amounts: List[float],
    token_ids: Optional[List[str]] = None  # 新增参数
) -> Dict[str, Any]:
    """
    Claim rewards by redeeming positions.
    
    如果提供 token_ids，会先查询链上实际余额再 redeem。
    """
    # Get proxy wallet address
    proxy_address = self.web3_client.exchange.functions.getPolyProxyWalletAddress(
        self.web3_client.account.address
    ).call()
    
    # Query actual balances if token_ids provided
    actual_amounts = []
    if token_ids:
        logger.info("Querying actual token balances from chain...")
        for token_id in token_ids:
            if token_id:
                balance = self.web3_client.get_token_balance(
                    token_id=token_id,
                    address=proxy_address
                )
                actual_amounts.append(balance)
                logger.info(f"Token {token_id}: balance = {balance}")
            else:
                actual_amounts.append(0)
        
        # Use actual balances instead of requested amounts
        amounts = actual_amounts
    
    # Redeem with actual amounts
    self.web3_client.redeem_position(
        condition_id=condition_id,
        amounts=amounts,
        neg_risk=True
    )
```

#### 2. Schema: 添加 token_ids 参数

```python
class ClaimRewardsRequest(BaseModel):
    condition_id: str
    amounts: List[float]
    token_ids: Optional[List[Optional[str]]] = Field(
        None, 
        description="Token IDs for balance query [token1_id, token2_id]"
    )
```

#### 3. 前端: 传递 token_ids

```typescript
const handleRedeem = async (position: Position) => {
  // 传递 token_ids 让后端查询实际余额
  const tokenIds = position.outcomeIndex === 0 
    ? [position.asset || null, position.oppositeAsset || null]  // [YES, NO]
    : [position.oppositeAsset || null, position.asset || null]; // [NO, YES]
  
  // amounts 是占位参数，后端会查询实际余额替换
  const amounts = [0, 0];
  
  await apiClient.claimRewards(position.conditionId, amounts, tokenIds);
};
```

## 正确的流程

```
前端: 传递 token_ids = [token1_id, token2_id]
      amounts = [0, 0]  (占位参数)
  ↓
后端: 查询实际余额
      balance1 = get_token_balance(token1_id)  // 例如 8.0
      balance2 = get_token_balance(token2_id)  // 例如 0
      actual_amounts = [8.0, 0]
  ↓
合约: balance - actual_amounts[0]
      8.0 - 8.0 = 0 ✅ 成功!
```

## 技术细节

### Token Balance 查询

```python
def get_token_balance(self, token_id: str, address: EthAddress) -> float:
    """
    Get the token balance of the given address.
    
    调用 ConditionalTokens 合约的 balanceOf 方法。
    """
    balance = self.conditional_tokens.functions.balanceOf(
        Web3.to_checksum_address(address),
        int(token_id)
    ).call()
    
    return float(balance / 1e6)  # 转换为标准单位
```

### Token IDs 顺序

对于二元市场，token_ids 应该是 `[outcome1_token_id, outcome2_token_id]`：

- **outcomeIndex = 0** (YES): `[YES_token_id, NO_token_id]`
- **outcomeIndex = 1** (NO): `[NO_token_id, YES_token_id]`

**注意**: 顺序必须与合约期望的 `[index1, index2]` 对应。

### 为什么需要两个 Token IDs?

Polymarket 使用 ConditionalTokens (ERC1155)：
- 每个二元市场有 2 个 outcome tokens
- Redeem 时需要指定每个 outcome 的数量
- `amounts = [amount1, amount2]` 对应 `token_ids = [token1, token2]`

## API 使用

### 请求示例

```http
POST /orders/rewards/claim
Content-Type: application/json

{
  "condition_id": "0x1234567890abcdef...",
  "amounts": [0, 0],
  "token_ids": [
    "123456789",  // outcome 1 token ID
    "987654321"   // outcome 2 token ID
  ]
}
```

### 响应示例

```json
{
  "status": "success",
  "condition_id": "0x1234...",
  "amounts": [8.5, 0],  // 实际查询到的余额
  "message": "Rewards claimed successfully"
}
```

## 日志示例

```
INFO - Claiming rewards for condition_id=0x123..., requested amounts=[0, 0], token_ids=['123456', '789012']
INFO - Querying actual token balances from chain...
INFO - Token 123456: balance = 8.5
INFO - Token 789012: balance = 0.0
INFO - Using actual balances: [8.5, 0.0]
INFO - Checking ERC1155 approval status...
INFO - Already approved, skipping approval transaction
INFO - Redeeming with amounts: [8.5, 0.0]
INFO - Rewards claimed successfully
```

## 优势

### ✅ 避免 Overflow 错误

- 使用实际余额，永远不会超过链上持有量
- 自动适应余额变化

### ✅ 自动同步

- 不依赖前端存储的过时数据
- 实时查询链上最新余额

### ✅ 灵活性

- 支持部分 redeem (如果需要)
- 支持手动指定 amounts (不传 token_ids)

## 注意事项

### 1. Gas 消耗

查询余额会增加少量 gas 消耗（view 函数，不上链），但 redeem 本身已经是链上操作。

### 2. Token IDs 必须正确

- 错误的 token_id 会导致查询失败
- 必须是该市场的实际 token IDs

### 3. Redeemable 状态

只有市场解决后才能 redeem：
- 前端通过 `position.redeemable === true` 判断
- 后端无额外验证，依赖合约逻辑

## 测试建议

### 测试用例 1: 正常 Redeem

```python
# 持有 10 个 YES token
# 请求 redeem
result = claim_rewards(
    condition_id="0x123...",
    amounts=[0, 0],
    token_ids=["yes_token_id", "no_token_id"]
)
# 期望: 实际 redeem 10 个
```

### 测试用例 2: 部分消耗后 Redeem

```python
# 最初持有 10 个
# 其他操作消耗了 3 个，剩余 7 个
# 请求 redeem
result = claim_rewards(
    condition_id="0x123...",
    amounts=[0, 0],
    token_ids=["yes_token_id", "no_token_id"]
)
# 期望: 实际 redeem 7 个 (查询到的实际余额)
```

### 测试用例 3: 无 Token IDs (降级)

```python
# 不传 token_ids，使用前端指定的 amounts
result = claim_rewards(
    condition_id="0x123...",
    amounts=[5.0, 0],
    token_ids=None
)
# 期望: 使用指定的 5.0 进行 redeem
# 风险: 如果余额 < 5.0 会失败
```

## 更新日志

**2025-10-19**:
- ✅ 识别 SafeMath overflow 的根本原因
- ✅ 实现链上余额查询逻辑
- ✅ 添加 token_ids 参数支持
- ✅ 更新前端传递 token_ids
- ✅ 避免使用过时的前端余额数据

## 相关文档

- [REDEEM_APPROVAL_FIX.md](./REDEEM_APPROVAL_FIX.md) - Approval 授权问题
- [REDEEM_FIX_PROXY_ADDRESS.md](./REDEEM_FIX_PROXY_ADDRESS.md) - Proxy Address 获取
- ConditionalTokens ERC1155 标准

## 总结

通过在 redeem 前查询链上实际余额，完全避免了 SafeMath overflow 错误。这是一个更健壮的方案，因为它不依赖前端可能过时的数据。
