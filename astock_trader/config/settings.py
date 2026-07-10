"""
配置设置
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据库
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/data/trader.db")

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# API配置
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", 8000))
APP_PASSWORD = os.getenv("APP_PASSWORD", "")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", 8 * 60 * 60))
CORS_ORIGINS = [origin.strip() for origin in os.getenv(
    "CORS_ORIGINS", "http://127.0.0.1:8888,http://localhost:8888"
).split(",") if origin.strip()]

# Web配置
WEB_PORT = int(os.getenv("WEB_PORT", 8501))

# 数据配置
DATA_CACHE_TTL = 300  # 缓存5分钟

# 交易配置
INITIAL_CASH = float(os.getenv("INITIAL_CASH", 100000))
COMMISSION = float(os.getenv("COMMISSION", 0.003))  # 千分之三

# 券商API配置（待填写）
QMT_PATH = os.getenv("QMT_PATH", "")
QMT_ACCOUNT = os.getenv("QMT_ACCOUNT", "")
QMT_PASSWORD = os.getenv("QMT_PASSWORD", "")
