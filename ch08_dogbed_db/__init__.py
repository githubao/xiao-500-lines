#!/usr/bin/env python
# encoding: utf-8

"""
@description: 

@author: baoqiang
@time: 2018/10/8 下午7:05
"""

from ch08_dogbed_db.interface import DBDB
import os

__all__ = ['DBDB', 'connect']


def connect(dbname):
    try:
        f = open(dbname, 'rb')
    except IOError:
        fd = os.open(dbname, os.O_RDWR | os.O_CREAT)
        f = os.fdopen(fd, 'rb')
    return DBDB(f)

