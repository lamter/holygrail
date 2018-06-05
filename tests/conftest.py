# codint:utf-8

import pymongo
import pytest
import logging.config
logging.config.fileConfig('../tmp/logging.ini')
from configparser import ConfigParser

@pytest.fixture(scope='session', autouse=True)
def config():
    config = ConfigParser()
    config.read('../tmp/config.ini')
    return config


@pytest.fixture(scope='session')
def client(config):
    assert isinstance(config, ConfigParser)
    sec = '回测相关数MongoDB据库'
    client = pymongo.MongoClient(
        host=config.get(sec, 'host'),
        port=config.getint(sec, 'port')
    )
    return client


@pytest.fixture(scope='session')
def db(config):
    assert isinstance(config, ConfigParser)
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


@pytest.fixture(scope='session')
def btinfo(db, config):
    sec = '回测相关数MongoDB据库'
    return db[config.get(sec, 'btinfo')]

@pytest.fixture(scope='session')
def btresult(db, config):
    sec = '回测相关数MongoDB据库'
    return db[config.get(sec, 'btresult')]

@pytest.fixture(scope='session')
def nav(config):
    from holygrail.nav import Nav
    path = config.get('单元测试', 'path')
    nav = Nav(None, 'rb', '布林带密集步长', 'SvtBollChannelStrategy', path)
    nav.run()
    return nav

