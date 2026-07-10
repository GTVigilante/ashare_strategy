from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {"日期", "开盘", "最高", "最低", "收盘", "成交量"}


@dataclass
class BacktestMetrics:
    final_value: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    trades: list[dict[str, Any]]
    equity_curve: list[dict[str, Any]]


class HistoricalDataError(RuntimeError):
    pass


def fetch_daily_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch unadjusted A-share daily bars so limit-up returns remain meaningful."""
    try:
        import akshare as ak

        frame = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="",
            timeout=15,
        )
    except Exception as exc:
        raise HistoricalDataError(f"获取 {symbol} 历史行情失败: {exc}") from exc
    if frame is None or frame.empty:
        raise HistoricalDataError(f"{symbol} 在所选区间没有历史行情")
    return frame


def run_tail_backtest(
    frame: pd.DataFrame,
    symbol: str,
    initial_cash: float,
    params: dict[str, Any] | None = None,
) -> BacktestMetrics:
    """Daily-bar approximation: buy signal-day close and sell next-day open."""
    params = params or {}
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise HistoricalDataError(f"行情缺少字段: {', '.join(sorted(missing))}")

    data = frame.copy()
    data["日期"] = pd.to_datetime(data["日期"])
    data = data.sort_values("日期").drop_duplicates("日期").reset_index(drop=True)
    for column in REQUIRED_COLUMNS - {"日期"}:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.dropna(subset=["开盘", "最高", "最低", "收盘", "成交量"])
    if len(data) < 22:
        raise HistoricalDataError("有效交易日不足 22 天，无法计算策略指标")

    close = data["收盘"]
    data["prev_return"] = close.pct_change()
    data["ma5"] = close.rolling(5).mean()
    data["ma10"] = close.rolling(10).mean()
    data["ma20"] = close.rolling(20).mean()
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    data["macd"] = (dif - dea) * 2
    data["volume_ratio"] = data["成交量"] / data["成交量"].rolling(5).mean().shift(1)
    data["amplitude"] = (data["最高"] - data["最低"]) / data["收盘"].shift(1) * 100

    min_price = float(params.get("min_price", 4))
    max_price = float(params.get("max_price", 30))
    min_volume_ratio = float(params.get("min_volume_ratio", 1.2))
    max_amplitude = float(params.get("max_amplitude", 5))
    commission = float(params.get("commission", 0.0003))
    slippage = float(params.get("slippage", 0.001))
    require_ma = bool(params.get("require_ma_bullish", True))
    require_macd = bool(params.get("require_macd_golden", True))

    cash = float(initial_cash)
    trades: list[dict[str, Any]] = []
    equity = [{"date": data.iloc[0]["日期"].strftime("%Y-%m-%d"), "value": cash}]
    for index in range(20, len(data) - 1):
        row = data.iloc[index]
        previous = data.iloc[index - 1]
        next_row = data.iloc[index + 1]
        signal = (
            previous["prev_return"] >= 0.095
            and min_price <= row["收盘"] <= max_price
            and row["volume_ratio"] >= min_volume_ratio
            and row["amplitude"] <= max_amplitude
        )
        if require_ma:
            signal = signal and row["ma5"] > row["ma10"] > row["ma20"]
        if require_macd:
            signal = signal and row["macd"] > 0 and row["macd"] >= previous["macd"]
        if not signal:
            continue

        buy_price = float(row["收盘"]) * (1 + slippage)
        sell_price = float(next_row["开盘"]) * (1 - slippage)
        gross_return = sell_price / buy_price - 1
        net_return = gross_return - commission * 2
        profit = cash * net_return
        cash += profit
        trades.append({
            "id": len(trades) + 1,
            "symbol": symbol,
            "name": "",
            "buy_date": row["日期"].strftime("%Y-%m-%d"),
            "buy_price": round(buy_price, 3),
            "sell_date": next_row["日期"].strftime("%Y-%m-%d"),
            "sell_price": round(sell_price, 3),
            "profit": round(profit, 2),
            "profit_percent": round(net_return * 100, 3),
            "hold_days": 1,
            "reason": "次交易日开盘卖出（日线近似）",
        })
        equity.append({"date": next_row["日期"].strftime("%Y-%m-%d"), "value": round(cash, 2)})

    returns = np.array([trade["profit_percent"] / 100 for trade in trades])
    values = np.array([point["value"] for point in equity], dtype=float)
    peaks = np.maximum.accumulate(values)
    drawdown = np.max((peaks - values) / peaks) if len(values) else 0
    sharpe = float(returns.mean() / returns.std(ddof=1) * np.sqrt(252)) if len(returns) > 1 and returns.std(ddof=1) else 0
    return BacktestMetrics(
        final_value=round(cash, 2),
        total_return=(cash / initial_cash - 1),
        sharpe_ratio=sharpe,
        max_drawdown=float(drawdown * 100),
        win_rate=float((returns > 0).mean()) if len(returns) else 0,
        trades=trades,
        equity_curve=equity,
    )
