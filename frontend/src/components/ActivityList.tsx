/**
 * Activity history component
 */

import React from 'react';
import { Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

const { Link } = Typography;

interface Activity {
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

interface ActivityListProps {
  activities: Activity[];
  loading?: boolean;
}

export const ActivityList: React.FC<ActivityListProps> = ({ activities, loading }) => {
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
        else if (type === 'DEPOSIT') color = 'green';
        else if (type === 'WITHDRAW') color = 'orange';
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
    },
    {
      title: 'Amount',
      dataIndex: 'amount',
      key: 'amount',
      render: (amount: number) => `${amount.toFixed(2)} USDC`,
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
      dataSource={activities}
      loading={loading}
      rowKey="id"
      pagination={{ pageSize: 15 }}
    />
  );
};
