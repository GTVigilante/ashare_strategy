# A股量化交易系统

## 架构

```
┌─────────────────────────────────────────┐
│              Web (Streamlit)            │  ← 前端
└─────────────────┬───────────────────────┘
                   │
┌─────────────────▼───────────────────────┐
│              API (FastAPI)              │  ← 后端
└─────────────────┬───────────────────────┘
                   │
┌─────────────────▼───────────────────────┐
│         策略引擎 (Backtrader)           │  ← 信号生成
└─────────────────┬───────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌───────────────┐     ┌───────────────┐
│  QMT / vn.py │     │   数据库      │
│   实盘交易    │     │ SQLite+Redis │
└───────────────┘     └───────────────┘
```

## 目录结构

```
astock_trader/
├── __init__.py
├── config/              # 配置
│   └── settings.py
├── models/              # 数据模型
│   ├── database.py
│   └── schemas.py
├── strategies/           # 策略
│   ├── base.py         # 基类
│   ├── tail_strategy.py
│   └── config.yaml
├── execution/           # 执行层
│   └── executor.py
├── api/                # FastAPI
│   └── main.py
├── web/                # Streamlit
│   └── app.py
├── data/               # 数据存储
└── requirements.txt
```

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
# 后端 API
uvicorn api.main:app --reload --port 8000

# 前端 Web
streamlit run web/app.py
```
