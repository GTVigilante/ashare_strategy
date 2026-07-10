import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from services.backtest_service import HistoricalDataError, fetch_daily_data, run_tail_backtest


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

    def test_falls_back_and_reuses_disk_cache(self):
        calls = {"primary": 0, "fallback": 0}

        def primary(**_):
            calls["primary"] += 1
            raise ConnectionError("rate limited")

        def fallback(**_):
            calls["fallback"] += 1
            return pd.DataFrame([{
                "date": "2025-01-02", "open": 10, "high": 11, "low": 9.5,
                "close": 10.5, "volume": 1000, "turnover": 0.04,
            }])

        with TemporaryDirectory() as directory:
            args = dict(
                symbol="000001", start_date="20250101", end_date="20250103",
                retries=1, cache_dir=Path(directory), primary_fetcher=primary,
                fallback_fetcher=fallback,
            )
            first = fetch_daily_data(**args)
            second = fetch_daily_data(**args)
        self.assertEqual(first.attrs["source"], "sina")
        self.assertEqual(second.attrs["source"], "cache")
        self.assertEqual(first.iloc[0]["换手率"], 4.0)
        self.assertEqual(calls, {"primary": 1, "fallback": 1})


if __name__ == "__main__":
    unittest.main()
