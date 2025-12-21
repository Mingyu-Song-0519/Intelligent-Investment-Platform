"""
Transformer 기반 주가 예측 모델
시계열 데이터에 특화된 Self-Attention 메커니즘 활용
"""
import numpy as np
import pandas as pd
from typing import Optional, Tuple, Dict
import logging

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.preprocessing import MinMaxScaler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TransformerBlock(layers.Layer):
    """Transformer 블록 (Multi-Head Attention + Feed Forward)"""
    
    def __init__(self, embed_dim: int, num_heads: int, ff_dim: int, dropout_rate: float = 0.1):
        super().__init__()
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.ff_dim = ff_dim
        self.dropout_rate = dropout_rate
        
        self.att = layers.MultiHeadAttention(num_heads=num_heads, key_dim=embed_dim)
        self.ffn = keras.Sequential([
            layers.Dense(ff_dim, activation="relu"),
            layers.Dense(embed_dim),
        ])
        self.layernorm1 = layers.LayerNormalization(epsilon=1e-6)
        self.layernorm2 = layers.LayerNormalization(epsilon=1e-6)
        self.dropout1 = layers.Dropout(dropout_rate)
        self.dropout2 = layers.Dropout(dropout_rate)
    
    def call(self, inputs, training=False):
        # Multi-Head Self-Attention
        attn_output = self.att(inputs, inputs)
        attn_output = self.dropout1(attn_output, training=training)
        out1 = self.layernorm1(inputs + attn_output)
        
        # Feed Forward Network
        ffn_output = self.ffn(out1)
        ffn_output = self.dropout2(ffn_output, training=training)
        return self.layernorm2(out1 + ffn_output)
    
    def get_config(self):
        config = super().get_config()
        config.update({
            "embed_dim": self.embed_dim,
            "num_heads": self.num_heads,
            "ff_dim": self.ff_dim,
            "dropout_rate": self.dropout_rate,
        })
        return config


class PositionalEncoding(layers.Layer):
    """시계열 데이터를 위한 Positional Encoding"""
    
    def __init__(self, max_len: int = 100, embed_dim: int = 64):
        super().__init__()
        self.max_len = max_len
        self.embed_dim = embed_dim
        
        # Positional encoding 계산
        position = np.arange(max_len)[:, np.newaxis]
        div_term = np.exp(np.arange(0, embed_dim, 2) * -(np.log(10000.0) / embed_dim))
        
        pe = np.zeros((max_len, embed_dim))
        pe[:, 0::2] = np.sin(position * div_term)
        pe[:, 1::2] = np.cos(position * div_term)
        
        self.pos_encoding = tf.constant(pe, dtype=tf.float32)
    
    def call(self, x):
        seq_len = tf.shape(x)[1]
        return x + self.pos_encoding[:seq_len, :]
    
    def get_config(self):
        config = super().get_config()
        config.update({
            "max_len": self.max_len,
            "embed_dim": self.embed_dim,
        })
        return config


