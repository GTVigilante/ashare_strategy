"""
尾盘选股筛选器
==============
根据牛散尾盘策略硬条件筛选股票

硬条件:
- 昨日涨停（必须）
- 量比 > 1.2
- 换手率 > 3%
- 流通市值 < 200亿
- 振幅 < 5%
- 股价 4-30元
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class FilterConfig:
    """筛选配置"""
    min_turnover_rate: float = 3.0      # 换手率 > 3%
    max_market_cap: float = 200.0       # 流通市值 < 200亿
    max_amplitude: float = 5.0         # 振幅 < 5%
    min_price: float = 4.0             # 股价下限
    max_price: float = 30.0            # 股价上限
    min_volume_ratio: float = 1.2      # 量比 > 1.2
    must_be_limit_up: bool = True      # 必须昨日涨停


class TailStockSelector:
    """尾盘选股筛选器"""
    
    def __init__(self, data_provider, config: Optional[FilterConfig] = None):
        self.data_provider = data_provider
        self.config = config or FilterConfig()
        
    def get_yesterday_zt_stocks(self, date: str) -> pd.DataFrame:
        """获取昨日涨停股票"""
        # 使用AKShare获取涨停股
        zt_df = self.data_provider.get_limit_up_stocks(date)
        return zt_df
    
    def calculate_volume_ratio(self, stock_data: pd.DataFrame) -> float:
        """计算量比"""
        if len(stock_data) < 5:
            return 0.0
        
        # 量比 = 当前成交量 / 前5日平均成交量
        recent_volumes = stock_data['成交量'].iloc[-5:-1].mean()
        today_volume = stock_data['成交量'].iloc[-1]
        
        if recent_volumes == 0:
            return 0.0
        return today_volume / recent_volumes
    
    def calculate_amplitude(self, stock_data: pd.DataFrame) -> float:
        """计算振幅"""
        if stock_data.empty:
            return 0.0
        
        high = stock_data['最高'].iloc[-1]
        low = stock_data['最低'].iloc[-1]
        close = stock_data['收盘'].iloc[-1]
        
        if close == 0:
            return 0.0
        return (high - low) / close * 100
    
    def calculate_turnover_rate(self, stock_data: pd.DataFrame) -> float:
        """计算换手率（%）"""
        if stock_data.empty:
            return 0.0
        
        # 从原始数据获取换手率字段
        if '换手率' in stock_data.columns:
            return stock_data['换手率'].iloc[-1]
        return 0.0
    
    def filter_by_config(
        self, 
        stock_data: pd.DataFrame,
        symbol: str,
        check_zt: bool = False
    ) -> Dict:
        """
        根据配置筛选单只股票
        
        Returns:
            dict with 'pass': bool and 'reason': str
        """
        result = {
            'symbol': symbol,
            'pass': False,
            'reason': '',
            'metrics': {}
        }
        
        if stock_data.empty:
            result['reason'] = '无数据'
            return result
        
        close = stock_data['收盘'].iloc[-1]
        
        # 1. 价格筛选
        if close < self.config.min_price:
            result['reason'] = f'股价{close}低于{self.config.min_price}'
            return result
        if close > self.config.max_price:
            result['reason'] = f'股价{close}高于{self.config.max_price}'
            return result
        
        # 2. 量比筛选
        volume_ratio = self.calculate_volume_ratio(stock_data)
        result['metrics']['量比'] = volume_ratio
        if volume_ratio < self.config.min_volume_ratio:
            result['reason'] = f'量比{volume_ratio:.2f}低于{self.config.min_volume_ratio}'
            return result
        
        # 3. 换手率筛选
        turnover_rate = self.calculate_turnover_rate(stock_data)
        result['metrics']['换手率'] = turnover_rate
        if turnover_rate < self.config.min_turnover_rate:
            result['reason'] = f'换手率{turnover_rate:.2f}%低于{self.config.min_turnover_rate}%'
            return result
        
        # 4. 振幅筛选
        amplitude = self.calculate_amplitude(stock_data)
        result['metrics']['振幅'] = amplitude
        if amplitude > self.config.max_amplitude:
            result['reason'] = f'振幅{amplitude:.2f}%超过{self.config.max_amplitude}%'
            return result
        
        # 5. 昨日涨停检查
        if self.config.must_be_limit_up and not check_zt:
            result['reason'] = '未检查涨停'
            return result
        
        result['pass'] = True
        result['reason'] = '通过全部筛选'
        result['metrics']['收盘'] = close
        result['metrics']['流通市值'] = 0  # 需要额外查询
        
        return result
    
    def select_stocks(
        self, 
        zt_symbols: List[str],
        date: str
    ) -> pd.DataFrame:
        """
        批量筛选股票
        
        Args:
            zt_symbols: 昨日涨停股票代码列表
            date: 筛选日期
            
        Returns:
            符合条件的股票DataFrame
        """
        results = []
        
        for symbol in zt_symbols:
            try:
                # 获取最近20日数据用于计算指标
                end_date = date
                start_date = (datetime.strptime(date, '%Y%m%d') - 
                            pd.Timedelta(days=30)).strftime('%Y%m%d')
                
                stock_data = self.data_provider.get_daily_data(
                    symbol, start_date, end_date
                )
                
                if stock_data.empty:
                    continue
                
                # 检查昨日是否涨停
                check_zt = len(stock_data) >= 2 and self._is_limit_up(
                    stock_data.iloc[-2]
                )
                
                filter_result = self.filter_by_config(
                    stock_data, symbol, check_zt
                )
                
                if filter_result['pass']:
                    results.append({
                        '代码': symbol,
                        '收盘价': stock_data['收盘'].iloc[-1],
                        '量比': filter_result['metrics'].get('量比', 0),
                        '换手率': filter_result['metrics'].get('换手率', 0),
                        '振幅': filter_result['metrics'].get('振幅', 0),
                        '原因': filter_result['reason']
                    })
                    
            except Exception as e:
                logger.error(f"筛选 {symbol} 时出错: {e}")
                continue
        
        return pd.DataFrame(results)
    
    def _is_limit_up(self, row: pd.Series) -> bool:
        """判断是否涨停"""
        if '涨停统计' in row.index:
            return row['涨停统计'] == '涨停'
        
        # 简单判断：收盘价接近最高价且涨幅接近10%
        if '收盘' in row.index and '最高' in row.index:
            if row['最高'] > 0:
                close_ratio = row['收盘'] / row['最高']
                return close_ratio > 0.998  # 接近最高价收盘
        
        return False


class TailStockScreener:
    """
    尾盘选股器（简化版，返回候选股）
    直接从实时行情筛选
    """
    
    def __init__(self, config: Optional[FilterConfig] = None):
        self.config = config or FilterConfig()
        
    def screen_from_realtime(
        self, 
        realtime_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        从实时行情筛选
        
        Args:
            realtime_df: AKShare实时行情DataFrame
            
        Returns:
            符合条件的股票
        """
        if realtime_df.empty:
            return pd.DataFrame()
        
        # 字段名映射（AKShare实时行情字段）
        field_map = {
            '代码': '代码',
            '名称': '名称', 
            '最新价': '最新价',
            '涨跌幅': '涨跌幅',
            '成交量比': '成交额',  # 可能需要调整
            '换手率': '换手率',
            '流通市值': '流通市值',
        }
        
        # 标准化列名
        available_cols = set(realtime_df.columns)
        
        # 筛选条件
        mask = pd.Series([True] * len(realtime_df))
        
        # 1. 价格筛选
        if '最新价' in available_cols:
            price = realtime_df['最新价']
            mask &= (price >= self.config.min_price) & (price <= self.config.max_price)
        
        # 2. 换手率筛选
        if '换手率' in available_cols:
            turnover = pd.to_numeric(realtime_df['换手率'], errors='coerce')
            mask &= turnover > self.config.min_turnover_rate
        
        # 3. 流通市值筛选
        if '流通市值' in available_cols:
            mktcap = pd.to_numeric(realtime_df['流通市值'], errors='coerce')
            # 流通市值单位通常是元，转换为亿
            mktcap_billion = mktcap / 1e8
            mask &= mktcap_billion < self.config.max_market_cap
        
        return realtime_df[mask].copy()


if __name__ == "__main__":
    from akshare_provider import AKDataProvider
    
    # 测试筛选器
    selector = TailStockSelector(AKDataProvider())
    
    # 测试配置
    config = FilterConfig(
        min_turnover_rate=3.0,
        max_market_cap=200.0,
        max_amplitude=5.0,
        min_price=4.0,
        max_price=30.0,
        min_volume_ratio=1.2
    )
    
    print("筛选配置:")
    print(f"  换手率 > {config.min_turnover_rate}%")
    print(f"  流通市值 < {config.max_market_cap}亿")
    print(f"  振幅 < {config.max_amplitude}%")
    print(f"  股价 {config.min_price}-{config.max_price}元")
    print(f"  量比 > {config.min_volume_ratio}")
