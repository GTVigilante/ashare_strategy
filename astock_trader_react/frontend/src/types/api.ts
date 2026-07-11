// A股量化交易系统 - API 类型定义

// 通用响应格式
export interface ApiResponse<T = any> {
  code: number;
  message: string;
  data: T;
}

// 分页响应
export interface PageResponse<T> {
  total: number;
  page: number;
  page_size: number;
  list: T[];
}

// ============ 策略 ============

export interface StrategyParams {
  min_turnover_rate?: number;      // 换手率 > x%
  max_market_cap?: number;        // 流通市值 < x亿
  max_amplitude?: number;         // 振幅 < x%
  min_price?: number;             // 股价下限
  max_price?: number;             // 股价上限
  min_volume_ratio?: number;      // 量比 > x
  require_ma_bullish?: boolean;   // 要求均线多头
  require_macd_golden?: boolean;  // 要求MACD金叉
  gap_up_threshold?: number;       // 高开阈值 %
  low_open_stop?: number;         // 低开止损 %
  stop_loss?: number;              // 止损 %
}

export interface Strategy {
  id?: number;
  name: string;
  description?: string;
  enabled: boolean;
  params: StrategyParams;
  created_at?: string;
  updated_at?: string;
}

// ============ 股票 ============

export interface StockInfo {
  symbol: string;
  name: string;
  price?: number;
  change?: number;
  change_percent?: number;
  turnover_rate?: number;
  volume_ratio?: number;
  market_cap?: number;
  amplitude?: number;
}

export interface StockCandidate extends StockInfo {
  close?: number;
  ma_bullish?: boolean;
  macd_golden?: boolean;
  breakout?: boolean;
  confidence?: number;
  reason?: string;
}

export interface StockIndicators {
  ma5?: number;
  ma10?: number;
  ma20?: number;
  ma_bullish?: boolean;
  macd?: number;
  dif?: number;
  dea?: number;
  macd_golden?: boolean;
  rsi?: number;
  boll_upper?: number;
  boll_mid?: number;
  boll_lower?: number;
}

export interface KLineData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  amount?: number;
}

// ============ 回测 ============

export interface BacktestTrade {
  id: number;
  symbol: string;
  name: string;
  buy_date: string;
  buy_price: number;
  sell_date: string;
  sell_price: number;
  profit: number;
  profit_percent: number;
  commission?: number;
  hold_days: number;
  reason: string;
}

export interface EquityPoint {
  date: string;
  value: number;
}

export interface BacktestResult {
  id: number;
  strategy: string;
  start_date: string;
  end_date: string;
  initial_cash: number;
  final_value: number;
  total_return: number;
  annual_return?: number;
  benchmark_return?: number;
  excess_return?: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  total_trades: number;
  profit_factor?: number;
  avg_profit?: number;
  max_profit?: number;
  min_profit?: number;
  max_consecutive_losses?: number;
  total_commission?: number;
  equity_curve: EquityPoint[];
  trades: BacktestTrade[];
  created_at?: string;
}

// ============ 自选股 ============

export interface WatchStock {
  symbol: string;
  name: string;
  added_at: string;
  tags?: string[];
  notes?: string;
}

// ============ 信号 ============

export type SignalType = 'buy' | 'sell';
export type SignalStatus = 'pending' | 'executed' | 'expired';

export interface Signal {
  id: number;
  symbol: string;
  name: string;
  signal_type: SignalType;
  price: number;
  confidence: number;
  reason: string;
  strategy: string;
  created_at: string;
  status: SignalStatus;
}

// ============ 订单 ============

export type OrderDirection = 'buy' | 'sell';
export type OrderStatus = 'pending' | 'filled' | 'cancelled';

export interface Order {
  id: number;
  order_id: string;
  symbol: string;
  name: string;
  direction: OrderDirection;
  price: number;
  quantity: number;
  amount: number;
  commission: number;
  status: OrderStatus;
  strategy?: string;
  created_at: string;
  filled_at?: string;
}

// ============ Dashboard ============

export interface AccountInfo {
  total_assets: number;
  cash: number;
  stocks_value: number;
  today_profit: number;
  today_profit_rate: number;
}

export interface Position {
  symbol: string;
  name: string;
  quantity: number;
  cost: number;
  price: number;
  profit: number;
  profit_rate: number;
}

export interface SignalCount {
  pending: number;
  today_buy: number;
  today_sell: number;
}

export interface DashboardData {
  account: AccountInfo;
  positions: Position[];
  signals: SignalCount;
  backtest: {
    latest_id: number;
    total_return: number;
    max_drawdown: number;
    win_rate: number;
    sharpe_ratio: number;
  };
  watchlist_count: number;
}
