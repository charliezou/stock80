import os
import sqlite3
import yfinance as yf
from configparser import ConfigParser
from datetime import datetime
from typing import List, Tuple
import numpy as np
import pandas as pd
import csv

class StockMetaDB:
    def __init__(self, storage_path: str, db_name: str):
        # 初始化存储路径
        os.makedirs(storage_path, exist_ok=True)
        
        # 初始化元数据库
        self.db_conn = sqlite3.connect(os.path.join(storage_path, db_name))
        self._create_tables()

    def _create_tables(self):
        '''创建元数据表结构'''
        cursor = self.db_conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks_info (
                code TEXT NOT NULL,
                market TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                data_path TEXT NOT NULL,
                shortName TEXT NOT NULL,
                sector TEXT NOT NULL,
                marketCap TEXT NOT NULL,
                trailingPE TEXT NOT NULL,
                dividendYield TEXT NOT NULL,
                PRIMARY KEY (code, market)
            )
        ''')
        self.db_conn.commit()

    def update(self, code: str, market: str, start_date: str, end_date: str, data_path: str, info):
        '''更新元数据'''
        now = datetime.now().isoformat()
        cursor = self.db_conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO stocks_info
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        ''', (code, market, start_date, end_date, now, data_path, info.get("shortName", "N/A"), info.get("sector", "N/A"), info.get("marketCap", "N/A"), info.get("trailingPE", "N/A"), info.get("dividendYield", "N/A")))
        self.db_conn.commit()

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
            'data_path': row[5],
            'shortName': row[6],
            'sector': row[7],
            'marketCap': row[8],
            'trailingPE': row[9],
            'dividendYield': row[10],
        } for row in rows]

    def get_stock_info(self, code: str, market: str):
        '''获取指定股票的元数据'''
        cursor = self.db_conn.cursor()
        cursor.execute('SELECT * FROM stocks_info WHERE code =? and market =?', (code,market,))
        result = cursor.fetchone()
        if not result:
            return None
        return {
            'code': result[0],
            'market': result[1],
            'start_date': result[2],
            'end_date': result[3],
            'last_updated': result[4],
            'data_path': result[5],
            'shortName': result[6],
            'sector': result[7],
            'marketCap': result[8],
            'trailingPE': result[9],
            'dividendYield': result[10],
        }

    def delete(self, code: str, market: str) -> bool:
        '''删除指定股票的元数据和数据文件'''
        cursor = self.db_conn.cursor()
        cursor.execute('SELECT data_path FROM stocks_info WHERE code =? and market =?', (code,market,))
        self.db_conn.commit()
        return True

