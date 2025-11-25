import os
import sqlite3
import akshare as ak
from configparser import ConfigParser
from datetime import datetime, timedelta
from typing import List, Tuple
import numpy as np
import pandas as pd


class StockDataManager:
    def __init__(self):
        self.config = ConfigParser()
        self.config.read('config.ini')
        
        # 初始化存储路径
        self.storage_path = self.config.get('Data', 'storage_path')
        os.makedirs(self.storage_path, exist_ok=True)
        
        # 初始化元数据库
        self.db_conn = sqlite3.connect(os.path.join(self.storage_path, 'metadata.db'))
        self._create_tables()

    def _create_tables(self):
        '''创建元数据表结构'''
        cursor = self.db_conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks_info (
                code TEXT PRIMARY KEY,
                market TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                data_path TEXT NOT NULL
            )
        ''')
        self.db_conn.commit()

    def _get_akshake_symbol(self, code, market):
        '''根据市场类型变换股票代码格式'''
        if market in ['A-SH', 'A-SZ']:
            return code
        elif market == 'HK':
            return f"0{code}"
        elif market == 'US':
            return f"105.{code}"
        elif market == 'DP':
            if code in ['^DJI', '^IXIC']:
                return code.replace('^', '.')
            elif code == '^HSI':
                return 'HSI'
            elif code in ['000001.SS', '399001.SZ', '399006.SZ']:
                return code.replace('.SZ', '').replace('.SS', '')
        return code

    def _get_akshare_function(self, market: str):
        '''根据市场类型获取akshare对应的数据获取函数'''
        market_functions = {
            'A-SH': ak.stock_zh_a_hist,           # 沪市A股
            'A-SZ': ak.stock_zh_a_hist,           # 深市A股
            'HK': ak.stock_hk_hist,               # 港股
            'US': ak.stock_us_hist,               # 美股
            'DP': ak.stock_zh_index_hist_csindex  # 默认使用A股
        }
        return market_functions.get(market, ak.stock_zh_a_hist)

    def _get_index_function(self, symbol: str):
        '''根据指数代码获取对应的akshare函数'''
        index_functions = {
            '^DJI': ak.index_us_stock_sina,             # 道琼斯指数
            '^IXIC': ak.index_us_stock_sina,            # 纳斯达克指数
            '^HSI': ak.stock_hk_daily,             # 恒生指数
            '000001': ak.stock_zh_index_hist_csindex,  # 上证指数
            '399001': ak.stock_zh_index_hist_csindex,  # 深证成指
            '399006': ak.stock_zh_index_hist_csindex   # 创业板指
        }
        
        # 默认使用A股指数函数
        return index_functions.get(symbol, ak.stock_zh_index_hist_csindex)

    def resample_weekly(self, data):
        """将日线数据重采样为周线数据"""
        return data.resample('W-FRI').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum',
        }).dropna()

    def calculate_volume_ratio(self, data, window_size=5):
        """计算量比"""
        mean_previous_volume = data['Volume'].rolling(window=window_size, min_periods=1).mean().shift(1)
        data['Volume_Ratio'] = data['Volume'] / mean_previous_volume
        return data

    def download_data(self, codes: List[Tuple[str, str]]):
        '''下载股票数据并存储'''
        success_codes = []
        
        for code, market in codes:
            try:
                # 获取akshare数据获取函数
                ak_function = self._get_index_function(code) if market== 'DP' else self._get_akshare_function(market)
                
                # 设置时间范围
                start_date = self.config.get('Data', 'start_date_akshare')
                end_date = datetime.now().strftime('%Y%m%d')

                symbol = self._get_akshake_symbol(code, market)
                
                # 下载数据
                if market in ['A-SH', 'A-SZ','HK','US']:
                    # A股数据
                    data = ak_function(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
                elif market == 'DP':
                    # 指数数据
                    if code in ['^DJI', '^IXIC']:
                        data = ak_function(symbol=symbol)
                    elif code in ['^HSI']:
                        data = ak_function(symbol=symbol, adjust="qfq")
                    elif code in ['000001.SS', '399001.SZ', '399006.SZ']:
                        data = ak_function(symbol=symbol, start_date=start_date, end_date=end_date)
                
                if data.empty:
                    print(f"No data available for {code} ({market})")
                    continue
                
                # 标准化数据格式
                data = self._standardize_data_format(data, market, code)
                
                # 重采样为周线数据
                weekly_data = self.resample_weekly(data)
                
                # 保存数据到CSV
                base_path = os.path.join(self.storage_path, code)
                daily_path = f"{base_path}_daily.csv"
                weekly_path = f"{base_path}_weekly.csv"
                
                data.to_csv(daily_path)
                weekly_data.to_csv(weekly_path)
                
                # 更新元数据库
                now = datetime.now().isoformat()
                cursor = self.db_conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO stocks_info
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (code, market, start_date, end_date, now, base_path))

                success_codes.append(code)
                print(f"Successfully downloaded data for {code} ({market})")
                
            except Exception as e:
                print(f"Failed to download {code} ({market}): {str(e)}")
        
        self.db_conn.commit()
        return success_codes

    def _standardize_data_format(self, data, market, code):
        """标准化数据格式"""
        # 重命名列以统一格式
        column_mapping = {
            'A-SH': {'日期': 'Date', '开盘': 'Open', '最高': 'High', '最低': 'Low', '收盘': 'Close', '成交量': 'Volume'},
            'A-SZ': {'日期': 'Date', '开盘': 'Open', '最高': 'High', '最低': 'Low', '收盘': 'Close', '成交量': 'Volume'},
            'HK': {'date': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'},
            'US': {'date': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'},
            'DP': {'日期': 'Date', '开盘': 'Open', '最高': 'High', '最低': 'Low', '收盘': 'Close', '成交量': 'Volume'}
        }
        mapping = column_mapping.get(market, {})

        if market == 'DP':
            if code in ['^DJI', '^IXIC']:
                mapping = column_mapping.get('US', {})
            elif code in ['^HSI']:
                mapping = column_mapping.get('HK', {})       

        data = data.rename(columns=mapping)
        
        # 设置日期索引
        if 'Date' in data.columns:
            data['Date'] = pd.to_datetime(data['Date'])
            data = data.set_index('Date')
        
        # 确保数据类型正确
        numeric_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in numeric_columns:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')
        data = data[['Open', 'High', 'Low', 'Close', 'Volume']]
        return data.dropna()

    def batch_download(self, codes, market, start_date=None):
        '''批量下载股票数据'''
        success_codes = []
        
        if start_date is None:
            start_date = self.config.get('Data', 'start_date')
        
        for code in codes:
            try:
                # 将单个股票代码转换为列表格式
                codes_list = [(code, market)]
                # 使用单个下载方法
                result = self.download_data(codes_list)
                if result:
                    success_codes.extend(result)
            except Exception as e:
                print(f"Failed to download {code} ({market}): {str(e)}")
        
        return success_codes

    def needs_update(self, code: str) -> bool:
        '''检查数据是否需要更新'''
        cursor = self.db_conn.cursor()
        cursor.execute('''
            SELECT last_updated FROM stocks_info WHERE code = ?
        ''', (code,))
        result = cursor.fetchone()
        
        if not result:
            return True
        
        last_updated = datetime.fromisoformat(result[0])
        refresh_days = self.config.getint('Data', 'refresh_days')
        return (datetime.now() - last_updated).days >= refresh_days

    def validate_data(self, code: str) -> bool:
        '''验证数据完整性'''
        base_path = os.path.join(self.storage_path, code)
        return os.path.exists(f"{base_path}_daily.csv") and \
               os.path.exists(f"{base_path}_weekly.csv")

    def delete_stock_data(self, code: str) -> bool:
        '''删除指定股票的元数据和数据文件'''
        cursor = self.db_conn.cursor()
        cursor.execute('SELECT data_path FROM stocks_info WHERE code = ?', (code,))
        result = cursor.fetchone()
        if not result:
            return False
        
        data_path = result[0]
        daily_file = f"{data_path}_daily.csv"
        weekly_file = f"{data_path}_weekly.csv"
        try:
            os.remove(daily_file)
            os.remove(weekly_file)
        except FileNotFoundError:
            pass
        
        cursor.execute('DELETE FROM stocks_info WHERE code = ?', (code,))
        self.db_conn.commit()
        return True

    def get_all_stocks(self) -> list:
        '''获取所有股票信息'''
        cursor = self.db_conn.cursor()
        cursor.execute('SELECT * FROM stocks_info')
        rows = cursor.fetchall()
        return [{
            'code': row[0],
            'market': row[1],
            'start_date': row[2],
            'end_date': row[3],
            'last_updated': row[4],
            'data_path': row[5]
        } for row in rows]

    def get_stock_data(self, code: str):
        '''获取指定股票的日线数据'''
        base_path = os.path.join(self.storage_path, code)
        daily_file = f"{base_path}_daily.csv"
        if not os.path.exists(daily_file):
            return None

        return pd.read_csv(daily_file, index_col=0, parse_dates=True)

    def get_stock_weekly_data(self, code: str):
        '''获取指定股票的周线数据'''
        base_path = os.path.join(self.storage_path, code)
        weekly_file = f"{base_path}_weekly.csv"
        if not os.path.exists(weekly_file):
            return None
        return pd.read_csv(weekly_file, index_col=0, parse_dates=True)
    
    def get_index_weekly_data(self, symbol):
        """获取指数周线数据"""
        df = self.get_stock_weekly_data(symbol)
        if df is None:
            return None
        return df['Close']
    
    def get_stock_market(self, code):
        """获取股票市场信息"""
        cursor = self.db_conn.cursor()
        cursor.execute('SELECT market FROM stocks_info WHERE code = ?', (code,))
        result = cursor.fetchone()
        return result[0] if result else 'US'

    def update_all_data(self):
        """更新所有股票数据"""
        all_stocks = self.get_all_stocks()
        codes_to_update = []
        
        for stock in all_stocks:
            if self.needs_update(stock['code']):
                codes_to_update.append((stock['code'], stock['market']))
        
        if codes_to_update:
            print(f"Updating data for {len(codes_to_update)} stocks...")
            return self.download_data(codes_to_update)
        else:
            print("All data is up to date.")
            return []


# 使用示例
if __name__ == "__main__":
    # 创建数据管理器实例
    data_mgr = StockDataManager()
    
    # 下载A股数据示例
    a_shares = [('000001', 'A-SH'), ('000002', 'A-SZ')]
    success = data_mgr.download_data(a_shares)
    print(f"Downloaded {len(success)} A-share stocks")
    
    # 下载指数数据示例
    indices = ['000001', '399001']  # 上证指数，深证成指
    success = data_mgr.download_index_data(indices)
    print(f"Downloaded {len(success)} indices")
    
    # 获取数据示例
    df = data_mgr.get_stock_weekly_data('000001')
    if df is not None:
        print(f"Retrieved data for 000001, shape: {df.shape}")