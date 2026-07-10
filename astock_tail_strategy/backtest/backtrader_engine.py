"""
Backtrader 回测引擎
==================
实现尾盘策略的回测框架

策略逻辑:
- 尾盘买入（14:30-15:00）
- 次日高开卖出
- 次日低开-2%全出
- 止损-3%到-5%
"""

import backtrader as bt
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

from stock_selectors.tail_stock_selector import FilterConfig
from indicators.technical_indicators import TechnicalAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class StrategyConfig:
    """策略配置"""
    # 买入设置
    buy_time_hour: int = 14      # 尾盘买入时间（小时）
    buy_time_minute: int = 30    # 尾盘买入时间（分钟）
    position_size: float = 0.95   # 单只仓位（0-1）
    
    # 卖出设置
    sell_on_gap_up: bool = True  # 高开卖出
    gap_up_threshold: float = 0.01  # 高开阈值 1%
    
    stop_loss: float = 0.03       # 止损线 -3%
    stop_loss_low: float = 0.05   # 止损线 -5%（更严格）
    
    low_open_stop: float = 0.02   # 低开止损 -2%
    
    # 持仓天数
    max_hold_days: int = 3        # 最大持仓天数
    
    # 技术指标要求
    require_ma_bullish: bool = True
    require_macd_golden: bool = True
    require_breakout: bool = False


