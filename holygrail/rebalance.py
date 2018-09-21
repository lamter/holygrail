"""
对多个策略的净值进行动态平衡
"""
import pandas as pd
import numpy as np
from .dealutils import calDrawdown


class Rebalance(object):
    """
    """

    def __init__(self, dailyReturnDF, diff):
        """

        :param navsDF: 多个策略的日收益, columns = [参数名], index=日期, values=每日收益
        """
        self.dailyReturnDF = dailyReturnDF
        self.diff = diff
        self.navDF = None  # 合成出来的净值曲线 columns=[参数名1, 参数名2, ..., 平均]
        self.drawdown = None # 对合成出来的净值曲线计算回撤

    def run(self):
        """
        执行动态平衡
        :return:
        """
        # 动态平衡
        self.reBalance()

        # 计算动态平衡后的回撤
        self.calDrawdown()


    def reBalance(self):
        """
        做动态平衡
        :return:
        """
        dailyReturnDF = self.dailyReturnDF
        diff = 1 - self.diff

        nav = pd.Series(1, index=dailyReturnDF.columns)
        navCumList = [[1] * (dailyReturnDF.shape[1] + 1)]
        _count = 0
        for dt in dailyReturnDF.index[1:]:
            _count += 1

            # 取出每天的收益率
            dr = dailyReturnDF.loc[dt]

            # 计算当天的权益
            nav *= (1 + dr)

            # 取出最大值和最小值，如果差异达到一定数值，动态再平衡
            idmax, idmin = nav.idxmax(), nav.idxmin()
            _max, _min = nav[idmax], nav[idmin]
            if _min / _max < diff:
                nav[idmax] = nav[idmin] = (_min + _max) / 2

            # 保存每天的净值
            _nav = list(nav)
            _nav.append(nav.mean())

            navCumList.append(_nav)

        # 合成的每日净值曲线df
        columns = list(dailyReturnDF.columns)
        columns.append('平均')
        self.navDF = navDF = pd.DataFrame(navCumList, index=dailyReturnDF.index, columns=columns)

    def calDrawdown(self):
        """

        :return:
        """
        dd = {}
        for col in self.navDF.columns:
            dd[col] = calDrawdown(self.navDF[col])

        self.drawdown = pd.DataFrame(dd)