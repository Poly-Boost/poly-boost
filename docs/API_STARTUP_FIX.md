# API 启动连接错误修复

## 问题描述

API 服务启动时报错:

```
httpx.ConnectError: [WinError 10054] An existing connection was forcibly closed by the remote host
```

错误发生在 `PolymarketClobClient` 初始化时。

### 根本原因

1. **时序问题**: `PolymarketClobClient` 在 `__init__` 方法中会**立即调用** API 来创建/获取 credentials
2. **代理配置滞后**: 在初始化时，它使用的是默认的 httpx client（没有代理配置）
3. **网络访问受限**: 如果需要通过代理访问 Polymarket API，初始化就会失败

### 代码分析

`PolymarketClobClient.__init__` 的执行流程:

```python
def __init__(self, private_key, proxy_address, creds=None, ...):
    self.client = httpx.Client(http2=True, timeout=30.0)  # 第102行: 创建默认client
    self.async_client = httpx.AsyncClient(...)             # 第103行
    self.signer = Signer(...)                              # 第105行
    self.builder = OrderBuilder(...)                       # 第106行
    self.creds = creds if creds else self.create_or_derive_api_creds()  # 第111行: 立即调用API!
```

**问题**: 第111行会立即调用 API，但此时使用的是第102行创建的默认 client（没有代理）。

**旧代码的错误做法**:
```python
# 错误: 先创建client，再替换httpx client
_clob_client = PolymarketClobClient(...)  # ❌ 这里就会失败，因为API调用时没有代理
_clob_client.client = httpx.Client(**client_kwargs)  # 太晚了
```

## 解决方案

### 核心思路

1. **提前获取 credentials**: 在初始化 `PolymarketClobClient` **之前**，先用配置好的 httpx client 获取 API credentials
2. **传入 credentials**: 将获取的 credentials 传给 `PolymarketClobClient` 的 `creds` 参数
3. **跳过 API 调用**: 这样 `__init__` 中的第111行就会使用传入的 credentials，不会调用 API

### 实现步骤

#### 1. 创建临时客户端获取 credentials

```python
# 创建配置好代理的临时客户端
temp_client = httpx.Client(**client_kwargs)  # 包含 proxy、timeout、verify_ssl

# 手动创建 Signer 和 headers
signer = Signer(private_key=private_key, chain_id=137)
headers = create_level_1_headers(signer, None)

try:
    # 尝试创建新的 API key
    response = temp_client.post(
        "https://clob.polymarket.com/auth/api-key",
        headers=headers
    )
    response.raise_for_status()
    creds = ApiCreds(**response.json())
except Exception:
    # 如果创建失败，尝试获取现有的 key
    response = temp_client.get(
        "https://clob.polymarket.com/auth/derive-api-key",
        headers=headers
    )
    response.raise_for_status()
    creds = ApiCreds(**response.json())

temp_client.close()
```

#### 2. 使用 credentials 初始化 client

```python
# 传入 credentials，跳过 __init__ 中的 API 调用
_clob_client = PolymarketClobClient(
    private_key=private_key,
    proxy_address=proxy_address,
    signature_type=signature_type,
    chain_id=137,
    creds=creds  # ✅ 关键: 传入 credentials
)

# 替换默认的 httpx clients
_clob_client.client = httpx.Client(**client_kwargs)
_clob_client.async_client = httpx.AsyncClient(**client_kwargs)
```

### 完整代码

```python
# Prepare httpx client kwargs
client_kwargs = {
    "http2": True,
    "timeout": timeout,
    "verify": verify_ssl
}
if proxy:
    client_kwargs["proxy"] = proxy

# Create temporary client to obtain credentials
logger.info("Creating temporary HTTP client to obtain Polymarket API credentials...")
temp_client = httpx.Client(**client_kwargs)

from polymarket_apis.utilities.signing.signer import Signer
from polymarket_apis.utilities.headers import create_level_1_headers
from polymarket_apis.types.clob_types import ApiCreds

# Get or create API credentials
signer = Signer(private_key=private_key, chain_id=137)
headers = create_level_1_headers(signer, None)

try:
    logger.info("Attempting to create new Polymarket API key...")
    response = temp_client.post(
        "https://clob.polymarket.com/auth/api-key",
        headers=headers
    )
    response.raise_for_status()
    creds = ApiCreds(**response.json())
    logger.info("Successfully created new API credentials")
except Exception as e:
    logger.info(f"API key creation failed ({e}), attempting to derive existing key...")
    try:
        response = temp_client.get(
            "https://clob.polymarket.com/auth/derive-api-key",
            headers=headers
        )
        response.raise_for_status()
        creds = ApiCreds(**response.json())
        logger.info("Successfully derived existing API credentials")
    except Exception as derive_error:
        logger.error(f"Failed to obtain API credentials: {derive_error}")
        temp_client.close()
        raise RuntimeError(
            "Failed to obtain Polymarket API credentials. "
            "Please check your network connection and proxy settings."
        ) from derive_error

temp_client.close()
logger.info("Temporary client closed")

# Initialize CLOB client with credentials
logger.info("Initializing PolymarketClobClient with obtained credentials...")
_clob_client = PolymarketClobClient(
    private_key=private_key,
    proxy_address=proxy_address,
    signature_type=signature_type,
    chain_id=137,
    creds=creds  # Pass credentials to skip API call
)
# Replace default clients
_clob_client.client = httpx.Client(**client_kwargs)
_clob_client.async_client = httpx.AsyncClient(**client_kwargs)
logger.info("PolymarketClobClient initialized successfully")
```

