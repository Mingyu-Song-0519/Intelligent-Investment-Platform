"""
Model Repository - Infrastructure Layer

Clean Architecture:
- 모델 저장/로드의 Infrastructure 계층
- 파일 시스템 세부사항을 Service Layer로부터 분리
"""
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


class ModelRepository:
    """
    AI 모델 및 메타데이터 저장/로드 Repository
    
    책임:
    - 모델 파일 및 메타데이터 영속성 관리
    - 파일 경로 생성 및 관리
    - 버전 관리 지원
    """
    
    def __init__(self, storage_path: str = "src/models/saved_models"):
        """
        Args:
            storage_path: 모델 저장 루트 디렉토리
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def save_model_with_metadata(
        self,
        ticker: str,
        model: Any,
        metadata: Dict[str, Any],
        model_type: str = "lstm"
    ) -> str:
        """
        모델과 메타데이터를 함께 저장
        
        Args:
            ticker: 종목 코드 (예: "005930", "AAPL")
            model: 저장할 모델 객체
            metadata: 메타데이터 딕셔너리
            model_type: 모델 타입 ("lstm", "xgboost", "transformer")
        
        Returns:
            저장된 모델 prefix (파일명 접두사)
        """
        # 파일명 prefix 생성
        safe_ticker = ticker.replace(":", "").replace("/", "").replace(".KS", "")
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"{safe_ticker}_{today}"
        
        # 버전 및 해시 추가
        metadata['version'] = '1.0.0'
        metadata['ticker'] = ticker
        metadata['model_type'] = model_type
        metadata['save_date'] = datetime.now().isoformat()
        
        # Feature 해시 계산
        if 'feature_cols' in metadata:
            feature_str = ','.join(sorted(metadata['feature_cols']))
            metadata['feature_hash'] = hashlib.md5(feature_str.encode()).hexdigest()[:8]
        
        # 메타데이터 저장
        metadata_path = self.storage_path / f"{prefix}_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return str(prefix)
    
    def load_metadata(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        저장된 모델의 메타데이터 로드
        
        Args:
            ticker: 종목 코드
        
        Returns:
            메타데이터 딕셔너리 또는 None (없을 경우)
        """
        # Ticker 변형 후보군 생성 (.KS 포함/미포함 모두 검색)
        candidates = set()
        base_ticker = ticker.replace(":", "").replace("/", "")
        candidates.add(base_ticker)
        candidates.add(base_ticker.replace(".KS", ""))
        
        metadata_files = []
        for cand in candidates:
            if not cand: continue
            for suffix in ["_lstm_metadata.json", "_xgboost_metadata.json", "_transformer_metadata.json"]:
                metadata_files.extend(list(self.storage_path.glob(f"{cand}_*{suffix}")))
        
        if not metadata_files:
            return None
        
        # 날짜순 정렬 (최신 파일)
        # 파일명: ticker_YYYYMMDD_model_metadata.json
        latest_file = sorted(metadata_files, reverse=True)[0]
        
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load metadata: {e}")
            return None
    
    def get_model_prefix(self, ticker: str) -> Optional[str]:
        """
        저장된 모델의 prefix 가져오기
        
        Args:
            ticker: 종목 코드
        
        Returns:
            모델 prefix 또는 None
        """
        metadata = self.load_metadata(ticker)
        if metadata is None:
            return None
        
        safe_ticker = ticker.replace(":", "").replace("/", "").replace(".KS", "")
        save_date = datetime.fromisoformat(metadata['save_date']).strftime("%Y%m%d")
        
        return f"{safe_ticker}_{save_date}"
