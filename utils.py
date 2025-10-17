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

        self.years_list = [int(y) for y in self.config.get('Returns', 'years', fallback='1,2,3,5,10').split(',')]

    def extract_envelope(self, data):
        """使用希尔伯特变换提取包络线"""
        # 设计低通滤波器
        b, a = butter(self.filter_order, self.cutoff_freq, btype='low')   
        # 零相位滤波
        envelope = filtfilt(b, a, data)

        return envelope

    def find_peaks(self, data):
        """使用希尔伯特变换提取包络线"""
        envelope = self.extract_envelope(data)

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

        peak = np.zeros(len(data))
        peak[peaks] = 1
        peak[valleys] = -1

        #todo 计算波峰和波谷的高度和宽度   

        return {
            'envelope':envelope,
            'peak':peaks, 
        }

    def extract_envelope_panda(self, prices):
        """使用希尔伯特变换提取包络线"""
        data = prices["Close"].values
        envelope = self.extract_envelope(data)
        prices["Envelope"] = envelope
        return prices
    
    def find_peaks_panda(self, prices):
        """使用希尔伯特变换提取包络线和波峰和波谷"""

        data = prices["Close"].values
        result = self.find_peaks(data)
        prices["Envelope"] = result['envelope']
        prices["Peak"] = result['peak']
        return prices

    def annualized_returns(self, data, data_type = 'week'):
        """计算年化收益率"""
        if data_type == 'week':
            period = 52
        elif data_type == 'day':
            period = 252
        elif data_type == 'month':
            period = 12
        else:
            raise ValueError("Invalid data_type. Supported values are 'week', 'day', and 'month'.")
        returns = []
        for years in self.years_list:
            period_prices = prices[-period*years:]
            if len(period_prices) < period*years:
                break
            start_price = period_prices[0]
            end_price = period_prices[-1]
            annualized_return = (end_price/start_price)**(1/years) - 1
            returns.append((years, annualized_return))
        return returns

    def annualized_returns_panda(self, prices, data_type = 'week'):
        """计算年化收益率"""
        return self.annualized_returns(prices['Close'], data_type)

    def growth_scores(self, peaks, data_type = 'week'):
        """计算成长分数,传入peak"""
        if data_type == 'week':
            period = 52
        elif data_type == 'day':
            period = 252
        elif data_type =='month':
            period = 12
        else:
            raise ValueError("Invalid data_type. Supported values are 'week', 'day', and'month'.")

        growth_scores = []

        k = np.where(peaks != 0)
        indicators = np.zeros(len(data))
        if peaks[k[0]] == -1:
            for i in range(1, len(k), 2):
                indicator[k[i-1]:k[i]] = 1
        else:
            for i in range(2, len(k), 2):
                indicator[k[i-1]:k[i]] = 1

        for years in self.years_list:
            period_indicators = indicators[-period*years:]
            if len(period_indicators) < period*years:
                break
            growth_score = np.sum(period_indicators) / period*years
            growth_scores.append((years, growth_score))
        return growth_scores

    def growth_scores_panda(self, prices, data_type = 'week'):
        """计算成长分数,需要先调用find_peaks_panda"""
        if 'Peak' not in prices.columns:
            raise ValueError("Peak column not found in prices DataFrame. Please call find_peaks_panda first.")
        return self.growth_scores(prices['Peak'].values, data_type)

    def normalization(self, data, clip=5.0):
        """数据归一化"""
        x = np.array(data)
        x_mean, x_std = np.mean(x, axis=0), np.std(x, axis=0)
        x = (x - x_mean) / (x_std + 1e-5)
        x = np.clip(x, -clip, clip)

        return x , x_mean, x_std

    def denormalization(self, data, x_mean, x_std):
        """数据反归一化"""
        x = np.array(data)
        x = x * (x_std + 1e-5) + x_mean
        return x

    def normalization_panda(self, prices, clip=5.0):
        """数据归一化"""
        columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        x = prices[columns].values.astype(np.float32)

        x_mean, x_std = np.mean(x, axis=0), np.std(x, axis=0)
        x = (x - x_mean) / (x_std + 1e-5)
        x = np.clip(x, -self.clip, self.clip)
        df = pd.DataFrame(x, columns=columns, index=prices.index)
        return df, x_mean, x_std
        
    def denormalization_panda(self, prices, x_mean, x_std):
        """数据反归一化"""
        columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        x = prices[columns].values.astype(np.float32)
        x = x * (x_std + 1e-5) + x_mean
        df = pd.DataFrame(x, columns=columns, index=prices.index)
        return df







