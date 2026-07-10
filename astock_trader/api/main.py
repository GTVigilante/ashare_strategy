"""
FastAPI 后端
提供 REST API 接口
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import pandas as pd
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database import (
    get_db, StrategyRepository, StockWatchRepository, 
    OrderRepository, BacktestRepository
)
from strategies.base import StrategyRegistry
from strategies.tail_strategy import TailStrategy
from strategies.config import load_strategy_config
from services.backtest_service import HistoricalDataError, fetch_daily_data, run_tail_backtest

# 创建应用
app = FastAPI(
    title="A股量化交易API",
    description="策略管理、选股、回测、信号生成",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化数据库
db = get_db()


# 响应包装器
def success_response(data: Any, message: str = "success") -> Dict:
    return {"code": 0, "message": message, "data": data}


def error_response(message: str, code: int = -1) -> Dict:
    return {"code": code, "message": message, "data": None}


# ============== Pydantic模型 ==============

class StrategyConfigUpdate(BaseModel):
    params: Dict[str, Any]


class StockWatchAdd(BaseModel):
    symbol: str
    name: str = ""
    notes: str = ""


class BacktestRequest(BaseModel):
    strategy_name: str = Field(alias="strategy")
    start_date: str
    end_date: str
    initial_cash: float = 100000
    symbols: List[str] = Field(default_factory=lambda: ["000001"])

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def validate_period(self):
        try:
            start = datetime.strptime(self.start_date, "%Y%m%d")
            end = datetime.strptime(self.end_date, "%Y%m%d")
        except ValueError as exc:
            raise ValueError("日期必须使用 YYYYMMDD 格式") from exc
        if start >= end:
            raise ValueError("开始日期必须早于结束日期")
        if self.initial_cash <= 0:
            raise ValueError("初始资金必须大于 0")
        if len(self.symbols) != 1 or not self.symbols[0].isdigit() or len(self.symbols[0]) != 6:
            raise ValueError("当前版本仅支持一个六位 A 股代码")
        return self


class StockQuery(BaseModel):
    symbol: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None


# ============== 策略管理API ==============

@app.get("/api/strategies")
def list_strategies():
    """获取所有策略"""
    repo = StrategyRepository(db)
    strategies = repo.get_all()
    
    # 也返回已注册但未保存的策略
    registered = StrategyRegistry.list_strategies()
    result = []
    
    for s in strategies:
        result.append({
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "params": s.params,
            "enabled": s.enabled
        })
    
    # 添加已注册但未保存的策略
    for name in registered:
        if not any(r['name'] == name for r in result):
            result.append({
                "name": name,
                "enabled": True
            })
    
    return success_response(result)


@app.get("/api/strategies/{name}")
def get_strategy(name: str):
    """获取策略详情"""
    repo = StrategyRepository(db)
    strategy = repo.get_by_name(name)
    
    if not strategy:
        # 尝试从已注册策略获取
        if name in StrategyRegistry.list_strategies():
            strategy_class = StrategyRegistry.get(name)
            instance = strategy_class()
            return {
                "name": instance.name,
                "description": instance.get_description(),
                "params": instance.params,
                "enabled": True
            }
        raise HTTPException(status_code=404, detail="策略不存在")
    
    return {
        "id": strategy.id,
        "name": strategy.name,
        "description": strategy.description,
        "params": strategy.params,
        "enabled": strategy.enabled
    }


@app.put("/api/strategies/{name}")
def update_strategy(name: str, config: StrategyConfigUpdate):
    """更新策略配置"""
    repo = StrategyRepository(db)
    strategy = repo.get_by_name(name)
    
    if strategy:
        repo.update(name, config.params)
    else:
        # 创建新策略
        strategy_class = StrategyRegistry.get(name)
        if not strategy_class:
            raise HTTPException(status_code=404, detail="策略不存在")
        instance = strategy_class(config.params)
        repo.create(
            name=instance.name,
            description=instance.get_description(),
            params=config.params
        )
    
    return {"message": "策略更新成功"}


# ============== 自选股API ==============

@app.get("/api/watch")
def list_watch():
    """获取自选股列表"""
    repo = StockWatchRepository(db)
    stocks = repo.get_all()
    data = [
        {
            "symbol": s.symbol,
            "name": s.name,
            "added_at": s.added_at.isoformat() if s.added_at else None,
            "notes": s.notes
        }
        for s in stocks
    ]
    return success_response(data)


@app.post("/api/watch")
def add_watch(stock: StockWatchAdd):
    """添加自选股"""
    repo = StockWatchRepository(db)
    try:
        result = repo.add(stock.symbol, stock.name, stock.notes)
        return {"message": "添加成功", "symbol": result.symbol}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/watch/{symbol}")
def remove_watch(symbol: str):
    """删除自选股"""
    repo = StockWatchRepository(db)
    success = repo.remove(symbol)
    if not success:
        raise HTTPException(status_code=404, detail="股票不存在")
    return {"message": "删除成功"}


# ============== 选股API ==============

@app.get("/api/screen")
def screen_stocks(
    date: str = Query(None, description="日期 YYYYMMDD"),
    strategy: str = Query("tail", description="策略名称")
):
    """筛选候选股票"""
    try:
        # 获取策略实例
        strategy_class = StrategyRegistry.get(strategy)
        if not strategy_class:
            raise HTTPException(status_code=404, detail="策略不存在")
        
        strategy_instance = strategy_class()
        
        # TODO: 调用AKShare获取涨停股数据
        # 返回模拟数据演示
        mock_stocks = [
            {"symbol": "600519", "name": "贵州茅台", "price": 1680.00, "change": 2.5, "change_percent": 2.5, "turnover_rate": 0.5, "volume_ratio": 1.5, "market_cap": 2100, "amplitude": 3.2, "close": 1680.00, "ma_bullish": True, "macd_golden": True, "breakout": True, "confidence": 85, "reason": "均线多头+MACD金叉"},
            {"symbol": "000858", "name": "五粮液", "price": 145.50, "change": 3.2, "change_percent": 3.2, "turnover_rate": 1.2, "volume_ratio": 1.8, "market_cap": 560, "amplitude": 4.1, "close": 145.50, "ma_bullish": True, "macd_golden": False, "breakout": True, "confidence": 72, "reason": "平台突破"},
            {"symbol": "600036", "name": "招商银行", "price": 35.80, "change": 1.8, "change_percent": 1.8, "turnover_rate": 0.8, "volume_ratio": 1.3, "market_cap": 890, "amplitude": 2.5, "close": 35.80, "ma_bullish": True, "macd_golden": True, "breakout": False, "confidence": 68, "reason": "MACD金叉"},
        ]
        
        return success_response({
            "date": date or datetime.now().strftime("%Y%m%d"),
            "strategy": strategy,
            "total": len(mock_stocks),
            "stocks": mock_stocks
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== 回测API ==============

@app.post("/api/backtest")
def run_backtest(request: BacktestRequest):
    """运行回测"""
    try:
        strategy_class = StrategyRegistry.get(request.strategy_name)
        if not strategy_class:
            raise HTTPException(status_code=404, detail="策略不存在")
        
        symbol = request.symbols[0]
        configured = load_strategy_config().get("strategies", {}).get("tail", {}).get("params", {})
        backtest_config = load_strategy_config().get("backtest", {})
        params = {**configured, **backtest_config}
        frame = fetch_daily_data(symbol, request.start_date, request.end_date)
        result = run_tail_backtest(frame, symbol, request.initial_cash, params)
        
        # 保存回测记录
        repo = BacktestRepository(db)
        record = repo.save({
            "strategy_name": request.strategy_name,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "initial_cash": request.initial_cash,
            "final_value": result.final_value,
            "total_return": result.total_return,
            "sharpe_ratio": result.sharpe_ratio,
            "max_drawdown": result.max_drawdown,
            "win_rate": result.win_rate,
            "total_trades": len(result.trades),
            "trades_detail": {"trades": result.trades, "equity_curve": result.equity_curve}
        })
        
        return success_response({
            "id": record.id,
            "strategy": request.strategy_name,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "initial_cash": request.initial_cash,
            "final_value": result.final_value,
            "total_return": result.total_return * 100,
            "sharpe_ratio": result.sharpe_ratio,
            "max_drawdown": result.max_drawdown,
            "win_rate": result.win_rate * 100,
            "total_trades": len(result.trades),
            "equity_curve": result.equity_curve,
            "trades": result.trades,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        })
        
    except HTTPException:
        raise
    except HistoricalDataError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/backtest/history")
def get_backtest_history(
    strategy_name: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取回测历史"""
    repo = BacktestRepository(db)
    records = repo.get_history(strategy_name, page_size)
    items = [{
        "id": r.id,
        "strategy": r.strategy_name,
        "start_date": r.start_date,
        "end_date": r.end_date,
        "initial_cash": r.initial_cash,
        "final_value": r.final_value,
        "total_return": (r.total_return or 0) * 100,
        "sharpe_ratio": r.sharpe_ratio or 0,
        "max_drawdown": r.max_drawdown or 0,
        "win_rate": (r.win_rate or 0) * 100,
        "total_trades": r.total_trades or 0,
        "equity_curve": (r.trades_detail or {}).get("equity_curve", []) if isinstance(r.trades_detail, dict) else [],
        "trades": (r.trades_detail or {}).get("trades", []) if isinstance(r.trades_detail, dict) else (r.trades_detail or []),
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in records]
    
    return success_response({
        "total": len(items),
        "page": page,
        "page_size": page_size,
        "list": items
    })


# ============== Dashboard API ==============

@app.get("/api/dashboard")
def get_dashboard():
    """获取仪表盘数据"""
    try:
        # 获取统计数据
        strategy_repo = StrategyRepository(db)
        watch_repo = StockWatchRepository(db)
        backtest_repo = BacktestRepository(db)
        
        strategies = strategy_repo.get_all()
        watch_stocks = watch_repo.get_all()
        recent_backtests = backtest_repo.get_history(limit=10)
        
        # 计算收益（如果有回测记录）
        total_return = 0
        if recent_backtests:
            # 取最新回测的总收益
            latest = recent_backtests[0]
            total_return = float(latest.total_return) if latest.total_return else 0
        
        data = {
            "account": {
                "total_assets": 100000,
                "cash": 80000,
                "stocks_value": 20000,
                "today_profit": 0,
                "today_profit_rate": 0,
            },
            "positions": [],
            "signals": {
                "pending": 0,
                "today_buy": 0,
                "today_sell": 0,
            },
            "backtest": {
                "latest_id": recent_backtests[0].id if recent_backtests else 0,
                "total_return": total_return,
                "max_drawdown": float(recent_backtests[0].max_drawdown) if recent_backtests and recent_backtests[0].max_drawdown else 0,
                "win_rate": float(recent_backtests[0].win_rate) if recent_backtests and recent_backtests[0].win_rate else 0,
                "sharpe_ratio": recent_backtests[0].sharpe_ratio if recent_backtests else 0,
            },
            "watchlist_count": len(watch_stocks),
            "strategy_count": len(strategies),
            "total_return": total_return,
            "today_return": 0,
            "win_rate": 0.65,
        }
        
        return success_response(data)
    except Exception as e:
        data = {
            "account": {"total_assets": 100000, "cash": 100000, "stocks_value": 0, "today_profit": 0, "today_profit_rate": 0},
            "positions": [],
            "signals": {"pending": 0, "today_buy": 0, "today_sell": 0},
            "backtest": {"latest_id": 0, "total_return": 0, "max_drawdown": 0, "win_rate": 0, "sharpe_ratio": 0},
            "watchlist_count": 0,
            "strategy_count": 0,
            "total_return": 0,
            "today_return": 0,
            "win_rate": 0,
        }
        return success_response(data)


@app.get("/api/dashboard/today-stocks")
def get_today_stocks():
    """获取今日选股"""
    return success_response({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "candidates": []
    })


# ============== 交易信号API ==============

@app.get("/api/signals")
def get_signals(
    strategy: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200)
):
    """获取交易信号"""
    # TODO: 从数据库获取信号
    return {
        "signals": [],
        "message": "功能待实现"
    }


# ============== 订单API ==============

@app.get("/api/orders")
def list_orders(limit: int = Query(100, ge=1, le=500)):
    """获取订单列表"""
    repo = OrderRepository(db)
    orders = repo.get_all(limit)
    
    return [
        {
            "id": o.id,
            "order_id": o.order_id,
            "symbol": o.symbol,
            "name": o.name,
            "direction": o.direction,
            "price": o.price,
            "quantity": o.quantity,
            "amount": o.amount,
            "status": o.status,
            "created_at": o.created_at.isoformat() if o.created_at else None
        }
        for o in orders
    ]


# ============== 健康检查 ==============

@app.get("/api/health")
def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


# ============== 启动 ==============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
