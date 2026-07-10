/* @refresh reload */
import { useState } from 'react';
import {
  Layout,
  Menu,
  Typography,
  Button,
  Space,
  Drawer,
} from 'antd';
import {
  DashboardOutlined,
  SearchOutlined,
  ExperimentOutlined,
  SettingOutlined,
  StarOutlined,
  MenuOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';

import Dashboard from './pages/Dashboard';
import Screening from './pages/Screening';
import Backtest from './pages/Backtest';
import Config from './pages/Config';
import Watchlist from './pages/Watchlist';
import './App.css';

const { Header, Content, Sider } = Layout;
const { Title, Text } = Typography;

const ACCESS_PASSWORD = '828844';

type PageKey = 'dashboard' | 'screening' | 'backtest' | 'watchlist' | 'config';

function App() {
  const [authenticated, setAuthenticated] = useState(false);
  const [password, setPassword] = useState('');
  const [collapsed, setCollapsed] = useState(false);
  const [currentPage, setCurrentPage] = useState<PageKey>('dashboard');
  const [drawerOpen, setDrawerOpen] = useState(false);

  const handleLogin = () => {
    if (password === ACCESS_PASSWORD) {
      setAuthenticated(true);
    }
  };

  const menuItems: MenuProps['items'] = [
    { key: 'dashboard', icon: <DashboardOutlined />, label: '仪表盘' },
    { key: 'screening', icon: <SearchOutlined />, label: '选股' },
    { key: 'backtest', icon: <ExperimentOutlined />, label: '回测' },
    { key: 'watchlist', icon: <StarOutlined />, label: '自选股' },
    { key: 'config', icon: <SettingOutlined />, label: '配置' },
  ];

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard': return <Dashboard />;
      case 'screening': return <Screening />;
      case 'backtest': return <Backtest />;
      case 'watchlist': return <Watchlist />;
      case 'config': return <Config />;
      default: return <Dashboard />;
    }
  };

  const handleMenuClick = (key: PageKey) => {
    setCurrentPage(key);
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

          <Space direction="vertical" style={{ width: '100%' }} size="middle">
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
          onClick={({ key }) => setCurrentPage(key as PageKey)}
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
        width={280}
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
          </div>
        </Header>

        <Content className="content-area">
          <div className="content-wrapper">
            {renderPage()}
          </div>
        </Content>
      </Layout>

      {/* 浮窗帮助按钮 */}
      <a
        href="/docs/guide.html"
        target="_blank"
        rel="noopener noreferrer"
        className="help-float-btn"
        title="使用指南"
      >
        <QuestionCircleOutlined style={{ fontSize: 24 }} />
      </a>
    </Layout>
  );
}

export default App;
