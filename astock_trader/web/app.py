"""
Streamlit Web 前端
A股量化交易系统
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 配置
API_BASE_URL = "http://localhost:8000/api"
ACCESS_PASSWORD = "828844"

# 页面配置
st.set_page_config(
    page_title="A股量化交易系统",
    page_icon="📈",
    layout="wide"
)


# ============== 密码验证 ==============

def check_password():
    """验证访问密码"""
    if 'password_verified' not in st.session_state:
        st.session_state['password_verified'] = False
    
    if st.session_state['password_verified']:
        return True
    
    st.markdown("""
    <style>
    .login-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 50px;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 16px;
        margin: 50px auto;
        max-width: 400px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🔐 请输入访问密码")
    
    password = st.text_input("密码", type="password", key="password_input")
    
    if password:
        if password == ACCESS_PASSWORD:
            st.session_state['password_verified'] = True
            st.rerun()
        else:
            st.error("密码错误，请重试")
            return False
    
    st.stop()
    return False


# 验证密码
check_password()


# ============== 辅助函数 ==============

@st.cache_data(ttl=300)
def fetch_strategies():
    """获取策略列表"""
    try:
        response = requests.get(f"{API_BASE_URL}/strategies", timeout=5)
        return response.json() if response.status_code == 200 else []
    except:
        return []


@st.cache_data(ttl=300)
def fetch_watchlist():
    """获取自选股"""
    try:
        response = requests.get(f"{API_BASE_URL}/watch", timeout=5)
        return response.json() if response.status_code == 200 else []
    except:
        return []


@st.cache_data(ttl=300)
def fetch_backtest_history(strategy: str = None):
    """获取回测历史"""
    try:
        url = f"{API_BASE_URL}/backtest/history"
        if strategy:
            url += f"?strategy_name={strategy}"
        response = requests.get(url, timeout=5)
        return response.json() if response.status_code == 200 else []
    except:
        return []


