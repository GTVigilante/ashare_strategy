# A 股策略与交易系统

本仓库包含尾盘策略研究框架、FastAPI 交易服务和 React 管理界面。

## 一键启动

要求 Python 3.12+、Node.js 20+、npm 和 curl。首次运行会创建本地配置、生成随机登录密码，并安装缺失依赖：

```bash
./start.sh
```

启动成功后访问 <http://127.0.0.1:8888>。终端会在首次配置时显示登录密码；按 `Ctrl+C` 同时停止前后端。

```bash
./start.sh --check       # 仅检查环境
./start.sh --setup-only  # 初始化配置和依赖，但不启动
```

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
cp .env.example .env
# 编辑 .env，为 APP_PASSWORD 设置长随机密码
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

当前可运行功能包括：

- 研究仪表盘和最近一次真实选股结果；
- 东方财富主源、 新浪备用源及磁盘行情缓存；
- 真实涨停池筛选与技术过滤；
- 自选股、标签和一键带入回测；
- 单股回测、三组参数对比、等权组合回测；
- 70/30 样本外验证和多窗口 Walk-Forward 诊断；
- 诊断准入、仓位/亏损/回撤限制下的内存模拟盘；
- 数据库策略配置，并统一作用于选股、回测和模拟盘准入。

回测采用“信号日收盘买入、下一交易日开盘卖出”的日线近似模型，并非分钟级真实成交；模拟盘不连接券商，价格由用户输入用于验证风控流程。系统不公开尚未实现的实盘信号或券商订单接口，这些结果不能直接用于投资决策或实盘交易。

登录口令由后端环境变量 `APP_PASSWORD` 验证，成功后签发默认有效期 8 小时的内存会话令牌。令牌会在后端重启后失效。不要将 `.env` 提交到仓库，也不要将服务直接暴露到公网；实盘使用前仍需补充持久化用户体系、HTTPS、限流、风控和部署加固。

历史行情默认先读取 `astock_trader/data/cache/daily/` 本地缓存。缓存未命中时先请求东方财富，连续失败后自动切换新浪数据源；缓存目录属于运行数据，不会提交到 Git。

## 验证

```bash
cd astock_trader_react/frontend
npm run lint
npm test
npm run build

cd ../../../astock_trader
./venv/bin/python -m unittest discover -s tests -v
./venv/bin/python -m compileall -q api models services strategies
```

推送到 `main` 或创建 Pull Request 时，GitHub Actions 会自动运行后端单元测试、Python 编译检查和前端生产构建。CI 不访问外部行情接口，避免第三方服务波动影响代码质量判断。

## 风险提示

本项目仅用于学习与研究，不构成投资建议。市场有风险，实盘前请使用独立数据集充分验证，并进行模拟盘测试。
