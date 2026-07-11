import unittest

from api.main import (
    get_backtest_history, get_dashboard, get_strategy, list_strategies,
    list_watch, paper_status,
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


if __name__ == "__main__":
    unittest.main()
