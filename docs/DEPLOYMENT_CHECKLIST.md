# Telegram Bot 钱包管理功能 - 部署检查清单

**功能**: Telegram Bot 钱包管理与交易
**分支**: `001-telegram-wallet-features`
**生成日期**: 2025-11-05

## 🎯 实施概览

本次实施完成了 Telegram Bot 的完整钱包管理和交易功能，包括：
- ✅ 钱包初始化（生成/导入）
- ✅ 钱包信息查看
- ✅ 持仓管理（查看、赎回、卖出）
- ✅ 订单管理（查看、取消）
- ✅ 活动历史查看
- ✅ 分页支持
- ✅ 完整的数据库集成

---

## 📋 部署前检查清单

### 1. 环境配置

- [ ] **检查 `.env` 文件**
  ```bash
  # 必须设置的环境变量
  TELEGRAM_BOT_TOKEN=your_actual_bot_token_here
  DATABASE_URL=postgresql://user:password@host:port/database
  # 或使用 SQLite (开发环境)
  # DATABASE_URL=sqlite:///polyboost_bot.db
  ```

- [ ] **验证 `config/config.yaml`**
  ```yaml
  telegram_bot:
    pagination:
      page_size: 10  # 确认分页大小配置
  ```

- [ ] **检查数据库连接**
  ```bash
  # PostgreSQL
  psql -U user -d database -c "SELECT 1"

  # SQLite (开发环境)
  # 自动创建，无需预先检查
  ```

### 2. 数据库初始化

- [ ] **运行数据库迁移脚本**
  ```bash
  python -m poly_boost.scripts.init_db
  ```

- [ ] **验证表创建**
  ```bash
  # PostgreSQL
  psql -U user -d database -c "\d user_wallets"

  # SQLite
  sqlite3 polyboost_bot.db ".schema user_wallets"
  ```

- [ ] **确认表结构**
  - telegram_user_id (BIGINT, PRIMARY KEY)
  - wallet_address (VARCHAR(42), UNIQUE)
  - private_key (VARCHAR(66))
  - wallet_name (VARCHAR(100), NULLABLE)
  - signature_type (INTEGER, DEFAULT 0)
  - created_at (TIMESTAMP)
  - updated_at (TIMESTAMP)

### 3. Telegram Bot 配置

- [ ] **获取 Bot Token**
  - 从 @BotFather 获取 token
  - 格式: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

- [ ] **配置 Bot 命令列表**
  发送给 @BotFather:
  ```
  /setcommands
  选择你的 bot
  粘贴命令列表：

  start - 初始化钱包或查看钱包信息
  wallet - 查看详细钱包信息
  fund - 获取充值地址和说明
  profile - 查看 Polymarket 公开资料
  positions - 查看和管理持仓
  orders - 查看和取消订单
  activities - 查看交易历史
  help - 显示帮助信息
  ```

### 4. 依赖检查

- [ ] **验证 Python 版本**
  ```bash
  python --version  # 应该是 3.13+
  ```

- [ ] **安装依赖**
  ```bash
  pip install -e .
  ```

- [ ] **验证关键依赖**
  ```bash
  python -c "import telegram; print(telegram.__version__)"  # >= 22.5
  python -c "import peewee; print(peewee.__version__)"      # >= 3.17.0
  python -c "import web3; print(web3.__version__)"          # >= 7.0.0
  python -c "import polymarket_apis; print(polymarket_apis.__version__)"  # >= 0.3.5
  ```

### 5. 代码验证

- [ ] **语法检查**
  ```bash
  python -m py_compile poly_boost/bot/main.py
  python -m py_compile poly_boost/models/user_wallet.py
  python -m py_compile poly_boost/services/user_wallet_service.py
  ```

- [ ] **导入测试**
  ```bash
  python -c "from poly_boost.models.user_wallet import UserWallet; print('✓ UserWallet')"
  python -c "from poly_boost.services.user_wallet_service import UserWalletService; print('✓ UserWalletService')"
  python -c "from poly_boost.bot.utils.pagination import PaginationHelper; print('✓ PaginationHelper')"
  python -c "from poly_boost.bot.conversations.wallet_init import wallet_init_conversation; print('✓ wallet_init_conversation')"
  ```

