/**
 * API client for communicating with backend
 */

import axios from 'axios';
import type { AxiosInstance } from 'axios';
import { config } from '../config';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: config.apiBaseUrl,
      timeout: config.apiTimeout,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        return response;
      },
      (error) => {
        console.error('API Error:', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  // Positions API
  async getPositions(walletAddress: string) {
    const response = await this.client.get(`/positions/${walletAddress}`);
    return response.data;
  }

  async getPositionValue(walletAddress: string) {
    const response = await this.client.get(`/positions/${walletAddress}/value`);
    return response.data;
  }

  // Wallets API
  async getWalletInfo(walletAddress: string) {
    const response = await this.client.get(`/wallets/${walletAddress}`);
    return response.data;
  }

  async getWalletBalance(walletAddress: string) {
    const response = await this.client.get(`/wallets/${walletAddress}/balance`);
    return response.data;
  }

  async listManagedWallets() {
    const response = await this.client.get('/wallets/');
    return response.data;
  }

  // Trading API
  async getTradingStatus() {
    const response = await this.client.get('/trading/status');
    return response.data;
  }

  async listTraders() {
    const response = await this.client.get('/trading/traders');
    return response.data;
  }

  async getTraderStats(traderName: string) {
    const response = await this.client.get(`/trading/traders/${traderName}/stats`);
    return response.data;
  }

  async startCopyTrading(traderName: string, sourceWallet: string) {
    const response = await this.client.post('/trading/copy/start', {
      trader_name: traderName,
      source_wallet: sourceWallet,
    });
    return response.data;
  }

  async stopCopyTrading(traderName: string, sourceWallet: string) {
    const response = await this.client.post('/trading/copy/stop', {
      trader_name: traderName,
      source_wallet: sourceWallet,
    });
    return response.data;
  }

  // Config API (read config.yaml wallets)
  async getConfigWallets() {
    const response = await this.client.get('/config/wallets');
    return response.data;
  }

  // Orders API
  async getActiveOrders(walletAddress: string, params?: { order_id?: string; condition_id?: string; token_id?: string }) {
    const response = await this.client.get(`/orders/${walletAddress}`, { params });
    return response.data;
  }

  async getTradeHistory(walletAddress: string, params?: { condition_id?: string; token_id?: string; trade_id?: string }) {
    const response = await this.client.get(`/orders/${walletAddress}/history`, { params });
    return response.data;
  }

  async marketSell(walletAddress: string, tokenId: string, amount: number | null, orderType: string = 'FOK') {
    const response = await this.client.post(`/orders/${walletAddress}/sell/market`, {
      token_id: tokenId,
      amount: amount,
      order_type: orderType,
    });
    return response.data;
  }

  async limitSell(walletAddress: string, tokenId: string, price: number, amount: number | null, orderType: string = 'GTC') {
    const response = await this.client.post(`/orders/${walletAddress}/sell/limit`, {
      token_id: tokenId,
      price: price,
      amount: amount,
      order_type: orderType,
    });
    return response.data;
  }

  async claimRewards(walletAddress: string, conditionId: string, amounts: number[], tokenIds?: (string | null)[]) {
    const response = await this.client.post(`/orders/${walletAddress}/rewards/claim`, {
      condition_id: conditionId,
      amounts: amounts,
      token_ids: tokenIds,
    });
    return response.data;
  }

  // Activity API
  async getActivitySummary(walletAddress: string, params?: { limit?: number }) {
    const response = await this.client.get(`/activity/${walletAddress}`, { params });
    return response.data;
  }

  async getActivityList(
    walletAddress: string,
    params?: {
      limit?: number;
      offset?: number;
      condition_id?: string;
      activity_type?: string;
      side?: string;
      sort_by?: string;
      sort_direction?: string;
    }
  ) {
    const response = await this.client.get(`/activity/${walletAddress}/list`, { params });
    return response.data;
  }
}

export const apiClient = new ApiClient();
