[![ci](https://github.com/theendlessriver13/flake8-timeout/workflows/ci/badge.svg)](https://github.com/theendlessriver13/flake8-timeout/actions?query=workflow%3Aci)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/theendlessriver13/flake8-timeout/master.svg)](https://results.pre-commit.ci/latest/github/theendlessriver13/flake8-timeout/master)
[![codecov](https://codecov.io/gh/theendlessriver13/flake8-timeout/branch/master/graph/badge.svg)](https://codecov.io/gh/theendlessriver13/flake8-timeout)

# flake8-timeout

flake8 plugin which checks that a timeout is set in all `requests` and `urllib.request.open` calls.

- For example: `requests.post('https://example.com')` or `urllib.request.open('https://example.com')` will trigger `FTA100`
- `requests.post('https://example.com', timeout=5)` or `urllib.request.open('https://example.com', timeout=5)` is expected instead

## installation

`pip install flake8-timeout`

## flake8 code

| Code   | Description                       |
| ------ | --------------------------------- |
| FTA100 | timeout missing for requests call |

## as a pre-commit hook

See [pre-commit](https://pre-commit.com) for instructions

Sample `.pre-commit-config.yaml`:

```yaml
-   repo: https://github.com/pycqa/flake8
    rev: 3.9.1
    hooks:
    -   id: flake8
        additional_dependencies: [flake8-timeout==0.1.0]
```
