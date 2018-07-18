import time
import os
import traceback
import logging
from configparser import ConfigParser

from holygrail.dealutils import *
from holygrail.nav import Nav
from holygrail.winroll import Winroll
from holygrail.optimize import Optimize


@exception
def initnav(ppid, configIni, us, group, className, path):
    logger = logging.getLogger()
    if not (os.getpid() != ppid and os.getppid() == ppid):
        logger.info('父进程 不执行 {}'.format(ppid))
        return

    config = ConfigParser()
    config.read(configIni)
    try:
        nav = Nav(config, us, group, className, path)
        # 生成净值和数据汇总
        nav.run()
    except Exception:
        traceback.print_exc()

    return us


@exception
def initWinrollDf(ppid, configIni, us, periodList, group, className, path):
    logger = logging.getLogger()
    if not (os.getpid() != ppid and os.getppid() == ppid):
        logger.info('父进程 不执行 {}'.format(ppid))
        return

    config = ConfigParser()
    config.read(configIni)

    nav = Nav(config, us, group, className, path)
    nav.run()
    wr = Winroll(nav)
    for period in periodList:
        logger.info('加载 winroll {} {}'.format(us, period))
        wr.loadOptsvNavByWin(period)


@exception
def optimizeOptHisNavHihestWinLowest(ppid, configIni, us, period, histNavRangeList, group, className, path):
    logger = logging.getLogger()
    if not (os.getpid() != ppid and os.getppid() == ppid):
        logger.info('父进程 不执行 {}'.format(ppid))
        return
    config = ConfigParser()
    config.read(configIni)

    nav = Nav(config, us, group, className, path)
    nav.run()

    wr = Winroll(nav)
    opt = Optimize(wr)
    opt.optHisNavHigestWinLowest([period], histNavRangeList)

@exception
def optimizeOptWinHighNav(ppid, configIni, us, period, histNavRangeList, group, className, path):
    logger = logging.getLogger()
    if not (os.getpid() != ppid and os.getppid() == ppid):
        logger.info('父进程 不执行 {}'.format(ppid))
        return
    config = ConfigParser()
    config.read(configIni)

    nav = Nav(config, us, group, className, path)
    nav.run()

    wr = Winroll(nav)
    opt = Optimize(wr)
    opt.optWinHighNav([period], histNavRangeList)
