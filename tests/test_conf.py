# codint:utf-8
import pytest

def test_config(config):
    """
    测试从 config.ini 文件中加载参数
    :param config:
    :return:
    """
    assert config.get('回测相关数据库', 'dbn') == 'cta'



def test_btinfo(btinfo):
    """
    将一批回测参数的配置实例化
    :param btinfo:
    :return:
    """
    from holygrail.btinfo import Btinfo
    print(btinfo.find_one())
    # Btinfo()
