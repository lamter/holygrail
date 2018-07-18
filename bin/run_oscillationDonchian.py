import os
import logging.config
from holygrail import optWinRollNav
from configparser import ConfigParser
from holygrail.dealutils import *
from holygrail.btinfo import Btinfo

logging.config.fileConfig('/Users/lamter/workspace/SlaveO/holygrail/tmp/logging.ini')
configIni = '/Users/lamter/workspace/SlaveO/holygrail/tmp/oscillationDonchian_opt.ini'

config = ConfigParser()
config.read(configIni)

path = config.get('优化', 'path')
db = getDB(config)

group, className = '镍唐奇安震荡', 'OscillationDonchianStrategy'

# periodList = ['{}BM'.format(i) for i in range(1, 13)]
# histNavRangeList = list(range(1, 101))
periodList = ['{}BM'.format(i) for i in range(1, 13)]
navRangeList = list(range(1, 101, 1))

btinfoCol = db[config.get('回测相关数MongoDB据库', 'btinfo')]

d = btinfoCol.find_one({'group': group, 'className': className}, {'_id': 0})
btInfo = Btinfo(**d)
usList = btInfo.underlyingSymbols[:]
usList = ['ni']

optWinRollNav(configIni, usList, group, className, periodList, navRangeList)

os.popen('say 分析数据完成')