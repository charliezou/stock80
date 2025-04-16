import unittest
import numpy as np
from feature_analysis import FeatureAnalyzer
from data_manager import StockDataManager

class TestFeatureAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = FeatureAnalyzer()
        # 生成测试数据：前30周线性增长，后30周波动
        self.test_data = np.concatenate([
            np.linspace(100, 200, 30),
            np.sin(np.linspace(0, 6*np.pi, 30)) * 20 + 180
        ])
        self.data_mgr = StockDataManager()


    def test_growth_score_calculation(self):
        # 测试完全增长序列
        perfect_growth = np.linspace(100, 200, 60)
        score = self.analyzer.calculate_growth_score(perfect_growth)
        self.assertAlmostEqual(score, 100.0, delta=0.1)

    def test_envelope_extraction(self):
        envelope = self.analyzer.extract_hilbert_envelope(self.test_data)
        # 验证包络线长度匹配
        self.assertEqual(len(envelope), len(self.test_data))
        # 验证包络线平滑性
        self.assertLess(np.std(np.diff(envelope)), 2.5)

    def test_stability_analysis(self):
        # 从DataManager获取完整数据
        df = self.data_mgr.get_stock_weekly_data('AAPL').iloc[-104:]

        result = self.analyzer.analyze_stability(df['Close'].values)
        print(result)

if __name__ == '__main__':
    unittest.main()