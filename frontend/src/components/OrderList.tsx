/**
 * Order list component
 */

import React from 'react';
import { Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

interface Order {
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

interface OrderListProps {
  orders: Order[];
  loading?: boolean;
}

export const OrderList: React.FC<OrderListProps> = ({ orders, loading }) => {
  const columns: ColumnsType<Order> = [
    {
      title: 'Time',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: 'Market',
      dataIndex: 'market',
      key: 'market',
    },
    {
      title: 'Side',
      dataIndex: 'side',
      key: 'side',
      render: (side: string) => (
        <Tag color={side === 'BUY' ? 'green' : 'red'}>
          {side}
        </Tag>
      ),
    },
    {
      title: 'Outcome',
      dataIndex: 'outcome',
      key: 'outcome',
    },
    {
      title: 'Price',
      dataIndex: 'price',
      key: 'price',
      render: (price: number) => `$${price.toFixed(4)}`,
    },
    {
      title: 'Size',
      dataIndex: 'size',
      key: 'size',
      render: (size: number) => size.toFixed(2),
    },
    {
      title: 'Filled',
      dataIndex: 'filled',
      key: 'filled',
      render: (filled: number, record: Order) => `${filled.toFixed(2)} / ${record.size.toFixed(2)}`,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        let color = 'default';
        if (status === 'FILLED') color = 'green';
        else if (status === 'OPEN') color = 'blue';
        else if (status === 'CANCELLED') color = 'red';
        return <Tag color={color}>{status}</Tag>;
      },
    },
  ];

  return (
    <Table
      columns={columns}
      dataSource={orders}
      loading={loading}
      rowKey="id"
      pagination={{ pageSize: 10 }}
    />
  );
};
