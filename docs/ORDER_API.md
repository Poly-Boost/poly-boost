# Order API 使用文档

## 概述

Order API 提供了在 Polymarket 上进行交易和管理订单的接口。支持市价单、限价单以及奖励收获功能。

## 配置要求

在使用 Order API 之前,需要在 `config/config.yaml` 中配置用户钱包信息:

```yaml
polymarket_api:
  proxy: "http://localhost:7891"  # 可选代理
  timeout: 30.0                    # API 超时时间
  verify_ssl: true                 # 是否验证 SSL

user_wallets:
  - name: "MyWallet"
    address: "0x..."               # 钱包地址
    proxy_address: "0x..."         # Polymarket 代理地址
    private_key_env: "MY_WALLET_PRIVATE_KEY"  # 私钥环境变量名
    signature_type: 2              # 签名类型: 0=EOA, 1=Polymarket proxy, 2=Browser wallet proxy
```

**重要**: 私钥应该通过环境变量设置,不要直接写在配置文件中!

```bash
export MY_WALLET_PRIVATE_KEY="your_private_key_here"
```

## API 端点

### 1. 市价出售头寸

**端点**: `POST /orders/sell/market`

市价立即出售头寸。

**请求体**:
```json
{
  "token_id": "123456789",
  "amount": 10.0,           // 可选,null 或不传表示出售全部
  "order_type": "FOK"       // FOK 或 GTC
}
```

**参数说明**:
- `token_id`: 要出售的 token ID
- `amount`: 出售数量,传 `null` 或不传表示出售全部持仓
- `order_type`: 
  - `FOK` (Fill or Kill): 全部成交或取消
  - `GTC` (Good Till Cancel): 持续有效直到取消

**响应示例**:
```json
{
  "status": "success",
  "order_id": "0xabc...",
  "token_id": "123456789",
  "amount": 10.0,
  "side": "SELL",
  "order_type": "market",
  "response": { ... }
}
```

### 2. 限价出售头寸

**端点**: `POST /orders/sell/limit`

以指定价格挂限价卖单。

**请求体**:
```json
{
  "token_id": "123456789",
  "price": 0.55,            // 限价,必须在 0-1 之间
  "amount": 10.0,           // 可选,null 表示出售全部
  "order_type": "GTC"       // GTC 或 GTD
}
```

**参数说明**:
- `price`: 限价价格,必须在 0 到 1 之间
- `order_type`:
  - `GTC` (Good Till Cancel): 持续有效直到取消
  - `GTD` (Good Till Date): 持续有效到指定日期

**响应示例**:
```json
{
  "status": "success",
  "order_id": "0xdef...",
  "token_id": "123456789",
  "amount": 10.0,
  "price": 0.55,
  "side": "SELL",
  "order_type": "limit",
  "response": { ... }
}
```

### 3. 市价买入头寸

**端点**: `POST /orders/buy/market`

市价立即买入头寸。

**请求体**:
```json
{
  "token_id": "123456789",
  "amount": 10.0,
  "order_type": "FOK"
}
```

### 4. 限价买入头寸

**端点**: `POST /orders/buy/limit`

以指定价格挂限价买单。

**请求体**:
```json
{
  "token_id": "123456789",
  "price": 0.45,
  "amount": 10.0,
  "order_type": "GTC"
}
```

### 5. 收获奖励

**端点**: `POST /orders/rewards/claim`

收获已解决市场的奖励。

**请求体**:
```json
{
  "condition_id": "0x1234...",
  "amounts": [10.0, 5.0]        // [outcome1数量, outcome2数量]
}
```

**参数说明**:
- `condition_id`: 已解决市场的 condition ID
- `amounts`: 要赎回的两个结果的数量数组

**响应示例**:
```json
{
  "status": "success",
  "condition_id": "0x1234...",
  "amounts": [10.0, 5.0],
  "message": "Rewards claimed successfully"
}
```

### 6. 查询活跃订单

**端点**: `GET /orders`

查询用户的活跃订单。

**查询参数**:
- `order_id` (可选): 按订单 ID 过滤
- `condition_id` (可选): 按市场 condition ID 过滤
- `token_id` (可选): 按 token ID 过滤

