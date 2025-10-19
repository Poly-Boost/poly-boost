# Redeem 调试指南

## 问题：amounts 是 [0, 0]，没有 redeem 任何代币

### 症状

交易成功执行，但是：
- `amounts = [0, 0]`
- 实际没有 redeem 任何代币
- 区块链浏览器显示交易成功但没有转账

### 可能的原因

#### 1. token_ids 没有正确传递

**前端检查**：

打开浏览器开发者工具（F12），查看 Console 输出：

```javascript
Redeem request: {
  conditionId: "0x...",
  tokenIds: ["123456", "789012"],  // ✅ 应该看到两个 token ID
  outcomeIndex: 0,
  size: 10.5,
  asset: "123456",
  oppositeAsset: "789012"
}
```

**检查点**：
- ✅ `tokenIds` 数组应该有 2 个元素
- ✅ 至少一个 token ID 不为 null
- ✅ `asset` 字段存在且有值
- ⚠️ 如果 `oppositeAsset` 是 null，需要检查后端数据

#### 2. 后端没有执行余额查询

**后端日志检查**：

查看后端日志，应该看到：

```
INFO - Claiming rewards for condition_id=0x..., requested amounts=[0, 0], token_ids=['123456', '789012']
INFO - Proxy wallet address: 0xABC...
INFO - Token IDs provided: ['123456', '789012']
INFO - Querying actual token balances from chain...
INFO - Token 0 (ID: 123456): balance = 10.5
INFO - Token 1 (ID: 789012): balance = 0.0
INFO - Final amounts (after balance query): [10.5, 0.0]
INFO - Redeeming with amounts: [10.5, 0.0]
```

**如果看到警告**：

```
WARNING - No valid token_ids provided (got: None), using requested amounts: [0, 0]
```

说明 token_ids 没有传到后端！

#### 3. 余额查询失败

**后端错误日志**：

```
ERROR - Failed to query balance for token 123456: ...
```

可能原因：
- Token ID 格式错误
- RPC 节点连接问题
- 合约调用失败

## 调试步骤

### Step 1: 检查前端请求

在浏览器开发者工具的 **Network** 标签中：

1. 找到 `POST /orders/rewards/claim` 请求
2. 查看 **Request Payload**:

```json
{
  "condition_id": "0x1234567890abcdef...",
  "amounts": [0, 0],
  "token_ids": ["123456789", "987654321"]  // ✅ 确认这个字段存在
}
```

**如果 `token_ids` 不存在或为 null**：
- 检查 Position 数据是否包含 `asset` 和 `oppositeAsset` 字段
- 检查前端代码是否正确构造 tokenIds 数组

### Step 2: 检查后端日志

启动 API 服务器后，查看控制台输出：

```bash
# 应该看到详细的日志
python run_api.py
```

**正常流程的日志**：

```
INFO - Claiming rewards for condition_id=...
INFO - Proxy wallet address: 0x...
INFO - Token IDs provided: ['...', '...']
INFO - Querying actual token balances from chain...
INFO - Token 0 (ID: ...): balance = X.XX
INFO - Token 1 (ID: ...): balance = Y.YY
INFO - Final amounts (after balance query): [X.XX, Y.YY]
INFO - Checking ERC1155 approval status...
INFO - Redeeming with amounts: [X.XX, Y.YY]
```

### Step 3: 手动测试余额查询

在 Python 中手动测试：

```python
from polymarket_apis.clients.web3_client import PolymarketWeb3Client
from web3 import Web3

# 初始化客户端
web3_client = PolymarketWeb3Client(
    private_key="your_private_key",
    chain_id=137
)

# 获取 proxy address
proxy_address = web3_client.exchange.functions.getPolyProxyWalletAddress(
    web3_client.account.address
).call()

print(f"Proxy address: {proxy_address}")

# 查询余额
token_id = "123456789"  # 替换为实际的 token ID
balance = web3_client.get_token_balance(token_id, proxy_address)

print(f"Token {token_id} balance: {balance}")
```

### Step 4: 检查 Position 数据结构

在前端打印完整的 position 对象：

```typescript
console.log('Full position data:', JSON.stringify(position, null, 2));
```

