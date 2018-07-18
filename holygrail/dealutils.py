import pytz
import json
import pymongo
from configparser import ConfigParser
import functools
import logging
import traceback

LOCAL_TIMEZONE = pytz.timezone('Asia/Shanghai')
TRAE_DAYS = 245  # 一年交易日的天数


def parseOptsv(optsv):
    """
    解析 optsv
    :param optsv:
    :return:
    """
    optsvSplit = optsv.split(',')
    # 品种
    us = underlyingSymbol = optsvSplit[0]
    # 参数
    argsStr = '{' + optsv[len(us) + 1:] + '}'
    return underlyingSymbol, json.loads(argsStr)


def getDB(config):
    sec = '回测相关数MongoDB据库'
    client = pymongo.MongoClient(
        host=config.get(sec, 'host'),
        port=config.getint(sec, 'port')
    )
    db = client[config.get(sec, 'dbn')]
    db.authenticate(
        config.get(sec, 'username'),
        config.get(sec, 'password')
    )
    return db


exceptionDic = {}


def exception(func):
    """
    用于捕获函数中的代码
    :param do:
     None       不抛出异常
     'raise'    继续抛出异常
    :return:
    """
    if func in exceptionDic:
        # 缓存
        return exceptionDic[func]

    @functools.wraps(func)
    def wrapper(*args, **kw):
        try:
            return func(*args, **kw)
        except Exception as e:
            logger = logging.getLogger()
            logger.error('{} {}'.format(str(args), str(kw)))
            logger.error(traceback.format_exc())
            raise

    # 缓存
    exceptionDic[func] = wrapper
    return wrapper

def calDrawdown(nav):
    """
    返回净值的回撤
    :param nav: Series(index=datetime , values=float(净值))
    :return: Series(index=datetime , values= float(回撤)<=0)
    """
    import numpy as np
    _max = np.maximum.accumulate(nav, 1)
    return nav / _max - 1