**示例**:
```
GET /orders?token_id=123456789
```

**响应示例**:
```json
[
  {
    "id": "0xabc...",
    "token_id": "123456789",
    "price": "0.55",
    "size": "10.0",
    "side": "SELL",
    ...
  }
]
```

### 7. 取消订单

**端点**: `DELETE /orders/cancel`

取消指定的订单。

**请求体**:
```json
{
  "order_id": "0xabc..."
}
```

### 8. 取消所有订单

**端点**: `DELETE /orders/cancel/all`

取消用户的所有活跃订单。

**无需请求体**

## 使用示例

### Python 示例

```python
import requests

BASE_URL = "http://localhost:8000"

# 市价出售全部头寸
def sell_all_market(token_id):
    response = requests.post(
        f"{BASE_URL}/orders/sell/market",
        json={
            "token_id": token_id,
            "amount": None,  # 出售全部
            "order_type": "FOK"
        }
    )
    return response.json()

# 限价出售部分头寸
def sell_limit(token_id, price, amount):
    response = requests.post(
        f"{BASE_URL}/orders/sell/limit",
        json={
            "token_id": token_id,
            "price": price,
            "amount": amount,
            "order_type": "GTC"
        }
    )
    return response.json()

# 收获奖励
def claim_rewards(condition_id, amounts):
    response = requests.post(
        f"{BASE_URL}/orders/rewards/claim",
        json={
            "condition_id": condition_id,
            "amounts": amounts
        }
    )
    return response.json()

# 使用示例
result = sell_all_market("123456789")
print(result)
```

### cURL 示例

```bash
# 市价出售全部
curl -X POST http://localhost:8000/orders/sell/market \
  -H "Content-Type: application/json" \
  -d '{
    "token_id": "123456789",
    "amount": null,
    "order_type": "FOK"
  }'

# 限价出售
curl -X POST http://localhost:8000/orders/sell/limit \
  -H "Content-Type: application/json" \
  -d '{
    "token_id": "123456789",
    "price": 0.55,
    "amount": 10.0,
    "order_type": "GTC"
  }'

# 收获奖励
curl -X POST http://localhost:8000/orders/rewards/claim \
  -H "Content-Type: application/json" \
  -d '{
    "condition_id": "0x1234...",
    "amounts": [10.0, 5.0]
  }'
```

## 错误处理

API 返回标准 HTTP 状态码:

- `200`: 成功
- `400`: 请求参数错误
- `500`: 服务器内部错误

错误响应格式:
```json
{
  "detail": "错误描述信息"
}
```

## 注意事项

1. **私钥安全**: 永远不要在代码或配置文件中硬编码私钥
2. **Gas 费用**: 链上交易(如收获奖励)需要支付 Polygon 网络的 gas 费用
3. **订单类型**: 
   - FOK 适合需要立即成交的场景
   - GTC 适合挂单等待成交的场景
4. **价格范围**: Polymarket 的价格范围是 0-1,表示概率
5. **Amount 为 null**: 在出售操作中,`amount` 参数为 `null` 时会自动查询链上余额并出售全部

## 调试技巧

1. 使用 `/health` 端点检查 API 是否正常运行
2. 查看日志文件了解详细的错误信息
3. 使用 `rest/poly-boost-orders.http` 文件进行接口测试
4. 确保配置文件中的钱包地址和私钥正确

## 技术架构

- **服务层**: `poly_boost/services/order_service.py` - 实现核心交易逻辑
- **路由层**: `poly_boost/api/routes/orders.py` - 定义 API 端点
- **Schema 层**: `poly_boost/api/schemas/order_schemas.py` - 请求/响应验证
- **依赖注入**: `poly_boost/api/dependencies.py` - 服务初始化和依赖管理

## 客户端集成

Order Service 集成了以下 Polymarket 客户端:

- **PolymarketClobClient**: 用于订单管理(创建、取消订单等)
- **PolymarketWeb3Client**: 用于链上操作(收获奖励等)

客户端配置自动适配 `config.yaml` 中的参数:
- `proxy`: 代理服务器
- `timeout`: 超时时间
- `verify_ssl`: SSL 验证
