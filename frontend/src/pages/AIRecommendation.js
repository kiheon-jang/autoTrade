import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Table,
  Tag,
  Progress,
  Alert,
  Spin,
  Typography,
  Space,
  Statistic,
  Divider,
  Timeline,
  Badge,
  Tooltip
} from 'antd';
import {
  RobotOutlined,
  ThunderboltOutlined,
  LineChartOutlined,
  SafetyOutlined,
  ReloadOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import styled from 'styled-components';
import { useWebSocket } from '../hooks/useWebSocket';
import { apiService as api } from '../services/api';

const { Title, Text, Paragraph } = Typography;

const AIContainer = styled.div`
  padding: 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
`;

const AICard = styled(Card)`
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  margin-bottom: 24px;
`;

const StrategyCard = styled(Card)`
  background: ${props => props.selected ? 'linear-gradient(135deg, #52c41a 0%, #73d13d 100%)' : 'rgba(255, 255, 255, 0.9)'};
  border: ${props => props.selected ? '2px solid #52c41a' : '1px solid #d9d9d9'};
  border-radius: 12px;
  transition: all 0.3s ease;
  cursor: pointer;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
  }
`;

const StatusIndicator = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  background: ${props => {
    switch(props.status) {
      case 'active': return '#f6ffed';
      case 'recommended': return '#e6f7ff';
      case 'monitoring': return '#fff7e6';
      default: return '#f5f5f5';
    }
  }};
  color: ${props => {
    switch(props.status) {
      case 'active': return '#52c41a';
      case 'recommended': return '#1890ff';
      case 'monitoring': return '#fa8c16';
      default: return '#8c8c8c';
    }
  }};
  border: 1px solid ${props => {
    switch(props.status) {
      case 'active': return '#b7eb8f';
      case 'recommended': return '#91d5ff';
      case 'monitoring': return '#ffd591';
      default: return '#d9d9d9';
    }
  }};
`;

const AIRecommendation = () => {
  const [loading, setLoading] = useState(false);
  const [recommendations, setRecommendations] = useState([]);
  const [marketAnalysis, setMarketAnalysis] = useState({});
  const [selectedStrategy, setSelectedStrategy] = useState(null);
  const [activeStrategy, setActiveStrategy] = useState(null);
  const [autoTrading, setAutoTrading] = useState(false);
  const [analysisHistory, setAnalysisHistory] = useState([]);
  const { isConnected } = useWebSocket();

  // 시장 분석 및 추천 로딩
  const loadRecommendations = async () => {
    setLoading(true);
    try {
      const response = await api.analyzeMarketAndRecommend({
        symbols: ['BTC', 'ETH', 'XRP'],
        timeframe: '1h',
        analysis_depth: 'comprehensive'
      });
      
      if (response.success) {
        setRecommendations(response.recommendations || []);
        setMarketAnalysis(response.market_summary || {});
        setAnalysisHistory(prev => [{
          timestamp: new Date(),
          analysis: response.market_summary,
          recommendations: response.recommendations
        }, ...prev.slice(0, 9)]);
      }
    } catch (error) {
      console.error('추천 로딩 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  // 전략 선택
  const selectStrategy = async (strategy) => {
    try {
      const response = await api.selectStrategy({
        strategy_id: strategy.strategy_id,
        auto_switch: true,
        max_risk: 0.05
      });
      
      const data = response.data || response;
      if (data.success) {
        setSelectedStrategy(strategy);
        setActiveStrategy(data.strategy);
        setAutoTrading(true);
      }
    } catch (error) {
      console.error('전략 선택 실패:', error);
    }
  };

  // 오토트레이딩 중지
  const stopAutoTrading = async () => {
    try {
      const response = await api.stopAutoTrading();
      const data = response.data || response;
      if (data.success) {
        setAutoTrading(false);
        setActiveStrategy(null);
        setSelectedStrategy(null);
      }
    } catch (error) {
      console.error('오토트레이딩 중지 실패:', error);
    }
  };

  // 현재 활성 전략 조회
  const loadActiveStrategy = async () => {
    try {
      const response = await api.getTradingStatus();
      if (response.is_trading && response.trading) {
        setActiveStrategy({
          strategy_name: response.trading.strategy_name || 'AI 추천 전략',
          confidence_score: response.trading.confidence || 0.8,
          risk_level: response.trading.risk_level || 'medium'
        });
        setAutoTrading(true);
        console.log('활성 전략 로드됨:', response.trading.strategy_name);
      }
    } catch (error) {
      console.error('활성 전략 조회 실패:', error);
    }
  };

  useEffect(() => {
    loadRecommendations();
    loadActiveStrategy();
    
    // 30분마다 자동 분석
    const interval = setInterval(loadRecommendations, 30 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const getRiskColor = (risk) => {
    switch(risk) {
      case 'low': return 'green';
      case 'medium': return 'orange';
      case 'high': return 'red';
      default: return 'default';
    }
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return 'green';
    if (confidence >= 0.6) return 'orange';
    return 'red';
  };

  const recommendationColumns = [
    {
      title: '전략명',
      dataIndex: 'strategy_name',
      key: 'strategy_name',
      render: (text, record) => (
        <Space>
          <RobotOutlined style={{ color: '#1890ff' }} />
          <Text strong>{text}</Text>
          {record.strategy_id === selectedStrategy?.strategy_id && (
            <Badge status="processing" text="선택됨" />
          )}
        </Space>
      )
    },
    {
      title: '신뢰도',
      dataIndex: 'confidence_score',
      key: 'confidence_score',
      render: (score) => (
        <Progress
          percent={Math.round(score * 100)}
          size="small"
          status={score >= 0.8 ? 'success' : score >= 0.6 ? 'normal' : 'exception'}
          format={(percent) => `${percent}%`}
        />
      )
    },
    {
      title: '예상수익률',
      dataIndex: 'expected_return',
      key: 'expected_return',
      render: (return_rate) => (
        <Text style={{ color: return_rate > 0 ? '#52c41a' : '#ff4d4f' }}>
          {(return_rate * 100).toFixed(1)}%
        </Text>
      )
    },
    {
      title: '리스크',
      dataIndex: 'risk_level',
      key: 'risk_level',
      render: (risk) => (
        <Tag color={getRiskColor(risk)}>
          {risk === 'low' ? '낮음' : risk === 'medium' ? '보통' : '높음'}
        </Tag>
      )
    },
    {
      title: '유효기간',
      dataIndex: 'validity_period',
      key: 'validity_period',
      render: (period) => `${period}분`
    },
    {
      title: '액션',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button
            type="primary"
            size="small"
            icon={<PlayCircleOutlined />}
            onClick={() => selectStrategy(record)}
            disabled={record.strategy_id === selectedStrategy?.strategy_id}
          >
            선택
          </Button>
          <Tooltip title={record.recommendation_reason}>
            <Button size="small" icon={<InfoCircleOutlined />}>
              상세
            </Button>
          </Tooltip>
        </Space>
      )
    }
  ];

  return (
    <AIContainer>
      <Row gutter={[24, 24]}>
        {/* 헤더 */}
        <Col span={24}>
          <AICard>
            <Row align="middle" justify="space-between">
              <Col>
                <Space>
                  <RobotOutlined style={{ fontSize: '24px', color: '#1890ff' }} />
                  <div>
                    <Title level={2} style={{ margin: 0 }}>
                      AI 전략 추천 시스템
                    </Title>
                    <Text type="secondary">
                      실시간 시황 분석을 통한 최적 전략 추천
                    </Text>
                  </div>
                </Space>
              </Col>
              <Col>
                <Space>
                  <Button
                    type="primary"
                    icon={<ReloadOutlined />}
                    loading={loading}
                    onClick={loadRecommendations}
                  >
                    분석 새로고침
                  </Button>
                  {autoTrading && (
                    <Button
                      danger
                      icon={<PauseCircleOutlined />}
                      onClick={stopAutoTrading}
                    >
                      오토트레이딩 중지
                    </Button>
                  )}
                </Space>
              </Col>
            </Row>
          </AICard>
        </Col>

        {/* 연결 상태 */}
        <Col span={24}>
          <Alert
            message={
              <Space>
                <StatusIndicator status={isConnected ? 'active' : 'inactive'}>
                  {isConnected ? '실시간 연결됨' : '연결 끊김'}
                </StatusIndicator>
                {autoTrading && (
                  <StatusIndicator status="monitoring">
                    <ThunderboltOutlined />
                    오토트레이딩 활성
                  </StatusIndicator>
                )}
              </Space>
            }
            type={isConnected ? 'success' : 'warning'}
            showIcon
          />
        </Col>

        {/* 시장 분석 요약 */}
        <Col span={24}>
          <AICard title="시장 분석 요약">
            <Row gutter={[16, 16]}>
              <Col span={6}>
                <Statistic
                  title="전체 트렌드"
                  value={marketAnalysis.overall_trend || 'neutral'}
                  prefix={<LineChartOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="변동성 수준"
                  value={marketAnalysis.volatility_level || 'medium'}
                  prefix={<SafetyOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="시장 심리"
                  value={marketAnalysis.market_sentiment || 'neutral'}
                  prefix={<RobotOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="리스크 평가"
                  value={marketAnalysis.risk_assessment || 'medium'}
                  prefix={<WarningOutlined />}
                />
              </Col>
            </Row>
          </AICard>
        </Col>

        {/* AI 추천 전략 */}
        <Col span={24}>
          <AICard title="AI 추천 전략">
            {loading ? (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <Spin size="large" />
                <div style={{ marginTop: '16px' }}>
                  <Text>AI가 시장을 분석하고 있습니다...</Text>
                </div>
              </div>
            ) : (
              <Table
                columns={recommendationColumns}
                dataSource={recommendations}
                rowKey="strategy_id"
                pagination={false}
                size="middle"
              />
            )}
          </AICard>
        </Col>

        {/* 활성 전략 */}
        {activeStrategy && (
          <Col span={24}>
            <AICard title="현재 활성 전략">
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div>
                      <Text strong>전략명: </Text>
                      <Text>{activeStrategy.recommendation?.strategy_name}</Text>
                    </div>
                    <div>
                      <Text strong>전략 타입: </Text>
                      <Tag color="blue">{activeStrategy.recommendation?.strategy_type}</Tag>
                    </div>
                    <div>
                      <Text strong>신뢰도: </Text>
                      <Progress
                        percent={Math.round((activeStrategy.recommendation?.confidence_score || 0) * 100)}
                        size="small"
                        status="active"
                      />
                    </div>
                  </Space>
                </Col>
                <Col span={12}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div>
                      <Text strong>시작 시간: </Text>
                      <Text>{new Date(activeStrategy.started_at).toLocaleString()}</Text>
                    </div>
                    <div>
                      <Text strong>자동 변경: </Text>
                      <Tag color={activeStrategy.auto_switch ? 'green' : 'default'}>
                        {activeStrategy.auto_switch ? '활성' : '비활성'}
                      </Tag>
                    </div>
                    <div>
                      <Text strong>상태: </Text>
                      <Tag color="processing">실행 중</Tag>
                    </div>
                  </Space>
                </Col>
              </Row>
            </AICard>
          </Col>
        )}

        {/* 분석 히스토리 */}
        <Col span={24}>
          <AICard title="분석 히스토리">
            <Timeline
              items={analysisHistory.slice(0, 5).map((item, index) => ({
                key: index,
                dot: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
                children: (
                  <div>
                    <Text strong>{item.timestamp.toLocaleString()}</Text>
                    <div style={{ marginTop: '8px' }}>
                      <Space>
                        <Tag color="blue">트렌드: {item.analysis.overall_trend}</Tag>
                        <Tag color="orange">변동성: {item.analysis.volatility_level}</Tag>
                        <Tag color="green">추천: {item.recommendations?.length || 0}개</Tag>
                      </Space>
                    </div>
                  </div>
                ),
              }))}
            />
          </AICard>
        </Col>
      </Row>
    </AIContainer>
  );
};

export default AIRecommendation;
