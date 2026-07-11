"""
FastAPI 后端
提供 REST API 接口
"""

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
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
from services.backtest_service import (
    HistoricalDataError, compare_tail_parameters, fetch_daily_data, run_equal_weight_portfolio,
    multi_window_walk_forward, run_tail_backtest, walk_forward_validate,
)
from services.screening_service import ScreeningDataError, screen_tail_candidates
from services.auth_service import SessionStore, password_matches
from services.paper_trading_service import PaperTradingEngine, PaperTradingError
from config.settings import APP_PASSWORD, SESSION_TTL_SECONDS, CORS_ORIGINS, API_HOST, API_PORT

# 创建应用
app = FastAPI(
    title="A股量化交易API",
    description="策略管理、选股、回测、信号生成",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化数据库
db = get_db()
sessions = SessionStore(SESSION_TTL_SECONDS)
paper_engine = PaperTradingEngine()


def bearer_token(request: Request) -> Optional[str]:
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    return token if scheme.lower() == "bearer" and token else None


@app.middleware("http")
async def require_authentication(request: Request, call_next):
    public_paths = {"/api/health", "/api/auth/login"}
    if request.method == "OPTIONS" or request.url.path in public_paths:
        return await call_next(request)
    if not sessions.validate(bearer_token(request)):
        return JSONResponse(status_code=401, content=error_response("未登录或会话已过期", 401))
    return await call_next(request)


# 响应包装器
def success_response(data: Any, message: str = "success") -> Dict:
    return {"code": 0, "message": message, "data": data}


def error_response(message: str, code: int = -1) -> Dict:
    return {"code": code, "message": message, "data": None}


# ============== Pydantic模型 ==============

class StrategyConfigUpdate(BaseModel):
    params: Dict[str, Any]
    enabled: Optional[bool] = None


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


class PortfolioBacktestRequest(BaseModel):
    strategy_name: str = Field(alias="strategy")
    start_date: str
    end_date: str
    initial_cash: float = 100000
    symbols: List[str]

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def validate_request(self):
        try:
            start = datetime.strptime(self.start_date, "%Y%m%d")
            end = datetime.strptime(self.end_date, "%Y%m%d")
        except ValueError as exc:
            raise ValueError("日期必须使用 YYYYMMDD 格式") from exc
        self.symbols = list(dict.fromkeys(self.symbols))
        if start >= end or self.initial_cash <= 0:
            raise ValueError("日期区间或初始资金无效")
        if not 2 <= len(self.symbols) <= 10:
            raise ValueError("组合回测支持 2 至 10 只股票")
        if any(not symbol.isdigit() or len(symbol) != 6 for symbol in self.symbols):
            raise ValueError("股票代码必须为六位数字")
        return self


class StockQuery(BaseModel):
    symbol: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class LoginRequest(BaseModel):
    password: str


class PaperOrderRequest(BaseModel):
    approval_token: str
    symbol: str
    side: str
    quantity: int
    price: float


@app.post("/api/auth/login")
def login(request: LoginRequest):
    if not APP_PASSWORD:
        raise HTTPException(status_code=503, detail="服务端尚未配置 APP_PASSWORD")
    if not password_matches(request.password, APP_PASSWORD):
        raise HTTPException(status_code=401, detail="密码错误")
    token, expires_in = sessions.create()
    return success_response({"token": token, "expires_in": expires_in})


@app.post("/api/auth/logout")
def logout(request: Request):
    sessions.revoke(bearer_token(request))
    return success_response(None, "已退出")


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
            return success_response({
                "name": instance.name,
                "description": instance.get_description(),
                "params": instance.params,
                "enabled": True
            })
        raise HTTPException(status_code=404, detail="策略不存在")
    
    return success_response({
        "id": strategy.id,
        "name": strategy.name,
        "description": strategy.description,
        "params": strategy.params,
        "enabled": strategy.enabled
    })


@app.put("/api/strategies/{name}")
def update_strategy(name: str, config: StrategyConfigUpdate):
    """更新策略配置"""
    repo = StrategyRepository(db)
    strategy = repo.get_by_name(name)
    
    if strategy:
        repo.update(name, config.params, enabled=config.enabled)
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
        if config.enabled is False:
            repo.update(name, config.params, enabled=False)
    
    return success_response(None, "策略更新成功")


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
        return success_response({"symbol": result.symbol}, "添加成功")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/watch/{symbol}")
def remove_watch(symbol: str):
    """删除自选股"""
    repo = StockWatchRepository(db)
    success = repo.remove(symbol)
    if not success:
        raise HTTPException(status_code=404, detail="股票不存在")
    return success_response(None, "删除成功")


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
        
        screen_date = date or datetime.now().strftime("%Y%m%d")
        configured = load_strategy_config().get("strategies", {}).get("tail", {}).get("params", {})
        result = screen_tail_candidates(screen_date, configured)
        return success_response({
            "date": screen_date,
            "pool_date": result["pool_date"],
            "pool_size": result["pool_size"],
            "processed": result["processed"],
            "strategy": strategy,
            "total": len(result["stocks"]),
            "stocks": result["stocks"],
            "skipped_errors": len(result["errors"]),
        })
    except HTTPException:
        raise
    except ScreeningDataError as e:
        raise HTTPException(status_code=422, detail=str(e))
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
        extended_metrics = {
            "annual_return": result.annual_return * 100,
            "benchmark_return": result.benchmark_return * 100,
            "excess_return": result.excess_return * 100,
            "profit_factor": result.profit_factor,
            "avg_profit": result.avg_profit,
            "max_profit": result.max_profit,
            "min_profit": result.min_profit,
            "max_consecutive_losses": result.max_consecutive_losses,
            "total_commission": result.total_commission,
        }
        
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
            "trades_detail": {"trades": result.trades, "equity_curve": result.equity_curve, "metrics": extended_metrics}
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
            **extended_metrics,
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
        **((r.trades_detail or {}).get("metrics", {}) if isinstance(r.trades_detail, dict) else {}),
    } for r in records]
    
    return success_response({
        "total": len(items),
        "page": page,
        "page_size": page_size,
        "list": items
    })


