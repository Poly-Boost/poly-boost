/**
 * Market page - Shows market overview and data
 */

import React, { useState, useEffect } from 'react';
import { Card, Statistic, Row, Col, Table, Typography, Spin } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, TeamOutlined } from '@ant-design/icons';
import { apiClient } from '../../api/client';

const { Title } = Typography;

export const MarketPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [tradingStatus, setTradingStatus] = useState<any>(null);

  useEffect(() => {
    loadMarketData();
  }, []);

  const loadMarketData = async () => {
    setLoading(true);
    try {
      const status = await apiClient.getTradingStatus();
      setTradingStatus(status);
    } catch (error) {
      console.error('Failed to load market data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <Title level={2}>Market Overview</Title>

      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="Active Traders"
              value={tradingStatus?.active_traders || 0}
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Total Volume"
              value={0}
              precision={2}
              valueStyle={{ color: '#3f8600' }}
              prefix={<ArrowUpOutlined />}
              suffix="USDC"
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="24h Change"
              value={0}
              precision={2}
              valueStyle={{ color: '#cf1322' }}
              prefix={<ArrowDownOutlined />}
              suffix="%"
            />
          </Card>
        </Col>
      </Row>

      <Card title="Recent Activity" style={{ marginTop: 24 }}>
        <Table
          dataSource={[]}
          columns={[
            {
              title: 'Time',
              dataIndex: 'time',
              key: 'time',
            },
            {
              title: 'Market',
              dataIndex: 'market',
              key: 'market',
            },
            {
              title: 'Type',
              dataIndex: 'type',
              key: 'type',
            },
            {
              title: 'Amount',
              dataIndex: 'amount',
              key: 'amount',
              render: (amount: number) => `${amount} USDC`,
            },
          ]}
          pagination={false}
        />
      </Card>
    </div>
  );
};
