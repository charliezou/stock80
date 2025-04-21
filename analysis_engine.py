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
        self.window_size = 15
        self.days_to_forecast = 8
        self.use_returns = False
        self.scale_method = 'first'
        self.forecast_cal_method = "mean"

    def _zscore_normalize(self, data: np.ndarray) -> np.ndarray:
        '''数据标准化处理'''
        return (data - np.mean(data)) / np.std(data)

    def find_similar_patterns(self, query_seq: np.ndarray, base_seq: np.ndarray) -> float:
        '''DTW相似度计算'''
        query_norm = self._zscore_normalize(query_seq)
        base_norm = self._zscore_normalize(base_seq)
        distance, _ = fastdtw(query_norm, base_norm, radius=self.dtw_radius, dist=euclidean)
        return distance

    def arima_forecast(self, data: np.ndarray, steps: int = 7) -> np.ndarray:
        '''ARIMA时间序列预测'''
        model = ARIMA(data, order=(2,1,2))
        model_fit = model.fit()
        return model_fit.forecast(steps=steps)

    def validate_prediction(self, full_data: np.ndarray, test_ratio: float = 0.2) -> float:
        '''历史留出法验证'''
        split_idx = int(len(full_data) * (1 - test_ratio))
        train_data = full_data[:split_idx]
        test_data = full_data[split_idx:]

        # 训练预测模型
        predictions = self.arima_forecast(train_data, steps=len(test_data))
        
        # 计算RMSE
        rmse = np.sqrt(np.mean((predictions - test_data)**2))
        return rmse


    def scale_series(self, series, method):
        if method == "minmax":
            return (series - series.min()) / (series.max() - series.min())
        if method == "first":
            return series / series[0]
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


    def retrieve_similar_patterns(self, series, window_size, forecast_days, method="minmax"):
        current_segment = series[-window_size:].values
        top_matches = [(float('inf'), -1)]

        for index in range(1,len(series) - 2 * window_size - forecast_days):
            historical_segment = series[index: index + window_size].values
            similarity_score = self.compute_dtw_distance(current_segment, historical_segment, method)

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

    def cal_forecast(self, close_prices, return_series, best_matches, window, days_to_forecast, method="median"):
        projected_prices = []
        for idx, (similarity_score, match_index) in enumerate(best_matches):
            # 获取预测段数据
            subsequent_segment = return_series[match_index + window:match_index + window + days_to_forecast].values
            projected_prices.append(subsequent_segment)
        # 计算中位数预测路径
        projected_prices = np.array(projected_prices)
        if method == "median":
            forecast_returns = np.median(projected_prices, axis=0)
        if method == "mean":
            forecast_returns = np.mean(projected_prices, axis=0)
        forecast_cumulative = (forecast_returns + 1).cumprod() * 100
        forecast_prices = forecast_cumulative / 100 *  close_prices.iloc[-1]

        return forecast_returns, forecast_prices

    def plot_patterns_and_forecast(self, fig, close_prices, return_series, best_matches, window, days_to_forecast, forecast_returns, forecast_prices):
        axes = fig.subplots(3, 1)

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
        axes[0].set_title(f'Price Patterns')
        axes[0].set_xlabel('Date')
        axes[0].set_ylabel('Price')
        axes[0].legend()

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
        axes[1].set_title(f"Similar {window}-Day Patterns and Forecast")
        axes[1].set_xlabel("Days")
        axes[1].set_ylabel("Reindexed Price")
        axes[1].legend()


        axes[2].plot(range(window), close_prices[-window:], color='black', linewidth=3, label="Current Price")
        median_forecast_prices = median_forecast_cumulative / 100 *  close_prices.iloc[-window-1]
        axes[2].plot(range(window + days_to_forecast), median_forecast_prices,
                    color='black', linestyle='dashed', label="Median Projected Path")
        for i in range (len(median_forecast_prices)):
            axes[2].text(i, median_forecast_prices[i], f"{median_forecast_prices[i]:.2f}", ha ='center', va='bottom')

        # 设置第三个子图
        axes[2].set_title(f"Similar {window}-Day Patterns and Forecast Price")
        axes[2].set_xlabel("Days")
        axes[2].set_ylabel("Reindexed Price")
        axes[2].legend()
