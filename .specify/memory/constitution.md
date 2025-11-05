<!--
  Sync Impact Report:
  Version change: 0.0.0 → 1.0.0
  Modified principles: Initial creation - all new
  Added sections: All sections (initial constitution)
  Removed sections: None
  Templates requiring updates:
    ✅ .specify/templates/plan-template.md (reviewed for alignment)
    ✅ .specify/templates/spec-template.md (reviewed for alignment)
    ✅ .specify/templates/tasks-template.md (reviewed for alignment)
  Follow-up TODOs: None
-->

# Poly-Boost Constitution

## Core Principles

### I. Service-First Architecture (NON-NEGOTIABLE)

**所有业务逻辑必须首先在 `poly_boost/services/` 中实现。** Services MUST:
- 包含可复用的业务逻辑，供 CLI、API、Telegram Bot 共享使用
- 具有清晰的单一职责（如 `trading_service.py`、`wallet_service.py`、`order_service.py`）
- 独立可测试，不依赖于具体的接口实现
- 处理自己的错误情况和日志记录
- 提供类型化的接口（使用 Python type hints）

**现有核心服务**:
- `activity_service.py`: 活动监控和过滤
- `order_service.py`: 订单管理和执行
- `position_service.py`: 持仓管理
- `trading_service.py`: 交易策略和执行
- `wallet_service.py`: 钱包操作和余额管理

**强制要求**:
- 新功能开发时，首先考虑是否可以复用或扩展现有服务
- 如果需要新建服务，必须在设计文档中说明理由
- CLI、API、Bot 中不得包含业务逻辑，只能调用 services 层
- 禁止在 `core/` 目录中添加与 services 重复的业务逻辑

**Rationale**: 多个接口（CLI、FastAPI API、Telegram Bot）共享相同的业务逻辑。在 services 层集中管理逻辑可以防止重复代码，确保所有访问方式的一致性，提高可维护性。

### II. Multi-Interface Consistency

每个功能必须在所有适用的三个接口中可访问：
- **CLI** (`poly_boost/cli.py`): 命令行直接交互
- **REST API** (`poly_boost/api/`): 程序化访问和 Web 前端集成
- **Telegram Bot** (`poly_boost/bot/`): 移动端/聊天界面交互

接口层是薄层，负责：
- 参数解析和验证
- 调用 services 层方法
- 格式化响应（JSON、文本、Telegram 消息等）
- 接口特定的错误处理

接口层禁止包含业务逻辑。

**Rationale**: 用户应该获得一致的功能，无论通过何种方式与机器人交互。Services 层提供唯一的真实来源。

### III. Security-First Design (NON-NEGOTIABLE)

安全性在处理以下内容的所有代码中必须是首要考虑：
- **私钥管理**:
  - 严禁硬编码或记录私钥
  - 仅使用环境变量（通过 `.env` 文件）
  - 加载时验证 0x 前缀和 66 字符长度
  - 严禁在日志、错误消息或 API 响应中暴露私钥
- **API 密钥**: Telegram bot token 等密钥存储在环境变量中
- **输入验证**:
  - 验证所有用户输入（钱包地址、金额、token ID）
  - 使用白名单验证，而非黑名单
  - 对数值进行范围检查
- **外部 API 调用**:
  - 使用超时设置
  - 优雅处理失败
  - 不向用户暴露内部错误详情
- **代理支持**: 所有外部 API 调用（Polymarket API、Polygon RPC）必须支持可选的代理配置

**Rationale**: 复制交易机器人处理用户资金和私钥。安全漏洞可能导致资金完全损失。安全性无法后期添加。

### IV. Polymarket Client Integration

所有 Polymarket 区块链交互必须使用官方 `polymarket_apis` 客户端库（位于 `.venv/Lib/site-packages/polymarket_apis/`）。该库提供：
- `ClobClient`: CLOB（中央限价订单簿）客户端，用于交易操作
- `OrderBuilder`: 订单构建工具
- 区块链工具和类型化接口

禁止直接区块链调用或自定义客户端实现，除非官方客户端缺少所需功能（必须记录在案）。

