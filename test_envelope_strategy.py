#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试包络线趋势跟踪策略和回测功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from envelope_strategy import EnvelopeStrategy
import pandas as pd
import matplotlib.pyplot as plt

# 设置全局字体为支持中文的字体
plt.rcParams['font.family'] = ['Songti SC', 'Heiti TC', 'sans-serif']
plt.rcParams['font.size'] = 8  # 字体大小
plt.rcParams['axes.unicode_minus'] = False  # 正确显示负号

def test_envelope_strategy():
    """
    测试包络线趋势跟踪策略
    """
    print("=" * 50)
    print("测试包络线趋势跟踪策略")
    print("=" * 50)
    
    # 创建策略实例
    strategy = EnvelopeStrategy()
    
    # 测试股票代码
    test_stocks = [
        #('000001', 'A-SH', '平安银行'),
        #('000002', 'A-SH', '万科A'),
        #('600000', 'A-SH', '浦发银行'),
        ('600036', 'A-SH', '招商银行')
    ]
    
    # 测试每只股票
    for stock_code, market, stock_name in test_stocks:
        print(f"\n测试股票: {stock_name} ({stock_code})")
        print("-" * 30)
        
        try:
                        
            # 生成买卖信号
            signals_df, envelope_history, extreme_data_history = strategy.generate_signals(stock_code, market)
            
            # 显示信号数量
            print(f"买卖信号数量: {len(signals_df)}")
            
            # 显示最后一个时间点的极值点数量
            if len(extreme_data_history) > 0:
                last_extreme_data = extreme_data_history[-1]['extreme_data']
                last_extreme_data2 = extreme_data_history[-1]['extreme_data2']
                print(f"最后一个时间点 - 低阈值包络线: 峰点数: {len(last_extreme_data['peaks'])}, 谷点数: {len(last_extreme_data['valleys'])}")
                print(f"最后一个时间点 - 高阈值包络线: 峰点数: {len(last_extreme_data2['peaks'])}, 谷点数: {len(last_extreme_data2['valleys'])}")
            
            # 显示最近的几个信号
            if len(signals_df) > 0:
                print("\n最近的买卖信号:")
                print(signals_df.tail(5).to_string())
            
            # 执行回测
            backtest_results = strategy.backtest_strategy(stock_code, market)
            
            # 显示回测结果
            print(f"\n回测结果:")
            print(f"初始资金: ¥{backtest_results['initial_capital']:,.2f}")
            print(f"最终价值: ¥{backtest_results['final_value']:,.2f}")
            print(f"累计收益: {backtest_results['cumulative_returns']:.2%}")
            print(f"年化收益: {backtest_results['annualized_returns']:.2%}")
            print(f"买入持有累计收益: {backtest_results['buy_hold_cumulative_returns']:.2%}")
            print(f"买入持有年化收益: {backtest_results['buy_hold_annualized_returns']:.2%}")
            print(f"最大回撤: {backtest_results['max_drawdown']:.2%}")
            print(f"夏普比率: {backtest_results['sharpe_ratio']:.2f}")
            print(f"交易次数: {backtest_results['num_trades']}")
            print(f"胜率: {backtest_results['win_rate']:.2%}")
            
            # 绘制回测结果图表
            fig = strategy.plot_backtest_results(backtest_results)
            plt.savefig(f'{stock_code}_{stock_name}_backtest.png', dpi=300, bbox_inches='tight')
            print(f"图表已保存为: {stock_code}_{stock_name}_backtest.png")
            plt.close()
            
        except Exception as e:
            print(f"测试失败: {str(e)}")
            continue

