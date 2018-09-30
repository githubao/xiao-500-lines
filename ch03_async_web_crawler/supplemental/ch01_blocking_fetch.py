#!/usr/bin/env python
# encoding: utf-8

"""
@description: 阻塞调用

@author: baoqiang
@time: 2018/9/30 下午3:50
"""

import socket


def fetch():
    sock = socket.socket()
    sock.connect(('xkcd.com', 80))

    request = 'GET /353/ HTTP/1.0\r\nHost: xkcd.com\r\n\r\n'
    sock.send(request.encode('ascii'))

    response = b''
    chuck = sock.recv(4096)
    while chuck:
        response += chuck
        chuck = sock.recv(4096)

    print('response: {}'.format(response))

    # with open('a.jpg', 'wb') as fb:
    #     fb.write(response)


def threaded_method():
    sock = socket.socket()
    sock.connect(('xkcd.com', 80))
    request = 'GET /353/ HTTP/1.0\r\nHost: xkcd.com\r\n\r\n'
    sock.send(request.encode('ascii'))
    response = b''
    chunk = sock.recv(4096)
    while chunk:
        response += chunk
        chunk = sock.recv(4096)

    print(response)


if __name__ == '__main__':
    # fetch()
    threaded_method()
