# Wallet Management Design

## 核心问题

在 Polymarket 中，有两种钱包类型：
1. **EOA 钱包**：直接使用用户的以太坊地址
2. **Proxy 钱包**：使用 Gnosis Safe 等代理合约

**关键挑战**：调用 Polymarket API 时，需要使用不同的地址：
- EOA 钱包 → 使用 EOA 地址
- Proxy 钱包 → 使用 Proxy 地址

## 解决方案

### 三层架构

```
┌─────────────────────────────────────────────────────────┐
│                     API Layer                           │
│  用户提供: wallet_identifier (可以是任何地址或名称)      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  WalletManager                          │
│  职责: 根据 identifier 查找钱包配置                      │
│  • 支持 EOA address 查找                                 │
│  • 支持 Proxy address 查找                               │
│  • 支持 Wallet name 查找                                 │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                    Wallet Object                        │
│  包含完整的钱包配置:                                      │
│  • name: 钱包名称                                        │
│  • eoa_address: EOA 地址                                 │
│  • proxy_address: Proxy 地址 (如果是 proxy 钱包)         │
│  • signature_type: 签名类型 (0=EOA, 2=Gnosis Safe)       │
│  • api_address: 调用 API 时使用的地址 (自动计算)          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                Service Layer                            │
│  使用: wallet.api_address 调用 Polymarket API           │
│  • PositionService.get_positions(wallet)                │
│  • OrderService.sell_position(...)                      │
│  • 无需关心钱包类型！                                     │
└─────────────────────────────────────────────────────────┘
```

## 核心设计

### 1. Wallet 抽象类

```python
class Wallet(ABC):
    @property
    @abstractmethod
    def api_address(self) -> str:
        """调用 API 时使用的地址"""
        pass

    @abstractmethod
    def matches_identifier(self, identifier: str) -> bool:
        """检查是否匹配给定的标识符"""
        pass
```

### 2. EOAWallet 实现

```python
class EOAWallet(Wallet):
    @property
    def api_address(self) -> str:
        return self.eoa_address  # EOA 直接使用原地址

    def matches_identifier(self, identifier: str) -> bool:
        identifier_lower = identifier.lower()
        return (
            self.eoa_address.lower() == identifier_lower or
            self.name.lower() == identifier_lower
        )
```

### 3. ProxyWallet 实现

```python
class ProxyWallet(Wallet):
    def __init__(self, name, eoa_address, proxy_address, ...):
        self.eoa_address = eoa_address
        self.proxy_address = proxy_address

    @property
    def api_address(self) -> str:
        return self.proxy_address  # Proxy 使用代理地址

    def matches_identifier(self, identifier: str) -> bool:
        identifier_lower = identifier.lower()
        return (
            self.eoa_address.lower() == identifier_lower or
            self.proxy_address.lower() == identifier_lower or
            self.name.lower() == identifier_lower
        )
```

## 使用流程

### 配置文件 (config.yaml)

```yaml
user_wallets:
  - name: "Alice"
    address: "0x1111..."  # EOA 地址
    signature_type: 0
    private_key_env: "ALICE_KEY"

  - name: "Bob Safe"
    address: "0x2222..."  # EOA 地址
    proxy_address: "0x3333..."  # Gnosis Safe 地址
    signature_type: 2
    private_key_env: "BOB_KEY"
```

### API 请求处理

```python
# 用户发起请求
GET /positions/0x2222...  # 用户提供 Bob 的 EOA 地址

# 1. API Layer
@router.get("/positions/{wallet_identifier}")
def get_positions(wallet_identifier: str):
    # 2. 从 WalletManager 查找钱包
    wallet_manager = get_wallet_manager()
    wallet = wallet_manager.get_or_raise(wallet_identifier)
    # ✓ 找到 Bob Safe (匹配 EOA address)

    # 3. 获取 PositionService
    position_service = get_position_service()

    # 4. 调用服务（服务自动使用正确的地址）
    positions = position_service.get_positions(wallet)
    # ✓ 内部使用 wallet.api_address = "0x3333..." (Proxy 地址)

    return positions
```

### 关键场景

#### 场景 1: 用户提供 Proxy 钱包的 EOA 地址

```python
# 用户输入: 0x2222... (Bob 的 EOA)
wallet = manager.get("0x2222...")
# → 找到 Bob Safe 钱包
# → wallet.api_address = "0x3333..." (Proxy 地址)
# → API 调用使用 "0x3333..."
```

#### 场景 2: 用户提供 Proxy 钱包的 Proxy 地址

```python
# 用户输入: 0x3333... (Bob 的 Proxy)
wallet = manager.get("0x3333...")
# → 找到 Bob Safe 钱包
# → wallet.api_address = "0x3333..." (Proxy 地址)
# → API 调用使用 "0x3333..."
```

#### 场景 3: 用户提供钱包名称

```python
# 用户输入: "Bob Safe"
wallet = manager.get("Bob Safe")
# → 找到 Bob Safe 钱包
# → wallet.api_address = "0x3333..." (Proxy 地址)
# → API 调用使用 "0x3333..."
```

## 核心优势

### 1. 统一抽象

**之前**：
```python
# 服务需要判断钱包类型
if signature_type == 0:
    address = eoa_address
else:
    address = proxy_address
balance = get_balance(address)
```

**现在**：
```python
# 服务直接使用 wallet.api_address
balance = get_balance(wallet.api_address)
```

### 2. 灵活查找

用户可以使用多种方式标识钱包：
- ✓ EOA 地址
- ✓ Proxy 地址
- ✓ 钱包名称
- ✓ 大小写不敏感

### 3. 类型安全

```python
# Wallet 是类型化对象，不是字典
def get_positions(wallet: Wallet) -> List[Position]:
    # IDE 自动补全，类型检查
    address = wallet.api_address
    name = wallet.name
    sig_type = wallet.signature_type
```

### 4. 易于扩展

添加新的钱包类型只需：
1. 继承 `Wallet` 基类
2. 实现 `api_address` 属性
3. 实现 `matches_identifier` 方法

### 5. 测试友好

```python
# 可以轻松创建 mock 钱包
mock_wallet = ProxyWallet(
    name="Test",
    eoa_address="0xAAA...",
    proxy_address="0xBBB...",
    ...
)
service = OrderService(mock_wallet, ...)
```

## 实现清单

- [x] `poly_boost/core/wallet.py` - Wallet 抽象层
- [x] `poly_boost/core/wallet_manager.py` - 钱包注册表
- [x] `poly_boost/core/client_factory.py` - 客户端工厂
- [x] `poly_boost/services/order_service.py` - 订单服务重构
- [x] `poly_boost/services/position_service.py` - 持仓服务重构
- [x] `poly_boost/services/wallet_service.py` - 钱包服务重构
- [x] `poly_boost/api/dependencies.py` - 依赖注入重构
- [x] `poly_boost/api/routes/orders.py` - API 路由更新
- [x] 综合测试验证

## 测试

运行测试验证设计：

```bash
# 基础功能测试
python test_wallet_refactor.py

# 完整流程测试
python test_correct_flow.py
```

## 总结

这个设计解决了多钱包类型适配的核心问题：

1. **用户友好**：可以用任何地址标识钱包
2. **类型安全**：使用 Wallet 对象而不是字典
3. **自动适配**：`wallet.api_address` 自动返回正确地址
4. **职责分离**：
   - WalletManager：查找钱包
   - Wallet：封装配置
   - Service：使用配置，不关心类型