@app.post("/api/backtest/portfolio")
def run_portfolio_backtest(request: PortfolioBacktestRequest):
    if request.strategy_name not in ("tail", "尾盘策略"):
        raise HTTPException(status_code=422, detail="组合回测当前仅支持尾盘策略")
    try:
        config = load_strategy_config()
        params = {
            **config.get("strategies", {}).get("tail", {}).get("params", {}),
            **config.get("backtest", {}),
        }
        frames = {
            symbol: fetch_daily_data(symbol, request.start_date, request.end_date)
            for symbol in request.symbols
        }
        result = run_equal_weight_portfolio(frames, request.initial_cash, params)
        return success_response({
            "strategy": request.strategy_name,
            "symbols": request.symbols,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "initial_cash": request.initial_cash,
            "final_value": result.final_value,
            "total_return": result.total_return * 100,
            "annual_return": result.annual_return * 100,
            "benchmark_return": result.benchmark_return * 100,
            "excess_return": result.excess_return * 100,
            "sharpe_ratio": result.sharpe_ratio,
            "max_drawdown": result.max_drawdown,
            "win_rate": result.win_rate * 100,
            "total_trades": len(result.trades),
            "profit_factor": result.profit_factor,
            "max_consecutive_losses": result.max_consecutive_losses,
            "total_commission": result.total_commission,
            "equity_curve": result.equity_curve,
            "trades": result.trades,
            "model": "fixed_equal_weight_subaccounts",
        })
    except HistoricalDataError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/api/backtest/compare")
def compare_backtests(request: BacktestRequest):
    """在同一份行情上比较标准、严格和宽松参数。"""
    if request.strategy_name not in ("tail", "尾盘策略"):
        raise HTTPException(status_code=422, detail="参数对比当前仅支持尾盘策略")
    try:
        symbol = request.symbols[0]
        config = load_strategy_config()
        params = {
            **config.get("strategies", {}).get("tail", {}).get("params", {}),
            **config.get("backtest", {}),
        }
        frame = fetch_daily_data(symbol, request.start_date, request.end_date)
        rows = compare_tail_parameters(frame, symbol, request.initial_cash, params)
        return success_response({
            "symbol": symbol,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "ranking": rows,
        })
    except HistoricalDataError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/api/backtest/walk-forward")
def walk_forward_backtest(request: BacktestRequest):
    if request.strategy_name not in ("tail", "尾盘策略"):
        raise HTTPException(status_code=422, detail="滚动验证当前仅支持尾盘策略")
    try:
        symbol = request.symbols[0]
        config = load_strategy_config()
        params = {
            **config.get("strategies", {}).get("tail", {}).get("params", {}),
            **config.get("backtest", {}),
        }
        frame = fetch_daily_data(symbol, request.start_date, request.end_date)
        return success_response(walk_forward_validate(frame, symbol, request.initial_cash, params))
    except HistoricalDataError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/api/backtest/walk-forward/multi")
