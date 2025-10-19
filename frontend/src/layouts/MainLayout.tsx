/**
 * Main application layout
 */

import React from 'react';
import { Layout, Menu } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import { BarChartOutlined, TeamOutlined } from '@ant-design/icons';

const { Header, Content, Footer } = Layout;

interface MainLayoutProps {
  children: React.ReactNode;
}

export const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    {
      key: '/market',
      icon: <BarChartOutlined />,
      label: 'Market',
    },
    {
      key: '/traders',
      icon: <TeamOutlined />,
      label: 'Traders',
    },
  ];

  const handleMenuClick = (e: { key: string }) => {
    navigate(e.key);
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center' }}>
        <div style={{ color: 'white', fontSize: '20px', fontWeight: 'bold', marginRight: '50px' }}>
          Poly Boost
        </div>
        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{ flex: 1, minWidth: 0 }}
        />
      </Header>
      <Content style={{ padding: '24px', minHeight: 'calc(100vh - 134px)' }}>
        <div style={{ background: '#fff', padding: 24, minHeight: 360, borderRadius: '8px' }}>
          {children}
        </div>
      </Content>
      <Footer style={{ textAlign: 'center' }}>
        Poly Boost ©{new Date().getFullYear()} - Polymarket Trading Dashboard
      </Footer>
    </Layout>
  );
};
