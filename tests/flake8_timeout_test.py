import ast

import pytest
from flake8.options.manager import OptionManager

from flake8_timeout import parse_function_spec
from flake8_timeout import Plugin


def results(s):
    return {'{}:{}: {}'.format(*r) for r in Plugin(ast.parse(s)).run()}


@pytest.mark.parametrize(
    's',
    (
        pytest.param('print("hello hello world")', id='print-statement'),
        pytest.param('', id='empty-string'),
        pytest.param('a = 5', id='simple-assignment'),
        pytest.param(
            'a = foo(x=5, timeout=None)',
            id='untracked-call-with-timeout',
        ),
        pytest.param(
            'from . import something\nsomething.func("url")',
            id='relative-import',
        ),
        pytest.param(
            'from foo import bar\nbar("url")',
            id='direct-call-not-tracked',
        ),
        pytest.param(
            'unknown.method("url")',
            id='unimported-attribute-call',
        ),
        pytest.param(
            'urllib.request.unknown("url")',
            id='nested-untracked-attribute',
        ),
        pytest.param(
            'some_object.method("url")',
            id='unimported-base-object',
        ),
        pytest.param(
            'funcs = [lambda x: x]\nfuncs[0]("url")',
            id='call-on-subscript',
        ),
        pytest.param(
            'def get_client():\n import requests\n return requests\nget_client().get("url")',  # noqa: E501
            id='call-on-call-result',
        ),
        pytest.param(
            'def get_obj():\n class Obj:\n  attr = None\n return Obj()\nget_obj().attr.method("url")',  # noqa: E501
            id='nested-attribute-on-call',
        ),
    ),
)
def test_no_requests_expression(s):
    assert not results(s)


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            '''\
import requests
a = requests.session(foo="bar")
''',
            id='requests-session',
        ),
        pytest.param(
            '''\
import urllib.request
a = urllib.request.Request(foo="bar")
''',
            id='urllib-request-constructor',
        ),
        pytest.param(
            'import requests\nrequests.unknown_method("url")',
            id='requests-unknown-method',
        ),
        pytest.param(
            'from urllib import request\n\nrequest.unknown_method("url")',
            id='urllib-request-unknown-method',
        ),
        pytest.param(
            'from urllib import request\n\nrequest.untracked_function("url")',
            id='urllib-request-untracked-function',
        ),
    ),
)
def test_unknown_method(s):
    assert not results(s)


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            '''\
import requests
a = requests.post("https://example.com", timeout=5, foo="bar")
''',
            id='requests-post-with-timeout',
        ),
        pytest.param(
            '''\
import urllib.request
a = urllib.request.urlopen(
    "https://example.com",
    timeout=5,
    bar="baz",
)
''',
            id='urllib-urlopen-with-timeout',
        ),
    ),
)
def test_timout_is_kwarg(s):
    assert not results(s)


