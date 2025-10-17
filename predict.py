import numpy as np
import pandas as pd
from scipy.spatial.distance import euclidean
from fastdtw import fastdtw
import matplotlib.pyplot as plt
from datetime import datetime

from data_manager import StockDataManager

from configparser import ConfigParser

class Dtw_Predictor:
    def __init__(self, config):
        self.config = ConfigParser()
        self.config.read('config.ini')

        self.dtw_radius = self.config.getint('Analysis', 'dtw_radius', fallback=1)
        self.window_size = self.config.getint('Analysis', 'window_size', fallback=15)
        self.days_to_forecast = self.config.getint('Analysis', 'days_to_forecast', fallback=8)
        self.use_returns = self.config.getboolean('Analysis', 'use_returns', fallback=False)
        self.use_volume = self.config.getboolean('Analysis', 'use_volume', fallback=False)
        self.scale_method = self.config.get('Analysis', 'scale_method', fallback='first')
        self.forecast_cal_method = self.config.get('Analysis', 'forecast_cal_method', fallback='sigmean')
        self.index_distance = self.config.getint('Analysis', 'index_distance', fallback=8)
        self.topn = self.config.getint('Analysis', 'topn', fallback=5)
        self.use_broad_market_index = self.config.getboolean('Analysis', 'use_broad_market_index', fallback=False)

    def scale_series(self, series):
        """对numpy序列进行缩放"""
        if self.scale_method == "minmax":   #适合prices;进行了纵向缩放
            return (series - np.min(series, axis=0)) / (np.max(series,axis=0) - np.min(series,axis=0))
        if self.scale_method == "first":    #适合prices
            return series / series[0]
        if self.scale_method == "mean":     #适合prices
            return series / np.mean(series, axis=0)
        if self.scale_method == "zscore":   #适合prices;进行了纵向缩放
            return np.clip((series - np.mean(series, axis=0)) / (np.std(series, axis=0) + 1e-5), -5, 5)
        if scale_method == "pctchange":   #适合returns
            return np.diff(series, axis=0) / series[:-1]

    def compute_dtw_distance(self, series_a, series_b):
        """计算两个序列之间的DTW距离"""
        scaled_a = self.scale_series(series_a)
        scaled_b = self.scale_series(series_b)
        if scaled_a.ndim == 1:
            scaled_a = scaled_a.reshape(-1, 1)
            scaled_b = scaled_b.reshape(-1, 1)
        distance, _ = fastdtw(scaled_a,
                            scaled_b,
                            radius=self.dtw_radius,
                            dist=euclidean)
        return distance

    def find_patterns(self, prices, symbol):
        """prices, indexs, volumes: panda数据"""  
        price_data = prices["Close"]
        volume_data = prices["Volume"]
        index_series = None
        if self.use_broad_market_index:
            market_data = self.getmarketindex(symbol)                        
            if market_data is not None:
                index_series = market_data.reindex(prices.index, method='ffill')["Close"]
            else:
                raise ValueError(f"Market index data for {indexsymbol} not found.")

        current_segment = price_data[-self.window_size:].values
    
        if self.use_volume:
            current_segment = np.column_stack((current_segment, volume_data[-self.window_size:].values))
           
        # 合并指数数据       
        if self.use_broad_market_index and index_series is not None:
            current_segment = np.column_stack((current_segment, index_series[-self.window_size:].values))
        
        matches = [(float('inf'), -1)]
        for index in range(1,len(price_data) - 2 * self.window_size - self.days_to_forecast):
            historical_segment = price_data[index: index + self.window_size].values
            
            if self.use_volume:
                historical_segment = np.column_stack((historical_segment, volume_data[index: index + self.window_size].values))

            if self.use_broad_market_index and index_series is not None:
                historical_segment = np.column_stack((historical_segment, index_series[index: index + self.window_size].values))

            similarity_score = self.compute_dtw_distance(current_segment, historical_segment)

            for i, (best_distance, _) in enumerate(matches):
                if similarity_score < best_distance:
                    matches = matches[:i] + [(similarity_score, index)] + matches[i:]
                    break

        #找出最近的topn个匹配项，要求best index之间的距离大于index_distance
        top_matches = []
        for i in range(len(matches)):
            _, index = matches[i]
            topass = False
            for j in range(len(top_matches)):
                _, index_b = top_matches[j]
                if abs(index - index_b) < self.index_distance:
                    topass = True
                    break
            if not topass:
                top_matches.append(matches[i])
            if len(top_matches) == self.topn:
                break
        return top_matches

    
    def forecast(self, prices, top_matches):
        """计算预测值"""
        price_data = prices["Close"]
        volume_data = prices["Volume"]
        return_series = price_data.pct_change(1)

        projected_prices = []
        similarity_scores = []
        for similarity_score, index in top_matches:
            # 获取预测段数据
            subsequent_segment = return_series[index + self.window_size:index + self.window_size + self.days_to_forecast].values
            projected_prices.append(subsequent_segment)
            similarity_scores.append(similarity_score)
            #print(f"Similarity Score = {similarity_score:.2f}, Match Returns = {subsequent_segment}")
        # 计算中位数预测路径
        projected_prices = np.array(projected_prices)
        similarity_scores = np.array(similarity_scores)
        if self.forecast_cal_method == "median":
            pred_returns = np.median(projected_prices, axis=0)
        if self.forecast_cal_method == "mean":
            pred_returns = np.mean(projected_prices, axis=0)
        if self.forecast_cal_method == "sigmean":
            similarity_scores = similarity_scores / np.sum(similarity_scores)
            sig_similarity_scores = np.exp(1/similarity_scores) / np.sum(np.exp(1/similarity_scores))
            #print(sig_similarity_scores)
            pred_returns = np.sum(projected_prices * sig_similarity_scores.reshape(-1, 1), axis=0)  

        pred_cumulative = (pred_returns + 1).cumprod() * 100
        pred_prices = pred_cumulative / 100 *  price_data.iloc[-1]
    
        return pred_prices, pred_returns

  
    def predict(self, prices, symbol, pred_date):
        before_prices = prices[prices.index <= pred_date]        
        after_prices = prices[prices.index > pred_date]

        top_matches = self.find_patterns(be_prices, symbol)
        pred_price, pred_return = self.forecast(be_prices, top_matches)

        if len(after_prices) == 0:
            real_price = np.asarray([])
        else:
            real_price = after_prices.values[:self.days_to_forecast]

        return pred_price, pred_return, real_price

    def long_predect(self, prices, symbol, start_date, end_date):
        preds = []
        for i in pda.index[(pda.index>=3) & (pda.index<=8)]
        for date in prices.index[(prices.index>=start_date) & (prices.index<=end_date)]:
            pred_price, pred_return, real_price = self.predict(prices, symbol, date)
            preds.append((date, pred_price, pred_return, real_price))
        return preds
        

    
