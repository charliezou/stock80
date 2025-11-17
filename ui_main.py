import sys
from PyQt5.QtCore import Qt, QDate, QDateTime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout,
                            QLabel, QPushButton, QFileDialog, QHBoxLayout,QListWidget,QInputDialog,QMessageBox,QListWidgetItem,
                            QLineEdit,QComboBox,QSplitter,QDateEdit)
from data_manager import StockDataManager
from feature_analysis import FeatureAnalyzer
from analysis_engine import AnalysisEngine
import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import time

# 设置全局字体为支持中文的字体
matplotlib.rcParams['font.family'] = ['Songti SC', 'Heiti TC', 'sans-serif']
matplotlib.rcParams['font.size'] = 8  # 字体大小
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
        
        # 初始化四个功能页
        self.data_page = DataManagementPage()
        self.trend_page = TrendAnalysisPage()
        self.feature_page = FeatureAnalysisPage()
        self.envelope_page = EnvelopeAnalysisPage()
        
        self.tabs.addTab(self.data_page, "数据管理")
        self.tabs.addTab(self.trend_page, "趋势预测")
        self.tabs.addTab(self.feature_page, "特征分析")
        self.tabs.addTab(self.envelope_page, "包络线分析")
        
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
        self.market_combo.addItems(['A-SH', 'A-SZ', 'HK', 'US', 'DP'])
        
        # 按钮
        self.import_btn = QPushButton("导入数据")
        self.update_btn = QPushButton("批量导入")
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
            success_codes = self.data_manager.download_data([(code, market)])
            self._refresh_stock_list()
            self.code_input.clear()
            if len(success_codes)>0:
                QMessageBox.information(self, '成功', '数据导入成功')
            else:
                QMessageBox.warning(self, '错误', '数据导入失败') 

        except Exception as e:
            QMessageBox.critical(self, '错误', f'导入失败: {str(e)}')
    
    def _handle_bulk_update(self):
        # 获取用户输入的配置名称和市场    
        market, ok = QInputDialog.getItem(self, '选择市场', '请选择市场:', ['A-SH', 'A-SZ', 'HK', 'US', 'DP'], 0, False)
        if not ok:
            return

        config_name, ok = QInputDialog.getText(self, '批量导入配置', '请输入配置名称:')
        if not ok:
            return
        
        # 从config.ini读取股票代码列表
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read('config.ini')
            
            if 'StockLists' not in config:
                QMessageBox.warning(self, '错误', '配置文件中没有StockLists配置段')
                return  

            stock_list_key = f"{market}_{config_name}"
            if config_name.strip() == "" or stock_list_key not in config['StockLists']:
                # 尝试使用市场名称作为键
                if market not in config['StockLists']:
                    QMessageBox.warning(self, '错误', f'配置文件中没有找到{market}市场的股票代码列表')
                    return
                stock_codes_str = config['StockLists'][market]
            else:
                stock_codes_str = config['StockLists'][stock_list_key]
            
            # 解析股票代码
            stock_codes = [code.strip() for code in stock_codes_str.split(',') if code.strip()]
            if not stock_codes:
                QMessageBox.warning(self, '错误', '股票代码列表为空')
                return
                
            # 确认导入
            confirm = QMessageBox.question(self, '确认批量导入', 
                f'确定要导入{market}市场的{len(stock_codes)}支股票吗？\n股票代码: {stock_codes_str}',
                QMessageBox.Yes | QMessageBox.No)
            
            if confirm != QMessageBox.Yes:
                return
            print(f"要导入的股票代码列表: {stock_codes}")
            # 批量导入数据
            success_codes = self.data_manager.batch_download(stock_codes, market)
            self._refresh_stock_list()
            
            if success_codes:
                QMessageBox.information(self, '成功', f'已成功导入{len(success_codes)}支股票数据')
            else:
                QMessageBox.warning(self, '警告', '没有成功导入任何股票数据')
    
        except Exception as e:
            QMessageBox.critical(self, '错误', f'批量导入失败: {str(e)}')
    
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

        main_layout = QVBoxLayout()
        
        # 主布局使用QSplitter
        splitter = QSplitter()
        

        # 左侧股票列表面板
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        self.stock_list = QListWidget()
        left_layout.addWidget(QLabel("已导入股票列表"))
        self.refresh_btn = QPushButton("刷新列表")
        self.refresh_btn.clicked.connect(self._load_stock_list)
        left_layout.addWidget(self.refresh_btn)

 

        left_layout.addWidget(self.stock_list)

        # 修改日期输入布局
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("开始日期:"))
        self.start_date_input = QDateEdit()
        self.start_date_input.setDisplayFormat("yyyy-MM-dd")
        self.start_date_input.setDate(QDate.currentDate().addMonths(-6))  # 默认半年前
        date_layout.addWidget(self.start_date_input)
        
        date_layout.addWidget(QLabel("结束日期:"))
        self.end_date_input = QDateEdit()
        self.end_date_input.setDisplayFormat("yyyy-MM-dd")
        self.end_date_input.setDate(QDate.currentDate())  # 默认今天
        date_layout.addWidget(self.end_date_input)
        
        left_layout.addLayout(date_layout)

        left_panel.setLayout(left_layout)

        # 添加分析状态标志
        self.is_analyzing = False
        self.current_analysis_date = None
        
        # 右侧图表区域
        right_panel = QWidget()
        layout = QVBoxLayout(right_panel)
        
        # 图表区域
        self.figure1 = Figure(figsize=(8, 4))
        self.canvas1 = FigureCanvasQTAgg(self.figure1)

        self.figure2 = Figure(figsize=(8, 4))
        self.canvas2 = FigureCanvasQTAgg(self.figure2)

        self.figure3 = Figure(figsize=(8, 4))
        self.canvas3 = FigureCanvasQTAgg(self.figure3)
        
        layout.addWidget(self.canvas1)
        layout.addWidget(self.canvas2)
        layout.addWidget(self.canvas3)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([200, 600])

        # 控制按钮
        self.analyze_btn = QPushButton("开始趋势分析")
        
        main_layout.addWidget(splitter)
        main_layout.addWidget(self.analyze_btn)
        self.setLayout(main_layout)

        # 修改按钮信号绑定
        self.analyze_btn.clicked.connect(self.on_analyze_clicked)  # 原连接可能需要调
        
        # 初始化数据管理器
        self.data_mgr = StockDataManager()
        self._load_stock_list()

        # 新增缓存相关属性
        self.analysis_cache = []  # 存储元组 (date_str, before_prices, best_matches, forecast_returns, forecast_prices, real_prices)
        self.current_cache_index = -1
        
    
    def _load_stock_list(self):
        stocks = self.data_mgr.get_all_stocks()
        self.stock_list.clear()
        for stock in stocks:
            item = QListWidgetItem(f"{stock['code']} - {stock['market']}")
            item.stock_code = stock['code']
            item.market = stock['market']
            self.stock_list.addItem(item)

    def keyPressEvent(self, event):
        """处理左右箭头切换缓存结果"""
        if event.key() == Qt.Key_Left:
            self.current_cache_index -= 1
            if self.current_cache_index <= -1:
                self.current_cache_index = len(self.analysis_cache)-1
            self._display_cached_result()
        elif event.key() == Qt.Key_Right:
            self.current_cache_index += 1
            if self.current_cache_index >= len(self.analysis_cache):
                self.current_cache_index = 0
            self._display_cached_result()
        else:
            super().keyPressEvent(event)

    def _display_cached_result(self):
        """显示缓存中的分析结果"""
        if 0 <= self.current_cache_index < len(self.analysis_cache):
            date_str, before_prices, best_matches, forecast_returns, forecast_prices, real_prices = self.analysis_cache[self.current_cache_index]
            
            # 清除旧图表
            self.figure1.clear()
            self.figure2.clear()
            self.figure3.clear()

            # 重新绘制图表
            engine = AnalysisEngine()
            engine.plot_patterns_and_forecast(
                [self.figure1, self.figure2, self.figure3],
                before_prices,
                best_matches,
                forecast_returns,
                forecast_prices,
                real_prices,
                date_str  # 添加日期参数用于标题显示
            )

            # 更新画布
            self.canvas1.draw_idle()
            self.canvas2.draw_idle()
            self.canvas3.draw_idle()


    def on_analyze_clicked(self):
        if self.is_analyzing:
            QMessageBox.information(self, '提示', '已有分析正在进行')
            return
            
        selected_items = self.stock_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, '警告', '请先选择股票')
            return
            
        start_date = self.start_date_input.date()
        end_date = self.end_date_input.date()
        if start_date > end_date:
            QMessageBox.warning(self, '错误', '开始日期不能晚于结束日期')
            return        
        
        # 生成日期序列
        self.date_queue = []
        current_date = start_date
        # 调整到最近的周五
        if current_date.dayOfWeek() != Qt.Friday:
            # 计算到下一个周五需要增加的天数
            days_to_add = (5 - current_date.dayOfWeek() + 7) % 7
            current_date = current_date.addDays(days_to_add)
        
        # 确保调整后的日期在范围内
        if current_date > end_date:
            QMessageBox.warning(self, '错误', '日期范围内没有有效的周五')
            return
            
        while current_date <= end_date:
            self.date_queue.append(current_date.toString("yyyy-MM-dd"))
            current_date = current_date.addDays(7)  # 直接增加7天保证后续都是周五

        # 修改按钮信号连接
        self.is_analyzing = True
        self.analyze_btn.setText("停止分析")
        self.analyze_btn.clicked.disconnect()
        self.analyze_btn.clicked.connect(self.cancel_analysis)
        
        # 启动分析线程
        import threading
        self.analysis_thread = threading.Thread(target=self._run_weekly_analysis, args=(selected_items[0],))
        self.analysis_thread.start()


    def _run_weekly_analysis(self, item):
        self.setFocus()  # 让窗口获得焦点
        self.analysis_cache = []  # 清空旧缓存
        
        for analysis_date in self.date_queue:
            if not self.is_analyzing:
                break

            print(f'开始分析{analysis_date}...')
            self.current_analysis_date = analysis_date
            
            # 获取分析结果
            stock_code = item.stock_code
            market = item.market
            dt = self.data_mgr.get_stock_weekly_data(stock_code).iloc[-1000:]
            close_prices = dt['Close']
            volume = dt['Volume']
            
            engine = AnalysisEngine()
            analysis_result = engine.find_patterns_and_forecast(
                close_prices,
                market=market,
                volume=volume,
                analysis_date=analysis_date
            )
            
            # 解包结果
            best_matches, forecast_returns, forecast_prices, real_prices, before_prices = analysis_result
            
            # 缓存原始数据
            self.analysis_cache.append((
                analysis_date,
                before_prices,
                best_matches,
                forecast_returns,
                forecast_prices,
                real_prices
            ))

            # 立即显示最新结果
            self.current_cache_index = len(self.analysis_cache) - 1
            self._display_cached_result()
            QApplication.processEvents()

        if self.analysis_cache:
            self.current_cache_index = len(self.analysis_cache) - 1
        
        self.cancel_analysis()
        #QMessageBox.information(self, '完成', '分析完成')
        
    def cancel_analysis(self):
        self.is_analyzing = False
        self.analyze_btn.setText("开始趋势分析")
        self.analyze_btn.clicked.disconnect()
        self.analyze_btn.clicked.connect(self.on_analyze_clicked)    

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
        self.refresh_btn = QPushButton("刷新列表")
        self.refresh_btn.clicked.connect(self.load_stock_list)
        left_layout.addWidget(self.refresh_btn)
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
        df = self.data_mgr.get_stock_weekly_data(stock_code).iloc[-520:]  # 取最近520周数据
        
        # 调用特征分析方法
        analyzer = FeatureAnalyzer()
        
        # 获取配置的年数列表
        years_list = [int(y) for y in self.data_mgr.config['Returns']['years'].split(',')]
        
        # 计算不同周期的年化收益
        close_prices = df['Close'].values
        annual_returns = analyzer.calculate_annualized_returns(close_prices, years_list)
        stability_data, envelope = analyzer.analyze_stability(close_prices, years_list)
        
        # 在成长性图表标题显示年化率
        return_labels = [f'{y}年: {r*100:.1f}%' for y,r in annual_returns]
        stability_labels = [f'{y}年: {r*100:.1f}' for y,r in stability_data['growth_scores']]
        
        # 更新成长性图表
        self.figure1.clear()
        ax1 = self.figure1.add_subplot(111)
        ax1.plot(df['Close'], label='收盘价')
        ax1.set_title(f'年化收益率: {return_labels}',fontsize=10)
        ax1.legend(fontsize=8)
        ax1.tick_params(axis='both', which='major', labelsize=8)
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
        ax2.set_title(f'成长性得分: {stability_labels}',fontsize=10)
        ax2.tick_params(axis='both', which='major', labelsize=8)
        ax2.legend(fontsize=8)
        self.canvas2.draw()

