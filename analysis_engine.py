import numpy as np
from scipy.spatial.distance import euclidean
from fastdtw import fastdtw
from statsmodels.tsa.arima.model import ARIMA

from configparser import ConfigParser

class AnalysisEngine:
    def __init__(self):
        self.config = ConfigParser()
        self.config.read('config.ini')
        self.dtw_radius = self.config.getint('Analysis', 'dtw_radius')

    def _zscore_normalize(self, data: np.ndarray) -> np.ndarray:
        '''数据标准化处理'''
        return (data - np.mean(data)) / np.std(data)

    def find_similar_patterns(self, query_seq: np.ndarray, base_seq: np.ndarray) -> float:
        '''DTW相似度计算'''
        query_norm = self._zscore_normalize(query_seq)
        base_norm = self._zscore_normalize(base_seq)
        distance, _ = fastdtw(query_norm, base_norm, radius=self.dtw_radius, dist=euclidean)
        return distance

    def arima_forecast(self, data: np.ndarray, steps: int = 7) -> np.ndarray:
        '''ARIMA时间序列预测'''
        model = ARIMA(data, order=(2,1,2))
        model_fit = model.fit()
        return model_fit.forecast(steps=steps)

    def validate_prediction(self, full_data: np.ndarray, test_ratio: float = 0.2) -> float:
        '''历史留出法验证'''
        split_idx = int(len(full_data) * (1 - test_ratio))
        train_data = full_data[:split_idx]
        test_data = full_data[split_idx:]

        # 训练预测模型
        predictions = self.arima_forecast(train_data, steps=len(test_data))
        
        # 计算RMSE
        rmse = np.sqrt(np.mean((predictions - test_data)**2))
        return rmse