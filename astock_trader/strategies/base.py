"""
策略基类
所有策略必须继承此基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
import yaml
from pathlib import Path


@dataclass
class StrategyConfig:
    """策略配置基类"""
    name: str = ""
    description: str = ""
    enabled: bool = True
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StockSignal:
    """股票信号"""
    symbol: str           # 股票代码
    name: str              # 股票名称
    signal_type: str       # buy / sell / hold
    price: float          # 信号产生时的价格
    confidence: float      # 置信度 0-1
    reason: str           # 原因
    timestamp: datetime = field(default_factory=datetime.now)
    strategy: str = ""    # 策略名称


@dataclass
class BacktestResult:
    """回测结果"""
    strategy_name: str
    start_date: str
    end_date: str
    total_return: float       # 总收益率
    sharpe_ratio: float      # 夏普比率
    max_drawdown: float      # 最大回撤
    win_rate: float          # 胜率
    total_trades: int        # 总交易次数
    avg_profit: float        # 平均收益
    trades: List[Dict] = field(default_factory=list)


class BaseStrategy(ABC):
    """
    策略基类
    
    所有策略必须实现:
    - get_name(): 返回策略名称
    - get_config(): 返回策略配置
    - select_stocks(): 选股
    - generate_signals(): 生成交易信号
    - backtest(): 回测
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.name = self.get_name()
        self.params = self.get_params()
        
    @abstractmethod
    def get_name(self) -> str:
        """返回策略名称"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """返回策略描述"""
        pass
    
    def get_params(self) -> Dict:
        """返回策略参数"""
        return self.config.get('params', {})
    
    @abstractmethod
    def select_stocks(
        self, 
        data: Any, 
        date: str
    ) -> List[StockSignal]:
        """
        选股
        
        Args:
            data: 股票数据
            date: 日期
            
        Returns:
            候选股票列表
        """
        pass
    
    @abstractmethod
    def generate_signals(
        self,
        stock_data: Any,
        current_date: str
    ) -> Optional[StockSignal]:
        """
        生成交易信号
        
        Args:
            stock_data: 股票数据
            current_date: 当前日期
            
        Returns:
            交易信号
        """
        pass
    
    def backtest(
        self,
        data: Any,
        start_date: str,
        end_date: str,
        initial_cash: float = 100000
    ) -> BacktestResult:
        """
        回测策略
        
        Args:
            data: 历史数据
            start_date: 开始日期
            end_date: 结束日期
            initial_cash: 初始资金
            
        Returns:
            回测结果
        """
        # 子类实现具体回测逻辑
        raise NotImplementedError
    
    def validate_params(self) -> bool:
        """验证参数是否有效"""
        return True
    
    @classmethod
    def load_from_config(cls, config_path: Path, strategy_name: str) -> 'BaseStrategy':
        """
        从配置文件加载策略
        
        Args:
            config_path: 配置文件路径
            strategy_name: 策略名称
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        strategies = config.get('strategies', {})
        if strategy_name not in strategies:
            raise ValueError(f"策略 {strategy_name} 不存在")
        
        return cls(config=strategies[strategy_name])
    
    def save_params(self, config_path: Path):
        """保存参数到配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if 'strategies' not in config:
            config['strategies'] = {}
        
        config['strategies'][self.name] = {
            'name': self.name,
            'description': self.get_description(),
            'enabled': self.params.get('enabled', True),
            'params': self.params
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)


class StrategyRegistry:
    """策略注册表"""
    
    _strategies: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, strategy_class: type):
        """注册策略"""
        cls._strategies[name] = strategy_class
    
    @classmethod
    def get(cls, name: str) -> Optional[type]:
        """获取策略类"""
        return cls._strategies.get(name)
    
    @classmethod
    def list_strategies(cls) -> List[str]:
        """列出所有已注册策略"""
        return list(cls._strategies.keys())
    
    @classmethod
    def create(cls, name: str, config: Dict = None) -> BaseStrategy:
        """创建策略实例"""
        strategy_class = cls.get(name)
        if not strategy_class:
            raise ValueError(f"策略 {name} 未注册")
        return strategy_class(config)
