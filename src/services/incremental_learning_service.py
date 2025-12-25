"""
Incremental Learning Service - Application Layer

Clean Architecture:
- 점진적 학습 유즈케이스 오케스트레이션
- UI는 이 서비스만 호출
- 비즈니스 로직 캡슐화
"""
import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict, Any
from datetime import datetime
from src.infrastructure.repositories.model_repository import ModelRepository


class IncrementalLearningService:
    """
    점진적 학습 오케스트레이션 서비스
    
    책임:
    - 신규 데이터 감지
    - Distribution Shift 분석
    - 점진적 학습 가능 여부 판단
    - Replay Buffer 생성
    """
    
    def __init__(self, model_repo: ModelRepository):
        """
        Args:
            model_repo: 모델 저장소 (DI)
        """
        self.model_repo = model_repo
    
    def check_incremental_availability(
        self,
        ticker: str,
        current_data: pd.DataFrame
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        점진적 학습 가능 여부 및 신규 데이터 정보 반환
        
        Args:
            ticker: 종목 코드
            current_data: 현재 전체 데이터 (date 컬럼 포함)
        
        Returns:
            (가능 여부, 신규 데이터 정보)
            
            info = {
                'new_data_count': int,
                'new_data_start': str,
                'new_data_end': str,
                'shift_detected': bool,
                'shift_info': dict or None,
                'recommendation': 'incremental' or 'full_retrain',
                'metadata': dict
            }
        """
        # 1. 저장된 모델 메타데이터 로드
        metadata = self.model_repo.load_metadata(ticker)
        if metadata is None:
            return False, None
        
        # 2. 신규 데이터 추출
        data_end_date = pd.to_datetime(metadata['data_end_date'])
        current_data_copy = current_data.copy()
        current_data_copy['date'] = pd.to_datetime(current_data_copy['date'])
        
        new_data = current_data_copy[current_data_copy['date'] > data_end_date]
        
        if len(new_data) == 0:
            return False, {
                'status': 'up_to_date',
                'new_data_count': 0,
                'metadata': metadata
            }
        
        # 3. Distribution Shift 감지
        old_data = current_data_copy[current_data_copy['date'] <= data_end_date]
        shift_detected, shift_info = self._detect_distribution_shift(old_data, new_data)
        
        # 4. Feature 호환성 검증
        compatible, error_msg = self._validate_feature_compatibility(
            current_features=current_data.columns.tolist(),
            metadata=metadata
        )
        
        if not compatible:
            # Feature 불일치 시 전체 재학습 강제
            return False, {'error': error_msg}
        
        # 5. 반환 정보 구성
        info = {
            'new_data_count': len(new_data),
            'new_data_start': new_data['date'].min().strftime('%Y-%m-%d'),
            'new_data_end': new_data['date'].max().strftime('%Y-%m-%d'),
            'shift_detected': shift_detected,
            'shift_info': shift_info,
            'recommendation': 'full_retrain' if shift_detected else 'incremental',
            'metadata': metadata
        }
        
        return True, info
    
    def _detect_distribution_shift(
        self,
        old_data: pd.DataFrame,
        new_data: pd.DataFrame,
        kl_threshold: float = 0.3,
        vol_threshold: float = 0.5
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        KL Divergence를 이용한 데이터 분포 변화 감지
        
        Args:
            old_data: 과거 데이터
            new_data: 신규 데이터
            kl_threshold: KL Divergence 임계값
            vol_threshold: 변동성 변화 비율 임계값
        
        Returns:
            (shift 감지 여부, 상세 정보)
        """
        try:
            from scipy.stats import entropy
            
            # 수익률 계산
            old_returns = old_data['close'].pct_change().dropna()
            new_returns = new_data['close'].pct_change().dropna()
            
            if len(old_returns) < 2 or len(new_returns) < 2:
                return False, None
            
            # 히스토그램 생성 (동일한 bins)
            bins = np.linspace(-0.1, 0.1, 50)
            old_hist, _ = np.histogram(old_returns, bins=bins, density=True)
            new_hist, _ = np.histogram(new_returns, bins=bins, density=True)
            
            # KL Divergence 계산 (0 방지를 위한 smoothing)
            old_hist = old_hist + 1e-10
            new_hist = new_hist + 1e-10
            old_hist = old_hist / old_hist.sum()
            new_hist = new_hist / new_hist.sum()
            
            kl_div = entropy(old_hist, new_hist)
            
            # 변동성 비교
            old_vol = old_returns.std()
            new_vol = new_returns.std()
            vol_ratio = abs(new_vol / old_vol - 1) if old_vol > 0 else 0
            
            # Shift 감지
            shift_detected = (kl_div > kl_threshold) or (vol_ratio > vol_threshold)
            
            if shift_detected:
                shift_info = {
                    'kl_divergence': float(kl_div),
                    'kl_threshold': kl_threshold,
                    'volatility_old': float(old_vol),
                    'volatility_new': float(new_vol),
                    'volatility_change_ratio': float(vol_ratio),
                    'recommendation': '⚠️ 시장 급변 감지: 전체 재학습 권장'
                }
                return True, shift_info
            
            return False, None
            
        except Exception as e:
            print(f"[WARNING] Distribution shift detection failed: {e}")
            return False, None
    
    def _validate_feature_compatibility(
        self,
        current_features: list,
        metadata: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Feature 호환성 검증
        
        Args:
            current_features: 현재 데이터의 Feature 목록
            metadata: 저장된 모델 메타데이터
        
        Returns:
            (호환 여부, 오류 메시지)
        """
        if 'feature_cols' not in metadata:
            # 구 버전 모델 (Feature 정보 없음)
            return False, "구 버전 모델입니다. 전체 재학습이 필요합니다."
        
        saved_features = set(metadata['feature_cols'])
        current_features_set = set(current_features)
        
        if saved_features != current_features_set:
            added = current_features_set - saved_features
            removed = saved_features - current_features_set
            
            error_msg = "Feature 불일치가 감지되었습니다.\n"
            if added:
                error_msg += f"  - 추가된 Feature: {added}\n"
            if removed:
                error_msg += f"  - 제거된 Feature: {removed}\n"
            error_msg += "전체 재학습이 필요합니다."
            
            return False, error_msg
        
        return True, None
    
    def create_replay_buffer(
        self,
        old_data: pd.DataFrame,
        new_data: pd.DataFrame,
        replay_ratio: float = 0.1
    ) -> pd.DataFrame:
        """
        Replay Buffer 생성: Recent 50% + Random 50% 하이브리드
        
        Args:
            old_data: 전체 과거 데이터
            new_data: 신규 데이터
            replay_ratio: Replay Buffer 비율 (기본 10%)
        
        Returns:
            Replay용 데이터
        """
        n_old = len(old_data)
        n_replay = int(n_old * replay_ratio)
        
        if n_replay < 1:
            return pd.DataFrame()
        
        # 최근 50% (시계열 특성 유지)
        n_recent = max(1, n_replay // 2)
        recent_sample = old_data.tail(n_recent)
        
        # 무작위 50% (과거 다양성 보장)
        n_random = max(0, n_replay - n_recent)
        if n_random > 0:
            random_sample = old_data.sample(n=min(n_random, len(old_data)), random_state=42)
            replay_buffer = pd.concat([recent_sample, random_sample]).drop_duplicates()
        else:
            replay_buffer = recent_sample
        
        # 시간 순 정렬
        if 'date' in replay_buffer.columns:
            replay_buffer = replay_buffer.sort_values('date')
        else:
            replay_buffer = replay_buffer.sort_index()
        
        return replay_buffer