class EnvelopeAnalysisPage(QWidget):
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
        self.refresh_btn = QPushButton("刷新列表")
        self.refresh_btn.clicked.connect(self.load_stock_list)
        left_layout.addWidget(self.refresh_btn)
        left_layout.addWidget(self.stock_list)
        
        # 添加时间窗口控制区域
        control_layout = QHBoxLayout()
        
        # 添加左右导航按钮
        self.prev_btn = QPushButton("← 前")
        self.next_btn = QPushButton("后 →")
        self.prev_btn.clicked.connect(self.show_previous_week)
        self.next_btn.clicked.connect(self.show_next_week)
        control_layout.addWidget(self.prev_btn)
        control_layout.addWidget(self.next_btn)
     
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
        self.analyze_btn = QPushButton("计算包络线指标")
        
        main_layout.addWidget(splitter)
        main_layout.addWidget(self.analyze_btn)
        self.setLayout(main_layout)
        
        # 初始化数据
        self.data_mgr = StockDataManager()
        self.current_stock_data = None
        self.current_stock_code = None
        self.window_start_index = 0  # 当前520周窗口的起始索引
        self.window_size = 260  # 默认窗口长度
        self.load_stock_list()
    
    def keyPressEvent(self, event):
        """处理键盘事件，实现左右键控制"""
        if self.current_stock_data is None:
            return
            
        if event.key() == Qt.Key_Left:
            # 左键按下，前推一周
            self.show_previous_week()
        elif event.key() == Qt.Key_Right:
            # 右键按下，后推一周
            self.show_next_week()
        elif event.key() == Qt.Key_A:
            # A键按下，前推52周
            self.show_previous_periods(52)
        elif event.key() == Qt.Key_D:
            # D键按下，后推52周
            self.show_next_periods(52)
        else:
            # 其他按键交给父类处理
            super().keyPressEvent(event)
        
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
        self.current_stock_code = stock_code
        
        # 从DataManager获取完整数据
        df = self.data_mgr.get_stock_weekly_data(stock_code)
        self.current_stock_data = df
        
        # 初始化窗口位置为最近104周
        self.window_start_index = max(0, len(df) - self.window_size)

        self.setFocus()
        
        # 分析当前窗口
        self.analyze_current_window()
        
    def show_previous_week(self):
        if self.current_stock_data is None:
            return
            
        # 前推一周，窗口起始索引减1
        self.window_start_index = max(0, self.window_start_index - 1)
        self.analyze_current_window()
        
    def show_next_week(self):
        if self.current_stock_data is None:
            return
            
        # 后推一周，窗口起始索引加1
        max_start_index = len(self.current_stock_data) - self.window_size
        self.window_start_index = min(max_start_index, self.window_start_index + 1)
        self.analyze_current_window()
        
    def show_previous_periods(self, periods):
        """前推指定周期数"""
        if self.current_stock_data is None:
            return
            
        # 前推指定周期，窗口起始索引减去periods
        self.window_start_index = max(0, self.window_start_index - periods)
        self.analyze_current_window()
        
    def show_next_periods(self, periods):
        """后推指定周期数"""
        if self.current_stock_data is None:
            return
            
        # 后推指定周期，窗口起始索引加上periods
        max_start_index = len(self.current_stock_data) - self.window_size
        self.window_start_index = min(max_start_index, self.window_start_index + periods)
        self.analyze_current_window()
        
    def analyze_current_window(self):
        if self.current_stock_data is None:
            return
            
        # 获取当前520周窗口的数据
        start_idx = self.window_start_index
        end_idx = start_idx + self.window_size
        window_df = self.current_stock_data.iloc[start_idx:end_idx]

        #window_df = self.current_stock_data.iloc[-520:]
        
        # 更新窗口信息显示
        start_date = window_df.index[0].strftime('%Y-%m-%d')
        end_date = window_df.index[-1].strftime('%Y-%m-%d')
        
        print(f"当前窗口:  ({start_date} 至 {end_date})")
        
        # 调用特征分析方法
        analyzer = FeatureAnalyzer()
        
        # 获取配置的年数列表
        years_list = [int(y) for y in self.data_mgr.config['Returns']['years'].split(',')]
        
        # 计算不同周期的年化收益
        close_prices = window_df['Close'].values
        annual_returns = analyzer.calculate_annualized_returns(close_prices, years_list)
        stability_data, envelope = analyzer.analyze_stability(close_prices, years_list)
        
        # 在成长性图表标题显示年化率
        return_labels = [f'{y}年: {r*100:.1f}%' for y,r in annual_returns]
        stability_labels = [f'{y}年: {r*100:.1f}' for y,r in stability_data['growth_scores']]
        
        # 更新成长性图表
        self.figure1.clear()
        ax1 = self.figure1.add_subplot(111)
        ax1.plot(window_df['Close'], label='收盘价')
        ax1.set_title(f'年化收益率: {return_labels}', fontsize=10)
        ax1.legend(fontsize=8)
        ax1.tick_params(axis='both', which='major', labelsize=8)
        self.canvas1.draw()
        
        # 更新稳定性图表
        self.figure2.clear()
        ax2 = self.figure2.add_subplot(111)
        #ax2.plot(window_df['Close'], label='原始价格')
        ax2.plot(window_df.index, envelope, 'g--', label='包络线')
        ax2.scatter(window_df.index[stability_data['peaks']],  # 使用日期索引
                   envelope[stability_data['peaks']], 
                   marker='^', color='b')
        ax2.scatter(window_df.index[stability_data['valleys']],  # 使用日期索引
                   envelope[stability_data['valleys']],
                   marker='v', color='r')
        ax2.set_title(f'成长性得分: {stability_labels}', fontsize=10)
        ax2.tick_params(axis='both', which='major', labelsize=8)
        ax2.legend(fontsize=8)
        self.canvas2.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())