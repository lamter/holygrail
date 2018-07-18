"""
生成各种回测数据
"""
import os
import pytest
import pandas as pd
import pickle


def test_btinfo(btinfo):
    """

    :return:
    """
    from holygrail.btinfo import Btinfo
    d = btinfo.find_one({}, {'_id': 0})
    print('生成测试用的btinfo，us: rb')
    assert d['underlyingSymbols'] == ['rb']
    assert '_id' not in d
    btInfo = Btinfo(**d)


def test_nav(config):
    """
    生成 originData 的本地缓存
    :param :
    :return:
    """
    from holygrail.nav import Nav

    print('生成测试用的 originData，us: rb')

    path = config.get('单元测试', 'path')

    nav = Nav(config, 'rb', '布林带密集步长', 'SvtBollChannelStrategy', path)

    # 生成净值和数据汇总
    nav.run()


def test_winrol_anaHisNavHihestWinLowest(nav):
    print(13131)
    from holygrail.winroll import Winroll
    wr = Winroll(nav)
    print('开始窗口滚动')
    wr.anaHisNavHihestWinLowest()


def test_multnav():
    """
    先生成 Nav() 的缓存
    :return:
    """



def test_optmulti(config, btinfo):
    from holygrail import optHisNavHihestWinLowest
    from holygrail import Btinfo

    d = btinfo.find_one({}, {'_id': 0})
    btInfo = Btinfo(**d)
    usList = btInfo.underlyingSymbols[:]

    periodList = [6, 11]
    histNavRangeList = [50, 90]
    group, className = '布林带密集步长', 'SvtBollChannelStrategy'
    configIni = '../tmp/config.ini'
    optHisNavHihestWinLowest(configIni, usList, group, className, periodList, histNavRangeList)


def test_drawPotentiometric(cnofig):
    import os
    import logging.config
    from configparser import ConfigParser

    import importlib
    import holygrail
    from holygrail import optHisNavHihestWinLowest

    importlib.reload(holygrail.winroll)
    importlib.reload(holygrail.optimize)
    from holygrail.optimize import Optimize
    from holygrail.winroll import Winroll
    from holygrail.nav import Nav

    # logging.config.fileConfig('/Users/lamter/workspace/SlaveO/holygrail/tmp/logging.ini')
    configIni = '/Users/lamter/workspace/SlaveO/holygrail/tmp/boll_opt.ini'
    config = ConfigParser()
    config.read(configIni)

    path = config.get('优化', 'path')

    group, className = '布林带密集步长', 'SvtBollChannelStrategy'
    periodList = ['{}BM'.format(i) for i in range(1, 13)]
    histNavRangeList = list(range(10, 200, 1))

    us = 'rb'
    nav = Nav(config, us, group, className, path)
    nav.run()
    wr = Winroll(nav)
    opt = Optimize(wr)

    # 运行优化
    # opt.optHisNavHihestWinLowest(periodList, histNavRangeList)

    # 绘图生成净值等势图
    opt.draw_3dpotentiometric_anaHisNavHihestWinLowest()