## 改进点总结

### ✅ 修复的问题

1. **连接错误**: 使用代理配置的临时客户端获取 credentials
2. **时序问题**: 在初始化前获取 credentials，避免 `__init__` 中的 API 调用
3. **错误处理**: 添加完善的日志和错误处理

### ✅ 新增功能

1. **详细日志**: 记录每个步骤的执行情况
2. **双重尝试**: 先尝试创建新 key，失败则尝试获取现有 key
3. **友好错误**: 提供清晰的错误消息和解决建议

### ✅ 代码质量

| 指标 | 改进 |
|------|------|
| 错误处理 | ✅ 完善 |
| 日志记录 | ✅ 详细 |
| 代理支持 | ✅ 正确配置 |
| 可维护性 | ✅ 提高 |

## 执行流程

### 正常流程

```
1. 加载配置 (proxy, timeout, verify_ssl)
   ↓
2. 准备 client_kwargs
   ↓
3. 创建临时 httpx.Client (带代理)
   ↓
4. 调用 /auth/api-key 创建 credentials
   ↓
5. 关闭临时 client
   ↓
6. 使用 credentials 初始化 PolymarketClobClient
   ↓
7. 替换为配置好的 httpx clients
   ↓
8. ✅ 启动成功
```

### 降级流程 (创建失败时)

```
4. 调用 /auth/api-key 创建失败
   ↓
5. 降级: 调用 /auth/derive-api-key 获取现有 key
   ↓
6. 关闭临时 client
   ↓
7. 使用 credentials 初始化 PolymarketClobClient
   ↓
8. ✅ 启动成功
```

## 日志示例

成功启动时的日志:

```
INFO - Creating temporary HTTP client to obtain Polymarket API credentials...
INFO - Attempting to create new Polymarket API key...
INFO - Successfully created new API credentials
INFO - Temporary client closed
INFO - Initializing PolymarketClobClient with obtained credentials...
INFO - PolymarketClobClient initialized successfully
```

降级时的日志:

```
INFO - Creating temporary HTTP client to obtain Polymarket API credentials...
INFO - Attempting to create new Polymarket API key...
INFO - API key creation failed (...), attempting to derive existing key...
INFO - Successfully derived existing API credentials
INFO - Temporary client closed
INFO - Initializing PolymarketClobClient with obtained credentials...
INFO - PolymarketClobClient initialized successfully
```

## 配置要求

确保 `config.yaml` 配置正确:

```yaml
polymarket_api:
  proxy: "http://localhost:7891"  # ✅ 必须: 如果需要代理
  timeout: 30.0                    # ✅ 建议: 适当的超时时间
  verify_ssl: true                 # ✅ 根据需要

user_wallets:
  - name: "MyWallet"
    address: "0x..."
    proxy_address: "0x..."
    private_key_env: "MY_WALLET_PRIVATE_KEY"
    signature_type: 2
```

环境变量:

```bash
export MY_WALLET_PRIVATE_KEY="your_private_key"
```

## 故障排查

### 问题: 仍然连接失败

**检查清单**:
1. ✅ 代理是否正确配置？
2. ✅ 代理是否正在运行？
3. ✅ 环境变量是否设置？
4. ✅ 网络连接是否正常？

### 问题: 获取 credentials 失败

**可能原因**:
- 私钥不正确
- proxy_address 不正确
- 代理无法访问 Polymarket API

**解决方案**:
```bash
# 测试代理连接
curl -x http://localhost:7891 https://clob.polymarket.com

# 检查配置
cat config/config.yaml

# 检查环境变量
echo $MY_WALLET_PRIVATE_KEY
```

## 相关文件

- `poly_boost/api/dependencies.py` - 主修复文件
- `config/config.example.yaml` - 配置示例
- `.env` - 环境变量文件

## 技术细节

### API 端点

1. **创建 API Key**: `POST /auth/api-key`
   - 需要 Level 1 签名头
   - 返回新的 API credentials

2. **获取现有 Key**: `GET /auth/derive-api-key`
   - 需要 Level 1 签名头
   - 返回现有的 API credentials

### ApiCreds 结构

```python
class ApiCreds:
    api_key: str
    api_secret: str
    api_passphrase: str
```

## 更新日志

**2025-10-19**:
- ✅ 修复 API 启动时的连接错误
- ✅ 实现提前获取 credentials 的方案
- ✅ 添加详细的日志记录
- ✅ 添加完善的错误处理
- ✅ 支持创建/获取 credentials 的降级逻辑
