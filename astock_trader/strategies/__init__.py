"""
策略模块
"""

from .base import BaseStrategy, StockSignal, BacktestResult, StrategyRegistry, StrategyConfig
from .tail_strategy import TailStrategy

__all__ = [
    'BaseStrategy',
    'StockSignal', 
    'BacktestResult',
    'StrategyRegistry',
    'StrategyConfig',
    'TailStrategy'
]
