// API 服务层
import axios from 'axios';
import type {
  ApiResponse,
  Strategy,
  StockCandidate,
  StockInfo,
  StockIndicators,
  KLineData,
  BacktestResult,
  PageResponse,
  WatchStock,
  Signal,
  Order,
  DashboardData,
} from '../types/api';

// API 基础配置
const BASE_URL = 'http://localhost:8000/api';

// 创建 axios 实例
const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

// ============ 策略 API ============

export const strategyApi = {
  // 获取策略列表
  list: (): Promise<ApiResponse<Strategy[]>> => api.get('/strategies'),

  // 获取策略详情
  get: (name: string): Promise<ApiResponse<Strategy>> =>
    api.get(`/strategies/${name}`),

  // 更新策略配置
  update: (
    name: string,
    params: Record<string, any>
  ): Promise<ApiResponse> => api.put(`/strategies/${name}`, { params }),

  // 切换策略启用状态
  toggle: (name: string): Promise<ApiResponse<{ enabled: boolean }>> =>
    api.post(`/strategies/${name}/toggle`),
};

// ============ 选股 API ============

export const screenApi = {
  // 筛选候选股票
  screen: (params?: {
    date?: string;
    strategy?: string;
  }): Promise<
    ApiResponse<{
      date: string;
      strategy: string;
      total: number;
      stocks: StockCandidate[];
    }>
  > => api.get('/screen', { params }),

  // 获取股票详情
  getStock: (
    symbol: string
  ): Promise<
    ApiResponse<
      StockInfo & {
        indicators: StockIndicators;
      }
    >
  > => api.get(`/stock/${symbol}`),

  // 获取K线数据
  getKLine: (
    symbol: string,
    params?: {
      period?: 'day' | 'week' | 'month' | 'minute';
      start_date?: string;
      end_date?: string;
    }
  ): Promise<
    ApiResponse<{
      symbol: string;
      name: string;
      period: string;
      data: KLineData[];
    }>
  > => api.get(`/stock/${symbol}/kline`, { params }),
};

// ============ 回测 API ============

export const backtestApi = {
  // 运行回测
  run: (data: {
    strategy: string;
    start_date: string;
    end_date: string;
    initial_cash?: number;
    symbols?: string[];
  }): Promise<ApiResponse<BacktestResult>> => api.post('/backtest', data),

  // 获取回测历史
  history: (params?: {
    strategy?: string;
    page?: number;
    page_size?: number;
  }): Promise<ApiResponse<PageResponse<BacktestResult>>> =>
    api.get('/backtest/history', { params }),

  // 获取回测详情
  get: (id: number): Promise<ApiResponse<BacktestResult>> =>
    api.get(`/backtest/${id}`),
};

// ============ 自选股 API ============

export const watchApi = {
  // 获取自选股列表
  list: (): Promise<ApiResponse<WatchStock[]>> => api.get('/watch'),

  // 添加自选股
  add: (data: {
    symbol: string;
    name?: string;
    tags?: string[];
    notes?: string;
  }): Promise<ApiResponse> => api.post('/watch', data),

  // 删除自选股
  remove: (symbol: string): Promise<ApiResponse> =>
    api.delete(`/watch/${symbol}`),
};

// ============ 信号 API ============

export const signalApi = {
  // 获取信号列表
  list: (params?: {
    strategy?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<ApiResponse<PageResponse<Signal>>> =>
    api.get('/signals', { params }),

  // 执行信号
  execute: (id: number): Promise<ApiResponse<{ order_id: string }>> =>
    api.post(`/signals/${id}/execute`),

  // 取消信号
  cancel: (id: number): Promise<ApiResponse> =>
    api.post(`/signals/${id}/cancel`),
};

// ============ 订单 API ============

export const orderApi = {
  // 获取订单列表
  list: (params?: {
    status?: string;
    symbol?: string;
    page?: number;
    page_size?: number;
  }): Promise<ApiResponse<PageResponse<Order>>> =>
    api.get('/orders', { params }),

  // 获取订单详情
  get: (orderId: string): Promise<ApiResponse<Order>> =>
    api.get(`/orders/${orderId}`),

  // 撤单
  cancel: (orderId: string): Promise<ApiResponse> =>
    api.post(`/orders/${orderId}/cancel`),
};

// ============ Dashboard API ============

export const dashboardApi = {
  // 获取仪表盘数据
  get: (): Promise<ApiResponse<DashboardData>> => api.get('/dashboard'),

  // 获取今日选股
  todayStocks: (): Promise<
    ApiResponse<{
      date: string;
      candidates: StockCandidate[];
    }>
  > => api.get('/dashboard/today-stocks'),
};

export default api;
