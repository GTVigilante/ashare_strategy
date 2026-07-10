// 回测页面
import { useEffect, useState } from 'react';
import {
  Card,
  Row,
  Col,
  Form,
  DatePicker,
  InputNumber,
  Select,
  Button,
  Statistic,
  Table,
  Tag,
  Typography,
  Space,
  Spin,
  message,
} from 'antd';

import {
  PlayCircleOutlined,
  HistoryOutlined,
  RiseOutlined,
  FallOutlined,
  TrophyOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

import { backtestApi } from '../api';
import type { BacktestResult, BacktestTrade } from '../types/api';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

export default function Backtest() {
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<BacktestResult[]>([]);
  const [currentResult, setCurrentResult] = useState<BacktestResult | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const res = await backtestApi.history({ page_size: 10 });
      if (res.code === 0) {
        setHistory(res.data.list || []);
      }
    } catch (error) {
      console.error('获取历史失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRunBacktest = async (values: any) => {
    try {
      setLoading(true);
      const res = await backtestApi.run({
        strategy: values.strategy,
        start_date: values.dates[0].format('YYYYMMDD'),
        end_date: values.dates[1].format('YYYYMMDD'),
        initial_cash: values.initial_cash || 100000,
      });

      if (res.code === 0) {
        setCurrentResult(res.data);
        message.success('回测完成');
        fetchHistory();
      } else {
        message.error(res.message);
      }
    } catch (error) {
      message.error('回测失败');
    } finally {
      setLoading(false);
    }
  };

  const tradeColumns: any = [
    {
      title: '股票',
      key: 'stock',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Tag color="blue">{record.symbol}</Tag>
          <Text>{record.name}</Text>
        </Space>
      ),
    },
    {
      title: '买入日期',
      dataIndex: 'buy_date',
      key: 'buy_date',
    },
    {
      title: '买入价',
      dataIndex: 'buy_price',
      key: 'buy_price',
      render: (v) => v.toFixed(2),
    },
    {
      title: '卖出日期',
      dataIndex: 'sell_date',
      key: 'sell_date',
    },
    {
      title: '卖出价',
      dataIndex: 'sell_price',
      key: 'sell_price',
      render: (v) => v.toFixed(2),
    },
    {
      title: '收益率',
      dataIndex: 'profit_percent',
      key: 'profit_percent',
      render: (v) => (
        <Text
          style={{ color: v >= 0 ? '#52c41a' : '#ff4d4f', fontWeight: 'bold' }}
        >
          {v >= 0 ? '+' : ''}
          {v.toFixed(2)}%
        </Text>
      ),
    },
    {
      title: '持仓天数',
      dataIndex: 'hold_days',
      key: 'hold_days',
    },
    {
      title: '卖出原因',
      dataIndex: 'reason',
      key: 'reason',
      ellipsis: true,
    },
  ];

  const historyColumns: any = [
    {
      title: '策略',
      dataIndex: 'strategy',
      key: 'strategy',
    },
    {
      title: '回测区间',
      key: 'period',
      render: (_, record) =>
        `${record.start_date} ~ ${record.end_date}`,
    },
    {
      title: '收益率',
      dataIndex: 'total_return',
      key: 'total_return',
      render: (v) => (
        <Text style={{ color: v >= 0 ? '#52c41a' : '#ff4d4f' }}>
          {v >= 0 ? '+' : ''}
          {v.toFixed(2)}%
        </Text>
      ),
    },
    {
      title: '夏普比率',
      dataIndex: 'sharpe_ratio',
      key: 'sharpe_ratio',
      render: (v) => v.toFixed(2),
    },
    {
      title: '胜率',
      dataIndex: 'win_rate',
      key: 'win_rate',
      render: (v) => `${v.toFixed(1)}%`,
    },
    {
      title: '回测日期',
      dataIndex: 'created_at',
      key: 'created_at',
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Button type="link" onClick={() => setCurrentResult(record)}>
          查看详情
        </Button>
      ),
    },
  ];

  return (
    <div className="backtest">
      <Title level={2}>🔄 策略回测</Title>

      <Row gutter={16}>
        {/* 回测参数 */}
        <Col span={8}>
          <Card title="回测参数">
            <Form
              form={form}
              layout="vertical"
              onFinish={handleRunBacktest}
              initialValues={{
                strategy: '尾盘策略',
                dates: [
                  dayjs().subtract(6, 'month'),
                  dayjs().subtract(1, 'day'),
                ],
                initial_cash: 100000,
              }}
            >
              <Form.Item
                label="策略"
                name="strategy"
                rules={[{ required: true }]}
              >
                <Select
                  options={[
                    { label: '尾盘策略', value: '尾盘策略' },
                    { label: '动量策略', value: '动量策略' },
                    { label: '突破策略', value: '突破策略' },
                  ]}
                />
              </Form.Item>

              <Form.Item
                label="回测区间"
                name="dates"
                rules={[{ required: true }]}
              >
                <RangePicker
                  style={{ width: '100%' }}
                  format="YYYY-MM-DD"
                />
              </Form.Item>

              <Form.Item label="初始资金" name="initial_cash">
                <InputNumber
                  style={{ width: '100%' }}
                  prefix="¥"
                />
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<PlayCircleOutlined />}
                  loading={loading}
                  block
                  size="large"
                >
                  开始回测
                </Button>
              </Form.Item>
            </Form>
          </Card>

          {/* 历史记录 */}
          <Card
            title={<><HistoryOutlined /> 历史回测</>}
            extra={
              <Button type="link" onClick={fetchHistory}>
                刷新
              </Button>
            }
            style={{ marginTop: 16 }}
          >
            <Table
              columns={historyColumns}
              dataSource={history}
              rowKey="id"
              pagination={false}
              size="small"
              loading={loading}
            />
          </Card>
        </Col>

        {/* 回测结果 */}
        <Col span={16}>
          <Card title="回测结果">
            {loading ? (
              <div style={{ textAlign: 'center', padding: 50 }}>
                <Spin size="large" />
              </div>
            ) : currentResult ? (
              <>
                {/* 核心指标 */}
                <Row gutter={16}>
                  <Col span={6}>
                    <Statistic
                      title="总收益率"
                      value={currentResult.total_return}
                      precision={2}
                      suffix="%"
                      prefix={
                        currentResult.total_return >= 0 ? (
                          <RiseOutlined style={{ color: '#52c41a' }} />
                        ) : (
                          <FallOutlined style={{ color: '#ff4d4f' }} />
                        )
                      }
                      valueStyle={{
                        color:
                          currentResult.total_return >= 0
                            ? '#52c41a'
                            : '#ff4d4f',
                      }}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="夏普比率"
                      value={currentResult.sharpe_ratio}
                      precision={2}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="胜率"
                      value={currentResult.win_rate}
                      precision={1}
                      suffix="%"
                      prefix={<TrophyOutlined />}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="最大回撤"
                      value={currentResult.max_drawdown}
                      precision={1}
                      suffix="%"
                      valueStyle={{ color: '#ff4d4f' }}
                    />
                  </Col>
                </Row>

                {/* 收益曲线（简化展示） */}
                <div style={{ margin: '24px 0', textAlign: 'center' }}>
                  <Text type="secondary">收益曲线</Text>
                  <div
                    style={{
                      height: 200,
                      background: '#f0f0f0',
                      borderRadius: 8,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      marginTop: 8,
                    }}
                  >
                    <Text type="secondary">
                      初始: ¥{currentResult.initial_cash.toLocaleString()} → 最终:
                      ¥{currentResult.final_value.toLocaleString()}
                    </Text>
                  </div>
                </div>

                {/* 交易记录 */}
                <Title level={4}>交易记录 ({currentResult.total_trades} 笔)</Title>
                <Table
                  columns={tradeColumns}
                  dataSource={currentResult.trades}
                  rowKey="id"
                  pagination={{ pageSize: 10 }}
                  size="small"
                  scroll={{ x: 1000 }}
                />
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: 100 }}>
                <Text type="secondary">配置参数后点击「开始回测」</Text>
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
