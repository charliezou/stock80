import numpy as np
import pandas as pd
from feature_analysis import FeatureAnalyzer
from data_manager import StockDataManager
import matplotlib.pyplot as plt

# 设置全局字体为支持中文的字体
plt.rcParams['font.family'] = ['Songti SC', 'Heiti TC', 'sans-serif']
plt.rcParams['font.size'] = 8  # 字体大小
plt.rcParams['axes.unicode_minus'] = False  # 正确显示负号

class EnvelopeStrategy:
    """
    包络线趋势跟踪策略类
    """
    def __init__(self):
        self.analyzer = FeatureAnalyzer()
        self.data_manager = StockDataManager()
    
    def get_position(self, extreme_data, extreme_data2):
        """
        根据extreme_data和extreme_data2判断仓位
        
        参数:
            extreme_data: 低阈值包络线的极值点数据
            extreme_data2: 高阈值包络线的极值点数据
            
        返回:
            position: 仓位 (1.0=满仓, 0.7=7成仓, 0.3=3成仓, 0.0=空仓)
            signal_type: 信号类型描述
        """
        # 获取最后一个极值点
        if len(extreme_data['peaks']) == 0 and len(extreme_data['valleys']) == 0:
            return 0.0, "无极值点"
            
        if len(extreme_data2['peaks']) == 0 and len(extreme_data2['valleys']) == 0:
            return 0.0, "无极值点"
        
        # 确定最后一个极值点的类型和位置
        last_extreme_type1 = None
        last_extreme_pos1 = -1
        
        if len(extreme_data['peaks']) > 0 and len(extreme_data['valleys']) > 0:
            if extreme_data['peaks'][-1] > extreme_data['valleys'][-1]:
                last_extreme_type1 = 'peak'
                last_extreme_pos1 = extreme_data['peaks'][-1]
            else:
                last_extreme_type1 = 'valley'
                last_extreme_pos1 = extreme_data['valleys'][-1]
        elif len(extreme_data['peaks']) > 0:
            last_extreme_type1 = 'peak'
            last_extreme_pos1 = extreme_data['peaks'][-1]
        elif len(extreme_data['valleys']) > 0:
            last_extreme_type1 = 'valley'
            last_extreme_pos1 = extreme_data['valleys'][-1]
        
        # 确定第二个极值点的类型和位置
        last_extreme_type2 = None
        last_extreme_pos2 = -1
        
        if len(extreme_data2['peaks']) > 0 and len(extreme_data2['valleys']) > 0:
            if extreme_data2['peaks'][-1] > extreme_data2['valleys'][-1]:
                last_extreme_type2 = 'peak'
                last_extreme_pos2 = extreme_data2['peaks'][-1]
            else:
                last_extreme_type2 = 'valley'
                last_extreme_pos2 = extreme_data2['valleys'][-1]
        elif len(extreme_data2['peaks']) > 0:
            last_extreme_type2 = 'peak'
            last_extreme_pos2 = extreme_data2['peaks'][-1]
        elif len(extreme_data2['valleys']) > 0:
            last_extreme_type2 = 'valley'
            last_extreme_pos2 = extreme_data2['valleys'][-1]
        
        # 根据四种情形判断仓位
        if last_extreme_type1 == 'valley' and last_extreme_type2 == 'valley':
            # 情形1：两个极值点均为谷点，满仓信号
            return 1.0, "满仓信号(双谷点)"
        elif last_extreme_type1 == 'peak' and last_extreme_type2 == 'peak':
            # 情形2：两个极值点均为峰点，空仓信号
            return 0.0, "空仓信号(双峰点)"
        elif last_extreme_type1 == 'valley' and last_extreme_type2 == 'peak':
            # 情形3：低阈值为谷点，高阈值为峰点，7成仓位
            return 0.7, "7成仓位(低阈值谷点+高阈值峰点)"
        elif last_extreme_type1 == 'peak' and last_extreme_type2 == 'valley':
            # 情形4：低阈值为峰点，高阈值为谷点，3成仓位
            return 0.3, "3成仓位(低阈值峰点+高阈值谷点)"
        
        return 0.0, "未知情况"
    
    def generate_signals(self, stock_code, market='A-SH', start_date=None, end_date=None):
        """
        生成买卖信号
        
        参数:
            stock_code: 股票代码
            market: 市场代码，默认'A-SH'（上海证券交易所）
            start_date: 开始日期
            end_date: 结束日期
            
        返回:
            signals: 包含买卖信号的DataFrame
            envelope_history: 每个时间点的包络线历史
            extreme_data_history: 每个时间点的极值点历史
        """
        
        # 获取股票价格数据
        df = self.data_manager.get_stock_weekly_data(stock_code, market)
        if df.empty:
            raise ValueError(f"无法获取股票{stock_code}的数据")
        
        # 应用日期过滤
        start_index = 0
        end_index = len(df) - 1
        if start_date is not None:
            start_index = df.index.get_loc(start_date)
        if end_date is not None:
            end_index = df.index.get_loc(end_date)
            
        # 初始化信号列表和历史数据
        signals = []
        current_position = 0.0  # 初始仓位为空仓
        last_position = 0.0
        envelope_history = []  # 存储每个时间点的包络线
        extreme_data_history = []  # 存储每个时间点的极值点数据
        
        # 遍历每个时间点，动态计算包络线和极值点
        for i in range(start_index, end_index+1):
            date = df.index[i]
            price = df['Close'].iloc[i]
            
            # 确保有足够的数据点来计算包络线（至少需要20个数据点）
            if i < 20:
                # 对于早期数据点，使用空的历史记录
                envelope_history.append(np.array([]))
                extreme_data_history.append({
                    'extreme_data': {'peaks': [], 'valleys': []},
                    'extreme_data2': {'peaks': [], 'valleys': []}
                })
                continue
            
            # 获取到当前时间点为止的所有价格数据
            current_prices = df['Close'].iloc[:i].values
            
            try:
                # 动态计算包络线
                current_envelope = self.analyzer.extract_hilbert_envelope(current_prices)
                
                # 动态计算极值点
                current_extreme_data = self.analyzer.find_extrema_in_envelope(current_envelope, low_rate=self.analyzer.low_rate)
                current_extreme_data2 = self.analyzer.find_extrema_in_envelope(current_envelope, low_rate=self.analyzer.low_rate2)
                
                # 保存历史数据
                envelope_history.append(current_envelope)
                extreme_data_history.append({
                    'extreme_data': current_extreme_data,
                    'extreme_data2': current_extreme_data2
                })
                
                # 每个时间点都判断仓位
                position, signal_type = self.get_position(current_extreme_data, current_extreme_data2)
                
                # 记录信号（只在仓位变化时记录）
                if position != last_position:
                    if position > last_position:
                        action = "买入"
                    elif position < last_position:
                        action = "卖出"
                        
                    signals.append({
                        'date': date,
                        'price': price,
                        'position': position,
                        'last_position': last_position,
                        'action': action,
                        'signal_type': signal_type
                    })
                    last_position = position
                    
            except Exception as e:
                # 如果计算失败，记录错误并跳过这个时间点
                print(f"计算包络线时出错，日期 {date}: {str(e)}")
                envelope_history.append(np.array([]))
                extreme_data_history.append({
                    'extreme_data': {'peaks': [], 'valleys': []},
                    'extreme_data2': {'peaks': [], 'valleys': []}
                })
                continue
        
        # 转换为DataFrame
        signals_df = pd.DataFrame(signals)
        
        # 返回信号、包络线历史和极值点历史
        return signals_df, envelope_history, extreme_data_history
    
    def backtest_strategy(self, stock_code, market='A-SH', initial_capital=100000, start_date=None, end_date=None):
        """
        包络线趋势跟踪策略的回测函数
        
        参数:
            stock_code: 股票代码
            market: 市场
            initial_capital: 初始资金
            start_date: 开始日期
            end_date: 结束日期
            
        返回:
            backtest_results: 回测结果字典
        """
        
        # 获取股票价格数据
        df = self.data_manager.get_stock_weekly_data(stock_code)
        if df.empty:
            raise ValueError(f"无法获取股票{stock_code}的数据")

        # 获取买卖信号
        signals_df, envelope_history, extreme_data_history = self.generate_signals(stock_code, market, start_date, end_date)
        
        # 应用日期过滤
        if start_date is not None:
            df = df[df.index >= start_date]
        if end_date is not None:
            df = df[df.index <= end_date]
        
        # 初始化回测结果
        capital = initial_capital
        position = 0.0  # 仓位比例
        shares = 0  # 持有股票数量
        cash = initial_capital  # 现金
        portfolio_value = []  # 组合价值历史
        position_history = []  # 仓位历史
        trades = []  # 交易记录
        
        # 遍历每个交易日
        for i in range(len(df)):
            date = df.index[i]
            price = df['Close'].iloc[i]
            
            # 检查是否有信号
            signal = signals_df[signals_df['date'] == date]
            if not signal.empty:
                # 更新仓位
                new_position = signal['position'].iloc[0]
                
                # 计算需要买入或卖出的股票数量
                current_value = cash + shares * price
                target_value = current_value * new_position
                
                if new_position > position:  # 买入
                    buy_value = target_value - shares * price
                    shares_to_buy = buy_value / price
                    shares += shares_to_buy
                    cash -= buy_value
                    
                    trades.append({
                        'date': date,
                        'action': '买入',
                        'price': price,
                        'shares': shares_to_buy,
                        'value': buy_value,
                        'position': new_position,
                        'signal_type': signal['signal_type'].iloc[0]
                    })
                elif new_position < position:  # 卖出
                    shares_to_sell = shares * (position - new_position) / position if position > 0 else 0
                    sell_value = shares_to_sell * price
                    shares -= shares_to_sell
                    cash += sell_value
                    
                    trades.append({
                        'date': date,
                        'action': '卖出',
                        'price': price,
                        'shares': shares_to_sell,
                        'value': sell_value,
                        'position': new_position,
                        'signal_type': signal['signal_type'].iloc[0]
                    })
                
                position = new_position
            
            # 计算当前组合价值
            current_value = cash + shares * price
            portfolio_value.append(current_value)
            position_history.append(position)
        
        # 计算回测指标
        portfolio_value = np.array(portfolio_value)
        returns = np.diff(portfolio_value) / portfolio_value[:-1]
        
        # 计算基准收益（买入并持有策略）
        buy_hold_returns = (df['Close'].values[1:] - df['Close'].values[:-1]) / df['Close'].values[:-1]
        
        # 计算累计收益
        cumulative_returns = (portfolio_value[-1] / initial_capital) - 1
        buy_hold_cumulative_returns = (df['Close'].iloc[-1] / df['Close'].iloc[0]) - 1
        
        # 计算年化收益
        years = len(df) / 52  # 假设一年有52周
        annualized_returns = (portfolio_value[-1] / initial_capital) ** (1/years) - 1
        buy_hold_annualized_returns = (df['Close'].iloc[-1] / df['Close'].iloc[0]) ** (1/years) - 1
        
        # 计算最大回撤
        peak = np.maximum.accumulate(portfolio_value)
        drawdown = (portfolio_value - peak) / peak
        max_drawdown = np.min(drawdown)
        
        # 计算夏普比率（假设无风险利率为0）
        if len(returns) > 0 and np.std(returns) > 0:
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(52)  # 年化
        else:
            sharpe_ratio = 0
        
        # 计算交易次数
        num_trades = len(trades)
        
        # 计算胜率
        profitable_trades = 0
        for i in range(0, len(trades)-1, 2):  # 每一对买入卖出
            if i+1 < len(trades):
                if trades[i]['action'] == '买入' and trades[i+1]['action'] == '卖出':
                    if trades[i+1]['value'] > trades[i]['value']:
                        profitable_trades += 1
        
        win_rate = profitable_trades / (num_trades // 2) if num_trades > 0 else 0
        
        # 获取最后一个时间点的包络线和极值点数据用于绘图
        if len(envelope_history) > 0:
            last_envelope = envelope_history[-1]
            last_extreme_data = extreme_data_history[-1]['extreme_data']
            last_extreme_data2 = extreme_data_history[-1]['extreme_data2']
        else:
            last_envelope = np.array([])
            last_extreme_data = {'peaks': [], 'valleys': []}
            last_extreme_data2 = {'peaks': [], 'valleys': []}
        
        # 整理回测结果
        backtest_results = {
            'stock_code': stock_code,
            'market': market,
            'initial_capital': initial_capital,
            'final_value': portfolio_value[-1],
            'cumulative_returns': cumulative_returns,
            'annualized_returns': annualized_returns,
            'buy_hold_cumulative_returns': buy_hold_cumulative_returns,
            'buy_hold_annualized_returns': buy_hold_annualized_returns,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'num_trades': num_trades,
            'win_rate': win_rate,
            'portfolio_value': portfolio_value,
            'position_history': position_history,
            'trades': pd.DataFrame(trades),
            'signals': signals_df,
            'envelope': last_envelope,
            'extreme_data': last_extreme_data,
            'extreme_data2': last_extreme_data2,
            'dates': df.index,
            'prices': df['Close'].values
        }
        
        return backtest_results
    
    def plot_backtest_results(self, backtest_results, figsize=(15, 10)):
        """
        绘制回测结果图表
        
        参数:
            backtest_results: 回测结果字典
            figsize: 图表大小
        """
        fig, axes = plt.subplots(4, 1, figsize=figsize)
        
        # 子图1：价格和包络线
        ax1 = axes[0]
        ax1.plot(backtest_results['dates'], backtest_results['prices'], label='价格', color='blue')
        ax1.plot(backtest_results['dates'], backtest_results['envelope'], label='包络线', color='orange', alpha=0.7)
        
        # 标记极值点
        peaks = backtest_results['extreme_data']['peaks']
        valleys = backtest_results['extreme_data']['valleys']
        peaks2 = backtest_results['extreme_data2']['peaks']
        valleys2 = backtest_results['extreme_data2']['valleys']
        
        if len(peaks) > 0:
            ax1.scatter(backtest_results['dates'][peaks], backtest_results['prices'][peaks], 
                       color='red', marker='v', label=f'低阈值峰点({len(peaks)})')
        if len(valleys) > 0:
            ax1.scatter(backtest_results['dates'][valleys], backtest_results['prices'][valleys], 
                       color='green', marker='^', label=f'低阈值谷点({len(valleys)})')
        if len(peaks2) > 0:
            ax1.scatter(backtest_results['dates'][peaks2], backtest_results['prices'][peaks2], 
                       color='darkred', marker='v', label=f'高阈值峰点({len(peaks2)})')
        if len(valleys2) > 0:
            ax1.scatter(backtest_results['dates'][valleys2], backtest_results['prices'][valleys2], 
                       color='darkgreen', marker='^', label=f'高阈值谷点({len(valleys2)})')
        
        ax1.set_title(f"{backtest_results['stock_code']} - 价格与包络线")
        ax1.legend()
        
        # 子图2：仓位变化
        ax2 = axes[1]
        ax2.plot(backtest_results['dates'], backtest_results['position_history'], label='仓位', color='purple')
        ax2.set_ylabel('仓位比例')
        ax2.set_ylim(-0.1, 1.1)
        ax2.set_title("仓位变化")
        ax2.legend()
        
        # 子图3：组合价值
        ax3 = axes[2]
        ax3.plot(backtest_results['dates'], backtest_results['portfolio_value'], label='策略组合价值', color='green')
        
        # 计算买入并持有策略的价值
        buy_hold_value = backtest_results['initial_capital'] * (backtest_results['prices'] / backtest_results['prices'][0])
        ax3.plot(backtest_results['dates'], buy_hold_value, label='买入持有价值', color='gray', alpha=0.7)
        
        # 标记买卖点
        trades = backtest_results['trades']
        if not trades.empty:
            buy_trades = trades[trades['action'] == '买入']
            sell_trades = trades[trades['action'] == '卖出']
            
            if not buy_trades.empty:
                ax3.scatter(buy_trades['date'], buy_trades['value'], color='red', marker='^', label='买入')
            if not sell_trades.empty:
                ax3.scatter(sell_trades['date'], sell_trades['value'], color='blue', marker='v', label='卖出')
        
        ax3.set_ylabel('组合价值')
        ax3.set_title("组合价值变化")
        ax3.legend()
        
        # 子图4：回测指标
        ax4 = axes[3]
        ax4.axis('off')
        
        # 显示回测指标
        metrics_text = f"""
        回测指标:
        ----------------------------------------
        股票代码: {backtest_results['stock_code']}
        初始资金: ¥{backtest_results['initial_capital']:,.2f}
        最终价值: ¥{backtest_results['final_value']:,.2f}
        
        策略累计收益: {backtest_results['cumulative_returns']:.2%}
        策略年化收益: {backtest_results['annualized_returns']:.2%}
        买入持有累计收益: {backtest_results['buy_hold_cumulative_returns']:.2%}
        买入持有年化收益: {backtest_results['buy_hold_annualized_returns']:.2%}
        
        最大回撤: {backtest_results['max_drawdown']:.2%}
        夏普比率: {backtest_results['sharpe_ratio']:.2f}
        
        交易次数: {backtest_results['num_trades']}
        胜率: {backtest_results['win_rate']:.2%}
        """
        
        ax4.text(0.1, 0.5, metrics_text, transform=ax4.transAxes, fontsize=10, 
                verticalalignment='center', fontfamily='monospace')
        
        plt.tight_layout()
        return fig