"""
卖出信号模块
===========
尾盘策略的卖出逻辑

卖出纪律:
- 次日高开即出
- 低开跌破开盘价-2%全出
- 止损线一般-3%到-5%
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class SellReason(Enum):
    """卖出原因"""
    GAP_UP = "高开卖出"
    LOW_OPEN_STOP = "低开止损"
    TRAILING_STOP = "移动止损"
    TIME_STOP = "时间止损"
    MANUAL = "手动卖出"


@dataclass
class SellSignal:
    """卖出信号"""
    should_sell: bool
    reason: SellReason
    price: float
    profit_ratio: float  # 收益率
    message: str


class SellSignalGenerator:
    """卖出信号生成器"""
    
    def __init__(
        self,
        gap_up_threshold: float = 0.01,     # 高开阈值 1%
        low_open_threshold: float = 0.02,    # 低开止损阈值 2%
        stop_loss: float = 0.03,             # 止损线 3%
        trailing_stop: float = 0.02,         # 移动止损 2%
        max_hold_days: int = 3               # 最大持仓天数
    ):
        self.gap_up_threshold = gap_up_threshold
        self.low_open_threshold = low_open_threshold
        self.stop_loss = stop_loss
        self.trailing_stop = trailing_stop
        self.max_hold_days = max_hold_days
        
        # 追踪最高价
        self.highest_price = 0.0
    
    def reset(self):
        """重置状态"""
        self.highest_price = 0.0
    
    def update_highest(self, price: float):
        """更新最高价（用于移动止损）"""
        if price > self.highest_price:
            self.highest_price = price
    
    def check_sell(
        self,
        current_price: float,
        open_price: float,
        buy_price: float,
        hold_days: int,
        is_next_day: bool = True
    ) -> SellSignal:
        """
        检查是否应该卖出
        
        Args:
            current_price: 当前价格
            open_price: 开盘价
            buy_price: 买入价
            hold_days: 持仓天数（0=买入当天）
            is_next_day: 是否次日
            
        Returns:
            SellSignal对象
        """
        # 计算收益率
        profit_ratio = (current_price - buy_price) / buy_price
        
        # 更新最高价
        self.update_highest(current_price)
        
        # 次日卖出逻辑
        if is_next_day and hold_days == 1:
            # 次日开盘价与买入价比较
            gap_ratio = (open_price - buy_price) / buy_price
            
            # 高开卖出
            if gap_ratio >= self.gap_up_threshold:
                return SellSignal(
                    should_sell=True,
                    reason=SellReason.GAP_UP,
                    price=open_price,
                    profit_ratio=gap_ratio,
                    message=f"次日高开 {gap_ratio*100:.2f}%，开盘价卖出"
                )
            
            # 低开止损
            low_open_ratio = (buy_price - open_price) / buy_price
            if low_open_ratio >= self.low_open_threshold:
                return SellSignal(
                    should_sell=True,
                    reason=SellReason.LOW_OPEN_STOP,
                    price=open_price,
                    profit_ratio=-low_open_ratio,
                    message=f"次日低开 {low_open_ratio*100:.2f}%，止损卖出"
                )
        
        # 盘中止损
        if profit_ratio <= -self.stop_loss:
            return SellSignal(
                should_sell=True,
                reason=SellReason.TRAILING_STOP,
                price=current_price,
                profit_ratio=profit_ratio,
                message=f"止损 {profit_ratio*100:.2f}%"
            )
        
        # 移动止损（从最高点回落）
        if self.highest_price > buy_price:
            pullback_ratio = (self.highest_price - current_price) / self.highest_price
            if pullback_ratio >= self.trailing_stop:
                return SellSignal(
                    should_sell=True,
                    reason=SellReason.TRAILING_STOP,
                    price=current_price,
                    profit_ratio=(current_price - buy_price) / buy_price,
                    message=f"移动止损，从最高点回落 {pullback_ratio*100:.2f}%"
                )
        
        # 时间止损
        if hold_days >= self.max_hold_days:
            return SellSignal(
                should_sell=True,
                reason=SellReason.TIME_STOP,
                price=current_price,
                profit_ratio=profit_ratio,
                message=f"持仓超过{self.max_hold_days}天，时间止损"
            )
        
        return SellSignal(
            should_sell=False,
            reason=SellReason.MANUAL,
            price=current_price,
            profit_ratio=profit_ratio,
            message="继续持有"
        )


class SellSignalChecker:
    """卖出信号检查器（用于回测分析）"""
    
    def __init__(self, config: Optional[SellSignalGenerator] = None):
        self.generator = config or SellSignalGenerator()
        
    def analyze_trade(
        self,
        buy_price: float,
        buy_date: str,
        sell_price: float,
        sell_date: str,
        high_prices: list = None
    ) -> Dict:
        """
        分析一笔交易
        
        Returns:
            分析结果
        """
        hold_days = (pd.to_datetime(sell_date) - pd.to_datetime(buy_date)).days
        profit_ratio = (sell_price - buy_price) / buy_price
        
        # 确定卖出原因
        gap_up = (sell_price - buy_price) / buy_price >= self.generator.gap_up_threshold
        low_open = (buy_price - sell_price) / buy_price >= self.generator.low_open_threshold
        stop_loss = profit_ratio <= -self.generator.stop_loss
        time_stop = hold_days >= self.generator.max_hold_days
        
        if gap_up:
            reason = "高开卖出"
        elif low_open:
            reason = "低开止损"
        elif stop_loss:
            reason = "止损"
        elif time_stop:
            reason = "时间止损"
        else:
            reason = "其他"
        
        return {
            'buy_price': buy_price,
            'sell_price': sell_price,
            'buy_date': buy_date,
            'sell_date': sell_date,
            'hold_days': hold_days,
            'profit_ratio': profit_ratio,
            'profit_amount': sell_price - buy_price,
            'reason': reason
        }
    
    def batch_analyze(self, trades: list) -> Dict:
        """
        批量分析交易
        
        Args:
            trades: 交易列表，每笔交易包含 buy_price, sell_price, buy_date, sell_date
            
        Returns:
            汇总统计
        """
        results = [self.analyze_trade(**t) for t in trades]
        
        if not results:
            return {
                'total_trades': 0,
                'win_trades': 0,
                'lose_trades': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'total_profit': 0
            }
        
        win_trades = [r for r in results if r['profit_ratio'] > 0]
        lose_trades = [r for r in results if r['profit_ratio'] <= 0]
        
        return {
            'total_trades': len(results),
            'win_trades': len(win_trades),
            'lose_trades': len(lose_trades),
            'win_rate': len(win_trades) / len(results) if results else 0,
            'avg_profit': sum(r['profit_ratio'] for r in results) / len(results),
            'total_profit': sum(r['profit_amount'] for r in results),
            'best_trade': max(results, key=lambda x: x['profit_ratio']) if results else None,
            'worst_trade': min(results, key=lambda x: x['profit_ratio']) if results else None,
            'trades': results
        }


# 辅助函数
def calculate_profit(buy_price: float, sell_price: float, commission: float = 0.003) -> Dict:
    """
    计算交易收益
    
    Args:
        buy_price: 买入价
        sell_price: 卖出价
        commission: 手续费率（双边）
        
    Returns:
        收益详情
    """
    # 买入成本
    buy_cost = buy_price * (1 + commission)
    
    # 卖出收入
    sell_income = sell_price * (1 - commission)
    
    # 收益率
    profit_ratio = (sell_income - buy_cost) / buy_cost
    
    return {
        'buy_cost': buy_cost,
        'sell_income': sell_income,
        'profit_ratio': profit_ratio,
        'profit_ratio_no_commission': (sell_price - buy_price) / buy_price
    }


def simulate_next_day_open(
    buy_price: float,
    next_open_price: float
) -> Dict:
    """
    模拟次日开盘情况
    
    Returns:
        模拟结果
    """
    change_ratio = (next_open_price - buy_price) / buy_price
    
    if change_ratio >= 0.01:
        action = "高开卖出"
        actual_profit = calculate_profit(buy_price, next_open_price)
    elif change_ratio <= -0.02:
        action = "低开止损"
        actual_profit = calculate_profit(buy_price, next_open_price)
    else:
        action = "观望"
        actual_profit = calculate_profit(buy_price, next_open_price)
    
    return {
        'buy_price': buy_price,
        'next_open': next_open_price,
        'change_ratio': change_ratio,
        'action': action,
        **actual_profit
    }


if __name__ == "__main__":
    # 测试卖出信号
    
    # 场景1: 高开
    print("=== 场景1: 次日高开 ===")
    signal = SellSignalGenerator()
    result = signal.check_sell(
        current_price=11.5,     # 当日价格
        open_price=11.2,       # 次日开盘价
        buy_price=10.0,        # 买入价
        hold_days=1,           # 持仓1天（次日）
        is_next_day=True
    )
    print(f"是否卖出: {result.should_sell}")
    print(f"原因: {result.reason.value}")
    print(f"价格: {result.price}")
    print(f"收益率: {result.profit_ratio*100:.2f}%")
    
    # 场景2: 低开止损
    print("\n=== 场景2: 次日低开止损 ===")
    signal.reset()
    result = signal.check_sell(
        current_price=9.6,
        open_price=9.6,
        buy_price=10.0,
        hold_days=1,
        is_next_day=True
    )
    print(f"是否卖出: {result.should_sell}")
    print(f"原因: {result.reason.value}")
    print(f"价格: {result.price}")
    print(f"收益率: {result.profit_ratio*100:.2f}%")
    
    # 场景3: 盘中止损
    print("\n=== 场景3: 盘中止损 ===")
    signal.reset()
    result = signal.check_sell(
        current_price=9.7,
        open_price=10.1,
        buy_price=10.0,
        hold_days=1,
        is_next_day=False
    )
    print(f"是否卖出: {result.should_sell}")
    print(f"原因: {result.reason.value}")
    print(f"收益率: {result.profit_ratio*100:.2f}%")
