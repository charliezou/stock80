import numpy as np
from scipy.signal import find_peaks, hilbert, butter, filtfilt

class UtilsAnalyzer:
    def __init__(self):
        self.config = ConfigParser()
        self.config.read('config.ini')
        # 新增滤波器参数
        self.cutoff_freq = self.config.getfloat('envelope', 'cutoff_freq', fallback=0.12)
        self.filter_order = self.config.getint('envelope', 'filter_order', fallback=5)
        self.distance = self.config.getfloat('envelope', 'distance', fallback=4)
        self.low_rate = self.config.getfloat('envelope', 'low_rate', fallback=0.10)

    def extract_hilbert_envelope(self, data):
        """使用希尔伯特变换提取包络线"""
        # 设计低通滤波器
        b, a = butter(self.filter_order, self.cutoff_freq, btype='low')   
        # 零相位滤波
        envelope = filtfilt(b, a, data)

        return envelope

    def extract_hilbert_envelope_panda(self, prices):
        """使用希尔伯特变换提取包络线"""
        data = prices["Close"].values
        envelope = self.extract_hilbert_envelope(data)
        prices["Envelope"] = envelope
        return prices

    def find_peaks(self, data):
        """使用希尔伯特变换提取包络线"""
        envelope = self.extract_hilbert_envelope(data)

        """在包络线中寻找波峰和波谷"""
        # 寻找波峰
        peaks, properties = find_peaks(
            envelope,
            prominence = 0.01,
            distance=self.distance
        )  
        #过滤涨幅低于阀值的波峰
        peaks = peaks[properties["prominences"] > (envelope[peaks] * self.low_rate)]   

        # 寻找波谷
        valleys, properties = find_peaks(
            - envelope + np.max(envelope) + np.min(envelope),
            prominence = 0.01,
            distance = self.distance
        )       
        #过滤跌幅低于阀值的波谷
        valleys = valleys[properties["prominences"] > (envelope[valleys] * self.low_rate/(1-self.low_rate))]

        return {
            'envelope':envelope,
            'peaks':peaks, 
            'valleys':valleys,      
        }
    
    def find_peaks_panda(self, prices):
        #todo
        return prices
