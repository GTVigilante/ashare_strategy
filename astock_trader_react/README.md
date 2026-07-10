# A股量化交易系统 - React版

## 快速启动

### 1. 启动前端（端口 8888）
```bash
cd astock_trader_react
./start_frontend.sh
```

### 2. 启动后端API（端口 8000）
```bash
cd astock_trader
./venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## 访问地址

- 前端: http://localhost:8888
- 密码: 828844

## 技术栈

- **前端**: React 18 + TypeScript + Vite + Ant Design
- **后端**: FastAPI + SQLAlchemy + SQLite
- **数据**: AKShare + Tushare

## 目录结构

```
astock_trader_react/
├── frontend/           # React前端
│   ├── src/
│   │   ├── api/       # API服务层
│   │   ├── pages/     # 页面组件
│   │   ├── types/     # TypeScript类型
│   │   └── App.tsx    # 主应用
│   └── docs/          # API规范文档
│
└── start_frontend.sh  # 启动脚本

astock_trader/          # FastAPI后端（原有项目）
├── api/               # API接口
├── models/            # 数据模型
├── strategies/         # 策略
└── venv/             # Python虚拟环境
```

## 页面功能

1. **📊 仪表盘** - 总资产、收益率、胜率、持仓
2. **📈 选股** - 筛选候选股票
3. **🔄 回测** - 运行策略回测
4. **⭐ 自选股** - 管理自选股
5. **⚙️ 配置** - 策略参数设置

## API规范

详见 `docs/API_SPEC.md`
