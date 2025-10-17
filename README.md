# Polymarket Copy Trading Bot

Automatically follow professional traders' strategies on Polymarket with intelligent copy trading.

[中文文档](README_CN.md)

## 🌟 Core Features

- ✅ **Real-time Monitoring**: Monitor all trading activities of target wallets
- ✅ **Auto Copy Trading**: Automatically execute copy trades based on configuration
- ✅ **Flexible Strategies**: Support Scale and Allocate modes
- ✅ **Risk Control**: Minimum amount filtering, error retry, trading statistics
- ✅ **Multiple Order Types**: Support market orders and limit orders
- ✅ **Event-Driven**: Low-latency architecture based on message queue
- ✅ **Multiple Interfaces**: CLI, FastAPI REST API, and Telegram Bot

## 📋 System Requirements

- Python 3.13+
- PostgreSQL (optional, for data persistence)
- Network proxy (optional, for accessing Polymarket API)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

### 2. Configure the Bot

```bash
# Copy configuration template
cp config.example.yaml config/config.yaml

# Edit configuration file
vim config/config.yaml
```

**Key Configuration**:

```yaml
# Set target wallet to monitor
monitoring:
  wallets:
    - "0x55be7aa03ecfbe37aa5460db791205f7ac9ddca3"

# Configure your wallet and strategy
user_wallets:
  - name: "MyWallet"
    address: "0x..."
    private_key_env: "MY_WALLET_PRIVATE_KEY"

    copy_strategy:
      min_trigger_amount: 10      # Minimum trigger amount
      order_type: "market"        # Order type: market/limit
      copy_mode: "scale"          # Copy mode: scale/allocate
      scale_percentage: 10.0      # Copy with 10% of target amount
```

### 3. Set Private Key (Secure Method)

**Recommended: Using .env file**

```bash
# Copy .env example file
cp .env.example .env

# Edit .env file and fill in actual private key
vim .env
```

`.env` file example:
```bash
# Replace with your actual private key (must start with 0x)
MY_WALLET_PRIVATE_KEY=0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
```

**Alternative: Set environment variables directly**

```bash
# Linux/Mac
export MY_WALLET_PRIVATE_KEY="0x..."

# Windows CMD
set MY_WALLET_PRIVATE_KEY=0x...

# Windows PowerShell
$env:MY_WALLET_PRIVATE_KEY="0x..."
```

⚠️ **Security Tips**:
- Never write private keys directly in `config.yaml`!
- `.env` file is in `.gitignore` and won't be committed to version control
- Private key must start with `0x` and be 66 characters long

### 4. Run the Bot

```bash
# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Run CLI
python run_cli.py

# Or run API server
python run_api.py

# Or run Telegram bot
python run_bot.py
```

On startup, you'll see:
```
✓ Loaded environment variables from: E:\...\polymarket-copy-trading-bot\.env
Loading configuration file...
CopyTrader 'MyWallet' initialized | Address: 0x... | Mode: scale
Monitoring active, press Ctrl+C to exit...
```

## 📊 Running Modes

### Monitor-Only Mode (Default)

Don't configure `user_wallets`, program will only monitor and print logs:

```yaml
# Don't configure or comment out user_wallets
# user_wallets: []
```

### Copy Trading Mode

Configure at least one `user_wallet`, program will automatically execute copy trades:

```yaml
user_wallets:
  - name: "MyWallet"
    address: "0x..."
    # ... strategy configuration
```

## 🎯 Copy Strategy Explained

### Scale Mode (Proportional Scaling)

Copy by fixed percentage of target trade amount:

```yaml
copy_mode: "scale"
scale_percentage: 10.0  # If target trades 100 USDC, we copy with 10 USDC
```

**Use Cases**:
- Fixed capital size
- Want fixed multiplier for risk exposure

### Allocate Mode (Proportional Allocation)

Copy by target wallet's asset allocation ratio (not yet fully implemented):

```yaml
copy_mode: "allocate"
# If target uses 5% of total assets for trade, we also use 5% of our total assets
```

**Use Cases**:
- Different capital size from target
- Want to maintain same asset allocation ratio

## 🛡️ Risk Control

### Filtering Mechanism

```yaml
copy_strategy:
  # Minimum trigger amount, avoid following small test trades
  min_trigger_amount: 10

  # Maximum trade amount, limit upper bound per copy trade
  max_trade_amount: 100
```

### Order Types

**Market Order** (recommended for beginners):
- Pros: Fast execution
- Cons: Possible slippage

```yaml
order_type: "market"
```

**Limit Order** (recommended for advanced users):
- Pros: Price guarantee, avoid slippage
- Cons: May not fill

```yaml
order_type: "limit"
limit_order_duration: 7200  # 2 hours validity
```

## 📁 Project Structure

```
polymarket-copy-trading-bot/
├── poly_boost/                 # Main source code package
│   ├── core/                  # Core business logic
│   │   ├── config_loader.py  # Configuration loader
│   │   ├── wallet_monitor.py # Wallet monitor
│   │   ├── copy_trader.py    # Copy trading core class
│   │   ├── order_executor.py # Order execution
│   │   └── ...
│   ├── services/              # Service layer
│   │   ├── position_service.py
│   │   ├── trading_service.py
│   │   └── wallet_service.py
│   ├── api/                   # FastAPI REST API
│   │   ├── main.py
│   │   └── routes/
│   ├── bot/                   # Telegram bot
│   │   ├── main.py
│   │   └── handlers/
│   └── cli.py                 # CLI interface
├── config/                    # Configuration files
│   └── config.yaml
├── tests/                     # Test files
├── scripts/                   # Utility scripts
├── run_cli.py                 # CLI launcher
├── run_api.py                 # API launcher
├── run_bot.py                 # Bot launcher
├── config.example.yaml        # Configuration example
├── README.md                  # This file (English)
└── README_CN.md               # Chinese documentation
```

