import numpy as np
import pandas as pd
from scipy.spatial.distance import euclidean
from fastdtw import fastdtw
from statsmodels.tsa.arima.model import ARIMA
import matplotlib.pyplot as plt

from configparser import ConfigParser

class AnalysisEngine:
    def __init__(self):
        self.config = ConfigParser()
        self.config.read('config.ini')
        self.dtw_radius = self.config.getint('Analysis', 'dtw_radius')

    def scale_series(self, series, method):
        if method == "minmax":
            return (series - series.min()) / (series.max() - series.min())
        if method == "first":
            return series / series[0]
        if method == "zscore":
            return (series - series.mean()) / series.std()
        if method is None:
            return series

    def compute_dtw_distance(self, series_a, series_b, method):
        scaled_a = self.scale_series(series_a, method)
        scaled_b = self.scale_series(series_b, method)
        distance, _ = fastdtw(scaled_a.reshape(-1, 1),
                            scaled_b.reshape(-1, 1),
                            radius=self.dtw_radius,
                            dist=euclidean)
        return distance


    def retrieve_similar_patterns(self, series, window_size, forecast_days, scale_method="first"):
        current_segment = series[-window_size:].values
        top_matches = [(float('inf'), -1)]

        for index in range(1,len(series) - 2 * window_size - forecast_days):
            historical_segment = series[index: index + window_size].values
            similarity_score = self.compute_dtw_distance(current_segment, historical_segment, scale_method)

            for i, (best_distance, _) in enumerate(top_matches):
                if similarity_score < best_distance:
                    top_matches = top_matches[:i] + [(similarity_score, index)] + top_matches[i:]
                    break
        return top_matches

    def find_best_matches(self, matches, index_distance = 8, topn=5):
        best_matches = []

        for i in range(len(matches)):
            _, index = matches[i]
            topass = False
            for j in range(len(best_matches)):
                _, index_b = best_matches[j]
                if abs(index - index_b) < index_distance:
                    topass = True
                    break
            if not topass:
                best_matches.append(matches[i])
            if len(best_matches) == topn:
                break
        return best_matches

    def cal_forecast(self, close_prices, return_series, best_matches, window, days_to_forecast, method="sigmean"):
        projected_prices = []
        similarity_scores = []
        for idx, (similarity_score, match_index) in enumerate(best_matches):
            # 获取预测段数据
            subsequent_segment = return_series[match_index + window:match_index + window + days_to_forecast].values
            projected_prices.append(subsequent_segment)
            similarity_scores.append(similarity_score)
        # 计算中位数预测路径
        projected_prices = np.array(projected_prices)
        similarity_scores = np.array(similarity_scores)
        if method == "median":
            forecast_returns = np.median(projected_prices, axis=0)
        if method == "mean":
            forecast_returns = np.mean(projected_prices, axis=0)
        if method == "sigmean":
            similarity_scores = similarity_scores / np.sum(similarity_scores)
            sig_similarity_scores = np.exp(1/similarity_scores) / np.sum(np.exp(1/similarity_scores))
            print(sig_similarity_scores)
            forecast_returns = np.sum(projected_prices * sig_similarity_scores.reshape(-1, 1), axis=0)  
        forecast_cumulative = (forecast_returns + 1).cumprod() * 100
        forecast_prices = forecast_cumulative / 100 *  close_prices.iloc[-1]

        return forecast_returns, forecast_prices

    def plot_patterns_and_forecast(self, figs, close_prices, return_series, best_matches, window, days_to_forecast, forecast_returns, forecast_prices):
        axes = [figs[i].add_subplot(111) for i in range(3)]

        # 绘制历史价格曲线
        axes[0].plot(close_prices, color='black', label='Stock Price History')

        # 颜色配置
        color_palette = ['red', 'green', 'purple', 'orange', 'cyan']
        projected_prices = []


        # 绘制匹配模式
        for idx, (similarity_score, match_index) in enumerate(best_matches):
            line_color = color_palette[idx % len(color_palette)]
            historical_data = close_prices[match_index:match_index + window]

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
            normalized_pattern = (return_series[match_index:match_index + window + days_to_forecast] + 1).cumprod() * 100
            axes[1].plot(range(window + days_to_forecast), normalized_pattern, color=line_color,
                        linewidth=3 if idx == 0 else 1, label=f"Pattern {idx + 1}")

        # 绘制当前模式
        normalized_current = (return_series[-window:] + 1).cumprod() * 100
        axes[1].plot(range(window), normalized_current, color='black', linewidth=3, label="Current Pattern")



        # 计算并绘制预测路径
        median_forecast = np.append(return_series[-window:], forecast_returns)
        median_forecast_cumulative = (median_forecast + 1).cumprod() * 100
        axes[1].plot(range(window + days_to_forecast), median_forecast_cumulative,
                    color='black', linestyle='dashed', label="Median Projected Path")

        # 设置第二个子图
        axes[1].set_title(f"Similar {window}-Day Patterns and Forecast",fontsize=10)
        axes[1].set_xlabel("Days",fontsize=8)
        axes[1].set_ylabel("Reindexed Price",fontsize=8)
        axes[1].tick_params(axis='both', which='major', labelsize=8)
        axes[1].legend(fontsize=8)


        axes[2].plot(range(window), close_prices[-window:], color='black', linewidth=3, label="Current Price")
        median_forecast_prices = median_forecast_cumulative / 100 *  close_prices.iloc[-window-1]
        axes[2].plot(range(window + days_to_forecast), median_forecast_prices,
                    color='black', linestyle='dashed', label="Median Projected Path")
        for i in range (len(median_forecast_prices)):
            axes[2].text(i, median_forecast_prices[i], f"{median_forecast_prices[i]:.2f}", ha ='center', va='bottom',fontsize=8)

        # 设置第三个子图
        axes[2].set_title(f"Similar {window}-Day Patterns and Forecast Price",fontsize=10)
        axes[2].set_xlabel("Days",fontsize=8)
        axes[2].set_ylabel("Reindexed Price",fontsize=8)
        axes[2].tick_params(axis='both', which='major', labelsize=8)
        axes[2].legend(fontsize=8)
