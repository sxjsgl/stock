import tushare as ts
import time
import pandas as pd
import sqlite3
import numpy as np
import os
import sys
import re
from configparser import ConfigParser
from multiprocessing import Pool

root = os.path.dirname(os.path.abspath(__file__)) + os.sep
config_file = os.path.abspath(root+'../config.ini')
config = ConfigParser()
config.read(config_file)


def refresh_stock_daily_process(tday, db_file, comment=None):
    api = ts.pro_api(config['account']['ts_token'])
    conn = sqlite3.connect(db_file)
    conn.execute('PRAGMA synchronous = OFF')
    while True:
        try:
            df1 = api.daily(trade_date=tday, fields='ts_code, trade_date, open, high, low, close, vol, amount')
            df2 = api.adj_factor(trade_date=tday, fields='ts_code, adj_factor')
            break
        except BaseException:
            time.sleep(1)
    if not df1.empty:
        df = df1.merge(df2, how='left')
        df.to_sql(tday, conn, if_exists='replace', index=False)
    conn.close()
    if comment is not None:
        print(comment)


class StockDb:
    file = root + 'stock.db'
    api = ts.pro_api(config['account']['ts_token'])
    trade_cal = api.trade_cal(exchange='SSE', is_open=1)  # 交易日历
    trade_cal.sort_values(by='cal_date', axis=0, ascending=True, inplace=True)
    trade_cal.reset_index(drop=True, inplace=True)


    def __init__(self):
        self.conn = sqlite3.connect(self.file)
        self.cursor = self.conn.cursor()
        table = []
        for temp in self.cursor.execute("select name from sqlite_master where type='table'").fetchall():
            if re.match('\d{8}', temp[0]):
                table.append(temp[0])
        # ------------------rs  未记录的下个交易日
        if table:
            self.rs = self.next_tday(table[-1])
        else:
            self.rs = '19900101'
        # ------------------re
        self.re = self.last_tday()
        self.refresh()

    def __del__(self):
        self.cursor.close()
        self.conn.close()

    def tday_span(self, ts='19900101', te='30000101'):
        te = min(self.last_tday(), te)
        res = self.trade_cal.loc[
            (self.trade_cal.cal_date >= ts) & (self.trade_cal.cal_date <= te), 'cal_date'].values.tolist()
        return res

    def last_tday(self, tday=None):
        if tday is None:
            tday = time.strftime('%Y%m%d', time.localtime())
        res = self.trade_cal.loc[self.trade_cal.cal_date < tday, 'cal_date'].values[-1]
        return res

    def next_tday(self, tday=None):
        if tday is None:
            tday = time.strftime('%Y%m%d', time.localtime())
        res = self.trade_cal.loc[self.trade_cal.cal_date > tday, 'cal_date'].values[0]
        return res

    def refresh(self):
        if self.rs <= self.re:  # 今天更新过就不更新了
            trs1 = time.time()
            self.refresh_stock_basic()
            self.refresh_stock_data()
            trs2 = time.time()
            print('refresh takes %5.1f minutes' % ((trs2 - trs1) / 60.0))
        else:
            print("It's the latest")

    def refresh_stock_basic(self):
        print('refreshing stock basic')
        while True:
            try:
                df_trade_basic = self.api.daily_basic(trade_date=self.re)
                df_stock_basic = self.api.stock_basic(exchange='', list_status='L')
                break
            except BaseException:
                time.sleep(1)
        df = df_trade_basic.merge(df_stock_basic, how='left')
        df.to_sql('stock_basic', self.conn, if_exists='replace', index=False)
        print('stock basic refresh complete')

    def refresh_stock_data(self):
        print('refreshing stock data')
        p = Pool()
        temp = self.tday_span(self.rs, self.re)
        for (i, tday) in enumerate(temp):
            p.apply_async(refresh_stock_daily_process, (tday, self.file, '%4d / %4d' % (i, len(temp))))
        p.close()
        p.join()
        print('stock data refresh complete')

    def get_stock_basic(self):
        self.cursor.execute('select * from stock_basic')
        df = pd.DataFrame(self.cursor.fetchall(), columns=[x[0] for x in self.cursor.description])
        return df

    def get_stock_data(self, code, ts='19900101', te='30000101'):
        list_date = self.cursor.execute('select list_date from stock_basic where ts_code="%s"' % (code,)).fetchall()
        if not list_date: # 没有这个代码
            return pd.DataFrame()
        temp = self.tday_span(max(ts, list_date[0][0]), te)
        columns = []
        res = []
        for tday in temp:
            self.cursor.execute('select * from "%s" where ts_code="%s"' % (tday, code))
            res.extend(self.cursor.fetchall())
            if not columns:
                columns = [x[0] for x in self.cursor.description]
        df = pd.DataFrame(res, columns=columns)
        df.loc[:, ['open', 'high', 'low', 'close']] = df.loc[:, ['open', 'high', 'low', 'close']].mul(df.adj_factor, axis='index') / df.adj_factor.max()
        return df

    def get_quotes(self, code): # ohl+price+volume+amount+ba1-5vp
        ts_api = ts.get_apis()
        df = ts.quotes(code.split('.')[0], conn=ts_api, asset='E')
        if df is None:
            return pd.DataFrame()
        df['close'] = df.loc[:, 'price']
        return df

    def get_ticks(self, code): # time, price, volume, type
        date = time.strftime('%Y-%m-%d', time.localtime())
        ts_api = ts.get_apis()
        df = ts.tick(code.split('.')[0], conn=ts_api, date=date, asset='E')
        if df is None:
            df = pd.DataFrame()
        return df

    def get_stock_list(self, index_code='000001.SH'):
        t = time.time()
        te = time.strftime('%Y%m%d', time.localtime(t))
        ts = time.strftime('%Y%m%d', time.localtime(t-90.0*24*60*60))
        df = self.api.index_weight(index_code=index_code, start_date=ts, end_date=te)
        res = [s[:6] for s in df.con_code]
        res = list(set(res))
        res.sort()
        return res


if __name__ == '__main__':
    db = StockDb()
    # db.refresh()
    db.get_stock_list()
