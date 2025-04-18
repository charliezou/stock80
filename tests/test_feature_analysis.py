import unittest
import numpy as np
from feature_analysis import FeatureAnalyzer
from data_manager import StockDataManager

class TestFeatureAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = FeatureAnalyzer()
        self.data_mgr = StockDataManager()
        self.test_data = self.data_mgr.get_stock_weekly_data('AAPL').iloc[-520:]['Close'].values


    def test_stability_analysis(self):
        result, envelope = self.analyzer.analyze_stability(self.test_data)
        print(result)

    def test_annualized_returns(self):
        # 测试不同周期的年化收益
        years_list = [1, 2, 3, 5, 10]
        returns = self.analyzer.calculate_annualized_returns(self.test_data, years_list)
        print(returns)

if __name__ == '__main__':
    unittest.main()