def test_timout_is_arg():
    s = '''\
import urllib.request
a = urllib.request.urlopen("https://example.com", None, 5, arg="t")
'''
    assert not results(s)


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            '''\
import requests
a = requests.post("https://example.com", params={"bar": "baz"})
''',
            id='requests-post-no-timeout',
        ),
        pytest.param(
            '''\
import requests
a = requests.post("https://example.com", timeout=None)
''',
            id='requests-post-timeout-none',
        ),
        pytest.param(
            '''\
import requests
a = requests.get("https://example.com", timeout=None)
''',
            id='requests-get-timeout-none',
        ),
        pytest.param(
            '''\
import requests
a = requests.put("https://example.com", timeout=None)
''',
            id='requests-put-timeout-none',
        ),
        pytest.param(
            '''\
import requests
a = requests.delete("https://example.com", timeout=None)
''',
            id='requests-delete-timeout-none',
        ),
        pytest.param(
            '''\
import urllib.request
a = urllib.request.urlopen("https://example.com", bar="baz")
''',
            id='urllib-urlopen-no-timeout',
        ),
    ),
)
def test_timeout_missing(s):
    msg, = results(s)
    assert msg == '2:4: TIM100 request call has no timeout'


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            '''\
import requests
a = foo(bar=requests.get("https://example.com"))
''',
            id='requests-as-kwarg',
        ),
        pytest.param(
            '''\
import urllib.request
a = foo(bar=urllib.request.urlopen("https://example.com"))
''',
            id='urllib-as-kwarg',
        ),
    ),
)
def test_call_as_func_kwarg(s):
    msg, = results(s)
    assert msg == '2:12: TIM100 request call has no timeout'


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            '''\
import requests
a = foo(requests.get("https://example.com"))
''',
            id='requests-as-positional',
        ),
        pytest.param(
            '''\
import urllib.request
a = foo(urllib.request.urlopen("https://example.com"))
''',
            id='urllib-as-positional',
        ),
    ),
)
def test_call_as_func_pos_arg(s):
    msg, = results(s)
    assert msg == '2:8: TIM100 request call has no timeout'


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            '''\
import requests
foo(bar=requests.get("https://example.com"))
''',
            id='requests-no-assignment',
        ),
        pytest.param(
            '''\
import urllib.request
foo(bar=urllib.request.urlopen("https://example.com"))
''',
            id='urllib-no-assignment',
        ),
    ),
)
def test_call_as_func_kwarg_no_assing(s):
    msg, = results(s)
    assert msg == '2:8: TIM100 request call has no timeout'


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            '''\
import requests
def foo(bar=requests.get("https://example.com")): ...
''',
            id='requests-function-default',
        ),
        pytest.param(
            '''\
import urllib.request
def foo(bar=urllib.request.urlopen("https://example.com")): ...
''',
            id='urllib-function-default',
        ),
    ),
)
def test_call_as_func_arg_default(s):
    msg, = results(s)
    assert msg == '2:12: TIM100 request call has no timeout'


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            'from urllib.request import urlopen\nurlopen("google.com")',
            id='from-import-direct-call',
        ),
        pytest.param(
            'from urllib import request\nrequest.urlopen("google.com")',
            id='from-import-module-then-attr',
        ),
        pytest.param(
            'from urllib.request import urlopen as _urlopen\n_urlopen("t.de")',
            id='from-import-with-alias',
        ),
        pytest.param(
            'from requests import get\nget("https://example.com")',
            id='requests-from-import',
        ),
        pytest.param(
            'from requests import post\npost("https://example.com", data={"key": "value"})',  # noqa: E501
            id='requests-from-import-post',
        ),
        pytest.param(
            'import requests as req\nreq.get("https://example.com")',
            id='import-requests-with-alias',
        ),
        pytest.param(
            'import urllib.request as ur\nur.urlopen("google.com")',
            id='import-urllib-request-with-alias',
        ),
    ),
)
def test_different_import_styles_no_timeout(s):
    msg, = results(s)
    assert msg == '2:0: TIM100 request call has no timeout'


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            'from urllib.request import urlopen\nurlopen("google.com", timeout=5)',  # noqa: E501
            id='from-import-direct-call',
        ),
        pytest.param(
            'from urllib import request\nrequest.urlopen("google.com", timeout=5)',  # noqa: E501
            id='from-import-module-then-attr',
        ),
        pytest.param(
            'from urllib.request import urlopen as _urlopen\n_urlopen("google.com", timeout=5)',  # noqa: E501
            id='from-import-with-alias',
        ),
        pytest.param(
            'from requests import get\nget("https://example.com", timeout=5)',
            id='requests-from-import',
        ),
        pytest.param(
            'import requests as req\nreq.get("https://t.com", timeout=5)',
            id='import-requests-with-alias',
        ),
        pytest.param(
            'import urllib.request as ur\nur.urlopen("google.com", timeout=5)',
            id='import-urllib-request-with-alias',
        ),
    ),
)
def test_import_styles_with_timeout(s):
    assert not results(s)


@pytest.fixture
def manager():
    mgr = OptionManager(
        version='0',
        plugin_versions='',
        formatter_names=(),
        parents=[],
    )
    Plugin.add_options(mgr)
    return mgr


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            'import requests\nrequests.get("url")',
            id='requests-get',
        ),
        pytest.param(
            'import requests\nrequests.post("url")',
            id='requests-post',
        ),
        pytest.param(
            'from requests import get\nget("url")',
            id='requests-from-import-get',
        ),
        pytest.param(
            'from requests import post\npost("url")',
            id='requests-from-import-post',
        ),
        pytest.param(
            'import urllib.request\nurllib.request.urlopen("url")',
            id='urllib-import-urlopen',
        ),
        pytest.param(
            'from urllib.request import urlopen\nurlopen("url")',
            id='urllib-from-import-urlopen',
        ),
    ),
)
def test_option_parsing_no_custom_functions_use_defaults(
        s: str,
        manager: OptionManager,
) -> None:
    Plugin.parse_options(manager.parse_args([]))
    msg, = results(s)
    assert msg == '2:0: TIM100 request call has no timeout'


