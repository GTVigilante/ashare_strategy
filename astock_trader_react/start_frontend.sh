#!/bin/bash
# A股量化交易系统 - React前端启动脚本

cd "$(dirname "$0")/frontend"

# 杀掉8888端口的其他进程
lsof -ti :8888 | xargs kill -9 2>/dev/null
sleep 1

echo "======================================"
echo "启动前端服务..."
echo "访问地址: http://localhost:8888"
echo "访问密码: 828844"
echo "======================================"

npm run dev -- --host 0.0.0.0 --port 8888
