class Btinfo(object):
    """
    一批回测数据的参数配置，通常在 cta.btinfo 里面的一条内容
    """

    def __init__(self, group, underlyingSymbols, className, param, opts, datetime, symbols):
        """
        直接从 btinfo 数据库中读取一条 document ，**document 方式传递以上参数
        :param group:
        :param underlyingSymbols:
        :param className:
        :param param:
        :param opts:
        :param datetime:
        :param symbols:
        """
        self.group = group
        self.underlyingSymbols = underlyingSymbols
        self.className = className
        self.param = param
        self.opts = opts
        self.datetime = datetime
        self.symbols = symbols
