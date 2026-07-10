import unittest

import pandas as pd

from services.backtest_service import HistoricalDataError, run_tail_backtest


class TailBacktestTests(unittest.TestCase):
    def make_bars(self):
        dates = pd.bdate_range("2025-01-01", periods=25)
        closes = [10 + index * 0.05 for index in range(25)]
        closes[19] = closes[18] * 1.10
        closes[20] = closes[19] * 1.01
        rows = []
        for date, close in zip(dates, closes):
            rows.append({
                "日期": date,
                "开盘": close * 0.995,
                "最高": close * 1.01,
                "最低": close * 0.99,
                "收盘": close,
                "成交量": 1_000_000,
            })
        rows[21]["开盘"] = rows[20]["收盘"] * 1.03
        return pd.DataFrame(rows)

    def test_generates_trade_and_equity_curve(self):
        result = run_tail_backtest(
            self.make_bars(),
            "000001",
            100_000,
            {
                "require_ma_bullish": False,
                "require_macd_golden": False,
                "min_volume_ratio": 0.5,
                "max_amplitude": 10,
                "commission": 0.0003,
                "slippage": 0.001,
            },
        )
        self.assertEqual(len(result.trades), 1)
        self.assertGreater(result.final_value, 100_000)
        self.assertEqual(len(result.equity_curve), 2)

    def test_rejects_short_history(self):
        with self.assertRaises(HistoricalDataError):
            run_tail_backtest(self.make_bars().head(10), "000001", 100_000)


if __name__ == "__main__":
    unittest.main()
