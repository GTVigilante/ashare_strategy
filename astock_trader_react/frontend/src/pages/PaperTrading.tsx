import { useEffect, useState } from 'react';
import { Alert, Button, Card, Col, Form, Input, InputNumber, Row, Select, Statistic, Table, Typography, message } from 'antd';
import dayjs from 'dayjs';
import { paperApi } from '../api';

const { Title, Text } = Typography;

export default function PaperTrading() {
  const [approval, setApproval] = useState('');
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const refresh = async () => { const r: any = await paperApi.status(); if (r.code === 0) setStatus(r.data); };
  useEffect(() => { refresh().catch(() => undefined); }, []);

  const approve = async () => {
    const symbol = form.getFieldValue('symbol');
    if (!/^\d{6}$/.test(symbol || '')) return message.error('请输入六位股票代码');
    setLoading(true);
    try {
      const r: any = await paperApi.approve({ strategy: '尾盘策略', start_date: dayjs().subtract(18, 'month').format('YYYYMMDD'), end_date: dayjs().subtract(1, 'day').format('YYYYMMDD'), initial_cash: 100000, symbols: [symbol] });
      if (r.code === 0) { setApproval(r.data.approval_token); message.success('策略已通过诊断，准入有效 1 小时'); }
    } catch (e) { message.error((e as any)?.response?.data?.detail || '策略未通过准入'); }
    finally { setLoading(false); }
  };
  const order = async (values: any) => {
    if (!approval) return message.error('请先运行策略准入');
    try {
      await paperApi.order({ ...values, approval_token: approval });
      message.success('模拟成交'); await refresh();
    } catch (e) { message.error((e as any)?.response?.data?.detail || '模拟订单被拒绝'); }
  };
  return <div>
    <Title level={2}>🧪 模拟盘</Title>
    <Alert type="warning" showIcon message="仅为内存模拟账户，不连接券商；服务重启后账户重置。价格由用户输入，仅用于验证风控流程。" style={{ marginBottom: 16 }} />
    <Row gutter={16}>
      <Col span={8}><Card title="策略准入与订单">
        <Form form={form} layout="vertical" onFinish={order} initialValues={{ symbol: '000001', side: 'buy', quantity: 100 }}>
          <Form.Item name="symbol" label="股票代码"><Input maxLength={6} /></Form.Item>
          <Button block onClick={approve} loading={loading}>运行多窗口诊断并申请准入</Button>
          <Form.Item name="side" label="方向" style={{ marginTop: 16 }}><Select options={[{ label: '买入', value: 'buy' }, { label: '卖出', value: 'sell' }]} /></Form.Item>
          <Form.Item name="quantity" label="数量"><InputNumber min={100} step={100} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="price" label="模拟价格" rules={[{ required: true }]}><InputNumber min={0.01} style={{ width: '100%' }} /></Form.Item>
          <Button block type="primary" htmlType="submit">提交模拟订单</Button>
        </Form>
      </Card></Col>
      <Col span={16}><Card title="账户与风控">
        <Row gutter={16}><Col span={8}><Statistic title="权益" value={status?.equity || 0} prefix="¥" /></Col><Col span={8}><Statistic title="现金" value={status?.cash || 0} prefix="¥" /></Col><Col span={8}><Statistic title="当前回撤" value={(status?.drawdown || 0) * 100} suffix="%" precision={2} /></Col></Row>
        <Text type="secondary">限制：单股 20% · 单日亏损 3% · 最大回撤 10%</Text>
        <Table style={{ marginTop: 16 }} pagination={false} rowKey="id" dataSource={status?.orders || []} columns={[{ title: '代码', dataIndex: 'symbol' }, { title: '方向', dataIndex: 'side' }, { title: '数量', dataIndex: 'quantity' }, { title: '价格', dataIndex: 'price' }, { title: '状态', dataIndex: 'status' }]} />
      </Card></Col>
    </Row>
  </div>;
}
