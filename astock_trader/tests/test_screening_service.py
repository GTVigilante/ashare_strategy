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
            {"min_volume_ratio": 1.2, "max_amplitude": 5},
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


if __name__ == "__main__":
    unittest.main()
