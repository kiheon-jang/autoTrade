import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Progress, Table, Tag, Space, Typography, Badge, Button } from 'antd';
import { 
  RiseOutlined, 
  DollarOutlined, 
  ThunderboltOutlined,
  BarChartOutlined 
} from '@ant-design/icons';
import styled from 'styled-components';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { monitoringAPI } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';

const { Title, Text } = Typography;

const DashboardContainer = styled.div`
  .metric-card {
    text-align: center;
    padding: 24px;
    border-radius: 12px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
  }
  
  .metric-value {
    font-size: 2.5rem;
    font-weight: 700;
    margin-bottom: 8px;
  }
  
  .metric-label {
    font-size: 1rem;
    opacity: 0.9;
  }
`;

const Dashboard = () => {
  const [dashboardData, setDashboardData] = useState({
    portfolio: {
      totalValue: 0,
      totalReturn: 0,
      totalReturnRate: 0,
      todayReturn: 0,
      todayReturnRate: 0,
    },
    strategies: [],
    recentTrades: [],
    performance: [],
    alerts: [],
  });
  const [loading, setLoading] = useState(true);
  const [tradingStatus, setTradingStatus] = useState(null);
  const { isConnected } = useWebSocket();

  useEffect(() => {
    fetchDashboardData();
    fetchTradingStatus();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [dashboardRes, portfolioRes, alertsRes] = await Promise.all([
        monitoringAPI.getDashboard(),
        monitoringAPI.getPortfolio(),
        monitoringAPI.getAlerts(),
      ]);

      setDashboardData({
        ...dashboardRes,
        portfolio: portfolioRes,
        alerts: alertsRes.alerts || [],
      });
    } catch (error) {
      console.error('대시보드 데이터 로딩 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTradingStatus = async () => {
    try {
      const { aiRecommendationAPI } = require('../services/api');
      const response = await aiRecommendationAPI.getTradingStatus();
      if (response.is_trading) {
        setTradingStatus(response);
      }
    } catch (error) {
      // 거래 중이 아닐 수 있음
    }
  };

  const recentTradesColumns = [
    {
      title: '시간',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (time) => new Date(time).toLocaleString(),
    },
    {
      title: '전략',
      dataIndex: 'strategy',
      key: 'strategy',
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
      dataIndex: 'returnRate',
      key: 'returnRate',
      render: (rate) => (
        <Text type={rate >= 0 ? 'success' : 'danger'}>
          {rate >= 0 ? '+' : ''}{rate.toFixed(2)}%
        </Text>
      ),
    },
  ];

  const strategyColumns = [
    {
      title: '전략명',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '타입',
      dataIndex: 'strategy_type',
      key: 'strategy_type',
      render: (type) => {
        const typeMap = {
          scalping: { color: 'blue', text: '스캘핑' },
          day_trading: { color: 'green', text: '데이트레이딩' },
          swing_trading: { color: 'orange', text: '스윙트레이딩' },
          long_term: { color: 'purple', text: '장기투자' },
        };
        const config = typeMap[type] || { color: 'default', text: type };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '상태',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active) => (
        <Tag color={active ? 'green' : 'default'}>
          {active ? '실행중' : '중지됨'}
        </Tag>
      ),
    },
    {
      title: '수익률',
      dataIndex: 'returnRate',
      key: 'returnRate',
      render: (rate) => (
        <Text type={rate >= 0 ? 'success' : 'danger'}>
          {rate >= 0 ? '+' : ''}{rate.toFixed(2)}%
        </Text>
      ),
    },
  ];

  return (
    <DashboardContainer>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={2}>📊 대시보드</Title>
          <Text type="secondary">전체 시스템 현황 및 성과 개요</Text>
        </Col>
        {tradingStatus && tradingStatus.is_trading && (
          <Col>
            <Card size="small" style={{ background: '#f6ffed', border: '1px solid #b7eb8f' }}>
              <Space>
                <Badge status="processing" />
                <Text strong style={{ color: '#52c41a' }}>
                  {tradingStatus.strategy.name} 실행 중
                </Text>
                <Button type="link" href="/monitoring" size="small">
                  모니터링 →
                </Button>
              </Space>
            </Card>
          </Col>
        )}
      </Row>
      
      {/* 주요 지표 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <div className="metric-card">
            <RiseOutlined style={{ fontSize: 32, marginBottom: 12 }} />
            <div className="metric-value">
              {dashboardData.portfolio.totalValue?.toLocaleString() || '0'}
            </div>
            <div className="metric-label">포트폴리오 가치</div>
          </div>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <div className="metric-card">
            <DollarOutlined style={{ fontSize: 32, marginBottom: 12 }} />
            <div className="metric-value">
              {dashboardData.portfolio.totalReturnRate?.toFixed(2) || '0'}%
            </div>
            <div className="metric-label">총 수익률</div>
          </div>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <div className="metric-card">
            <ThunderboltOutlined style={{ fontSize: 32, marginBottom: 12 }} />
            <div className="metric-value">
              {dashboardData.strategies?.filter(s => s.is_active).length || 0}
            </div>
            <div className="metric-label">활성 전략</div>
          </div>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <div className="metric-card">
            <BarChartOutlined style={{ fontSize: 32, marginBottom: 12 }} />
            <div className="metric-value">
              {dashboardData.portfolio.todayReturnRate?.toFixed(2) || '0'}%
            </div>
            <div className="metric-label">오늘 수익률</div>
          </div>
        </Col>
      </Row>

      {/* 차트와 테이블 */}
      <Row gutter={[24, 24]}>
        <Col xs={24} lg={16}>
          <Card title="포트폴리오 성과" extra={<BarChartOutlined />}>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={dashboardData.performance || []}>
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
            <Table
              dataSource={dashboardData.strategies || []}
              columns={strategyColumns}
              pagination={false}
              size="small"
              rowKey="id"
            />
          </Card>
        </Col>
      </Row>

      {/* 최근 거래 내역 */}
      <Row style={{ marginTop: 24 }}>
        <Col span={24}>
          <Card title="최근 거래 내역">
            <Table
              dataSource={dashboardData.recentTrades || []}
              columns={recentTradesColumns}
              pagination={{ pageSize: 5 }}
              size="small"
              rowKey="id"
            />
          </Card>
        </Col>
      </Row>
    </DashboardContainer>
  );
};

export default Dashboard;
