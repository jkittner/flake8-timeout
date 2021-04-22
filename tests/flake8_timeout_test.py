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


@pytest.mark.parametrize(
    's',
    (
        'a = requests.session(foo="bar")',
        'a = urllib.request.Request(foo="bar")',
    ),
)
def test_unknown_method(s):
    assert not results(s)


@pytest.mark.parametrize(
    's',
    (
        'a = requests.post("https://example.com", timeout=5, foo="bar")',
        '''\
a = urllib.request.urlopen(
    "https://example.com",
    timeout=5,
    bar="baz",
)
''',
    ),
)
def test_timout_is_kwarg(s):
    assert not results(s)


@pytest.mark.parametrize(
    's',
    (
        'a = requests.post("https://example.com", params={"bar": "baz"})',
        'a = requests.post("https://example.com", timeout=None)',
        'a = requests.get("https://example.com", timeout=None)',
        'a = requests.put("https://example.com", timeout=None)',
        'a = requests.delete("https://example.com", timeout=None)',
        'a = urllib.request.urlopen("https://example.com", bar="baz")',
    ),
)
def test_timeout_missing(s):
    msg, = results(s)
    assert msg == '1:4: FTA100 request call has no timeout'


@pytest.mark.parametrize(
    's',
    (
        'a = foo(bar=requests.get("https://example.com"))',
        'a = foo(bar=urllib.request.urlopen("https://example.com"))',
    ),
)
def test_call_as_kwarg(s):
    msg, = results(s)
    assert msg == '1:12: FTA100 request call has no timeout'


@pytest.mark.parametrize(
    's',
    (
        'a = foo(bar=requests.get("https://example.com"))',
        'a = foo(bar=urllib.request.urlopen("https://example.com"))',
    ),
)
def test_call_as_arg(s):
    msg, = results(s)
    assert msg == '1:12: FTA100 request call has no timeout'


@pytest.mark.parametrize(
    's',
    (
        'foo(bar=requests.get("https://example.com"))',
        'foo(bar=urllib.request.urlopen("https://example.com"))',
    ),
)
def test_call_as_arg_no_assing(s):
    msg, = results(s)
    assert msg == '1:8: FTA100 request call has no timeout'


@pytest.mark.parametrize(
    's',
    (
        'def foo(bar=requests.get("https://example.com")):\n    ...',
        'def foo(bar=urllib.request.urlopen("https://example.com")):\n    ...',
    ),
)
def test_call_as_function_argument_default(s):
    s = 'def foo(bar=requests.get("https://example.com")):\n    ...'
    msg, = results(s)
    assert msg == '1:12: FTA100 request call has no timeout'
