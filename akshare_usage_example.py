#!/usr/bin/env python3
"""
基于akshare的data_manager.py使用示例
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_manager_akshare import StockDataManager
import pandas as pd

def example_basic_usage():
    """基本使用示例"""
    print("=== 基本使用示例 ===")
    
    # 1. 创建数据管理器实例
    data_mgr = StockDataManager()
    print("1. 数据管理器实例创建成功")
    
    # 2. 获取所有股票信息
    all_stocks = data_mgr.get_all_stocks()
    print(f"2. 当前存储的股票数量: {len(all_stocks)}")
    
    if all_stocks:
        # 显示前5个股票信息
        for i, stock in enumerate(all_stocks[:5]):
            print(f"   {i+1}. {stock['code']} ({stock['market']}) - 最后更新: {stock['last_updated'][:10]}")
    
    # 3. 检查数据是否需要更新
    if all_stocks:
        sample_stock = all_stocks[0]['code']
        needs_update = data_mgr.needs_update(sample_stock)
        print(f"3. 股票 {sample_stock} 需要更新: {needs_update}")

def example_volume_ratio_calculation():
    """量比计算示例"""
    print("\n=== 量比计算示例 ===")
    
    # 创建模拟数据
    dates = pd.date_range('2024-01-01', periods=10, freq='W')
    volumes = [100, 120, 110, 130, 140, 150, 160, 170, 180, 190]
    
    data = pd.DataFrame({
        'Volume': volumes
    }, index=dates)
    
    data_mgr = StockDataManager()
    
    # 计算量比
    result = data_mgr.calculate_volume_ratio(data, window_size=5)
    
    print("原始成交量数据:")
    for i, (date, volume) in enumerate(zip(dates, volumes)):
        print(f"  第{i+1}周: {date.strftime('%Y-%m-%d')} - 成交量: {volume}")
    
    print("\n量比计算结果:")
    for i, (date, volume_ratio) in enumerate(zip(result.index, result['Volume_Ratio'])):
        if pd.notna(volume_ratio):
            print(f"  第{i+1}周: {date.strftime('%Y-%m-%d')} - 量比: {volume_ratio:.3f}")

def example_data_resampling():
    """数据重采样示例"""
    print("\n=== 数据重采样示例 ===")
    
    # 创建模拟日线数据
    dates = pd.date_range('2024-01-01', periods=15, freq='D')
    data = pd.DataFrame({
        'Open': [100 + i for i in range(15)],
        'High': [105 + i for i in range(15)],
        'Low': [95 + i for i in range(15)],
        'Close': [102 + i for i in range(15)],
        'Volume': [1000 + i*100 for i in range(15)]
    }, index=dates)
    
    data_mgr = StockDataManager()
    
    # 重采样为周线数据
    weekly_data = data_mgr.resample_weekly(data)
    
    print("原始日线数据:")
    print(f"  时间范围: {data.index[0].strftime('%Y-%m-%d')} 到 {data.index[-1].strftime('%Y-%m-%d')}")
    print(f"  数据点数: {len(data)}")
    
    print("\n重采样后的周线数据:")
    print(f"  时间范围: {weekly_data.index[0].strftime('%Y-%m-%d')} 到 {weekly_data.index[-1].strftime('%Y-%m-%d')}")
    print(f"  数据点数: {len(weekly_data)}")
    
    print("\n周线数据详情:")
    for i, (date, row) in enumerate(weekly_data.iterrows()):
        print(f"  第{i+1}周 ({date.strftime('%Y-%m-%d')}):")
        print(f"    开盘: {row['Open']:.2f}, 最高: {row['High']:.2f}, 最低: {row['Low']:.2f}, 收盘: {row['Close']:.2f}")
        print(f"    成交量: {row['Volume']:.0f}")

def example_stock_data_retrieval():
    """股票数据获取示例"""
    print("\n=== 股票数据获取示例 ===")
    
    data_mgr = StockDataManager()
    all_stocks = data_mgr.get_all_stocks()
    
    if all_stocks:
        # 获取第一个股票的周线数据
        sample_stock = all_stocks[0]['code']
        print(f"获取股票 {sample_stock} 的周线数据...")
        
        weekly_data = data_mgr.get_stock_weekly_data(sample_stock)
        
        if weekly_data is not None:
            print(f"成功获取数据，数据形状: {weekly_data.shape}")
            print(f"时间范围: {weekly_data.index[0].strftime('%Y-%m-%d')} 到 {weekly_data.index[-1].strftime('%Y-%m-%d')}")
            
            # 显示最新5周的数据
            recent_data = weekly_data.tail(5)
            print("\n最新5周数据:")
            for date, row in recent_data.iterrows():
                print(f"  {date.strftime('%Y-%m-%d')}: 开盘{row['Open']:.2f}, 收盘{row['Close']:.2f}, 成交量{row['Volume']:.0f}")
        else:
            print("未找到数据文件")
    else:
        print("当前没有存储的股票数据")

def main():
    """主函数"""
    print("基于akshare的data_manager.py使用示例")
    print("=" * 50)
    
    examples = [
        ("基本使用", example_basic_usage),
        ("量比计算", example_volume_ratio_calculation),
        ("数据重采样", example_data_resampling),
        ("数据获取", example_stock_data_retrieval)
    ]
    
    for example_name, example_func in examples:
        try:
            example_func()
            print("\n" + "-" * 50 + "\n")
        except Exception as e:
            print(f"示例 '{example_name}' 执行失败: {str(e)}")
            print("\n" + "-" * 50 + "\n")
    
    print("使用示例执行完成！")
    print("\n主要功能总结:")
    print("• 支持多种市场数据下载 (A股、港股、美股)")
    print("• 自动数据重采样 (日线→周线)")
    print("• 量比计算功能")
    print("• 元数据管理")
    print("• 数据更新检查")
    print("• 批量操作支持")

if __name__ == "__main__":
    main()