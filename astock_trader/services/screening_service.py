from datetime import datetime, timedelta
from typing import Any, Callable
import time

import pandas as pd

from services.backtest_service import HistoricalDataError, fetch_daily_data


class ScreeningDataError(RuntimeError):
    pass


def fetch_limit_up_pool(date: str) -> pd.DataFrame:
    try:
        import akshare as ak

        frame = ak.stock_zt_pool_em(date=date)
    except Exception as exc:
        raise ScreeningDataError(f"获取 {date} 涨停池失败: {exc}") from exc
    return frame if frame is not None else pd.DataFrame()


def find_previous_limit_up_pool(
    date: str,
    pool_fetcher: Callable[[str], pd.DataFrame] = fetch_limit_up_pool,
    lookback_days: int = 7,
) -> tuple[str, pd.DataFrame]:
    target = datetime.strptime(date, "%Y%m%d")
    last_error: Exception | None = None
    for days_back in range(1, lookback_days + 1):
        candidate = (target - timedelta(days=days_back)).strftime("%Y%m%d")
        try:
            frame = pool_fetcher(candidate)
        except Exception as exc:
            last_error = exc
            continue
        if frame is not None and not frame.empty:
            return candidate, frame
    detail = f": {last_error}" if last_error else ""
    raise ScreeningDataError(f"目标日前 {lookback_days} 天没有可用涨停池数据{detail}")


def screen_tail_candidates(
    date: str,
    params: dict[str, Any],
    pool_fetcher: Callable[[str], pd.DataFrame] = fetch_limit_up_pool,
    history_fetcher: Callable[[str, str, str], pd.DataFrame] = fetch_daily_data,
    max_candidates: int | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    pool_date, pool = find_previous_limit_up_pool(date, pool_fetcher)
    required = {"代码", "名称"}
    if not required.issubset(pool.columns):
        raise ScreeningDataError(f"涨停池缺少字段: {', '.join(sorted(required - set(pool.columns)))}")

    min_price = float(params.get("min_price", 4))
    max_price = float(params.get("max_price", 30))
    min_turnover = float(params.get("min_turnover_rate", 3))
    max_market_cap = float(params.get("max_market_cap", 200))
    max_amplitude = float(params.get("max_amplitude", 5))
    min_volume_ratio = float(params.get("min_volume_ratio", 1.2))
    require_ma = bool(params.get("require_ma_bullish", True))
    require_macd = bool(params.get("require_macd_golden", True))
    start_date = (datetime.strptime(date, "%Y%m%d") - timedelta(days=60)).strftime("%Y%m%d")

    candidates = []
    errors = []
    rows = pool if max_candidates is None else pool.head(max_candidates)
    processed = 0

    def report(symbol: str, name: str, status: str, reason: str) -> None:
        nonlocal processed
        processed += 1
        if progress_callback:
            progress_callback({
                "processed": processed,
                "total": len(rows),
                "current_symbol": symbol,
                "current_name": name,
                "detail": {"symbol": symbol, "name": name, "status": status, "reason": reason},
            })

    for _, pool_row in rows.iterrows():
        symbol = str(pool_row["代码"]).zfill(6)
        name = str(pool_row.get("名称", ""))
        if progress_callback:
            progress_callback({
                "processed": processed,
                "total": len(rows),
                "current_symbol": symbol,
                "current_name": name,
                "detail": None,
            })
        market_cap = pd.to_numeric(pool_row.get("流通市值"), errors="coerce")
        market_cap_yi = float(market_cap / 1e8) if pd.notna(market_cap) else None
        if market_cap_yi is not None and market_cap_yi >= max_market_cap:
            report(symbol, name, "rejected", f"流通市值 {market_cap_yi:.1f} 亿超过上限")
            continue
        try:
            time.sleep(0.15)
            bars = history_fetcher(symbol, start_date, date).copy()
            if "日期" not in bars.columns and isinstance(bars.index, pd.DatetimeIndex):
                bars = bars.reset_index()
            if len(bars) < 21:
                report(symbol, name, "rejected", f"历史行情仅 {len(bars)} 个交易日")
                continue
            bars["日期"] = pd.to_datetime(bars["日期"])
            bars = bars[bars["日期"] <= pd.to_datetime(date)].sort_values("日期")
            for column in ("开盘", "最高", "最低", "收盘", "成交量", "换手率"):
                if column in bars:
                    bars[column] = pd.to_numeric(bars[column], errors="coerce")
            row = bars.iloc[-1]
            previous = bars.iloc[-6:-1]
            price = float(row["收盘"])
            turnover = float(row.get("换手率", 0) or 0)
            amplitude = float((row["最高"] - row["最低"]) / bars.iloc[-2]["收盘"] * 100)
            avg_volume = float(previous["成交量"].mean())
            volume_ratio = float(row["成交量"] / avg_volume) if avg_volume else 0
            if not (min_price <= price <= max_price):
                report(symbol, name, "rejected", f"股价 {price:.2f} 不在配置区间")
                continue
            if turnover < min_turnover:
                report(symbol, name, "rejected", f"换手率 {turnover:.2f}% 低于阈值")
                continue
            if amplitude > max_amplitude:
                report(symbol, name, "rejected", f"振幅 {amplitude:.2f}% 超过阈值")
                continue
            if volume_ratio < min_volume_ratio:
                report(symbol, name, "rejected", f"量比 {volume_ratio:.2f} 低于阈值")
                continue

            close = bars["收盘"]
            ma5, ma10, ma20 = (float(close.rolling(n).mean().iloc[-1]) for n in (5, 10, 20))
            ma_bullish = ma5 > ma10 > ma20
            dif = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
            dea = dif.ewm(span=9, adjust=False).mean()
            macd = (dif - dea) * 2
            macd_golden = bool(macd.iloc[-1] > 0 and macd.iloc[-1] >= macd.iloc[-2])
            breakout = bool(price > bars["最高"].iloc[-21:-1].max())
            if require_ma and not ma_bullish:
                report(symbol, name, "rejected", "未满足均线多头")
                continue
            if require_macd and not macd_golden:
                report(symbol, name, "rejected", "未满足 MACD 增强")
                continue
            signals = [name for passed, name in ((ma_bullish, "均线多头"), (macd_golden, "MACD增强"), (breakout, "20日突破")) if passed]
            confidence = min(0.95, 0.55 + len(signals) * 0.1 + min(volume_ratio, 3) * 0.05)
            candidates.append({
                "symbol": symbol,
                "name": name,
                "price": price,
                "close": price,
                "change": float(row.get("涨跌幅", 0) or 0),
                "change_percent": float(row.get("涨跌幅", 0) or 0),
                "turnover_rate": turnover,
                "volume_ratio": volume_ratio,
                "market_cap": market_cap_yi,
                "amplitude": amplitude,
                "ma_bullish": ma_bullish,
                "macd_golden": macd_golden,
                "breakout": breakout,
                "confidence": confidence,
                "reason": "昨日涨停；" + ("、".join(signals) if signals else "通过硬条件"),
            })
            report(symbol, name, "selected", "通过全部筛选条件")
        except (HistoricalDataError, KeyError, ValueError, TypeError, IndexError) as exc:
            errors.append(f"{symbol}: {exc}")
            report(symbol, name, "error", str(exc))

    candidates.sort(key=lambda item: item["confidence"], reverse=True)
    return {"pool_date": pool_date, "pool_size": len(pool),
            "processed": processed, "stocks": candidates, "errors": errors}
