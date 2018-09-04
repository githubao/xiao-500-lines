#!/usr/bin/env python
# encoding: utf-8

"""
@description: 测试模板引擎

@author: baoqiang
@time: 2018/9/4 下午6:51
"""

from templite import Templite, TempliteSyntaxError
from unittest import TestCase


class TempliteTest(TestCase):
    def try_render(self, text, ctx=None, result=None):
        actual = Templite(text).render(ctx or {})
        if result:
            self.assertEqual(actual, result)
        else:
            print(actual)

    def test_should_pass(self):
        text = """
            <h1>Hello {{name|upper}}!</h1>
            {% for topic in topics %}
                <p>You are interested in {{topic}}.</p>
            {% endfor %}
        """

        values = {'name': 'Ned', 'upper': str.upper, 'topics': ['Python', 'Geometry', 'Juggling']}

        self.try_render(text, values)


if __name__ == '__main__':
    pass
