import unittest
from unittest.mock import MagicMock, patch

from api.main import (
    get_backtest_history, get_dashboard, get_strategy, list_strategies,
    list_watch, paper_status, StrategyConfigUpdate, update_strategy,
    tail_runtime_params,
    toggle_strategy,
    get_today_stocks, latest_screening,
    StockWatchAdd, add_watch,
)


class ApiContractTests(unittest.TestCase):
    def assert_envelope(self, response):
        self.assertEqual(set(("code", "message", "data")) - set(response), set())
        self.assertEqual(response["code"], 0)

    def test_frontend_read_endpoints_use_same_envelope(self):
        responses = [
            get_dashboard(), list_strategies(), get_strategy("尾盘策略"),
            list_watch(), get_backtest_history(page=1, page_size=10), paper_status(),
        ]
        for response in responses:
            with self.subTest(response=response):
                self.assert_envelope(response)

    @patch("api.main.StrategyRepository")
    def test_strategy_update_keeps_enabled_separate_from_params(self, repository_class):
        repository = repository_class.return_value
        repository.get_by_name.return_value = MagicMock()

        response = update_strategy(
            "尾盘策略",
            StrategyConfigUpdate(params={"min_price": 5}, enabled=False),
        )

        repository.update.assert_called_once_with(
            "尾盘策略", {"min_price": 5}, enabled=False,
        )
        self.assert_envelope(response)

    @patch("api.main.load_strategy_config")
    @patch("api.main.StrategyRepository")
    def test_runtime_params_merge_saved_overrides_with_backtest_defaults(
        self, repository_class, load_config,
    ):
        load_config.return_value = {
            "strategies": {"tail": {"params": {"min_price": 4, "stop_loss": 3}}},
            "backtest": {"commission_rate": 0.0003},
        }
        repository_class.return_value.get_by_name.return_value = MagicMock(
            enabled=True, params={"min_price": 8},
        )

        params = tail_runtime_params(include_backtest=True)

        self.assertEqual(params["min_price"], 8)
        self.assertEqual(params["stop_loss"], 3)
        self.assertEqual(params["commission_rate"], 0.0003)

    @patch("api.main.StrategyRepository")
    def test_disabled_strategy_cannot_run(self, repository_class):
        repository_class.return_value.get_by_name.return_value = MagicMock(
            enabled=False, params={},
        )
        with self.assertRaisesRegex(Exception, "尾盘策略当前已停用"):
            tail_runtime_params()

    @patch("api.main.StrategyRepository")
    def test_strategy_toggle_preserves_params(self, repository_class):
        repository = repository_class.return_value
        repository.get_by_name.return_value = MagicMock(
            enabled=True, params={"min_price": 8},
        )

        response = toggle_strategy("尾盘策略")

        repository.update.assert_called_once_with(
            "尾盘策略", {"min_price": 8}, enabled=False,
        )
        self.assertFalse(response["data"]["enabled"])

    def test_dashboard_candidates_use_latest_real_screening_result(self):
        original = dict(latest_screening)
        try:
            latest_screening.update({
                "date": "20260711",
                "candidates": [{"symbol": "000001", "name": "测试股"}],
            })
            response = get_today_stocks()
            self.assertEqual(response["data"]["date"], "20260711")
            self.assertEqual(response["data"]["candidates"][0]["symbol"], "000001")
        finally:
            latest_screening.update(original)

    def test_watch_request_validates_symbol_and_normalizes_tags(self):
        request = StockWatchAdd(
            symbol=" 000001 ", tags=["银行", " 银行 ", "低估"],
        )
        self.assertEqual(request.symbol, "000001")
        self.assertEqual(request.tags, ["银行", "低估"])
        with self.assertRaisesRegex(Exception, "六位数字"):
            StockWatchAdd(symbol="123")

    @patch("api.main.StockWatchRepository")
    def test_duplicate_watch_has_clear_conflict(self, repository_class):
        repository_class.return_value.get_by_symbol.return_value = MagicMock()
        with self.assertRaisesRegex(Exception, "已在自选列表"):
            add_watch(StockWatchAdd(symbol="000001"))


if __name__ == "__main__":
    unittest.main()