**服务层集成**:
- `wallet_service.py` 封装钱包操作
- `order_service.py` 封装订单构建和执行
- `trading_service.py` 使用这些服务进行高级交易逻辑

**Rationale**: 官方客户端正确处理认证、签名、API 版本控制和错误处理。自定义实现存在安全漏洞和 API 兼容性问题的风险。

### V. Configuration Management

所有配置必须集中在 `config/config.yaml` 中，并通过 `poly_boost/core/config_loader.py` 加载。配置必须支持：
- 多个用户钱包及其独立策略
- 数据库连接（可选）
- API 端点和代理设置
- 监控参数（轮询间隔、批次大小）
- 日志配置

环境特定覆盖（dev/staging/prod）应使用环境变量或单独的配置文件，而非代码更改。

**配置验证**:
- 启动时验证所有必需配置项
- 提供清晰的错误消息指示缺失或无效的配置
- 支持配置热重载（适用时）

**Rationale**: 交易机器人行为必须可调整而无需修改代码。配置错误应在启动时捕获，而非交易期间。

### VI. Robust Error Handling and Observability

所有操作必须实现全面的错误处理：
- **日志记录**:
  - 使用结构化日志，具有适当的级别（DEBUG、INFO、WARNING、ERROR）
  - 包含上下文信息（钱包地址、市场 ID、金额）而不暴露密钥
  - 按日期将日志写入 `logs/` 目录
  - 适当显示到 stdout/stderr
- **重试逻辑**:
  - 网络操作必须使用指数退避重试
  - 记录重试尝试和失败
  - 设置最大重试次数以防止无限循环
- **交易统计**:
  - 跟踪成功/失败率
  - 过滤的活动
  - 执行时间
  - 余额变化
- **错误上下文**: 记录足够的上下文以调试问题，但不暴露密钥

**服务层职责**: 每个服务负责记录自己的操作和错误。

**Rationale**: 交易机器人无人值守运行。详细的日志对于调试问题、监控性能和审计交易至关重要。用户需要了解机器人的决策。

### VII. Test Coverage for Critical Paths

以下内容必须进行测试：
- **交易逻辑**:
  - 复制策略计算（scale 模式、allocate 模式）
  - 金额验证和限制
  - 过滤逻辑
- **订单执行**:
  - 交易过滤
  - 金额验证
  - 订单创建和提交
- **配置加载**:
  - 私钥验证
  - 策略解析
  - 环境变量加载
- **服务层**:
  - 所有公共服务方法
  - 边界条件
  - 错误处理路径

测试应为外部 API（Polymarket API、Polygon RPC）使用 mock，以实现快速、可靠的测试执行。

**测试组织**:
- `tests/unit/`: 单元测试（快速、隔离）
- `tests/integration/`: 集成测试（跨服务）
- `tests/contract/`: 合约测试（API 端点、服务合约）

**Rationale**: 交易错误可能导致财务损失。核心交易逻辑必须在部署前通过自动化测试验证。

### VIII. Documentation and Developer Experience

所有代码必须包含：
- **模块 Docstrings**: 描述目的和关键功能
- **函数 Docstrings**: 记录参数、返回值、异常和副作用
- **设计文档**: 主要功能必须在 `docs/design/` 中有设计文档，解释架构和决策
- **README 文件**: 面向用户的文档，包含设置、配置和故障排除
- **API 文档**: API 端点必须有 OpenAPI/Swagger 文档

代码应自文档化，使用清晰的命名。注释解释"为什么"，而非"是什么"。

**中英文文档**:
- 用户文档应提供中英文版本
- 代码注释使用英文
- 设计文档可使用中文或英文

**Rationale**: 复制交易很复杂。新开发人员（和未来的你）需要清晰的文档来理解、维护和安全扩展系统。

### IX. Service Layer Reuse and Extension

**修改现有代码时的优先级**:
1. **首先检查** `poly_boost/services/` 是否已有可复用的逻辑
2. **优先扩展**现有服务，而非创建新服务
3. **必须重构**将接口层（CLI/API/Bot）中的业务逻辑移至服务层
4. **禁止重复**在多个地方实现相同的业务逻辑

