import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout,
                            QLabel, QPushButton, QFileDialog, QHBoxLayout,QListWidget,QInputDialog,QMessageBox,QListWidgetItem,
                            QLineEdit,QComboBox,QSplitter)
from data_manager import StockDataManager
from feature_analysis import FeatureAnalyzer
import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# 设置全局字体为支持中文的字体
matplotlib.rcParams['font.family'] = ['Songti SC', 'Heiti TC', 'sans-serif']
matplotlib.rcParams['font.size'] = 9
matplotlib.rcParams['axes.unicode_minus'] = False  # 正确显示负号

plt.style.use('ggplot')
plt.rcParams['axes.prop_cycle'] = plt.cycler(color=plt.cm.cividis.colors)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 窗口基本设置
        self.setWindowTitle("智能股票分析系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 主垂直布局
        main_layout = QVBoxLayout(main_widget)
        
        # 创建标签页
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # 初始化三个功能页
        self.data_page = DataManagementPage()
        self.trend_page = TrendAnalysisPage()
        self.feature_page = FeatureAnalysisPage()
        
        self.tabs.addTab(self.data_page, "数据管理")
        self.tabs.addTab(self.trend_page, "趋势预测")
        self.tabs.addTab(self.feature_page, "特征分析")
        
        # 应用样式
        self._apply_styles()

    def _apply_styles(self):
        # MacOS风格样式
        with open('styles.qss', 'r', encoding='utf-8') as f:
            self.setStyleSheet(f.read())


class DataManagementPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        
        # 数据操作区域
        control_layout = QHBoxLayout()
        
        # 输入控件
        self.code_input = QLineEdit(placeholderText='请输入股票代码')
        self.market_combo = QComboBox()
        self.market_combo.addItems(['A-SH', 'A-SZ', 'HK', 'US'])
        
        # 按钮
        self.import_btn = QPushButton("导入数据")
        self.update_btn = QPushButton("批量更新")
        self.validate_btn = QPushButton("验证数据")
        
        # 连接信号槽
        self.import_btn.clicked.connect(self._handle_import)
        self.update_btn.clicked.connect(self._handle_bulk_update)
        self.data_manager = StockDataManager()
        
        # 布局排列
        control_layout.addWidget(QLabel('代码:'))
        control_layout.addWidget(self.code_input)
        control_layout.addWidget(QLabel('市场:'))
        control_layout.addWidget(self.market_combo)
        control_layout.addSpacing(20)
        control_layout.addWidget(self.import_btn)
        control_layout.addWidget(self.update_btn)
        control_layout.addWidget(self.validate_btn)
        
        # 数据展示区域
        self.stock_list = QListWidget()
        
        self.stock_list.itemDoubleClicked.connect(self._handle_delete)
        
        layout.addLayout(control_layout)
        layout.addWidget(self.stock_list)
        self.setLayout(layout)
        self._refresh_stock_list()

    def _handle_delete(self, item):
        confirm = QMessageBox.question(self, "确认删除", 
            f"确定要删除{item.stock_code} ({item.market}) 吗？",
            QMessageBox.Yes | QMessageBox.No)

        if confirm == QMessageBox.Yes:
            if self.data_manager.delete_stock_data(item.stock_code):
                self.stock_list.takeItem(self.stock_list.row(item))
            else:
                QMessageBox.warning(self, "错误", "删除股票数据失败")
        
    def _handle_import(self):
        code = self.code_input.text().strip()
        market = self.market_combo.currentText()
        
        if not code:
            QMessageBox.warning(self, '输入错误', '请输入股票代码')
            self.code_input.setFocus()
            return
        
        try:
            self.data_manager.download_data([(code, market)])
            self._refresh_stock_list()
            self.code_input.clear()
            QMessageBox.information(self, '成功', '数据导入成功')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'导入失败: {str(e)}')
    
    def _handle_bulk_update(self):
        stocks = self.data_manager.get_all_stocks()
        try:
            self.data_manager.download_data([(code, market) for code, market, _ in stocks])
            self._refresh_stock_list()
            QMessageBox.information(self, '成功', f'已更新{len(stocks)}支股票数据')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'批量更新失败: {str(e)}')
    
    def _refresh_stock_list(self):
        stocks = self.data_manager.get_all_stocks()
        self.stock_list.clear()
        for stock in stocks:
            item = QListWidgetItem(f"{stock['code']}\t{stock['market']}\t{stock['end_date']}")
            item.stock_code = stock['code']
            item.market = stock['market']
            self.stock_list.addItem(item)
               

class TrendAnalysisPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        
        # 图表区域
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvasQTAgg(self.figure)
        
        # 控制区域
        self.analyze_btn = QPushButton("开始趋势分析")
        
        layout.addWidget(self.canvas)
        layout.addWidget(self.analyze_btn)
        self.setLayout(layout)

class FeatureAnalysisPage(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout()
        
        # 创建水平分割布局
        splitter = QSplitter()
        
        # 左侧股票列表面板
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        self.stock_list = QListWidget()
        left_layout.addWidget(QLabel("已导入股票列表"))
        left_layout.addWidget(self.stock_list)
        left_panel.setLayout(left_layout)
        
        # 右侧图表区域
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        self.figure1 = Figure(figsize=(8, 4))
        self.canvas1 = FigureCanvasQTAgg(self.figure1)
        self.figure2 = Figure(figsize=(8, 4))
        self.canvas2 = FigureCanvasQTAgg(self.figure2)
        right_layout.addWidget(self.canvas1)
        right_layout.addWidget(self.canvas2)
        right_panel.setLayout(right_layout)
        
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([200, 600])
        
        # 控制按钮
        self.analyze_btn = QPushButton("计算特征指标")
        
        main_layout.addWidget(splitter)
        main_layout.addWidget(self.analyze_btn)
        self.setLayout(main_layout)
        
        # 初始化数据
        self.data_mgr = StockDataManager()
        self.load_stock_list()
        
    def load_stock_list(self):
        stocks = self.data_mgr.get_all_stocks()
        self.stock_list.clear()
        for stock in stocks:
            item = QListWidgetItem(f"{stock['code']} - {stock['market']}")
            item.stock_code = stock['code']
            self.stock_list.addItem(item)
        self.stock_list.itemClicked.connect(self.on_stock_selected)

    def on_stock_selected(self, item):
        # 获取股票代码
        stock_code = item.stock_code
        
        # 从DataManager获取完整数据
        df = self.data_mgr.get_stock_weekly_data(stock_code).iloc[-520:]  # 取最近104周数据
        
        # 调用特征分析方法
        analyzer = FeatureAnalyzer()
        
        # 获取配置的年数列表
        years_list = [int(y) for y in self.data_mgr.config['Returns']['years'].split(',')]
        
        # 计算不同周期的年化收益
        close_prices = df['Close'].values
        annual_returns = analyzer.calculate_annualized_returns(close_prices, years_list)
        stability_data, envelope = analyzer.analyze_stability(close_prices)
        
        # 在成长性图表标题显示年化率
        return_labels = [f'{y}年: {r*100:.1f}%' for y,r in annual_returns]
        
        # 更新成长性图表
        self.figure1.clear()
        ax1 = self.figure1.add_subplot(111)
        ax1.plot(df['Close'], label='收盘价')
        ax1.set_title(f'年化收益率: {return_labels}')
        ax1.legend()
        self.canvas1.draw()
        
        # 更新稳定性图表
        self.figure2.clear()
        ax2 = self.figure2.add_subplot(111)
        ax2.plot(df['Close'], label='原始价格')
        ax2.plot(df.index, envelope, 'g--', label='包络线')
        ax2.scatter(df.index[stability_data['peaks']],  # 使用日期索引
                   df['Close'].iloc[stability_data['peaks']], 
                   marker='^', color='b')
        ax2.scatter(df.index[stability_data['valleys']],  # 使用日期索引
                   df['Close'].iloc[stability_data['valleys']],
                   marker='v', color='r')
        ax2.set_title(f'稳定性分析 - 得分: {stability_data["growth_score"]:.2f}')
        ax2.legend()
        self.canvas2.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())