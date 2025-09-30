import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Layout } from 'antd';
import styled from 'styled-components';

// 컴포넌트 임포트
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';
import AIRecommendation from './pages/AIRecommendation';
// import Strategies from './pages/Strategies';
// import Backtesting from './pages/Backtesting';
import Monitoring from './pages/Monitoring';
// import Settings from './pages/Settings';

const { Content } = Layout;

const AppContainer = styled.div`
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
`;

const MainLayout = styled(Layout)`
  min-height: 100vh;
  background: transparent;
`;

const MainContent = styled(Content)`
  margin: 24px;
  padding: 24px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  min-height: calc(100vh - 48px);
  overflow: auto;
`;

function App() {
  return (
    <AppContainer>
      <MainLayout>
        <Sidebar />
        <Layout>
          <Header />
          <MainContent>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/ai-recommendation" element={<AIRecommendation />} />
              {/* <Route path="/strategies" element={<Strategies />} /> */}
              {/* <Route path="/backtesting" element={<Backtesting />} /> */}
              <Route path="/monitoring" element={<Monitoring />} />
              {/* <Route path="/settings" element={<Settings />} /> */}
            </Routes>
          </MainContent>
        </Layout>
      </MainLayout>
    </AppContainer>
  );
}

export default App;