class TailStrategy(bt.Strategy):
    """
    尾盘策略
    
    买入信号: 
    - 14:30-15:00 尾盘买入
    - 满足选股条件（硬条件+软指标）
    
    卖出信号:
    - 次日高开即出
    - 次日低开-2%全出
    - 止损-3%
    """
    
    params = (
        ('config', StrategyConfig()),
        ('printlog', False),
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        
        # 追踪订单
        self.order = None
        self.buyprice = None
        self.buycomm = None
        
        # 买入日期
        self.buy_date = None
        
        # 技术分析器
        self.tech_analyzer = TechnicalAnalyzer()
        
    def log(self, txt, dt=None):
        """日志"""
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            logger.info(f'{dt.isoformat()} {txt}')
    
    def notify_order(self, order):
        """订单通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入完成: 价格 {order.executed.price:.2f}, '
                        f'成本 {order.executed.value:.2f}, '
                        f'手续费 {order.executed.comm:.2f}')
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                self.buy_date = self.datas[0].datetime.date(0)
            elif order.issell():
                self.log(f'卖出完成: 价格 {order.executed.price:.2f}, '
                        f'成本 {order.executed.value:.2f}, '
                        f'手续费 {order.executed.comm:.2f}')
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单 取消/保证金不足/拒绝')
        
        self.order = None
    
    def notify_trade(self, trade):
        """交易通知"""
        if not trade.isclosed:
            return
        
        self.log(f'交易盈利: 毛利润 {trade.pnl:.2f}, 净利润 {trade.pnlcomm:.2f}')
    
    def next(self):
        """主循环"""
        # 检查订单
        if self.order:
            return
        
        # 获取当前时间
        dt = self.datas[0].datetime.datetime(0)
        now = dt.time() if dt else None
        
        # 持仓检查
        if self.position:
            self._check_sell(now)
            return
        
        # 尾盘买入信号
        if self._is_tail_time(now) and not self.position:
            self._try_buy()
    
    def _is_tail_time(self, now) -> bool:
        """判断是否尾盘时间"""
        if now is None:
            return False
        
        config = self.params.config
        tail_start = config.buy_time_hour * 60 + config.buy_time_minute
        market_end = 15 * 60  # 15:00收盘
        
        current_minutes = now.hour * 60 + now.minute
        return tail_start <= current_minutes <= market_end
    
    def _check_sell(self, now):
        """检查卖出信号"""
        config = self.params.config
        
        # 获取持仓天数
        if self.buy_date:
            hold_days = (self.datas[0].datetime.date(0) - self.buy_date).days
        else:
            hold_days = 0
        
        # 最大持仓天数检查
        if hold_days >= config.max_hold_days:
            self.log(f'持仓超过{max_hold_days}天，强制卖出')
            self.close()
            return
        
        # 次日判断（买入后的第一天）
        if hold_days == 0:
            return  # 当天买入不卖
        
        # 获取当日开盘价和当前价
        open_price = self.dataopen[0]
        current_price = self.dataclose[0]
        buy_price = self.buyprice
        
        # 次日开盘卖出逻辑
        if hold_days == 1:
            # 高开卖出
            if config.sell_on_gap_up:
                gap_ratio = (open_price - buy_price) / buy_price
                if gap_ratio >= config.gap_up_threshold:
                    self.log(f'高开卖出: 开盘价 {open_price:.2f}, 溢价 {gap_ratio*100:.2f}%')
                    self.close()
                    return
            
            # 低开止损
            low_open_ratio = (buy_price - open_price) / buy_price
            if low_open_ratio >= config.low_open_stop:
                self.log(f'低开止损: 开盘价 {open_price:.2f}, 低开 {low_open_ratio*100:.2f}%')
                self.close()
                return
        
        # 盘中止损
        current_ratio = (current_price - buy_price) / buy_price
        if current_ratio <= -config.stop_loss:
            self.log(f'止损卖出: 当前价 {current_price:.2f}, 亏损 {current_ratio*100:.2f}%')
            self.close()
    
    def _try_buy(self):
        """尝试买入"""
        config = self.params.config
        
        # 获取数据用于技术分析
        data_df = self._get_dataframe()
        
        if data_df.empty or len(data_df) < 30:
            return
        
        # 技术分析
        tech_result = self.tech_analyzer.analyze(
            data_df,
            require_ma_bullish=config.require_ma_bullish,
            require_macd_golden=config.require_macd_golden,
            require_breakout=config.require_breakout
        )
        
        # 检查技术指标
        if config.require_ma_bullish and not tech_result['signals'].get('均线多头', False):
            self.log('不满足均线多头条件')
            return
        
        if config.require_macd_golden and not tech_result['signals'].get('MACD金叉', False):
            self.log('不满足MACD金叉条件')
            return
        
        # 价格过滤
        price = self.dataclose[0]
        if price < 4 or price > 30:
            self.log(f'价格{price}不在4-30元区间')
            return
        
        # 执行买入
        self.log(f'尾盘买入: 价格 {price:.2f}, 账户可用 {self.broker.getcash():.2f}')
        self.order = self.buy()
    
    def _get_dataframe(self) -> pd.DataFrame:
        """将Backtrader数据转换为DataFrame"""
        dates = bt.num2date(self.datas[0].datetime.array)
        df = pd.DataFrame({
            '日期': dates,
            '开盘': self.datas[0].open.get(size=len(self.datas[0])),
            '最高': self.datas[0].high.get(size=len(self.datas[0])),
            '最低': self.datas[0].low.get(size=len(self.datas[0])),
            '收盘': self.datas[0].close.get(size=len(self.datas[0])),
            '成交量': self.datas[0].volume.get(size=len(self.datas[0])),
        })
        return df


class BacktestEngine:
    """回测引擎"""
    
    def __init__(
        self,
        initial_cash: float = 100000,
        config: Optional[StrategyConfig] = None
    ):
        self.initial_cash = initial_cash
        self.config = config or StrategyConfig()
        self.cerebro = None
        self.results = {}
        
    def setup(self) -> bt.Cerebro:
        """设置回测引擎"""
        cerebro = bt.Cerebro()
        
        # 设置初始资金
        cerebro.broker.setcash(self.initial_cash)
        
        # 设置手续费（千分之三，双边）
        cerebro.broker.setcommission(commission=0.003)
        
        # 设置滑点（千分之五）
        cerebro.broker.set_slippage_perc(0.005)
        
        # 添加策略
        cerebro.addstrategy(
            TailStrategy,
            config=self.config,
            printlog=True
        )
        
        # 添加分析器
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        self.cerebro = cerebro
        return cerebro
    
    def add_data(self, df: pd.DataFrame, name: str):
        """添加数据"""
        if self.cerebro is None:
            self.setup()
        
        # 转换DataFrame为Backtrader数据格式
        data = bt.feeds.PandasData(
            dataname=df,
            datetime=0,      # 日期列索引
            open=1,          # 开盘价列索引
            high=2,          # 最高价列索引
            low=3,          # 最低价列索引
            close=4,         # 收盘价列索引
            volume=5,       # 成交量列索引
            openinterest=-1
        )
        
        self.cerebro.adddata(data, name=name)
    
    def run(self) -> Dict:
        """运行回测"""
        if self.cerebro is None:
            self.setup()
        
        print(f'初始资金: {self.initial_cash:.2f}')
        print(f'开始回测...')
        
        results = self.cerebro.run()
        strat = results[0]
        
        # 获取最终资金
        final_value = self.cerebro.broker.getvalue()
        
        print(f'最终资金: {final_value:.2f}')
        print(f'总收益率: {(final_value - self.initial_cash) / self.initial_cash * 100:.2f}%')
        
        # 获取分析结果
        self.results = {
            'initial_cash': self.initial_cash,
            'final_value': final_value,
            'total_return': (final_value - self.initial_cash) / self.initial_cash,
            'final_value': final_value
        }
        
        # 分析器结果
        if hasattr(strat.analyzers, 'sharpe'):
            sharpe = strat.analyzers.sharpe.get_analysis()
            self.results['sharpe_ratio'] = sharpe.get('sharperatio')
        
        if hasattr(strat.analyzers, 'drawdown'):
            dd = strat.analyzers.drawdown.get_analysis()
            self.results['max_drawdown'] = dd.get('max', {}).get('drawdown', 0)
        
        if hasattr(strat.analyzers, 'trades'):
            trades = strat.analyzers.trades.get_analysis()
            self.results['trade_stats'] = trades
        
        return self.results
    
    def plot_results(self, save_path: Optional[str] = None):
        """绘制回测结果"""
        if self.cerebro:
            if save_path:
                self.cerebro.plot(savefig=save_path)
            else:
                self.cerebro.plot()


# 兼容全局变量
max_hold_days = 3


if __name__ == "__main__":
    # 测试回测引擎
    from data.akshare_provider import AKDataProvider
    
    # 获取数据
    provider = AKDataProvider()
    
    # 测试单只股票
    symbol = '000001'
    data = provider.get_daily_data(symbol, '20240101', '20240630')
    
    if not data.empty:
        # 创建回测引擎
        engine = BacktestEngine(
            initial_cash=100000,
            config=StrategyConfig()
        )
        
        # 添加数据
        engine.add_data(data, name=symbol)
        
        # 运行回测
        results = engine.run()
        
        print("\n回测结果汇总:")
        print(results)