### 6. 安全检查

- [ ] **私钥安全**
  - ✅ 私钥消息立即删除 (FR-004)
  - ✅ 私钥不出现在日志中
  - ✅ 私钥不出现在错误消息中
  - ⚠️ 数据库访问控制已配置（生产环境必须）

- [ ] **数据库安全**
  - [ ] 数据库用户权限最小化
  - [ ] 数据库文件权限设置 (chmod 600)
  - [ ] PostgreSQL SSL 连接启用
  - [ ] 定期备份策略已配置

- [ ] **环境变量安全**
  - [ ] `.env` 文件已加入 `.gitignore`
  - [ ] 生产环境使用独立的 `.env` 文件
  - [ ] Bot token 定期轮换

---

## 🚀 部署步骤

### 开发环境部署

1. **设置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 设置 TELEGRAM_BOT_TOKEN 和 DATABASE_URL
   ```

2. **初始化数据库**
   ```bash
   python -m poly_boost.scripts.init_db
   ```

3. **启动 Bot**
   ```bash
   python -m poly_boost.bot.main
   ```

4. **测试基本功能**
   - 发送 `/start` 初始化钱包
   - 发送 `/wallet` 查看钱包信息
   - 发送 `/positions` 查看持仓

### 生产环境部署 (systemd)

1. **创建 systemd service 文件**
   ```bash
   sudo nano /etc/systemd/system/polyboost-bot.service
   ```

   内容：
   ```ini
   [Unit]
   Description=Polymarket Copy Trading Bot
   After=network.target postgresql.service

   [Service]
   Type=simple
   User=polyboost
   WorkingDirectory=/opt/polyboost
   EnvironmentFile=/opt/polyboost/.env
   ExecStart=/opt/polyboost/.venv/bin/python -m poly_boost.bot.main
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

2. **启用和启动服务**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable polyboost-bot
   sudo systemctl start polyboost-bot
   ```

3. **检查状态**
   ```bash
   sudo systemctl status polyboost-bot
   sudo journalctl -u polyboost-bot -f
   ```

### Docker 部署

1. **构建镜像**
   ```bash
   docker build -t polyboost-bot .
   ```

2. **运行容器**
   ```bash
   docker run -d \
     --name polyboost-bot \
     --env-file .env \
     -v $(pwd)/polyboost_bot.db:/app/polyboost_bot.db \
     --restart unless-stopped \
     polyboost-bot
   ```

3. **查看日志**
   ```bash
   docker logs -f polyboost-bot
   ```

---

## ✅ 部署后验证

### 1. 功能测试

- [ ] **钱包初始化测试**
  - 发送 `/start` (无钱包)
  - 点击 "生成新钱包"
  - 验证收到钱包地址和私钥
  - 再次发送 `/start` 验证显示现有钱包

- [ ] **钱包导入测试**
  - 使用新账户发送 `/start`
  - 点击 "使用现有钱包"
  - 输入有效私钥
  - 验证私钥消息被删除
  - 验证钱包成功导入

- [ ] **钱包信息测试**
  - 发送 `/wallet` 查看详情
  - 发送 `/fund` 查看充值信息和二维码
  - 发送 `/profile` 获取 Polymarket 链接

- [ ] **持仓管理测试**
  - 发送 `/positions` 查看持仓列表
  - 测试分页（如果超过10个持仓）
  - 选择一个持仓查看详情
  - 验证赎回/卖出按钮正确显示

- [ ] **订单管理测试**
  - 发送 `/orders` 查看活跃订单
  - 测试分页
  - 选择订单并取消
  - 验证空订单列表正确显示

- [ ] **活动历史测试**
  - 发送 `/activities` 查看交易历史
  - 测试分页
  - 验证活动类型正确显示

### 2. 边界情况测试

- [ ] **空列表处理**
  - 无持仓时发送 `/positions`
  - 无订单时发送 `/orders`
  - 无活动时发送 `/activities`
  - 验证分页控件隐藏 (FR-007)

- [ ] **错误处理**
  - 网络断开时发送命令
  - 验证显示清晰的错误消息 (FR-017)
  - 验证不显示过时数据

- [ ] **并发测试**
  - 多个用户同时初始化钱包
  - 验证无冲突
  - 验证每个用户的数据隔离

### 3. 性能测试

- [ ] **响应时间**
  - Bot 命令响应 < 3秒
  - 分页渲染 < 1秒
  - 钱包初始化 < 1分钟

- [ ] **数据库性能**
  - 查询钱包 < 10ms
  - 创建钱包 < 50ms

### 4. 安全验证

- [ ] **私钥安全**
  - 验证私钥消息被删除
  - 检查日志无私钥
  - 检查数据库私钥字段格式正确

- [ ] **访问控制**
  - 用户只能访问自己的钱包
  - 无法查看其他用户的私钥

---

## 🐛 常见问题排查

### Bot 不响应

1. **检查 Bot token**
   ```bash
   echo $TELEGRAM_BOT_TOKEN
   # 格式: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