def test_date_range():
    """
    测试日期范围功能
    """
    print("\n" + "=" * 50)
    print("测试日期范围功能")
    print("=" * 50)
    
    # 创建策略实例
    strategy = EnvelopeStrategy()
    
    # 测试股票代码
    stock_code = '600036'
    market = 'A-SH'
    
    # 设置日期范围
    start_date = '2019-01-04'
    end_date = '2025-11-07'
    
    print(f"测试股票: {stock_code} ({market})")
    print(f"日期范围: {start_date} 至 {end_date}")
    print("-" * 30)
    
    try:
        # 生成买卖信号
        signals_df, envelope_history, extreme_data_history = strategy.generate_signals(
            stock_code, market, start_date=start_date, end_date=end_date
        )
        
        # 显示信号数量
        print(f"买卖信号数量: {len(signals_df)}")
        
        # 显示日期范围
        if len(signals_df) > 0:
            print(f"信号日期范围: {signals_df['date'].min()} 至 {signals_df['date'].max()}")
        
        # 执行回测
        backtest_results = strategy.backtest_strategy(
            stock_code, market, start_date=start_date, end_date=end_date
        )
        
        # 显示回测结果
        print(f"\n回测结果:")
        print(f"初始资金: ¥{backtest_results['initial_capital']:,.2f}")
        print(f"最终价值: ¥{backtest_results['final_value']:,.2f}")
        print(f"累计收益: {backtest_results['cumulative_returns']:.2%}")
        print(f"年化收益: {backtest_results['annualized_returns']:.2%}")
        print(f"最大回撤: {backtest_results['max_drawdown']:.2%}")
        print(f"交易次数: {backtest_results['num_trades']}")
        print(f"胜率: {backtest_results['win_rate']:.2%}")
        
        # 绘制回测结果图表
        fig = strategy.plot_backtest_results(backtest_results)
        plt.savefig(f'{stock_code}_date_range_backtest.png', dpi=300, bbox_inches='tight')
        print(f"图表已保存为: {stock_code}_date_range_backtest.png")
        plt.close()
        
        print("\n✓ 日期范围测试成功")
        
    except Exception as e:
        print(f"✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

def test_position_logic():
    """
    测试仓位判断逻辑
    """
    print("\n" + "=" * 50)
    print("测试仓位判断逻辑")
    print("=" * 50)
    
    # 创建策略实例
    strategy = EnvelopeStrategy()
    
    # 测试案例
    test_cases = [
        {
            'name': '情形1: 双谷点',
            'extreme_data': {'peaks': [], 'valleys': [10, 20, 30]},
            'extreme_data2': {'peaks': [], 'valleys': [8, 18, 28]},
            'expected_position': 1.0
        },
        {
            'name': '情形2: 双峰点',
            'extreme_data': {'peaks': [10, 20, 30], 'valleys': []},
            'extreme_data2': {'peaks': [8, 18, 28], 'valleys': []},
            'expected_position': 0.0
        },
        {
            'name': '情形3: 低阈值谷点+高阈值峰点',
            'extreme_data': {'peaks': [], 'valleys': [10, 20, 30]},
            'extreme_data2': {'peaks': [8, 18, 28], 'valleys': []},
            'expected_position': 0.7
        },
        {
            'name': '情形4: 低阈值峰点+高阈值谷点',
            'extreme_data': {'peaks': [10, 20, 30], 'valleys': []},
            'extreme_data2': {'peaks': [], 'valleys': [8, 18, 28]},
            'expected_position': 0.3
        }
    ]
    
    for test_case in test_cases:
        print(f"\n测试案例: {test_case['name']}")
        print("-" * 30)
        
        position, signal_type = strategy.get_position(
            test_case['extreme_data'], 
            test_case['extreme_data2']
        )
        
        print(f"预期仓位: {test_case['expected_position']}")
        print(f"实际仓位: {position}")
        print(f"信号类型: {signal_type}")
        
        if position == test_case['expected_position']:
            print("✓ 测试通过")
        else:
            print("✗ 测试失败")

if __name__ == "__main__":
    # 测试仓位判断逻辑
    #test_position_logic()
    
    # 测试日期范围功能
    test_date_range()
    
    # 测试包络线趋势跟踪策略
    #test_envelope_strategy()
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)