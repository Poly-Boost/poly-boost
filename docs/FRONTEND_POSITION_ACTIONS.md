# 前端头寸操作功能

## 概述

在 `PositionList.tsx` 组件中新增了头寸操作功能,允许用户直接从前端界面执行交易操作。

## 新增功能

### 1. 操作列 (Actions Column)

在头寸列表中新增"Actions"列,根据头寸状态显示不同的操作按钮:

#### 可赎回头寸 (Redeemable)
- **显示条件**: `position.redeemable === true`
- **操作按钮**: "Redeem" 按钮
- **功能**: 收获已解决市场的奖励

#### 不可赎回头寸 (Active)
- **显示条件**: `position.redeemable === false` 或 `undefined`
- **操作按钮**: 
  - "Market Sell" - 市价卖出
  - "Limit Sell" - 限价卖出

### 2. 市价卖出 (Market Sell)

**功能描述**:
- 立即以市场价格出售全部头寸
- 使用 FOK (Fill or Kill) 订单类型
- 一键操作,无需额外确认

**实现逻辑**:
```typescript
const handleMarketSell = async (position: Position) => {
  await apiClient.marketSell(position.asset || '', null, 'FOK');
  // null 表示出售全部数量
};
```

### 3. 限价卖出 (Limit Sell)

**功能描述**:
- 以指定价格挂限价卖单
- 弹出对话框让用户设置价格
- 使用 GTC (Good Till Cancel) 订单类型

**对话框内容**:
- Market: 市场名称
- Outcome: YES/NO 标签
- Size: 头寸数量 (全部)
- Current Price: 当前市场价格
- Limit Price: 可调整的限价输入框 (0.01 - 0.99)

**价格输入**:
- 最小值: 0.01
- 最大值: 0.99
- 步进: 0.01
- 精度: 4位小数
- 默认值: 当前市场价格

### 4. 收获奖励 (Redeem)

**功能描述**:
- 收获已解决市场的奖励
- 自动计算赎回数量
- 根据 `outcomeIndex` 确定赎回哪个结果

**实现逻辑**:
```typescript
const amounts = position.outcomeIndex === 0 
  ? [position.size, 0]  // 赎回第一个结果
  : [0, position.size]; // 赎回第二个结果
```

## UI/UX 特性

### 加载状态
- 操作进行时按钮显示 loading 状态
- 防止重复提交
- 通过 `actionLoading` 状态管理

### 消息提示
- **成功**: 绿色成功提示
- **失败**: 红色错误提示,显示详细错误信息

### 按钮状态
- **禁用条件**:
  - Market/Limit Sell: 缺少 `asset` (token ID)
  - Redeem: 缺少 `conditionId`
- **加载状态**: 当前操作的头寸

### 响应式设计
- 操作列固定在右侧 (`fixed: 'right'`)
- 表格支持横向滚动 (`scroll={{ x: 1500 }}`)
- 按钮使用小尺寸 (`size="small"`)

## API 集成

### 新增 API 方法 (client.ts)

```typescript
// 市价卖出
async marketSell(tokenId: string, amount: number | null, orderType: string = 'FOK')

// 限价卖出
async limitSell(tokenId: string, price: number, amount: number | null, orderType: string = 'GTC')

// 收获奖励
async claimRewards(conditionId: string, amounts: number[])
```

### 后端端点

- `POST /orders/sell/market` - 市价卖出
- `POST /orders/sell/limit` - 限价卖出
- `POST /orders/rewards/claim` - 收获奖励

## 代码结构

```typescript
PositionList.tsx
├── State Management
│   ├── limitSellModal (限价卖出对话框状态)
│   └── actionLoading (加载状态)
├── Event Handlers
│   ├── handleMarketSell() (市价卖出)
│   ├── handleOpenLimitSell() (打开限价对话框)
│   ├── handleLimitSellConfirm() (确认限价卖出)
│   └── handleRedeem() (收获奖励)
├── Table Columns
│   └── Actions Column (操作列)
└── Modal
    └── Limit Sell Dialog (限价卖出对话框)
```

## 使用示例

### 市价卖出
1. 在头寸列表中找到要出售的头寸
2. 点击 "Market Sell" 按钮
3. 系统自动以市场价出售全部数量
4. 显示成功或失败消息

### 限价卖出
1. 在头寸列表中找到要出售的头寸
2. 点击 "Limit Sell" 按钮
3. 在弹出对话框中调整价格
4. 点击 "OK" 确认
5. 系统创建限价卖单

### 收获奖励
1. 在头寸列表中找到可赎回的头寸 (显示 "Redeem" 按钮)
2. 点击 "Redeem" 按钮
3. 系统自动赎回奖励
4. 显示成功或失败消息

## 错误处理

### 网络错误
```typescript
catch (error: unknown) {
  const err = error as { response?: { data?: { detail?: string } }; message?: string };
  message.error(`Failed: ${err.response?.data?.detail || err.message || 'Unknown error'}`);
}
```

### 常见错误提示
- "Missing condition ID" - 赎回操作缺少条件ID
- "Failed to sell" - 市价卖出失败
- "Failed to create limit order" - 限价单创建失败
- "Failed to redeem" - 赎回失败

## 类型安全

### Position 接口
```typescript
interface Position {
  asset?: string;           // Token ID (用于交易)
  conditionId?: string;     // Condition ID (用于赎回)
  redeemable?: boolean;     // 是否可赎回
  outcomeIndex?: number;    // 结果索引 (0或1)
  size: number;             // 头寸数量
  curPrice?: number;        // 当前价格
  // ... 其他字段
}
```

## 最佳实践

### 1. 用户体验
- 操作前无需额外确认 (市价卖出)
- 限价卖出提供可视化确认对话框
- 实时显示操作状态
- 明确的成功/失败反馈

### 2. 安全性
- 所有操作需要后端认证
- 前端只发送必要的参数
- 错误信息不暴露敏感数据

### 3. 性能
- 使用状态管理避免不必要的重渲染
- 按钮禁用防止重复提交
- 异步操作不阻塞UI

## 测试建议

### 单元测试
- 测试按钮显示逻辑 (redeemable vs not redeemable)
- 测试价格输入验证
- 测试错误处理

### 集成测试
- 测试完整的市价卖出流程
- 测试限价卖出对话框交互
- 测试赎回流程

### E2E 测试
```typescript
// 示例测试用例
it('should market sell position', async () => {
  // 1. 找到头寸行
  // 2. 点击 Market Sell 按钮
  // 3. 等待成功消息
  // 4. 验证头寸已更新
});
```

## 未来改进

### 潜在功能
- [ ] 部分卖出 (指定数量)
- [ ] 批量操作
- [ ] 操作历史记录
- [ ] 撤销限价单
- [ ] 价格提醒
- [ ] 确认对话框 (可选)

### UI 优化
- [ ] 更详细的加载动画
- [ ] 操作成功后刷新列表
- [ ] 价格图表预览
- [ ] 快捷键支持

## 相关文档

- [ORDER_API.md](./ORDER_API.md) - 后端API文档
- [ORDER_SERVICE_README.md](./ORDER_SERVICE_README.md) - 服务层文档
- [PositionList.tsx](../frontend/src/components/PositionList.tsx) - 源代码

## 依赖

- React 18+
- Ant Design 5+
- TypeScript 4+
- axios

## 更新日志

**2025-10-19**:
- ✅ 新增操作列
- ✅ 实现市价卖出功能
- ✅ 实现限价卖出功能
- ✅ 实现收获奖励功能
- ✅ 添加加载状态
- ✅ 添加错误处理
- ✅ 添加限价卖出对话框
