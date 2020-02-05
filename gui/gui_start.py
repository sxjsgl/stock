import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from gui.gui_window import Ui_MainWindow
import time
import os
import re
import pandas as pd
import numpy as np
import math
import pyqtgraph as pg
from gui.kline import *
import time


def dt_cal(tlist):
    dt = []
    for t in tlist:
        if t[11:13] < '12':
            offset = (9 * 3600.0 + 30 * 60.0)
        else:
            offset = 11 * 3600.0
        temp = float(t[11:13]) * 3600.0 + float(t[14:16]) * 60.0 - offset
        dt.append(temp)
    return dt


class window_kline(QtWidgets.QMainWindow, Ui_MainWindow):
    code = '000000'

    def __init__(self, db):
        super(window_kline, self).__init__()
        self.setupUi(self)
        # ---------------------------btn
        self.sh.toggled.connect(self.stocklist_update)
        self.sz.toggled.connect(self.stocklist_update)
        self.sh300.toggled.connect(self.stocklist_update)
        self.zz500.toggled.connect(self.stocklist_update)
        self.cyb.toggled.connect(self.stocklist_update)
        self.zx.toggled.connect(self.stocklist_update)
        # ---------------------------定时器
        timer1 = QtCore.QTimer(self)
        timer1.setInterval(1000)
        timer1.timeout.connect(self.time1_update)
        timer1.start()

        timer3 = QtCore.QTimer(self)
        timer3.setInterval(3000)
        timer3.timeout.connect(self.time3_update)
        timer3.start()
        # ---------------------------画图逻辑
        self.stock_list.itemClicked.connect(lambda: self.code_change(self.stock_list.currentItem().text()))
        self.stock_code.returnPressed.connect(lambda: self.code_change(self.stock_code.text()))
        # self.main_show.currentChanged.connect(self.pic_redraw)
        # --------------------------init stock pic
        self.db = db
        self.sh.setChecked(True)
        self.code_change('000001')

    def code_change(self, code):
        # --------------------------------code test
        temp = re.search('(\d{6})', code)
        if temp:
            temp = temp.groups()[0]
            if temp[0] != '6':
                code = temp + '.SZ'
            else:
                code = temp + '.SH'
        else:
            return
        if code == self.code:
            return
        self.code = code

        self.draw_kline()
        # self.draw_timebar()
        self.time3_update()

    def stocklist_update(self):
        # --------------清空
        self.stock_list.clear()
        # ---------------------
        sender = self.sender()
        btns = [self.sh, self.sz, self.sh300, self.zz500, self.cyb, self.zx]
        codes = ['000001.SH', '399001.SZ', '399300.SZ', '000905.SH', '399006.SZ', '000000']
        temp = btns.index(sender)
        index_code = codes[temp]
        for code in self.db.get_stock_list(index_code):
            self.stock_list.addItem(code)

    def draw_kline(self):
        # --------------删除以前的内容
        for w in self.kline_d1.widgets:
            self.kline_d1.layout.removeWidget(w)
        for w in self.kline_d2.widgets:
            self.kline_d2.layout.removeWidget(w)
        # -----------------重新画
        df = self.db.get_stock_data(self.code, ts='20200101')
        if df.empty:
            return

        strings = df.trade_date.to_list()
        strings.append(time.strftime('%Y%m%d', time.localtime()))
        values = range(-len(strings)+1, 1)
        stringaxis = DateAxis([values, strings], orientation='bottom')

        self.kline_w1 = pg.PlotWidget(axisItems={'bottom': stringaxis})
        self.kline_w1.addItem(candle_stick_item(df, df.shape[0]))
        self.kline_d1.addWidget(self.kline_w1)

        self.kline_w2 = pg.PlotWidget(axisItems={'bottom': stringaxis})
        self.kline_w2.addItem(volume_item(df, df.shape[0]))
        self.kline_d2.addWidget(self.kline_w2)

    def kline_update(self, df):
        # -------------------删除以前的组件
        if hasattr(self, 'c_item'):
            self.kline_w1.removeItem(self.c_item)
            self.kline_w2.removeItem(self.v_item)
        # -------------------
        self.c_item = candle_stick_item(df)
        self.v_item = volume_item(df)
        self.kline_w1.addItem(self.c_item)
        self.kline_w2.addItem(self.v_item)

    def draw_timebar(self):
        # --------------删除以前的内容
        for w in self.timebar_d1.widgets:
            self.timebar_d1.layout.removeWidget(w)
        for w in self.timebar_d2.widgets:
            self.timebar_d2.layout.removeWidget(w)
        # -----------------重新画
        df = self.db.get_ticks(self.code)
        if df.empty:
            return
        self.timebar_t = dt_cal(df.datetime)
        self.timebar_p = df.price.to_list()
        self.timebar_v = df.vol.to_list()

        strings = ['09:30', '10:00', '10:30', '11:00', '11:30', '13:30', '14:00', '14:30', '15:00']
        temp = time.strftime('%Y-%m-%d ', time.localtime())
        values = dt_cal([temp + s for s in strings])
        ticks = [(i, j) for i, j in zip(values, strings)]
        stringaxis = pg.AxisItem(orientation='bottom')
        stringaxis.setTicks([ticks])

        self.timebar_w1 = pg.PlotWidget(axisItems={'bottom': stringaxis})
        self.timebar_w1.setXRange(min(values), max(values))
        self.timebar_w1.setLimits(xMax=max(values), xMin=min(values))
        self.timebar_p1 = self.timebar_w1.plot(x=self.timebar_t, y=self.timebar_p)
        self.timebar_d1.addWidget(self.timebar_w1)

        self.timebar_w2 = pg.PlotWidget(axisItems={'bottom': stringaxis})
        self.timebar_w2.setXRange(min(values), max(values))
        self.timebar_w2.setLimits(xMax=max(values), xMin=min(values))
        self.timebar_p2 = self.timebar_w2.plot(x=self.timebar_t, y=self.timebar_v, fillLevel=0.0, brush=(50, 50, 200, 100), pen=(50, 50, 200, 100))
        self.timebar_d2.addWidget(self.timebar_w2)

    def timebar_update(self, df):
        t_now = time.strftime('%Y-%m-%d %H:%M', time.localtime())
        self.timebar_t.extend(dt_cal([t_now]))
        self.timebar_p.extend(df.price)
        self.timebar_v.extend(df.cur_vol)
        self.timebar_p1.setData(x=self.timebar_t, y=self.timebar_p)
        self.timebar_p2.setData(x=self.timebar_t, y=self.timebar_v, fillLevel=0.0, brush=(50, 50, 200, 100), pen=(50, 50, 200, 100))

    def quote_update(self, df):
        # -----------------删除以前的组件
        self.sell_list.clear()
        self.buy_list.clear()
        # ------------------
        sell_order = []
        for i in range(5):
            p = df.loc[0, 'ask' + str(5 - i)]
            v = df.loc[0, 'ask_vol' + str(5 - i)]
            sell_order.append('%7s  %4s' % (p, v))

        buy_order = []
        for i in range(5):
            p = df.loc[0, 'bid' + str(i + 1)]
            v = df.loc[0, 'bid_vol' + str(i + 1)]
            buy_order.append('%7s  %4s' % (p, v))

        self.sell_list.addItems(sell_order)
        self.buy_list.addItems(buy_order)

    def time1_update(self):
        self.time_lcd.display(time.strftime('%H:%M:%S', time.localtime(time.time())))

    def time3_update(self):
        t_now = time.strftime('%H:%M:%S', time.localtime())
        if (t_now < '09:30:00') | ((t_now > '11:30:00') & (t_now < '13:00:00')) | (t_now > '15:00:10'):
            return

        # df = self.db.get_quotes(self.code)
        # if df.empty:
        #     return
        #
        # self.quote_update(df)
        # self.kline_update(df)
        # self.timebar_update(df)


if __name__ == '__main__':
    from data.data_sqlite3 import StockDb

    db = StockDb()
    app = QtWidgets.QApplication(sys.argv)
    win = window_kline(db)
    win.show()
    app.exec_()