class TransformerPredictor:
    """Transformer 기반 주가 예측기"""
    
    def __init__(
        self,
        sequence_length: int = 30,
        embed_dim: int = 64,
        num_heads: int = 4,
        ff_dim: int = 128,
        num_transformer_blocks: int = 2,
        dropout_rate: float = 0.1,
        learning_rate: float = 1e-4
    ):
        self.sequence_length = sequence_length
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.ff_dim = ff_dim
        self.num_transformer_blocks = num_transformer_blocks
        self.dropout_rate = dropout_rate
        self.learning_rate = learning_rate
        
        self.model: Optional[keras.Model] = None
        self.scaler_X = MinMaxScaler()
        self.scaler_y = MinMaxScaler()
        self.feature_columns = []
        self.is_trained = False
    
    def _build_model(self, input_shape: Tuple[int, int]) -> keras.Model:
        """Transformer 모델 구축"""
        inputs = layers.Input(shape=input_shape)
        
        # 입력 임베딩 (선형 변환)
        x = layers.Dense(self.embed_dim)(inputs)
        
        # Positional Encoding
        x = PositionalEncoding(max_len=input_shape[0], embed_dim=self.embed_dim)(x)
        
        # Transformer Blocks
        for _ in range(self.num_transformer_blocks):
            x = TransformerBlock(
                embed_dim=self.embed_dim,
                num_heads=self.num_heads,
                ff_dim=self.ff_dim,
                dropout_rate=self.dropout_rate
            )(x)
        
        # Global Average Pooling
        x = layers.GlobalAveragePooling1D()(x)
        
        # Dense layers
        x = layers.Dense(64, activation="relu")(x)
        x = layers.Dropout(self.dropout_rate)(x)
        x = layers.Dense(32, activation="relu")(x)
        
        # 출력층 (다음 날 종가 예측)
        outputs = layers.Dense(1)(x)
        
        model = keras.Model(inputs=inputs, outputs=outputs)
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=self.learning_rate),
            loss="mse",
            metrics=["mae"]
        )
        
        return model
    
    def prepare_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """데이터 전처리 및 시퀀스 생성"""
        # 특성 선택
        feature_cols = ['open', 'high', 'low', 'close', 'volume']
        
        # 기술적 지표가 있으면 추가
        for col in ['rsi', 'macd', 'macd_signal', 'sma_20', 'sma_50', 'bb_upper', 'bb_lower']:
            if col in df.columns:
                feature_cols.append(col)
        
        self.feature_columns = feature_cols
        
        # 결측치 제거
        data = df[feature_cols].dropna()
        
        if len(data) < self.sequence_length + 1:
            raise ValueError(f"데이터가 부족합니다. 최소 {self.sequence_length + 1}개 필요")
        
        # 정규화
        X_scaled = self.scaler_X.fit_transform(data.values)
        y_scaled = self.scaler_y.fit_transform(data['close'].values.reshape(-1, 1))
        
        # 시퀀스 생성
        X, y = [], []
        for i in range(len(X_scaled) - self.sequence_length):
            X.append(X_scaled[i:i + self.sequence_length])
            y.append(y_scaled[i + self.sequence_length])
        
        return np.array(X), np.array(y)
    
    def train(
        self,
        df: pd.DataFrame,
        epochs: int = 50,
        batch_size: int = 32,
        validation_split: float = 0.2,
        verbose: int = 1
    ) -> Dict:
        """모델 학습"""
        # 이전 세션 클리어 (메모리 누수 방지)
        keras.backend.clear_session()
        
        logger.info("Transformer 모델 학습 시작...")
        
        X, y = self.prepare_data(df)
        
        # 모델 구축
        self.model = self._build_model(input_shape=(X.shape[1], X.shape[2]))
        
        # Early Stopping
        early_stop = keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True
        )
        
        # 학습
        history = self.model.fit(
            X, y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            callbacks=[early_stop],
            verbose=verbose
        )
        
        self.is_trained = True
        logger.info("Transformer 모델 학습 완료")
        
        return {
            'train_loss': history.history['loss'][-1],
            'val_loss': history.history['val_loss'][-1],
            'epochs_trained': len(history.history['loss'])
        }
    
    def predict(self, df: pd.DataFrame) -> float:
        """다음 날 종가 예측"""
        if not self.is_trained or self.model is None:
            raise ValueError("모델이 학습되지 않았습니다")
        
        # 마지막 시퀀스 추출
        data = df[self.feature_columns].dropna().values
        
        if len(data) < self.sequence_length:
            raise ValueError(f"예측에 필요한 데이터가 부족합니다. 최소 {self.sequence_length}개 필요")
        
        # 마지막 sequence_length개 데이터 사용
        last_sequence = data[-self.sequence_length:]
        last_sequence_scaled = self.scaler_X.transform(last_sequence)
        
        # 예측
        X_pred = last_sequence_scaled.reshape(1, self.sequence_length, -1)
        y_pred_scaled = self.model.predict(X_pred, verbose=0)
        
        # 역정규화
        y_pred = self.scaler_y.inverse_transform(y_pred_scaled)
        predicted_price = float(y_pred[0, 0])
        
        # 예측값 클리핑 (전일 종가 대비 ±30% 제한 - 한국 시장 기준)
        current_price = df['close'].iloc[-1]
        max_price = current_price * 1.30
        min_price = current_price * 0.70
        
        if predicted_price > max_price:
            predicted_price = max_price
        elif predicted_price < min_price:
            predicted_price = min_price
            
        return predicted_price
    
    def predict_direction(self, df: pd.DataFrame) -> Dict:
        """방향 예측 (상승/하락)"""
        current_price = df['close'].iloc[-1]
        predicted_price = self.predict(df)
        
        direction = 'up' if predicted_price > current_price else 'down'
        change_pct = (predicted_price - current_price) / current_price * 100
        
        # 신뢰도 계산 개선
        # 1. 변동폭이 너무 크면(>15%) 이상치로 판단하여 신뢰도 감소
        # 2. 변동폭이 너무 작으면(<0.5%) 방향성 불확실하여 신뢰도 감소
        abs_change = abs(change_pct)
        
        if abs_change > 15.0:
            confidence = max(0.1, 1.0 - (abs_change - 15.0) / 10.0) # 15% 초과시 감소
        elif abs_change < 0.5:
            confidence = 0.5 + abs_change # 0.5~0.55
        else:
            # 0.5% ~ 15% 구간: 변동폭이 클수록 신뢰도 증가 (최대 0.9)
            confidence = 0.5 + min(abs_change / 30.0, 0.4)
            
        return {
            'direction': direction,
            'predicted_price': predicted_price,
            'current_price': current_price,
            'change_pct': change_pct,
            'confidence': confidence
        }
    
    def save_model(self, path: str):
        """모델 및 스케일러 저장"""
        if self.model is not None:
            from pathlib import Path
            # 확장자 분리
            base_path = path.rsplit('.', 1)[0]
            
            # 디렉토리가 없으면 생성
            path_obj = Path(base_path)
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Keras 모델 저장
            self.model.save(f"{base_path}.keras")
            
            # Scaler 저장
            import joblib
            joblib.dump(self.scaler_X, f"{base_path}_scaler_X.pkl")
            joblib.dump(self.scaler_y, f"{base_path}_scaler_y.pkl")
            
            logger.info(f"모델 및 스케일러 저장 완료: {base_path}")
    
    def load_model(self, path: str):
        """모델 및 스케일러 로드"""
        base_path = path.rsplit('.', 1)[0]
        
        # Keras 모델 로드
        self.model = keras.models.load_model(
            f"{base_path}.keras",
            custom_objects={
                'TransformerBlock': TransformerBlock,
                'PositionalEncoding': PositionalEncoding
            }
        )
        
        # Scaler 로드
        import joblib
        try:
            self.scaler_X = joblib.load(f"{base_path}_scaler_X.pkl")
            self.scaler_y = joblib.load(f"{base_path}_scaler_y.pkl")
            self.is_trained = True
            logger.info(f"모델 및 스케일러 로드 완료: {base_path}")
        except Exception as e:
            logger.warning(f"스케일러 로드 실패: {e}")
            self.is_trained = False


# 테스트
if __name__ == "__main__":
    # 샘플 데이터 생성
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=200, freq='D')
    df = pd.DataFrame({
        'date': dates,
        'open': np.random.randn(200).cumsum() + 100,
        'high': np.random.randn(200).cumsum() + 102,
        'low': np.random.randn(200).cumsum() + 98,
        'close': np.random.randn(200).cumsum() + 100,
        'volume': np.random.randint(1000000, 10000000, 200)
    })
    
    # 모델 학습
    predictor = TransformerPredictor(sequence_length=30)
    result = predictor.train(df, epochs=10, verbose=1)
    print(f"학습 결과: {result}")
    
    # 예측
    predicted = predictor.predict(df)
    print(f"예측 종가: {predicted:,.2f}")
    
    direction = predictor.predict_direction(df)
    print(f"방향 예측: {direction}")
