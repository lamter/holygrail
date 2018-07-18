# holygrail
从回测结果中寻找圣杯

## 净值 Nav
```python
# 给定回测结果的MongoDB数据库
import pymongo
import pandas as pd
client = pymongo.MongoClient()
cursor = client.db.col.find({}, {'_id': 0})
oroginDF = pd.DataFrame((d for d in cursor))

from holygrail.nav import Nav
nav = Nav(originDF, 'rb', 'groupName', 'className')

# 生成净值和数据汇总
nav.run()

# 将 nav 实例用 pickle 导出
nav.dump(path)
```

## 窗口滚动 winroll
```python
from holygrail.nav import Nav
nav = Nav(originDF, 'rb', 'groupName', 'className')

from holygrail.winroll import Winroll
wr = Winroll(nav)

# 选取窗口期内历史净值排名第N个
hisNav = wr.anaHisNavHihestWinLowest()
# 绘制净值图
hisNav.nav.plot(grid=True)
# 当前窗口期内的 optsv
optsv = hisNav.optsv[-1]
```

## 窗口滚动优化
```python
from holy
```