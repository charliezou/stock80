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
        self.low_rate = self.config.getfloat('envelope', 'low_rate', fallback=0.10)

    def extract_hilbert_envelope(self, price_data: np.ndarray):
        """使用希尔伯特变换提取包络线"""
        # 设计低通滤波器
        b, a = butter(self.filter_order, self.cutoff_freq, btype='low')
        
        # 零相位滤波
        envelope = filtfilt(b, a, price_data)

        return envelope

    def find_extrema_in_envelope(self, envelope, distance=4, low_rate=None):
        if low_rate is None:
            low_rate = self.low_rate
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

        return {
            'peaks':peaks, 
            'valleys':valleys,
            
        }

    def calculate_growth_score(self, envelope, peaks, valleys):
        #计算成长性分数
        envelope_len = len(envelope)        
        k=np.append(peaks,valleys)
        k.sort()
        if (k[0] != 0):
            k = np.append(np.asarray([0]),k)
        if (k[-1] != envelope_len-1):
            k = np.append(k, np.asarray([envelope_len-1]))

        print(k)
        
        #计算波峰和波谷的周期长度
        if (peaks[0] == k[1]):
            peaks_len = [k[i]-k[i-1] for i in range(1, len(k) , 2)]
            valleys_len = [k[i]-k[i-1] for i in range(2, len(k), 2)]
        else:
            peaks_len = [k[i]-k[i-1] for i in range(2, len(k) , 2)]
            valleys_len = [k[i]-k[i-1] for i in range(1, len(k), 2)]

        # 计算波峰和波谷的价格值
        peaks_values = envelope[peaks]
        valleys_values = envelope[valleys]

        # 计算波峰和波谷的涨跌幅       
        if peaks[0] > valleys[0]:   #波谷在前面
            peaks_rate = np.asarray([envelope[peaks[i]]/envelope[valleys[i]]-1 for i in range(len(peaks))])
            valleys_rate = np.append(np.asarray([envelope[valleys[0]] / np.max(envelope[:valleys[0]])-1]), 
                np.asarray([envelope[valleys[i]]/envelope[peaks[i-1]]-1 for i in range(1, len(valleys))]))
        else:
            peaks_rate = np.append(np.asarray([envelope[peaks[0]] / np.min(envelope[:peaks[0]])-1]), 
                np.asarray([envelope[peaks[i]]/envelope[valleys[i-1]]-1 for i in range(1, len(peaks))]))
            valleys_rate = np.asarray([envelope[valleys[i]]/envelope[peaks[i]]-1 for i in range(len(valleys))])

        return {
            'growth_score': (np.sum(peaks_len) / envelope_len) * 100,
            'peaks_values':peaks_values,
            'valleys_values':valleys_values,
            'peaks_rate':peaks_rate,
            'valleys_rate':valleys_rate,
            'peaks_len':peaks_len,
            'peaks_avg_len':np.mean(peaks_len),
            'peaks_std_len':np.std(peaks_len),
            'valleys_len':valleys_len,
            'valleys_avg_len':np.mean(valleys_len),
            'valleys_std_len':np.std(valleys_len)
        }

    def calculate_growth_score_v2(self, envelope, peaks, valleys, years_list):
        #计算成长性分数

        envelope_len = len(envelope) 

        k=np.append(peaks,valleys)
        k.sort()
        if (k[0] != 0):
            k = np.append(np.asarray([0]),k)
        if (k[-1] != envelope_len-1):
            k = np.append(k, np.asarray([envelope_len-1]))
      
        #计算波峰和波谷的周期长度
        if (peaks[0] == k[1]):
            peaks_len = [k[i]-k[i-1] for i in range(1, len(k) , 2)]
            valleys_len = [k[i]-k[i-1] for i in range(2, len(k), 2)]
        else:
            peaks_len = [k[i]-k[i-1] for i in range(2, len(k) , 2)]
            valleys_len = [k[i]-k[i-1] for i in range(1, len(k), 2)]

        indicator = np.asarray([0] * envelope_len)
        if (peaks[0] == k[1]):
            for i in range(1, len(k), 2):
                indicator[k[i-1]:k[i]] = 1
        else:
            for i in range(2, len(k), 2):
                indicator[k[i-1]:k[i]] = 1

        growth_scores = []
        for years in years_list:
            period_indicator = indicator[-52*years:]
            if len(period_indicator) < 52*years:
                break
            growth_scores.append((years,np.sum(period_indicator) / len(period_indicator)))

        
        # 计算波峰和波谷的价格值
        peaks_values = envelope[peaks]
        valleys_values = envelope[valleys]

        # 计算波峰和波谷的涨跌幅       
        if peaks[0] > valleys[0]:   #波谷在前面
            peaks_rate = np.asarray([envelope[peaks[i]]/envelope[valleys[i]]-1 for i in range(len(peaks))])
            valleys_rate = np.append(np.asarray([envelope[valleys[0]] / np.max(envelope[:valleys[0]])-1]), 
                np.asarray([envelope[valleys[i]]/envelope[peaks[i-1]]-1 for i in range(1, len(valleys))]))
        else:
            peaks_rate = np.append(np.asarray([envelope[peaks[0]] / np.min(envelope[:peaks[0]])-1]), 
                np.asarray([envelope[peaks[i]]/envelope[valleys[i-1]]-1 for i in range(1, len(peaks))]))
            valleys_rate = np.asarray([envelope[valleys[i]]/envelope[peaks[i]]-1 for i in range(len(valleys))])

        return {
            'growth_score': (np.sum(peaks_len) / envelope_len) * 100,
            'growth_scores':growth_scores,
            'peaks_values':peaks_values,
            'valleys_values':valleys_values,
            'peaks_rate':peaks_rate,
            'valleys_rate':valleys_rate,
            'peaks_len':peaks_len,
            'peaks_avg_len':np.mean(peaks_len),
            'peaks_std_len':np.std(peaks_len),
            'valleys_len':valleys_len,
            'valleys_avg_len':np.mean(valleys_len),
            'valleys_std_len':np.std(valleys_len)
        }

    def calculate_annualized_returns(self, prices, years_list):
        returns = []
        for years in years_list:
            period_prices = prices[-52*years:]
            if len(period_prices) < 52*years:
                break
            start_price = period_prices[0]
            end_price = period_prices[-1]
            annualized_return = (end_price/start_price)**(1/years) - 1
            returns.append((years,annualized_return))
        return returns

    def analyze_stability(self, price_data: np.ndarray, years_list) -> dict:
        '''稳定性分析算法'''
        envelope = self.extract_hilbert_envelope(price_data)
        extreme_data = self.find_extrema_in_envelope(envelope)
        growth_data = self.calculate_growth_score_v2(envelope, extreme_data['peaks'], extreme_data['valleys'],years_list)

        return extreme_data | growth_data, envelope

