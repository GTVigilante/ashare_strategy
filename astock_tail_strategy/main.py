"""
尾盘选股策略主程序
================
整合选股、指标分析和回测的完整流程

使用方式:
    python main.py --symbol 000001 --start 20240101 --end 20240630
    python main.py --screen --date 20240628
    python main.py --backtest --symbols 000001,000002 --start 20240101 --end 20240630
"""

import argparse
import logging
from datetime import datetime
from typing import List, Dict

from data.akshare_provider import AKDataProvider
from stock_selectors.tail_stock_selector import TailStockSelector, FilterConfig
from indicators.technical_indicators import TechnicalAnalyzer
from strategies.sell_signals import SellSignalGenerator
from backtest.backtrader_engine import BacktestEngine, StrategyConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TailStockStrategy:
    """尾盘策略完整流程"""
    
    def __init__(
        self,
        selector_config: FilterConfig = None,
        strategy_config: StrategyConfig = None
    ):
        self.data_provider = AKDataProvider()
        self.selector = TailStockSelector(self.data_provider, selector_config)
        self.analyzer = TechnicalAnalyzer()
        self.strategy_config = strategy_config or StrategyConfig()
        self.sell_generator = SellSignalGenerator(
            gap_up_threshold=self.strategy_config.gap_up_threshold,
            low_open_threshold=self.strategy_config.low_open_stop,
            stop_loss=self.strategy_config.stop_loss,
            max_hold_days=self.strategy_config.max_hold_days
        )
    
    def screen(self, date: str) -> List[Dict]:
        """
        筛选候选股票
        
        Args:
            date: 日期 'YYYYMMDD'
            
        Returns:
            符合条件的股票列表
        """
        logger.info(f"开始筛选 {date} 的候选股票...")
        
        # 获取昨日涨停股票
        zt_stocks = self.data_provider.get_limit_up_stocks(date)
        
        if zt_stocks.empty:
            logger.info("未找到涨停股票")
            return []
        
        zt_symbols = zt_stocks['代码'].tolist()[:20]  # 限制数量
        logger.info(f"昨日涨停股票数量: {len(zt_symbols)}")
        
        # 筛选
        candidates = self.selector.select_stocks(zt_symbols, date)
        
        logger.info(f"通过筛选的候选股票: {len(candidates)}")
        
        # 技术分析
        results = []
        for _, row in candidates.iterrows():
            symbol = row['代码']
            
            try:
                # 获取数据
                end_date = date
                start_date = (datetime.strptime(date, '%Y%m%d') - 
                            datetime.timedelta(days=60)).strftime('%Y%m%d')
                
                data = self.data_provider.get_daily_data(symbol, start_date, end_date)
                
                if data.empty or len(data) < 30:
                    continue
                
                # 技术分析
                tech_result = self.analyzer.analyze(
                    data,
                    require_ma_bullish=self.strategy_config.require_ma_bullish,
                    require_macd_golden=self.strategy_config.require_macd_golden,
                    require_breakout=self.strategy_config.require_breakout
                )
                
                stock_info = {
                    '代码': symbol,
                    '收盘价': row.get('收盘价', 0),
                    '量比': row.get('量比', 0),
                    '换手率': row.get('换手率', 0),
                    '振幅': row.get('振幅', 0),
                    '均线多头': tech_result['signals'].get('均线多头', False),
                    'MACD金叉': tech_result['signals'].get('MACD金叉', False),
                    '平台突破': tech_result['signals'].get('平台突破', False),
                    '技术通过': tech_result['pass']
                }
                
                results.append(stock_info)
                
            except Exception as e:
                logger.error(f"分析 {symbol} 时出错: {e}")
                continue
        
        # 按技术指标排序
        results.sort(key=lambda x: (
            x['技术通过'],
            x['均线多头'],
            x['MACD金叉'],
            x['量比']
        ), reverse=True)
        
        return results
    
    def backtest_single(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Dict:
        """
        单只股票回测
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            回测结果
        """
        logger.info(f"回测 {symbol} 从 {start_date} 到 {end_date}...")
        
        # 获取数据
        data = self.data_provider.get_daily_data(symbol, start_date, end_date)
        
        if data.empty:
            return {'error': '无数据'}
        
        # 创建回测引擎
        engine = BacktestEngine(
            initial_cash=100000,
            config=self.strategy_config
        )
        
        # 添加数据
        engine.add_data(data, name=symbol)
        
        # 运行回测
        results = engine.run()
        results['symbol'] = symbol
        
        return results
    
    def backtest_batch(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """
        批量回测
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            回测结果列表
        """
        logger.info(f"批量回测 {len(symbols)} 只股票...")
        
        results = []
        for symbol in symbols:
            try:
                result = self.backtest_single(symbol, start_date, end_date)
                results.append(result)
            except Exception as e:
                logger.error(f"回测 {symbol} 出错: {e}")
                continue
        
        return results


def main():
    parser = argparse.ArgumentParser(description='A股尾盘策略')
    
    # 操作模式
    parser.add_argument('--screen', action='store_true', help='筛选候选股票')
    parser.add_argument('--backtest', action='store_true', help='运行回测')
    parser.add_argument('--symbol', type=str, help='单只股票代码')
    parser.add_argument('--symbols', type=str, help='逗号分隔的股票代码')
    
    # 日期参数
    parser.add_argument('--date', type=str, default=None, help='筛选日期 YYYYMMDD')
    parser.add_argument('--start', type=str, default='20240101', help='回测开始日期')
    parser.add_argument('--end', type=str, default=None, help='回测结束日期')
    
    # 配置参数
    parser.add_argument('--initial-cash', type=float, default=100000, help='初始资金')
    parser.add_argument('--no-ma', action='store_true', help='不要求均线多头')
    parser.add_argument('--no-macd', action='store_true', help='不要求MACD金叉')
    
    args = parser.parse_args()
    
    # 默认日期设置
    if args.date is None:
        args.date = datetime.now().strftime('%Y%m%d')
    if args.end is None:
        args.end = datetime.now().strftime('%Y%m%d')
    
    # 创建策略配置
    strategy_config = StrategyConfig(
        require_ma_bullish=not args.no_ma,
        require_macd_golden=not args.no_macd
    )
    
    # 创建策略实例
    strategy = TailStockStrategy(strategy_config=strategy_config)
    
    if args.screen:
        # 筛选模式
        results = strategy.screen(args.date)
        
        print(f"\n{'='*60}")
        print(f"筛选结果 - {args.date}")
        print(f"{'='*60}")
        
        if results:
            for i, stock in enumerate(results[:10], 1):
                print(f"\n{i}. {stock['代码']}")
                print(f"   收盘价: {stock['收盘价']:.2f}")
                print(f"   量比: {stock['量比']:.2f}")
                print(f"   换手率: {stock['换手率']:.2f}%")
                print(f"   均线多头: {'✓' if stock['均线多头'] else '✗'}")
                print(f"   MACD金叉: {'✓' if stock['MACD金叉'] else '✗'}")
                print(f"   技术通过: {'✓' if stock['技术通过'] else '✗'}")
        else:
            print("无符合条件的股票")
    
    elif args.backtest:
        # 回测模式
        symbols = []
        if args.symbol:
            symbols = [args.symbol]
        elif args.symbols:
            symbols = args.symbols.split(',')
        else:
            print("请指定 --symbol 或 --symbols")
            return
        
        if len(symbols) == 1:
            # 单只股票回测
            result = strategy.backtest_single(symbols[0], args.start, args.end)
            
            print(f"\n{'='*60}")
            print(f"回测结果 - {symbols[0]}")
            print(f"{'='*60}")
            print(f"初始资金: {result.get('initial_cash', 0):.2f}")
            print(f"最终资金: {result.get('final_value', 0):.2f}")
            print(f"总收益率: {result.get('total_return', 0)*100:.2f}%")
            print(f"夏普比率: {result.get('sharpe_ratio', 'N/A')}")
            print(f"最大回撤: {result.get('max_drawdown', 0):.2f}%")
        else:
            # 批量回测
            results = strategy.backtest_batch(symbols, args.start, args.end)
            
            print(f"\n{'='*60}")
            print(f"批量回测结果 - {len(symbols)} 只股票")
            print(f"{'='*60}")
            
            for result in results:
                if 'error' in result:
                    continue
                print(f"\n{result['symbol']}:")
                print(f"  收益率: {result.get('total_return', 0)*100:.2f}%")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
