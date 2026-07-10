"""
数据库层
使用SQLAlchemy + SQLite
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import json

from config.settings import DATABASE_URL, BASE_DIR

Base = declarative_base()


# ============== 数据模型 ==============

class Strategy(Base):
    """策略配置"""
    __tablename__ = 'strategies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    params = Column(JSON)  # 策略参数
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class StockWatch(Base):
    """自选股"""
    __tablename__ = 'stock_watch'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False)  # 股票代码
    name = Column(String(100))  # 股票名称
    added_at = Column(DateTime, default=datetime.now)
    notes = Column(Text)  # 备注
    tags = Column(JSON)  # 标签


class Order(Base):
    """订单记录"""
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(50), unique=True)  # 券商订单号
    symbol = Column(String(20), nullable=False)  # 股票代码
    name = Column(String(100))  # 股票名称
    direction = Column(String(10))  # buy/sell
    price = Column(Float, nullable=False)  # 成交价格
    quantity = Column(Integer, nullable=False)  # 成交数量
    amount = Column(Float)  # 成交金额
    commission = Column(Float, default=0)  # 手续费
    status = Column(String(20), default='pending')  # pending/filled/cancelled
    strategy = Column(String(100))  # 策略名称
    created_at = Column(DateTime, default=datetime.now)
    filled_at = Column(DateTime)


class BacktestRecord(Base):
    """回测记录"""
    __tablename__ = 'backtest_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_name = Column(String(100), nullable=False)
    start_date = Column(String(20), nullable=False)
    end_date = Column(String(20), nullable=False)
    initial_cash = Column(Float)
    final_value = Column(Float)
    total_return = Column(Float)  # 总收益率
    sharpe_ratio = Column(Float)  # 夏普比率
    max_drawdown = Column(Float)  # 最大回撤
    win_rate = Column(Float)  # 胜率
    total_trades = Column(Integer)  # 总交易次数
    trades_detail = Column(JSON)  # 交易明细
    created_at = Column(DateTime, default=datetime.now)


class TradeSignal(Base):
    """交易信号"""
    __tablename__ = 'trade_signals'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    name = Column(String(100))
    signal_type = Column(String(20))  # buy/sell
    price = Column(Float)
    confidence = Column(Float)  # 置信度
    reason = Column(Text)
    strategy = Column(String(100))
    created_at = Column(DateTime, default=datetime.now)
    status = Column(String(20), default='pending')  # pending/executed/expired


# ============== 数据库管理 ==============

class Database:
    """数据库管理类"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_db()
        return cls._instance
    
    def _init_db(self):
        """初始化数据库"""
        db_path = Path(BASE_DIR) / 'data' / 'trader.db'
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.engine = create_engine(
            DATABASE_URL,
            echo=False,
            connect_args={'check_same_thread': False} if 'sqlite' in DATABASE_URL else {}
        )
        
        # 创建表
        Base.metadata.create_all(self.engine)
        
        # 创建会话工厂
        self.SessionLocal = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=self.engine
        )
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()
    
    def close(self):
        """关闭数据库连接"""
        self.engine.dispose()


# ============== Repository ==============

class StrategyRepository:
    """策略仓储"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def get_all(self) -> List[Strategy]:
        with self.db.get_session() as session:
            return session.query(Strategy).all()
    
    def get_by_name(self, name: str) -> Optional[Strategy]:
        with self.db.get_session() as session:
            return session.query(Strategy).filter(Strategy.name == name).first()
    
    def create(self, name: str, description: str, params: Dict) -> Strategy:
        with self.db.get_session() as session:
            strategy = Strategy(
                name=name,
                description=description,
                params=params,
                enabled=True
            )
            session.add(strategy)
            session.commit()
            session.refresh(strategy)
            return strategy
    
    def update(self, name: str, params: Dict) -> Optional[Strategy]:
        with self.db.get_session() as session:
            strategy = session.query(Strategy).filter(Strategy.name == name).first()
            if strategy:
                strategy.params = params
                strategy.updated_at = datetime.now()
                session.commit()
                session.refresh(strategy)
            return strategy
    
    def delete(self, name: str) -> bool:
        with self.db.get_session() as session:
            result = session.query(Strategy).filter(Strategy.name == name).delete()
            session.commit()
            return result > 0


class StockWatchRepository:
    """自选股仓储"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def get_all(self) -> List[StockWatch]:
        with self.db.get_session() as session:
            return session.query(StockWatch).order_by(StockWatch.added_at.desc()).all()
    
    def add(self, symbol: str, name: str = '', notes: str = '') -> StockWatch:
        with self.db.get_session() as session:
            watch = StockWatch(
                symbol=symbol,
                name=name,
                notes=notes
            )
            session.add(watch)
            session.commit()
            session.refresh(watch)
            return watch
    
    def remove(self, symbol: str) -> bool:
        with self.db.get_session() as session:
            result = session.query(StockWatch).filter(StockWatch.symbol == symbol).delete()
            session.commit()
            return result > 0


class OrderRepository:
    """订单仓储"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def get_all(self, limit: int = 100) -> List[Order]:
        with self.db.get_session() as session:
            return session.query(Order).order_by(Order.created_at.desc()).limit(limit).all()
    
    def create(self, order_data: Dict) -> Order:
        with self.db.get_session() as session:
            order = Order(**order_data)
            session.add(order)
            session.commit()
            session.refresh(order)
            return order


class BacktestRepository:
    """回测记录仓储"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def save(self, result: Dict) -> BacktestRecord:
        with self.db.get_session() as session:
            record = BacktestRecord(**result)
            session.add(record)
            session.commit()
            session.refresh(record)
            return record
    
    def get_history(self, strategy_name: str = None, limit: int = 20) -> List[BacktestRecord]:
        with self.db.get_session() as session:
            query = session.query(BacktestRecord)
            if strategy_name:
                query = query.filter(BacktestRecord.strategy_name == strategy_name)
            return query.order_by(BacktestRecord.created_at.desc()).limit(limit).all()
    
    def get_best(self, strategy_name: str) -> Optional[BacktestRecord]:
        with self.db.get_session() as session:
            return session.query(BacktestRecord).filter(
                BacktestRecord.strategy_name == strategy_name
            ).order_by(BacktestRecord.total_return.desc()).first()


# 便捷函数
def get_db() -> Database:
    return Database()


# 初始化数据库
db = Database()
