import React, { useState, useEffect } from 'react';
import { 
  Row, 
  Col, 
  Card, 
  Table, 
  Tag, 
  Progress, 
  Statistic, 
  Space, 
  Typography, 
  Button, 
  Modal, 
  Form, 
  Input, 
  Select, 
  message,
  Tabs,
  Badge,
  Tooltip
} from 'antd';
import { 
  RobotOutlined, 
  BarChartOutlined, 
  ThunderboltOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import styled from 'styled-components';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { mlModelsAPI } from '../services/api';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { Option } = Select;

const MLModelsContainer = styled.div`
  .model-card {
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease;
    
    &:hover {
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
      transform: translateY(-2px);
    }
  }
  
  .metric-card {
    text-align: center;
    padding: 24px;
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
    font-size: 0.9rem;
    opacity: 0.9;
  }
  
  .status-badge {
    &.active {
      background: #f6ffed;
      border-color: #b7eb8f;
      color: #52c41a;
    }
    
    &.training {
      background: #fff7e6;
      border-color: #ffd591;
      color: #fa8c16;
    }
    
    &.error {
      background: #fff2f0;
      border-color: #ffccc7;
      color: #ff4d4f;
    }
  }
`;

const MLModels = () => {
  const [models, setModels] = useState([]);
  const [performance, setPerformance] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [trainingModalVisible, setTrainingModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [trainingForm] = Form.useForm();

  useEffect(() => {
    fetchModels();
    fetchPerformance();
    fetchPredictions();
  }, []);

  const fetchModels = async () => {
    try {
      const response = await mlModelsAPI.getModels();
      setModels(response.data || []);
    } catch (error) {
      console.error('모델 목록 로딩 실패:', error);
      message.error('모델 목록을 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const fetchPerformance = async () => {
    try {
      const response = await mlModelsAPI.getPerformance();
      setPerformance(response.data || []);
    } catch (error) {
      console.error('성능 데이터 로딩 실패:', error);
    }
  };

  const fetchPredictions = async () => {
    try {
      const response = await mlModelsAPI.getPredictions();
      setPredictions(response.data || []);
    } catch (error) {
      console.error('예측 데이터 로딩 실패:', error);
    }
  };

  const handleCreateModel = async (values) => {
    try {
      await mlModelsAPI.createModel(values);
      message.success('모델이 생성되었습니다.');
      setModalVisible(false);
      form.resetFields();
      fetchModels();
    } catch (error) {
      console.error('모델 생성 실패:', error);
      message.error('모델 생성에 실패했습니다.');
    }
  };

  const handleTrainModel = async (values) => {
    try {
      await mlModelsAPI.trainModel(values);
      message.success('모델 훈련이 시작되었습니다.');
      setTrainingModalVisible(false);
      trainingForm.resetFields();
      fetchModels();
    } catch (error) {
      console.error('모델 훈련 실패:', error);
      message.error('모델 훈련에 실패했습니다.');
    }
  };

  const handleDeployModel = async (modelId) => {
    try {
      await mlModelsAPI.deployModel({ model_id: modelId });
      message.success('모델이 배포되었습니다.');
      fetchModels();
    } catch (error) {
      console.error('모델 배포 실패:', error);
      message.error('모델 배포에 실패했습니다.');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return 'success';
      case 'training': return 'warning';
      case 'error': return 'error';
      default: return 'default';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'active': return '활성';
      case 'training': return '훈련중';
      case 'error': return '오류';
      default: return '알 수 없음';
    }
  };

  const modelColumns = [
    {
      title: '모델명',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <Space>
          <RobotOutlined />
          <Text strong>{text}</Text>
        </Space>
      ),
    },
    {
      title: '타입',
      dataIndex: 'model_type',
      key: 'model_type',
      render: (type) => {
        const typeMap = {
          'random_forest': { color: 'blue', text: 'Random Forest' },
          'gradient_boosting': { color: 'green', text: 'Gradient Boosting' },
          'logistic_regression': { color: 'orange', text: 'Logistic Regression' },
          'neural_network': { color: 'purple', text: 'Neural Network' },
        };
        const config = typeMap[type] || { color: 'default', text: type };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '상태',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={getStatusColor(status)}>
          {getStatusText(status)}
        </Tag>
      ),
    },
    {
      title: '정확도',
      dataIndex: 'accuracy',
      key: 'accuracy',
      render: (accuracy) => (
        <Progress 
          percent={Math.round(accuracy * 100)} 
          size="small" 
          status={accuracy > 0.8 ? 'success' : accuracy > 0.6 ? 'normal' : 'exception'}
        />
      ),
    },
    {
      title: '생성일',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => new Date(date).toLocaleDateString(),
    },
    {
      title: '액션',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button 
            type="primary" 
            size="small" 
            icon={<PlayCircleOutlined />}
            onClick={() => handleDeployModel(record.id)}
            disabled={record.status !== 'active'}
          >
            배포
          </Button>
          <Button 
            size="small" 
            icon={<ReloadOutlined />}
            onClick={() => fetchModels()}
          >
            새로고침
          </Button>
        </Space>
      ),
    },
  ];

  const performanceColumns = [
    {
      title: '모델',
      dataIndex: 'model_name',
      key: 'model_name',
    },
    {
      title: '정확도',
      dataIndex: 'accuracy',
      key: 'accuracy',
      render: (value) => `${(value * 100).toFixed(2)}%`,
    },
    {
      title: '정밀도',
      dataIndex: 'precision',
      key: 'precision',
      render: (value) => `${(value * 100).toFixed(2)}%`,
    },
    {
      title: '재현율',
      dataIndex: 'recall',
      key: 'recall',
      render: (value) => `${(value * 100).toFixed(2)}%`,
    },
    {
      title: 'F1 점수',
      dataIndex: 'f1_score',
      key: 'f1_score',
      render: (value) => `${(value * 100).toFixed(2)}%`,
    },
    {
      title: 'AUC',
      dataIndex: 'auc',
      key: 'auc',
      render: (value) => `${(value * 100).toFixed(2)}%`,
    },
    {
      title: '측정일',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => new Date(date).toLocaleString(),
    },
  ];

  return (
    <MLModelsContainer>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={2}>🤖 ML 모델 관리</Title>
          <Text type="secondary">머신러닝 모델 훈련, 배포 및 성능 모니터링</Text>
        </Col>
        <Col>
          <Space>
            <Button 
              type="primary" 
              icon={<RobotOutlined />}
              onClick={() => setModalVisible(true)}
            >
              새 모델 생성
            </Button>
            <Button 
              icon={<ThunderboltOutlined />}
              onClick={() => setTrainingModalVisible(true)}
            >
              모델 훈련
            </Button>
          </Space>
        </Col>
      </Row>

      {/* 주요 지표 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <div className="metric-card">
            <RobotOutlined style={{ fontSize: 32, marginBottom: 12 }} />
            <div className="metric-value">
              {models.length}
            </div>
            <div className="metric-label">총 모델 수</div>
          </div>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <div className="metric-card">
            <CheckCircleOutlined style={{ fontSize: 32, marginBottom: 12 }} />
            <div className="metric-value">
              {models.filter(m => m.status === 'active').length}
            </div>
            <div className="metric-label">활성 모델</div>
          </div>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <div className="metric-card">
            <BarChartOutlined style={{ fontSize: 32, marginBottom: 12 }} />
            <div className="metric-value">
              {models.length > 0 ? (models.reduce((sum, m) => sum + (m.accuracy || 0), 0) / models.length * 100).toFixed(1) : 0}%
            </div>
            <div className="metric-label">평균 정확도</div>
          </div>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <div className="metric-card">
            <ThunderboltOutlined style={{ fontSize: 32, marginBottom: 12 }} />
            <div className="metric-value">
              {models.filter(m => m.status === 'training').length}
            </div>
            <div className="metric-label">훈련 중</div>
          </div>
        </Col>
      </Row>

      <Tabs defaultActiveKey="models">
        <TabPane tab="모델 목록" key="models">
          <Card className="model-card">
            <Table
              dataSource={models}
              columns={modelColumns}
              loading={loading}
              rowKey="id"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </TabPane>

        <TabPane tab="성능 모니터링" key="performance">
          <Row gutter={[24, 24]}>
            <Col xs={24} lg={16}>
              <Card title="모델 성능 추이" className="model-card">
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={performance}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="created_at" />
                    <YAxis domain={[0, 1]} />
                    <RechartsTooltip />
                    <Line 
                      type="monotone" 
                      dataKey="accuracy" 
                      stroke="#1890ff" 
                      strokeWidth={2}
                      name="정확도"
                    />
                    <Line 
                      type="monotone" 
                      dataKey="precision" 
                      stroke="#52c41a" 
                      strokeWidth={2}
                      name="정밀도"
                    />
                    <Line 
                      type="monotone" 
                      dataKey="recall" 
                      stroke="#fa8c16" 
                      strokeWidth={2}
                      name="재현율"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </Card>
            </Col>
            
            <Col xs={24} lg={8}>
              <Card title="성능 지표" className="model-card">
                <Table
                  dataSource={performance.slice(-5)}
                  columns={performanceColumns}
                  pagination={false}
                  size="small"
                  rowKey="id"
                />
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane tab="예측 결과" key="predictions">
          <Card title="최근 예측 결과" className="model-card">
            <Table
              dataSource={predictions}
              columns={[
                {
                  title: '모델',
                  dataIndex: 'model_name',
                  key: 'model_name',
                },
                {
                  title: '예측값',
                  dataIndex: 'prediction',
                  key: 'prediction',
                  render: (value) => (
                    <Tag color={value > 0.5 ? 'green' : 'red'}>
                      {value > 0.5 ? '매수 신호' : '매도 신호'}
                    </Tag>
                  ),
                },
                {
                  title: '신뢰도',
                  dataIndex: 'confidence',
                  key: 'confidence',
                  render: (value) => `${(value * 100).toFixed(1)}%`,
                },
                {
                  title: '예측 시간',
                  dataIndex: 'created_at',
                  key: 'created_at',
                  render: (date) => new Date(date).toLocaleString(),
                },
              ]}
              rowKey="id"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </TabPane>
      </Tabs>

      {/* 모델 생성 모달 */}
      <Modal
        title="새 모델 생성"
        visible={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateModel}
        >
          <Form.Item
            name="name"
            label="모델명"
            rules={[{ required: true, message: '모델명을 입력해주세요.' }]}
          >
            <Input placeholder="예: BTC_Price_Predictor" />
          </Form.Item>
          
          <Form.Item
            name="model_type"
            label="모델 타입"
            rules={[{ required: true, message: '모델 타입을 선택해주세요.' }]}
          >
            <Select placeholder="모델 타입을 선택하세요">
              <Option value="random_forest">Random Forest</Option>
              <Option value="gradient_boosting">Gradient Boosting</Option>
              <Option value="logistic_regression">Logistic Regression</Option>
              <Option value="neural_network">Neural Network</Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            name="description"
            label="설명"
          >
            <Input.TextArea placeholder="모델에 대한 설명을 입력하세요." />
          </Form.Item>
          
          <Form.Item>
            <Button type="primary" htmlType="submit" block>
              모델 생성
            </Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* 모델 훈련 모달 */}
      <Modal
        title="모델 훈련"
        visible={trainingModalVisible}
        onCancel={() => setTrainingModalVisible(false)}
        footer={null}
      >
        <Form
          form={trainingForm}
          layout="vertical"
          onFinish={handleTrainModel}
        >
          <Form.Item
            name="model_id"
            label="모델 선택"
            rules={[{ required: true, message: '모델을 선택해주세요.' }]}
          >
            <Select placeholder="훈련할 모델을 선택하세요">
              {models.map(model => (
                <Option key={model.id} value={model.id}>
                  {model.name} ({model.model_type})
                </Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item
            name="training_data_period"
            label="훈련 데이터 기간 (일)"
            rules={[{ required: true, message: '훈련 데이터 기간을 입력해주세요.' }]}
          >
            <Input type="number" placeholder="30" />
          </Form.Item>
          
          <Form.Item
            name="test_data_period"
            label="테스트 데이터 기간 (일)"
            rules={[{ required: true, message: '테스트 데이터 기간을 입력해주세요.' }]}
          >
            <Input type="number" placeholder="7" />
          </Form.Item>
          
          <Form.Item>
            <Button type="primary" htmlType="submit" block>
              훈련 시작
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </MLModelsContainer>
  );
};

export default MLModels;
