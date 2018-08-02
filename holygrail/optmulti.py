"""
多进程优化接口
"""
from threading import Event
import os
from multiprocessing import Process
from configparser import ConfigParser
import logging

from .nav import Nav
from .winroll import Winroll
from .optimize import Optimize

from .multifunc import *


def optHisNavHihestWinLowest(configIni, usList, group, className, periodList, histNavRangeList):
    """
    Optimize.optHisNavHihestWinLowest 的多进程模式
    :return:
    """
    logger = logging.getLogger()

    config = ConfigParser()
    config.read(configIni)
    pid = os.getpid()

    cpu = config.getint('优化', 'cpu')
    logger.info('使用 cpu: {}'.format(cpu))

    path = config.get('优化', 'path')

    # 先生成 Nav 的缓存
    _initNav(usList, pid, configIni, group, className, path)

    # 生成  Wiroll.df
    _initWinrollDF(usList, cpu, pid, configIni, periodList, group, className, path)

    # 分解任务, 异步执行，并进行缓存
    _optHisNavHihestWinLowest(pid, configIni, usList, cpu, periodList, histNavRangeList, group, className, path)

    # 对优化结果进行分析
    _anaHisNavHihestWinLowest(configIni, usList, periodList, histNavRangeList, group, className, path)


def _initNav(usList, pid, configIni, group, className, path):
    for us in usList:
        logging.info('加载 nav {}'.format(us))
        p = Process(name=us, target=initnav, args=(pid, configIni, us, group, className, path))
        p.daemon = True
        p.start()
        p.join()


def _initWinrollDF(usList, cpu, pid, configIni, periodList, group, className, path):
    logger = logging.getLogger()
    stoped = Event()
    # 生成 winroll
    processList = []
    count = 0

    for us in usList:
        logger.info('加载 winroll {}'.format(us))
        p = Process(name=us, target=initWinrollDf, args=(pid, configIni, us, periodList, group, className, path))
        p.daemon = True
        p.start()
        processList.append(p)
        count += 1
        while count >= cpu and not stoped.wait(0.1):
            finished = []
            for p in processList:
                if not p.is_alive():
                    count -= 1
                    p.terminate()
                    finished.append(p)
            for p in finished:
                processList.remove(p)

    for p in processList:
        p.join()


def _optHisNavHihestWinLowest(pid, configIni, usList, cpu, periodList, histNavRangeList, group, className, path):
    logger = logging.getLogger()
    stoped = Event()
    processList = []
    count = 0
    for us in usList:
        for period in periodList:
            logger.info('opt {} period: {}'.format(us, period))
            p = Process(name=us,
                        target=optimizeOptHisNavHihestWinLowest,
                        args=(pid, configIni, us, period, histNavRangeList, group, className, path))
            p.daemon = True
            p.start()
            processList.append(p)
            count += 1
            while count >= cpu and not stoped.wait(0.1):
                finished = []
                for p in processList:
                    if not p.is_alive():
                        count -= 1
                        p.terminate()
                        finished.append(p)
                for p in finished:
                    processList.remove(p)

    for p in processList:
        p.join()

def _optWinHighNav(pid, configIni, usList, cpu, periodList, navRangeList, group, className, path):
    logger = logging.getLogger()
    stoped = Event()
    processList = []
    count = 0
    for us in usList:
        for period in periodList:
            logger.info('opt {} period: {}'.format(us, period))
            p = Process(name=us,
                        target=optimizeOptWinHighNav,
                        args=(pid, configIni, us, period, navRangeList, group, className, path))
            p.daemon = True
            p.start()
            processList.append(p)
            count += 1
            while count >= cpu and not stoped.wait(0.1):
                finished = []
                for p in processList:
                    if not p.is_alive():
                        count -= 1
                        p.terminate()
                        finished.append(p)
                for p in finished:
                    processList.remove(p)

    for p in processList:
        p.join()


def _anaHisNavHihestWinLowest(configIni, usList, periodList, histNavRangeList, group, className, path):
    config = ConfigParser()
    config.read(configIni)

    for us in usList:
        nav = Nav(config, us, group, className, path)
        nav.run()

        wr = Winroll(nav)
        opt = Optimize(wr)
        opt.optHisNavHigestWinLowest(periodList, histNavRangeList)

        # 生成 排名-窗口期 净值等势图
        # AnaHisNavHigestWinLowest
        opt.draw3Dpotentiometric(method='anaHisNavHigestWinLowest', months=12 * 10)

        # 生成等势图历史变迁视频
        opt.vedio3DpotentiometricHistory(method='anaHisNavHigestWinLowest')

        # 统计收益率区间频率
        opt.anaReturnRateRangeFrequency(method='anaHisNavHigestWinLowest')


def optWinRollNav(configIni, usList, group, className, periodList, navRangeList):
    """
    简单的取窗口期内净值最大进行滚动
    :return:
    """
    logger = logging.getLogger()

    config = ConfigParser()
    config.read(configIni)
    pid = os.getpid()

    cpu = config.getint('优化', 'cpu')
    logger.info('使用 cpu: {}'.format(cpu))

    path = config.get('优化', 'path')

    # # 先生成 Nav 的缓存
    # _initNav(usList, pid, configIni, group, className, path)
    #
    # # 生成  Wiroll.df
    # _initWinrollDF(usList, cpu, pid, configIni, periodList, group, className, path)
    #
    # # 分解任务, 异步执行，并进行缓存
    # _optWinHighNav(pid, configIni, usList, cpu, periodList, navRangeList, group, className, path)

    # 对优化结果进行分析
    _anaWinHIghNav(configIni, usList, periodList, navRangeList, group, className, path)

def _anaWinHIghNav(configIni, usList, periodList, histNavRangeList, group, className, path):
    config = ConfigParser()
    config.read(configIni)

    for us in usList:
        nav = Nav(config, us, group, className, path)
        nav.run()

        wr = Winroll(nav)
        opt = Optimize(wr)
        opt.optWinHighNav(periodList, histNavRangeList)

        # # 生成 排名-窗口期 净值等势图
        # opt.draw3Dpotentiometric(method='anaWinHighNav',months=12 * 10)
        #
        # # 生成等势图历史变迁视频
        # opt.vedio3DpotentiometricHistory(method='anaWinHighNav')
        #
        # # 统计收益率区间频率
        # opt.anaReturnRateRangeFrequency(method='anaWinHighNav')

        # 统计最大最小回撤
        opt.anaDrawdown(method='anaWinHighNav')