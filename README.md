[![ci](https://github.com/jkittner/flake8-timeout/workflows/ci/badge.svg)](https://github.com/jkittner/flake8-timeout/actions?query=workflow%3Aci)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/jkittner/flake8-timeout/master.svg)](https://results.pre-commit.ci/latest/github/jkittner/flake8-timeout/master)

# flake8-timeout

A flake8 plugin that checks for missing `timeout` parameters in network calls.

[requests](https://requests.readthedocs.io/en/latest/api/#requests.Session.request) and [urllib.request.urlopen](https://docs.python.org/3/library/urllib.request.html#urllib.request.urlopen) do not set timeouts by default unlike [httpx](https://www.python-httpx.org/advanced/timeouts/) and [aiohttp](https://docs.aiohttp.org/en/stable/client_quickstart.html#timeouts).

flake8-timeout checks `requests` and `urllib.request.urlopen` calls by default but can be configured to track any function that accepts a timeout parameter.

## installation

```bash
pip install flake8-timeout
```

## flake8 code

| Code   | Description                      |
| ------ | -------------------------------- |
| TIM100 | timeout missing for request call |

## default tracked functions

The plugin tracks these functions by default:

- `requests.get`
- `requests.post`
- `requests.put`
- `requests.delete`
- `requests.head`
- `requests.patch`
- `requests.options`
- `requests.request`
- `urllib.request.urlopen` (timeout at positional index 2)

## configuration

### as a pre-commit hook

See [pre-commit](https://pre-commit.com) for instructions

Sample `.pre-commit-config.yaml`:

```yaml
-   repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
    -   id: flake8
        additional_dependencies: [flake8-timeout==2.0.0]
```

### extending the defaults

Use `--timeout-extend-funcs` to add custom functions while keeping the defaults:

**Command line:**
```bash
flake8 --timeout-extend-funcs=my_http_lib.request,custom.api.call:1
```

**Pre-commit:**
```yaml
-   repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
    -   id: flake8
        additional_dependencies: [flake8-timeout==2.0.0]
        args: [--timeout-extend-funcs=my_http_lib.request,custom.api.call:1]
```

This will check the defaults plus your custom functions.

### overriding the defaults

Use `--timeout-funcs` to replace the defaults entirely:

**Command line:**
```bash
flake8 --timeout-funcs=custom.http.get,custom.http.post:2
```

**Pre-commit:**
```yaml
-   repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
    -   id: flake8
        additional_dependencies: [flake8-timeout==2.0.0]
        args: [--timeout-funcs=custom.http.get,custom.http.post:2]
```

This will only check the functions you specify, ignoring the defaults.

### positional timeout arguments

Some functions accept timeout as a positional argument. Specify the 0-based index after a colon:

```
my_lib.fetch:2    # timeout is at index 2 (3rd argument)
other.call:0      # timeout is at index 0 (1st argument)
```

Example with positional timeout:

```python
# my_lib.fetch(url, data, timeout)
my_lib.fetch('https://api.example.com', None, 30)  # OK - timeout at index 2
my_lib.fetch('https://api.example.com', None)      # TIM100 - missing timeout
```
