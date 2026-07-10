#!/bin/bash
# 启动A股量化交易系统

# 项目目录
cd "$(dirname "$0")"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3.12 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "检查依赖..."
pip install -q streamlit fastapi uvicorn sqlalchemy akshare backtrader pandas numpy plotly pyyaml python-dotenv requests 2>/dev/null

# 启动 Streamlit (端口 8888)
echo ""
echo "======================================"
echo "启动 Web 服务..."
echo "访问地址: http://localhost:8888"
echo "访问密码: 828844"
echo "======================================"
echo ""

streamlit run web/app.py --server.port 8888 --server.address 0.0.0.0
