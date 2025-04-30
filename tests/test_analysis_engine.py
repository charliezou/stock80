import unittest
import numpy as np
from analysis_engine import AnalysisEngine
from data_manager import StockDataManager

class TestAnalysisEngine(unittest.TestCase):
    def setUp(self):
        self.engine = AnalysisEngine()
        self.data_mgr = StockDataManager()
        dt = self.data_mgr.get_stock_weekly_data('AAPL').iloc[-1000:]
        self.close_prices = dt['Close']
        self.volume = dt['Volume']

    def test_find_patterns_and_forecast(self):
        best_matches,forecast_returns, forecast_prices,real_prices,_ = self.engine.find_patterns_and_forecast(self.close_prices,'US',self.volume,'2025-04-07')
        print(forecast_returns)
        print(forecast_prices)
        print(real_prices)

if __name__ == '__main__':
    unittest.main()