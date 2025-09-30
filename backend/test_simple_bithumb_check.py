import hashlib
import hmac
import time
import base64
from urllib.parse import urlencode
import requests

API_KEY = "13fe3082684f7e859cec64bbd06740be"
SECRET_KEY = "7df353db18bc2fc7875631be6c565a70"

def test_bithumb_api():
    endpoint = '/info/balance'
    nonce = str(int(time.time() * 1000))
    params = {'currency': 'BTC'}  # endpoint 추가하지 않음
    
    post_data = urlencode(params)
    message = endpoint + chr(0) + post_data + chr(0) + nonce
    
    # 빗썸 공식 서명 생성 (공식 샘플 방식)
    # 1단계: HMAC-SHA512 암호화 (Secret Key는 원본 문자열 사용)
    h = hmac.new(
        SECRET_KEY.encode('utf-8'),  # 원본 문자열 그대로 사용
        message.encode('utf-8'),
        hashlib.sha512
    )
    
    # 2단계: hexdigest()로 16진수 문자열 생성
    hex_output = h.hexdigest()
    
    # 3단계: 16진수 문자열을 UTF-8로 인코딩 후 Base64 인코딩
    utf8_hex_output = hex_output.encode('utf-8')
    api_sign = base64.b64encode(utf8_hex_output).decode('utf-8')
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Api-Key': API_KEY,
        'Api-Sign': api_sign,
        'Api-Nonce': nonce
    }
    
    response = requests.post(
        'https://api.bithumb.com' + endpoint,
        data=params,
        headers=headers
    )
    
    print("=" * 50)
    print(f"HTTP Status: {response.status_code}")
    data = response.json()
    print(f"응답 코드: {data.get('status')}")
    print(f"응답 메시지: {data.get('message')}")
    print("=" * 50)
    
    if data.get('status') == '0000':
        print("✅ API 키 정상 작동!")
    elif data.get('status') == '5300':
        print("❌ 인증 실패 - 활성화 대기 또는 키 오류")
    else:
        print(f"❌ 에러: {data}")

if __name__ == "__main__":
    test_bithumb_api()