def multi_walk_forward_backtest(request: BacktestRequest):
    if request.strategy_name not in ("tail", "尾盘策略"):
        raise HTTPException(status_code=422, detail="多窗口验证当前仅支持尾盘策略")
    try:
        symbol = request.symbols[0]
        config = load_strategy_config()
        params = {
            **config.get("strategies", {}).get("tail", {}).get("params", {}),
            **config.get("backtest", {}),
        }
        frame = fetch_daily_data(symbol, request.start_date, request.end_date)
        return success_response(multi_window_walk_forward(frame, symbol, request.initial_cash, params))
    except HistoricalDataError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/api/paper/approve")
def approve_paper_strategy(request: BacktestRequest):
    """后端重新诊断策略，达标后签发一小时模拟盘准入。"""
    try:
        symbol = request.symbols[0]
        config = load_strategy_config()
        params = {
            **config.get("strategies", {}).get("tail", {}).get("params", {}),
            **config.get("backtest", {}),
        }
        frame = fetch_daily_data(symbol, request.start_date, request.end_date)
        report = multi_window_walk_forward(frame, symbol, request.initial_cash, params)
        diagnostic = report["diagnostic"]
        token = paper_engine.approve(symbol, diagnostic["score"])
        return success_response({"approval_token": token, "expires_in": 3600,
                                 "symbol": symbol, "diagnostic": diagnostic})
    except (HistoricalDataError, PaperTradingError) as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/api/paper/status")
def paper_status():
    return success_response(paper_engine.status())


@app.post("/api/paper/orders")
def place_paper_order(request: PaperOrderRequest):
    try:
        order = paper_engine.execute(request.approval_token, request.symbol, request.side,
                                     request.quantity, request.price)
        return success_response(order, "模拟成交")
    except PaperTradingError as e:
        raise HTTPException(status_code=422, detail=str(e))


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
        paper = paper_engine.status()
        
        # 计算收益（如果有回测记录）
        total_return = 0
        if recent_backtests:
            # 取最新回测的总收益
            latest = recent_backtests[0]
            total_return = float(latest.total_return) if latest.total_return else 0
        
        positions = [{
            "symbol": symbol, "name": "", "quantity": int(position["quantity"]),
            "cost": position["cost"], "price": position["last_price"],
            "profit": (position["last_price"] - position["cost"]) * position["quantity"],
            "profit_rate": (position["last_price"] / position["cost"] - 1) * 100 if position["cost"] else 0,
        } for symbol, position in paper["positions"].items()]
        data = {
            "account": {
                "total_assets": paper["equity"],
                "cash": paper["cash"],
                "stocks_value": paper["equity"] - paper["cash"],
                "today_profit": paper["equity"] - paper_engine.account.day_start_equity,
                "today_profit_rate": paper["daily_return"] * 100,
            },
            "positions": positions,
            "signals": {
                "pending": 0,
                "today_buy": 0,
                "today_sell": 0,
            },
            "backtest": {
                "latest_id": recent_backtests[0].id if recent_backtests else 0,
                "total_return": total_return * 100,
                "max_drawdown": float(recent_backtests[0].max_drawdown) if recent_backtests and recent_backtests[0].max_drawdown else 0,
                "win_rate": float(recent_backtests[0].win_rate) * 100 if recent_backtests and recent_backtests[0].win_rate else 0,
                "sharpe_ratio": recent_backtests[0].sharpe_ratio if recent_backtests else 0,
            },
            "watchlist_count": len(watch_stocks),
            "strategy_count": len(StrategyRegistry.list_strategies()),
            "total_return": total_return * 100,
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
    return success_response({"total": 0, "page": 1, "page_size": limit, "list": []}, "暂无交易信号")


# ============== 订单API ==============

@app.get("/api/orders")
def list_orders(limit: int = Query(100, ge=1, le=500)):
    """获取订单列表"""
    repo = OrderRepository(db)
    orders = repo.get_all(limit)
    
    data = [
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
    return success_response({"total": len(data), "page": 1, "page_size": limit, "list": data})


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
    uvicorn.run(app, host=API_HOST, port=API_PORT)
