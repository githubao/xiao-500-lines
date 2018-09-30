#!/usr/bin/env python
# encoding: utf-8

"""
@description: DO NOT DO THIS!

@author: baoqiang
@time: 2018/9/30 下午3:44
"""

import socket


def fetch():
    sock = socket.socket()
    sock.setblocking(False)

    try:
        sock.connect(('xkcd.com', 80))
    except BlockingIOError:
        pass

    request = 'GET /353/ HTTP/1.0\r\nHost: xkcd.com\r\n\r\n'
    encoded = request.encode('ascii')

    while True:
        try:
            sock.send(encoded)
            break
        except OSError as e:
            pass

    print('sent')

    response = b''
    chuck = sock.recv(4096)
    while chuck:
        response += chuck
        chuck = sock.recv(4096)

    print('response: {}'.format(response))


if __name__ == '__main__':
    fetch()
