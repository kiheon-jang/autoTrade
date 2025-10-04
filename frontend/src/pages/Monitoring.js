import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Row, 
  Col, 
  Tag, 
  Typography, 
  Space,
  Button,
  Badge,
  Empty
} from 'antd';
import { 
  RiseOutlined,
  FallOutlined,
  SearchOutlined,
  FireOutlined,
  CrownOutlined,
  TrophyOutlined
} from '@ant-design/icons';
import styled from 'styled-components';
import api from '../services/api';

// API 기본 URL 가져오기
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8008';

const { Title, Text } = Typography;

const MonitoringContainer = styled.div.withConfig({
  shouldForwardProp: (prop) => prop !== 'status',
})`
  .status-badge {
    margin-right: 12px;
  }
  
  .trading-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 24px;
  }
  
  .position-card {
    border-left: 4px solid #52c41a;
    padding: 16px;
    margin-bottom: 12px;
    background: #f6ffed;
    border-radius: 8px;
  }
  
  .pnl-positive {
    color: #52c41a;
    font-weight: 600;
  }
  
  .pnl-negative {
    color: #ff4d4f;
    font-weight: 600;
  }
  
  .trade-row {
    padding: 12px;
    border-bottom: 1px solid #f0f0f0;
    
    &:hover {
      background: #fafafa;
    }
  }
`;

