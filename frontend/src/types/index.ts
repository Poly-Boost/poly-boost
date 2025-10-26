/**
 * Type definitions
 */

export interface Position {
  id: string;
  market: string;
  outcome: string;
  size: number;
  value: number;
  avgPrice: number;
  pnl?: number;
}

export interface Order {
  id: string;
  market: string;
  outcome: string;
  side: 'BUY' | 'SELL';
  price: number;
  size: number;
  filled: number;
  status: 'OPEN' | 'FILLED' | 'CANCELLED';
  createdAt: string;
}

export interface Activity {
  id: string;
  type: 'TRADE' | 'SPLIT' | 'MERGE' | 'REDEEM' | 'REWARD' | 'CONVERSION';
  market?: string;
  outcome?: string;
  side?: 'BUY' | 'SELL';
  amount: number;
  price?: number;
  timestamp: string;
  txHash?: string;
}

// Backend response types
export interface BackendOpenOrder {
  order_id: string;
  status: string;
  owner: string;
  maker_address: string;
  condition_id: string;
  token_id: string;
  side: 'BUY' | 'SELL';
  original_size: number;
  size_matched: number;
  price: number;
  outcome: string;
  expiration: string;
  order_type: 'GTC' | 'GTD';
  associate_trades: string[];
  created_at: string;
  market_name?: string | null;  // Added by backend
}

export interface BackendPolygonTrade {
  trade_id: string;
  taker_order_id: string;
  condition_id: string;
  id: string;
  side: 'BUY' | 'SELL';
  size: number;
  fee_rate_bps: number;
  price: number;
  status: string;
  match_time: string;
  last_update: string;
  outcome: string;
  bucket_index: number;
  owner: string;
  maker_address: string;
  transaction_hash: string;
  maker_orders: any[];
  trader_side: 'TAKER' | 'MAKER';
}

export interface BackendActivity {
  proxy_wallet: string;
  timestamp: string;
  condition_id: string;
  type: 'TRADE' | 'SPLIT' | 'MERGE' | 'REDEEM' | 'REWARD' | 'CONVERSION';
  size: number;
  usdc_size: number;
  price: number;
  asset: string;
  side: string | null;
  outcome_index: number;
  title: string;
  slug: string;
  icon: string;
  event_slug: string;
  outcome: string;
  name: string;
  pseudonym: string;
  bio: string;
  profile_image: string;
  profile_image_optimized: string;
  transaction_hash: string;
}

export interface WalletInfo {
  address: string;
  name?: string;
  balance: number;
  totalValue: number;
  positionCount: number;
}

export interface PositionSummary {
  wallet_address: string;
  total_positions: number;
  total_value: number;
  positions: any[];
}

export interface ConfigWallet {
  name: string;
  address: string;
  proxy_address?: string;
  type?: string;
}
