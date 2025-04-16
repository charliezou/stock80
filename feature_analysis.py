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
        envelope = filtfilt(b, a, price_data)

        return envelope

    def find_extrema_in_envelope(self,envelope, distance=4, low_rate=0.05):
        """在包络线中寻找波峰和波谷"""
        # 寻找波峰
        peaks, properties = find_peaks(
            envelope,
            prominence = 0.01,
            distance=distance
        )  
        #过滤涨幅低于阀值的波峰
        peaks = peaks[properties["prominences"] > (envelope[peaks] * low_rate)]     

        # 寻找波谷
        valleys, properties = find_peaks(
            - envelope + np.max(envelope) + np.min(envelope),
            prominence = 0.01,
            distance=distance
        )       

        #过滤跌幅低于阀值的波谷

        valleys = valleys[properties["prominences"] > (envelope[valleys] * low_rate/(1-low_rate))]

        # 计算波峰和波谷的涨跌幅       
        if peaks[0] > valleys[0]:   #波谷在前面
            peaks_rate = np.asarray([envelope[peaks[i]]/envelope[valleys[i]]-1 for i in range(len(peaks))])
            valleys_rate = np.append(np.asarray([envelope[valleys[0]] / np.max(envelope[:valleys[0]])-1]), 
                np.asarray([envelope[valleys[i]]/envelope[peaks[i-1]]-1 for i in range(1, len(valleys))]))
        else:
            peaks_rate = np.append(np.asarray([envelope[peaks[0]] / np.min(envelope[:peaks[0]])-1]), 
                np.asarray([envelope[peaks[i]]/envelope[valleys[i-1]]-1 for i in range(1, len(peaks))]))
            valleys_rate = np.asarray([envelope[valleys[i]]/envelope[peaks[i]]-1 for i in range(len(valleys))])

        #峰值点
        peaks_values = envelope[peaks]
        valleys_values = envelope[valleys]            

        return {
            'peaks':peaks, 
            'valleys':valleys,
            'peaks_rate':peaks_rate,
            'valleys_rate':valleys_rate,
            'peaks_values':peaks_values,
            'valleys_values':valleys_values
        }

    def calculate_growth_score(self, weekly_data: np.ndarray) -> float:
        '''计算成长性分数'''
        positive_weeks = np.sum(np.diff(weekly_data) > 0)
        return (positive_weeks / (len(weekly_data)-1)) * 100

    def calculate_annualized_returns(self, prices, years_list):
        returns = []
        for years in years_list:
            period_prices = prices[-52*years:]
            if len(period_prices) < 52*years:
                returns.append(None)
                continue
            start_price = period_prices[0]
            end_price = period_prices[-1]
            annualized_return = (end_price/start_price)**(1/years) - 1
            returns.append(annualized_return)
        return returns

    def analyze_stability(self, price_data: np.ndarray) -> dict:
        '''稳定性分析算法'''
        envelope = self.extract_hilbert_envelope(price_data)
        extreme_data = self.find_extrema_in_envelope(envelope)

        #peaks, _ = find_peaks(price_data, distance=10)
        #valleys, _ = find_peaks(-price_data, distance=10)

        valley_values = envelope[extreme_data['valleys']]
        stability_score = 1 - (np.std(valley_values) / np.mean(valley_values))

        return {
            'envelope': envelope.tolist(),
            'peaks': extreme_data['peaks'].tolist(),
            'valleys': extreme_data['valleys'].tolist(),
            'peaks_rate': extreme_data['peaks_rate'].tolist(),
            'valleys_rate': extreme_data['valleys_rate'].tolist(),
            'peaks_values': extreme_data['peaks_values'].tolist(),
            'valleys_values': extreme_data['valleys_values'].tolist(),
            'stability_score': stability_score
        }