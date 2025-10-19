/**
 * Main application component
 */

import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import { MainLayout } from './layouts/MainLayout';
import { MarketPage } from './pages/Market';
import { TradersPage } from './pages/Traders';

function App() {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#1890ff',
          borderRadius: 6,
        },
      }}
    >
      <Router>
        <MainLayout>
          <Routes>
            <Route path="/" element={<Navigate to="/market" replace />} />
            <Route path="/market" element={<MarketPage />} />
            <Route path="/traders" element={<TradersPage />} />
          </Routes>
        </MainLayout>
      </Router>
    </ConfigProvider>
  );
}

export default App;
