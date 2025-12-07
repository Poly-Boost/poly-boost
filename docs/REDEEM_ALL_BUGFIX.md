# 批量赎回功能修复记录

## 修复日期
2025-12-07

## 问题描述

### 问题 1: 导入错误
**错误信息：**
```
NameError: name 'Dict' is not defined
```

**原因：** 在 `order_schemas.py` 中使用了 `Dict` 类型但未从 `typing` 导入。

**修复：**
```python
# poly_boost/api/schemas/order_schemas.py
from typing import Optional, List, Any, Dict  # 添加 Dict
```

### 问题 2: Position 对象字段名错误
**错误信息：**
```
ValueError: Missing token_id (asset)
```

**原因：** 代码尝试从 Position 对象读取 `asset` 字段，但实际字段名是 `token_id`。

**Position 对象的实际字段：**
```python
Position.model_fields.keys() = {
    'proxy_wallet',
    'token_id',           # ✅ 正确字段
    'complementary_token_id',
    'condition_id',
    'outcome',
    'complementary_outcome',
    'outcome_index',
    'size',
    'avg_price',
    'current_price',
    'redeemable',
    'initial_value',
    'current_value',
    'cash_pnl',
    'percent_pnl',
    'total_bought',
    'realized_pnl',
    'percent_realized_pnl',
    'title',
    'slug',
    'icon',
    'event_slug',
    'end_date',
    'negative_risk'
}
```

**修复：**
```python
# poly_boost/services/order_service.py

# 修复前（错误）:
token_id = getattr(position, 'asset', None)

# 修复后（正确）:
token_id = getattr(position, 'token_id', None)
```

同时修复了错误记录部分：
```python
# 修复前:
error_detail = {
    "token_id": getattr(position, 'asset', 'unknown'),
    ...
}

# 修复后:
error_detail = {
    "token_id": getattr(position, 'token_id', 'unknown'),
    ...
}
```

## 修复的文件

1. ✅ `poly_boost/api/schemas/order_schemas.py` - 添加 Dict 导入
2. ✅ `poly_boost/services/order_service.py` - 修正字段名从 `asset` 到 `token_id`

## 验证步骤

1. **验证导入：**
```bash
python -c "from poly_boost.api.schemas.order_schemas import RedeemAllResponse; print('OK')"
```

2. **验证服务：**
```bash
python -c "from poly_boost.services.order_service import OrderService; print('OK')"
```

3. **重启服务并测试：**
```bash
# 启动后端
uvicorn poly_boost.api.main:app --reload

# 测试批量赎回功能
```

## 字段映射对照表

### Frontend (TypeScript) ↔ Backend (Python)

| 前端字段名 | 后端 Position 字段 | 说明 |
|----------|------------------|------|
| `asset` | `token_id` | Token ID（主要） |
| `oppositeAsset` | `complementary_token_id` | 互补 Token ID |
| `conditionId` | `condition_id` | Condition ID |
| `outcome` | `outcome` | 结果（YES/NO） |
| `size` | `size` | 仓位大小 |
| `avgPrice` | `avg_price` | 平均价格 |
| `curPrice` | `current_price` | 当前价格 |
| `currentValue` | `current_value` | 当前价值 |
| `redeemable` | `redeemable` | 是否可赎回 |

### 注意事项

**前端显示字段名：** 前端组件（如 `PositionList.tsx`）使用的是 `asset` 作为显示字段，但这是从后端 API 转换后的数据。

**后端 API 响应转换：**
- `PositionService` 从 Polymarket API 获取 Position 对象
- Position 对象原生字段是 `token_id`
- 可能需要在 API 层做字段映射（如果前端期望 `asset` 字段）

**当前解决方案：** 后端直接使用 `token_id`，前端需要相应调整或在 API 层做转换。

## 测试结果

- [x] 导入错误已修复
- [x] Position 字段映射已修正
- [ ] 批量赎回功能测试（待用户测试）

## 后续建议

1. **统一字段命名：** 考虑在 API 层统一转换，使前后端使用一致的字段名
2. **类型定义：** 在前端添加 TypeScript 类型定义，明确 Position 接口
3. **文档更新：** 更新 API 文档，说明 Position 对象的准确字段名
4. **单元测试：** 添加 Position 数据处理的单元测试，避免字段错误

---

**修复完成时间：** 2025-12-07
**测试状态：** 等待用户测试验证
