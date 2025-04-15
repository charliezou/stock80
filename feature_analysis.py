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

        return filtered

    def find_peaks_in_envelope(self,envelope, distance=5, low_rate=0.05):
        peaks, properties = find_peaks(
            envelope,
            prominence = 0.01,
            distance=distance
        )
        #过滤涨幅低于5%的波峰
        peaks = peaks[properties["prominences"] > (envelope[peaks] * low_rate)]
        
        # 寻找波谷
        valleys = np.asarray([np.argmin(envelope[peaks[i-1]:peaks[i]]) + peaks[i-1] for i in range(1, len(peaks))])
        
        valley_begin = np.argmin(envelope[:peaks[0]])
        valley_end = np.argmin(envelope[peaks[-1]:]) + peaks[-1]
        if envelope[valley_begin] <= envelope[peaks[0]] * (1-low_rate):
            valleys = np.append(np.asarray([valley_begin]), valleys)
        if envelope[valley_end] <= envelope[peaks[-1]] * (1-low_rate):
            valleys = np.append(valleys, np.asarray([valley_end]))
        valleys = np.int16(valleys)

        # 计算波峰和波谷的涨跌幅
        if peaks[0] > valleys[0]:
            peaks_rate = np.asarray([envelope[peaks[i]]/envelope[valleys[i]]-1 for i in range(len(peaks))])
        else:
            peaks_rate = np.append(np.asarray([0.0]), np.asarray([envelope[peaks[i]]/envelope[valleys[i-1]]-1 for i in range(1, len(peaks))]))
        if peaks[0] < valleys[0]:
            valleys_rate = np.asarray([envelope[valleys[i]]/envelope[peaks[i]]-1 for i in range(len(peaks))])
        else:
            valleys_rate = np.append(np.asarray([0.0]), np.asarray([envelope[valleys[i]]/envelope[peaks[i-1]]-1 for i in range(1, len(valleys))]))

        return peaks, valleys, peaks_rate, valleys_rate

    def calculate_growth_score(self, weekly_data: np.ndarray) -> float:
        '''计算成长性分数'''
        positive_weeks = np.sum(np.diff(weekly_data) > 0)
        return (positive_weeks / len(weekly_data)) * 100

    def analyze_stability(self, price_data: np.ndarray) -> dict:
        '''稳定性分析算法'''
        envelope = self.extract_hilbert_envelope(price_data)
        peaks, valleys, peaks_rate, valleys_rate = self.find_peaks_in_envelope(envelope)

        #peaks, _ = find_peaks(price_data, distance=10)
        #valleys, _ = find_peaks(-price_data, distance=10)

        valley_values = envelope[valleys]
        stability_score = 1 - (np.std(valley_values) / np.mean(valley_values))

        return {
            'filtered': envelope.tolist(),
            'peaks': peaks.tolist(),
            'valleys': valleys.tolist(),
            'stability_score': stability_score
        }