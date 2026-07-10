# A股尾盘策略框架

基于 AKShare + Backtrader 的尾盘选股+回测框架

## 策略逻辑

**核心思想**: 抓次日高开溢价，尾盘买入次日开盘冲高卖出，快进快出

### 选股条件

| 条件 | 取值 | 说明 |
|------|------|------|
| 昨日涨停 | 必须 | 当日最强信号，主力资金认可 |
| 量比 | >1.2 | 尾盘放量，资金在抢 |
| 换手率 | >3% | 流动性好，进出方便 |
| 流通市值 | <200亿 | 盘子小，拉升容易 |
| 振幅 | <5% | 当日波动不能太大 |
| 股价 | 4-30元 | 太高门槛高，太低股性差 |

### 技术指标（软参考）

- 均线多头（5日 > 10日 > 20日）
- MACD 金叉，红柱放大
- 平台突破：横盘后放量突破

### 卖出纪律

- 次日高开即出，不恋战
- 低开跌破开盘价 -2% 全出
- 止损线 -3% 到 -5%

## 安装

```bash
cd astock_tail_strategy

# 使用项目自带的虚拟环境（Python 3.12）
source venv/bin/activate

# 或者手动创建虚拟环境
python3.12 -m venv venv
source venv/bin/activate

# 安装依赖（如果虚拟环境中没有）
pip install akshare backtrader pandas numpy matplotlib

# 直接运行（无需激活虚拟环境）
./venv/bin/python main.py --help
```

依赖（已包含在 venv 中）:
- akshare>=1.12.0
- backtrader>=1.9.78
- pandas>=2.0.0
- numpy>=1.24.0
- matplotlib>=3.7.0

## 使用方法

### 1. 筛选候选股票

```bash
# 筛选今日候选股票
python main.py --screen --date 20240628

# 筛选昨日候选股票
python main.py --screen
```

### 2. 单只股票回测

```bash
# 回测单只股票
python main.py --backtest --symbol 000001 --start 20240101 --end 20240630
```

### 3. 批量回测

```bash
# 批量回测多只股票
python main.py --backtest --symbols 000001,000002,600000 --start 20240101 --end 20240630
```

### 4. 自定义参数

```bash
# 不要求均线多头
python main.py --backtest --symbol 000001 --start 20240101 --end 20240630 --no-ma

# 不要求MACD金叉
python main.py --backtest --symbol 000001 --start 20240101 --end 20240630 --no-macd
```

## 项目结构

```
astock_tail_strategy/
├── __init__.py
├── main.py                    # 主程序入口
├── examples.py                # 使用示例
├── requirements.txt           # 依赖
├── config.ini                 # 配置文件
├── README.md
├── venv/                      # Python虚拟环境（自动创建）
├── data/
│   └── akshare_provider.py    # AKShare数据获取
├── stock_selectors/           # 选股筛选器
│   └── tail_stock_selector.py # 尾盘选股筛选器
├── indicators/
│   └── technical_indicators.py # 技术指标计算
├── strategies/
│   └── sell_signals.py       # 卖出信号逻辑
├── backtest/
│   └── backtrader_engine.py  # Backtrader回测引擎
└── utils/
    └── config_loader.py      # 配置加载器
```

## 配置文件说明

编辑 `config.ini` 自定义策略参数:

```ini
[filter]
min_turnover_rate = 3.0       # 换手率 > 3%
max_market_cap = 200.0        # 流通市值 < 200亿

[sell]
gap_up_threshold = 0.01       # 高开阈值 1%
low_open_stop = 0.02          # 低开止损 2%
stop_loss = 0.03              # 止损线 3%
```

## 下一步

- [ ] 接入 QMT 实盘交易
- [ ] 增加更多技术指标
- [ ] 添加实时行情监控
- [ ] 优化回测性能

## 风险提示

⚠️ 所有策略仅供参考，股市有风险，投资需谨慎。

本框架仅供学习和研究使用，实盘交易前请充分测试并了解相关风险。
