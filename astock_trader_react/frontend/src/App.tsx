/* @refresh reload */
import { lazy, Suspense, useEffect, useState } from 'react';
import {
  Layout,
  Menu,
  Typography,
  Button,
  Space,
  Drawer,
  message,
  Spin,
} from 'antd';
import {
  DashboardOutlined,
  SearchOutlined,
  ExperimentOutlined,
  SettingOutlined,
  StarOutlined,
  SafetyCertificateOutlined,
  MenuOutlined,
  QuestionCircleOutlined,
  LogoutOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';

import './App.css';
import { authApi } from './api';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const Screening = lazy(() => import('./pages/Screening'));
const Backtest = lazy(() => import('./pages/Backtest'));
const Config = lazy(() => import('./pages/Config'));
const Watchlist = lazy(() => import('./pages/Watchlist'));
const PaperTrading = lazy(() => import('./pages/PaperTrading'));

const { Header, Content, Sider } = Layout;
const { Title, Text } = Typography;

type PageKey = 'dashboard' | 'screening' | 'backtest' | 'paper' | 'watchlist' | 'config';
const pagePaths: Record<PageKey, string> = {
  dashboard: '/dashboard', screening: '/screening', backtest: '/backtest',
  paper: '/paper', watchlist: '/watchlist', config: '/config',
};

function App() {
  const [authenticated, setAuthenticated] = useState(authApi.hasSession());
  const [password, setPassword] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const currentPage = (Object.entries(pagePaths).find(([, path]) => location.pathname === path)?.[0] || 'dashboard') as PageKey;

  useEffect(() => {
    const handleUnauthorized = () => setAuthenticated(false);
    window.addEventListener('ashare:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('ashare:unauthorized', handleUnauthorized);
  }, []);

  const handleLogin = async () => {
    if (!password) return;
    setLoginLoading(true);
    try {
      const response = await authApi.login(password);
      if (response.code === 0) {
        setPassword('');
        setAuthenticated(true);
      }
    } catch (error) {
      const detail = (error as any)?.response?.data?.detail;
      message.error(detail || '登录失败');
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } finally {
      setAuthenticated(false);
    }
  };

  const menuItems: MenuProps['items'] = [
    { key: 'dashboard', icon: <DashboardOutlined />, label: '仪表盘' },
    { key: 'screening', icon: <SearchOutlined />, label: '选股' },
    { key: 'backtest', icon: <ExperimentOutlined />, label: '回测' },
    { key: 'paper', icon: <SafetyCertificateOutlined />, label: '模拟盘' },
    { key: 'watchlist', icon: <StarOutlined />, label: '自选股' },
    { key: 'config', icon: <SettingOutlined />, label: '配置' },
  ];

  const handleMenuClick = (key: PageKey) => {
    navigate(pagePaths[key]);
    setDrawerOpen(false);
  };

  // 登录页面
  if (!authenticated) {
    return (
      <div className="login-container">
        <div className="login-box">
          <div style={{ textAlign: 'center', marginBottom: 32 }}>
            <Title level={2} className="login-title">📈 A股量化系统</Title>
            <Text type="secondary">请输入访问密码</Text>
          </div>

          <Space orientation="vertical" style={{ width: '100%' }} size="middle">
            <input
              type="password"
              className="login-input"
              placeholder="输入密码"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
            />
            <Button
              type="primary"
              size="large"
              block
              onClick={handleLogin}
              loading={loginLoading}
            >
              进入系统
            </Button>
          </Space>
        </div>
      </div>
    );
  }

  // 主应用 - 响应式布局
  return (
    <Layout className="app-layout">
      {/* 桌面端侧边栏 */}
      <Sider
        className="desktop-sider"
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="dark"
        width={220}
        breakpoint="lg"
        collapsedWidth={80}
        onBreakpoint={(broken) => {
          if (broken) setCollapsed(true);
        }}
      >
        <div className="logo">
          {!collapsed && (
            <Title level={4} style={{ color: '#fff', margin: 0 }}>
              📈 量化系统
            </Title>
          )}
          {collapsed && <span style={{ fontSize: 20 }}>📈</span>}
        </div>

        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[currentPage]}
          items={menuItems}
          onClick={({ key }) => handleMenuClick(key as PageKey)}
        />
      </Sider>

      {/* 移动端顶部导航 */}
      <Layout className="mobile-header">
        <Header className="mobile-nav">
          <div className="mobile-nav-content">
            <Button
              type="text"
              icon={<MenuOutlined />}
              onClick={() => setDrawerOpen(true)}
              className="menu-btn"
            />
            <Title level={4} className="mobile-title">A股量化</Title>
            <div style={{ width: 40 }} />
          </div>
        </Header>
      </Layout>

      {/* 移动端抽屉菜单 */}
      <Drawer
        title="菜单"
        placement="left"
        onClose={() => setDrawerOpen(false)}
        open={drawerOpen}
        size={280}
        className="mobile-drawer"
      >
        <Menu
          mode="inline"
          selectedKeys={[currentPage]}
          items={menuItems}
          onClick={({ key }) => handleMenuClick(key as PageKey)}
        />
      </Drawer>

      <Layout className="main-layout">
        <Header className="desktop-header" style={{ padding: '0 16px' }}>
          <div className="header-content">
            <Title level={4} style={{ margin: 0, fontSize: 16 }}>
              A股量化交易系统
            </Title>
            <Text type="secondary" className="header-date">
              {new Date().toLocaleDateString('zh-CN', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </Text>
            <Button type="text" icon={<LogoutOutlined />} onClick={handleLogout}>退出</Button>
          </div>
        </Header>

        <Content className="content-area">
          <div className="content-wrapper">
            <Suspense fallback={<div style={{ padding: 80, textAlign: 'center' }}><Spin size="large" /></div>}>
              <Routes>
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/screening" element={<Screening />} />
                <Route path="/backtest" element={<Backtest />} />
                <Route path="/paper" element={<PaperTrading />} />
                <Route path="/watchlist" element={<Watchlist />} />
                <Route path="/config" element={<Config />} />
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Routes>
            </Suspense>
          </div>
        </Content>
      </Layout>

      {/* 浮窗帮助按钮 */}
      <a
        href="https://github.com/GTVigilante/ashare_strategy#readme"
        target="_blank"
        rel="noopener noreferrer"
        className="help-float-btn"
        title="项目文档"
      >
        <QuestionCircleOutlined style={{ fontSize: 24 }} />
      </a>
    </Layout>
  );
}

export default App;
