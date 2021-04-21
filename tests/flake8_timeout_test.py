import ast

import pytest

from flake8_timeout import Plugin


def results(s):
    return {'{}:{}: {}'.format(*r) for r in Plugin(ast.parse(s)).run()}


@pytest.mark.parametrize(
    's',
    (
        'print("hello hello world")',
        '',
        'a = 5',
        'a = foo(x=5, timeout=None)',
    ),
)
def test_no_requests_expression(s):
    assert not results(s)


def test_requests_unknown_method():
    s = 'a = requests.session(foo="bar")'
    assert not results(s)


def test_timout_is_kwarg():
    s = 'a = requests.post("https://example.com", timeout=5, foo="bar")'
    assert not results(s)


@pytest.mark.parametrize(
    's',
    (
        'a = requests.post("https://example.com", params={"bar": "baz"})',
        'a = requests.post("https://example.com", timeout=None)',
        'a = requests.get("https://example.com", timeout=None)',
        'a = requests.put("https://example.com", timeout=None)',
        'a = requests.delete("https://example.com", timeout=None)',
    ),
)
def test_timeout_missing(s):
    msg, = results(s)
    assert msg == '1:4: FTA100 request call has no timeout'

# cases not covered yet


def test_requests_call_as_kwarg():
    s = 'a = foo(bar=requests.get("https://example.com"))'
    msg, = results(s)
    assert msg == '1:12: FTA100 request call has no timeout'


def test_requests_call_as_args():
    s = 'a = foo(bar=requests.get("https://example.com"))'
    msg, = results(s)
    assert msg == '1:12: FTA100 request call has no timeout'


def test_requests_call_as_args_no_assing():
    s = 'foo(bar=requests.get("https://example.com"))'
    msg, = results(s)
    assert msg == '1:8: FTA100 request call has no timeout'


def test_requests_call_as_function_argument_default():
    s = 'def foo(bar=requests.get("https://example.com")):\n    ...'
    msg, = results(s)
    assert msg == '1:12: FTA100 request call has no timeout'