const Monitoring = () => {
  const [tradingStatus, setTradingStatus] = useState(null);
  const [aiStrategyDetails, setAiStrategyDetails] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([
        fetchTradingStatus(),
        fetchAiStrategyDetails()
      ]);
      setLoading(false);
    };

    loadData();

    // 5초마다 상태 업데이트
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchTradingStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/trading/status`);
      const data = await response.json();
      setTradingStatus(data);
    } catch (error) {
      console.error('거래 상태 조회 실패:', error);
    }
  };

  const fetchAiStrategyDetails = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/monitoring/ai-strategy-details`);
      const data = await response.json();
      setAiStrategyDetails(data);
    } catch (error) {
      console.error('AI 전략 상세 정보 조회 실패:', error);
    }
  };


  // AI 추천 전략이 실행 중인 경우 상세 모니터링 화면 표시
  if (aiStrategyDetails && aiStrategyDetails.is_trading) {
    const { strategy, trading } = aiStrategyDetails;
    const pnlPercentage = trading.pnl_percentage || 0;
    const isProfitable = trading.total_return >= 0;

    return (
      <MonitoringContainer>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* 거래 상태 헤더 (AI Strategy) */}
          <Card className="trading-card">
            <Row gutter={24} align="middle">
              <Col flex="auto">
                <Space size="large">
                  <Badge status="processing" text={
                    <Text style={{ color: 'white', fontSize: '16px' }}>
                      <PlayCircleOutlined /> AI 전략 실행 중
                    </Text>
                  } />
                  <div>
                    <Text style={{ color: 'rgba(255,255,255,0.8)' }}>실행 전략</Text>
                    <br />
                    <Title level={4} style={{ color: 'white', margin: 0 }}>
                      {strategy?.name || 'AI 추천 전략'}
                    </Title>
                    <div style={{ marginTop: 4 }}>
                      <Tag color={trading.mode === 'paper' ? 'blue' : 'green'} style={{ color: 'white' }}>
                        {trading.mode === 'paper' ? '📝 페이퍼 트레이딩' : '💰 실거래'}
                      </Tag>
                    </div>
                  </div>
                </Space>
              </Col>
              <Col>
                <Button 
                  danger 
                  icon={<StopOutlined />} 
                  size="large"
                  onClick={() => {
                    handleStopTrading();
                    console.log('AI 전략 중지');
                  }}
                >
                  전략 중지
                </Button>
              </Col>
            </Row>
          </Card>




          {/* 실시간 분석 현황 (AI Strategy) */}
          <Card 
            title={
              <Space>
                <SearchOutlined spin />
                <span>실시간 시장 분석</span>
                <Badge count={tradingStatus?.analysis?.scanning_coins || 99} style={{ backgroundColor: '#52c41a' }} />
              </Space>
            }
          >
            <Row gutter={[16, 16]}>
              <Col xs={24} md={8}>
                <Card size="small" style={{ background: '#fff7e6', borderLeft: '4px solid #fa8c16' }}>
                  <Space direction="vertical">
                    <Space>
                      <FireOutlined style={{ color: '#fa8c16', fontSize: 20 }} />
                      <Text strong>Tier 1: 거래량 급등</Text>
                    </Space>
                    <Title level={4} style={{ margin: 0 }}>
                      {tradingStatus?.analysis?.tiers?.tier1?.count || 0}개
                    </Title>
                    <Text type="secondary">1초마다 스캔</Text>
                    <div style={{ marginTop: 8 }}>
                      {tradingStatus?.analysis?.tiers?.tier1?.coins?.slice(0, 5).map(coin => (
                        <Tag key={coin} color="orange">{coin}</Tag>
                      ))}
                      {tradingStatus?.analysis?.tiers?.tier1?.coins?.length > 5 && <Text type="secondary">...</Text>}
                    </div>
                  </Space>
                </Card>
              </Col>
              
              <Col xs={24} md={8}>
                <Card size="small" style={{ background: '#f6ffed', borderLeft: '4px solid #52c41a' }}>
                  <Space direction="vertical">
                    <Space>
                      <CrownOutlined style={{ color: '#52c41a', fontSize: 20 }} />
                      <Text strong>Tier 2: 핵심 코인</Text>
                    </Space>
                    <Title level={4} style={{ margin: 0 }}>
                      {tradingStatus?.analysis?.tiers?.tier2?.count || 0}개
                    </Title>
                    <Text type="secondary">5초마다 스캔</Text>
                    <div style={{ marginTop: 8 }}>
                      {tradingStatus?.analysis?.tiers?.tier2?.coins?.slice(0, 5).map(coin => (
                        <Tag key={coin} color="green">{coin}</Tag>
                      ))}
                      {tradingStatus?.analysis?.tiers?.tier2?.coins?.length > 5 && <Text type="secondary">...</Text>}
                    </div>
                  </Space>
                </Card>
              </Col>
              
              <Col xs={24} md={8}>
                <Card size="small" style={{ background: '#e6f7ff', borderLeft: '4px solid #1890ff' }}>
                  <Space direction="vertical">
                    <Space>
                      <TrophyOutlined style={{ color: '#1890ff', fontSize: 20 }} />
                      <Text strong>Tier 3: 시가총액 상위</Text>
                    </Space>
                    <Title level={4} style={{ margin: 0 }}>
                      {tradingStatus?.analysis?.tiers?.tier3?.count || 0}개
                    </Title>
                    <Text type="secondary">30초마다 스캔</Text>
                    <div style={{ marginTop: 8 }}>
                      {tradingStatus?.analysis?.tiers?.tier3?.coins?.slice(0, 5).map(coin => (
                        <Tag key={coin} color="blue">{coin}</Tag>
                      ))}
                      {tradingStatus?.analysis?.tiers?.tier3?.coins?.length > 5 && <Text type="secondary">...</Text>}
                    </div>
                  </Space>
                </Card>
              </Col>
            </Row>
          </Card>

          {/* 실시간 분석 진행 상황 */}
          <Card 
            title={
              <Space>
                <SearchOutlined spin />
                <span>실시간 분석 진행 상황</span>
                <Badge count={tradingStatus?.analysis?.scanning_coins || 0} style={{ backgroundColor: '#1890ff' }} />
              </Space>
            }
          >
            <Row gutter={[16, 16]}>
              <Col xs={24} md={8}>
                <Card size="small" style={{ background: '#fff7e6', borderLeft: '4px solid #fa8c16' }}>
                  <Space direction="vertical">
                    <Space>
                      <FireOutlined style={{ color: '#fa8c16', fontSize: 20 }} />
                      <Text strong>Tier 1 분석 중</Text>
                    </Space>
                    <Title level={4} style={{ margin: 0 }}>
                      {tradingStatus?.analysis?.tiers?.tier1?.count || 0}개 코인
                    </Title>
                    <Text type="secondary">거래량 급등 감지 (1초마다)</Text>
                    <div style={{ marginTop: 8 }}>
                      {tradingStatus?.analysis?.tiers?.tier1?.coins?.slice(0, 5).map(coin => (
                        <Tag key={coin} color="orange">{coin}</Tag>
                      ))}
                      {tradingStatus?.analysis?.tiers?.tier1?.coins?.length > 5 && <Text type="secondary">...</Text>}
                    </div>
                    <div style={{ marginTop: 8 }}>
                      <Text type="secondary">분석 중: 거래량 급등 패턴, 가격 변동성, 매수/매도 압력</Text>
                    </div>
                  </Space>
                </Card>
              </Col>
              
              <Col xs={24} md={8}>
                <Card size="small" style={{ background: '#f6ffed', borderLeft: '4px solid #52c41a' }}>
                  <Space direction="vertical">
                    <Space>
                      <CrownOutlined style={{ color: '#52c41a', fontSize: 20 }} />
                      <Text strong>Tier 2 분석 중</Text>
                    </Space>
                    <Title level={4} style={{ margin: 0 }}>
                      {tradingStatus?.analysis?.tiers?.tier2?.count || 0}개 코인
                    </Title>
                    <Text type="secondary">핵심 코인 모니터링 (5초마다)</Text>
                    <div style={{ marginTop: 8 }}>
                      {tradingStatus?.analysis?.tiers?.tier2?.coins?.slice(0, 5).map(coin => (
                        <Tag key={coin} color="green">{coin}</Tag>
                      ))}
                      {tradingStatus?.analysis?.tiers?.tier2?.coins?.length > 5 && <Text type="secondary">...</Text>}
                    </div>
                    <div style={{ marginTop: 8 }}>
                      <Text type="secondary">분석 중: 기술적 지표, 추세 분석, 지지/저항선</Text>
                    </div>
                  </Space>
                </Card>
              </Col>
              
              <Col xs={24} md={8}>
                <Card size="small" style={{ background: '#e6f7ff', borderLeft: '4px solid #1890ff' }}>
                  <Space direction="vertical">
                    <Space>
                      <TrophyOutlined style={{ color: '#1890ff', fontSize: 20 }} />
                      <Text strong>Tier 3 분석 중</Text>
                    </Space>
                    <Title level={4} style={{ margin: 0 }}>
                      {tradingStatus?.analysis?.tiers?.tier3?.count || 0}개 코인
                    </Title>
                    <Text type="secondary">시가총액 상위 스캔 (30초마다)</Text>
                    <div style={{ marginTop: 8 }}>
                      {tradingStatus?.analysis?.tiers?.tier3?.coins?.slice(0, 5).map(coin => (
                        <Tag key={coin} color="blue">{coin}</Tag>
                      ))}
                      {tradingStatus?.analysis?.tiers?.tier3?.coins?.length > 5 && <Text type="secondary">...</Text>}
                    </div>
                    <div style={{ marginTop: 8 }}>
                      <Text type="secondary">분석 중: 시장 전체 동향, 상관관계, 리스크 평가</Text>
                    </div>
                  </Space>
                </Card>
              </Col>
            </Row>
          </Card>

          {/* 매수/매도 신호 현황 */}
          <Card 
            title={
              <Space>
                <SearchOutlined spin />
                <span>실시간 거래 신호</span>
                <Badge count={(tradingStatus?.analysis?.top_opportunities?.filter(o => o.signal === 'BUY').length || 0) + (tradingStatus?.analysis?.top_opportunities?.filter(o => o.signal === 'SELL').length || 0)} style={{ backgroundColor: '#52c41a' }} />
              </Space>
            }
          >
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={12}>
                <Card size="small" style={{ background: '#f6ffed', borderLeft: '4px solid #52c41a' }}>
                  <Space direction="vertical">
                    <Space>
                      <RiseOutlined style={{ color: '#52c41a', fontSize: 20 }} />
                      <Text strong>매수 신호</Text>
                    </Space>
                    <Title level={4} style={{ margin: 0 }}>
                      {tradingStatus?.analysis?.top_opportunities?.filter(o => o.signal === 'BUY').length || 0}개
                    </Title>
                    <Text type="secondary">BUY 신호 감지</Text>
                    <div style={{ marginTop: 8 }}>
                      {tradingStatus?.analysis?.top_opportunities?.filter(o => o.signal === 'BUY').slice(0, 5).map(opp => (
                        <Tag key={opp.symbol} color="green">{opp.symbol}</Tag>
                      ))}
                      {tradingStatus?.analysis?.top_opportunities?.filter(o => o.signal === 'BUY').length > 5 && <Text type="secondary">...</Text>}
                    </div>
                  </Space>
                </Card>
              </Col>
              
              <Col xs={24} sm={12}>
                <Card size="small" style={{ background: '#fff2f0', borderLeft: '4px solid #ff4d4f' }}>
                  <Space direction="vertical">
                    <Space>
                      <FallOutlined style={{ color: '#ff4d4f', fontSize: 20 }} />
                      <Text strong>매도 신호</Text>
                    </Space>
                    <Title level={4} style={{ margin: 0 }}>
                      {tradingStatus?.analysis?.top_opportunities?.filter(o => o.signal === 'SELL').length || 0}개
                    </Title>
                    <Text type="secondary">SELL 신호 감지</Text>
                    <div style={{ marginTop: 8 }}>
                      {tradingStatus?.analysis?.top_opportunities?.filter(o => o.signal === 'SELL').slice(0, 5).map(opp => (
                        <Tag key={opp.symbol} color="red">{opp.symbol}</Tag>
                      ))}
                      {tradingStatus?.analysis?.top_opportunities?.filter(o => o.signal === 'SELL').length > 5 && <Text type="secondary">...</Text>}
                    </div>
                  </Space>
                </Card>
              </Col>
            </Row>
          </Card>

        </Space>
      </MonitoringContainer>
    );
  }

  // 거래가 실행 중이 아닌 경우 - 시장 분석 현황만 표시
  if ((!tradingStatus || !tradingStatus.is_trading) && (!aiStrategyDetails || !aiStrategyDetails.is_trading)) {
    return (
      <MonitoringContainer>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* 시장 분석 현황 헤더 */}
          <Card className="trading-card">
            <Row gutter={24} align="middle">
              <Col flex="auto">
                <Space size="large">
                  <Badge status="default" text={
                    <Text style={{ color: 'white', fontSize: '16px' }}>
                      <SearchOutlined /> 시장 분석 모니터링
                    </Text>
                  } />
                  <div>
                    <Text style={{ color: 'rgba(255,255,255,0.8)' }}>현재 상태</Text>
                    <br />
                    <Title level={4} style={{ color: 'white', margin: 0 }}>
                      시장 분석 대기 중
                    </Title>
                    <div style={{ marginTop: 4 }}>
                      <Tag color="orange" style={{ color: 'white' }}>
                        📊 실시간 시장 스캔
                      </Tag>
                    </div>
                  </div>
                </Space>
              </Col>
              <Col>
                <Button 
                  type="primary" 
                  size="large"
                  href="/ai-recommendation"
                >
                  AI 추천 전략 시작하기
                </Button>
              </Col>
            </Row>
          </Card>

          {/* 실시간 분석 진행 상황 */}
          <Card 
            title={
              <Space>
                <SearchOutlined spin />
                <span>실시간 분석 진행 상황</span>
                <Badge count={tradingStatus?.analysis?.scanning_coins || 0} style={{ backgroundColor: '#1890ff' }} />
              </Space>
            }
          >
            <Row gutter={[16, 16]}>
              <Col xs={24} md={8}>
                <Card size="small" style={{ background: '#fff7e6', borderLeft: '4px solid #fa8c16' }}>
                  <Space direction="vertical">
                    <Space>
                      <FireOutlined style={{ color: '#fa8c16', fontSize: 20 }} />
                      <Text strong>Tier 1 분석 중</Text>
                    </Space>
                    <Title level={4} style={{ margin: 0 }}>
                      {tradingStatus?.analysis?.tiers?.tier1?.count || 0}개 코인
                    </Title>
                    <Text type="secondary">거래량 급등 감지 (1초마다)</Text>
                    <div style={{ marginTop: 8 }}>
                      {tradingStatus?.analysis?.tiers?.tier1?.coins?.slice(0, 5).map(coin => (
                        <Tag key={coin} color="orange">{coin}</Tag>
                      ))}
                      {tradingStatus?.analysis?.tiers?.tier1?.coins?.length > 5 && <Text type="secondary">...</Text>}
                    </div>
                    <div style={{ marginTop: 8 }}>
                      <Text type="secondary">분석 중: 거래량 급등 패턴, 가격 변동성, 매수/매도 압력</Text>
                    </div>
                  </Space>
                </Card>
              </Col>
              
              <Col xs={24} md={8}>
                <Card size="small" style={{ background: '#f6ffed', borderLeft: '4px solid #52c41a' }}>
                  <Space direction="vertical">
                    <Space>
                      <CrownOutlined style={{ color: '#52c41a', fontSize: 20 }} />
                      <Text strong>Tier 2 분석 중</Text>
                    </Space>
                    <Title level={4} style={{ margin: 0 }}>
                      {tradingStatus?.analysis?.tiers?.tier2?.count || 0}개 코인
                    </Title>
                    <Text type="secondary">핵심 코인 모니터링 (5초마다)</Text>
                    <div style={{ marginTop: 8 }}>
                      {tradingStatus?.analysis?.tiers?.tier2?.coins?.slice(0, 5).map(coin => (
                        <Tag key={coin} color="green">{coin}</Tag>
                      ))}
                      {tradingStatus?.analysis?.tiers?.tier2?.coins?.length > 5 && <Text type="secondary">...</Text>}
                    </div>
                    <div style={{ marginTop: 8 }}>
                      <Text type="secondary">분석 중: 기술적 지표, 추세 분석, 지지/저항선</Text>
                    </div>
                  </Space>
                </Card>
              </Col>
              
              <Col xs={24} md={8}>
                <Card size="small" style={{ background: '#e6f7ff', borderLeft: '4px solid #1890ff' }}>
                  <Space direction="vertical">
                    <Space>
                      <TrophyOutlined style={{ color: '#1890ff', fontSize: 20 }} />
                      <Text strong>Tier 3 분석 중</Text>
                    </Space>
                    <Title level={4} style={{ margin: 0 }}>
                      {tradingStatus?.analysis?.tiers?.tier3?.count || 0}개 코인
                    </Title>
                    <Text type="secondary">시가총액 상위 스캔 (30초마다)</Text>
                    <div style={{ marginTop: 8 }}>
                      {tradingStatus?.analysis?.tiers?.tier3?.coins?.slice(0, 5).map(coin => (
                        <Tag key={coin} color="blue">{coin}</Tag>
                      ))}
                      {tradingStatus?.analysis?.tiers?.tier3?.coins?.length > 5 && <Text type="secondary">...</Text>}
                    </div>
                    <div style={{ marginTop: 8 }}>
                      <Text type="secondary">분석 중: 시장 전체 동향, 상관관계, 리스크 평가</Text>
                    </div>
                  </Space>
                </Card>
              </Col>
            </Row>
          </Card>

          {/* 매수/매도 신호 현황 */}
          <Card 
            title={
              <Space>
                <SearchOutlined spin />
                <span>발견된 거래 신호</span>
                <Badge count={(tradingStatus?.analysis?.top_opportunities?.filter(o => o.signal === 'BUY').length || 0) + (tradingStatus?.analysis?.top_opportunities?.filter(o => o.signal === 'SELL').length || 0)} style={{ backgroundColor: '#52c41a' }} />
              </Space>
            }
          >
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={12}>
                <Card size="small" style={{ background: '#f6ffed', borderLeft: '4px solid #52c41a' }}>
                  <Space direction="vertical">
                    <Space>
                      <RiseOutlined style={{ color: '#52c41a', fontSize: 20 }} />
                      <Text strong>매수 신호</Text>
                    </Space>
                    <Title level={4} style={{ margin: 0 }}>
                      {tradingStatus?.analysis?.top_opportunities?.filter(o => o.signal === 'BUY').length || 0}개
                    </Title>
                    <Text type="secondary">BUY 신호 감지</Text>
                    <div style={{ marginTop: 8 }}>
                      {tradingStatus?.analysis?.top_opportunities?.filter(o => o.signal === 'BUY').slice(0, 5).map(opp => (
                        <Tag key={opp.symbol} color="green">{opp.symbol}</Tag>
                      ))}
                      {tradingStatus?.analysis?.top_opportunities?.filter(o => o.signal === 'BUY').length > 5 && <Text type="secondary">...</Text>}
                    </div>
                  </Space>
                </Card>
              </Col>
              
              <Col xs={24} sm={12}>
                <Card size="small" style={{ background: '#fff2f0', borderLeft: '4px solid #ff4d4f' }}>
                  <Space direction="vertical">
                    <Space>
                      <FallOutlined style={{ color: '#ff4d4f', fontSize: 20 }} />
                      <Text strong>매도 신호</Text>
                    </Space>
                    <Title level={4} style={{ margin: 0 }}>
                      {tradingStatus?.analysis?.top_opportunities?.filter(o => o.signal === 'SELL').length || 0}개
                    </Title>
                    <Text type="secondary">SELL 신호 감지</Text>
                    <div style={{ marginTop: 8 }}>
                      {tradingStatus?.analysis?.top_opportunities?.filter(o => o.signal === 'SELL').slice(0, 5).map(opp => (
                        <Tag key={opp.symbol} color="red">{opp.symbol}</Tag>
                      ))}
                      {tradingStatus?.analysis?.top_opportunities?.filter(o => o.signal === 'SELL').length > 5 && <Text type="secondary">...</Text>}
                    </div>
                  </Space>
                </Card>
              </Col>
            </Row>
          </Card>

          {/* AI 추천 시작 안내 */}
          <Card>
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={
                <span>
                  거래를 시작하려면 AI 추천 전략을 선택하세요<br />
                  <Text type="secondary">
                    현재 시장 분석은 계속 진행되고 있습니다
                  </Text>
                </span>
              }
            >
              <Space>
                <Button type="primary" size="large" href="/ai-recommendation">
                  AI 추천 전략 시작하기
                </Button>
                <Button size="large" href="/strategies">
                  전통적 전략 보기
                </Button>
              </Space>
            </Empty>
          </Card>
        </Space>
      </MonitoringContainer>
    );
  }

  // 기본 모니터링 화면 - 현재는 사용되지 않음 (AI 추천 전략만 사용)
  return null;
};

export default Monitoring;