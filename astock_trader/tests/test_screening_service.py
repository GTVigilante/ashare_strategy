import unittest

import pandas as pd

from services.screening_service import ScreeningDataError, screen_tail_candidates


class ScreeningServiceTests(unittest.TestCase):
    def setUp(self):
        dates = pd.bdate_range(end="2025-02-10", periods=30)
        close = [10 + index * 0.08 for index in range(30)]
        self.bars = pd.DataFrame({
            "日期": dates,
            "开盘": close,
            "最高": [value * 1.01 for value in close],
            "最低": [value * 0.99 for value in close],
            "收盘": close,
            "成交量": [1_000_000] * 29 + [2_000_000],
            "换手率": [4.0] * 30,
        })

    def pool_fetcher(self, date):
        if date == "20250207":
            return pd.DataFrame([{"代码": "000001", "名称": "测试股份", "流通市值": 10_000_000_000}])
        return pd.DataFrame()

    def test_filters_real_contract_shape(self):
        result = screen_tail_candidates(
            "20250210",
            {"min_volume_ratio": 1.2, "max_amplitude": 5,
             "require_ma_bullish": False, "require_macd_golden": False},
            pool_fetcher=self.pool_fetcher,
            history_fetcher=lambda *_: self.bars,
        )
        self.assertEqual(result["pool_date"], "20250207")
        self.assertEqual(len(result["stocks"]), 1)
        self.assertEqual(result["stocks"][0]["symbol"], "000001")
        self.assertTrue(result["stocks"][0]["ma_bullish"])

    def test_reports_missing_pool_instead_of_empty_result(self):
        with self.assertRaises(ScreeningDataError):
            screen_tail_candidates(
                "20250210",
                {},
                pool_fetcher=lambda _: pd.DataFrame(),
                history_fetcher=lambda *_: self.bars,
            )

    def test_default_analyzes_entire_pool_and_reports_each_detail(self):
        events = []
        pool = pd.DataFrame([
            {"代码": "000001", "名称": "第一只", "流通市值": 10_000_000_000},
            {"代码": "000002", "名称": "第二只", "流通市值": 10_000_000_000},
            {"代码": "000003", "名称": "超大盘", "流通市值": 30_000_000_000},
        ])

        result = screen_tail_candidates(
            "20250210",
            {"max_market_cap": 200, "min_volume_ratio": 1.2, "max_amplitude": 5},
            pool_fetcher=lambda date: pool if date == "20250207" else pd.DataFrame(),
            history_fetcher=lambda *_: self.bars,
            progress_callback=events.append,
        )

        self.assertEqual(result["pool_size"], 3)
        self.assertEqual(result["processed"], 3)
        detail_events = [event for event in events if event["detail"] is not None]
        self.assertEqual(len(detail_events), 3)
        self.assertEqual(detail_events[-1]["processed"], 3)
        self.assertEqual(detail_events[-1]["total"], 3)
        self.assertEqual(detail_events[-1]["detail"]["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
