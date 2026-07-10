"""
尾盘策略实现
继承自BaseStrategy
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
import pandas as pd
import logging

from .base import BaseStrategy, StrategyConfig, StockSignal, BacktestResult, StrategyRegistry

logger = logging.getLogger(__name__)


class TailStrategy(BaseStrategy):
    """
    尾盘策略
    
    核心逻辑：尾盘买入，次日开盘卖出
    
    选股条件：
    - 昨日涨停（必须）
    - 量比 > 1.2
    - 换手率 > 3%
    - 流通市值 < 200亿
    - 振幅 < 5%
    - 股价 4-30元
    
    卖出规则：
    - 次日高开即出
    - 低开-2%止损
    - 止损-3%
    """
    
    def get_name(self) -> str:
        return "尾盘策略"
    
    def get_description(self) -> str:
        return "尾盘买入，次日开盘卖出，抓次日高开溢价"
    
    def select_stocks(
        self,
        data: Any,
        date: str
    ) -> List[StockSignal]:
        """
        筛选候选股票
        
        Args:
            data: 包含涨停股数据的DataFrame
            date: 日期
            
        Returns:
            候选股票列表
        """
        signals = []
        
        # 从涨停股中筛选
        if isinstance(data, pd.DataFrame) and not data.empty:
            for _, row in data.iterrows():
                # 基本条件检查
                if self._check_basic_conditions(row):
                    signal = StockSignal(
                        symbol=row.get('代码', ''),
                        name=row.get('名称', ''),
                        signal_type='potential_buy',
                        price=row.get('收盘', 0),
                        confidence=0.7,
                        reason='满足选股条件',
                        strategy=self.name
                    )
                    signals.append(signal)
        
        return signals
    
    def _check_basic_conditions(self, row: pd.Series) -> bool:
        """检查基本条件"""
        try:
            # 股价条件
            price = row.get('最新价', 0) or row.get('收盘', 0)
            if price < self.params.get('min_price', 4) or price > self.params.get('max_price', 30):
                return False
            
            # 换手率条件
            turnover = row.get('换手率', 0)
            if turnover < self.params.get('min_turnover_rate', 3):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查条件失败: {e}")
            return False
    
    def generate_signals(
        self,
        stock_data: pd.DataFrame,
        current_date: str
    ) -> Optional[StockSignal]:
        """
        生成交易信号
        
        Args:
            stock_data: 股票历史数据
            current_date: 当前日期
            
        Returns:
            交易信号
        """
        if stock_data.empty or len(stock_data) < 20:
            return None
        
        # 获取最近N天数据
        recent = stock_data.tail(20)
        
        # 检查技术指标
        ma_bullish = self._check_ma_bullish(recent)
        macd_golden = self._check_macd_golden(recent)
        
        # 尾盘时间检查（简化：收盘前30分钟）
        # 实际应用中需要结合实时时间
        
        if self.params.get('require_ma_bullish', True) and not ma_bullish:
            return None
        
        if self.params.get('require_macd_golden', True) and not macd_golden:
            return None
        
        current_price = recent['收盘'].iloc[-1]
        
        return StockSignal(
            symbol=stock_data.attrs.get('symbol', ''),
            name=stock_data.attrs.get('name', ''),
            signal_type='buy',
            price=current_price,
            confidence=0.8 if (ma_bullish and macd_golden) else 0.6,
            reason=f"尾盘买入信号 - 均线多头:{ma_bullish}, MACD金叉:{macd_golden}",
            strategy=self.name
        )
    
    def _check_ma_bullish(self, data: pd.DataFrame) -> bool:
        """检查均线多头"""
        if len(data) < 20:
            return False
        
        ma5 = data['收盘'].rolling(5).mean().iloc[-1]
        ma10 = data['收盘'].rolling(10).mean().iloc[-1]
        ma20 = data['收盘'].rolling(20).mean().iloc[-1]
        
        return ma5 > ma10 > ma20
    
    def _check_macd_golden(self, data: pd.DataFrame) -> bool:
        """检查MACD金叉"""
        if len(data) < 26:
            return False
        
        # 计算EMA
        ema12 = data['收盘'].ewm(span=12, adjust=False).mean()
        ema26 = data['收盘'].ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        macd = (dif - dea) * 2
        
        # 检查最近两天
        if len(macd) >= 2:
            return macd.iloc[-1] > 0 and macd.iloc[-1] > macd.iloc[-2]
        
        return False
    
    def backtest(
        self,
        data: Any,
        start_date: str,
        end_date: str,
        initial_cash: float = 100000
    ) -> BacktestResult:
        """
        回测尾盘策略
        
        这个是简化版，实际应用中应使用Backtrader
        """
        # TODO: 使用Backtrader进行完整回测
        logger.info(f"回测 {self.name}: {start_date} ~ {end_date}")
        
        return BacktestResult(
            strategy_name=self.name,
            start_date=start_date,
            end_date=end_date,
            total_return=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            win_rate=0.0,
            total_trades=0,
            avg_profit=0.0,
            trades=[]
        )
    
    def get_sell_signal(
        self,
        buy_price: float,
        next_open: float,
        current_price: float,
        hold_days: int
    ) -> Optional[StockSignal]:
        """
        获取卖出信号
        
        Args:
            buy_price: 买入价
            next_open: 次日开盘价
            current_price: 当前价格
            hold_days: 持仓天数
        """
        gap_up_threshold = self.params.get('gap_up_threshold', 0.01)
        low_open_stop = self.params.get('low_open_stop', 0.02)
        stop_loss = self.params.get('stop_loss', 0.03)
        
        # 次日开盘卖出逻辑
        if hold_days == 1:
            # 高开卖出
            gap_ratio = (next_open - buy_price) / buy_price
            if gap_ratio >= gap_up_threshold:
                return StockSignal(
                    symbol="",
                    name="",
                    signal_type='sell',
                    price=next_open,
                    confidence=1.0,
                    reason=f"高开卖出，开盘溢价{gap_ratio*100:.2f}%",
                    strategy=self.name
                )
            
            # 低开止损
            low_ratio = (buy_price - next_open) / buy_price
            if low_ratio >= low_open_stop:
                return StockSignal(
                    symbol="",
                    name="",
                    signal_type='sell',
                    price=next_open,
                    confidence=1.0,
                    reason=f"低开止损，低开{low_ratio*100:.2f}%",
                    strategy=self.name
                )
        
        # 盘中止损
        current_ratio = (current_price - buy_price) / buy_price
        if current_ratio <= -stop_loss:
            return StockSignal(
                symbol="",
                name="",
                signal_type='sell',
                price=current_price,
                confidence=1.0,
                reason=f"止损，亏损{current_ratio*100:.2f}%",
                strategy=self.name
            )
        
        return None


# 注册策略
StrategyRegistry.register('tail', TailStrategy)
StrategyRegistry.register('尾盘策略', TailStrategy)
