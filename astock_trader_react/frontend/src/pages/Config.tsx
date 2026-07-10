// 配置文件
import { useState, useEffect } from 'react';
import {
  Card,
  Form,
  InputNumber,
  Switch,
  Button,
  Space,
  Typography,
  message,
  Divider,
} from 'antd';

import { SaveOutlined, ReloadOutlined } from '@ant-design/icons';
import { strategyApi } from '../api';
import type { Strategy } from '../types/api';

const { Title } = Typography;

export default function Config() {
  const [loading, setLoading] = useState(false);
  const [strategy, setStrategy] = useState<Strategy | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchStrategy();
  }, []);

  const fetchStrategy = async () => {
    try {
      const res = await strategyApi.get('尾盘策略');
      if (res.code === 0) {
        setStrategy(res.data);
        form.setFieldsValue({
          ...res.data.params,
          enabled: res.data.enabled,
        });
      }
    } catch (error) {
      console.error('获取策略失败:', error);
    }
  };

  const handleSave = async (values: any) => {
    try {
      setLoading(true);
      const res = await strategyApi.update('尾盘策略', values);
      if (res.code === 0) {
        message.success('配置已保存');
        fetchStrategy();
      }
    } catch (error) {
      message.error('保存失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="config">
      <Title level={2}>⚙️ 策略配置</Title>

      <Card>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          initialValues={{
            enabled: true,
            min_turnover_rate: 3.0,
            max_market_cap: 200.0,
            max_amplitude: 5.0,
            min_price: 4.0,
            max_price: 30.0,
            min_volume_ratio: 1.2,
            gap_up_threshold: 1.0,
            low_open_stop: 2.0,
            stop_loss: 3.0,
          }}
        >
          {/* 基本信息 */}
          <Form.Item label="启用策略" name="enabled" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Divider>选股条件</Divider>

          <Space size="large" wrap>
            <Form.Item label="换手率 >" name="min_turnover_rate">
              <InputNumber min={0} max={20} step={0.5} addonAfter="%" />
            </Form.Item>

            <Form.Item label="流通市值 <" name="max_market_cap">
              <InputNumber min={10} max={1000} step={10} addonAfter="亿" />
            </Form.Item>

            <Form.Item label="振幅 <" name="max_amplitude">
              <InputNumber min={1} max={20} step={0.5} addonAfter="%" />
            </Form.Item>

            <Form.Item label="股价范围" name="price_range">
              <Space.Compact>
                <Form.Item name="min_price" noStyle>
                  <InputNumber min={1} max={100} placeholder="最低" />
                </Form.Item>
                <InputNumber disabled value="~" style={{ width: 40 }} />
                <Form.Item name="max_price" noStyle>
                  <InputNumber min={1} max={100} placeholder="最高" />
                </Form.Item>
              </Space.Compact>
            </Form.Item>

            <Form.Item label="量比 >" name="min_volume_ratio">
              <InputNumber min={0.5} max={5} step={0.1} />
            </Form.Item>
          </Space>

          <Divider>卖出规则</Divider>

          <Space size="large" wrap>
            <Form.Item label="高开卖出阈值" name="gap_up_threshold">
              <InputNumber min={0.5} max={10} step={0.1} addonAfter="%" />
            </Form.Item>

            <Form.Item label="低开止损阈值" name="low_open_stop">
              <InputNumber min={0.5} max={10} step={0.1} addonAfter="%" />
            </Form.Item>

            <Form.Item label="止损线" name="stop_loss">
              <InputNumber min={1} max={20} step={0.5} addonAfter="%" />
            </Form.Item>
          </Space>

          <Divider />

          <Form.Item>
            <Space>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                htmlType="submit"
                loading={loading}
              >
                保存配置
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={fetchStrategy}
              >
                重置
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
