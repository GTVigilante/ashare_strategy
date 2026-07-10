"""
AKShare 数据获取模块
===================
提供A股实时和历史数据获取功能
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class AKDataProvider:
    """AKShare 数据提供者"""
    
    def __init__(self):
        self.cache = {}  # 简单缓存
        
    def get_realtime_quotes(self) -> pd.DataFrame:
        """获取实时行情（全部A股）"""
        try:
            df = ak.stock_zh_a_spot_em()
            return df
        except Exception as e:
            logger.error(f"获取实时行情失败: {e}")
            return pd.DataFrame()
    
    def get_daily_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取日线数据
        
        Args:
            symbol: 股票代码，如 '000001'
            start_date: 开始日期 'YYYYMMDD'
            end_date: 结束日期 'YYYYMMDD'
        """
        cache_key = f"{symbol}_{start_date}_{end_date}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # 统一格式：沪市加前缀 sh，深市加前缀 sz
            if symbol.startswith('6'):
                symbol_code = f"sh{symbol}"
            else:
                symbol_code = f"sz{symbol}"
            
            df = ak.stock_zh_a_hist(
                symbol=symbol, 
                period="daily", 
                start_date=start_date, 
                end_date=end_date, 
                adjust="qfq"
            )
            
            if not df.empty:
                df['日期'] = pd.to_datetime(df['日期'])
                df.set_index('日期', inplace=True)
                self.cache[cache_key] = df
            return df
        except Exception as e:
            logger.error(f"获取日线数据失败 {symbol}: {e}")
            return pd.DataFrame()
    
    def get_realtime_data(self, symbol: str) -> Dict:
        """获取单只股票实时数据"""
        try:
            df = ak.stock_zh_a_spot_em()
            stock = df[df['代码'] == symbol]
            if not stock.empty:
                return stock.iloc[0].to_dict()
            return {}
        except Exception as e:
            logger.error(f"获取实时数据失败 {symbol}: {e}")
            return {}
    
    def get_limit_up_stocks(self, date: str) -> pd.DataFrame:
        """
        获取涨停股票列表
        
        Args:
            date: 日期 'YYYYMMDD'
        """
        try:
            df = ak.stock_zt_pool_em(date=date)
            # 筛选涨停股票
            zt = df[df['涨停统计'] == '涨停']
            return zt
        except Exception as e:
            logger.error(f"获取涨停股票失败 {date}: {e}")
            return pd.DataFrame()
    
    def get_stock_info(self, symbol: str) -> Dict:
        """获取股票基本信息"""
        try:
            df = ak.stock_individual_info_em(symbol=symbol)
            info = dict(zip(df['item'], df['value']))
            return info
        except Exception as e:
            logger.error(f"获取股票信息失败 {symbol}: {e}")
            return {}
    
    def get_market_cap(self, symbol: str) -> Optional[float]:
        """获取流通市值（亿元）"""
        try:
            info = self.get_stock_info(symbol)
            # 尝试从信息中提取流通市值
            for key, value in info.items():
                if '流通' in key and '市值' in key:
                    # 尝试解析数值
                    value_str = str(value).replace(',', '')
                    if '亿' in value_str:
                        return float(value_str.replace('亿', ''))
                    elif '万' in value_str:
                        return float(value_str.replace('万', '')) / 10000
            return None
        except Exception as e:
            logger.error(f"获取流通市值失败 {symbol}: {e}")
            return None


def get_stock_basics() -> pd.DataFrame:
    """获取A股股票基本信息（全局函数，方便调用）"""
    try:
        df = ak.stock_info_a_code_name()
        return df
    except Exception as e:
        logger.error(f"获取股票基本信息失败: {e}")
        return pd.DataFrame()


if __name__ == "__main__":
    # 测试数据获取
    provider = AKDataProvider()
    
    # 测试1: 获取今日涨停股票
    today = datetime.now().strftime('%Y%m%d')
    print(f"获取 {today} 涨停股票...")
    zt_stocks = provider.get_limit_up_stocks(today)
    print(f"涨停股票数量: {len(zt_stocks)}")
    
    # 测试2: 获取单只股票日线数据
    print("\n获取平安银行日线数据...")
    data = provider.get_daily_data('000001', '20240101', '20240630')
    if not data.empty:
        print(f"数据行数: {len(data)}")
        print(data.tail())
