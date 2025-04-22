import unittest
import numpy as np
from analysis_engine import AnalysisEngine
from data_manager import StockDataManager

class TestAnalysisEngine(unittest.TestCase):
    def setUp(self):
        self.engine = AnalysisEngine()
        self.data_mgr = StockDataManager()
        self.close_prices = self.data_mgr.get_stock_weekly_data('AAPL').iloc[-1000:]['Close']
        self.return_series = self.close_prices.pct_change(1)

    def test_stability_analysis(self):
        window_size = 15
        days_to_forecast = 8
        use_returns = False
        scale_method = 'first'
        forecast_cal_method = "mean"


        if use_returns:
            matches = self.engine.retrieve_similar_patterns(self.return_series, window_size, days_to_forecast, scale_method)
        else:
            matches = self.engine.retrieve_similar_patterns(self.close_prices, window_size, days_to_forecast, scale_method)
        best_matches = self.engine.find_best_matches(matches, index_distance = 8)
        print(best_matches)
        forecast_returns, forecast_prices = self.engine.cal_forecast(self.close_prices, self.return_series, best_matches, window_size, days_to_forecast, forecast_cal_method)
        
        print(forecast_prices)

if __name__ == '__main__':
    unittest.main()