// 选股页面
import { useEffect, useRef, useState } from 'react';
import {
  Card,
  Row,
  Col,
  DatePicker,
  Select,
  Table,
  Tag,
  Button,
  Space,
  Typography,
  Descriptions,
  Modal,
  Spin,
  message,
  Alert,
  Progress,
  Statistic,
} from 'antd';

import {
  SearchOutlined,
  PlusOutlined,
  ThunderboltOutlined,
  LineChartOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

import { screenApi, strategyApi, watchApi } from '../api';
import type { ScreeningJob, StockCandidate, StrategyParams } from '../types/api';
import { apiErrorMessage } from '../utils/apiError';

const { Title, Text } = Typography;


export default function Screening() {
  const [loading, setLoading] = useState(false);
  const [stocks, setStocks] = useState<StockCandidate[]>([]);
  const [poolInfo, setPoolInfo] = useState('');
  const [date, setDate] = useState<string>(dayjs().format('YYYYMMDD'));
  const [strategy, setStrategy] = useState<string>('尾盘策略');
  const [selectedStock, setSelectedStock] = useState<StockCandidate | null>(null);
  const [detailLoading] = useState(false);
  const [strategyParams, setStrategyParams] = useState<StrategyParams>({});
  const [job, setJob] = useState<ScreeningJob | null>(null);
  const pollTimer = useRef<number | null>(null);

  useEffect(() => {
    strategyApi.get('尾盘策略').then((res) => {
      if (res.code === 0) setStrategyParams(res.data.params || {});
    }).catch(() => undefined);
  }, []);

  useEffect(() => () => {
    if (pollTimer.current !== null) window.clearTimeout(pollTimer.current);
  }, []);

  const handleScreen = async () => {
    try {
      setLoading(true);
      setStocks([]);
      setPoolInfo('');
      setJob(null);
      const res = await screenApi.start({ date, strategy });
      if (res.code === 0) {
        const poll = async () => {
          try {
            const response = await screenApi.job(res.data.job_id);
            if (response.code !== 0) throw new Error(response.message);
            const nextJob = response.data;
            setJob(nextJob);
            if (nextJob.status === 'completed') {
              setStocks(nextJob.stocks || []);
              setPoolInfo(`${nextJob.pool_date} 涨停池 ${nextJob.pool_size} 只 · 已完整分析 ${nextJob.processed} 只`);
              setLoading(false);
              if (!nextJob.stocks.length) message.info('完整涨停池分析完成，但没有股票通过全部条件');
              return;
            }
            if (nextJob.status === 'failed') {
              setLoading(false);
              message.error(nextJob.error || '完整涨停池分析失败');
              return;
            }
            pollTimer.current = window.setTimeout(poll, 800);
          } catch (error) {
            setLoading(false);
            message.error(apiErrorMessage(error, '获取筛选进度失败'));
          }
        };
        await poll();
      } else {
        setLoading(false);
        message.error(res.message || '创建完整涨停池分析任务失败');
      }
    } catch (error) {
      setLoading(false);
      console.error('筛选失败:', error);
      message.error(apiErrorMessage(error, '筛选失败，请稍后重试'));
    }
  };

  const handleAddWatch = async (stock: StockCandidate) => {
    try {
      const res = await watchApi.add({
        symbol: stock.symbol,
        name: stock.name,
      });
      if (res.code === 0) {
        message.success(`已添加 ${stock.name} 到自选`);
      }
    } catch (error) {
      message.error(apiErrorMessage(error, '添加失败'));
    }
  };

  const handleViewDetail = (stock: StockCandidate) => {
    setSelectedStock(stock);
  };

  const columns: any = [
    {
      title: '股票',
      key: 'stock',
      render: (_, record) => (
        <Space orientation="vertical" size={0}>
          <Tag color="blue">{record.symbol}</Tag>
          <Text strong>{record.name}</Text>
        </Space>
      ),
    },
    {
      title: '收盘价',
      dataIndex: 'close',
      key: 'close',
      render: (v) => <Text strong>¥{v?.toFixed(2)}</Text>,
    },
    {
      title: '换手率',
      dataIndex: 'turnover_rate',
      key: 'turnover_rate',
      render: (v) => <Tag color={v >= 5 ? 'green' : 'orange'}>{v?.toFixed(1)}%</Tag>,
    },
    {
      title: '量比',
      dataIndex: 'volume_ratio',
      key: 'volume_ratio',
      render: (v) => <Tag color={v >= 1.5 ? 'purple' : 'default'}>{v?.toFixed(2)}</Tag>,
    },
    {
      title: '技术信号',
      key: 'signals',
      render: (_, record) => (
        <Space>
          {record.ma_bullish && <Tag color="cyan">均线多头</Tag>}
          {record.macd_golden && <Tag color="gold">MACD金叉</Tag>}
          {record.breakout && <Tag color="red">突破</Tag>}
        </Space>
      ),
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      render: (v) => (
        <div
          style={{
            width: 60,
            height: 60,
            borderRadius: '50%',
            background: `conic-gradient(#1890ff ${(v || 0) * 100}%, #f0f0f0 0)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <span style={{ fontSize: 14, fontWeight: 'bold' }}>
            {((v || 0) * 100).toFixed(0)}%
          </span>
        </div>
      ),
    },
    {
      title: '原因',
      dataIndex: 'reason',
      key: 'reason',
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<LineChartOutlined />}
            onClick={() => handleViewDetail(record)}
          >
            详情
          </Button>
          <Button
            type="link"
            icon={<PlusOutlined />}
            onClick={() => handleAddWatch(record)}
          >
            自选
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div className="screening">
      <Title level={2}>📈 尾盘选股</Title>

      {/* 筛选条件 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col>
            <Space>
              <DatePicker
                onChange={(d) => setDate(d ? d.format('YYYYMMDD') : '')}
                defaultValue={dayjs()}
                format="YYYYMMDD"
              />
              <Select
                value={strategy}
                onChange={setStrategy}
                style={{ width: 150 }}
                options={[
                  { label: '尾盘策略', value: '尾盘策略' },
                ]}
              />
              <Button
                type="primary"
                icon={<SearchOutlined />}
                onClick={handleScreen}
                loading={loading}
              >
                开始筛选
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 选股条件说明 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={24}>
          <Col>
            <Text type="secondary">换手率 &gt; {strategyParams.min_turnover_rate ?? 3}%</Text>
          </Col>
          <Col>
            <Text type="secondary">流通市值 &lt; {strategyParams.max_market_cap ?? 200}亿</Text>
          </Col>
          <Col>
            <Text type="secondary">振幅 &lt; {strategyParams.max_amplitude ?? 5}%</Text>
          </Col>
          <Col>
            <Text type="secondary">股价 {strategyParams.min_price ?? 4}-{strategyParams.max_price ?? 30}元</Text>
          </Col>
          <Col>
            <Text type="secondary">量比 &gt; {strategyParams.min_volume_ratio ?? 1.2}</Text>
          </Col>
          <Col>
            <Text type="secondary">昨日涨停</Text>
          </Col>
          {strategyParams.require_ma_bullish !== false && <Col><Text type="secondary">均线多头</Text></Col>}
          {strategyParams.require_macd_golden !== false && <Col><Text type="secondary">MACD 增强</Text></Col>}
        </Row>
      </Card>
      <Alert
        type="info"
        showIcon
        title="系统会分析完整涨停池并实时显示进度。首次运行可能需要数分钟；已缓存股票会明显加快。"
        style={{ marginBottom: 16 }}
      />

      {job && (
        <Card title="完整涨停池分析进度" style={{ marginBottom: 16 }}>
          <Progress
            percent={job.pool_size ? Math.round(job.processed / job.pool_size * 100) : 0}
            status={job.status === 'failed' ? 'exception' : job.status === 'completed' ? 'success' : 'active'}
            format={() => job.pool_size ? `${job.processed} / ${job.pool_size}` : '正在获取涨停池'}
          />
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={12} md={6}><Statistic title="已处理" value={job.processed} suffix={job.pool_size ? `/ ${job.pool_size}` : ''} /></Col>
            <Col xs={12} md={6}><Statistic title="通过" value={job.details.filter((item) => item.status === 'selected').length} /></Col>
            <Col xs={12} md={6}><Statistic title="未通过" value={job.details.filter((item) => item.status === 'rejected').length} /></Col>
            <Col xs={12} md={6}><Statistic title="数据错误" value={job.details.filter((item) => item.status === 'error').length} /></Col>
          </Row>
          {job.current_symbol && <Text type="secondary">当前：{job.current_symbol} {job.current_name}</Text>}
          <Table
            style={{ marginTop: 16 }}
            size="small"
            rowKey="symbol"
            dataSource={job.details}
            pagination={{ pageSize: 8, showSizeChanger: false }}
            locale={{ emptyText: job.status === 'queued' ? '任务排队中' : '正在获取第一只股票' }}
            columns={[
              { title: '代码', dataIndex: 'symbol', width: 90 },
              { title: '名称', dataIndex: 'name', width: 110 },
              { title: '结论', dataIndex: 'status', width: 90, render: (value) => <Tag color={value === 'selected' ? 'success' : value === 'error' ? 'error' : 'default'}>{value === 'selected' ? '通过' : value === 'error' ? '错误' : '未通过'}</Tag> },
              { title: '明细', dataIndex: 'reason', ellipsis: true },
            ]}
          />
        </Card>
      )}

      {/* 筛选结果 */}
      <Card
        title={`筛选结果 (${stocks.length} 只)`}
        extra={
          <Tag color="blue">
            <ThunderboltOutlined /> 真实数据 {poolInfo}
          </Tag>
        }
      >
        <Table
            columns={columns}
            dataSource={stocks}
            rowKey="symbol"
            pagination={{ pageSize: 10 }}
            size="middle"
            loading={loading && !job}
          />
      </Card>

      {/* 股票详情弹窗 */}
      <Modal
        title={`${selectedStock?.name} (${selectedStock?.symbol})`}
        open={!!selectedStock}
        onCancel={() => setSelectedStock(null)}
        footer={[
          <Button key="close" onClick={() => setSelectedStock(null)}>
            关闭
          </Button>,
          <Button
            key="add"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => selectedStock && handleAddWatch(selectedStock)}
          >
            加入自选
          </Button>,
        ]}
        width={700}
      >
        {detailLoading ? (
          <Spin />
        ) : (
          <Descriptions column={2} bordered>
            <Descriptions.Item label="最新价">
              ¥{selectedStock?.price?.toFixed(2)}
            </Descriptions.Item>
            <Descriptions.Item label="换手率">
              {selectedStock?.turnover_rate?.toFixed(1)}%
            </Descriptions.Item>
            <Descriptions.Item label="量比">
              {selectedStock?.volume_ratio?.toFixed(2)}
            </Descriptions.Item>
            <Descriptions.Item label="振幅">
              {selectedStock?.amplitude?.toFixed(1)}%
            </Descriptions.Item>
            <Descriptions.Item label="均线多头">
              {selectedStock?.ma_bullish ? '✅ 是' : '❌ 否'}
            </Descriptions.Item>
            <Descriptions.Item label="MACD金叉">
              {selectedStock?.macd_golden ? '✅ 是' : '❌ 否'}
            </Descriptions.Item>
            <Descriptions.Item label="置信度" span={2}>
              {((selectedStock?.confidence || 0) * 100).toFixed(0)}%
            </Descriptions.Item>
            <Descriptions.Item label="入选原因" span={2}>
              {selectedStock?.reason}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
}
