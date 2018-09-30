#!/usr/bin/env python
# encoding: utf-8

"""
@description: 爬取

@author: baoqiang
@time: 2018/9/25 下午7:53
"""

import logging
from collections import namedtuple
import asyncio
import urllib.parse
import re
import time
import cgi

try:
    from asyncio import JoinableQueue as Queue
except ImportError:
    from asyncio import Queue

import aiohttp

logger = logging.getLogger(__name__)


def lenient_host(host):
    parts = host.split('.')[-2:]
    return ''.join(parts)


def is_redirect(response):
    return response.status in (300, 301, 302, 303, 307)


FetchStatistic = namedtuple('FetchStatistic',
                            ['url', 'next_url', 'status', 'exception', 'size', 'content_type', 'encoding', 'num_urls',
                             'num_new_urls'])


class Crawler:
    def __init__(self, roots, exclude=None, strict=True, max_redirect=10, max_tries=4, max_tasks=10, *, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.roots = roots
        self.exclude = exclude
        self.strict = strict
        self.max_redirect = max_redirect
        self.max_tries = max_tries
        self.max_tasks = max_tasks
        self.q = Queue(loop=self.loop)
        self.seen_urls = set()
        self.done = []
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.root_domains = set()
        for root in roots:
            parts = urllib.parse.urlparse(root)
            host, port = urllib.parse.splitport(parts.netloc)
            if not host:
                continue
            if re.match(r'\A[\d\.]*\Z]', host):
                self.root_domains.add(host)
            else:
                host = host.lower()
                if self.strict:
                    self.root_domains.add(host)
                else:
                    self.root_domains.add(lenient_host(host))
        for root in roots:
            self.add_url(root)
        self.t0 = time.time()
        self.t1 = None

    def close(self):
        self.session.close()

    def host_okay(self, host):
        host = host.lower()
        if host in self.root_domains:
            return True
        if re.match(r'\A[\d\.]*\Z', host):
            return False
        if self.strict:
            return self._host_okay_strictish(host)
        else:
            return self._host_okay_lenient(host)

    def _host_okay_strictish(self, host):
        host = host[4:] if host.startswith('www.') else 'www.' + host
        return host in self.root_domains

    def _host_okay_lenient(self, host):
        return lenient_host(host) in self.root_domains

    def record_statistic(self, fetch_statistic):
        self.done.append(fetch_statistic)

    @asyncio.coroutine
    def parse_links(self, response):
        links = set()
        content_type = None
        encoding = None
        body = yield from response.read()

        if response.status == 200:
            content_type = response.headers.get('content-type')
            pdict = {}

            if content_type:
                content_type, pdict = cgi.parse_header(content_type)

            encoding = pdict.get('charset', 'utf-8')
            if content_type in ('text/html', 'application/xml'):
                text = yield from response.text()

                urls = set(re.findall(r"""(?i)href=["']?([^\s"'<>]+)""", text))
                if urls:
                    logger.info('got %r distinct urls from %r', len(urls), response.url)
                for url in urls:
                    normalized = urllib.parse.urljoin(response.url, url)
                    defragmented, frag = urllib.parse.urldefrag(normalized)
                    if self.url_allowed(defragmented):
                        links.add(defragmented)

        stats = FetchStatistic(url=response.url, next_url=None, status=response.status, exception=None, size=len(body),
                               content_type=content_type, encoding=encoding, num_urls=len(links),
                               num_new_urls=len(links - self.seen_urls))
        return stats, links

    @asyncio.coroutine
    def fetch(self, url, max_redirect):
        tries = 0
        exception = None
        while tries < self.max_tries:
            try:
                response = yield from self.session.get(url, allow_redirects=False)
                if tries > 1:
                    logger.info('try %r for % success', tries, url)
                break
            except aiohttp.ClientError as client_error:
                logger.info('try %r for %r raised %r', tries, url, client_error)
                exception = client_error

            tries += 1

        else:
            logger.error('%r failed after %r tries', url, self.max_tries)

            self.record_statistic(FetchStatistic(url=url, next_url=None, status=None, exception=exception, size=0,
                                                 content_type=None, encoding=None, num_urls=0, num_new_urls=0))
            return

        try:
            if is_redirect(response):
                location = response.headers['location']
                next_url = urllib.parse.urljoin(url, location)
                self.record_statistic(
                    FetchStatistic(url=url, next_url=next_url, status=response.status, exception=None, size=0,
                                   content_type=None, encoding=None, num_urls=0, num_new_urls=0))
                if next_url in self.seen_urls:
                    return
                if max_redirect > 0:
                    logger.info('redirect to %r from %r', next_url, url)
                    self.add_url(next_url, max_redirect - 1)
                else:
                    logger.error('redirect limit reached for &r from %r', next_url, url)
            else:
                stat, links = yield from self.parse_links(response)
                self.record_statistic(stat)
                for link in links.difference(self.seen_urls):
                    self.q.put_nowait((link, self.max_redirect))
                self.seen_urls.update(links)
        finally:
            pass

    @asyncio.coroutine
    def work(self):
        try:
            while True:
                url, max_redirect = yield from self.q.get()
                assert url in self.seen_urls
                yield from self.fetch(url, max_redirect)
                self.q.task_done()
        except asyncio.CancelledError:
            pass

    def url_allowed(self, url):
        if self.exclude and re.search(self.exclude, url):
            return False
        parts = urllib.parse.urlparse(url)
        if parts.scheme not in ('http', 'https'):
            logger.debug('skipping non-http scheme in %r', url)
            return False
        host, port = urllib.parse.splitport(parts.netloc)
        if not self.host_okay(host):
            logger.debug('skipping non-root host in %r', url)
            return False
        return True

    def add_url(self, url, max_redirect=None):
        if max_redirect is None:
            max_redirect = self.max_redirect
        logger.debug('adding %r %r', url, max_redirect)
        self.seen_urls.add(url)
        self.q.put_nowait((url, max_redirect))

    def crawl(self):
        workers = [asyncio.Task(self.work(), loop=self.loop) for _ in range(self.max_tasks)]
        self.t0 = time.time()
        yield from self.q.join()
        self.t1 = time.time()
        for w in workers:
            w.cancel()
