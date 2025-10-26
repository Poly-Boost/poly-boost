/**
 * Activity history component
 */

import React, { useMemo } from 'react';
import { Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import type { BackendActivity } from '../types';

const { Link } = Typography;

interface Activity {
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

interface ActivityListProps {
  activities: BackendActivity[];
  loading?: boolean;
}

// Convert backend activity data to frontend format
const convertBackendActivity = (activity: BackendActivity): Activity => ({
  id: activity.transaction_hash,
  type: activity.type,
  market: activity.title,
  outcome: activity.outcome,
  side: activity.side as 'BUY' | 'SELL' | undefined,
  amount: activity.usdc_size,
  price: activity.price,
  timestamp: activity.timestamp,
  txHash: activity.transaction_hash,
});

export const ActivityList: React.FC<ActivityListProps> = ({ activities, loading }) => {
  // Convert backend data to frontend format
  const formattedActivities = useMemo(() => {
    return activities.map(convertBackendActivity);
  }, [activities]);

  const columns: ColumnsType<Activity> = [
    {
      title: 'Time',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss'),
      sorter: (a, b) => dayjs(a.timestamp).unix() - dayjs(b.timestamp).unix(),
      defaultSortOrder: 'descend',
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => {
        let color = 'default';
        if (type === 'TRADE') color = 'blue';
        else if (type === 'SPLIT') color = 'purple';
        else if (type === 'MERGE') color = 'cyan';
        else if (type === 'REDEEM') color = 'green';
        else if (type === 'REWARD') color = 'gold';
        else if (type === 'CONVERSION') color = 'magenta';
        return <Tag color={color}>{type}</Tag>;
      },
    },
    {
      title: 'Market',
      dataIndex: 'market',
      key: 'market',
      render: (market?: string) => market || 'N/A',
    },
    {
      title: 'Side',
      dataIndex: 'side',
      key: 'side',
      render: (side?: string) => side ? (
        <Tag color={side === 'BUY' ? 'green' : 'red'}>
          {side}
        </Tag>
      ) : 'N/A',
    },
    {
      title: 'Outcome',
      dataIndex: 'outcome',
      key: 'outcome',
      render: (outcome?: string) => outcome || 'N/A',
    },
    {
      title: 'Price',
      dataIndex: 'price',
      key: 'price',
      render: (price?: number) => price ? `$${price.toFixed(4)}` : 'N/A',
      sorter: (a, b) => (a.price || 0) - (b.price || 0),
    },
    {
      title: 'Amount',
      dataIndex: 'amount',
      key: 'amount',
      render: (amount: number) => `${amount.toFixed(2)} USDC`,
      sorter: (a, b) => a.amount - b.amount,
    },
    {
      title: 'Tx Hash',
      dataIndex: 'txHash',
      key: 'txHash',
      render: (hash?: string) => hash ? (
        <Link href={`https://polygonscan.com/tx/${hash}`} target="_blank">
          {hash.substring(0, 10)}...
        </Link>
      ) : 'N/A',
    },
  ];

  return (
    <Table
      columns={columns}
      dataSource={formattedActivities}
      loading={loading}
      rowKey="id"
      pagination={{
        defaultPageSize: 15,
        showSizeChanger: true,
        pageSizeOptions: ['10', '20', '50', '100'],
      }}
    />
  );
};
