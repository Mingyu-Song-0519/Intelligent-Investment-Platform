"""
AI 예측 모델 모듈 - LSTM 및 XGBoost 기반 주가 예측
"""
import numpy as np
import pandas as pd
from typing import Tuple, Optional, Dict, Any
from pathlib import Path
import pickle
import sys

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MODEL_CONFIG, MODELS_DIR

# TensorFlow 경고 메시지 억제
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# sklearn 경고 메시지 억제
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='sklearn')

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential, load_model
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("[WARNING] TensorFlow not installed. LSTM model will not be available.")

try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("[WARNING] XGBoost not installed. XGBoost model will not be available.")

from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, mean_squared_error


class DataPreprocessor:
    """데이터 전처리 클래스"""
    
    def __init__(self, sequence_length: int = 60):
        """
        Args:
            sequence_length: LSTM 입력 시퀀스 길이
        """
        self.sequence_length = sequence_length
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.feature_columns = None
    
    def prepare_lstm_data(
        self, 
        df: pd.DataFrame, 
        target_col: str = 'close',
        feature_cols: Optional[list] = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        LSTM 모델용 데이터 준비
        
        Args:
            df: 원본 데이터프레임
            target_col: 예측 대상 컬럼
            feature_cols: 학습에 사용할 컬럼들
            
        Returns:
            (X_train, X_test, y_train, y_test) 튜플
        """
        if feature_cols is None:
            feature_cols = ['close', 'volume', 'rsi', 'macd']
        
        # 사용 가능한 컬럼만 선택
        available_cols = [col for col in feature_cols if col in df.columns]
        self.feature_columns = available_cols
        
        # 결측치 처리
        data = df[available_cols].dropna()
        
        if len(data) < self.sequence_length + 1:
            raise ValueError(f"데이터가 부족합니다. 최소 {self.sequence_length + 1}개 필요.")
        
        # 정규화
        scaled_data = self.scaler.fit_transform(data)
        
        # 시퀀스 생성
        X, y = [], []
        target_idx = available_cols.index(target_col)
        
        for i in range(self.sequence_length, len(scaled_data)):
            X.append(scaled_data[i - self.sequence_length:i])
            y.append(scaled_data[i, target_idx])
        
        X, y = np.array(X), np.array(y)
        
        # Train/Test 분할 (시계열이므로 순서 유지)
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        return X_train, X_test, y_train, y_test
    
    def prepare_classification_data(
        self, 
        df: pd.DataFrame,
        feature_cols: Optional[list] = None,
        lookahead: int = 1
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        분류 모델용 데이터 준비 (다음 날 등락 예측)
        
        Args:
            df: 원본 데이터프레임
            feature_cols: 학습에 사용할 컬럼들
            lookahead: 예측 기간 (기본값: 1일 후)
            
        Returns:
            (X_train, X_test, y_train, y_test) 튜플
        """
        if feature_cols is None:
            feature_cols = ['close', 'volume', 'rsi', 'macd', 'bb_percent']
        
        # 사용 가능한 컬럼만 선택
        available_cols = [col for col in feature_cols if col in df.columns]
        self.feature_columns = available_cols
        
        data = df.copy()
        
        # 레이블 생성: 다음 날 상승(1) / 하락(0)
        data['target'] = (data['close'].shift(-lookahead) > data['close']).astype(int)
        
        # 결측치 제거
        data = data.dropna()
        
        X = data[available_cols].values
        y = data['target'].values
        
        # 정규화
        X = self.scaler.fit_transform(X)
        
        # Train/Test 분할
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, shuffle=False
        )
        
        return X_train, X_test, y_train, y_test
    
    def inverse_transform(self, scaled_data: np.ndarray) -> np.ndarray:
        """정규화된 데이터를 원래 스케일로 복원"""
        if len(scaled_data.shape) == 1:
            # 단일 컬럼인 경우
            dummy = np.zeros((len(scaled_data), len(self.feature_columns)))
            dummy[:, 0] = scaled_data
            return self.scaler.inverse_transform(dummy)[:, 0]
        return self.scaler.inverse_transform(scaled_data)


