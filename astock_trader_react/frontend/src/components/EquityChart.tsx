import { Line } from '@ant-design/charts';
import type { EquityPoint } from '../types/api';

export default function EquityChart({ data }: { data: EquityPoint[] }) {
  return <Line
    data={data}
    xField="date"
    yField="value"
    height={220}
    axis={{ y: { labelFormatter: (value) => `¥${Number(value).toLocaleString()}` } }}
  />;
}
