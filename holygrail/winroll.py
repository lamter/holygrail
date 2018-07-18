"""
窗口滚动优化方法
"""
import os
import logging
import pickle
import datetime

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from .nav import Nav


class Winroll(object):
    """
    roll开头的函数，是根据不同的优化目标来进行窗口滚动，比如 rollNav 就是基于净值来进行窗口滚动
    """

    def __init__(self, nav):
        # assert isinstance(nav, Nav)
        self.nav = nav
        self.logger = logging.getLogger(self.nav.us)
        # 给定窗口期内的净值
        self.optsvNavByWin = None  # pd.DataFrame(index=datatime, columns=[optsv1, optsv2, ...])
        # # 给定窗口期内的胜率
        # self.optsvWinRateByWin = None # pd.DataFrame(index=datatime, columns=[optsv1, optsv2, ...])

    @property
    def path(self):
        return self.nav.path

    @staticmethod
    def _calReturnByOptsv(nav, period):
        """
        由日线净值计算出每一个窗口期内的收益
        :param nav:
        :param rollingSumDF:
        :param period:
        :return:
        """
        dic = {}  # {’optsv': 窗口}
        for optsv in nav.summarizeDialyDF.index:
            _navDF = nav.dailyReturnRateByOptsv[optsv].copy()

            _navDF['日收益率'] = _navDF['日收益率'] + 1
            # 获得窗口对象
            rollNavDF = _navDF.resample(period)['日收益率'].prod()
            dic[optsv] = rollNavDF

        # 窗口期收益
        return pd.DataFrame(dic)

    @staticmethod
    def _calWinRateByOptsv(nav, period):
        """
        由日线净值计算出每一个窗口期内的收益
        :param nav:
        :param rollingSumDF:
        :param period:
        :return:
        """

        # TODO 获得窗口期内的胜率
        dic = {}  # {’optsv': 窗口}
        for optsv in nav.summarizeDialyDF.index:
            _navDF = nav.dailyReturnRateByOptsv[optsv].copy()

            _navDF['日收益率'] = _navDF['日收益率'] + 1
            # 获得窗口对象
            rollNavDF = _navDF.resample(period)['日收益率'].prod()
            dic[optsv] = rollNavDF

        # 窗口期收益
        return pd.DataFrame(dic)


    def _choseNavInWin(self, df, rollingSumNavDF, hisNavRange):
        """

        :param df: 每个窗口期内收益
        :param rollingSumNavDF: 当前窗口期历史净值
        :param hisNavRange:
        :return:
        """

        optsvList = []
        dates = list(rollingSumNavDF.columns)
        for dt in dates:
            # 取出每一个窗口期的所有组合
            hisNavByDaySerie = rollingSumNavDF[dt]
            # 按照历史净值排序，取出净值历史排名前 hisNavRange 个参数组合
            hisNavByDaySerie = hisNavByDaySerie.sort_values(ascending=False)
            hisNavByDaySerie = hisNavByDaySerie[:hisNavRange]
            # 取出净值历史排名前 hisNavRange 个 optsv 在当前窗口期内的表现
            winNav = df.loc[dt]
            winNav = winNav[hisNavByDaySerie.index]
            # 选取窗口期内收益为正的，且收益最小的
            _winNav = winNav[winNav > 1]
            if _winNav.shape[0] > 0:
                optsv = _winNav.idxmin()
            else:
                # 如果窗口期内没有收益为正的，就选取收益最大的（即亏损最小的）
                optsv = winNav.idxmax()
            optsvList.append(optsv)
        return optsvList

    def anaHisNavHigestWinLowest(self, period='3BM', hisNavRange=100):
        """
        1. 选取历史收益最大的 hisNavRange 组参数
        2. 选择其中窗口期内表现最差的那组参数
        3. 进行窗口轮动
        :param preiod: 窗口期
        :param hisNavRange:
        :return:
        """

        # 计算窗口期收益
        self.optsvNavByWin= self.loadDF(period)

        # 计算出窗口期净值曲线
        # winRollNavDF 的 optsv 是 index1 引用于 index2 得到 nav
        # winRollNavDF 的最后一个 optsv 基于最后一个窗口的数据计算得到的。最后一个窗口的数据可能是不完整的
        winRollNavDF = self._hisNavHihestWinLowest(self.df, hisNavRange)

        # 转换为日线净值曲线
        dailyRollNavDF = self._win2daily(winRollNavDF)
        return winRollNavDF, dailyRollNavDF

    def _win2daily(self, winRollNavDF):
        nav = self.nav

        winRollNavDF = winRollNavDF.copy()
        dailyReturnRateByWindows = pd.Series([0], index=[winRollNavDF.index[0]])

        startDate = winRollNavDF.index[0] + datetime.timedelta(days=1)

        optsvList = [np.nan]

        for i, dt in enumerate(winRollNavDF.optsv.index[1:]):
            endDate = dt
            optsv = winRollNavDF.optsv.iloc[i]  # 窗口期内最优参数
            dailyReturnRate = nav.dailyReturnRateByOptsv[optsv]  # 日净值曲线
            # _startDate, _endDate , _dailyReturnRate= startDate, endDate, dailyReturnRate
            startDate, endDate = self._win2dailyStartEndDate(startDate, endDate, dailyReturnRate)
            if startDate <= endDate:
                dailyReturnRate = dailyReturnRate[startDate:endDate]
                endDate = dailyReturnRate.index[-1]
                dailyReturnRateByWindows = dailyReturnRateByWindows.append(dailyReturnRate['日收益率'])
                optsvList.extend([optsv] * dailyReturnRate.shape[0])

            startDate = endDate + datetime.timedelta(days=1)

        dailyRollNav = dailyReturnRateByWindows + 1
        assert isinstance(dailyRollNav, pd.Series)

        dic = {'日收益率': dailyReturnRateByWindows, 'nav': dailyRollNav.cumprod(), 'optsv': optsvList}
        return pd.DataFrame(dic, columns=['nav', '日收益率', 'optsv'])

    def _win2dailyStartEndDate(self, startDate, endDate, dailyReturnRate):
        count = 0
        maxTry = 1000
        while True:
            try:
                _ = dailyReturnRate.loc[startDate]
                count = 0
                break
            except KeyError:
                if count > maxTry:
                    raise ValueError('次数过多')
                startDate += datetime.timedelta(days=1)
                count += 1
        while True:
            try:
                _ = dailyReturnRate.loc[endDate]
                count = 0
                break
            except KeyError:
                if count > maxTry:
                    raise ValueError('次数过多')
                endDate -= datetime.timedelta(days=1)
                count += 1

        return startDate, endDate

    def _hisNavHihestWinLowest(self, df, hisNavRange):
        # 将窗口期收益累乘为历史收益
        rollingSumNavDF = df.cumprod().T

        # 取出每个窗口期历史净值最大的 period 组
        optsvList = self._choseNavInWin(df, rollingSumNavDF, hisNavRange)
        dates = list(rollingSumNavDF.columns)

        # idxmins 中的每个元素，就是每个窗口期中，根据之前的最优参数而使用的参数
        rollingNavList = [1]
        for i, d in enumerate(dates[1:]):
            # dixmins 中的 index 跟 dates 一一对应的
            # 这里 index 要应用到下一个 date 上去
            rollingNavList.append(df.loc[d, optsvList[i]])

        s = pd.Series(rollingNavList, index=dates)
        return pd.DataFrame({'窗口收益率': s - 1, 'nav': s.cumprod(), 'optsv': optsvList})


    def anaWinHighNav(self, period='3BM', navRange=100):
        """
        1. 选取历史收益最大的 navRange 组参数
        2. 选择其中窗口期内表现最差的那组参数
        3. 进行窗口轮动
        :param preiod: 窗口期
        :param hisNavRange:
        :return:
        """

        # 计算窗口期收益
        df = self.optsvNavByWin= self.loadOptsvNavByWin(period)

        # 计算出窗口期净值曲线
        # winRollNavDF 的 optsv 是 index1 引用于 index2 得到 nav
        # winRollNavDF 的最后一个 optsv 基于最后一个窗口的数据计算得到的。最后一个窗口的数据可能是不完整的
        # 取出每个窗口期历史净值最大的 period 组
        rollingNavDF = df.T
        optsvList = self._choseNavInWin(df, rollingNavDF, navRange)
        dates = list(rollingNavDF.columns)

        # idxmins 中的每个元素，就是每个窗口期中，根据之前的最优参数而使用的参数
        rollingNavList = [1]
        for i, d in enumerate(dates[1:]):
            # dixmins 中的 index 跟 dates 一一对应的
            # 这里 index 要应用到下一个 date 上去
            rollingNavList.append(df.loc[d, optsvList[i]])

        s = pd.Series(rollingNavList, index=dates)
        winRollNavDF = pd.DataFrame({'窗口收益率': s - 1, 'nav': s.cumprod(), 'optsv': optsvList})

        # 转换为日线净值曲线
        dailyRollNavDF = self._win2daily(winRollNavDF)
        return winRollNavDF, dailyRollNavDF

    def loadOptsvNavByWin(self, period):
        fn = '{}.optsvNavByWin_{}.pickle'.format(self.__class__.__name__, period)
        path = os.path.join(self.path, fn)
        if os.path.exists(path):
            # 尝试从缓存加载
            self.logger.info('缓存加载 {}'.format(path))
            df = pd.read_pickle(path)
        else:
            # 直接计算
            df = self._calReturnByOptsv(self.nav, period)
            # 缓存
            self.logger.info('缓存 {}'.format(path))
            df.to_pickle(path)

        return df


    def loadOptsvWinRateByWin(self, period):
        """
        给成窗口期内的胜率
        :return:
        """
        fn = '{}.optsvWinRateByWin_{}.pickle'.format(self.__class__.__name__, period)
        path = os.path.join(self.path, fn)
        if os.path.exists(path):
            # 尝试从缓存加载
            self.logger.info('缓存加载 {}'.format(path))
            df = pd.read_pickle(path)
        else:
            # 直接计算
            df = self._calWinRateByOptsv(self.nav, period)
            # 缓存
            self.logger.info('缓存 {}'.format(path))
            df.to_pickle(path)

        return df