def test_option_parsing_extend_functions(manager: OptionManager) -> None:
    options = manager.parse_args([
        '--timeout-extend-funcs=foo.bar.baz,my.module.request',
    ])
    Plugin.parse_options(options)

    # default functions should still work
    s = 'import requests\nrequests.get("url")'
    msg, = results(s)
    assert msg == '2:0: TIM100 request call has no timeout'

    # extended function should also work
    s = 'from foo import bar\nbar.baz("url")'
    msg, = results(s)
    assert msg == '2:0: TIM100 request call has no timeout'


def test_option_parsing_override_functions(manager: OptionManager) -> None:
    options = manager.parse_args(['--timeout-funcs=foo.bar.baz'])
    Plugin.parse_options(options)

    # default functions should not be detected
    s = 'import requests\nrequests.get("url")'
    assert not results(s)

    # new function is detected
    s = 'from foo import bar\nbar.baz("url")'
    msg, = results(s)
    assert msg == '2:0: TIM100 request call has no timeout'


def test_option_parsing_positional_arg_timeout(manager: OptionManager) -> None:
    options = manager.parse_args([
        '--timeout-extend-funcs=my.func:3,other.func:1',
    ])
    Plugin.parse_options(options)

    # timeout at idx 3 works
    s = 'from my import func\nfunc("url", None, None, 10)'
    assert not results(s)

    # timeout at idx 1 works
    s = 'from other import func\nfunc("url", 10)'
    assert not results(s)


def test_custom_tracked_function_no_timeout(manager: OptionManager) -> None:
    options = manager.parse_args(
        ['--timeout-extend-funcs=foo.bar.baz'],
    )
    Plugin.parse_options(options)

    s = 'from foo import bar\nbar.baz("url")'
    msg, = results(s)
    assert msg == '2:0: TIM100 request call has no timeout'


def test_custom_tracked_function_with_timeout(manager: OptionManager) -> None:
    options = manager.parse_args(
        ['--timeout-extend-funcs=foo.bar.baz'],
    )
    Plugin.parse_options(options)

    s = 'from foo import bar\nbar.baz("url", timeout=5)'
    assert not results(s)


def test_custom_positional_timeout(manager: OptionManager) -> None:
    options = manager.parse_args([
        '--timeout-extend-funcs=my.module.func:2',
    ])
    Plugin.parse_options(options)

    s = '''\
from my import module
module.func('url', None, 10)
'''
    assert not results(s)


def test_custom_positional_timeout_missing(manager: OptionManager) -> None:
    options = manager.parse_args([
        '--timeout-extend-funcs=my.module.func:2',
    ])
    Plugin.parse_options(options)

    s = 'from my import module\nmodule.func("url", None)'
    # Should fail because only 2 args but needs 3
    msg, = results(s)
    assert msg == '2:0: TIM100 request call has no timeout'


@pytest.mark.parametrize(
    ('spec', 'expected'),
    (
        pytest.param(
            'urllib.request.urlopen',
            (('urllib.request', 'urlopen'), None),
            id='urllib-no-index',
        ),
        pytest.param(
            'requests.get',
            (('requests', 'get'), None),
            id='requests-no-index',
        ),
        pytest.param(
            'foo.bar.baz',
            (('foo.bar', 'baz'), None),
            id='nested-module-no-index',
        ),
        pytest.param(
            'a.b.c.d.e',
            (('a.b.c.d', 'e'), None),
            id='deeply-nested-no-index',
        ),
        pytest.param(
            'urllib.request.urlopen:2',
            (('urllib.request', 'urlopen'), 2),
            id='urllib-with-index',
        ),
        pytest.param(
            'my.func:0',
            (('my', 'func'), 0),
            id='index-zero',
        ),
        pytest.param(
            'foo.bar:5',
            (('foo', 'bar'), 5),
            id='index-five',
        ),
    ),
)
def test_parse_function_spec_valid(spec, expected):
    assert parse_function_spec(spec) == expected


@pytest.mark.parametrize(
    ('spec', 'error_msg'),
    (
        pytest.param(
            'single',
            "Function spec must be at least 'module.function': single",
            id='missing-module',
        ),
        pytest.param(
            'my.func:abc',
            'Positional index must be an integer in spec: my.func:abc',
            id='invalid-index-non-digit',
        ),
        pytest.param(
            'foo.bar:notanumber',
            'Positional index must be an integer in spec: foo.bar:notanumber',
            id='invalid-index-text',
        ),
    ),
)
def test_parse_function_spec_invalid(spec, error_msg):
    with pytest.raises(ValueError) as excinfo:
        parse_function_spec(spec)
    msg, = excinfo.value.args
    assert msg == error_msg


def test_complex_nested_expression():
    s = '''\
import requests

def outer():
    def inner():
        requests.get('url')
    return inner
'''
    msg, = results(s)
    assert msg == '5:8: TIM100 request call has no timeout'