**必需的字段**：
```json
{
  "asset": "123456789",           // ✅ 当前持有的 token ID
  "oppositeAsset": "987654321",   // ⚠️ 对面的 token ID (可能缺失)
  "conditionId": "0xabc...",      // ✅ Condition ID
  "outcomeIndex": 0,              // ✅ 0 或 1
  "size": 10.5,                   // 持仓数量
  "redeemable": true              // 是否可 redeem
}
```

**如果 `oppositeAsset` 缺失**：

后端会使用 `amounts[1] = 0`，只 redeem 当前持有的 token。这通常是正确的（只持有一边）。

## 常见问题

### Q1: 为什么 amounts 是 [0, 0]？

**A**: 前端传的就是 `[0, 0]`，这是占位参数。后端应该查询实际余额并替换它。

如果最终还是 `[0, 0]`，说明：
1. token_ids 没有传到后端
2. 余额查询失败
3. 查询到的余额确实是 0（没有持仓）

### Q2: 如何确认 token_ids 正确？

**A**: Token ID 应该是数字字符串，例如 `"123456789"`。

可以在 Polymarket 前端查看：
1. 打开浏览器开发者工具
2. 查看 Network 请求
3. 找到持仓相关的 API 响应
4. 查看 token ID 字段

### Q3: oppositeAsset 为什么是 null？

**A**: 可能的原因：
1. 后端 API 没有返回该字段
2. 该市场只有单边持仓
3. 数据结构不完整

**解决方案**：

如果只有 `asset` 没有 `oppositeAsset`，可以这样构造：

```typescript
// 只 redeem 当前持有的一边
const tokenIds = position.outcomeIndex === 0 
  ? [position.asset, null]  // [YES, null]
  : [null, position.asset]; // [null, YES]
```

后端会忽略 null 的 token ID，只查询有值的那个。

### Q4: 如何强制使用指定的 amounts？

**A**: 不传 `token_ids` 参数：

```typescript
// 使用前端指定的 amounts，不查询余额
const amounts = [position.size, 0];
await apiClient.claimRewards(position.conditionId, amounts);  // 不传第3个参数
```

**注意**: 这样做有风险，如果实际余额不足会失败。

## 修复建议

### 方案 1: 确保 token_ids 正确传递（推荐）

**前端**：
```typescript
// 添加日志
console.log('Token IDs:', tokenIds);
console.log('Request payload:', { condition_id, amounts, token_ids: tokenIds });

// 发送请求
await apiClient.claimRewards(conditionId, amounts, tokenIds);
```

**后端**：
- 已添加详细日志
- 检查日志输出

### 方案 2: 如果 oppositeAsset 总是缺失

修改后端逻辑，只 redeem 非 null 的 token：

```python
# 如果只有一个 token_id，只查询和 redeem 那一个
if token_ids:
    for i, token_id in enumerate(token_ids):
        if token_id:
            balance = get_token_balance(token_id)
            actual_amounts.append(balance)
        else:
            actual_amounts.append(0)  # 另一边是 0
```

这个逻辑已经实现了！

### 方案 3: 降级到使用 position.size

如果 token_ids 方案不工作，可以暂时降级：

```typescript
// 临时方案：使用前端的 size
const amounts = position.outcomeIndex === 0 
  ? [position.size, 0]
  : [0, position.size];

await apiClient.claimRewards(position.conditionId, amounts);  // 不传 token_ids
```

**风险**: 如果 size 过时，会失败。

## 下一步

1. **启用日志**：确保前端和后端都有详细日志
2. **测试一次**：点击 Redeem 按钮
3. **查看日志**：
   - 浏览器 Console
   - 浏览器 Network 标签
   - 后端控制台
4. **分享日志**：如果还有问题，分享日志以便进一步诊断

## 验证清单

在点击 Redeem 后，检查：

- [ ] 前端 Console 显示 `Redeem request` 日志
- [ ] `tokenIds` 数组有值（至少一个非 null）
- [ ] Network 请求的 payload 包含 `token_ids` 字段
- [ ] 后端日志显示 "Token IDs provided"
- [ ] 后端日志显示 "Querying actual token balances"
- [ ] 后端日志显示查询到的余额（应该 > 0）
- [ ] 后端日志显示 "Redeeming with amounts: [X, Y]" (X 或 Y > 0)
- [ ] 区块链浏览器显示实际转账

如果以上任何一步失败，就能定位问题所在。
