/**
 * Order list component - Displays active (open) orders
 */

import React, { useMemo } from 'react';
import { Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import type { BackendOpenOrder } from '../types';

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
  orders: BackendOpenOrder[];
  loading?: boolean;
}

// Convert backend active order data to frontend order format
const convertOpenOrderToOrder = (openOrder: BackendOpenOrder): Order => ({
  id: openOrder.order_id,
  market: openOrder.market_name || openOrder.condition_id, // Use market name if available
  outcome: openOrder.outcome,
  side: openOrder.side,
  price: openOrder.price,
  size: openOrder.original_size,
  filled: openOrder.size_matched,
  status: openOrder.status as 'OPEN' | 'FILLED' | 'CANCELLED',
  createdAt: openOrder.created_at,
});

export const OrderList: React.FC<OrderListProps> = ({ orders, loading }) => {
  // Convert backend data to frontend format
  const formattedOrders = useMemo(() => {
    return orders.map(convertOpenOrderToOrder);
  }, [orders]);

  const columns: ColumnsType<Order> = [
    {
      title: 'Time',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss'),
      sorter: (a, b) => dayjs(a.createdAt).unix() - dayjs(b.createdAt).unix(),
    },
    {
      title: 'Market',
      dataIndex: 'market',
      key: 'market',
      ellipsis: true,
      render: (market: string) => (
        <span title={market}>{market}</span>
      ),
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
      sorter: (a, b) => a.price - b.price,
    },
    {
      title: 'Size',
      dataIndex: 'size',
      key: 'size',
      render: (size: number) => size.toFixed(2),
      sorter: (a, b) => a.size - b.size,
    },
    {
      title: 'Filled',
      dataIndex: 'filled',
      key: 'filled',
      render: (filled: number, record: Order) => `${filled.toFixed(2)} / ${record.size.toFixed(2)}`,
      sorter: (a, b) => a.filled - b.filled,
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
        else color = 'orange'; // For other statuses like LIVE, etc.
        return <Tag color={color}>{status}</Tag>;
      },
      filters: [
        { text: 'OPEN', value: 'OPEN' },
        { text: 'FILLED', value: 'FILLED' },
        { text: 'CANCELLED', value: 'CANCELLED' },
      ],
      onFilter: (value, record) => record.status === value,
    },
  ];

  return (
    <Table
      columns={columns}
      dataSource={formattedOrders}
      loading={loading}
      rowKey="id"
      pagination={{
        defaultPageSize: 10,
        showSizeChanger: true,
        pageSizeOptions: ['10', '20', '50', '100'],
      }}
    />
  );
};