class StockDataMgr:
    def __init__(self):
        self.config = ConfigParser()
        self.config.read('config.ini')

        # 初始化存储路径
        self.storage_path = self.config.get('Data', 'storage_path')
        os.makedirs(self.storage_path, exist_ok=True)

        # 初始化元数据库
        self.metadata_db = StockMetaDB(self.storage_path, self.config.get('Data', 'db_name'))

    def _get_yf_symbol(self, code, market):
        '''根据市场类型获取股票代码后缀'''
        if market == 'cn':
            if code.startswith('6'):
                return f"{code}.SS"
            elif code.startswith('0') or code.startswith('3'):
                return f"{code}.SZ"
        elif market == 'hk':
            return f"{code}.HK"       
        else:
            return code

    def resample_weekly(self, data):
        """将日线数据重采样为周线数据"""
        return data.resample('W-FRI').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum',
        }).dropna()     

    #todo: 优化从qlib下载数据

    def download(self, code, market, start_date= None):
        '''下载股票数据并存储'''
        if start_date is None:
            start_date = self.config.get('Data','start_date')

        symbol = self._get_yf_symbol(code, market)
        try:
            # 获取yfinance数据
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.now()
            end_date = end.strftime('%Y-%m-%d')

            # 生成存储路径
            base_path = os.path.join(self.storage_path, f"{market}_data")
            os.makedirs(base_path, exist_ok=True)

            # 下载日线数据           
            data = yf.download(symbol, group_by="ticker", start=start, end=end, interval='1D', auto_adjust=True)
            if data.empty:
                print(f"No data available for {symbol}")
                return False
            daily_data = data[symbol]
            daily_data = daily_data.dropna().drop_duplicates()

            # 重采样为周线数据
            weekly_data = self.resample_weekly(daily_data)
            
            # 保存数据到CSV
            daily_path = f"{base_path}/{code}_daily.csv"
            weekly_path = f"{base_path}/{code}_weekly.csv"
            daily_data.to_csv(daily_path)
            weekly_data.to_csv(weekly_path)

            info = yf.Ticker(symbol).info

            # 更新元数据库
            self.metadata_db.update(code, market, start_date, end_date, base_path, info)
            return True
        except Exception as e:
            print(f"Failed to download: {str(e)}")
            return False

    def batch_download(self, codes, market, start_date= None):
        '''批量下载股票数据'''
        success_codes = []
        '''下载股票数据并存储'''
        if start_date is None:
            start_date = self.config.get('Data','start_date')

        # 生成存储路径
        base_path = os.path.join(self.storage_path, f"{market}_data")
        os.makedirs(base_path, exist_ok=True)
        
        symbols = [self._get_yf_symbol(code, market) for code, market in codes]
        symbol_code = dict(zip(symbols, codes))
        try:
            # 获取yfinance数据
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.now()
            end_date = end.strftime('%Y-%m-%d')

            # 下载日线数据           
            datas = yf.download(symbols, group_by="ticker", start=start, end=end, interval='1D', auto_adjust=True)
            infos = yf.Tickers(symbols).tickers    
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

                info = infos[symbol].info
                # 更新元数据库
                self.metadata_db.update(code, market, start_date, end_date, base_path, info)
                success_codes.append(code)
            return success_codes
        except Exception as e:
            print(f"Failed to download: {str(e)}")
            return success_codes

    def read_instrument(self, instrument, market):
        '''从指定文件读取代码'''
        codes = []
        try:
            file_path = os.path.join(self.storage_path, f"{instrument}.txt")
            with open(file_path, 'r', encoding='utf-8') as file:
                # 使用 csv.reader 读取文件，指定分隔符为制表符
                reader = csv.reader(file, delimiter='\t')
                for row in reader:
                    if row:  # 确保行不为空
                        if market == 'cn' or market == 'hk':
                            codes.append(row[0][2:])
                        elif market == 'us':
                            codes.append(row[0])  # 添加第一列（股票代码）到列表
        except FileNotFoundError:
            print(f"文件未找到：{file_path}")
        except Exception as e:
            print(f"读取文件时发生错误：{e}")

        return codes
    

    def instrument_batch_download(self, instrument, market, start_date= None):
        '''从指定文件读取代码批量下载'''
        codes = self.read_instrument(instrument, market)
        if codes==[]:
            return False
        return self.batch_download(codes, market, start_date), codes

    def get_symbol(self, code, market, data_type = "day"):
        '''获取指定股票的日线数据'''
        #todo: 优化从catch中获取数据
        base_path = os.path.join(self.storage_path, f"{market}_data")
        if data_type == "day":
            file = f"{base_path}/{code}_daily.csv"
        elif data_type == "week":
            file = f"{base_path}/{code}_weekly.csv"
        if not os.path.exists(file):
            return None
        return pd.read_csv(file, index_col=0, parse_dates=True)

    def get_symbols(self, codes, market, data_type = "day"):
        '''获取指定股票的日线数据'''
        #todo: 优化从catch中获取数据
        base_path = os.path.join(self.storage_path, f"{market}_data")
        if codes==[]:
            return None
        result = {}
        for code in codes:           
            if data_type == "day":
                file = f"{base_path}/{code}_daily.csv"  
            elif data_type == "week":
                file = f"{base_path}/{code}_weekly.csv"  
            if not os.path.exists(file):
                continue
            result[(code,market,data_type)] = pd.read_csv(file, index_col=0, parse_dates=True)
        return result

    def get_instrument_symbols(self, instrument, market, data_type = "day"):
        '''从指定文件读取代码批量下载'''
        codes = self.read_instrument(instrument, market)
        if codes==[]:
            return None
        return self.get_symbols(codes, market, data_type), codes

    def get_all_stocks_info(self) -> list:
        '''获取所有股票信息'''
        return self.metadata_db.get_all_stocks()

    def get_stock_info(self, code: str, market: str):
        '''获取指定股票的元数据'''
        return self.metadata_db.get_stock_info(code, market)

    def delete(self, code: str, market: str) -> bool:
        '''删除指定股票的元数据和数据文件'''
        stock_info = self.metadata_db.get_stock_info(code, market)
        if not stock_info:
            return False
        base_path = stock_info['data_path']
        daily_file = f"{base_path}/{code}_daily.csv"
        weekly_file = f"{base_path}/{code}_weekly.csv"
        if os.path.exists(daily_file):
            os.remove(daily_file)
        if os.path.exists(weekly_file):
            os.remove(weekly_file)
        self.metadata_db.delete(code, market)
        return True


