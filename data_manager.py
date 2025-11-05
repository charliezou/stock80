import os
import sqlite3
import yfinance as yf
from configparser import ConfigParser
from datetime import datetime
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

    def _get_symbol_suffix(self, market: str) -> str:
        '''根据市场类型获取股票代码后缀'''
        return {
            'A-SH': '.SS',   # 沪市
            'A-SZ': '.SZ',   # 深市
            'HK': '.HK',     # 港股
            'US': ''         # 美股
        }.get(market, '')

    def resample_weekly(self, data):
        """将日线数据重采样为周线数据"""
        return data.resample('W-FRI').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum',
        }).dropna()

    def download_data(self, codes: List[Tuple[str, str]]):
        success_codes = []
        '''下载股票数据并存储'''
        for code, market in codes:
            symbol = code + self._get_symbol_suffix(market)
            try:
                # 获取yfinance数据
                start_date = self.config.get('Data', 'start_date')
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.now()
                end_date = end.strftime('%Y-%m-%d')
                
                # 下载日线和周线数据
                data = yf.download(symbol, start=start, end=end, interval='1D', auto_adjust=True)
                if data.empty:
                    print(f"No data available for {symbol}")
                    continue
                data = data.drop_duplicates()
                daily_data = pd.DataFrame({
                    'Open' : data['Open'][symbol],                    
                    'High' : data['High'][symbol],
                    'Low' : data['Low'][symbol],
                    'Close' : data['Close'][symbol],
                    'Volume' : data['Volume'][symbol],
                })
                weekly_data = self.resample_weekly(daily_data)
                
                # 保存数据到CSV
                base_path = os.path.join(self.storage_path, code)
                daily_path = f"{base_path}_daily.csv"
                weekly_path = f"{base_path}_weekly.csv"
                
                daily_data.to_csv(daily_path)
                weekly_data.to_csv(weekly_path)
                
                # 更新元数据库
                now = datetime.now().isoformat()
                cursor = self.db_conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO stocks_info
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (code, market, start_date, end_date, now, base_path))

                success_codes.append(code)
                
            except Exception as e:
                print(f"Failed to download {symbol}: {str(e)}")
        
        self.db_conn.commit()
        return success_codes

    def batch_download(self, codes, start_date= None):
        '''批量下载股票数据'''
        success_codes = []
        '''下载股票数据并存储'''
        if start_date is None:
            start_date = self.config.get('Data','start_date')

        # 生成存储路径
        base_path = self.storage_path
        os.makedirs(base_path, exist_ok=True)
        
        symbols = [code + self._get_symbol_suffix(market) for code, market in codes]
        symbol_code = dict(zip(symbols, codes))
        try:
            # 获取yfinance数据
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.now()
            end_date = end.strftime('%Y-%m-%d')

            # 下载日线数据           
            datas = yf.download(symbols, group_by="ticker", start=start, end=end, interval='1D', auto_adjust=True)
            #infos = yf.Tickers(symbols).tickers    
            if datas.empty:
                print(f"No data available for all symbols")
                return success_codes
            
            for symbol in symbols:
                if symbol not in data.columns:
                    print(f"No data available for {symbol}")
                    continue
                code = symbol_code[symbol]
                # 处理数据
                daily_data = datas[symbol]
                daily_data = daily_data.dropna().drop_duplicates()

                # 重采样为周线数据
                weekly_data = self.resample_weekly(daily_data)
                
                # 保存数据到CSV
                daily_path = f"{base_path}/{code}_daily.csv"
                weekly_path = f"{base_path}/{code}_weekly.csv"
                daily_data.to_csv(daily_path)
                weekly_data.to_csv(weekly_path)

                #info = infos[symbol].info
                #print(info)
                # 更新元数据库
                now = datetime.now().isoformat()
                cursor = self.db_conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO stocks_info
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (code, market, start_date, end_date, now, base_path))
                success_codes.append(code)
            return success_codes
        except Exception as e:
            print(f"Failed to download: {str(e)}")
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
        df =  self.get_stock_weekly_data(symbol)
        if df is None:
            return None
        return df['Close']
    
    def get_stock_market(self, code):
        """获取股票市场信息"""
        cursor = self.db_conn.cursor()
        cursor.execute('SELECT market FROM stocks_info WHERE code = ?', (code,))
        result = cursor.fetchone()
        return result[0] if result else 'US'