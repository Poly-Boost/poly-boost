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
  type: 'TRADE' | 'DEPOSIT' | 'WITHDRAW';
  market?: string;
  outcome?: string;
  side?: 'BUY' | 'SELL';
  amount: number;
  price?: number;
  timestamp: string;
  txHash?: string;
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