def add_to_watchlist(symbol: str, name: str):
    """添加自选股"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/watch",
            json={"symbol": symbol, "name": name},
            timeout=5
        )
        return response.status_code == 200
    except:
        return False


def remove_from_watchlist(symbol: str):
    """删除自选股"""
    try:
        response = requests.delete(f"{API_BASE_URL}/watch/{symbol}", timeout=5)
        return response.status_code == 200
    except:
        return False


# ============== 侧边栏 ==============

def sidebar():
    """侧边栏"""
    st.sidebar.title("📊 A股量化系统")
    
    # 导航
    page = st.sidebar.radio(
        "功能",
        ["📈 选股", "🔄 回测", "⭐ 自选", "⚙️ 策略配置", "📋 订单记录"]
    )
    
    st.sidebar.markdown("---")
    
    # 系统状态
    st.sidebar.subheader("系统状态")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            st.sidebar.success("✅ 服务正常")
        else:
            st.sidebar.error("❌ 服务异常")
    except:
        st.sidebar.warning("⚠️ 后端未启动")
        st.sidebar.caption("运行: uvicorn api.main:app --reload")
    
    return page


# ============== 选股页面 ==============

def page_screening():
    """选股页面"""
    st.header("📈 尾盘选股")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        date = st.date_input("日期", datetime.now())
        date_str = date.strftime("%Y%m%d")
    
    with col2:
        strategies = fetch_strategies()
        strategy_names = [s['name'] for s in strategies] if strategies else ["尾盘策略"]
        selected_strategy = st.selectbox("策略", strategy_names)
    
    with col3:
        st.write("")  # 空白
        st.write("")  # 空白
        if st.button("🔍 开始筛选", type="primary", use_container_width=True):
            st.session_state['screen_triggered'] = True
    
    st.markdown("---")
    
    # 选股条件
    st.subheader("选股条件")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("换手率", "> 3%")
        st.metric("流通市值", "< 200亿")
    with col2:
        st.metric("振幅", "< 5%")
        st.metric("股价", "4-30元")
    with col3:
        st.metric("量比", "> 1.2")
        st.metric("昨日涨停", "必须")
    
    st.markdown("---")
    
    # 筛选结果
    st.subheader("筛选结果")
    
    if st.session_state.get('screen_triggered', False):
        # TODO: 调用API获取筛选结果
        st.info("数据接口待接入，请先启动后端服务")
        
        # 示例数据
        example_data = {
            "date": date_str,
            "strategy": selected_strategy,
            "stocks": [
                {"代码": "300001", "名称": "测试股票", "收盘价": 15.5, "换手率": 5.2, "量比": 1.5},
                {"代码": "300002", "名称": "示例股票", "收盘价": 22.3, "换手率": 4.1, "量比": 1.8},
            ]
        }
        
        if example_data.get("stocks"):
            df = pd.DataFrame(example_data["stocks"])
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("暂无符合条件的股票")
    else:
        st.info("点击「开始筛选」获取候选股票")


# ============== 回测页面 ==============

def page_backtest():
    """回测页面"""
    st.header("🔄 策略回测")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("回测参数")
        
        # 选择策略
        strategies = fetch_strategies()
        strategy_names = [s['name'] for s in strategies] if strategies else ["尾盘策略"]
        selected_strategy = st.selectbox("选择策略", strategy_names)
        
        # 日期范围
        start_date = st.date_input("开始日期", datetime.now() - timedelta(days=90))
        end_date = st.date_input("结束日期", datetime.now())
        
        # 初始资金
        initial_cash = st.number_input("初始资金", value=100000, step=10000)
        
        # 运行回测
        if st.button("▶️ 运行回测", type="primary", use_container_width=True):
            st.session_state['backtest_triggered'] = True
    
    with col2:
        st.subheader("回测结果")
        
        if st.session_state.get('backtest_triggered', False):
            # TODO: 调用API运行回测
            st.info("数据接口待接入")
            
            # 示例回测结果
            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a:
                st.metric("总收益率", "+12.5%")
            with col_b:
                st.metric("夏普比率", "1.85")
            with col_c:
                st.metric("最大回撤", "-8.2%")
            with col_d:
                st.metric("胜率", "65%")
            
            # 收益曲线图（示例）
            fig = px.line(
                x=list(range(90)),
                y=[100000 + i*150 + (i**1.5)*10 for i in range(90)],
                title="收益曲线"
            )
            fig.update_layout(
                xaxis_title="交易日",
                yaxis_title="账户价值",
                template="plotly_dark"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("配置参数后点击「运行回测」")
    
    # 回测历史
    st.markdown("---")
    st.subheader("历史回测")
    
    history = fetch_backtest_history()
    if history:
        df = pd.DataFrame(history)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("暂无回测记录")


# ============== 自选页面 ==============

def page_watchlist():
    """自选股页面"""
    st.header("⭐ 自选股管理")
    
    # 添加自选股
    with st.expander("➕ 添加自选股"):
        col1, col2 = st.columns([1, 2])
        with col1:
            symbol = st.text_input("股票代码", placeholder="如: 000001")
        with col2:
            name = st.text_input("股票名称", placeholder="如: 平安银行")
        
        if st.button("添加", use_container_width=True):
            if symbol:
                if add_to_watchlist(symbol, name):
                    st.success(f"已添加 {symbol} {name}")
                    st.rerun()
                else:
                    st.error("添加失败")
    
    st.markdown("---")
    
    # 自选股列表
    st.subheader("我的自选")
    
    watchlist = fetch_watchlist()
    
    if watchlist:
        df = pd.DataFrame(watchlist)
        st.dataframe(
            df,
            columns=["symbol", "name", "notes", "added_at"],
            use_container_width=True
        )
        
        # 删除操作
        if st.button("🗑️ 删除选中"):
            st.info("功能待实现")
    else:
        st.info("暂无自选股，请添加")


# ============== 策略配置页面 ==============

def page_strategy_config():
    """策略配置页面"""
    st.header("⚙️ 策略配置")
    
    strategies = fetch_strategies()
    
    if not strategies:
        st.warning("暂无策略，请检查后端服务")
        return
    
    # 选择策略
    strategy_names = [s['name'] for s in strategies]
    selected = st.selectbox("选择策略", strategy_names)
    
    # 获取选中策略详情
    strategy = next((s for s in strategies if s['name'] == selected), None)
    
    if strategy:
        st.subheader(f"配置: {strategy['name']}")
        
        if strategy.get('description'):
            st.caption(strategy['description'])
        
        st.markdown("---")
        
        # 参数配置
        params = strategy.get('params', {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.number_input(
                "换手率 (%)",
                value=float(params.get('min_turnover_rate', 3.0)),
                step=0.1,
                key="turnover"
            )
            st.number_input(
                "流通市值上限 (亿)",
                value=float(params.get('max_market_cap', 200.0)),
                step=10.0,
                key="market_cap"
            )
            st.number_input(
                "振幅上限 (%)",
                value=float(params.get('max_amplitude', 5.0)),
                step=0.1,
                key="amplitude"
            )
        
        with col2:
            st.number_input(
                "股价下限",
                value=float(params.get('min_price', 4.0)),
                step=0.5,
                key="min_price"
            )
            st.number_input(
                "股价上限",
                value=float(params.get('max_price', 30.0)),
                step=0.5,
                key="max_price"
            )
            st.number_input(
                "量比要求",
                value=float(params.get('min_volume_ratio', 1.2)),
                step=0.1,
                key="volume_ratio"
            )
        
        st.markdown("---")
        
        # 卖出配置
        st.subheader("卖出设置")
        
        col1, col2 = st.columns(2)
        with col1:
            st.number_input(
                "高开阈值 (%)",
                value=float(params.get('gap_up_threshold', 1.0)),
                step=0.1,
                key="gap_up"
            )
            st.number_input(
                "低开止损 (%)",
                value=float(params.get('low_open_stop', 2.0)),
                step=0.1,
                key="low_open"
            )
        with col2:
            st.number_input(
                "止损线 (%)",
                value=float(params.get('stop_loss', 3.0)),
                step=0.1,
                key="stop_loss"
            )
        
        # 保存按钮
        if st.button("💾 保存配置", type="primary", use_container_width=True):
            st.success("配置已保存")


# ============== 订单页面 ==============

def page_orders():
    """订单记录页面"""
    st.header("📋 订单记录")
    
    try:
        response = requests.get(f"{API_BASE_URL}/orders", timeout=5)
        if response.status_code == 200:
            orders = response.json()
            
            if orders:
                df = pd.DataFrame(orders)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("暂无订单记录")
        else:
            st.warning("获取订单失败")
    except:
        st.info("数据接口待接入，请先启动后端服务")


# ============== 主函数 ==============

def main():
    """主函数"""
    
    # 侧边栏
    page = sidebar()
    
    # 页面内容
    if page == "📈 选股":
        page_screening()
    elif page == "🔄 回测":
        page_backtest()
    elif page == "⭐ 自选":
        page_watchlist()
    elif page == "⚙️ 策略配置":
        page_strategy_config()
    elif page == "📋 订单记录":
        page_orders()
    
    # 页脚
    st.markdown("---")
    st.caption("A股量化交易系统 v1.0.0 | ⚠️ 投资有风险")


if __name__ == "__main__":
    main()
