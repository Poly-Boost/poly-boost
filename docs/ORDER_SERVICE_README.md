# Order Service - 订单管理服务

## 概述

Order Service 是 Poly-Boost 新增的核心服务,提供完整的 Polymarket 交易功能。支持市价单、限价单交易以及奖励收获。

## 特性

### ✅ 已实现功能

- **市价交易**
  - 市价买入
  - 市价出售(支持出售全部)

- **限价交易**
  - 限价买入
  - 限价出售(支持出售全部)

- **订单管理**
  - 查询活跃订单
  - 取消单个订单
  - 取消所有订单

- **奖励管理**
  - 收获已解决市场的奖励

### 🎯 核心优势

1. **智能出售**: `amount` 参数支持 `null`,自动查询链上余额并出售全部
2. **配置适配**: 完全适配 `config.yaml` 的 API 配置(proxy, timeout, ssl)
3. **类型安全**: 使用 Pydantic 进行请求/响应验证
4. **错误处理**: 完善的异常处理和日志记录

## 架构设计

```
poly_boost/
├── services/
│   └── order_service.py          # 核心业务逻辑
├── api/
│   ├── routes/
│   │   └── orders.py              # API 端点定义
│   ├── schemas/
│   │   └── order_schemas.py       # 请求/响应模型
│   └── dependencies.py            # 依赖注入
```

### 依赖的客户端

- **PolymarketClobClient**: 订单簿操作(创建/取消订单)
- **PolymarketWeb3Client**: 链上操作(收获奖励)

## 快速开始

### 1. 配置环境

在 `config/config.yaml` 中配置:

```yaml
polymarket_api:
  proxy: "http://localhost:7891"
  timeout: 30.0
  verify_ssl: true

user_wallets:
  - name: "MyWallet"
    address: "0xYourAddress"
    proxy_address: "0xYourProxyAddress"
    private_key_env: "MY_WALLET_PRIVATE_KEY"
    signature_type: 2
```

设置环境变量:

```bash
export MY_WALLET_PRIVATE_KEY="your_private_key_here"
```

### 2. 启动 API 服务

```bash
python run_api.py
```

### 3. 使用 API

#### 方式一: HTTP 请求

使用 `rest/poly-boost-orders.http` 文件测试:

```http
POST http://localhost:8000/orders/sell/market
Content-Type: application/json

{
  "token_id": "123456789",
  "amount": null,
  "order_type": "FOK"
}
```

#### 方式二: Python 代码

```python
import requests

# 市价出售全部
response = requests.post(
    "http://localhost:8000/orders/sell/market",
    json={
        "token_id": "123456789",
        "amount": None,  # 出售全部
        "order_type": "FOK"
    }
)
print(response.json())
```

#### 方式三: 直接使用 Service

```python
from poly_boost.services import OrderService

# 假设已初始化 service
result = service.sell_position_market(
    token_id="123456789",
    amount=None,  # 出售全部
    order_type=OrderType.FOK
)
```

## API 端点

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/orders/sell/market` | 市价出售 |
| POST | `/orders/sell/limit` | 限价出售 |
| POST | `/orders/buy/market` | 市价买入 |
| POST | `/orders/buy/limit` | 限价买入 |
| POST | `/orders/rewards/claim` | 收获奖励 |
| GET | `/orders` | 查询订单 |
| DELETE | `/orders/cancel` | 取消订单 |
| DELETE | `/orders/cancel/all` | 取消所有订单 |

详细文档请查看 [ORDER_API.md](./ORDER_API.md)

## 示例代码

### 市价出售全部头寸

```python
from poly_boost.services.order_service import OrderService
from polymarket_apis.types.clob_types import OrderType

# 出售全部 (amount=None)
result = service.sell_position_market(
    token_id="123456789",
    amount=None,
    order_type=OrderType.FOK
)

print(f"订单ID: {result['order_id']}")
print(f"出售数量: {result['amount']}")
```

### 限价出售指定数量

```python
# 以 0.55 价格出售 10 个单位
result = service.sell_position_limit(
    token_id="123456789",
    price=0.55,
    amount=10.0,
    order_type=OrderType.GTC
)
```

### 收获奖励

```python
# 收获已解决市场的奖励
result = service.claim_rewards(
    condition_id="0xabc123...",
    amounts=[10.0, 5.0]  # [outcome1, outcome2]
)
```

更多示例请查看 `examples/order_example.py`

## 配置说明

### API 配置适配

Order Service 完全适配 `config.yaml` 中的配置:

```yaml
polymarket_api:
  proxy: "http://localhost:7891"    # HTTP 代理
  timeout: 30.0                      # 请求超时(秒)
  verify_ssl: true                   # SSL 验证
```

这些配置会自动应用到:
- `PolymarketClobClient` 的 HTTP 客户端
- `PolymarketWeb3Client` 的 Web3 连接

### 钱包配置

```yaml
user_wallets:
  - name: "MyWallet"
    address: "0x..."                 # EOA 地址
    proxy_address: "0x..."           # Polymarket 代理地址
    private_key_env: "MY_KEY"        # 私钥环境变量名
    signature_type: 2                # 签名类型
```

**签名类型说明**:
- `0`: EOA 钱包
- `1`: Polymarket 代理钱包
- `2`: 浏览器钱包代理 (推荐)

## 安全注意事项

⚠️ **重要提示**:

1. **私钥安全**: 永远不要在代码或配置文件中硬编码私钥
2. **环境变量**: 使用环境变量存储敏感信息
3. **测试环境**: 建议先在测试网测试
4. **小额测试**: 首次使用建议小额测试
5. **API 密钥**: 妥善保管 API 密钥和签名

## 故障排查

### 问题: 服务初始化失败

**错误信息**: `No user wallets configured`

**解决方案**:
```yaml
# 在 config.yaml 中添加:
user_wallets:
  - name: "MyWallet"
    # ... 其他配置
```

### 问题: 私钥未设置

**错误信息**: `Order service requires wallet configuration with private_key`

**解决方案**:
```bash
export MY_WALLET_PRIVATE_KEY="your_private_key"
```

### 问题: SSL 验证错误

**解决方案**:
```yaml
polymarket_api:
  verify_ssl: false  # 仅在必要时禁用
```

### 问题: 代理连接失败

**解决方案**:
```yaml
polymarket_api:
  proxy: null  # 或移除代理配置
```

## 测试

### 单元测试

```bash
pytest tests/test_order_service.py
```

### API 测试

使用 `rest/poly-boost-orders.http` 文件进行集成测试。

### 手动测试

运行示例脚本:

```bash
python examples/order_example.py
```

## 性能优化

1. **连接复用**: 使用 `httpx.Client` 连接池
2. **超时控制**: 可配置的请求超时
3. **异步支持**: `PolymarketClobClient` 支持异步操作

## 技术栈

- **FastAPI**: Web 框架
- **Pydantic**: 数据验证
- **httpx**: HTTP 客户端
- **web3.py**: 以太坊交互
- **polymarket-apis**: Polymarket SDK

## 相关文档

- [ORDER_API.md](./ORDER_API.md) - 完整 API 文档
- [config.example.yaml](../config/config.example.yaml) - 配置示例
- [order_example.py](../examples/order_example.py) - 代码示例

## 贡献

欢迎提交 Issue 和 Pull Request!

## 许可证

与主项目保持一致。
