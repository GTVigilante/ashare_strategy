// 回测页面
import { lazy, Suspense, useEffect, useState } from 'react';
import {
  Card,
  Row,
  Col,
  Form,
  DatePicker,
  InputNumber,
  Input,
  Select,
  Button,
  Statistic,
  Table,
  Tag,
  Typography,
  Space,
  Spin,
  message,
  Descriptions,
  Alert,
  List,
  Progress,
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
import type { BacktestResult, BacktestTrade, MultiWalkForwardResult, ParameterComparison, WalkForwardResult } from '../types/api';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;
const EquityChart = lazy(() => import('../components/EquityChart'));

export default function Backtest() {
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<BacktestResult[]>([]);
  const [currentResult, setCurrentResult] = useState<BacktestResult | null>(null);
  const [comparison, setComparison] = useState<ParameterComparison[]>([]);
  const [comparing, setComparing] = useState(false);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [walkForwardLoading, setWalkForwardLoading] = useState(false);
  const [walkForward, setWalkForward] = useState<WalkForwardResult | null>(null);
  const [multiWalkLoading, setMultiWalkLoading] = useState(false);
  const [multiWalk, setMultiWalk] = useState<MultiWalkForwardResult | null>(null);
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
        symbols: [values.symbol],
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

  const handleCompare = async () => {
    try {
      const values = await form.validateFields();
      setComparing(true);
      const res = await backtestApi.compare({
        strategy: values.strategy,
        start_date: values.dates[0].format('YYYYMMDD'),
        end_date: values.dates[1].format('YYYYMMDD'),
        initial_cash: values.initial_cash || 100000,
        symbols: [values.symbol],
      });
      if (res.code === 0) setComparison(res.data.ranking || []);
    } catch (error) {
      const detail = (error as any)?.response?.data?.detail;
      if (detail) message.error(detail);
    } finally {
      setComparing(false);
    }
  };

  const handlePortfolio = async () => {
    try {
      const values = await form.validateFields();
      const symbols = String(values.portfolio_symbols || '')
        .split(/[,，\s]+/).map((item) => item.trim()).filter(Boolean);
      if (symbols.length < 2 || symbols.length > 10 || symbols.some((item) => !/^\d{6}$/.test(item))) {
        message.error('请输入 2 至 10 个六位股票代码');
        return;
      }
      setPortfolioLoading(true);
      const res = await backtestApi.portfolio({
        strategy: values.strategy,
        start_date: values.dates[0].format('YYYYMMDD'),
        end_date: values.dates[1].format('YYYYMMDD'),
        initial_cash: values.initial_cash || 100000,
        symbols,
      });
      if (res.code === 0) {
        setCurrentResult(res.data);
        message.success('组合回测完成');
      }
    } catch (error) {
      const detail = (error as any)?.response?.data?.detail;
      if (detail) message.error(detail);
    } finally {
      setPortfolioLoading(false);
    }
  };

  const handleWalkForward = async () => {
    try {
      const values = await form.validateFields();
      setWalkForwardLoading(true);
      const res = await backtestApi.walkForward({
        strategy: values.strategy,
        start_date: values.dates[0].format('YYYYMMDD'),
        end_date: values.dates[1].format('YYYYMMDD'),
        initial_cash: values.initial_cash || 100000,
        symbols: [values.symbol],
      });
      if (res.code === 0) setWalkForward(res.data);
    } catch (error) {
      const detail = (error as any)?.response?.data?.detail;
      if (detail) message.error(detail);
    } finally {
      setWalkForwardLoading(false);
    }
  };

  const handleMultiWalkForward = async () => {
    try {
      const values = await form.validateFields();
      setMultiWalkLoading(true);
      const res = await backtestApi.multiWalkForward({
        strategy: values.strategy,
        start_date: values.dates[0].format('YYYYMMDD'),
        end_date: values.dates[1].format('YYYYMMDD'),
        initial_cash: values.initial_cash || 100000,
        symbols: [values.symbol],
      });
      if (res.code === 0) setMultiWalk(res.data);
    } catch (error) {
      const detail = (error as any)?.response?.data?.detail;
      if (detail) message.error(detail);
    } finally {
      setMultiWalkLoading(false);
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
                symbol: '000001',
                dates: [
                  dayjs().subtract(6, 'month'),
                  dayjs().subtract(1, 'day'),
                ],
                initial_cash: 100000,
                portfolio_symbols: '000001,600000,600036',
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
                label="股票代码"
                name="symbol"
                rules={[
                  { required: true, message: '请输入股票代码' },
                  { pattern: /^\d{6}$/, message: '请输入六位 A 股代码' },
                ]}
                extra="当前版本一次回测一只股票"
              >
                <Input maxLength={6} placeholder="例如 000001" />
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
              <Button block onClick={handleCompare} loading={comparing}>
                对比三组参数
              </Button>
              <Button block onClick={handleWalkForward} loading={walkForwardLoading} style={{ marginTop: 8 }}>
                运行 70/30 样本外验证
              </Button>
              <Button block onClick={handleMultiWalkForward} loading={multiWalkLoading} style={{ marginTop: 8 }}>
                运行多窗口 Walk-Forward
              </Button>

              <Form.Item
                label="组合股票"
                name="portfolio_symbols"
                extra="用逗号分隔 2-10 个代码；每只股票分配相同初始资金"
                style={{ marginTop: 16 }}
              >
                <Input placeholder="000001,600000,600036" />
              </Form.Item>
              <Button block onClick={handlePortfolio} loading={portfolioLoading}>
                运行等权组合回测
              </Button>
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
                {currentResult.model === 'fixed_equal_weight_subaccounts' && (
                  <Tag color="purple" style={{ marginBottom: 16 }}>
                    等权组合：{currentResult.symbols?.join('、')}
                  </Tag>
                )}
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

                <Descriptions bordered size="small" column={3} style={{ marginTop: 24 }}>
                  <Descriptions.Item label="年化收益">
                    {(currentResult.annual_return ?? 0).toFixed(2)}%
                  </Descriptions.Item>
                  <Descriptions.Item label="买入持有基准">
                    {(currentResult.benchmark_return ?? 0).toFixed(2)}%
                  </Descriptions.Item>
                  <Descriptions.Item label="超额收益">
                    {(currentResult.excess_return ?? 0).toFixed(2)}%
                  </Descriptions.Item>
                  <Descriptions.Item label="盈亏比">
                    {currentResult.profit_factor == null ? '无亏损交易' : currentResult.profit_factor.toFixed(2)}
                  </Descriptions.Item>
                  <Descriptions.Item label="最大连续亏损">
                    {currentResult.max_consecutive_losses ?? 0} 笔
                  </Descriptions.Item>
                  <Descriptions.Item label="手续费合计">
                    ¥{(currentResult.total_commission ?? 0).toFixed(2)}
                  </Descriptions.Item>
                </Descriptions>

                <div style={{ margin: '24px 0' }}>
                  <Title level={4}>资金曲线</Title>
                  {currentResult.equity_curve?.length > 1 ? (
                    <Suspense fallback={<Spin />}>
                      <EquityChart data={currentResult.equity_curve} />
                    </Suspense>
                  ) : (
                    <Text type="secondary">区间内没有产生交易，资金保持不变。</Text>
                  )}
                  <div style={{ marginTop: 8 }}>
                    <Text type="secondary">日线近似：信号日收盘买入，下一交易日开盘卖出，已计手续费和滑点。</Text>
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

      {comparison.length > 0 && (
        <Card title="参数对比排行榜" style={{ marginTop: 16 }}>
          <Table
            rowKey="name"
            pagination={false}
            dataSource={comparison}
            columns={[
              { title: '排名', render: (_value, _record, index) => index + 1 },
              { title: '参数组', dataIndex: 'name' },
              { title: '总收益', dataIndex: 'total_return', render: (v) => `${v.toFixed(2)}%` },
              { title: '超额收益', dataIndex: 'excess_return', render: (v) => `${v.toFixed(2)}%` },
              { title: '最大回撤', dataIndex: 'max_drawdown', render: (v) => `${v.toFixed(2)}%` },
              { title: '胜率', dataIndex: 'win_rate', render: (v) => `${v.toFixed(1)}%` },
              { title: '交易数', dataIndex: 'total_trades' },
              { title: '盈亏比', dataIndex: 'profit_factor', render: (v) => v == null ? '—' : v.toFixed(2) },
              {
                title: '关键参数',
                dataIndex: 'params',
                render: (params) => `量比≥${params.min_volume_ratio}，振幅≤${params.max_amplitude}%`,
              },
            ]}
          />
          <Text type="secondary">排行榜按超额收益排序。参数比较使用完全相同的股票、区间、初始资金和行情数据。</Text>
        </Card>
      )}

      {walkForward && (
        <Card title="样本外验证" style={{ marginTop: 16 }}>
          <Descriptions bordered column={3} size="small">
            <Descriptions.Item label="训练区间">{walkForward.train_start} 至 {walkForward.train_end}</Descriptions.Item>
            <Descriptions.Item label="验证区间">{walkForward.validation_start} 至 {walkForward.validation_end}</Descriptions.Item>
            <Descriptions.Item label="训练选中参数">{walkForward.selected_name}</Descriptions.Item>
            <Descriptions.Item label="样本外总收益">{walkForward.validation.total_return.toFixed(2)}%</Descriptions.Item>
            <Descriptions.Item label="样本外基准">{(walkForward.validation.benchmark_return ?? 0).toFixed(2)}%</Descriptions.Item>
            <Descriptions.Item label="样本外超额">{(walkForward.validation.excess_return ?? 0).toFixed(2)}%</Descriptions.Item>
            <Descriptions.Item label="最大回撤">{walkForward.validation.max_drawdown.toFixed(2)}%</Descriptions.Item>
            <Descriptions.Item label="交易次数">{walkForward.validation.total_trades}</Descriptions.Item>
            <Descriptions.Item label="胜率">{walkForward.validation.win_rate.toFixed(1)}%</Descriptions.Item>
          </Descriptions>
          <Text type="secondary" style={{ display: 'block', marginTop: 12 }}>
            训练段用于选择参数；验证段只使用选定参数。验证前历史仅用于指标预热，不允许产生交易。
          </Text>
        </Card>
      )}

      {multiWalk && (
        <Card title="多窗口 Walk-Forward" style={{ marginTop: 16 }}>
          <Alert
            type={multiWalk.diagnostic.verdict === 'promising' ? 'success' : multiWalk.diagnostic.verdict === 'caution' ? 'warning' : 'error'}
            showIcon
            message={`策略诊断：${multiWalk.diagnostic.label}`}
            description={multiWalk.diagnostic.disclaimer}
            style={{ marginBottom: 16 }}
          />
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Progress type="dashboard" percent={multiWalk.diagnostic.score} format={(value) => `${value}分`} />
            </Col>
            <Col span={9}>
              <Title level={5}>主要问题</Title>
              <List size="small" dataSource={multiWalk.diagnostic.issues} locale={{ emptyText: '未触发主要风险规则' }} renderItem={(item) => <List.Item>{item}</List.Item>} />
            </Col>
            <Col span={9}>
              <Title level={5}>下一步建议</Title>
              <List size="small" dataSource={multiWalk.diagnostic.recommendations} renderItem={(item) => <List.Item>{item}</List.Item>} />
            </Col>
          </Row>
          <Descriptions bordered column={4} size="small" style={{ marginBottom: 16 }}>
            <Descriptions.Item label="窗口数">{multiWalk.window_count}</Descriptions.Item>
            <Descriptions.Item label="累计收益">{multiWalk.summary.total_return.toFixed(2)}%</Descriptions.Item>
            <Descriptions.Item label="累计超额">{multiWalk.summary.excess_return.toFixed(2)}%</Descriptions.Item>
            <Descriptions.Item label="正收益窗口">{multiWalk.summary.positive_windows}/{multiWalk.window_count}</Descriptions.Item>
          </Descriptions>
          <Table
            rowKey="index"
            pagination={false}
            dataSource={multiWalk.windows}
            columns={[
              { title: '窗口', dataIndex: 'index' },
              { title: '训练区间', render: (_v, r) => `${r.train_start} ~ ${r.train_end}` },
              { title: '验证区间', render: (_v, r) => `${r.validation_start} ~ ${r.validation_end}` },
              { title: '选中参数', dataIndex: 'selected_name' },
              { title: '验证收益', dataIndex: 'total_return', render: (v) => `${v.toFixed(2)}%` },
              { title: '超额收益', dataIndex: 'excess_return', render: (v) => `${v.toFixed(2)}%` },
              { title: '最大回撤', dataIndex: 'max_drawdown', render: (v) => `${v.toFixed(2)}%` },
              { title: '交易数', dataIndex: 'total_trades' },
            ]}
          />
          <Text type="secondary">
            固定使用 60 日训练、20 日验证并每次向前滚动 20 日；验证资金在窗口之间连续复利。
          </Text>
        </Card>
      )}
    </div>
  );
}
