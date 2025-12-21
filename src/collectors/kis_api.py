import requests
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import os
import sys

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent

class KisApi:
    """한국투자증권 REST API 클라이언트"""
    
    URL_REAL = "https://openapi.koreainvestment.com:9443"
    URL_VIRTUAL = "https://openapivts.koreainvestment.com:29443"
    
    def __init__(self, app_key, app_secret, account_no, is_virtual=True):
        self.app_key = app_key
        self.app_secret = app_secret
        self.account_no = account_no
        self.is_virtual = is_virtual
        self.base_url = self.URL_VIRTUAL if is_virtual else self.URL_REAL
        
        self.access_token = None
        self.token_expired = None
        
        # 계좌번호 분리 (앞 8자리, 뒤 2자리)
        if '-' in account_no:
            self.cano, self.acnt_prdt_cd = account_no.split('-')
        else:
            self.cano = account_no[:8]
            self.acnt_prdt_cd = account_no[8:]
            
        self.token_file = PROJECT_ROOT / "token.json"
        self.load_token()

    def load_token(self):
        """토큰 파일에서 로드"""
        try:
            if self.token_file.exists():
                with open(self.token_file, 'r') as f:
                    data = json.load(f)
                    expired = datetime.fromisoformat(data['expired'])
                    if datetime.now() < expired:
                        self.access_token = data['token']
                        self.token_expired = expired
                        print(f"[INFO] 저장된 Access Token 로드 (만료: {expired})")
        except Exception as e:
            print(f"[WARNING] 토큰 로드 실패: {e}")

    def save_token(self):
        """토큰 파일 저장"""
        try:
            data = {
                'token': self.access_token,
                'expired': self.token_expired.isoformat()
            }
            with open(self.token_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"[WARNING] 토큰 저장 실패: {e}")

    def get_access_token(self):
        """접근 토큰 발급/갱신"""
        # 기존 토큰이 있고 유효하면 반환
        if self.access_token and self.token_expired and datetime.now() < self.token_expired:
            return self.access_token
            
        path = "/oauth2/tokenP"
        url = f"{self.base_url}{path}"
        
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        try:
            res = requests.post(url, headers=headers, data=json.dumps(body))
            res.raise_for_status()
            data = res.json()
            
            self.access_token = data['access_token']
            # 토큰 유효기간 (보통 24시간이지만 안전하게 12시간으로 설정)
            self.token_expired = datetime.now() + timedelta(hours=12)
            print(f"[INFO] Access Token 발급 성공 (만료: {data['access_token_token_expired']})")
            
            # 파일 저장
            self.save_token()
            return self.access_token
            
        except Exception as e:
            print(f"[ERROR] Access Token 발급 실패: {e}")
            # print(f"Response: {res.text}") # 403 에러 등의 경우 text 확인
            raise

    def get_approval_key(self):
        """실시간(WebSocket) 접속키 발급"""
        path = "/oauth2/Approval"
        url = f"{self.base_url}{path}"
        
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret
        }
        
        try:
            res = requests.post(url, headers=headers, data=json.dumps(body))
            res.raise_for_status()
            data = res.json()
            print(f"[INFO] Approval Key 발급 성공")
            return data['approval_key']
        except Exception as e:
            print(f"[ERROR] Approval Key 발급 실패: {e}")
            raise

    def get_current_price(self, ticker):
        """주식 현재가 조회 (REST)"""
        path = "/uapi/domestic-stock/v1/quotations/inquire-price"
        url = f"{self.base_url}{path}"
        
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.get_access_token()}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKST01010100"  # 주식현재가 시세
        }
        
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": ticker
        }
        
        try:
            res = requests.get(url, headers=headers, params=params)
            res.raise_for_status()
            data = res.json()
            
            if data['rt_cd'] != '0':
                print(f"[ERROR] API 호출 오류: {data['msg1']}")
                return None
                
            output = data['output']
            return {
                'ticker': ticker,
                'price': int(output['stck_prpr']),
                'change': int(output['prdy_vrss']),
                'change_rate': float(output['prdy_ctrt']),
                'volume': int(output['acml_vol']),
                'high': int(output['stck_hgpr']),
                'low': int(output['stck_lwpr']),
                'open': int(output['stck_oprc']),
                'timestamp': datetime.now()
            }
        except Exception as e:
            print(f"[ERROR] 현재가 조회 실패 ({ticker}): {e}")
            return None

    def get_orderbook(self, ticker):
        """주식 호가 조회 (REST)"""
        path = "/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn"
        url = f"{self.base_url}{path}"
        
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.get_access_token()}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKST01010200"  # 주식호가(10단계)
        }
        
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": ticker
        }
        
        try:
            res = requests.get(url, headers=headers, params=params)
            res.raise_for_status()
            data = res.json()
            output1 = data['output1']
            
            ask_prices = []
            ask_volumes = []
            bid_prices = []
            bid_volumes = []
            
            for i in range(1, 11):
                ask_prices.append(int(output1[f'askp{i}']))
                ask_volumes.append(int(output1[f'askp_rsqn{i}']))
                bid_prices.append(int(output1[f'bidp{i}']))
                bid_volumes.append(int(output1[f'bidp_rsqn{i}']))
            
            return {
                'ticker': ticker,
                'ask_prices': ask_prices,
                'ask_volumes': ask_volumes,
                'bid_prices': bid_prices,
                'bid_volumes': bid_volumes,
                'timestamp': datetime.now()
            }
        except Exception as e:
            print(f"[ERROR] 호가 조회 실패 ({ticker}): {e}")
            return None