**服务扩展原则**:
- 保持向后兼容性（添加参数使用默认值）
- 使用类型提示确保接口清晰
- 更新相关测试
- 更新服务文档

**Rationale**: 随着项目增长，重复的业务逻辑会导致维护噩梦。服务层必须是唯一的业务逻辑来源，确保一致性和可维护性。

## Technology Constraints

### Language and Runtime

- **Python 3.13+**: 需要现代类型提示和性能改进
- **Type Hints**: 所有函数签名使用类型提示
- **Async/Await**: I/O 密集型任务（API 调用、数据库查询）优先使用异步操作

### Required Dependencies

- **polymarket_apis**: 官方 Polymarket 客户端库
- **py-clob-client**: CLOB 客户端（polymarket_apis 的一部分）
- **FastAPI**: REST API 框架
- **python-telegram-bot**: Telegram bot 框架
- **PostgreSQL Driver**: 可选数据持久化
- **python-dotenv**: 环境变量管理
- **pytest**: 测试框架

额外的依赖项必须有合理的理由，并在 requirements.txt 中记录版本约束。

### Project Structure

```
poly-boost/
├── poly_boost/              # 主包
│   ├── core/               # 核心逻辑（配置、监控、交易基础）
│   ├── services/           # 业务服务层（必须用于共享逻辑）
│   │   ├── activity_service.py
│   │   ├── order_service.py
│   │   ├── position_service.py
│   │   ├── trading_service.py
│   │   └── wallet_service.py
│   ├── api/                # FastAPI REST API（薄接口层）
│   ├── bot/                # Telegram bot（薄接口层）
│   └── cli.py              # CLI 接口（薄接口层）
├── config/                 # 配置文件
│   └── config.yaml         # 主配置
├── tests/                  # 测试文件（镜像源代码结构）
│   ├── unit/
│   ├── integration/
│   └── contract/
├── docs/                   # 文档
│   └── design/             # 设计文档
├── logs/                   # 日志文件（不提交）
├── .env                    # 环境变量（不提交）
└── scripts/                # 工具脚本
```

## Development Workflow

### Adding New Features

1. **Design First**: 如果功能非平凡，在 `docs/design/` 中记录功能
2. **Check Services**: 检查 `poly_boost/services/` 中是否有可复用的逻辑
3. **Service Layer**: 在适当的服务中实现核心逻辑，或创建新服务（需要说明理由）
4. **Interface Integration**: 添加到 CLI、API 和 Telegram bot（仅调用服务）
5. **Testing**: 为服务层和关键路径添加测试
6. **Documentation**: 更新 README 和相关文档

### Code Review Requirements

所有更改必须审查：
- **Security**: 无暴露的密钥，适当的输入验证
- **Architecture**:
  - 逻辑在服务层，而非接口层
  - 复用现有服务而非重复实现
  - 新服务有合理的理由
- **Error Handling**: 适当的日志记录和重试逻辑
- **Testing**: 覆盖关键路径
- **Documentation**: 更新代码注释和面向用户的文档

### Deployment

- **Configuration Validation**: 部署前测试配置加载
- **Dry Run**: 首先使用小金额在仅监控模式下测试
- **Monitoring**: 初始部署期间观察日志
- **Rollback Plan**: 保留先前版本以便快速回滚

## Governance

本 Constitution 取代所有其他实践，是项目架构和开发标准的最终权威。

### Amendment Process

1. 提出更改，包括理由和影响分析
2. 与团队/维护者审查更改
3. 更新相关文档（模板、README 文件）
4. 按照语义化版本控制递增版本

### Compliance

- 所有 pull request 必须验证符合 Constitution 原则
- 偏离必须明确说明理由并记录
- 复杂架构（例如，额外的抽象层）必须说明为什么简单方法不足
- 安全违规是立即拒绝的理由
- **服务层优先原则违规**（在接口层实现业务逻辑）必须在代码审查中指出并修正

### Version History

**Version**: 1.0.0 | **Ratified**: 2025-11-05 | **Last Amended**: 2025-11-05
