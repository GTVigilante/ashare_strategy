// 配置文件
import { useState, useEffect, useCallback } from 'react';
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
import { apiErrorMessage } from '../utils/apiError';

const { Title, Paragraph } = Typography;
type ConfigValues = Strategy['params'] & { enabled: boolean };

export default function Config() {
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const fetchStrategy = useCallback(async () => {
    try {
      const res = await strategyApi.get('尾盘策略');
      if (res.code === 0) {
        form.setFieldsValue({
          ...res.data.params,
          enabled: res.data.enabled,
        });
      }
    } catch (error) {
      console.error('获取策略失败:', error);
      message.error('策略配置加载失败，请检查服务连接');
    }
  }, [form]);

  useEffect(() => {
    fetchStrategy();
  }, [fetchStrategy]);

  const handleSave = async (values: ConfigValues) => {
    try {
      setLoading(true);
      const { enabled, ...params } = values;
      const res = await strategyApi.update('尾盘策略', params, enabled);
      if (res.code === 0) {
        message.success('配置已保存');
        fetchStrategy();
      }
    } catch (error) {
      message.error(apiErrorMessage(error, '保存失败'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="config">
      <Title level={2}>⚙️ 策略配置</Title>
      <Paragraph type="secondary">参数会用于后续选股与回测。保存前请确认单位，建议每次调整后重新执行样本外验证。</Paragraph>

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
            require_ma_bullish: true,
            require_macd_golden: true,
          }}
        >
          {/* 基本信息 */}
          <Form.Item label="启用策略" name="enabled" valuePropName="checked" tooltip="关闭后保留参数，但标记该策略为停用">
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

          <Divider>技术过滤</Divider>

          <Space size="large" wrap>
            <Form.Item label="要求均线多头" name="require_ma_bullish" valuePropName="checked" tooltip="MA5 > MA10 > MA20">
              <Switch />
            </Form.Item>
            <Form.Item label="要求 MACD 增强" name="require_macd_golden" valuePropName="checked" tooltip="MACD 为正且不弱于前一交易日">
              <Switch />
            </Form.Item>
          </Space>

          <Paragraph type="secondary">
            当前回测采用日线近似：信号日收盘买入、下一交易日开盘卖出，并计入手续费与滑点；暂不提供盘中止损参数。
          </Paragraph>

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
