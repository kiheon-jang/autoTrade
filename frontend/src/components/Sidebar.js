import React from 'react';
import { Layout, Menu } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import styled from 'styled-components';
import {
  DashboardOutlined,
  BarChartOutlined,
  MonitorOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  FundOutlined,
  RobotOutlined
} from '@ant-design/icons';

const { Sider } = Layout;

const SidebarContainer = styled(Sider)`
  background: rgba(255, 255, 255, 0.95) !important;
  backdrop-filter: blur(10px);
  border-right: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 2px 0 20px rgba(0, 0, 0, 0.1);
  
  .ant-layout-sider-children {
    display: flex;
    flex-direction: column;
  }
`;

const Logo = styled.div`
  padding: 24px 16px;
  text-align: center;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  margin-bottom: 16px;
`;

const LogoIcon = styled.div`
  font-size: 2rem;
  color: #1890ff;
  margin-bottom: 8px;
`;

const LogoText = styled.div`
  font-size: 1.25rem;
  font-weight: 700;
  color: #262626;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
`;

const StyledMenu = styled(Menu)`
  border: none !important;
  background: transparent !important;
  
  .ant-menu-item {
    margin: 4px 8px !important;
    border-radius: 8px !important;
    height: 48px !important;
    line-height: 48px !important;
    
    &:hover {
      background: rgba(24, 144, 255, 0.1) !important;
    }
    
    &.ant-menu-item-selected {
      background: rgba(24, 144, 255, 0.15) !important;
      color: #1890ff !important;
      font-weight: 600 !important;
    }
  }
`;

const Sidebar = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: '대시보드',
    },
    {
      key: '/ai-recommendation',
      icon: <RobotOutlined />,
      label: 'AI 전략 추천',
    },
    // {
    //   key: '/strategies',
    //   icon: <FundOutlined />,
    //   label: '전략 관리',
    // },
    // {
    //   key: '/backtesting',
    //   icon: <BarChartOutlined />,
    //   label: '백테스팅',
    // },
    {
      key: '/monitoring',
      icon: <MonitorOutlined />,
      label: '실시간 모니터링',
    },
    // {
    //   key: '/settings',
    //   icon: <SettingOutlined />,
    //   label: '설정',
    // },
  ];

  const handleMenuClick = ({ key }) => {
    navigate(key);
  };

  return (
    <SidebarContainer width={240} theme="light">
      <Logo>
        <LogoIcon>
          <ThunderboltOutlined />
        </LogoIcon>
        <LogoText>AutoTrade</LogoText>
      </Logo>
      
      <StyledMenu
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={handleMenuClick}
      />
    </SidebarContainer>
  );
};

export default Sidebar;
