// API 服务层
import axios from 'axios';
import type {
  ApiResponse,
  Strategy,
  StockCandidate,
  BacktestResult,
  ParameterComparison,
  WalkForwardResult,
  MultiWalkForwardResult,
  PageResponse,
  WatchStock,
  DashboardData,
  PaperOrder,
  PaperStatus,
} from '../types/api';

// API 基础配置
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api';
const TOKEN_KEY = 'ashare_session_token';

// 创建 axios 实例
const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error);
    if (error?.response?.status === 401 && !error?.config?.url?.includes('/auth/login')) {
      sessionStorage.removeItem(TOKEN_KEY);
      window.dispatchEvent(new Event('ashare:unauthorized'));
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  login: async (password: string): Promise<ApiResponse<{ token: string; expires_in: number }>> => {
    const response = await api.post('/auth/login', { password }) as unknown as ApiResponse<{ token: string; expires_in: number }>;
    if (response.code === 0) sessionStorage.setItem(TOKEN_KEY, response.data.token);
    return response;
  },
  logout: async () => {
    try { await api.post('/auth/logout'); } finally { sessionStorage.removeItem(TOKEN_KEY); }
  },
  hasSession: () => Boolean(sessionStorage.getItem(TOKEN_KEY)),
};

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
    params: Record<string, unknown>,
    enabled?: boolean,
  ): Promise<ApiResponse> => api.put(`/strategies/${name}`, { params, enabled }),

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
      pool_date: string;
      pool_size: number;
      processed: number;
      strategy: string;
      total: number;
      stocks: StockCandidate[];
      skipped_errors: number;
    }>
  > => api.get('/screen', { params, timeout: 120000 }),

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

  compare: (data: {
    strategy: string;
    start_date: string;
    end_date: string;
    initial_cash?: number;
    symbols: string[];
  }): Promise<ApiResponse<{ symbol: string; start_date: string; end_date: string; ranking: ParameterComparison[] }>> =>
    api.post('/backtest/compare', data),

  portfolio: (data: {
    strategy: string;
    start_date: string;
    end_date: string;
    initial_cash?: number;
    symbols: string[];
  }): Promise<ApiResponse<BacktestResult>> => api.post('/backtest/portfolio', data),

  walkForward: (data: {
    strategy: string;
    start_date: string;
    end_date: string;
    initial_cash?: number;
    symbols: string[];
  }): Promise<ApiResponse<WalkForwardResult>> => api.post('/backtest/walk-forward', data),

  multiWalkForward: (data: {
    strategy: string;
    start_date: string;
    end_date: string;
    initial_cash?: number;
    symbols: string[];
  }): Promise<ApiResponse<MultiWalkForwardResult>> => api.post('/backtest/walk-forward/multi', data),
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

export const paperApi = {
  approve: (data: { strategy: string; start_date: string; end_date: string; initial_cash: number; symbols: string[] }): Promise<ApiResponse<{ approval_token: string; expires_in: number; symbol: string }>> =>
    api.post('/paper/approve', data),
  status: (): Promise<ApiResponse<PaperStatus>> => api.get('/paper/status'),
  order: (data: { approval_token: string; symbol: string; side: 'buy' | 'sell'; quantity: number; price: number }) =>
    api.post('/paper/orders', data) as Promise<ApiResponse<PaperOrder>>,
};

export default api;
