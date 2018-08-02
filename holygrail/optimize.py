import os
import pandas as pd
import logging
import traceback
from PIL import Image
import cv2
import glob as gb

from collections import defaultdict, OrderedDict
from myplot.nav import draw_3D_potentiometric
from .dealutils import calDrawdown


class Optimize(object):
    """
    使用指定的窗口期滚动方法，穷举优化
    opt开头的函数是优化方法
    ana开头的函数是分析汇总数据
    """

    def __init__(self, winroll):
        # assert isinstance(winroll, Winroll)
        self.winroll = winroll
        self.logger = logging.getLogger(self.winroll.nav.us)
        # 每个实例只保留一个结果
        self.rollNav = {}  # {period: {histNavRangeList:[]}}
        self.winRollNav = None
        self.dailyRollNav = None

    @property
    def us(self):
        return self.winroll.nav.us

    @property
    def group(self):
        return self.winroll.nav.group

    @property
    def className(self):
        return self.winroll.nav.className

    @property
    def path(self):
        return self.winroll.nav.path

    def optHisNavHigestWinLowest(self, periodList, histNavRangeList):
        """
        优化 anaHisNavHigestWinLowest 的结果
        在窗口周期 periodList 范围内，和在 histNavRangeList 净值历史排名范围内
        获取对应的历史收益
        :param periodList:
        :param histNavRangeList:
        :return: DataFrame() 获得对应窗口周期和历史排名下的参数的收益
        """

        winNavDic = {}
        dailyNavDic = {}

        for hisNavRange in histNavRangeList:
            w, d = [], []
            for period in periodList:
                # 生成窗口净值和对应的日线净值

                winRollNavDF, dailyRollNavDF = self._optHisNavHigestWinLowestRollNav(period, hisNavRange)
                w.append(winRollNavDF)
                d.append(dailyRollNavDF)
            winNavDic[hisNavRange] = w
            dailyNavDic[hisNavRange] = d

        self.winRollNav = pd.DataFrame(winNavDic, index=periodList).T
        self.dailyRollNav = pd.DataFrame(dailyNavDic, index=periodList).T

    def _optHisNavHigestWinLowestRollNav(self, period, hisNavRange):
        """
        获取 winRollNavDF, dailyRollNavDF
        :param period:
        :param hisNavRange:
        :return:
        """
        fn_1 = '{}.winRollNavDF_{}_{}.pickle'.format(self.__class__.__name__, period, hisNavRange)
        fn_2 = '{}.dailyRollNavDF_{}_{}.pickle'.format(self.__class__.__name__, period, hisNavRange)
        path_1 = os.path.join(self.path, fn_1)
        path_2 = os.path.join(self.path, fn_2)

        # 以period, hisNavRange 作为参数规则取得滚动窗口净值 winrollNav
        if os.path.exists(path_1) and os.path.exists(path_2):
            # 从缓存加载
            self.logger.info('缓存加载 {} {}'.format(fn_1, fn_2))
            winRollNavDF = pd.read_pickle(path_1)
            dailyRollNavDF = pd.read_pickle(path_2)
        else:
            # 直接生成
            self.logger.info('计算 {} {}'.format(fn_1, fn_2))
            winRollNavDF, dailyRollNavDF = self._async_optHisNavHigestWinLowestRollNav(
                period, hisNavRange, path_1, path_2)

        return winRollNavDF, dailyRollNavDF

    def _async_optHisNavHigestWinLowestRollNav(self, period, hisNavRange, path_1, path_2):
        winRollNavDF, dailyRollNavDF = self.winroll.anaHisNavHigestWinLowest(period, hisNavRange)
        winRollNavDF.to_pickle(path_1)
        dailyRollNavDF.to_pickle(path_2)
        return winRollNavDF, dailyRollNavDF

    def anaEndNav(self, days=0):
        """
        分析穷举后的数据，根据日线，获取最终净值
        :return:
        """
        days = -(1 + days)

        def foo(bm):
            return bm.apply(lambda df: df.nav[days])

        return self.dailyRollNav.apply(foo)

    def draw3Dpotentiometric(self, method, months=3):
        """
        生成历史 24 个月变迁图
        取 24个月
        :return:
        """
        dic = defaultdict(lambda: defaultdict(list))

        def bar(df, period):
            s = df['nav'].resample('1BM').last().to_dict()
            for d, nav in s.items():
                dic[d][period].append(nav)

        def foo(period):
            period.apply(bar, args=(period.name,))

        self.dailyRollNav.apply(foo)

        # 生成三维数据
        padic = {
            k: pd.DataFrame(
                v,
                index=self.dailyRollNav.index,
                columns=self.dailyRollNav.columns
            ) for k, v in dic.items()
            }

        orDic = self.orDic = OrderedDict()

        # 根据日期重新排序
        for k in sorted(list(padic.keys())):
            orDic[k] = padic[k]

        dtList = list(orDic.keys())[-months:]

        for dt in dtList:
            try:
                fn = '{}.{}.potentiometric_{}.png'.format(self.__class__.__name__, method, dt.date())
                path = os.path.join(self.path, fn)
                if not os.path.exists(path):
                    self.logger.info('绘制等势图 {}'.format(fn))
                    df = orDic[dt].copy()
                    df.columns = map(lambda x: int(x.strip('BM')), df.columns)

                    # draw_3D_potentiometric 需要使用 with 语法
                    g = draw_3D_potentiometric(
                        df, figsize=(20, 20), fontsize=20,
                        title='{}_{}'.format(self.us, dt.date()),
                        onlyShadow=True,
                        view=[90, 0],
                        isShow=False,
                    )

                    with g as fig:
                        fig.savefig(path)
                    # 裁剪图片
                    self._adjust3dpotentiometric(path)
            except ValueError:
                err = traceback.format_exc()
                if 'zero-size array' in err:
                    self.logger.warning(err)
                else:
                    raise

    def _adjust3dpotentiometric(self, path):
        """
        裁剪 等势图
        :return:
        """
        im = Image.open(path)
        # img_size = im.size
        x = 450
        y = 300
        w = 1200
        h = 1200
        region = im.crop((x, y, x + w, y + h))
        region.save(path)

    def vedio3DpotentiometricHistory(self, method):
        """
        将 draw3DpotentiometricAnaHisNavHigestWinLowest 中的图片做成历史等势图历史变迁的视频
        :return:
        """
        fn = '{}.{}3dPotentiometric.avi'.format(self.__class__.__name__, method)
        path = os.path.join(self.path, fn)
        if os.path.exists(path):
            return
        fps = 2  # 视频帧率
        # fourcc = cv2.cv.CV_FOURCC('M', 'J', 'P', 'G')
        fnpng = '{}.{}.potentiometric_*.png'.format(self.__class__.__name__, method)
        _filter = os.path.join(self.path, fnpng)
        img_path = sorted(gb.glob(_filter))

        size = (1200, 1200)  # (1360,480)为视频大小
        videoWriter = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'MJPG'), fps, size)

        imageSize = (1200, 1200)
        for path in img_path:
            img = cv2.imread(path)
            img = cv2.resize(img, imageSize)
            videoWriter.write(img)
        videoWriter.release()

    def anaReturnRateRangeFrequency(self, method):
        """
        收益率区间频率统计
        :return:
        """
        fn = '{}.returnRateRangeFrequency_{}.pickle'.format(self.__class__.__name__, method)
        path = os.path.join(self.path, fn)
        if os.path.exists(path):
            rangeFrequency = pd.read_pickle(path)
            return rangeFrequency

        nav = self.winroll.nav
        df = self.anaEndNav()

        td = nav.endDate - nav.startDate
        years = td.days / 365

        # 将所有收益率合并成一个 Series
        navList = []
        df.apply(lambda s: navList.extend(s.values))
        navSeries = pd.Series(navList)
        navSeries[navSeries < 0] = 0
        # 计算收益率
        returnRateSeries = navSeries.apply(lambda d: d ** (1 / years) - 1)

        # 等分收益率为10个区间
        areas = 10
        try:
            quartiles = pd.qcut(returnRateSeries, areas)
        except ValueError:
            err = traceback.format_exc()
            if 'Bin edges must be unique' in err:
                quartiles = pd.cut(returnRateSeries, areas)
            else:
                raise

        # 定义聚合函数
        def get_stats(group):
            return {'区间频率': group.count()}

        # 将收益率切割成10个数量想等的区间
        # 以便于确定前50%的收益率是多少
        grouped = returnRateSeries.groupby(quartiles)
        rangeFrequency = grouped.apply(get_stats).unstack().sort_index(ascending=False)
        rangeFrequency.index.name = '年化收益率区间'
        ratio = pd.Series(range(1, areas + 1), index=rangeFrequency.index)
        ratio *= 10
        rangeFrequency['区间比例(%)'] = ratio

        # 设置索引为区间比例 10% ~ 100%
        rangeFrequency = rangeFrequency.reset_index().set_index('区间比例(%)')

        # 缓存
        rangeFrequency.to_pickle(path)

        return rangeFrequency


    def optWinHighNav(self, periodList, navRangeList):
        """
        优化 anaWinHighNav 的结果
        在窗口周期 periodList 范围内，和在 navRangeList 窗口期内净值最高的
        :param periodList:
        :param navRangeList:
        :return: DataFrame() 获得对应窗口周期和历史排名下的参数的收益
        """

        winNavDic = {}
        dailyNavDic = {}

        for hisNavRange in navRangeList:
            w, d = [], []
            for period in periodList:
                # 生成窗口净值和对应的日线净值

                winRollNavDF, dailyRollNavDF = self._optWinHighNav(period, hisNavRange)
                w.append(winRollNavDF)
                d.append(dailyRollNavDF)
            winNavDic[hisNavRange] = w
            dailyNavDic[hisNavRange] = d

        self.winRollNav = pd.DataFrame(winNavDic, index=periodList).T
        self.dailyRollNav = pd.DataFrame(dailyNavDic, index=periodList).T

    def _optWinHighNav(self, period, hisNavRange):
        """
        获取 winRollNavDF, dailyRollNavDF
        :param period:
        :param hisNavRange:
        :return:
        """
        fn_1 = '{}.winRollNavDF_WinHighNav_{}_{}.pickle'.format(self.__class__.__name__, period, hisNavRange)
        fn_2 = '{}.dailyRollNavDF_WinHighNav_{}_{}.pickle'.format(self.__class__.__name__, period, hisNavRange)
        path_1 = os.path.join(self.path, fn_1)
        path_2 = os.path.join(self.path, fn_2)

        # 以period, hisNavRange 作为参数规则取得滚动窗口净值 winrollNav
        if os.path.exists(path_1) and os.path.exists(path_2):
            # 从缓存加载
            self.logger.info('缓存加载 {} {}'.format(fn_1, fn_2))
            winRollNavDF = pd.read_pickle(path_1)
            dailyRollNavDF = pd.read_pickle(path_2)
        else:
            # 直接生成
            self.logger.info('计算 {} {}'.format(fn_1, fn_2))
            winRollNavDF, dailyRollNavDF = self._async_optWinHighNav(
                period, hisNavRange, path_1, path_2)

        return winRollNavDF, dailyRollNavDF

    def _async_optWinHighNav(self, period, hisNavRange, path_1, path_2):
        winRollNavDF, dailyRollNavDF = self.winroll.anaWinHighNav(period, hisNavRange)
        winRollNavDF.to_pickle(path_1)
        dailyRollNavDF.to_pickle(path_2)
        return winRollNavDF, dailyRollNavDF


    def anaDrawdown(self, method):
        """
        分析最大回撤
        :return:
        """
        fn = '{}.maxDrawdown_{}.pickle'.format(self.__class__.__name__, method)
        path = os.path.join(self.path, fn)
        if os.path.exists(path):
            minDrawdown = pd.read_pickle(path)
            return minDrawdown

        def maxDrawndwon(nav):
            nav = nav.nav
            s = calDrawdown(nav).min()
            return s.min()

        return self.dailyRollNav.apply(lambda _df:_df.apply(maxDrawndwon))
