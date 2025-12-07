/**
 * Traders page - Shows trader positions, orders, and activities
 */

import React, { useState, useEffect } from 'react';
import { Card, Select, Statistic, Row, Col, Tabs, Typography, Spin, message, Button, Modal, Table } from 'antd';
import { WalletOutlined, DollarOutlined, LineChartOutlined, ReloadOutlined, GiftOutlined } from '@ant-design/icons';
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
  const [redeemAllLoading, setRedeemAllLoading] = useState(false);
  const [wallets, setWallets] = useState<ConfigWallet[]>([]);
  const [selectedWallet, setSelectedWallet] = useState<string>('');
  const [positionData, setPositionData] = useState<PositionSummary | null>(null);
  const [balance, setBalance] = useState<number | null>(null);
  const [orders, setOrders] = useState<any[]>([]);
  const [activities, setActivities] = useState<any[]>([]);
  const [currentTab, setCurrentTab] = useState<string>('positions');
  const [ordersLoaded, setOrdersLoaded] = useState(false);
  const [activitiesLoaded, setActivitiesLoaded] = useState(false);
  const [redeemConfirmModalVisible, setRedeemConfirmModalVisible] = useState(false);
  const [redeemResultModalVisible, setRedeemResultModalVisible] = useState(false);
  const [redeemResult, setRedeemResult] = useState<any>(null);

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

  // 计算可赎回仓位
  const redeemablePositions = positionData?.positions?.filter(p => p.redeemable === true) || [];
  const redeemableCount = redeemablePositions.length;
  const redeemableTotalValue = redeemablePositions.reduce((sum, p) => sum + (p.currentValue || 0), 0);

  // 打开批量赎回确认弹窗
  const handleOpenRedeemAll = () => {
    if (redeemableCount === 0) {
      message.warning('没有可赎回的仓位');
      return;
    }
    setRedeemConfirmModalVisible(true);
  };

  // 执行批量赎回
  const handleConfirmRedeemAll = async () => {
    setRedeemConfirmModalVisible(false);
    setRedeemAllLoading(true);

    const hideLoading = message.loading({ content: '批量赎回进行中...', key: 'redeem-all', duration: 0 });

    try {
      const result = await apiClient.redeemAllPositions(selectedWallet);

      hideLoading();
      setRedeemAllLoading(false);

      // 显示结果
      setRedeemResult(result);
      setRedeemResultModalVisible(true);

      // 根据结果显示提示
      if (result.status === 'success') {
        message.success(`成功赎回 ${result.successful} 个仓位`);
      } else if (result.status === 'partial') {
        message.warning(`部分成功: 成功 ${result.successful} 个, 失败 ${result.failed} 个`);
      } else {
        message.error('批量赎回失败');
      }

      // 自动刷新仓位列表
      await loadWalletData(selectedWallet);

    } catch (error: unknown) {
      hideLoading();
      setRedeemAllLoading(false);

      const err = error as { response?: { data?: { detail?: string } }; message?: string };
      message.error(`批量赎回失败: ${err.response?.data?.detail || err.message || '未知错误'}`);
      console.error('Redeem all error:', error);
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
            icon={<GiftOutlined />}
            onClick={handleOpenRedeemAll}
            loading={redeemAllLoading}
            disabled={!selectedWallet || redeemableCount === 0}
            type="primary"
            style={{ backgroundColor: '#52c41a' }}
          >
            Redeem All ({redeemableCount})
          </Button>
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
                      walletAddress={selectedWallet}
                      onCancelled={loadOrders}
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

      {/* 批量赎回确认弹窗 */}
      <Modal
        title="确认批量赎回"
        open={redeemConfirmModalVisible}
        onOk={handleConfirmRedeemAll}
        onCancel={() => setRedeemConfirmModalVisible(false)}
        okText="确认赎回"
        cancelText="取消"
        confirmLoading={redeemAllLoading}
      >
        <div style={{ padding: '20px 0' }}>
          <div style={{ marginBottom: 16 }}>
            <Typography.Text strong>可赎回仓位数量: </Typography.Text>
            <Typography.Text style={{ fontSize: '18px', color: '#1890ff' }}>
              {redeemableCount} 个
            </Typography.Text>
          </div>
          <div style={{ marginBottom: 16 }}>
            <Typography.Text strong>预估总价值: </Typography.Text>
            <Typography.Text style={{ fontSize: '18px', color: '#52c41a' }}>
              ${redeemableTotalValue.toFixed(2)} USDC
            </Typography.Text>
          </div>
          <div style={{ marginBottom: 16, padding: 12, background: '#fff7e6', border: '1px solid #ffd591', borderRadius: 4 }}>
            <Typography.Text type="warning" strong>
              ⚠️ 注意事项:
            </Typography.Text>
            <ul style={{ marginTop: 8, marginBottom: 0, paddingLeft: 20 }}>
              <li>此操作会产生 Gas 费用，请确保钱包余额充足</li>
              <li>赎回过程可能需要几分钟时间，请耐心等待</li>
              <li>个别仓位赎回失败不会影响其他仓位</li>
            </ul>
          </div>
          <div style={{ padding: 12, background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: 4 }}>
            <Typography.Text style={{ fontSize: '12px', color: '#52c41a' }}>
              <strong>即将赎回的仓位:</strong>
            </Typography.Text>
            <div style={{ maxHeight: 200, overflow: 'auto', marginTop: 8 }}>
              {redeemablePositions.map((p, idx) => (
                <div key={idx} style={{ padding: '4px 0', borderBottom: idx < redeemablePositions.length - 1 ? '1px solid #d9f7be' : 'none' }}>
                  <Typography.Text style={{ fontSize: '12px' }}>
                    {idx + 1}. {p.title || 'Unknown'} - {p.outcome} (${p.currentValue?.toFixed(2)})
                  </Typography.Text>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Modal>

      {/* 批量赎回结果弹窗 */}
      <Modal
        title="批量赎回结果"
        open={redeemResultModalVisible}
        onOk={() => setRedeemResultModalVisible(false)}
        onCancel={() => setRedeemResultModalVisible(false)}
        footer={[
          <Button key="close" type="primary" onClick={() => setRedeemResultModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={800}
      >
        {redeemResult && (
          <div>
            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={8}>
                <Statistic
                  title="总数"
                  value={redeemResult.total_positions}
                  prefix={<GiftOutlined />}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="成功"
                  value={redeemResult.successful}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="失败"
                  value={redeemResult.failed}
                  valueStyle={{ color: redeemResult.failed > 0 ? '#ff4d4f' : '#666' }}
                />
              </Col>
            </Row>

            {redeemResult.successful > 0 && (
              <div style={{ marginBottom: 24 }}>
                <Typography.Title level={5} style={{ color: '#52c41a' }}>
                  ✓ 成功赎回的仓位 ({redeemResult.successful})
                </Typography.Title>
                <Table
                  size="small"
                  dataSource={redeemResult.results}
                  rowKey={(record, index) => `success-${index}`}
                  pagination={false}
                  scroll={{ y: 200 }}
                  columns={[
                    {
                      title: '市场',
                      dataIndex: 'market_name',
                      key: 'market_name',
                      width: 200,
                      ellipsis: true,
                    },
                    {
                      title: '结果',
                      dataIndex: 'outcome',
                      key: 'outcome',
                      width: 80,
                      render: (outcome: string) => (
                        <Typography.Text strong style={{ color: outcome?.toUpperCase() === 'YES' ? '#52c41a' : '#ff4d4f' }}>
                          {outcome?.toUpperCase()}
                        </Typography.Text>
                      ),
                    },
                    {
                      title: '金额',
                      dataIndex: 'amounts',
                      key: 'amounts',
                      width: 100,
                      render: (amounts: number[]) => (
                        <Typography.Text>
                          ${amounts?.reduce((a, b) => a + b, 0).toFixed(2)}
                        </Typography.Text>
                      ),
                    },
                    {
                      title: '交易哈希',
                      dataIndex: 'tx_hash',
                      key: 'tx_hash',
                      ellipsis: true,
                      render: (txHash: string) => (
                        txHash ? (
                          <a
                            href={`https://polygonscan.com/tx/${txHash}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ fontSize: '12px' }}
                          >
                            {txHash.substring(0, 10)}...{txHash.substring(txHash.length - 8)}
                          </a>
                        ) : 'N/A'
                      ),
                    },
                  ]}
                />
              </div>
            )}

            {redeemResult.failed > 0 && (
              <div>
                <Typography.Title level={5} style={{ color: '#ff4d4f' }}>
                  ✗ 赎回失败的仓位 ({redeemResult.failed})
                </Typography.Title>
                <Table
                  size="small"
                  dataSource={redeemResult.errors}
                  rowKey={(record, index) => `error-${index}`}
                  pagination={false}
                  scroll={{ y: 200 }}
                  columns={[
                    {
                      title: '市场',
                      dataIndex: 'market_name',
                      key: 'market_name',
                      width: 200,
                      ellipsis: true,
                    },
                    {
                      title: '结果',
                      dataIndex: 'outcome',
                      key: 'outcome',
                      width: 80,
                      render: (outcome: string) => (
                        <Typography.Text strong>
                          {outcome?.toUpperCase()}
                        </Typography.Text>
                      ),
                    },
                    {
                      title: '错误原因',
                      dataIndex: 'error_message',
                      key: 'error_message',
                      ellipsis: true,
                      render: (error: string) => (
                        <Typography.Text type="danger" style={{ fontSize: '12px' }}>
                          {error}
                        </Typography.Text>
                      ),
                    },
                  ]}
                />
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};