class LSTMPredictor:
    """LSTM 기반 주가 예측 모델"""
    
    def __init__(self, sequence_length: int = None):
        """
        Args:
            sequence_length: 입력 시퀀스 길이
        """
        if not TENSORFLOW_AVAILABLE:
            raise ImportError("TensorFlow가 설치되어 있지 않습니다.")
        
        config = MODEL_CONFIG['LSTM']
        self.sequence_length = sequence_length or config['sequence_length']
        self.units = config['units']
        self.dropout = config['dropout']
        self.epochs = config['epochs']
        self.batch_size = config['batch_size']
        self.model = None
        self.preprocessor = DataPreprocessor(self.sequence_length)
    
    def build_model(self, input_shape: Tuple[int, int]) -> Sequential:
        """LSTM 모델 구축"""
        model = Sequential([
            LSTM(self.units[0], return_sequences=True, input_shape=input_shape),
            Dropout(self.dropout),
            LSTM(self.units[1], return_sequences=True),
            Dropout(self.dropout),
            LSTM(self.units[2], return_sequences=False),
            Dropout(self.dropout),
            Dense(25, activation='relu'),
            Dense(1)
        ])
        
        model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        return model
    
    def train(
        self, 
        df: pd.DataFrame,
        target_col: str = 'close',
        feature_cols: Optional[list] = None,
        verbose: int = 1
    ) -> Dict[str, Any]:
        """
        모델 학습
        
        Args:
            df: 학습 데이터
            target_col: 예측 대상 컬럼
            feature_cols: 특성 컬럼들
            verbose: 출력 레벨
            
        Returns:
            학습 결과 딕셔너리
        """
        # 데이터 준비
        X_train, X_test, y_train, y_test = self.preprocessor.prepare_lstm_data(
            df, target_col, feature_cols
        )
        
        # 모델 구축
        input_shape = (X_train.shape[1], X_train.shape[2])
        self.model = self.build_model(input_shape)
        
        # 콜백 설정
        callbacks = [
            EarlyStopping(
                monitor='val_loss', 
                patience=10, 
                restore_best_weights=True
            ),
        ]
        
        # 학습
        history = self.model.fit(
            X_train, y_train,
            epochs=self.epochs,
            batch_size=self.batch_size,
            validation_data=(X_test, y_test),
            callbacks=callbacks,
            verbose=verbose
        )
        
        # 평가
        y_pred = self.model.predict(X_test, verbose=0)
        
        # 스케일 복원
        y_test_actual = self.preprocessor.inverse_transform(y_test)
        y_pred_actual = self.preprocessor.inverse_transform(y_pred.flatten())
        
        rmse = np.sqrt(mean_squared_error(y_test_actual, y_pred_actual))
        
        return {
            'history': history.history,
            'rmse': rmse,
            'y_test': y_test_actual,
            'y_pred': y_pred_actual
        }
    
    def predict(self, df: pd.DataFrame, feature_cols: Optional[list] = None) -> np.ndarray:
        """예측 수행"""
        if self.model is None:
            raise ValueError("모델이 학습되지 않았습니다.")
        
        feature_cols = feature_cols or self.preprocessor.feature_columns
        available_cols = [col for col in feature_cols if col in df.columns]
        
        data = df[available_cols].dropna().tail(self.sequence_length).values
        scaled_data = self.preprocessor.scaler.transform(data)
        
        X = scaled_data.reshape(1, self.sequence_length, -1)
        prediction = self.model.predict(X, verbose=0)
        
        return self.preprocessor.inverse_transform(prediction.flatten())
    
    def save(self, name: str = 'lstm_model'):
        """
        모델 저장
        
        Args:
            name: 모델 파일명 또는 절대 경로
        """
        if self.model is None:
            raise ValueError("저장할 모델이 없습니다.")
        
        path_obj = Path(name)
        # 절대 경로이거나 부모 디렉토리가 존재하면 그대로 사용
        if path_obj.is_absolute() or path_obj.parent.exists():
            model_path = path_obj.with_suffix('.keras')
            scaler_path = path_obj.parent / f"{path_obj.stem}_scaler.pkl"
            feature_path = path_obj.parent / f"{path_obj.stem}_features.pkl"
            # 디렉토리가 없으면 생성
            model_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            model_path = MODELS_DIR / f"{name}.keras"
            scaler_path = MODELS_DIR / f"{name}_scaler.pkl"
            feature_path = MODELS_DIR / f"{name}_features.pkl"
            MODELS_DIR.mkdir(parents=True, exist_ok=True)
        
        self.model.save(model_path)
        with open(scaler_path, 'wb') as f:
            pickle.dump(self.preprocessor.scaler, f)
        with open(feature_path, 'wb') as f:
            pickle.dump(self.preprocessor.feature_columns, f)
        
        print(f"[INFO] 모델 저장 완료: {model_path}")
    
    def load(self, name: str = 'lstm_model'):
        """모델 로드"""
        path_obj = Path(name)
        # 절대 경로이거나 부모 디렉토리가 존재하면 그대로 사용
        if path_obj.is_absolute() or path_obj.parent.exists():
            model_path = path_obj.with_suffix('.keras')
            scaler_path = path_obj.parent / f"{path_obj.stem}_scaler.pkl"
            feature_path = path_obj.parent / f"{path_obj.stem}_features.pkl"
        else:
            model_path = MODELS_DIR / f"{name}.keras"
            scaler_path = MODELS_DIR / f"{name}_scaler.pkl"
            feature_path = MODELS_DIR / f"{name}_features.pkl"
        
        if not model_path.exists():
            raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {model_path}")
            
        self.model = load_model(model_path)
        with open(scaler_path, 'rb') as f:
            self.preprocessor.scaler = pickle.load(f)
        
        # feature_columns 로드 (파일이 있는 경우)
        if feature_path.exists():
            with open(feature_path, 'rb') as f:
                self.preprocessor.feature_columns = pickle.load(f)
        else:
            # 기본 feature columns 사용
            self.preprocessor.feature_columns = ['close', 'volume', 'rsi', 'macd', 'ma5', 'ma20']
            
        # [중요] 모델의 실제 입력 형태와 Feature 개수 일치 보장
        # 파일에서 로드했더라도 모델과 다를 수 있으므로 검증 필수
        try:
            if hasattr(self.model, 'input_shape'):
                # model.input_shape는 (None, seq_len, n_features) 형태
                n_features_model = self.model.input_shape[-1]
                n_features_cols = len(self.preprocessor.feature_columns)
                
                if n_features_model != n_features_cols:
                    print(f"[WARNING] Feature 불일치 감지! 모델: {n_features_model}, 설정값: {n_features_cols}")
                    
                    # 1. 모델이 더 적은 경우 -> 잘라내기
                    if n_features_model < n_features_cols:
                        self.preprocessor.feature_columns = self.preprocessor.feature_columns[:n_features_model]
                        print(f"[INFO] Feature 자동 축소: {self.preprocessor.feature_columns}")
                    
                    # 2. 모델이 더 많은 경우 -> 기본값에서 추가 (또는 패딩 처리 필요하지만 여기선 경고만)
                    else:
                        st.warning(f"모델이 더 많은 Feature({n_features_model})를 요구합니다. 재학습이 권장됩니다.")
                        # 임시로 기본 컬럼에서 모자란 만큼 채워넣기 시도 (위험하지만 에러 방지용)
                        default_pool = ['close', 'volume', 'rsi', 'macd', 'ma5', 'ma20', 'ma60', 'ma120']
                        current = self.preprocessor.feature_columns
                        for col in default_pool:
                            if col not in current and len(current) < n_features_model:
                                current.append(col)
                        self.preprocessor.feature_columns = current
                        
        except Exception as e:
            print(f"[WARNING] Feature 자동 조정 중 오류: {e}")
        
        print(f"[INFO] 모델 로드 완료: {model_path}")
    