2. **检查 Bot 进程**
   ```bash
   ps aux | grep "poly_boost.bot.main"
   ```

3. **检查日志**
   ```bash
   sudo journalctl -u polyboost-bot -n 50
   ```

### 数据库连接失败

1. **验证连接字符串**
   ```bash
   echo $DATABASE_URL
   ```

2. **测试连接**
   ```bash
   # PostgreSQL
   psql $DATABASE_URL -c "SELECT 1"

   # SQLite
   sqlite3 polyboost_bot.db "SELECT 1"
   ```

3. **检查权限**
   ```bash
   ls -la polyboost_bot.db  # SQLite
   ```

### 私钥验证失败

1. **检查私钥格式**
   - 必须以 `0x` 开头
   - 总长度 66 字符
   - 只包含十六进制字符

2. **使用 Python 测试**
   ```python
   from eth_account import Account

   # 测试私钥
   private_key = "0x..."
   account = Account.from_key(private_key)
   print(f"Address: {account.address}")
   ```

### API 调用失败

1. **检查网络连接**
   ```bash
   curl https://clob.polymarket.com/health
   curl https://data-api.polymarket.com/health
   ```

2. **检查代理配置**
   ```yaml
   # config/config.yaml
   polymarket_api:
     proxy: "http://localhost:7891"  # 如果需要
   ```

---

## 📊 监控指标

### 关键指标

- **用户指标**
  - 总用户数: `SELECT COUNT(*) FROM user_wallets`
  - 今日新增用户: `SELECT COUNT(*) FROM user_wallets WHERE created_at::date = CURRENT_DATE`
  - 活跃用户数（7天）

- **性能指标**
  - Bot 响应时间
  - 数据库查询时间
  - API 调用成功率

- **错误指标**
  - 错误率（按命令）
  - 网络错误频率
  - 数据库连接失败次数

### 日志监控

```bash
# 监控错误
sudo journalctl -u polyboost-bot | grep ERROR

# 监控警告
sudo journalctl -u polyboost-bot | grep WARNING

# 监控用户活动
sudo journalctl -u polyboost-bot | grep "Wallet initialized"
```

---

## 📝 维护任务

### 每日任务

- [ ] 检查 Bot 运行状态
- [ ] 检查错误日志
- [ ] 验证数据库备份

### 每周任务

- [ ] 查看性能指标
- [ ] 清理过期日志
- [ ] 检查磁盘空间

### 每月任务

- [ ] 更新依赖包
- [ ] 审查安全配置
- [ ] 测试数据库恢复

---

## 🔄 回滚计划

如果部署出现问题：

1. **停止服务**
   ```bash
   sudo systemctl stop polyboost-bot
   ```

2. **回滚代码**
   ```bash
   git checkout main
   ```

3. **回滚数据库（如果需要）**
   ```bash
   # 从备份恢复
   pg_restore -d database backup.dump
   ```

4. **重启服务**
   ```bash
   sudo systemctl start polyboost-bot
   ```

---

## 📞 支持联系方式

- **技术问题**: 提交 GitHub Issue
- **紧急问题**: 联系 @team-leads
- **安全问题**: 联系 @security-team

---

**部署检查清单最后更新**: 2025-11-05
**版本**: 1.0.0
