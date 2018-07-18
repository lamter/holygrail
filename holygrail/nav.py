import os
from itertools import chain
import logging
import traceback

import pandas as pd
import numpy as np
import pickle
import pymongo

from .dealutils import *
from .btinfo import Btinfo


class Nav(object):
    """
    从回测结果中计算该品种主力连续的净值
    """

    def __init__(self, config, us, group, className, path):
        """

        :param originDf:
        :param us:
        :param group:
        :param className:
        :param path: 计算缓存文件的路径
        """
        self.logger = logging.getLogger(us)
        self.us = us
        self.group = group
        self.className = className
        self.config = config

        # 从 btresult 中加载的原始数据
        self.origin = None
        if not os.path.exists(path):
            raise ValueError('路径 {}'.format(path))

        # 生成指定路径，/tmp/holygrail/rb_密集布林带_SvtBoll/
        self.path = os.path.join(path, '{}_{}_{}'.format(self.us, self.group, self.className))

        # 该批回测数据的信息

        # 主力连续的日收益和日净值
        self.dailyReturnRateByOptsv = {}  # {'optsv': pd.DataFrame()}

        # 根据日线净值汇总的数据
        self.summarizeColumns = [
            '品种', '爆仓', '最大回撤', '最终净值', '最大保证金占用', '最大净值', '最小净值',
            '首个交易日', '最后交易日', '总交易日', '盈利交易日', '亏损交易日',
            '日复利', '年复利', '日均收益率', '收益标准差', '夏普率'
        ]
        self.summarizeDialyDF = None  # 汇总的日线数据

    def run(self):
        """
        初始化数据
        :return:
        """
        if not os.path.exists(self.path):
            # 生成指定路径，进行计算
            os.mkdir(self.path)
        else:
            # 尝试从缓存中加载
            self.logger.info('尝试缓存加载')
            if self.load():
                # 加载成功
                return

        self.logger.info('开始计算')

        # 从数据库加载 origin 数据
        self.loadOrigin()

        df = self.origin

        # 根据回测参数分组
        group = df.groupby('optsv')

        optsvList = group.indices.keys()

        # 计算出一组参数的净值曲线，以及回撤等数据
        # 这个计算出的 DataFrame 是以交易日为索引的每日数据
        summarize = []
        for optsv in optsvList:
            # optsv是一组参数的唯一标志, 对每一组参数进行净值曲线计算
            consisDF = group.get_group(optsv)
            # 1.计算净值
            navDF = self._calDailyNav(consisDF)

            # 2. 根据净值计算回撤
            navDF = self._calDailyDrawback(navDF)
            # 缓存计算好的净值
            self.dailyReturnRateByOptsv[optsv] = navDF

            # 据此计算其他数值汇总参数
            dic = self._summarizingDailyByOptsv(optsv, consisDF, navDF)
            dic['optsv'] = optsv
            summarize.append(dic)

            # 汇总的数据
        self.summarizeDialyDF = pd.DataFrame(summarize).set_index('optsv')
        columns = self.summarizeColumns[:]
        for c in self.summarizeDialyDF.columns:
            if c not in self.summarizeColumns:
                columns.append(c)

        self.summarizeDialyDF = self.summarizeDialyDF[columns]

        # 缓存当前属性
        self.dump()

    @property
    def startDate(self):
        try:
            return self._startDate
        except AttributeError:
            self._startDate = min(self.summarizeDialyDF['首个交易日'].value_counts().index)
            return self._startDate

    @property
    def endDate(self):
        try:
            return self._endDate
        except AttributeError:
            self._endDate = max(self.summarizeDialyDF['最后交易日'].value_counts().index)
            return self._endDate

    def _calDailyNav(self, consisDF):
        """
        据此计算其他数值汇总参数
        :param consisDF:
        :return:
        """
        # 取得每一组主力连续的数据 consisDF
        # assert consisDF.columns == ['日收益率', '结算日', 'optsv', 'underlyingSymbol', 'activeEndDate']

        # 将主力consisDF生成净值曲线
        # 按照合约变更的时间顺序排序
        consisDF = consisDF.sort_values('activeEndDate')

        # 衔接日期
        dateIndex = pd.DatetimeIndex(list(chain(*consisDF['结算日'])), name='datetime', tz=LOCAL_TIMEZONE)

        # 衔接收益率
        navDF = pd.DataFrame({'日收益率': list(chain(*consisDF['日收益率']))}, index=dateIndex)

        navDF.reset_index(inplace=True)
        navDF = navDF.drop_duplicates('datetime')
        navDF = navDF.set_index('datetime')

        # 累乘，得到净值序列
        navDF['净值'] = navDF['日收益率'] + 1
        navDF['净值'] = navDF['净值'].cumprod()
        # 将净值小于0全部设置为0
        navDF['净值'][navDF['净值'] < 0] = 0

        return navDF

    def _calDailyDrawback(self, navDF):
        """
        根据交易日计算最大回撤
        :param navDF:
        :return:
        """
        # 计算最大回测
        # 累乘，得到净值序列
        navDF['净值新高'] = navDF['净值'].cummax()
        navDF['回撤'] = (navDF['净值'] - navDF['净值新高']) / navDF['净值新高']
        return navDF

    def _summarizingDailyByOptsv(self, optsv, consisDF, navDF):
        """
        汇总一个主力连续的数据
        :param optsv:
        :param consisDF:
        :param navDF: pd.DataFrame()
        :return: dict()
        """
        us, kwargs = parseOptsv(optsv)
        mean = navDF['日收益率'].mean()
        std = navDF['日收益率'].std()
        minNav = navDF['净值'].min()
        dic = {
            '品种': us,
            '首个交易日': navDF.index[0].to_pydatetime(),
            '最后交易日': navDF.index[-1].to_pydatetime(),
            '总交易日': navDF.shape[0],

            '最大保证金占用': consisDF['最大保证金占用'].max(),
            '最终净值': navDF['净值'].iloc[-1],
            '最大净值': navDF['净值'].max(),
            '最小净值': navDF['净值'].min(),
            '爆仓': minNav < 0.1,
            '最大回撤': navDF['回撤'].min(),

            '日均收益率': mean,
            '收益标准差': std,
        }
        try:
            dic['夏普率'] = mean / std * np.sqrt(TRAE_DAYS),
        except ZeroDivisionError:
            dic['夏普率'] = 0
        dic['日复利'] = navDF['净值'].iloc[-1] ** (1 / dic['总交易日'])
        dic['年复利'] = (navDF['净值'].iloc[-1] ** (1 / dic['总交易日'])) ** TRAE_DAYS
        try:
            dic['盈利交易日'] = (navDF['日收益率'] > 0).value_counts()[True]
        except KeyError:
            dic['盈利交易日'] = 0
        try:
            dic['亏损交易日'] = (navDF['日收益率'] < 0).value_counts()[True]
        except KeyError:
            dic['亏损交易日'] = 0

        # 参数
        dic.update(kwargs)
        return dic

    def dump(self):
        """
        缓存当前计算结果
        :return:
        """
        properties = ['dailyReturnRateByOptsv', 'summarizeDialyDF']
        for p in properties:
            fn = '{}.{}.pickle'.format(self.__class__.__name__, p)
            path = os.path.join(self.path, fn)
            with open(path, 'wb') as f:
                self.logger.info('缓存 {}'.format(path))
                pickle.dump(getattr(self, p), f)

    def load(self):
        """
        从缓存中加载计算结果
        文件名和属性对应方式为  类名.属性名.pickle，如  Nav.dailyReturnRateByOptsv.pickle
        :return:
        """
        isSucessed = False
        try:
            _, _, files = next(os.walk(self.path))
            cache = {}
            className = self.__class__.__name__ + '.'
            for fn in files:

                if not fn.startswith(className) or not fn.endswith('.pickle'):
                    # 查找属于当前类的属性
                    continue

                path = os.path.join(self.path, fn)
                fn = fn.strip('.pickle').lstrip(className)
                if not hasattr(self, fn):
                    # 是否属于当前类
                    continue

                self.logger.info('缓存加载 {}'.format(fn))
                with open(path, 'rb') as f:
                    cache[fn] = pickle.load(f)
            # 使用加载的缓存
            if cache:
                for k, v in cache.items():
                    setattr(self, k, v)
                isSucessed = True
        except Exception:
            self.logger.error(traceback.format_exc())

        return isSucessed

    def loadOrigin(self):
        """

        :return:
        """
        config = self.config
        sec = '回测相关数MongoDB据库'
        db = getDB(config)
        btresult = db[config.get(sec, 'btresult')]
        self.btresult = btresult
        sql = {
            'underlyingSymbol': self.us,
            'group': self.group,
            'className': self.className,
        }
        cursor = btresult.find(sql, {'_id': 0})

        self.origin = pd.DataFrame((_ for _ in cursor))