class XGBoostClassifier:
    """XGBoost 기반 등락 예측 모델"""
    
    def __init__(self):
        if not XGBOOST_AVAILABLE:
            raise ImportError("XGBoost가 설치되어 있지 않습니다.")
        
        config = MODEL_CONFIG['XGBOOST']
        self.model = XGBClassifier(
            n_estimators=config['n_estimators'],
            max_depth=config['max_depth'],
            learning_rate=config['learning_rate'],
            objective=config['objective'],
            use_label_encoder=False,
            eval_metric='logloss'
        )
        self.preprocessor = DataPreprocessor()
    
    def train(
        self, 
        df: pd.DataFrame,
        feature_cols: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        모델 학습
        
        Returns:
            학습 결과 딕셔너리
        """
        X_train, X_test, y_train, y_test = self.preprocessor.prepare_classification_data(
            df, feature_cols
        )
        
        self.model.fit(X_train, y_train)
        
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, output_dict=True)
        
        return {
            'accuracy': accuracy,
            'report': report,
            'feature_importance': dict(zip(
                self.preprocessor.feature_columns,
                self.model.feature_importances_
            ))
        }
    
    def predict(self, df: pd.DataFrame) -> Tuple[int, float]:
        """
        다음 날 등락 예측
        
        Returns:
            (예측 클래스, 확률) 튜플
        """
        feature_cols = self.preprocessor.feature_columns
        available_cols = [col for col in feature_cols if col in df.columns]
        
        X = df[available_cols].iloc[-1:].values
        X_scaled = self.preprocessor.scaler.transform(X)
        
        prediction = self.model.predict(X_scaled)[0]
        probability = self.model.predict_proba(X_scaled)[0]
        
        return prediction, probability[prediction]
    
    def save(self, name: str = 'xgboost_model'):
        """모델 저장"""
        path_obj = Path(name)
        # 절대 경로이거나 부모 디렉토리가 존재하면 그대로 사용
        if path_obj.is_absolute() or path_obj.parent.exists():
            model_path = path_obj.with_suffix('.pkl')
            scaler_path = path_obj.parent / f"{path_obj.stem}_scaler.pkl"
            feature_path = path_obj.parent / f"{path_obj.stem}_features.pkl"
            # 디렉토리가 없으면 생성
            model_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            model_path = MODELS_DIR / f"{name}.pkl"
            scaler_path = MODELS_DIR / f"{name}_scaler.pkl"
            feature_path = MODELS_DIR / f"{name}_features.pkl"
            MODELS_DIR.mkdir(parents=True, exist_ok=True)
            
        with open(model_path, 'wb') as f:
            pickle.dump(self.model, f)
        with open(scaler_path, 'wb') as f:
            pickle.dump(self.preprocessor.scaler, f)
        with open(feature_path, 'wb') as f:
            pickle.dump(self.preprocessor.feature_columns, f)
        
        print(f"[INFO] 모델 저장 완료: {model_path}")

    def load(self, name: str = 'xgboost_model'):
        """모델 로드"""
        path_obj = Path(name)
        if path_obj.is_absolute() or path_obj.parent.exists():
            model_path = path_obj.with_suffix('.pkl')
            scaler_path = path_obj.parent / f"{path_obj.stem}_scaler.pkl"
            feature_path = path_obj.parent / f"{path_obj.stem}_features.pkl"
        else:
            model_path = MODELS_DIR / f"{name}.pkl"
            scaler_path = MODELS_DIR / f"{name}_scaler.pkl"
            feature_path = MODELS_DIR / f"{name}_features.pkl"
        
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)
        with open(scaler_path, 'rb') as f:
            self.preprocessor.scaler = pickle.load(f)
        # feature_columns 로드
        if feature_path.exists():
            with open(feature_path, 'rb') as f:
                self.preprocessor.feature_columns = pickle.load(f)
        
        print(f"[INFO] 모델 로드 완료: {model_path}")


# 사용 예시
if __name__ == "__main__":
    print("=== AI 예측 모델 테스트 ===\n")
    
    # 샘플 데이터 로드
    import yfinance as yf
    from src.analyzers.technical_analyzer import TechnicalAnalyzer
    
    ticker = yf.Ticker("005930.KS")
    df = ticker.history(period="2y")
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    df = df.reset_index()
    
    # 기술적 지표 추가
    analyzer = TechnicalAnalyzer(df)
    analyzer.add_all_indicators()
    df = analyzer.get_dataframe()
    
    # XGBoost 분류 모델 테스트
    if XGBOOST_AVAILABLE:
        print("--- XGBoost 등락 예측 모델 ---")
        xgb_model = XGBoostClassifier()
        result = xgb_model.train(df)
        print(f"정확도: {result['accuracy']:.2%}")
        print(f"특성 중요도: {result['feature_importance']}")
