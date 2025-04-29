import numpy as np
import pandas as pd
from scipy.spatial.distance import euclidean
from fastdtw import fastdtw
import matplotlib.pyplot as plt
from datetime import datetime

from data_manager import StockDataManager

from configparser import ConfigParser

class AnalysisEngine:
    def __init__(self):
        self.config = ConfigParser()
        self.config.read('config.ini')
        self.dtw_radius = self.config.getint('Analysis', 'dtw_radius', fallback=1)
        self.window_size = self.config.getint('Analysis', 'window_size', fallback=15)
        self.days_to_forecast = self.config.getint('Analysis', 'days_to_forecast', fallback=8)
        self.use_returns = self.config.getboolean('Analysis', 'use_returns', fallback=False)
        self.scale_method = self.config.get('Analysis', 'scale_method', fallback='first')
        self.forecast_cal_method = self.config.get('Analysis', 'forecast_cal_method', fallback='sigmean')
        self.index_distance = self.config.getint('Analysis', 'index_distance', fallback=8)
        self.topn = self.config.getint('Analysis', 'topn', fallback=5)
        self.use_broad_market_index = self.config.getboolean('Analysis', 'use_broad_market_index', fallback=False)
        
        self.data_mgr = StockDataManager()
        # 新增指数数据字典
        self.broad_indices = {}
        if self.use_broad_market_index:
            self.load_broad_market_indices()

    def load_broad_market_indices(self):
        """从数据库加载主要大盘指数周数据"""
        index_map = {
            'HK': '^HSI',
            'A-SH': '000001.SS',
            'A-SZ': '399001.SZ',
            'US': '^IXIC'
        }
        self.broad_indices = {
            market: self.data_mgr.get_index_weekly_data(symbol)
            for market, symbol in index_map.items()
        }

    def scale_series(self, series):
        if self.scale_method == "minmax":
            return (series - series.min()) / (series.max() - series.min())
        if self.scale_method == "first":
            return series / series[0]
        if self.scale_method == "zscore":
            return (series - series.mean()) / series.std()
        if self.scale_method is None:
            return series

    def compute_dtw_distance(self, series_a, series_b):
        scaled_a = self.scale_series(series_a)
        scaled_b = self.scale_series(series_b)
        distance, _ = fastdtw(scaled_a.reshape(-1, 1),
                            scaled_b.reshape(-1, 1),
                            radius=self.dtw_radius,
                            dist=euclidean)
        return distance


    def retrieve_similar_patterns(self, series, market=None):
        if self.use_returns:
            series = series.pct_change(1)
                    
        current_segment = series[-self.window_size:].values

        if market is not None:
            market_data = self.broad_indices.get(market)      
        # 合并股票和指数数据
        if self.use_broad_market_index and market_data is not None:
            if self.use_returns:
                market_data = market_data.pct_change(1)
            
            # 对齐时间序列
            index_series = market_data.reindex(series.index, method='ffill')
            index_segment = index_series[-self.window_size:].values
            current_segment = np.column_stack((current_segment, index_segment))
        
        top_matches = [(float('inf'), -1)]

        for index in range(1,len(series) - 2 * self.window_size - self.days_to_forecast):
            historical_segment = series[index: index + self.window_size].values
            if self.use_broad_market_index and market_data is not None:
                index_segment = index_series[index: index + self.window_size].values
                historical_segment = np.column_stack((historical_segment, index_segment))
            similarity_score = self.compute_dtw_distance(current_segment, historical_segment)

            for i, (best_distance, _) in enumerate(top_matches):
                if similarity_score < best_distance:
                    top_matches = top_matches[:i] + [(similarity_score, index)] + top_matches[i:]
                    break
        return top_matches

    def set_window_size(self, value):
        self.window_size = value

    def set_days_to_forecast(self, value):
        self.days_to_forecast = value

    def find_best_matches(self, matches):
        best_matches = []

        for i in range(len(matches)):
            _, index = matches[i]
            topass = False
            for j in range(len(best_matches)):
                _, index_b = best_matches[j]
                if abs(index - index_b) < self.index_distance:
                    topass = True
                    break
            if not topass:
                best_matches.append(matches[i])
            if len(best_matches) == self.topn:
                break
        return best_matches

    def cal_forecast(self, close_prices, best_matches):
        return_series = close_prices.pct_change(1)
        projected_prices = []
        similarity_scores = []
        for idx, (similarity_score, match_index) in enumerate(best_matches):
            # 获取预测段数据
            subsequent_segment = return_series[match_index + self.window_size:match_index + self.window_size + self.days_to_forecast].values
            projected_prices.append(subsequent_segment)
            similarity_scores.append(similarity_score)
        # 计算中位数预测路径
        projected_prices = np.array(projected_prices)
        similarity_scores = np.array(similarity_scores)
        if self.forecast_cal_method == "median":
            forecast_returns = np.median(projected_prices, axis=0)
        if self.forecast_cal_method == "mean":
            forecast_returns = np.mean(projected_prices, axis=0)
        if self.forecast_cal_method == "sigmean":
            similarity_scores = similarity_scores / np.sum(similarity_scores)
            sig_similarity_scores = np.exp(1/similarity_scores) / np.sum(np.exp(1/similarity_scores))
            print(sig_similarity_scores)
            forecast_returns = np.sum(projected_prices * sig_similarity_scores.reshape(-1, 1), axis=0)  
        forecast_cumulative = (forecast_returns + 1).cumprod() * 100
        forecast_prices = forecast_cumulative / 100 *  close_prices.iloc[-1]

        return forecast_returns, forecast_prices

    def find_patterns_and_forecast(self, close_prices, market = None, analysis_date=None):

        if analysis_date is not None:
            before_prices = close_prices[close_prices.index<=analysis_date]
            after_prices = close_prices[close_prices.index>analysis_date]
        else:
            before_prices = close_prices
            after_prices = None
                
        matches = self.retrieve_similar_patterns(before_prices, market)
        best_matches = self.find_best_matches(matches)
        forecast_returns, forecast_prices = self.cal_forecast(before_prices, best_matches)
        if after_prices is None or len(after_prices) == 0:
            real_prices = np.asarray([])
        else:
            real_prices = after_prices.values[:self.days_to_forecast]
        
        return best_matches,forecast_returns, forecast_prices ,real_prices, before_prices

    def plot_patterns_and_forecast(self, figs, close_prices, best_matches, forecast_returns, forecast_prices, real_prices):
        return_series = close_prices.pct_change(1)
        axes = [figs[i].add_subplot(111) for i in range(3)]

        # 绘制历史价格曲线
        axes[0].plot(close_prices, color='black', label='Stock Price History')

        # 颜色配置
        color_palette = ['red', 'green', 'purple', 'orange', 'cyan']
        projected_prices = []


        # 绘制匹配模式
        for idx, (similarity_score, match_index) in enumerate(best_matches):
            line_color = color_palette[idx % len(color_palette)]
            historical_data = close_prices[match_index:match_index + self.window_size]

            axes[0].plot(historical_data, color=line_color, label=f"Pattern {idx + 1},{similarity_score:.2f},{str(close_prices.index[match_index])[:10]}")



        # 设置第一个子图
        axes[0].set_title(f'Price Patterns',fontsize=10)
        axes[0].set_xlabel('Date',fontsize=8)
        axes[0].set_ylabel('Price',fontsize=8)
        axes[0].tick_params(axis='both', which='major', labelsize=8)
        axes[0].legend(fontsize=8)

        # 绘制归一化模式
        for idx, (_, match_index) in enumerate(best_matches):
            line_color = color_palette[idx % len(color_palette)]
            normalized_pattern = (return_series[match_index:match_index + self.window_size + self.days_to_forecast] + 1).cumprod() * 100
            axes[1].plot(range(self.window_size + self.days_to_forecast), normalized_pattern, color=line_color,
                        linewidth=3 if idx == 0 else 1, label=f"Pattern {idx + 1}")

        # 绘制当前模式
        normalized_current = (return_series[-self.window_size:] + 1).cumprod() * 100
        axes[1].plot(range(self.window_size), normalized_current, color='black', linewidth=3, label="Current Pattern")



        # 计算并绘制预测路径
        median_forecast = np.append(return_series[-self.window_size:], forecast_returns)
        median_forecast_cumulative = (median_forecast + 1).cumprod() * 100
        axes[1].plot(range(self.window_size + self.days_to_forecast), median_forecast_cumulative,
                    color='black', linestyle='dashed', label="Median Projected Path")

        # 设置第二个子图
        axes[1].set_title(f"Similar {self.window_size}-Day Patterns and Forecast",fontsize=10)
        axes[1].set_xlabel("Days",fontsize=8)
        axes[1].set_ylabel("Reindexed Price",fontsize=8)
        axes[1].tick_params(axis='both', which='major', labelsize=8)
        axes[1].legend(fontsize=8)


        axes[2].plot(range(self.window_size), close_prices[-self.window_size:], color='black', linewidth=3, label="Current Price")
        median_forecast_prices = median_forecast_cumulative / 100 *  close_prices.iloc[-self.window_size-1]
        axes[2].plot(range(self.window_size + self.days_to_forecast), median_forecast_prices,
                    color='black', linestyle='dashed', label="Median Projected Path")
        for i in range (len(median_forecast_prices)):
            axes[2].text(i, median_forecast_prices[i], f"{median_forecast_prices[i]:.2f}", ha ='center', va='bottom',fontsize=8)

        axes[2].plot(range(self.window_size-1, self.window_size + len(real_prices)), np.append(np.asarray(close_prices[-1]), real_prices), color='red', linestyle='dashed', label="Real Price")
        #for i in range (len(real_prices)):
        #    axes[2].text(self.window_size+i, real_prices[i], f"{real_prices[i]:.2f}", ha ='center', va='bottom',fontsize=8, color='red')

        # 设置第三个子图
        axes[2].set_title(f"Similar {self.window_size}-Day Patterns and Forecast Price",fontsize=10)
        axes[2].set_xlabel("Days",fontsize=8)
        axes[2].set_ylabel("Reindexed Price",fontsize=8)
        axes[2].tick_params(axis='both', which='major', labelsize=8)
        axes[2].legend(fontsize=8)

