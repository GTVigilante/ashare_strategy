"""
配置文件加载器
"""

import configparser
from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class Config:
    """完整配置"""
    # 选股配置
    min_turnover_rate: float = 3.0
    max_market_cap: float = 200.0
    max_amplitude: float = 5.0
    min_price: float = 4.0
    max_price: float = 30.0
    min_volume_ratio: float = 1.2
    must_be_limit_up: bool = True
    
    # 技术指标
    require_ma_bullish: bool = True
    require_macd_golden: bool = True
    require_breakout: bool = False
    
    # 买入设置
    buy_time_hour: int = 14
    buy_time_minute: int = 30
    position_size: float = 0.95
    
    # 卖出设置
    sell_on_gap_up: bool = True
    gap_up_threshold: float = 0.01
    low_open_stop: float = 0.02
    stop_loss: float = 0.03
    max_hold_days: int = 3
    
    # 回测设置
    initial_cash: float = 100000
    commission: float = 0.003
    slippage: float = 0.005


def load_config(config_path: str = None) -> Config:
    """从配置文件加载"""
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(__file__), 
            'config.ini'
        )
    
    config = Config()
    
    if os.path.exists(config_path):
        parser = configparser.ConfigParser()
        parser.read(config_path)
        
        # 读取选股配置
        if 'filter' in parser:
            config.min_turnover_rate = parser.getfloat('filter', 'min_turnover_rate', fallback=3.0)
            config.max_market_cap = parser.getfloat('filter', 'max_market_cap', fallback=200.0)
            config.max_amplitude = parser.getfloat('filter', 'max_amplitude', fallback=5.0)
            config.min_price = parser.getfloat('filter', 'min_price', fallback=4.0)
            config.max_price = parser.getfloat('filter', 'max_price', fallback=30.0)
            config.min_volume_ratio = parser.getfloat('filter', 'min_volume_ratio', fallback=1.2)
            config.must_be_limit_up = parser.getboolean('filter', 'must_be_limit_up', fallback=True)
        
        # 读取技术指标配置
        if 'technical' in parser:
            config.require_ma_bullish = parser.getboolean('technical', 'require_ma_bullish', fallback=True)
            config.require_macd_golden = parser.getboolean('technical', 'require_macd_golden', fallback=True)
            config.require_breakout = parser.getboolean('technical', 'require_breakout', fallback=False)
        
        # 读取买入设置
        if 'buy' in parser:
            config.buy_time_hour = parser.getint('buy', 'buy_time_hour', fallback=14)
            config.buy_time_minute = parser.getint('buy', 'buy_time_minute', fallback=30)
            config.position_size = parser.getfloat('buy', 'position_size', fallback=0.95)
        
        # 读取卖出设置
        if 'sell' in parser:
            config.sell_on_gap_up = parser.getboolean('sell', 'sell_on_gap_up', fallback=True)
            config.gap_up_threshold = parser.getfloat('sell', 'gap_up_threshold', fallback=0.01)
            config.low_open_stop = parser.getfloat('sell', 'low_open_stop', fallback=0.02)
            config.stop_loss = parser.getfloat('sell', 'stop_loss', fallback=0.03)
            config.max_hold_days = parser.getint('sell', 'max_hold_days', fallback=3)
        
        # 读取回测设置
        if 'backtest' in parser:
            config.initial_cash = parser.getfloat('backtest', 'initial_cash', fallback=100000)
            config.commission = parser.getfloat('backtest', 'commission', fallback=0.003)
            config.slippage = parser.getfloat('backtest', 'slippage', fallback=0.005)
    
    return config


if __name__ == "__main__":
    # 测试配置加载
    config = load_config()
    print("当前配置:")
    print(f"  换手率 > {config.min_turnover_rate}%")
    print(f"  流通市值 < {config.max_market_cap}亿")
    print(f"  振幅 < {config.max_amplitude}%")
    print(f"  股价 {config.min_price}-{config.max_price}元")
    print(f"  量比 > {config.min_volume_ratio}")
    print(f"  均线多头: {config.require_ma_bullish}")
    print(f"  MACD金叉: {config.require_macd_golden}")
