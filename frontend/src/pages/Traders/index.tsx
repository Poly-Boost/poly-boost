/**
 * Traders page - Shows trader positions, orders, and activities
 */

import React, { useState, useEffect } from 'react';
import { Card, Select, Statistic, Row, Col, Tabs, Typography, Spin, message } from 'antd';
import { WalletOutlined, DollarOutlined, LineChartOutlined } from '@ant-design/icons';
import { apiClient } from '../../api/client';
import { PositionList } from '../../components/PositionList';
import { OrderList } from '../../components/OrderList';
import { ActivityList } from '../../components/ActivityList';
import type { ConfigWallet, PositionSummary } from '../../types';

const { Title } = Typography;
const { Option } = Select;

export const TradersPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [wallets, setWallets] = useState<ConfigWallet[]>([]);
  const [selectedWallet, setSelectedWallet] = useState<string>('');
  const [positionData, setPositionData] = useState<PositionSummary | null>(null);

  useEffect(() => {
    loadWallets();
  }, []);

  useEffect(() => {
    if (selectedWallet) {
      loadWalletData(selectedWallet);
    }
  }, [selectedWallet]);

  const loadWallets = async () => {
    try {
      const configWallets = await apiClient.getConfigWallets();
      setWallets(configWallets);

      // Auto-select first monitored wallet
      const firstMonitored = configWallets.find((w: any) => w.type === 'monitored');
      if (firstMonitored) {
        setSelectedWallet(firstMonitored.address);
      }
    } catch (error) {
      console.error('Failed to load wallets:', error);
      message.error('Failed to load wallet configuration');
    }
  };

  const loadWalletData = async (address: string) => {
    setLoading(true);
    try {
      // Load positions
      const positions = await apiClient.getPositions(address);
      setPositionData(positions);
    } catch (error) {
      console.error('Failed to load wallet data:', error);
      message.error('Failed to load wallet data');
    } finally {
      setLoading(false);
    }
  };

  const handleWalletChange = (value: string) => {
    setSelectedWallet(value);
  };

  const selectedWalletInfo = wallets.find(w => w.address === selectedWallet);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2}>Traders Dashboard</Title>
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

      {selectedWallet && (
        <>
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={8}>
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
            <Col span={8}>
              <Card>
                <Statistic
                  title="Total Position Value"
                  value={positionData?.total_value || 0}
                  precision={2}
                  prefix={<DollarOutlined />}
                  suffix="USDC"
                  valueStyle={{ color: '#3f8600' }}
                />
              </Card>
            </Col>
            <Col span={8}>
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
              defaultActiveKey="positions"
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
                      orders={[]}
                      loading={false}
                    />
                  ),
                },
                {
                  key: 'activities',
                  label: 'Activity History',
                  children: (
                    <ActivityList
                      activities={[]}
                      loading={false}
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
