import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout,
                            QLabel, QPushButton, QFileDialog, QHBoxLayout,QListWidget,QInputDialog,QMessageBox,QListWidgetItem)
from data_manager import StockDataManager
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

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
        self.import_btn = QPushButton("导入股票数据")
        self.update_btn = QPushButton("批量更新数据")
        self.validate_btn = QPushButton("验证数据完整性")
        
        # 连接信号槽
        self.import_btn.clicked.connect(self._handle_import)
        self.update_btn.clicked.connect(self._handle_bulk_update)
        self.data_manager = StockDataManager()
        
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
        code, ok1 = QInputDialog.getText(self, '输入股票代码', '请输入股票代码:')
        market, ok2 = QInputDialog.getItem(self, '选择市场', '请选择所属市场:', 
            ['A-SH', 'A-SZ', 'HK', 'US'], 0, False)
        
        if ok1 and ok2 and code:
            try:
                self.data_manager.download_data([(code.strip(), market)])
                self._refresh_stock_list()
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
            #self.stock_list.addItem(f"{stock['code']}: {stock['market']}: {stock['last_updated']}")
            
            item = QListWidgetItem(f"{stock['code']}\t{stock['market']}\t{stock['last_updated'][:10]}")
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
        layout = QVBoxLayout()
        
        # 双图表布局
        self.figure1 = Figure(figsize=(8, 4))
        self.canvas1 = FigureCanvasQTAgg(self.figure1)
        self.figure2 = Figure(figsize=(8, 4))
        self.canvas2 = FigureCanvasQTAgg(self.figure2)
        
        # 控制按钮
        self.analyze_btn = QPushButton("计算特征指标")
        
        layout.addWidget(self.canvas1)
        layout.addWidget(self.canvas2)
        layout.addWidget(self.analyze_btn)
        self.setLayout(layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())