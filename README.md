# A 股策略与交易系统

本仓库包含尾盘策略研究框架、FastAPI 交易服务和 React 管理界面。

## 目录

- `astock_tail_strategy/`：基于 AKShare 和 Backtrader 的独立策略研究、选股与回测工具。
- `astock_trader/`：FastAPI API、SQLite 数据层及策略服务。
- `astock_trader_react/`：React + TypeScript 管理界面。

## 本地启动

要求 Python 3.12 和 Node.js 20+。

### 后端

```bash
cd astock_trader
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --host 127.0.0.1 --port 8000
```

健康检查：<http://127.0.0.1:8000/api/health>

### React 前端

```bash
cd astock_trader_react/frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 8888
```

访问 <http://127.0.0.1:8888>。

## 当前状态

前后端的仪表盘、自选股、策略配置、真实涨停池选股和单股日线回测可以本地运行。回测采用“信号日收盘买入、下一交易日开盘卖出”的日线近似模型，并非分钟级真实成交；这些结果不能直接用于投资决策或实盘交易。

前端口令仅用于本地演示，无法替代后端身份认证。不要将服务直接暴露到公网。实盘使用前需要补充服务端认证、真实行情接入、完整回测、风控、测试和部署加固。

## 验证

```bash
cd astock_trader_react/frontend
npm run build

cd ../../../astock_trader
./venv/bin/python -m compileall -q api models strategies
```

## 风险提示

本项目仅用于学习与研究，不构成投资建议。市场有风险，实盘前请使用独立数据集充分验证，并进行模拟盘测试。
