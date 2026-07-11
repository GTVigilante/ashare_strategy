from dataclasses import dataclass
from typing import Any, Callable
import time
from datetime import datetime
from pathlib import Path

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
    annual_return: float
    benchmark_return: float
    excess_return: float
    profit_factor: float | None
    avg_profit: float
    max_profit: float
    min_profit: float
    max_consecutive_losses: int
    total_commission: float
    trades: list[dict[str, Any]]
    equity_curve: list[dict[str, Any]]


class HistoricalDataError(RuntimeError):
    pass


def tail_parameter_variants(base: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Return named, deterministic parameter sets for like-for-like comparison."""
    standard = dict(base)
    strict = {**base, "min_volume_ratio": 1.5, "max_amplitude": 3.0,
              "require_ma_bullish": True, "require_macd_golden": True}
    relaxed = {**base, "min_volume_ratio": 1.0, "max_amplitude": 8.0,
               "require_ma_bullish": False, "require_macd_golden": False}
    return [("标准", standard), ("严格", strict), ("宽松", relaxed)]


def compare_tail_parameters(
    frame: pd.DataFrame,
    symbol: str,
    initial_cash: float,
    base: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = []
    for name, params in tail_parameter_variants(base):
        result = run_tail_backtest(frame, symbol, initial_cash, params)
        rows.append({
            "name": name,
            "params": {
                key: params.get(key) for key in (
                    "min_volume_ratio", "max_amplitude", "require_ma_bullish", "require_macd_golden"
                )
            },
            "total_return": result.total_return * 100,
            "annual_return": result.annual_return * 100,
            "benchmark_return": result.benchmark_return * 100,
            "excess_return": result.excess_return * 100,
            "max_drawdown": result.max_drawdown,
            "win_rate": result.win_rate * 100,
            "total_trades": len(result.trades),
            "profit_factor": result.profit_factor,
            "total_commission": result.total_commission,
        })
    return sorted(rows, key=lambda row: (row["excess_return"], row["total_return"]), reverse=True)


def walk_forward_validate(
    frame: pd.DataFrame,
    symbol: str,
    initial_cash: float,
    base: dict[str, Any],
    train_ratio: float = 0.7,
) -> dict[str, Any]:
    data = frame.copy()
    data["日期"] = pd.to_datetime(data["日期"])
    data = data.sort_values("日期").drop_duplicates("日期").reset_index(drop=True)
    if len(data) < 70:
        raise HistoricalDataError("滚动验证至少需要 70 个交易日")
    split_index = int(len(data) * train_ratio)
    split_index = min(max(split_index, 45), len(data) - 20)
    train = data.iloc[:split_index].copy()
    validation_start = data.iloc[split_index]["日期"]
    validation = data.iloc[max(0, split_index - 30):].copy()

    ranking = compare_tail_parameters(train, symbol, initial_cash, base)
    selected_name = ranking[0]["name"]
    selected_params = dict(tail_parameter_variants(base)) [selected_name]
    result = run_tail_backtest(
        validation, symbol, initial_cash, selected_params,
        evaluation_start_date=validation_start.strftime("%Y%m%d"),
    )
    return {
        "symbol": symbol,
        "train_start": train.iloc[0]["日期"].strftime("%Y-%m-%d"),
        "train_end": train.iloc[-1]["日期"].strftime("%Y-%m-%d"),
        "validation_start": validation_start.strftime("%Y-%m-%d"),
        "validation_end": data.iloc[-1]["日期"].strftime("%Y-%m-%d"),
        "selected_name": selected_name,
        "selected_params": ranking[0]["params"],
        "training_ranking": ranking,
        "validation": {
            "total_return": result.total_return * 100,
            "annual_return": result.annual_return * 100,
            "benchmark_return": result.benchmark_return * 100,
            "excess_return": result.excess_return * 100,
            "max_drawdown": result.max_drawdown,
            "sharpe_ratio": result.sharpe_ratio,
            "win_rate": result.win_rate * 100,
            "total_trades": len(result.trades),
            "profit_factor": result.profit_factor,
            "equity_curve": result.equity_curve,
            "trades": result.trades,
        },
    }


def multi_window_walk_forward(
    frame: pd.DataFrame,
    symbol: str,
    initial_cash: float,
    base: dict[str, Any],
    train_days: int = 60,
    validation_days: int = 20,
) -> dict[str, Any]:
    data = frame.copy()
    data["日期"] = pd.to_datetime(data["日期"])
    data = data.sort_values("日期").drop_duplicates("日期").reset_index(drop=True)
    if len(data) < train_days + validation_days * 2:
        raise HistoricalDataError(f"多窗口验证至少需要 {train_days + validation_days * 2} 个交易日")

    cash = float(initial_cash)
    windows = []
    combined_curve = []
    benchmark_growth = 1.0
    for start in range(0, len(data) - train_days - validation_days + 1, validation_days):
        train_end = start + train_days
        validation_end = train_end + validation_days
        train = data.iloc[start:train_end].copy()
        validation_start_date = data.iloc[train_end]["日期"]
        validation = data.iloc[max(start, train_end - 30):validation_end].copy()
        ranking = compare_tail_parameters(train, symbol, cash, base)
        selected_name = ranking[0]["name"]
        selected_params = dict(tail_parameter_variants(base))[selected_name]
        opening_cash = cash
        result = run_tail_backtest(
            validation, symbol, opening_cash, selected_params,
            evaluation_start_date=validation_start_date.strftime("%Y%m%d"),
        )
        cash = result.final_value
        benchmark_growth *= 1 + result.benchmark_return
        curve = result.equity_curve
        if combined_curve and curve and combined_curve[-1]["date"] == curve[0]["date"]:
            curve = curve[1:]
        combined_curve.extend(curve)
        windows.append({
            "index": len(windows) + 1,
            "train_start": train.iloc[0]["日期"].strftime("%Y-%m-%d"),
            "train_end": train.iloc[-1]["日期"].strftime("%Y-%m-%d"),
            "validation_start": validation_start_date.strftime("%Y-%m-%d"),
            "validation_end": data.iloc[validation_end - 1]["日期"].strftime("%Y-%m-%d"),
            "selected_name": selected_name,
            "opening_cash": round(opening_cash, 2),
            "closing_cash": round(cash, 2),
            "total_return": result.total_return * 100,
            "benchmark_return": result.benchmark_return * 100,
            "excess_return": result.excess_return * 100,
            "max_drawdown": result.max_drawdown,
            "total_trades": len(result.trades),
        })

    values = pd.Series([point["value"] for point in combined_curve], dtype=float)
    peaks = values.cummax()
    total_return = cash / initial_cash - 1
    benchmark_return = benchmark_growth - 1
    selections: dict[str, int] = {}
    for window in windows:
        selections[window["selected_name"]] = selections.get(window["selected_name"], 0) + 1
    return {
        "symbol": symbol,
        "train_days": train_days,
        "validation_days": validation_days,
        "window_count": len(windows),
        "windows": windows,
        "summary": {
            "initial_cash": initial_cash,
            "final_value": round(cash, 2),
            "total_return": total_return * 100,
            "benchmark_return": benchmark_return * 100,
            "excess_return": (total_return - benchmark_return) * 100,
            "max_drawdown": float(((peaks - values) / peaks).max() * 100) if len(values) else 0,
            "positive_windows": sum(window["total_return"] > 0 for window in windows),
            "selection_counts": selections,
            "equity_curve": combined_curve,
        },
    }


def run_equal_weight_portfolio(
    frames: dict[str, pd.DataFrame],
    initial_cash: float,
    params: dict[str, Any],
) -> BacktestMetrics:
    """Combine fixed equal-weight subaccounts into one portfolio curve."""
    if not frames:
        raise HistoricalDataError("组合至少需要一只股票")
    allocation = initial_cash / len(frames)
    results = {
        symbol: run_tail_backtest(frame, symbol, allocation, params)
        for symbol, frame in frames.items()
    }
    curves = []
    all_trades = []
    for symbol, result in results.items():
        series = pd.Series(
            {pd.to_datetime(point["date"]): point["value"] for point in result.equity_curve},
            name=symbol,
            dtype=float,
        )
        curves.append(series)
        all_trades.extend(result.trades)
    combined = pd.concat(curves, axis=1).sort_index().ffill().bfill().sum(axis=1)
    portfolio_returns = combined.pct_change().dropna()
    final_value = float(combined.iloc[-1])
    total_return = final_value / initial_cash - 1
    elapsed_days = max(1, (combined.index[-1] - combined.index[0]).days)
    annual_return = (1 + total_return) ** (365 / elapsed_days) - 1 if total_return > -1 else -1
    peaks = combined.cummax()
    max_drawdown = float(((peaks - combined) / peaks).max() * 100)
    sharpe = float(portfolio_returns.mean() / portfolio_returns.std(ddof=1) * np.sqrt(252)) \
        if len(portfolio_returns) > 1 and portfolio_returns.std(ddof=1) else 0
    trade_returns = np.array([trade["profit_percent"] / 100 for trade in all_trades])
    wins, losses = trade_returns[trade_returns > 0], trade_returns[trade_returns < 0]
    profit_factor = float(wins.sum() / abs(losses.sum())) if len(losses) and abs(losses.sum()) else None
    consecutive = max_consecutive = 0
    for trade in sorted(all_trades, key=lambda item: item["sell_date"]):
        consecutive = consecutive + 1 if trade["profit_percent"] < 0 else 0
        max_consecutive = max(max_consecutive, consecutive)
    benchmark_return = float(np.mean([result.benchmark_return for result in results.values()]))
    return BacktestMetrics(
        final_value=round(final_value, 2), total_return=total_return,
        sharpe_ratio=sharpe, max_drawdown=max_drawdown,
        win_rate=float((trade_returns > 0).mean()) if len(trade_returns) else 0,
        annual_return=float(annual_return), benchmark_return=benchmark_return,
        excess_return=float(total_return - benchmark_return), profit_factor=profit_factor,
        avg_profit=float(trade_returns.mean() * 100) if len(trade_returns) else 0,
        max_profit=float(trade_returns.max() * 100) if len(trade_returns) else 0,
        min_profit=float(trade_returns.min() * 100) if len(trade_returns) else 0,
        max_consecutive_losses=max_consecutive,
        total_commission=float(sum(result.total_commission for result in results.values())),
        trades=sorted(all_trades, key=lambda item: (item["buy_date"], item["symbol"])),
        equity_curve=[{"date": date.strftime("%Y-%m-%d"), "value": round(value, 2)} for date, value in combined.items()],
    )


def _market_symbol(symbol: str) -> str:
    return f"sh{symbol}" if symbol.startswith(("5", "6", "9")) else f"sz{symbol}"


def _normalize_fallback(frame: pd.DataFrame) -> pd.DataFrame:
    mapping = {
        "date": "日期", "open": "开盘", "high": "最高", "low": "最低",
        "close": "收盘", "volume": "成交量", "turnover": "换手率",
    }
    result = frame.rename(columns=mapping).copy()
    if "换手率" in result:
        result["换手率"] = pd.to_numeric(result["换手率"], errors="coerce") * 100
    return result


def fetch_daily_data(
    symbol: str,
    start_date: str,
    end_date: str,
    retries: int = 3,
    cache_dir: Path | None = None,
    primary_fetcher: Callable[..., pd.DataFrame] | None = None,
    fallback_fetcher: Callable[..., pd.DataFrame] | None = None,
) -> pd.DataFrame:
    """Fetch daily bars with disk cache and Eastmoney -> Sina failover."""
    cache_dir = cache_dir or Path(__file__).resolve().parent.parent / "data" / "cache" / "daily"
    cache_file = cache_dir / f"{symbol}_{start_date}_{end_date}.csv"
    if cache_file.exists():
        current_query = end_date >= datetime.now().strftime("%Y%m%d")
        fresh = time.time() - cache_file.stat().st_mtime < 300
        if not current_query or fresh:
            cached = pd.read_csv(cache_file)
            cached.attrs["source"] = "cache"
            return cached

    if primary_fetcher is None or fallback_fetcher is None:
        import akshare as ak
        primary_fetcher = primary_fetcher or ak.stock_zh_a_hist
        fallback_fetcher = fallback_fetcher or ak.stock_zh_a_daily
    errors = []
    frame = pd.DataFrame()
    for attempt in range(retries):
        try:
            frame = primary_fetcher(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="",
                timeout=15,
            )
            if frame is not None and not frame.empty:
                frame.attrs["source"] = "eastmoney"
                break
            errors.append("东方财富返回空数据")
        except Exception as exc:
            errors.append(f"东方财富: {exc}")
            if attempt + 1 < retries:
                time.sleep(0.5 * (attempt + 1))
    if frame is None or frame.empty:
        try:
            frame = fallback_fetcher(symbol=_market_symbol(symbol), start_date=start_date, end_date=end_date, adjust="")
            frame = _normalize_fallback(frame)
            frame.attrs["source"] = "sina"
        except Exception as exc:
            errors.append(f"新浪: {exc}")
    if frame is None or frame.empty:
        raise HistoricalDataError(f"{symbol} 在所选区间没有历史行情；" + " | ".join(errors))
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise HistoricalDataError(f"{symbol} 行情缺少字段: {', '.join(sorted(missing))}")
    source = frame.attrs.get("source", "unknown")
    cache_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(cache_file, index=False)
    frame.attrs["source"] = source
    return frame


def run_tail_backtest(
    frame: pd.DataFrame,
    symbol: str,
    initial_cash: float,
    params: dict[str, Any] | None = None,
    evaluation_start_date: str | None = None,
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
    evaluation_start = pd.to_datetime(evaluation_start_date) if evaluation_start_date else data.iloc[0]["日期"]
    evaluation_data = data[data["日期"] >= evaluation_start]
    if len(evaluation_data) < 2:
        raise HistoricalDataError("评估区间至少需要 2 个交易日")

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
    total_commission = 0.0
    trades: list[dict[str, Any]] = []
    equity = [{"date": evaluation_data.iloc[0]["日期"].strftime("%Y-%m-%d"), "value": cash}]
    for index in range(20, len(data) - 1):
        row = data.iloc[index]
        previous = data.iloc[index - 1]
        next_row = data.iloc[index + 1]
        if row["日期"] < evaluation_start:
            continue
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
        commission_cost = cash * commission + cash * (1 + gross_return) * commission
        profit = cash * gross_return - commission_cost
        net_return = profit / cash
        total_commission += commission_cost
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
            "commission": round(commission_cost, 2),
            "hold_days": 1,
            "reason": "次交易日开盘卖出（日线近似）",
        })
        equity.append({"date": next_row["日期"].strftime("%Y-%m-%d"), "value": round(cash, 2)})

    returns = np.array([trade["profit_percent"] / 100 for trade in trades])
    final_date = evaluation_data.iloc[-1]["日期"].strftime("%Y-%m-%d")
    if equity[-1]["date"] != final_date:
        equity.append({"date": final_date, "value": round(cash, 2)})
    values = np.array([point["value"] for point in equity], dtype=float)
    peaks = np.maximum.accumulate(values)
    drawdown = np.max((peaks - values) / peaks) if len(values) else 0
    sharpe = float(returns.mean() / returns.std(ddof=1) * np.sqrt(252)) if len(returns) > 1 and returns.std(ddof=1) else 0
    total_return = cash / initial_cash - 1
    elapsed_days = max(1, (evaluation_data.iloc[-1]["日期"] - evaluation_data.iloc[0]["日期"]).days)
    annual_return = (1 + total_return) ** (365 / elapsed_days) - 1 if total_return > -1 else -1
    benchmark_return = float(evaluation_data.iloc[-1]["收盘"] / evaluation_data.iloc[0]["收盘"] - 1)
    wins = returns[returns > 0]
    losses = returns[returns < 0]
    profit_factor = float(wins.sum() / abs(losses.sum())) if len(losses) and abs(losses.sum()) else None
    consecutive = max_consecutive = 0
    for value in returns:
        consecutive = consecutive + 1 if value < 0 else 0
        max_consecutive = max(max_consecutive, consecutive)
    return BacktestMetrics(
        final_value=round(cash, 2),
        total_return=total_return,
        sharpe_ratio=sharpe,
        max_drawdown=float(drawdown * 100),
        win_rate=float((returns > 0).mean()) if len(returns) else 0,
        annual_return=float(annual_return),
        benchmark_return=benchmark_return,
        excess_return=float(total_return - benchmark_return),
        profit_factor=profit_factor,
        avg_profit=float(returns.mean() * 100) if len(returns) else 0,
        max_profit=float(returns.max() * 100) if len(returns) else 0,
        min_profit=float(returns.min() * 100) if len(returns) else 0,
        max_consecutive_losses=max_consecutive,
        total_commission=float(total_commission),
        trades=trades,
        equity_curve=equity,
    )
