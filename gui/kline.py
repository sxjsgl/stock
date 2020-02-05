import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui


class DateAxis(pg.AxisItem):
    def __init__(self, axistick, *args, **kwargs):
        pg.AxisItem.__init__(self, *args, **kwargs)
        self.x_values = axistick[0]
        self.x_strings = axistick[1]

    def tickStrings(self, values, scale, spacing):
        strns = []
        for v in values:
            vs = v * scale
            try:
                vstr = self.x_strings[self.x_values.index(vs)]
            except BaseException:
                vstr = ''
            finally:
                strns.append(vstr)
        return strns


class candle_stick_item(pg.GraphicsObject):
    '''
    传入的是df，index是数字，open,high,low,close,vol
    '''
    def __init__(self, data, offset=0):
        pg.GraphicsObject.__init__(self)
        self.data = data
        self.offset = offset
        self.generate_picture()

    def generate_picture(self):
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        w = 1.0 / 3.0
        for (i, x) in self.data.loc[:, ['open', 'high', 'low', 'close']].iterrows():
            t = i - self.offset
            if x.open >= x.close:
                p.setBrush(pg.mkBrush('g'))
                p.setPen(pg.mkPen('g'))
            else:
                p.setBrush(pg.mkBrush('r'))
                p.setPen(pg.mkPen('r'))
            p.drawLine(QtCore.QPointF(t, x.high), QtCore.QPointF(t, x.low))
            p.drawRect(QtCore.QRectF(t - w, x.open, 2 * w, x.close - x.open))
        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return QtCore.QRectF(self.picture.boundingRect())


class volume_item(pg.GraphicsObject):
    '''
    传入的是df，index是数字，open,high,low,close,vol
    '''
    def __init__(self, data, offset=0):
        pg.GraphicsObject.__init__(self)
        self.data = data
        self.offset = offset
        self.generate_picture()

    def generate_picture(self):
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        w = 1.0 / 3.0
        for (i, x) in self.data.loc[:, ['open', 'close', 'vol']].iterrows():
            t = i - self.offset
            if x.open >= x.close:
                p.setBrush(pg.mkBrush('g'))
                p.setPen(pg.mkPen('g'))
            else:
                p.setBrush(pg.mkBrush('r'))
                p.setPen(pg.mkPen('r'))
            p.drawRect(QtCore.QRectF(t - w, 0, 2 * w, x.vol))
        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return QtCore.QRectF(self.picture.boundingRect())


if __name__ == '__main__':
    from data.data_sqlite3 import StockDb

    db = StockDb()
    df = db.get_realtime_quotes('000001')
    df['close'] = df.loc[:, 'price']
    candle_stick_item(df)


