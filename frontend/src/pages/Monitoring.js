import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Row, 
  Col, 
  Table, 
  Tag, 
  Typography, 
  Statistic,
  Progress,
  Space,
  Button,
  Tabs,
  List,
  Avatar,
  Badge
} from 'antd';
import { 
  MonitorOutlined, 
  ThunderboltOutlined,
  DollarOutlined,
  LineChartOutlined,
  AlertOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import styled from 'styled-components';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { monitoringAPI } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';

const { Title, Text } = Typography;

const MonitoringContainer = styled.div`
  .status-card {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 24px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }
  
  .metric-card {
    text-align: center;
    padding: 20px;
    border-radius: 12px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
  }
  
  .metric-value {
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 8px;
  }
  
  .metric-label {
    font-size: 0.875rem;
    opacity: 0.9;
  }
  
  .alert-item {
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 8px;
    border-left: 4px solid;
  }
  
  .alert-info {
    background: #e6f7ff;
    border-left-color: #1890ff;
  }
  
  .alert-warning {
    background: #fff7e6;
    border-left-color: #fa8c16;
  }
  
  .alert-error {
    background: #fff2f0;
    border-left-color: #ff4d4f;
  }
`;

const Monitoring = () => {
  const [dashboardData, setDashboardData] = useState({
    portfolio: {
      totalValue: 0,
      totalReturn: 0,
      todayReturn: 0,
    },
    strategies: [],
    trades: [],
    alerts: [],
    performance: [],
  });
  const [loading, setLoading] = useState(true);
  const { isConnected, lastMessage } = useWebSocket();

  useEffect(() => {
    fetchMonitoringData();
    const interval = setInterval(fetchMonitoringData, 5000); // 5초마다 업데이트
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (lastMessage) {
      updateRealtimeData(lastMessage);
    }
  }, [lastMessage]);

  const fetchMonitoringData = async () => {
    try {
      const [dashboardRes, portfolioRes, tradesRes, alertsRes] = await Promise.all([
        monitoringAPI.getDashboard(),
        monitoringAPI.getPortfolio(),
        monitoringAPI.getTrades({ limit: 20 }),
        monitoringAPI.getAlerts(),
      ]);

      setDashboardData({
        ...dashboardData,
        ...dashboardRes.data,
        portfolio: portfolioRes.data,
        trades: tradesRes.data.trades || [],
        alerts: alertsRes.data.alerts || [],
      });
    } catch (error) {
      console.error('모니터링 데이터 로딩 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateRealtimeData = (data) => {
    setDashboardData(prev => ({
      ...prev,
      portfolio: {
        ...prev.portfolio,
        ...data.portfolio,
      },
      trades: [data.trade, ...prev.trades].slice(0, 20), // 최신 20개만 유지
    }));
  };

  const tradesColumns = [
    {
      title: '시간',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (time) => new Date(time).toLocaleString(),
    },
    {
      title: '전략',
      dataIndex: 'strategy_name',
      key: 'strategy_name',
    },
    {
      title: '심볼',
      dataIndex: 'symbol',
      key: 'symbol',
    },
    {
      title: '타입',
      dataIndex: 'side',
      key: 'side',
      render: (side) => (
        <Tag color={side === 'buy' ? 'green' : 'red'}>
          {side === 'buy' ? '매수' : '매도'}
        </Tag>
      ),
    },
    {
      title: '가격',
      dataIndex: 'price',
      key: 'price',
      render: (price) => `₩${price.toLocaleString()}`,
    },
    {
      title: '수량',
      dataIndex: 'quantity',
      key: 'quantity',
    },
    {
      title: '수익률',
      dataIndex: 'return_rate',
      key: 'return_rate',
      render: (rate) => (
        <Text type={rate >= 0 ? 'success' : 'danger'}>
          {rate >= 0 ? '+' : ''}{rate.toFixed(2)}%
        </Text>
      ),
    },
  ];

  const getAlertType = (type) => {
    const typeMap = {
      info: { color: 'blue', className: 'alert-info' },
      warning: { color: 'orange', className: 'alert-warning' },
      error: { color: 'red', className: 'alert-error' },
    };
    return typeMap[type] || { color: 'default', className: 'alert-info' };
  };

  return (
    <MonitoringContainer>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2}>실시간 모니터링</Title>
        <Space>
          <Badge 
            status={isConnected ? 'success' : 'error'} 
            text={isConnected ? '실시간 연결됨' : '연결 끊김'} 
          />
          <Button 
            icon={<ReloadOutlined />} 
            onClick={fetchMonitoringData}
            loading={loading}
          >
            새로고침
          </Button>
        </Space>
      </div>

      {/* 주요 지표 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <div className="metric-card">
            <div className="metric-value">
              ₩{dashboardData.portfolio.totalValue.toLocaleString()}
            </div>
            <div className="metric-label">총 자산</div>
          </div>
        </Col>
        <Col xs={24} sm={8}>
          <div className="metric-card">
            <div className="metric-value">
              {dashboardData.portfolio.totalReturn >= 0 ? '+' : ''}
              {dashboardData.portfolio.totalReturn.toFixed(2)}%
            </div>
            <div className="metric-label">총 수익률</div>
          </div>
        </Col>
        <Col xs={24} sm={8}>
          <div className="metric-card">
            <div className="metric-value">
              {dashboardData.portfolio.todayReturn >= 0 ? '+' : ''}
              {dashboardData.portfolio.todayReturn.toFixed(2)}%
            </div>
            <div className="metric-label">오늘 수익률</div>
          </div>
        </Col>
      </Row>

      <Tabs 
        defaultActiveKey="overview"
        items={[
          {
            key: 'overview',
            label: '개요',
            children: (
              <Row gutter={[16, 16]}>
                <Col xs={24} lg={16}>
                  <Card title="포트폴리오 성과" extra={<LineChartOutlined />}>
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={dashboardData.performance}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" />
                        <YAxis />
                        <Tooltip />
                        <Line 
                          type="monotone" 
                          dataKey="value" 
                          stroke="#1890ff" 
                          strokeWidth={2}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </Card>
                </Col>
                
                <Col xs={24} lg={8}>
                  <Card title="전략 현황">
                    <List
                      dataSource={dashboardData.strategies}
                      renderItem={(strategy) => (
                        <List.Item>
                          <List.Item.Meta
                            avatar={
                              <Avatar 
                                style={{ 
                                  backgroundColor: strategy.is_active ? '#52c41a' : '#d9d9d9' 
                                }}
                                icon={<ThunderboltOutlined />}
                              />
                            }
                            title={strategy.name}
                            description={
                              <Space>
                                <Tag color={strategy.is_active ? 'green' : 'default'}>
                                  {strategy.is_active ? '실행중' : '중지됨'}
                                </Tag>
                                <Text type="secondary">
                                  {strategy.strategy_type}
                                </Text>
                              </Space>
                            }
                          />
                        </List.Item>
                      )}
                    />
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'trades',
            label: '거래 내역',
            children: (
              <Card title="최근 거래 내역">
                <Table
                  dataSource={dashboardData.trades}
                  columns={tradesColumns}
                  rowKey="id"
                  pagination={{ pageSize: 10 }}
                  size="small"
                />
              </Card>
            ),
          },
          {
            key: 'alerts',
            label: '알림',
            children: (
              <Card title="시스템 알림">
                <List
                  dataSource={dashboardData.alerts}
                  renderItem={(alert) => {
                    const alertConfig = getAlertType(alert.type);
                    return (
                      <List.Item>
                        <div className={`alert-item ${alertConfig.className}`}>
                          <Space>
                            <AlertOutlined style={{ color: alertConfig.color }} />
                            <Text strong>{alert.title}</Text>
                            <Text type="secondary">
                              {new Date(alert.timestamp).toLocaleString()}
                            </Text>
                          </Space>
                          <div style={{ marginTop: 8 }}>
                            <Text>{alert.message}</Text>
                          </div>
                        </div>
                      </List.Item>
                    );
                  }}
                />
              </Card>
            ),
          },
          {
            key: 'performance',
            label: '성과 분석',
            children: (
              <Row gutter={[16, 16]}>
                <Col xs={24} sm={12}>
                  <Card title="일별 수익률">
                    <ResponsiveContainer width="100%" height={200}>
                      <LineChart data={dashboardData.performance}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" />
                        <YAxis />
                        <Tooltip />
                        <Line 
                          type="monotone" 
                          dataKey="return" 
                          stroke="#52c41a" 
                          strokeWidth={2}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </Card>
                </Col>
                
                <Col xs={24} sm={12}>
                  <Card title="리스크 지표">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <div>
                        <Text>샤프 비율</Text>
                        <Progress 
                          percent={75} 
                          strokeColor="#52c41a"
                          style={{ marginTop: 8 }}
                        />
                      </div>
                      <div>
                        <Text>최대 낙폭</Text>
                        <Progress 
                          percent={25} 
                          strokeColor="#ff4d4f"
                          style={{ marginTop: 8 }}
                        />
                      </div>
                      <div>
                        <Text>승률</Text>
                        <Progress 
                          percent={68} 
                          strokeColor="#1890ff"
                          style={{ marginTop: 8 }}
                        />
                      </div>
                    </Space>
                  </Card>
                </Col>
              </Row>
            ),
          },
        ]}
      />
    </MonitoringContainer>
  );
};

export default Monitoring;
