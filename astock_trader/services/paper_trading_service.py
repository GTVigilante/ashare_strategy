import secrets
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any


class PaperTradingError(RuntimeError):
    pass


@dataclass
class Approval:
    symbol: str
    score: int
    expires_at: float


@dataclass
class PaperAccount:
    initial_cash: float = 100_000
    cash: float = 100_000
    peak_equity: float = 100_000
    day_start_equity: float = 100_000
    positions: dict[str, dict[str, float]] = field(default_factory=dict)
    orders: list[dict[str, Any]] = field(default_factory=list)


class PaperTradingEngine:
    def __init__(self, initial_cash: float = 100_000, max_position: float = 0.20,
                 daily_loss_limit: float = 0.03, drawdown_limit: float = 0.10):
        self.account = PaperAccount(initial_cash, initial_cash, initial_cash, initial_cash)
        self.max_position = max_position
        self.daily_loss_limit = daily_loss_limit
        self.drawdown_limit = drawdown_limit
        self.approvals: dict[str, Approval] = {}
        self.lock = Lock()

    def approve(self, symbol: str, score: int, ttl_seconds: int = 3600) -> str:
        if score < 75:
            raise PaperTradingError("策略诊断低于 75 分，不允许进入模拟盘")
        token = secrets.token_urlsafe(24)
        self.approvals[token] = Approval(symbol, score, time.time() + ttl_seconds)
        return token

    def equity(self, prices: dict[str, float] | None = None) -> float:
        prices = prices or {}
        return self.account.cash + sum(
            position["quantity"] * prices.get(symbol, position["last_price"])
            for symbol, position in self.account.positions.items()
        )

    def status(self, prices: dict[str, float] | None = None) -> dict[str, Any]:
        equity = self.equity(prices)
        return {
            "cash": round(self.account.cash, 2), "equity": round(equity, 2),
            "peak_equity": round(self.account.peak_equity, 2),
            "drawdown": (self.account.peak_equity - equity) / self.account.peak_equity,
            "daily_return": equity / self.account.day_start_equity - 1,
            "positions": self.account.positions, "orders": self.account.orders[-50:],
            "limits": {"max_position": self.max_position, "daily_loss": self.daily_loss_limit,
                       "max_drawdown": self.drawdown_limit},
        }

    def execute(self, approval_token: str, symbol: str, side: str,
                quantity: int, price: float) -> dict[str, Any]:
        with self.lock:
            approval = self.approvals.get(approval_token)
            if not approval or approval.expires_at <= time.time() or approval.symbol != symbol:
                raise PaperTradingError("模拟盘准入无效、已过期或股票不匹配")
            if side not in {"buy", "sell"} or quantity <= 0 or quantity % 100 != 0 or price <= 0:
                raise PaperTradingError("方向、价格或数量无效；A 股数量必须为 100 股整数倍")
            equity = self.equity({symbol: price})
            self.account.peak_equity = max(self.account.peak_equity, equity)
            if equity / self.account.day_start_equity - 1 <= -self.daily_loss_limit:
                raise PaperTradingError("已触发单日亏损熔断")
            if (self.account.peak_equity - equity) / self.account.peak_equity >= self.drawdown_limit:
                raise PaperTradingError("已触发账户最大回撤熔断")

            amount = quantity * price
            position = self.account.positions.get(symbol, {"quantity": 0, "cost": 0, "last_price": price})
            if side == "buy":
                if amount > self.account.cash:
                    raise PaperTradingError("模拟账户现金不足")
                if position["quantity"] * price + amount > equity * self.max_position:
                    raise PaperTradingError("订单将超过单股 20% 仓位限制")
                old_amount = position["quantity"] * position["cost"]
                position["quantity"] += quantity
                position["cost"] = (old_amount + amount) / position["quantity"]
                self.account.cash -= amount
                self.account.positions[symbol] = position
            else:
                if position["quantity"] < quantity:
                    raise PaperTradingError("模拟持仓不足")
                position["quantity"] -= quantity
                self.account.cash += amount
                if position["quantity"] == 0:
                    self.account.positions.pop(symbol, None)
                else:
                    self.account.positions[symbol] = position
            position["last_price"] = price
            order = {"id": len(self.account.orders) + 1, "symbol": symbol, "side": side,
                     "quantity": quantity, "price": price, "amount": amount,
                     "created_at": time.time(), "status": "filled", "mode": "paper"}
            self.account.orders.append(order)
            return order
