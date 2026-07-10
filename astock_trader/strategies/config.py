"""
策略配置加载器
"""

import yaml
from pathlib import Path
from typing import Dict

# 获取配置路径
CONFIG_PATH = Path(__file__).parent / 'config.yaml'


def load_strategy_config() -> Dict:
    """加载策略配置"""
    if not CONFIG_PATH.exists():
        return {}
    
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_strategy_params(strategy_name: str) -> Dict:
    """获取指定策略的参数"""
    config = load_strategy_config()
    strategies = config.get('strategies', {})
    
    if strategy_name in strategies:
        return strategies[strategy_name].get('params', {})
    
    return {}


def get_backtest_config() -> Dict:
    """获取回测配置"""
    config = load_strategy_config()
    return config.get('backtest', {})