## 🧪 Testing

```bash
# Run unit tests
python tests/test_copy_trader.py

# Run message queue tests
python tests/test_message_queue.py

# Verify refactor
python scripts/verify_refactor.py
```

## 📝 Logs

Log files are in `logs/` directory, split by date:

```bash
# View logs in real-time
tail -f logs/$(date +%Y-%m-%d).log  # Linux/Mac
type logs\YYYY-MM-DD.log            # Windows
```

Logs include:
- Monitoring status
- Trading activities
- Copy trade decisions
- Order execution results
- Errors and retry information

## 🔧 Configuration Reference

### Complete Configuration Example

```yaml
# Database configuration (optional)
database:
  url: "postgresql://user:pass@localhost:5432/polymarket_bot"

# Logging configuration
logging:
  log_dir: "logs"
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR

# API configuration
polymarket_api:
  proxy: "http://localhost:7891"  # Optional
  verify_ssl: false
  timeout: 30.0

# Polygon RPC configuration
polygon_rpc:
  url: "https://polygon-rpc.com"
  proxy: "http://localhost:7891"  # Optional
  verify_ssl: false

# Monitoring configuration
monitoring:
  wallets:
    - "0x..."  # Target wallet address
  poll_interval_seconds: 5
  batch_size: 100

# Message queue configuration
queue:
  type: "memory"
  memory:
    max_workers: 10

# Copy trading configuration
user_wallets:
  - name: "MyWallet"
    address: "0x..."
    proxy_address: "0x..."  # Optional, for signature_type=2
    signature_type: 0       # 0=EOA mode, 2=Proxy mode
    private_key_env: "MY_WALLET_PRIVATE_KEY"

    copy_strategy:
      min_trigger_amount: 10
      min_trade_amount: 0
      max_trade_amount: 100
      order_type: "market"
      limit_order_duration: 7200
      copy_mode: "scale"
      scale_percentage: 10.0
```

## ⚠️ Security Recommendations

1. **Private Key Management**
   - Use environment variables for private keys
   - Use key management services in production (AWS Secrets Manager, HashiCorp Vault)
   - Rotate private keys regularly

2. **Fund Security**
   - Use dedicated trading wallets
   - Start with small test amounts
   - Check account balance regularly

3. **Risk Control**
   - Set reasonable `min_trigger_amount`
   - Start with smaller `scale_percentage`
   - Monitor trading statistics and failure rate

4. **Operational Security**
   - Monitor program running status
   - Set up alert mechanisms
   - Backup configuration and data regularly

## 📊 Monitoring Metrics

Program prints trading statistics on exit:

```
[MyWallet] Trading Statistics:
  - Total Activities: 150
  - Filtered: 100
  - Trade Attempts: 50
  - Successful: 48
  - Failed: 2
```

## 🐛 Troubleshooting

### Issue: Program Won't Start

**Check**:
- Are environment variables set?
- Is config file format correct?
- Are dependencies fully installed?

### Issue: Cannot Execute Trades

**Check**:
- Is wallet balance sufficient?
- Is network connection normal?
- Is private key correct?
- Is API access restricted?

### Issue: Trades Being Filtered

**Check**:
- Is `min_trigger_amount` set too high?
- Is activity type `TRADE`?
- Check logs for specific reasons

## 🛠️ Development

### Add Custom Subscribers

```python
def my_custom_handler(activities: List[dict]):
    for activity in activities:
        # Custom processing logic
        pass

# Subscribe in main.py
activity_queue.subscribe(wallet_address, my_custom_handler)
```

### Extend Filtering Logic

Add custom filtering conditions in `CopyTrader._should_process_activity()`:

```python
# Add market whitelist filtering
whitelist = self.strategy_config.get('whitelist_markets', [])
if whitelist and market_id not in whitelist:
    return False
```

## 📚 Related Documentation

- [Design Document](docs/design/copy-trading-feature-design.md)
- [Implementation Summary](COPY_TRADING_IMPLEMENTATION.md)
- [Message Queue Refactor Summary](MESSAGE_QUEUE_REFACTOR_SUMMARY.md)
- [Polymarket CLOB API Documentation](https://docs.polymarket.com/)
- [py-clob-client GitHub](https://github.com/Polymarket/py-clob-client)

## 🤝 Contributing

Issues and Pull Requests are welcome!

## 📄 License

[MIT License](LICENSE)

## ⚖️ Disclaimer

This software is for educational and research purposes only. Users bear all risks when using this software for actual trading. The author is not responsible for any financial losses.

**Important Notes**:
- Cryptocurrency trading involves high risk
- Past performance does not guarantee future returns
- Only use funds you can afford to lose
- Fully understand trading rules and risks before use

---

**Happy Trading! 🚀**

For questions, check log files or submit an Issue.
