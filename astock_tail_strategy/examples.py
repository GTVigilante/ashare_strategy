"""
完整使用示例
============

本文件展示如何使用尾盘策略框架进行选股和回测
"""

from datetime import datetime, timedelta
import pandas as pd

# 导入框架模块
from data.akshare_provider import AKDataProvider
from stock_selectors.tail_stock_selector import TailStockSelector, FilterConfig
from indicators.technical_indicators import TechnicalAnalyzer
from strategies.sell_signals import SellSignalGenerator, simulate_next_day_open
from backtest.backtrader_engine import BacktestEngine, StrategyConfig


def example_screening():
    """示例：筛选候选股票"""
    print("=" * 60)
    print("示例1: 筛选候选股票")
    print("=" * 60)
    
    # 创建数据提供者
    provider = AKDataProvider()
    
    # 创建筛选器配置
    filter_config = FilterConfig(
        min_turnover_rate=3.0,      # 换手率 > 3%
        max_market_cap=200.0,       # 流通市值 < 200亿
        max_amplitude=5.0,          # 振幅 < 5%
        min_price=4.0,              # 股价下限
        max_price=30.0,            # 股价上限
        min_volume_ratio=1.2,       # 量比 > 1.2
        must_be_limit_up=True       # 必须昨日涨停
    )
    
    # 创建筛选器
    selector = TailStockSelector(provider, filter_config)
    
    # 筛选日期（使用最近交易日）
    date = "20240628"  # 可以改为 datetime.now().strftime('%Y%m%d')
    
    # 获取涨停股票
    zt_stocks = provider.get_limit_up_stocks(date)
    print(f"昨日涨停股票数量: {len(zt_stocks)}")
    
    # 筛选（这里演示逻辑，实际需要批量处理）
    for _, row in zt_stocks.head(5).iterrows():
        symbol = row.get('代码', '')
        name = row.get('名称', '')
        print(f"  {symbol} - {name}")


def example_technical_analysis():
    """示例：技术分析"""
    print("\n" + "=" * 60)
    print("示例2: 技术分析")
    print("=" * 60)
    
    provider = AKDataProvider()
    analyzer = TechnicalAnalyzer()
    
    # 获取股票数据
    symbol = '000001'  # 平安银行
    data = provider.get_daily_data(symbol, '20240101', '20240630')
    
    if not data.empty:
        # 综合技术分析
        result = analyzer.analyze(
            data,
            require_ma_bullish=True,
            require_macd_golden=True,
            require_breakout=False
        )
        
        print(f"\n技术分析结果 - {symbol}")
        print(f"  通过: {'✓' if result['pass'] else '✗'}")
        print(f"  原因: {result['reason']}")
        print(f"  均线多头: {'✓' if result['signals'].get('均线多头') else '✗'}")
        print(f"  MACD金叉: {'✓' if result['signals'].get('MACD金叉') else '✗'}")
        print(f"  RSI: {result['signals'].get('RSI', 0):.2f}")
        print(f"  量比: {result['signals'].get('量比', 0):.2f}")


def example_sell_signals():
    """示例：卖出信号分析"""
    print("\n" + "=" * 60)
    print("示例3: 卖出信号分析")
    print("=" * 60)
    
    # 模拟次日开盘情况
    buy_price = 10.0
    next_open_price = 10.5
    
    result = simulate_next_day_open(buy_price, next_open_price)
    
    print(f"\n买入价: {result['buy_price']:.2f}")
    print(f"次日开盘: {result['next_open']:.2f}")
    print(f"开盘涨幅: {result['change_ratio']*100:.2f}%")
    print(f"建议操作: {result['action']}")
    print(f"实际收益(含手续费): {result['profit_ratio']*100:.2f}%")


def example_backtest():
    """示例：单只股票回测"""
    print("\n" + "=" * 60)
    print("示例4: 单只股票回测")
    print("=" * 60)
    
    provider = AKDataProvider()
    
    # 策略配置
    strategy_config = StrategyConfig(
        require_ma_bullish=True,
        require_macd_golden=True,
        require_breakout=False,
        buy_time_hour=14,
        buy_time_minute=30,
        sell_on_gap_up=True,
        gap_up_threshold=0.01,
        low_open_stop=0.02,
        stop_loss=0.03,
        max_hold_days=3
    )
    
    # 创建回测引擎
    engine = BacktestEngine(
        initial_cash=100000,
        config=strategy_config
    )
    
    # 获取数据
    symbol = '000001'
    data = provider.get_daily_data(symbol, '20240101', '20240630')
    
    if not data.empty:
        # 添加数据
        engine.add_data(data, name=symbol)
        
        # 运行回测
        results = engine.run()
        
        print(f"\n回测结果 - {symbol}")
        print(f"  初始资金: {results.get('initial_cash', 0):.2f}")
        print(f"  最终资金: {results.get('final_value', 0):.2f}")
        print(f"  总收益率: {results.get('total_return', 0)*100:.2f}%")
        print(f"  夏普比率: {results.get('sharpe_ratio', 'N/A')}")
        print(f"  最大回撤: {results.get('max_drawdown', 0):.2f}%")


def example_batch_backtest():
    """示例：批量回测"""
    print("\n" + "=" * 60)
    print("示例5: 批量回测")
    print("=" * 60)
    
    from main import TailStockStrategy
    
    # 创建策略实例
    strategy = TailStockStrategy()
    
    # 回测股票列表
    symbols = ['000001', '000002', '600000']
    start_date = '20240101'
    end_date = '20240630'
    
    # 批量回测
    results = strategy.backtest_batch(symbols, start_date, end_date)
    
    print(f"\n批量回测结果:")
    total_return = 0
    for result in results:
        if 'error' in result:
            continue
        symbol = result.get('symbol', '')
        ret = result.get('total_return', 0) * 100
        total_return += ret
        print(f"  {symbol}: {ret:.2f}%")
    
    if results:
        avg_return = total_return / len(results)
        print(f"\n  平均收益率: {avg_return:.2f}%")


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("A股尾盘策略框架 - 使用示例")
    print("=" * 60)
    
    try:
        example_screening()
        example_technical_analysis()
        example_sell_signals()
        example_backtest()
        # example_batch_backtest()  # 批量回测需要较长时间
        
        print("\n" + "=" * 60)
        print("示例完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
