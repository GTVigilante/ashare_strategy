import { useEffect, useState } from 'react';
import { Alert, Button, Card, Col, Form, Input, InputNumber, Progress, Row, Select, Space, Statistic, Table, Tag, Typography, message } from 'antd';
import dayjs from 'dayjs';
import { paperApi } from '../api';
import type { PaperApproval, PaperStatus } from '../types/api';
import { apiErrorMessage } from '../utils/apiError';

const { Title, Text } = Typography;

export default function PaperTrading() {
  const [approval, setApproval] = useState('');
  const [approvalInfo, setApprovalInfo] = useState<PaperApproval | null>(null);
  const [status, setStatus] = useState<PaperStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [orderLoading, setOrderLoading] = useState(false);
  const [form] = Form.useForm();
  const refresh = async () => { const r = await paperApi.status(); if (r.code === 0) setStatus(r.data); };
  useEffect(() => { refresh().catch(() => undefined); }, []);

  const approve = async () => {
    const symbol = form.getFieldValue('symbol');
    if (!/^\d{6}$/.test(symbol || '')) return message.error('请输入六位股票代码');
    setLoading(true);
    try {
      const r = await paperApi.approve({ strategy: '尾盘策略', start_date: dayjs().subtract(18, 'month').format('YYYYMMDD'), end_date: dayjs().subtract(1, 'day').format('YYYYMMDD'), initial_cash: 100000, symbols: [symbol] });
      if (r.code === 0) { setApproval(r.data.approval_token); setApprovalInfo(r.data); message.success('策略已通过诊断，准入有效 1 小时'); }
    } catch (e) { message.error(apiErrorMessage(e, '策略未通过准入')); }
    finally { setLoading(false); }
  };
  const order = async (values: { symbol: string; side: 'buy' | 'sell'; quantity: number; price: number }) => {
    if (!approval) return message.error('请先运行策略准入');
    setOrderLoading(true);
    try {
      await paperApi.order({ ...values, approval_token: approval });
      message.success('模拟成交'); await refresh();
    } catch (e) { message.error(apiErrorMessage(e, '模拟订单被拒绝')); }
    finally { setOrderLoading(false); }
  };
  const positions = Object.entries(status?.positions || {}).map(([symbol, value]) => ({ symbol, ...value }));
  return <div>
    <Title level={2}>🧪 模拟盘</Title>
    <Alert type="warning" showIcon title="仅为内存模拟账户，不连接券商；服务重启后账户重置。价格由用户输入，仅用于验证风控流程。" style={{ marginBottom: 16 }} />
    <Row gutter={16}>
      <Col xs={24} xl={8}><Card title="策略准入与订单">
        <Form form={form} layout="vertical" onFinish={order} initialValues={{ symbol: '000001', side: 'buy', quantity: 100 }}>
          <Form.Item name="symbol" label="股票代码"><Input maxLength={6} /></Form.Item>
          <Button block onClick={approve} loading={loading}>运行多窗口诊断并申请准入</Button>
          {approvalInfo && <Card size="small" style={{ marginTop: 16 }}>
            <Space align="center">
              <Progress type="circle" size={56} percent={approvalInfo.diagnostic.score} format={(value) => `${value}分`} />
              <div><Tag color="success">准入已签发</Tag><br /><Text strong>{approvalInfo.diagnostic.label}</Text><br /><Text type="secondary">{approvalInfo.symbol} · 有效 {Math.round(approvalInfo.expires_in / 60)} 分钟</Text></div>
            </Space>
          </Card>}
          <Form.Item name="side" label="方向" style={{ marginTop: 16 }}><Select options={[{ label: '买入', value: 'buy' }, { label: '卖出', value: 'sell' }]} /></Form.Item>
          <Form.Item name="quantity" label="数量"><InputNumber min={100} step={100} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="price" label="模拟价格" rules={[{ required: true }]}><InputNumber min={0.01} style={{ width: '100%' }} /></Form.Item>
          <Button block type="primary" htmlType="submit" loading={orderLoading}>提交模拟订单</Button>
        </Form>
      </Card></Col>
      <Col xs={24} xl={16}><Card title="账户与风控">
        <Row gutter={[16, 16]}><Col xs={24} sm={8}><Statistic title="权益" value={status?.equity || 0} prefix="¥" /></Col><Col xs={24} sm={8}><Statistic title="现金" value={status?.cash || 0} prefix="¥" /></Col><Col xs={24} sm={8}><Statistic title="当前回撤" value={(status?.drawdown || 0) * 100} suffix="%" precision={2} /></Col></Row>
        <Text type="secondary">限制：单股 {((status?.limits.max_position ?? 0.2) * 100).toFixed(0)}% · 单日亏损 {((status?.limits.daily_loss ?? 0.03) * 100).toFixed(0)}% · 最大回撤 {((status?.limits.max_drawdown ?? 0.1) * 100).toFixed(0)}%</Text>
        <Card size="small" title={`当前持仓（${positions.length}）`} style={{ marginTop: 16 }}>
          <Table pagination={false} rowKey="symbol" dataSource={positions} locale={{ emptyText: '暂无模拟持仓' }} columns={[{ title: '代码', dataIndex: 'symbol' }, { title: '数量', dataIndex: 'quantity' }, { title: '成本价', dataIndex: 'cost', render: (v) => `¥${v.toFixed(2)}` }, { title: '最近价格', dataIndex: 'last_price', render: (v) => `¥${v.toFixed(2)}` }]} />
        </Card>
        <Card size="small" title="模拟成交记录" style={{ marginTop: 16 }}>
          <Table pagination={false} rowKey="id" dataSource={status?.orders || []} locale={{ emptyText: '暂无模拟成交' }} columns={[{ title: '代码', dataIndex: 'symbol' }, { title: '方向', dataIndex: 'side', render: (v) => v === 'buy' ? '买入' : '卖出' }, { title: '数量', dataIndex: 'quantity' }, { title: '价格', dataIndex: 'price', render: (v) => `¥${v.toFixed(2)}` }, { title: '状态', dataIndex: 'status', render: () => <Tag color="success">已成交</Tag> }]} />
        </Card>
      </Card></Col>
    </Row>
  </div>;
}
