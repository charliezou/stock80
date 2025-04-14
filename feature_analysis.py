import numpy as np
from scipy.signal import find_peaks, hilbert, butter, filtfilt
from configparser import ConfigParser

class FeatureAnalyzer:
    def __init__(self):
        self.config = ConfigParser()
        self.config.read('config.ini')
        # 新增滤波器参数
        self.cutoff_freq = self.config.getfloat('envelope', 'cutoff_freq', fallback=0.1)
        self.filter_order = self.config.getint('envelope', 'filter_order', fallback=3)

    def extract_hilbert_envelope(self, price_data: np.ndarray) -> dict:
        """使用希尔伯特变换提取包络线"""
        # 设计低通滤波器
        b, a = butter(self.filter_order, self.cutoff_freq, btype='low')
        
        # 零相位滤波
        filtered = filtfilt(b, a, price_data)
        
        # 希尔伯特变换
        analytic_signal = hilbert(filtered)
        amplitude_envelope = np.abs(analytic_signal)
        
        # 计算上下包络
        upper_env = filtered + amplitude_envelope
        lower_env = filtered - amplitude_envelope
        
        return {
            'upper_env': upper_env.tolist(),
            'lower_env': lower_env.tolist(),
            'filtered': filtered.tolist()
        }
    def calculate_growth_score(self, weekly_data: np.ndarray) -> float:
        '''计算成长性分数'''
        positive_weeks = np.sum(np.diff(weekly_data) > 0)
        return (positive_weeks / len(weekly_data)) * 100

    def analyze_stability(self, price_data: np.ndarray) -> dict:
        '''稳定性分析算法'''
        envelope = self.extract_hilbert_envelope(price_data)

        peaks, _ = find_peaks(price_data, distance=10)
        valleys, _ = find_peaks(-price_data, distance=10)

        valley_values = price_data[valleys]
        stability_score = 1 - (np.std(valley_values) / np.mean(valley_values))

        return {
            'upper_env': envelope['upper_env'],
            'lower_env': envelope['lower_env'],
            'filtered': envelope['filtered'],
            'peaks': peaks.tolist(),
            'valleys': valleys.tolist(),
            'stability_score': stability_score
        }