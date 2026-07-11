import unittest

from services.paper_trading_service import PaperTradingEngine, PaperTradingError


class PaperTradingTests(unittest.TestCase):
    def test_requires_diagnostic_gate(self):
        engine = PaperTradingEngine()
        with self.assertRaises(PaperTradingError):
            engine.approve("000001", 74)

    def test_enforces_lot_and_position_limit(self):
        engine = PaperTradingEngine()
        token = engine.approve("000001", 80)
        with self.assertRaises(PaperTradingError):
            engine.execute(token, "000001", "buy", 50, 10)
        with self.assertRaises(PaperTradingError):
            engine.execute(token, "000001", "buy", 2100, 10)
        order = engine.execute(token, "000001", "buy", 2000, 10)
        self.assertEqual(order["mode"], "paper")
        self.assertEqual(engine.account.positions["000001"]["quantity"], 2000)

    def test_daily_loss_circuit_breaker(self):
        engine = PaperTradingEngine()
        token = engine.approve("000001", 90)
        engine.account.cash = 96_000
        with self.assertRaisesRegex(PaperTradingError, "单日亏损"):
            engine.execute(token, "000001", "buy", 100, 10)


if __name__ == "__main__":
    unittest.main()
