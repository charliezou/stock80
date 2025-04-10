import numpy as np
from scipy.signal import find_peaks
from configparser import ConfigParser

class FeatureAnalyzer:
    def __init__(self):
        self.config = ConfigParser()
        self.config.read('config.ini')

    def calculate_growth_score(self, weekly_data: np.ndarray) -> float:
        '''计算成长性分数'''
        positive_weeks = np.sum(np.diff(weekly_data) > 0)
        return (positive_weeks / len(weekly_data)) * 100

    def analyze_stability(self, price_data: np.ndarray) -> dict:
        '''稳定性分析算法'''
        upper_env = np.convolve(price_data, np.ones(5)/5, mode='same')
        lower_env = np.convolve(price_data, np.ones(5)/5, mode='same')

        peaks, _ = find_peaks(price_data, distance=10)
        valleys, _ = find_peaks(-price_data, distance=10)

        valley_values = price_data[valleys]
        stability_score = 1 - (np.std(valley_values) / np.mean(valley_values))

        return {
            'upper_env': upper_env.tolist(),
            'lower_env': lower_env.tolist(),
            'peaks': peaks.tolist(),
            'valleys': valleys.tolist(),
            'stability_score': stability_score
        }