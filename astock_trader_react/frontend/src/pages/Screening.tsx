// 选股页面
import { useEffect, useState } from 'react';
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
} from 'antd';

import {
  SearchOutlined,
  PlusOutlined,
  ThunderboltOutlined,
  LineChartOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

import { screenApi, strategyApi, watchApi } from '../api';
import type { StockCandidate, StrategyParams } from '../types/api';
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

  useEffect(() => {
    strategyApi.get('尾盘策略').then((res) => {
      if (res.code === 0) setStrategyParams(res.data.params || {});
    }).catch(() => undefined);
  }, []);

  const handleScreen = async () => {
    try {
      setLoading(true);
      const res = await screenApi.screen({ date, strategy });
      if (res.code === 0) {
        setStocks(res.data.stocks || []);
        setPoolInfo(`${res.data.pool_date} 涨停池 ${res.data.pool_size} 只 · 深度分析前 ${res.data.processed} 只`);
        if (!res.data.stocks?.length) message.info('真实数据获取成功，但没有股票通过全部条件');
      }
    } catch (error) {
      console.error('筛选失败:', error);
      message.error(apiErrorMessage(error, '筛选失败，请稍后重试'));
    } finally {
      setLoading(false);
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
        title="首次筛选需要下载候选股历史行情，可能耗时 10-60 秒；后续相同区间会命中本地缓存。"
        style={{ marginBottom: 16 }}
      />

      {/* 筛选结果 */}
      <Card
        title={`筛选结果 (${stocks.length} 只)`}
        extra={
          <Tag color="blue">
            <ThunderboltOutlined /> 真实数据 {poolInfo}
          </Tag>
        }
      >
        {loading ? (
          <div style={{ textAlign: 'center', padding: 50 }}>
            <Spin size="large" />
          </div>
        ) : (
          <Table
            columns={columns}
            dataSource={stocks}
            rowKey="symbol"
            pagination={{ pageSize: 10 }}
            size="middle"
          />
        )}
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
