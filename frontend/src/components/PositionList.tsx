/**
 * Position list component
 */

import React, { useState } from 'react';
import { Table, Tag, Typography, Button, Space, Modal, InputNumber, message } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { apiClient } from '../api/client';

const POLYMARKET_EVENT_URL = 'https://polymarket.com/event';

const { Text } = Typography;

interface Position {
  title: string;
  slug?: string;
  outcome: string;
  size: number;
  avgPrice: number;
  currentValue: number;
  percentPnl: number;
  asset?: string;
  conditionId?: string;
  proxyWallet?: string;
  oppositeAsset?: string;
  oppositeOutcome?: string;
  outcomeIndex?: number;
  curPrice?: number;
  redeemable?: boolean;
  initialValue?: number;
  cashPnl?: number;
  totalBought?: number;
  realizedPnl?: number;
  percentRealizedPnl?: number;
  icon?: string;
  eventSlug?: string;
  endDate?: string;
  negativeRisk?: boolean;
}

interface PositionListProps {
  positions: Position[];
  loading?: boolean;
  walletAddress: string;
}

export const PositionList: React.FC<PositionListProps> = ({ positions, loading, walletAddress }) => {
  const [limitSellModal, setLimitSellModal] = useState<{
    visible: boolean;
    position: Position | null;
    price: number;
  }>({
    visible: false,
    position: null,
    price: 0,
  });
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // 市价卖出
  const handleMarketSell = async (position: Position) => {
    try {
      setActionLoading(position.asset || '');
      await apiClient.marketSell(walletAddress, position.asset || '', null, 'FOK');
      message.success(`Successfully sold ${position.title} at market price`);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } }; message?: string };
      message.error(`Failed to sell: ${err.response?.data?.detail || err.message || 'Unknown error'}`);
    } finally {
      setActionLoading(null);
    }
  };

  // 打开限价卖出对话框
  const handleOpenLimitSell = (position: Position) => {
    setLimitSellModal({
      visible: true,
      position,
      price: position.curPrice || 0.5,
    });
  };

  // 执行限价卖出
  const handleLimitSellConfirm = async () => {
    if (!limitSellModal.position) return;

    try {
      setActionLoading(limitSellModal.position.asset || '');
      await apiClient.limitSell(
        walletAddress,
        limitSellModal.position.asset || '',
        limitSellModal.price,
        null,
        'GTC'
      );
      message.success(`Successfully created limit sell order for ${limitSellModal.position.title} at $${limitSellModal.price}`);
      setLimitSellModal({ visible: false, position: null, price: 0 });
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } }; message?: string };
      message.error(`Failed to create limit order: ${err.response?.data?.detail || err.message || 'Unknown error'}`);
    } finally {
      setActionLoading(null);
    }
  };

  // 收获奖励
  const handleRedeem = async (position: Position) => {
    if (!position.conditionId) {
      message.error('Missing condition ID');
      return;
    }

    // 检查必要的字段
    if (!position.asset) {
      message.error('Missing token ID (asset field)');
      console.error('Position missing asset field:', position);
      return;
    }

    try {
      setActionLoading(position.asset);
      
      // 传递 token_ids 让后端查询实际余额
      // 根据 outcomeIndex 确定当前持仓和对面持仓的 token_id
      const tokenIds = position.outcomeIndex === 0 
        ? [position.asset, position.oppositeAsset || null]  // [YES, NO]
        : [position.oppositeAsset || null, position.asset]; // [NO, YES]
      
      console.log('Redeem request:', {
        conditionId: position.conditionId,
        tokenIds,
        outcomeIndex: position.outcomeIndex,
        size: position.size,
        asset: position.asset,
        oppositeAsset: position.oppositeAsset
      });
      
      // amounts 参数在后端会被实际余额替换
      const amounts = [0, 0]; // 占位参数，后端会查询实际余额
      
      await apiClient.claimRewards(walletAddress, position.conditionId, amounts, tokenIds);
      message.success(`Successfully redeemed rewards for ${position.title}`);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } }; message?: string };
      console.error('Redeem error:', error);
      message.error(`Failed to redeem: ${err.response?.data?.detail || err.message || 'Unknown error'}`);
    } finally {
      setActionLoading(null);
    }
  };

  const columns: ColumnsType<Position> = [
    {
      title: 'Market',
      dataIndex: 'title',
      key: 'market',
      render: (text: string, record: Position) => {
        const marketUrl = record.eventSlug ? `${POLYMARKET_EVENT_URL}/${record.eventSlug}` : null;
        return marketUrl ? (
          <a href={marketUrl} target="_blank" rel="noopener noreferrer">
            <Text strong>{text || 'Unknown'}</Text>
          </a>
        ) : (
          <Text strong>{text || 'Unknown'}</Text>
        );
      },
    },
    {
      title: 'Outcome',
      dataIndex: 'outcome',
      key: 'outcome',
      render: (outcome: string) => {
        const upperOutcome = outcome?.toUpperCase();
        return (
          <Tag color={upperOutcome === 'YES' ? 'green' : upperOutcome === 'NO' ? 'red' : 'default'}>
            {upperOutcome || 'N/A'}
          </Tag>
        );
      },
    },
    {
      title: 'Size',
      dataIndex: 'size',
      key: 'size',
      render: (size: number) => size?.toFixed(2) || '0.00',
      sorter: (a, b) => (a.size || 0) - (b.size || 0),
    },
    {
      title: 'Avg Price',
      dataIndex: 'avgPrice',
      key: 'avgPrice',
      render: (price: number) => `$${price?.toFixed(4) || '0.0000'}`,
      sorter: (a, b) => (a.avgPrice || 0) - (b.avgPrice || 0),
    },
    {
      title: 'Current Price',
      dataIndex: 'curPrice',
      key: 'curPrice',
      render: (price: number) => `$${price?.toFixed(4) || '0.0000'}`,
      sorter: (a, b) => (a.curPrice || 0) - (b.curPrice || 0),
    },
    {
      title: 'Initial Value',
      dataIndex: 'initialValue',
      key: 'initialValue',
      render: (value: number) => `$${value?.toFixed(2) || '0.00'}`,
      sorter: (a, b) => (a.initialValue || 0) - (b.initialValue || 0),
    },
    {
      title: 'Current Value',
      dataIndex: 'currentValue',
      key: 'currentValue',
      render: (value: number) => `$${value?.toFixed(2) || '0.00'}`,
      sorter: (a, b) => (a.currentValue || 0) - (b.currentValue || 0),
      defaultSortOrder: 'descend',
    },
    {
      title: 'Cash PnL',
      dataIndex: 'cashPnl',
      key: 'cashPnl',
      render: (pnl: number) => {
        if (pnl === undefined || pnl === null) return 'N/A';
        const color = pnl >= 0 ? 'green' : 'red';
        return <Text style={{ color }}>{pnl >= 0 ? '+' : ''}${pnl.toFixed(4)}</Text>;
      },
      sorter: (a, b) => (a.cashPnl || 0) - (b.cashPnl || 0),
    },
    {
      title: 'PnL %',
      dataIndex: 'percentPnl',
      key: 'percentPnl',
      render: (pnl: number) => {
        if (pnl === undefined || pnl === null) return 'N/A';
        // Backend already returns percentage (not decimal), so no need to multiply by 100
        const color = pnl >= 0 ? 'green' : 'red';
        return <Text style={{ color }}>{pnl >= 0 ? '+' : ''}{pnl.toFixed(2)}%</Text>;
      },
      sorter: (a, b) => (a.percentPnl || 0) - (b.percentPnl || 0),
    },
    {
      title: 'Actions',
      key: 'actions',
      fixed: 'right',
      width: 280,
      render: (_: unknown, record: Position) => {
        const isLoading = actionLoading === record.asset;
        
        // 如果可以redeem,显示redeem按钮
        if (record.redeemable) {
          return (
            <Button
              type="primary"
              size="small"
              onClick={() => handleRedeem(record)}
              loading={isLoading}
              disabled={!record.conditionId}
            >
              Redeem
            </Button>
          );
        }
        
        // 否则显示卖出按钮
        return (
          <Space size="small">
            <Button
              type="primary"
              size="small"
              onClick={() => handleMarketSell(record)}
              loading={isLoading}
              disabled={!record.asset}
            >
              Market Sell
            </Button>
            <Button
              size="small"
              onClick={() => handleOpenLimitSell(record)}
              loading={isLoading}
              disabled={!record.asset}
            >
              Limit Sell
            </Button>
          </Space>
        );
      },
    },
  ];

  return (
    <>
      <Table
        columns={columns}
        dataSource={positions}
        loading={loading}
        rowKey={(record) => record.asset || record.conditionId || ''}
        pagination={{
          defaultPageSize: 10,
          showSizeChanger: true,
          pageSizeOptions: ['10', '20', '50', '100'],
        }}
        scroll={{ x: 1500 }}
      />
      
      {/* 限价卖出对话框 */}
      <Modal
        title="Limit Sell Order"
        open={limitSellModal.visible}
        onOk={handleLimitSellConfirm}
        onCancel={() => setLimitSellModal({ visible: false, position: null, price: 0 })}
        confirmLoading={actionLoading === limitSellModal.position?.asset}
      >
        {limitSellModal.position && (
          <div style={{ padding: '20px 0' }}>
            <div style={{ marginBottom: 16 }}>
              <Text strong>Market: </Text>
              <Text>{limitSellModal.position.title}</Text>
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text strong>Outcome: </Text>
              <Tag color={limitSellModal.position.outcome?.toUpperCase() === 'YES' ? 'green' : 'red'}>
                {limitSellModal.position.outcome?.toUpperCase()}
              </Tag>
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text strong>Size: </Text>
              <Text>{limitSellModal.position.size?.toFixed(2)} (All)</Text>
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text strong>Current Price: </Text>
              <Text>${limitSellModal.position.curPrice?.toFixed(4)}</Text>
            </div>
            <div>
              <Text strong>Limit Price: </Text>
              <InputNumber
                min={0.01}
                max={0.99}
                step={0.01}
                value={limitSellModal.price}
                onChange={(value) => setLimitSellModal({ ...limitSellModal, price: value || 0.5 })}
                precision={4}
                style={{ width: 200 }}
                prefix="$"
              />
            </div>
            <div style={{ marginTop: 16, padding: 10, background: '#f0f0f0', borderRadius: 4 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                Note: This will create a limit sell order for all {limitSellModal.position.size?.toFixed(2)} shares at ${limitSellModal.price?.toFixed(4)} per share.
              </Text>
            </div>
          </div>
        )}
      </Modal>
    </>
  );
};
