import unittest
from unittest.mock import MagicMock, patch

from api.main import (
    get_backtest_history, get_dashboard, get_strategy, list_strategies,
    list_watch, paper_status, StrategyConfigUpdate, update_strategy,
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


if __name__ == "__main__":
    unittest.main()
