# coding: utf-8
from setuptools import setup, find_packages
import os


def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as f:
        return f.read()


__version__ = "0.1.0"

setup(
    name='holygrail',
    version=__version__,
    keywords='圣杯',
    description=u'',
    long_description=read("README.md"),

    url='https://github.com/lamter/holygrail',
    author='lamter',
    author_email='lamter.fu@gmail.com',

    packages=find_packages(),
    package_data={

    },
    install_requires=read("requirements.txt").splitlines(),
    classifiers=['Development Status :: 4 - Beta',
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3.5',
                 'Programming Language :: Python :: 3.6',
                 'License :: OSI Approved :: Apache License'],
)
