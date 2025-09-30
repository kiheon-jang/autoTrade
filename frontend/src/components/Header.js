import React, { useState, useEffect } from 'react';
import { Layout, Avatar, Dropdown, Badge, Button, Space, Typography } from 'antd';
import { BellOutlined, UserOutlined, LogoutOutlined, SettingOutlined } from '@ant-design/icons';
import styled from 'styled-components';
import { useWebSocket } from '../hooks/useWebSocket';

const { Header: AntHeader } = Layout;
const { Text } = Typography;

const HeaderContainer = styled(AntHeader)`
  background: rgba(255, 255, 255, 0.95) !important;
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.1);
  padding: 0 24px !important;
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const StatusIndicator = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
`;

const ConnectionStatus = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.875rem;
  font-weight: 500;
  background: ${props => props.$connected ? '#f6ffed' : '#fff2f0'};
  color: ${props => props.$connected ? '#52c41a' : '#ff4d4f'};
  border: 1px solid ${props => props.$connected ? '#b7eb8f' : '#ffccc7'};
`;

const StatusDot = styled.div`
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: ${props => props.$connected ? '#52c41a' : '#ff4d4f'};
  animation: ${props => props.$connected ? 'pulse 2s infinite' : 'none'};
  
  @keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.5; }
    100% { opacity: 1; }
  }
`;

const Header = () => {
  const [notifications, setNotifications] = useState(0);
  const { isConnected, lastMessage } = useWebSocket();

  useEffect(() => {
    // WebSocket 메시지가 오면 알림 카운트 증가
    if (lastMessage) {
      setNotifications(prev => prev + 1);
    }
  }, [lastMessage]);

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '프로필',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '설정',
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '로그아웃',
      danger: true,
    },
  ];

  const handleUserMenuClick = ({ key }) => {
    switch (key) {
      case 'logout':
        // 로그아웃 로직
        console.log('로그아웃');
        break;
      default:
        console.log(`메뉴 클릭: ${key}`);
    }
  };

  return (
    <HeaderContainer>
      <StatusIndicator>
        <ConnectionStatus $connected={isConnected}>
          <StatusDot $connected={isConnected} />
          {isConnected ? '실시간 연결됨' : '연결 끊김'}
        </ConnectionStatus>
        
        <Text type="secondary">
          {isConnected ? '데이터 수신 중...' : '연결 대기 중...'}
        </Text>
      </StatusIndicator>

      <Space size="middle">
        <Badge count={notifications} size="small">
          <Button 
            type="text" 
            icon={<BellOutlined />} 
            size="large"
            style={{ color: '#666' }}
          />
        </Badge>

        <Dropdown
          menu={{
            items: userMenuItems,
            onClick: handleUserMenuClick,
          }}
          placement="bottomRight"
          arrow
        >
          <Button type="text" style={{ padding: 0 }}>
            <Space>
              <Avatar icon={<UserOutlined />} />
              <Text strong>사용자</Text>
            </Space>
          </Button>
        </Dropdown>
      </Space>
    </HeaderContainer>
  );
};

export default Header;
