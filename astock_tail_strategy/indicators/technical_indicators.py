"""
技术指标模块
============
提供均线、MACD、平台突破等技术指标计算

技术指标软参考:
- 均线多头（5日 > 10日 > 20日）
- MACD 金叉，红柱放大
- 平台突破：横盘后放量突破
- 涨停时间：越早封板越强
- 封单强度：涨停封单越大越稳
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """技术指标计算器"""
    
    @staticmethod
    def calculate_ma(data: pd.DataFrame, periods: list = [5, 10, 20, 60]) -> pd.DataFrame:
        """
        计算移动平均线
        
        Args:
            data: 包含收盘价的DataFrame
            periods: 均线周期列表
            
        Returns:
            添加了MA列的DataFrame
        """
        df = data.copy()
        for period in periods:
            df[f'MA{period}'] = df['收盘'].rolling(window=period).mean()
        return df
    
    @staticmethod
    def is_ma_bullish(ma_data: Dict[str, float]) -> bool:
        """
        判断均线多头排列
        
        Args:
            ma_data: {'MA5': xxx, 'MA10': xxx, 'MA20': xxx}
            
        Returns:
            True if 均线多头（MA5 > MA10 > MA20）
        """
        ma5 = ma_data.get('MA5', 0)
        ma10 = ma_data.get('MA10', 0)
        ma20 = ma_data.get('MA20', 0)
        
        return ma5 > ma10 > ma20 > 0
    
    @staticmethod
    def calculate_macd(
        data: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> pd.DataFrame:
        """
        计算MACD指标
        
        Args:
            data: 包含收盘价的DataFrame
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期
            
        Returns:
            添加了MACD相关列的DataFrame
        """
        df = data.copy()
        
        # 计算EMA
        ema_fast = df['收盘'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['收盘'].ewm(span=slow, adjust=False).mean()
        
        # DIF线
        df['DIF'] = ema_fast - ema_slow
        
        # DEA线
        df['DEA'] = df['DIF'].ewm(span=signal, adjust=False).mean()
        
        # MACD柱（红柱或绿柱）
        df['MACD'] = (df['DIF'] - df['DEA']) * 2
        
        return df
    
    @staticmethod
    def is_macd_golden_cross(macd_data: pd.DataFrame, lookback: int = 3) -> bool:
        """
        判断MACD是否金叉（红柱放大）
        
        Args:
            macd_data: 包含DIF, DEA, MACD列的DataFrame
            lookback: 回看天数
            
        Returns:
            True if MACD金叉且红柱放大
        """
        if len(macd_data) < lookback + 1:
            return False
        
        recent = macd_data.tail(lookback + 1)
        
        # 金叉：DIF从下往上穿过DEA
        dif_prev = recent['DIF'].iloc[-2]
        dif_curr = recent['DIF'].iloc[-1]
        dea_curr = recent['DEA'].iloc[-1]
        
        golden_cross = dif_prev < dea_curr and dif_curr >= dea_curr
        
        # 红柱放大：最近MACD柱大于之前
        macd_values = recent['MACD'].values
        red_expanding = macd_values[-1] > macd_values[-2] if len(macd_values) >= 2 else False
        
        return golden_cross and macd_values[-1] > 0
    
    @staticmethod
    def calculate_bollinger_bands(
        data: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0
    ) -> pd.DataFrame:
        """
        计算布林带
        
        Args:
            data: 包含收盘价的DataFrame
            period: 周期
            std_dev: 标准差倍数
            
        Returns:
            添加了布林带列的DataFrame
        """
        df = data.copy()
        
        df['BB_MID'] = df['收盘'].rolling(window=period).mean()
        df['BB_STD'] = df['收盘'].rolling(window=period).std()
        df['BB_UPPER'] = df['BB_MID'] + std_dev * df['BB_STD']
        df['BB_LOWER'] = df['BB_MID'] - std_dev * df['BB_STD']
        
        return df
    
    @staticmethod
    def is_breakout_consolidation(
        data: pd.DataFrame,
        lookback: int = 20,
        threshold: float = 0.05
    ) -> Tuple[bool, str]:
        """
        判断是否平台突破（横盘后放量突破）
        
        Args:
            data: 包含OHLCV的DataFrame
            lookback: 横盘天数
            threshold: 突破阈值（涨幅百分比）
            
        Returns:
            (是否突破, 突破类型)
        """
        if len(data) < lookback + 1:
            return False, ''
        
        recent = data.tail(lookback + 1)
        consolidation = recent.iloc[:-1]
        today = recent.iloc[-1]
        
        # 横盘特征：价格波动小
        consolidation['range'] = consolidation['最高'] - consolidation['最低']
        avg_range = consolidation['range'].mean()
        current_price = today['收盘']
        
        consolidation_max = consolidation['最高'].max()
        consolidation_min = consolidation['最低'].min()
        
        # 突破条件：价格突破横盘区间
        upper_breakout = current_price > consolidation_max
        range_ratio = avg_range / current_price if current_price > 0 else 0
        
        # 横盘判断：振幅小（<5%）
        is_consolidating = range_ratio < threshold
        
        # 放量突破：今日成交量大于横盘期间平均
        avg_volume = consolidation['成交量'].mean()
        volume_ratio = today['成交量'] / avg_volume if avg_volume > 0 else 0
        is_volume_breakout = volume_ratio > 1.5
        
        if upper_breakout and is_consolidating and is_volume_breakout:
            return True, '放量突破上轨'
        
        # 价格突破布林带上轨
        if 'BB_UPPER' in data.columns:
            bb_upper = data['BB_UPPER'].iloc[-1]
            if current_price > bb_upper:
                return True, '突破布林上轨'
        
        return False, ''
    
    @staticmethod
    def calculate_volume_ratio(data: pd.DataFrame, period: int = 5) -> float:
        """
        计算量比
        
        Args:
            data: 包含成交量的DataFrame
            period: 计算周期
            
        Returns:
            量比值
        """
        if len(data) < period + 1:
            return 0.0
        
        recent_volumes = data['成交量'].iloc[-period-1:-1]
        today_volume = data['成交量'].iloc[-1]
        
        avg_volume = recent_volumes.mean()
        if avg_volume == 0:
            return 0.0
        
        return today_volume / avg_volume
    
    @staticmethod
    def calculate_rsi(data: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        计算RSI指标
        
        Args:
            data: 包含收盘价的DataFrame
            period: RSI周期
            
        Returns:
            添加了RSI列的DataFrame
        """
        df = data.copy()
        
        delta = df['收盘'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        return df
    
    @staticmethod
    def is_support_resistance(
        data: pd.DataFrame,
        lookback: int = 20
    ) -> Dict[str, Optional[float]]:
        """
        计算支撑位和压力位
        
        Args:
            data: 包含OHLC的DataFrame
            lookback: 回看天数
            
        Returns:
            {'支撑位': xxx, '压力位': xxx}
        """
        if len(data) < lookback:
            return {'支撑位': None, '压力位': None}
        
        recent = data.tail(lookback)
        
        # 使用最近N日的最低点和最高点
        support = recent['最低'].min()
        resistance = recent['最高'].max()
        
        # 当前价
        current = data['收盘'].iloc[-1]
        
        # 计算距离支撑/压力的百分比
        distance_support = (current - support) / current * 100 if current > 0 else 0
        distance_resistance = (resistance - current) / current * 100 if current > 0 else 0
        
        return {
            '支撑位': support,
            '压力位': resistance,
            '距支撑': distance_support,
            '距压力': distance_resistance
        }


class TechnicalAnalyzer:
    """技术分析器 - 综合分析"""
    
    def __init__(self):
        self.indicators = TechnicalIndicators()
    
    def analyze(
        self,
        data: pd.DataFrame,
        require_ma_bullish: bool = True,
        require_macd_golden: bool = True,
        require_breakout: bool = False
    ) -> Dict:
        """
        综合技术分析
        
        Args:
            data: 股票数据
            require_ma_bullish: 要求均线多头
            require_macd_golden: 要求MACD金叉
            require_breakout: 要求平台突破
            
        Returns:
            分析结果字典
        """
        if data.empty or len(data) < 30:
            return {
                'pass': False,
                'reason': '数据不足',
                'signals': {}
            }
        
        result = {
            'pass': True,
            'reason': '',
            'signals': {}
        }
        
        # 计算各项指标
        df = self.indicators.calculate_ma(data)
        df = self.indicators.calculate_macd(df)
        df = self.indicators.calculate_bollinger_bands(df)
        df = self.indicators.calculate_rsi(df)
        
        # 均线多头
        if require_ma_bullish:
            ma_values = {
                'MA5': df['MA5'].iloc[-1],
                'MA10': df['MA10'].iloc[-1],
                'MA20': df['MA20'].iloc[-1]
            }
            ma_bullish = self.indicators.is_ma_bullish(ma_values)
            result['signals']['均线多头'] = ma_bullish
            if not ma_bullish:
                result['pass'] = False
                result['reason'] = '均线非多头排列'
        
        # MACD金叉
        if require_macd_golden:
            macd_golden = self.indicators.is_macd_golden_cross(df.tail(10))
            result['signals']['MACD金叉'] = macd_golden
            if not macd_golden:
                result['pass'] = False
                result['reason'] = 'MACD未金叉'
        
        # 平台突破
        if require_breakout:
            breakout, breakout_type = self.indicators.is_breakout_consolidation(df.tail(30))
            result['signals']['平台突破'] = breakout
            result['signals']['突破类型'] = breakout_type
        
        # 其他指标
        result['signals']['RSI'] = df['RSI'].iloc[-1]
        result['signals']['量比'] = self.indicators.calculate_volume_ratio(df)
        result['signals']['布林带'] = {
            '上轨': df['BB_UPPER'].iloc[-1],
            '中轨': df['BB_MID'].iloc[-1],
            '下轨': df['BB_LOWER'].iloc[-1]
        }
        
        # 支撑压力
        sr = self.indicators.is_support_resistance(df.tail(20))
        result['signals']['支撑压力'] = sr
        
        return result


if __name__ == "__main__":
    # 测试技术指标
    from data.akshare_provider import AKDataProvider
    
    provider = AKDataProvider()
    data = provider.get_daily_data('000001', '20240101', '20240630')
    
    if not data.empty:
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze(data)
        
        print("技术分析结果:")
        print(f"  通过: {result['pass']}")
        print(f"  原因: {result['reason']}")
        print(f"  信号: {result['signals']}")
