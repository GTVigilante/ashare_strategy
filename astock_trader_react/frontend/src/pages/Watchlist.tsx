/* 自选股页面 */
import { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Typography,
  Modal,
  Form,
  Input,
  message,
  Popconfirm,
} from 'antd';

import {
  PlusOutlined,
  DeleteOutlined,
  LineChartOutlined,
} from '@ant-design/icons';

import { watchApi } from '../api';
import type { WatchStock } from '../types/api';
import { apiErrorMessage } from '../utils/apiError';

const { Title } = Typography;

export default function Watchlist() {
  const [loading, setLoading] = useState(false);
  const [stocks, setStocks] = useState<WatchStock[]>([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchStocks();
  }, []);

  const fetchStocks = async () => {
    try {
      setLoading(true);
      const res = await watchApi.list();
      if (res.code === 0) {
        setStocks(res.data || []);
      }
    } catch (error) {
      console.error('获取失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async (values: any) => {
    try {
      const res = await watchApi.add(values);
      if (res.code === 0) {
        message.success('添加成功');
        setModalVisible(false);
        form.resetFields();
        fetchStocks();
      }
    } catch (error) {
      message.error(apiErrorMessage(error, '添加失败'));
    }
  };

  const handleDelete = async (symbol: string) => {
    try {
      const res = await watchApi.remove(symbol);
      if (res.code === 0) {
        message.success('已删除');
        fetchStocks();
      }
    } catch (error) {
      message.error(apiErrorMessage(error, '删除失败'));
    }
  };

  const columns: any = [
    {
      title: '股票代码',
      dataIndex: 'symbol',
      key: 'symbol',
      render: (text) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[]) => (
        <>
          {tags?.map((tag) => (
            <Tag key={tag} color="gold">
              {tag}
            </Tag>
          ))}
        </>
      ),
    },
    {
      title: '备注',
      dataIndex: 'notes',
      key: 'notes',
      ellipsis: true,
    },
    {
      title: '添加时间',
      dataIndex: 'added_at',
      key: 'added_at',
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<LineChartOutlined />}
            size="small"
          >
            分析
          </Button>
          <Popconfirm
            title="确定删除？"
            onConfirm={() => handleDelete(record.symbol)}
          >
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              size="small"
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className="watchlist">
      <Title level={2}>⭐ 自选股</Title>

      <Card
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setModalVisible(true)}
          >
            添加自选
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={stocks}
          rowKey="symbol"
          loading={loading}
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: '暂无自选股，点击右上角添加' }}
        />
      </Card>

      {/* 添加弹窗 */}
      <Modal
        title="添加自选股"
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        footer={null}
      >
        <Form form={form} layout="vertical" onFinish={handleAdd}>
          <Form.Item
            label="股票代码"
            name="symbol"
            rules={[{ required: true, message: '请输入股票代码' }]}
          >
            <Input placeholder="如: 300001" />
          </Form.Item>

          <Form.Item label="股票名称" name="name">
            <Input placeholder="如: 测试股票" />
          </Form.Item>

          <Form.Item label="标签" name="tags">
            <Input placeholder="多个标签用逗号分隔" />
          </Form.Item>

          <Form.Item label="备注" name="notes">
            <Input.TextArea rows={2} placeholder="备注信息" />
          </Form.Item>

          <Form.Item>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit">
                添加
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
