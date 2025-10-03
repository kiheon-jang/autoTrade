import { useState, useEffect, useRef, useCallback } from 'react';

const useWebSocket = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [error, setError] = useState(null);
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const pingIntervalRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectDelay = 5000; // 5초로 증가

  const connectWebSocket = useCallback(() => {
    try {
      // 이전 연결 정리
      if (socketRef.current) {
        socketRef.current.close();
      }

      // FastAPI WebSocket 엔드포인트에 직접 연결
      const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8008';
      console.log(`WebSocket 연결 시도: ${wsUrl}/api/v1/monitoring/ws`);
      socketRef.current = new WebSocket(`${wsUrl}/api/v1/monitoring/ws`);

      socketRef.current.onopen = () => {
        console.log('✅ WebSocket 연결 성공');
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;

        // Ping 메시지 전송 (60초마다로 증가)
        pingIntervalRef.current = setInterval(() => {
          if (socketRef.current?.readyState === WebSocket.OPEN) {
            socketRef.current.send('ping');
          }
        }, 60000);
      };

      socketRef.current.onclose = (event) => {
        console.log('WebSocket 연결 끊김:', event.code, event.reason);
        setIsConnected(false);
        
        // Ping 인터벌 정리
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
        }

        // 자동 재연결 시도
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          console.log(`재연결 시도 (${reconnectAttemptsRef.current}/${maxReconnectAttempts})...`);
          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket();
          }, reconnectDelay);
        } else {
          setError('WebSocket 재연결 실패 (최대 시도 횟수 초과)');
        }
      };

      socketRef.current.onerror = (err) => {
        console.error('❌ WebSocket 연결 오류:', err);
        setError('WebSocket 연결 실패');
        setIsConnected(false);
      };

      socketRef.current.onmessage = (event) => {
        try {
          // pong 응답은 무시
          if (event.data === 'pong') {
            return;
          }

          const data = JSON.parse(event.data);
          console.log('📨 WebSocket 메시지 수신:', data.type);
          setLastMessage(data);
        } catch (error) {
          console.error('메시지 파싱 오류:', error, event.data);
        }
      };

    } catch (error) {
      console.error('WebSocket 연결 실패:', error);
      setError(error.message);
      setIsConnected(false);
    }
  }, []);

  useEffect(() => {
    connectWebSocket();

    return () => {
      // 정리
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [connectWebSocket]);

  const sendMessage = (message) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket이 연결되지 않았습니다. 메시지를 보낼 수 없습니다.');
    }
  };

  const subscribe = (event, callback) => {
    // FastAPI WebSocket은 이벤트 기반이 아닌 메시지 기반이므로
    // lastMessage를 통해 데이터를 받습니다
    console.log('WebSocket 구독:', event);
  };

  const unsubscribe = (event, callback) => {
    console.log('WebSocket 구독 해제:', event);
  };

  const reconnect = () => {
    reconnectAttemptsRef.current = 0;
    connectWebSocket();
  };

  return {
    isConnected,
    lastMessage,
    error,
    sendMessage,
    subscribe,
    unsubscribe,
    reconnect,
  };
};

export { useWebSocket };
export default useWebSocket;