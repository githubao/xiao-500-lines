#!/usr/bin/env python
# encoding: utf-8

"""
@description: 使用协程异步爬虫

@author: baoqiang
@time: 2018/9/30 下午4:39
"""

import re
import socket
import time
import urllib.parse
from selectors import DefaultSelector
from selectors import EVENT_READ, EVENT_WRITE


class Future:
    def __init__(self):
        self.result = None
        self._callbacks = []

    def result(self):
        return self.result

    def add_done_callback(self, fn):
        self._callbacks.append(fn)

    def set_result(self, result):
        self.result = result
        for fn in self._callbacks:
            fn(self)

    def __iter__(self):
        yield self
        return self.result


class Task:
    def __init__(self, coro):
        self.coro = coro
        f = Future()
        f.set_result(None)
        self.step(f)

    def step(self, future):
        try:
            next_future = self.coro.send(future.result)
        except StopIteration:
            return

        next_future.add_done_callback(self.step)


url_todos = {'/'}
seen_urls = {'/'}
concurrency_achieved = 0
selector = DefaultSelector()
stopped = False


def connected(sock, address):
    f = Future()

    sock.setblocking(False)
    try:
        sock.connect(address)
    except BlockingIOError:
        pass

    def on_connected():
        f.set_result(None)

    selector.register(sock.fileno(), EVENT_WRITE, on_connected)
    yield from f
    selector.unregister(sock.fileno())


def read(sock):
    f = Future()

    def on_readable():
        f.set_result(sock.recv(4096))

    selector.register(sock.fileno(), EVENT_READ, on_readable)
    chuck = yield from f
    selector.unregister(sock.fileno())
    return chuck


def read_all(sock):
    response = []
    chuck = yield from read(sock)
    while chuck:
        response.append(chuck)
        chuck = yield from read(sock)

    return b''.join(response)


class Fetcher:
    def __init__(self, url):
        self.response = b''
        self.url = url

    def fetch(self):
        global concurrency_achieved, stopped
        concurrency_achieved = max(concurrency_achieved, len(url_todos))

        sock = socket.socket()
        yield from connected(sock, ('xkcd.com', 80))
        get = 'GET {} HTTP/1.0\r\nHost: xkcd.com\r\n\r\n'.format(self.url)
        sock.send(get.encode('ascii'))
        self.response = yield from read_all(sock)

        self._process_response()

        url_todos.remove(self.url)
        if not url_todos:
            stopped = True
        print('{} -> {}'.format(self.url, self.response))

    def _process_response(self):
        if not self.response:
            print('error: {}'.format(self.url))
            return
        if not self._is_html():
            return

        urls = set(re.findall(r"""(?i)href=["']?([^\s"'<>]+)""", self.body()))

        for url in urls:
            normalized = urllib.parse.urljoin(self.url, url)
            parts = urllib.parse.urlparse(normalized)
            if parts.scheme not in ('', 'http', 'https'):
                continue
            host, port = urllib.parse.splitport(parts.netloc)
            if host and host.lower() not in ['xkcd.com', 'www.xkcd.com']:
                continue
            defragmented, frag = urllib.parse.urldefrag(parts.path)
            if defragmented not in seen_urls:
                url_todos.add(defragmented)
                seen_urls.add(defragmented)

                Task(Fetcher(defragmented).fetch())

    def _is_html(self):
        head, body = self.response.split(b'\r\n\r\n', 1)
        headers = dict(h.split(': ') for h in head.decode().split('\r\n')[1:])
        return headers.get('Content-Type', '').startswith('text/html')


def run():
    start = time.time()
    fetcher = Fetcher('/')
    Task(fetcher.fetch())

    while not stopped:
        events = selector.select()
        for event_key, event_mask in events:
            callback = event_key.data
            callback()

    print('{} URLs fetched in {:.1f} seconds, achieved concurrency: {}'.format(
        len(seen_urls), time.time() - start, concurrency_achieved))


if __name__ == '__main__':
    run()
