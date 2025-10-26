/**
 * Traders page - Shows trader positions, orders, and activities
 */

import React, { useState, useEffect } from 'react';
import { Card, Select, Statistic, Row, Col, Tabs, Typography, Spin, message, Button } from 'antd';
import { WalletOutlined, DollarOutlined, LineChartOutlined, ReloadOutlined } from '@ant-design/icons';
import { apiClient } from '../../api/client';
import { PositionList } from '../../components/PositionList';
import { OrderList } from '../../components/OrderList';
import { ActivityList } from '../../components/ActivityList';
import type { ConfigWallet, PositionSummary } from '../../types';

const { Title } = Typography;
const { Option } = Select;

const SELECTED_WALLET_KEY = 'poly-boost-selected-wallet';

export const TradersPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [activitiesLoading, setActivitiesLoading] = useState(false);
  const [wallets, setWallets] = useState<ConfigWallet[]>([]);
  const [selectedWallet, setSelectedWallet] = useState<string>('');
  const [positionData, setPositionData] = useState<PositionSummary | null>(null);
  const [balance, setBalance] = useState<number | null>(null);
  const [orders, setOrders] = useState<any[]>([]);
  const [activities, setActivities] = useState<any[]>([]);
  const [currentTab, setCurrentTab] = useState<string>('positions');
  const [ordersLoaded, setOrdersLoaded] = useState(false);
  const [activitiesLoaded, setActivitiesLoaded] = useState(false);

  useEffect(() => {
    loadWallets();
  }, []);

  useEffect(() => {
    if (selectedWallet) {
      loadWalletData(selectedWallet);
      // Reset load states when wallet changes
      setOrdersLoaded(false);
      setActivitiesLoaded(false);
      setOrders([]);
      setActivities([]);
    }
  }, [selectedWallet]);

  const loadWallets = async () => {
    try {
      const configWallets = await apiClient.getConfigWallets();
      setWallets(configWallets);

      // Try to restore previously selected wallet from localStorage
      const savedWallet = localStorage.getItem(SELECTED_WALLET_KEY);

      if (savedWallet) {
        // Check if saved wallet still exists in config
        const walletExists = configWallets.find((w: any) => w.address === savedWallet);
        if (walletExists) {
          setSelectedWallet(savedWallet);
          return;
        }
      }

      // If no saved wallet or saved wallet doesn't exist, auto-select first monitored wallet
      const firstMonitored = configWallets.find((w: any) => w.type === 'monitored');
      if (firstMonitored) {
        setSelectedWallet(firstMonitored.address);
        localStorage.setItem(SELECTED_WALLET_KEY, firstMonitored.address);
      }
    } catch (error) {
      console.error('Failed to load wallets:', error);
      message.error('Failed to load wallet configuration');
    }
  };

  const loadWalletData = async (address: string) => {
    setLoading(true);
    try {
      // Load positions and balance in parallel, but handle errors independently
      const [positionsResult, balanceResult] = await Promise.allSettled([
        apiClient.getPositions(address),
        apiClient.getWalletBalance(address),
      ]);

      // Handle positions result
      if (positionsResult.status === 'fulfilled') {
        setPositionData(positionsResult.value);
      } else {
        console.error('Failed to load positions:', positionsResult.reason);
        message.error('Failed to load positions');
        setPositionData(null);
      }

      // Handle balance result (don't fail if balance query fails)
      if (balanceResult.status === 'fulfilled') {
        const balanceData = balanceResult.value;

        // Check if balance query was successful (backend now returns success flag)
        if (balanceData.success && balanceData.balance !== null) {
          setBalance(balanceData.balance);
        } else {
          console.warn('Balance query failed:', balanceData.error || 'Unknown error');
          message.warning('Balance unavailable for this wallet');
          setBalance(null);
        }
      } else {
        console.error('Failed to load balance:', balanceResult.reason);
        message.warning('Failed to load balance (positions still available)');
        setBalance(null);
      }
    } catch (error) {
      console.error('Unexpected error loading wallet data:', error);
      message.error('Unexpected error occurred');
    } finally {
      setLoading(false);
    }
  };

  const loadOrders = async () => {
    if (!selectedWallet) return;
    setOrdersLoading(true);
    try {
      console.log('Loading active orders for wallet:', selectedWallet);
      const ordersData = await apiClient.getActiveOrders(selectedWallet);
      setOrders(ordersData);
      setOrdersLoaded(true);
      console.log('Loaded', ordersData.length, 'active orders');
    } catch (error) {
      console.error('Failed to load orders:', error);
      message.error('Failed to load active orders');
      setOrders([]);
    } finally {
      setOrdersLoading(false);
    }
  };

  const loadActivities = async () => {
    if (!selectedWallet) return;
    setActivitiesLoading(true);
    try {
      console.log('Loading activities for wallet:', selectedWallet);
      const activitiesData = await apiClient.getActivityList(selectedWallet, {
        limit: 100,
        sort_direction: 'DESC'
      });
      setActivities(activitiesData);
      setActivitiesLoaded(true);
      console.log('Loaded', activitiesData.length, 'activities');
    } catch (error) {
      console.error('Failed to load activities:', error);
      message.error('Failed to load activities');
      setActivities([]);
    } finally {
      setActivitiesLoading(false);
    }
  };

  const handleWalletChange = (value: string) => {
    setSelectedWallet(value);
    // Save to localStorage when user changes wallet
    localStorage.setItem(SELECTED_WALLET_KEY, value);
  };

  const handleRefresh = async () => {
    if (!selectedWallet) return;

    // Refresh based on current tab
    if (currentTab === 'positions') {
      await loadWalletData(selectedWallet);
    } else if (currentTab === 'orders') {
      await loadOrders();
    } else if (currentTab === 'activities') {
      await loadActivities();
    }
  };

  const handleTabChange = (key: string) => {
    setCurrentTab(key);

    // Auto-load data when switching to a tab if not loaded yet
    if (key === 'orders' && !ordersLoaded && !ordersLoading) {
      loadOrders();
    } else if (key === 'activities' && !activitiesLoaded && !activitiesLoading) {
      loadActivities();
    }
  };

  const isAnyLoading = loading || ordersLoading || activitiesLoading;

  const selectedWalletInfo = wallets.find(w => w.address === selectedWallet);

  // Calculate total portfolio value (position value + balance)
  // If balance is unavailable (null), only show position value
  const totalPortfolio = (positionData?.total_value || 0) + (balance !== null ? balance : 0);
  const isBalanceAvailable = balance !== null;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2}>Traders Dashboard</Title>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <Button
            icon={<ReloadOutlined />}
            onClick={handleRefresh}
            loading={isAnyLoading}
            disabled={!selectedWallet}
          >
            Refresh All
          </Button>
          <Select
            style={{ width: 400 }}
            placeholder="Select a wallet"
            value={selectedWallet}
            onChange={handleWalletChange}
            loading={wallets.length === 0}
          >
            {wallets.map((wallet) => (
              <Option key={wallet.address} value={wallet.address}>
                {wallet.name} - {wallet.address.substring(0, 8)}...{wallet.address.substring(wallet.address.length - 6)}
                {wallet.type === 'monitored' && ' (Monitored)'}
              </Option>
            ))}
          </Select>
        </div>
      </div>

      {selectedWallet && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={24}>
              <Card>
                <Statistic
                  title="Wallet Address"
                  value={selectedWalletInfo?.name || 'Unknown'}
                  prefix={<WalletOutlined />}
                  valueStyle={{ fontSize: '18px' }}
                />
                <div style={{ fontSize: '12px', color: '#888', marginTop: '8px' }}>
                  {selectedWallet.substring(0, 16)}...{selectedWallet.substring(selectedWallet.length - 8)}
                </div>
              </Card>
            </Col>
          </Row>
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={6}>
              <Card>
                <Statistic
                  title={isBalanceAvailable ? "Total Portfolio" : "Total Portfolio (Position Only)"}
                  value={totalPortfolio}
                  precision={2}
                  prefix={<DollarOutlined />}
                  suffix="USDC"
                  valueStyle={{ color: '#722ed1', fontSize: '24px', fontWeight: 'bold' }}
                  loading={loading}
                />
                {!isBalanceAvailable && !loading && (
                  <div style={{ fontSize: '12px', color: '#ff9800', marginTop: '8px' }}>
                    Balance unavailable - showing positions only
                  </div>
                )}
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="USDC Balance"
                  value={balance !== null ? balance : 0}
                  precision={2}
                  prefix={<DollarOutlined />}
                  suffix={balance !== null ? "USDC" : "(unavailable)"}
                  valueStyle={{ color: balance !== null ? '#1890ff' : '#999' }}
                  loading={loading}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Position Value"
                  value={positionData?.total_value || 0}
                  precision={2}
                  prefix={<DollarOutlined />}
                  suffix="USDC"
                  valueStyle={{ color: '#3f8600' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Active Positions"
                  value={positionData?.total_positions || 0}
                  prefix={<LineChartOutlined />}
                />
              </Card>
            </Col>
          </Row>

          <Card>
            <Tabs
              activeKey={currentTab}
              onChange={handleTabChange}
              items={[
                {
                  key: 'positions',
                  label: 'Positions',
                  children: loading ? (
                    <div style={{ textAlign: 'center', padding: '50px' }}>
                      <Spin size="large" />
                    </div>
                  ) : (
                    <PositionList
                      positions={positionData?.positions || []}
                      loading={loading}
                      walletAddress={selectedWallet}
                    />
                  ),
                },
                {
                  key: 'orders',
                  label: 'Orders',
                  children: (
                    <OrderList
                      orders={orders}
                      loading={ordersLoading}
                    />
                  ),
                },
                {
                  key: 'activities',
                  label: 'Activity History',
                  children: (
                    <ActivityList
                      activities={activities}
                      loading={activitiesLoading}
                    />
                  ),
                },
              ]}
            />
          </Card>
        </>
      )}

      {!selectedWallet && (
        <Card>
          <div style={{ textAlign: 'center', padding: '50px', color: '#888' }}>
            Please select a wallet to view trader data
          </div>
        </Card>
      )}
    </div>
  );
};
