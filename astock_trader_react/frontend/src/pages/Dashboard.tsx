// 仪表盘页面
import { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Progress,
  Spin,
  Typography,
  Space,
  Button,
  Alert,
} from 'antd';

import {
  DollarOutlined,
  RiseOutlined,
  TrophyOutlined,
  ThunderboltOutlined,
  SafetyOutlined,
  SearchOutlined,
  ExperimentOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

import { dashboardApi } from '../api';
import type { DashboardData, StockCandidate } from '../types/api';

const { Title, Text } = Typography;

export default function Dashboard() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<DashboardData | null>(null);
  const [todayStocks, setTodayStocks] = useState<StockCandidate[]>([]);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [dashboardRes, stocksRes] = await Promise.all([
        dashboardApi.get(),
        dashboardApi.todayStocks(),
      ]);

      if (dashboardRes.code === 0) {
        setData(dashboardRes.data);
      }

      if (stocksRes.code === 0) {
        setTodayStocks(stocksRes.data.candidates || []);
      }
    } catch (error) {
      console.error('获取数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const positionColumns: any = [
    {
      title: '股票',
      dataIndex: 'symbol',
      key: 'symbol',
      render: (text, record) => (
        <Space>
          <Tag color="blue">{text}</Tag>
          <span>{record.name}</span>
        </Space>
      ),
    },
    {
      title: '持仓数量',
      dataIndex: 'quantity',
      key: 'quantity',
    },
    {
      title: '成本价',
      dataIndex: 'cost',
      key: 'cost',
      render: (v) => v.toFixed(2),
    },
    {
      title: '现价',
      dataIndex: 'price',
      key: 'price',
      render: (v) => v.toFixed(2),
    },
    {
      title: '盈亏',
      key: 'profit',
      render: (_, record) => (
        <span style={{ color: record.profit >= 0 ? '#52c41a' : '#ff4d4f' }}>
          {record.profit >= 0 ? '+' : ''}
          {record.profit.toFixed(2)} ({record.profit_rate.toFixed(2)}%)
        </span>
      ),
    },
  ];

  const stockColumns: any = [
    {
      title: '股票',
      dataIndex: 'symbol',
      key: 'symbol',
      render: (text, record) => (
        <Space orientation="vertical" size={0}>
          <Tag color="gold">{text}</Tag>
          <span style={{ fontSize: 12 }}>{record.name}</span>
        </Space>
      ),
    },
    {
      title: '收盘价',
      dataIndex: 'close',
      key: 'close',
      render: (v) => v?.toFixed(2),
    },
    {
      title: '换手率',
      dataIndex: 'turnover_rate',
      key: 'turnover_rate',
      render: (v) => `${v?.toFixed(1)}%`,
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      render: (v) => <Progress percent={(v || 0) * 100} size="small" />,
    },
  ];

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div className="dashboard">
      <Row justify="space-between" align="middle" gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col>
          <Title level={2} style={{ marginBottom: 4 }}>研究工作台</Title>
          <Text type="secondary">真实行情研究、样本外验证与受控模拟盘</Text>
        </Col>
        <Col>
          <Space wrap>
            <Button icon={<SearchOutlined />} onClick={() => navigate('/screening')}>运行选股</Button>
            <Button icon={<ExperimentOutlined />} onClick={() => navigate('/backtest')}>开始回测</Button>
            <Button type="primary" icon={<SafetyCertificateOutlined />} onClick={() => navigate('/paper')}>进入模拟盘</Button>
          </Space>
        </Col>
      </Row>
      <Alert
        type="info"
        showIcon
        title="当前为研究与模拟模式"
        description="行情来自 AKShare（东方财富主源、失败时切换新浪）；模拟盘不连接券商，策略需通过样本外诊断才可申请准入。"
        style={{ marginBottom: 20 }}
      />

      {/* 账户概览 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="总资产"
              value={data?.account.total_assets}
              prefix={<DollarOutlined />}
              precision={2}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="可用资金"
              value={data?.account.cash}
              precision={2}
              prefix="$"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="持仓市值"
              value={data?.account.stocks_value}
              precision={2}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card
            style={{
              background:
                (data?.account.today_profit_rate || 0) >= 0
                  ? 'linear-gradient(135deg, #52c41a22, #52c41a11)'
                  : 'linear-gradient(135deg, #ff4d4f22, #ff4d4f11)',
            }}
          >
            <Statistic
              title="今日收益"
              value={data?.account.today_profit}
              precision={2}
              prefix={(data?.account.today_profit_rate || 0) >= 0 ? '+' : ''}
              suffix={`(${data?.account.today_profit_rate?.toFixed(2)}%)`}
              valueStyle={{
                color:
                  (data?.account.today_profit_rate || 0) >= 0
                    ? '#52c41a'
                    : '#ff4d4f',
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* 性能指标 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="累计收益率"
              value={data?.backtest.total_return}
              precision={2}
              suffix="%"
              prefix={<RiseOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="胜率"
              value={data?.backtest.win_rate}
              precision={1}
              suffix="%"
              prefix={<TrophyOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="夏普比率"
              value={data?.backtest.sharpe_ratio}
              precision={2}
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="最大回撤"
              value={data?.backtest.max_drawdown}
              precision={1}
              suffix="%"
              prefix={<SafetyOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 持仓和今日选股 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={12}>
          <Card title="当前持仓" extra={<Tag>{data?.positions.length || 0} 只</Tag>}>
            <Table
              columns={positionColumns}
              dataSource={data?.positions || []}
              rowKey="symbol"
              pagination={false}
              size="small"
              locale={{ emptyText: '暂无持仓' }}
            />
          </Card>
        </Col>
        <Col xs={24} xl={12}>
          <Card
            title="今日候选"
            extra={
              <Tag color="gold">
                {todayStocks.length} 只符合条件的股票
              </Tag>
            }
          >
            <Table
              columns={stockColumns}
              dataSource={todayStocks}
              rowKey="symbol"
              pagination={false}
              size="small"
              locale={{ emptyText: '暂无候选股票' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
