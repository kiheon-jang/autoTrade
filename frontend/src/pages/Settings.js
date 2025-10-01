import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Form, 
  Input, 
  Button, 
  Switch, 
  Select, 
  InputNumber,
  message,
  Tabs,
  Row,
  Col,
  Typography,
  Space,
  Divider,
  Alert
} from 'antd';
import { 
  SettingOutlined, 
  KeyOutlined, 
  BellOutlined,
  SecurityScanOutlined,
  SaveOutlined
} from '@ant-design/icons';
import styled from 'styled-components';

const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

const SettingsContainer = styled.div`
  .settings-card {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 24px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }
  
  .api-key-input {
    font-family: 'Courier New', monospace;
  }
  
  .setting-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 0;
    border-bottom: 1px solid #f0f0f0;
  }
  
  .setting-item:last-child {
    border-bottom: none;
  }
  
  .setting-label {
    font-weight: 500;
    color: #262626;
  }
  
  .setting-description {
    color: #8c8c8c;
    font-size: 0.875rem;
    margin-top: 4px;
  }
`;

const Settings = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [settings, setSettings] = useState({
    apiKeys: {
      bithumb: {
        accessKey: '',
        secretKey: '',
      },
      upbit: {
        accessKey: '',
        secretKey: '',
      },
      binance: {
        apiKey: '',
        secretKey: '',
      },
    },
    trading: {
      maxPositions: 5,
      riskPerTrade: 2.0,
      stopLoss: 5.0,
      takeProfit: 10.0,
    },
    notifications: {
      email: true,
      push: false,
      sms: false,
      tradingAlerts: true,
      systemAlerts: true,
    },
    system: {
      autoStart: true,
      debugMode: false,
      logLevel: 'INFO',
      dataRetention: 30,
    },
  });

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      // 설정 로드 (실제 API 연동 시 구현)
      form.setFieldsValue(settings);
    } catch (error) {
      console.error('설정 로딩 실패:', error);
    }
  };

  const handleSaveSettings = async (values) => {
    try {
      setLoading(true);
      // 설정 저장 (실제 API 연동 시 구현)
      console.log('설정 저장:', values);
      message.success('설정이 저장되었습니다.');
    } catch (error) {
      message.error('설정 저장에 실패했습니다.');
      console.error('설정 저장 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async (exchange) => {
    try {
      message.loading(`${exchange} 연결 테스트 중...`, 2);
      // API 연결 테스트 (실제 구현 시)
      message.success(`${exchange} 연결 성공!`);
    } catch (error) {
      message.error(`${exchange} 연결 실패: ${error.message}`);
    }
  };

  return (
    <SettingsContainer>
      <Title level={2}>설정</Title>

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSaveSettings}
        initialValues={settings}
      >
        <Tabs 
          defaultActiveKey="api"
          items={[
            {
              key: 'api',
              label: 'API 키 설정',
              icon: <KeyOutlined />,
              children: (
            <Card title="거래소 API 키" className="settings-card">
              <Alert
                message="보안 주의사항"
                description="API 키는 안전하게 보관하세요. 절대 타인과 공유하지 마세요."
                type="warning"
                showIcon
                style={{ marginBottom: 24 }}
              />

              <Row gutter={[16, 16]}>
                <Col xs={24} lg={8}>
                  <Card title="빗썸" size="small">
                    <Form.Item
                      name={['apiKeys', 'bithumb', 'accessKey']}
                      label="Access Key"
                    >
                      <Input.Password className="api-key-input" />
                    </Form.Item>
                    <Form.Item
                      name={['apiKeys', 'bithumb', 'secretKey']}
                      label="Secret Key"
                    >
                      <Input.Password className="api-key-input" />
                    </Form.Item>
                    <Button 
                      onClick={() => handleTestConnection('빗썸')}
                      style={{ width: '100%' }}
                    >
                      연결 테스트
                    </Button>
                  </Card>
                </Col>

                <Col xs={24} lg={8}>
                  <Card title="업비트" size="small">
                    <Form.Item
                      name={['apiKeys', 'upbit', 'accessKey']}
                      label="Access Key"
                    >
                      <Input.Password className="api-key-input" />
                    </Form.Item>
                    <Form.Item
                      name={['apiKeys', 'upbit', 'secretKey']}
                      label="Secret Key"
                    >
                      <Input.Password className="api-key-input" />
                    </Form.Item>
                    <Button 
                      onClick={() => handleTestConnection('업비트')}
                      style={{ width: '100%' }}
                    >
                      연결 테스트
                    </Button>
                  </Card>
                </Col>

                <Col xs={24} lg={8}>
                  <Card title="바이낸스" size="small">
                    <Form.Item
                      name={['apiKeys', 'binance', 'apiKey']}
                      label="API Key"
                    >
                      <Input.Password className="api-key-input" />
                    </Form.Item>
                    <Form.Item
                      name={['apiKeys', 'binance', 'secretKey']}
                      label="Secret Key"
                    >
                      <Input.Password className="api-key-input" />
                    </Form.Item>
                    <Button 
                      onClick={() => handleTestConnection('바이낸스')}
                      style={{ width: '100%' }}
                    >
                      연결 테스트
                    </Button>
                  </Card>
                </Col>
              </Row>
            </Card>
              ),
            },
            {
              key: 'trading',
              label: '거래 설정',
              icon: <SettingOutlined />,
              children: (
            <Card title="거래 파라미터" className="settings-card">
              <Row gutter={[16, 16]}>
                <Col xs={24} sm={12}>
                  <Form.Item
                    name={['trading', 'maxPositions']}
                    label="최대 포지션 수"
                    rules={[{ required: true, message: '최대 포지션 수를 입력해주세요.' }]}
                  >
                    <InputNumber
                      min={1}
                      max={20}
                      style={{ width: '100%' }}
                      placeholder="예: 5"
                    />
                  </Form.Item>
                </Col>
                
                <Col xs={24} sm={12}>
                  <Form.Item
                    name={['trading', 'riskPerTrade']}
                    label="거래당 리스크 (%)"
                    rules={[{ required: true, message: '리스크 비율을 입력해주세요.' }]}
                  >
                    <InputNumber
                      min={0.1}
                      max={10}
                      step={0.1}
                      style={{ width: '100%' }}
                      placeholder="예: 2.0"
                    />
                  </Form.Item>
                </Col>
                
                <Col xs={24} sm={12}>
                  <Form.Item
                    name={['trading', 'stopLoss']}
                    label="손절선 (%)"
                  >
                    <InputNumber
                      min={1}
                      max={50}
                      step={0.5}
                      style={{ width: '100%' }}
                      placeholder="예: 5.0"
                    />
                  </Form.Item>
                </Col>
                
                <Col xs={24} sm={12}>
                  <Form.Item
                    name={['trading', 'takeProfit']}
                    label="익절선 (%)"
                  >
                    <InputNumber
                      min={1}
                      max={100}
                      step={0.5}
                      style={{ width: '100%' }}
                      placeholder="예: 10.0"
                    />
                  </Form.Item>
                </Col>
              </Row>
            </Card>
              ),
            },
            {
              key: 'notifications',
              label: '알림 설정',
              icon: <BellOutlined />,
              children: (
            <Card title="알림 설정" className="settings-card">
              <div className="setting-item">
                <div>
                  <div className="setting-label">이메일 알림</div>
                  <div className="setting-description">
                    거래 및 시스템 알림을 이메일로 받습니다.
                  </div>
                </div>
                <Form.Item name={['notifications', 'email']} valuePropName="checked">
                  <Switch />
                </Form.Item>
              </div>

              <div className="setting-item">
                <div>
                  <div className="setting-label">푸시 알림</div>
                  <div className="setting-description">
                    브라우저 푸시 알림을 받습니다.
                  </div>
                </div>
                <Form.Item name={['notifications', 'push']} valuePropName="checked">
                  <Switch />
                </Form.Item>
              </div>

              <div className="setting-item">
                <div>
                  <div className="setting-label">거래 알림</div>
                  <div className="setting-description">
                    거래 실행 및 결과에 대한 알림을 받습니다.
                  </div>
                </div>
                <Form.Item name={['notifications', 'tradingAlerts']} valuePropName="checked">
                  <Switch />
                </Form.Item>
              </div>

              <div className="setting-item">
                <div>
                  <div className="setting-label">시스템 알림</div>
                  <div className="setting-description">
                    시스템 오류 및 경고에 대한 알림을 받습니다.
                  </div>
                </div>
                <Form.Item name={['notifications', 'systemAlerts']} valuePropName="checked">
                  <Switch />
                </Form.Item>
              </div>
            </Card>
              ),
            },
            {
              key: 'system',
              label: '시스템 설정',
              icon: <SecurityScanOutlined />,
              children: (
            <Card title="시스템 설정" className="settings-card">
              <Row gutter={[16, 16]}>
                <Col xs={24} sm={12}>
                  <Form.Item
                    name={['system', 'logLevel']}
                    label="로그 레벨"
                  >
                    <Select>
                      <Option value="DEBUG">DEBUG</Option>
                      <Option value="INFO">INFO</Option>
                      <Option value="WARNING">WARNING</Option>
                      <Option value="ERROR">ERROR</Option>
                    </Select>
                  </Form.Item>
                </Col>
                
                <Col xs={24} sm={12}>
                  <Form.Item
                    name={['system', 'dataRetention']}
                    label="데이터 보관 기간 (일)"
                  >
                    <InputNumber
                      min={7}
                      max={365}
                      style={{ width: '100%' }}
                      placeholder="예: 30"
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Divider />

              <div className="setting-item">
                <div>
                  <div className="setting-label">자동 시작</div>
                  <div className="setting-description">
                    시스템 시작 시 자동으로 거래를 시작합니다.
                  </div>
                </div>
                <Form.Item name={['system', 'autoStart']} valuePropName="checked">
                  <Switch />
                </Form.Item>
              </div>

              <div className="setting-item">
                <div>
                  <div className="setting-label">디버그 모드</div>
                  <div className="setting-description">
                    상세한 로그를 출력합니다. (성능에 영향을 줄 수 있습니다)
                  </div>
                </div>
                <Form.Item name={['system', 'debugMode']} valuePropName="checked">
                  <Switch />
                </Form.Item>
              </div>
            </Card>
              ),
            },
          ]}
        />

        <Card style={{ marginTop: 24 }}>
          <Space>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={loading}
              icon={<SaveOutlined />}
              size="large"
            >
              설정 저장
            </Button>
            <Button size="large">
              초기화
            </Button>
          </Space>
        </Card>
      </Form>
    </SettingsContainer>
  );
};

export default Settings;
