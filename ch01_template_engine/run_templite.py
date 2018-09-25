#!/usr/bin/env python
# encoding: utf-8

"""
@description: 测试模板引擎

@author: baoqiang
@time: 2018/9/4 下午6:51
"""

from ch01_template_engine.templite import Templite


class TempliteHello(object):
    """
    def render_function(context, do_dots):
        c_upper = context['upper']
        c_topics = context['topics']
        c_name = context['name']
        result = []
        append_result = result.append
        extend_result = result.extend
        to_str = str
        extend_result(['\n            <h1>Hello ', to_str(c_upper(c_name)), '!</h1>\n            '])
        for c_topic in c_topics:
            extend_result(['\n                <p>You are interested in ', to_str(c_topic), '.</p>\n            '])
        append_result('\n        ')
        return "".join(result)

    """
    def try_render(self, text, ctx=None):
        actual = Templite(text).render(ctx or {})
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
    temp = TempliteHello()
    temp.test_should_pass()

