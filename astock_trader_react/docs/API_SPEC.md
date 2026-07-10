# A股量化交易系统 - API 接口规范

**版本**: v1.0.0
**更新日期**: 2026-07-02
**Base URL**: `http://localhost:8000/api`

---

## 目录

1. [认证](#认证)
2. [策略管理](#策略管理)
3. [选股筛选](#选股筛选)
4. [回测](#回测)
5. [自选股](#自选股)
6. [交易信号](#交易信号)
7. [订单管理](#订单管理)
8. [Dashboard](#dashboard)

---

## 认证

### 访问令牌验证
```
GET /api/auth/verify
```
验证当前访问是否有效。

**响应**:
```json
{
  "valid": true,
  "message": "验证成功"
}
```

---

## 策略管理

### 获取策略列表
```
GET /api/strategies
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": 1,
      "name": "尾盘策略",
      "description": "尾盘买入，次日开盘卖出",
      "enabled": true,
      "params": {
        "min_turnover_rate": 3.0,
        "max_market_cap": 200.0,
        "max_amplitude": 5.0,
        "min_price": 4.0,
        "max_price": 30.0,
        "min_volume_ratio": 1.2,
        "gap_up_threshold": 1.0,
        "low_open_stop": 2.0,
        "stop_loss": 3.0
      }
    }
  ]
}
```

### 获取单个策略详情
```
GET /api/strategies/{name}
```

**参数**:
- `name` (路径参数): 策略名称

**响应**: 同上，但只有单个策略对象

### 更新策略配置
```
PUT /api/strategies/{name}
```

**请求体**:
```json
{
  "params": {
    "min_turnover_rate": 5.0,
    "max_market_cap": 150.0
  }
}
```

**响应**:
```json
{
  "code": 0,
  "message": "更新成功"
}
```

### 切换策略启用状态
```
POST /api/strategies/{name}/toggle
```

**响应**:
```json
{
  "code": 0,
  "message": "状态已切换",
  "data": {
    "enabled": false
  }
}
```

---

## 选股筛选

### 筛选候选股票
```
GET /api/screen
```

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| date | string | 否 | 日期，YYYYMMDD，默认今天 |
| strategy | string | 否 | 策略名称，默认 tail |

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "date": "20260702",
    "strategy": "尾盘策略",
    "total": 5,
    "stocks": [
      {
        "symbol": "300001",
        "name": "测试股票",
        "close": 15.50,
        "turnover_rate": 5.2,
        "volume_ratio": 1.8,
        "market_cap": 45.6,
        "amplitude": 3.5,
        "ma_bullish": true,
        "macd_golden": false,
        "breakout": false,
        "confidence": 0.75,
        "reason": "满足选股条件"
      }
    ]
  }
}
```

### 获取股票详情
```
GET /api/stock/{symbol}
```

**参数**:
- `symbol` (路径参数): 股票代码

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "symbol": "300001",
    "name": "测试股票",
    "price": 15.50,
    "change": 2.5,
    "change_percent": 19.23,
    "turnover_rate": 5.2,
    "volume_ratio": 1.8,
    "market_cap": 45.6,
    "amplitude": 3.5,
    "indicators": {
      "ma5": 14.20,
      "ma10": 13.80,
      "ma20": 13.50,
      "ma_bullish": true,
      "macd": 0.25,
      "dif": 0.30,
      "dea": 0.28,
      "macd_golden": true,
      "rsi": 68.5,
      "boll_upper": 16.80,
      "boll_mid": 15.20,
      "boll_lower": 13.60
    }
  }
}
```

### 获取股票K线数据
```
GET /api/stock/{symbol}/kline
```

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| period | string | 否 | K线周期: day/week/month/minute，默认 day |
| start_date | string | 否 | 开始日期 YYYYMMDD |
| end_date | string | 否 | 结束日期 YYYYMMDD |

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "symbol": "300001",
    "name": "测试股票",
    "period": "day",
    "data": [
      {
        "date": "2026-06-01",
        "open": 14.50,
        "high": 15.80,
        "low": 14.20,
        "close": 15.50,
        "volume": 1250000,
        "amount": 19250000
      }
    ]
  }
}
```

---

## 回测

### 运行回测
```
POST /api/backtest
```

**请求体**:
```json
{
  "strategy": "尾盘策略",
  "start_date": "20260101",
  "end_date": "20260630",
  "initial_cash": 100000,
  "symbols": ["300001", "300002"]
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "strategy": "尾盘策略",
    "start_date": "20260101",
    "end_date": "20260630",
    "initial_cash": 100000,
    "final_value": 115200,
    "total_return": 15.2,
    "annual_return": 32.5,
    "sharpe_ratio": 1.85,
    "max_drawdown": -8.2,
    "win_rate": 65.0,
    "total_trades": 45,
    "profit_factor": 1.95,
    "avg_profit": 1.2,
    "max_profit": 8.5,
    "min_profit": -3.2,
    "equity_curve": [
      {"date": "2026-01-01", "value": 100000},
      {"date": "2026-01-02", "value": 100850}
    ],
    "trades": [
      {
        "id": 1,
        "symbol": "300001",
        "name": "测试股票",
        "buy_date": "2026-06-01",
        "buy_price": 15.50,
        "sell_date": "2026-06-02",
        "sell_price": 16.00,
        "profit": 3.0,
        "profit_percent": 3.23,
        "hold_days": 1,
        "reason": "高开卖出"
      }
    ]
  }
}
```

### 获取回测历史
```
GET /api/backtest/history
```

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| strategy | string | 否 | 策略名称筛选 |
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页数量，默认 20 |

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 10,
    "page": 1,
    "page_size": 20,
    "list": [
      {
        "id": 1,
        "strategy": "尾盘策略",
        "start_date": "20260101",
        "end_date": "20260630",
        "total_return": 15.2,
        "sharpe_ratio": 1.85,
        "max_drawdown": -8.2,
        "win_rate": 65.0,
        "created_at": "2026-07-02 10:00:00"
      }
    ]
  }
}
```

### 获取回测详情
```
GET /api/backtest/{id}
```

**响应**: 同运行回测的响应结构

---

## 自选股

### 获取自选股列表
```
GET /api/watch
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "symbol": "300001",
      "name": "测试股票",
      "added_at": "2026-07-01 10:00:00",
      "tags": ["关注", "科技"],
      "notes": "备注信息"
    }
  ]
}
```

### 添加自选股
```
POST /api/watch
```

**请求体**:
```json
{
  "symbol": "300001",
  "name": "测试股票",
  "tags": ["关注"],
  "notes": "备注"
}
```

**响应**:
```json
{
  "code": 0,
  "message": "添加成功"
}
```

### 删除自选股
```
DELETE /api/watch/{symbol}
```

**响应**:
```json
{
  "code": 0,
  "message": "删除成功"
}
```

---

## 交易信号

### 获取当前信号
```
GET /api/signals
```

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| strategy | string | 否 | 策略筛选 |
| status | string | 否 | pending/executed/expired |
| page | int | 否 | 页码 |
| page_size | int | 否 | 每页数量 |

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 5,
    "list": [
      {
        "id": 1,
        "symbol": "300001",
        "name": "测试股票",
        "signal_type": "buy",
        "price": 15.50,
        "confidence": 0.85,
        "reason": "尾盘买入信号",
        "strategy": "尾盘策略",
        "created_at": "2026-07-02 14:30:00",
        "status": "pending"
      }
    ]
  }
}
```

### 执行信号
```
POST /api/signals/{id}/execute
```

**响应**:
```json
{
  "code": 0,
  "message": "执行成功",
  "data": {
    "order_id": "ORD2026070214300001"
  }
}
```

### 取消信号
```
POST /api/signals/{id}/cancel
```

**响应**:
```json
{
  "code": 0,
  "message": "已取消"
}
```

---

## 订单管理

### 获取订单列表
```
GET /api/orders
```

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | pending/filled/cancelled |
| symbol | string | 否 | 股票代码 |
| page | int | 否 | 页码 |
| page_size | int | 否 | 每页数量 |

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 20,
    "list": [
      {
        "id": 1,
        "order_id": "ORD2026070214300001",
        "symbol": "300001",
        "name": "测试股票",
        "direction": "buy",
        "price": 15.50,
        "quantity": 100,
        "amount": 1550.00,
        "commission": 4.65,
        "status": "filled",
        "strategy": "尾盘策略",
        "created_at": "2026-07-02 14:30:00",
        "filled_at": "2026-07-02 14:30:05"
      }
    ]
  }
}
```

### 获取订单详情
```
GET /api/orders/{order_id}
```

**响应**: 同上，但只有单个订单对象

### 撤单
```
POST /api/orders/{order_id}/cancel
```

**响应**:
```json
{
  "code": 0,
  "message": "撤单成功"
}
```

---

## Dashboard

### 获取仪表盘数据
```
GET /api/dashboard
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "account": {
      "total_assets": 115200,
      "cash": 50000,
      "stocks_value": 65200,
      "today_profit": 1200,
      "today_profit_rate": 1.05
    },
    "positions": [
      {
        "symbol": "300001",
        "name": "测试股票",
        "quantity": 100,
        "cost": 15.50,
        "price": 16.00,
        "profit": 50.00,
        "profit_rate": 3.23
      }
    ],
    "signals": {
      "pending": 3,
      "today_buy": 2,
      "today_sell": 1
    },
    "backtest": {
      "latest_id": 5,
      "total_return": 15.2,
      "win_rate": 65.0,
      "sharpe_ratio": 1.85
    },
    "watchlist_count": 10
  }
}
```

### 获取今日选股
```
GET /api/dashboard/today-stocks
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "date": "2026-07-02",
    "candidates": [
      {
        "symbol": "300001",
        "name": "测试股票",
        "close": 15.50,
        "turnover_rate": 5.2,
        "confidence": 0.85
      }
    ]
  }
}
```

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 通用响应格式

**成功**:
```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

**失败**:
```json
{
  "code": 400,
  "message": "参数错误",
  "data": null
}
```
