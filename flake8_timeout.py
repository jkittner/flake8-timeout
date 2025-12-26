import argparse
import ast
import importlib.metadata as importlib_metadata
from collections.abc import Generator
from typing import Any

from flake8.options.manager import OptionManager

MSG = 'TIM100 request call has no timeout'
# Format: 'module.function' or 'module.function:positional_index'
DEFAULT_TRACKED_FUNCTIONS = [
    'urllib.request.urlopen:2',  # urlopen(url, data=None, timeout=...)
    'requests.get',  # get(url, **kwargs)
    'requests.post',
    'requests.put',
    'requests.delete',
    'requests.head',
    'requests.patch',
    'requests.options',
    'requests.request',
]


def parse_function_spec(spec: str) -> tuple[tuple[str, str], int | None]:
    # Split off positional index if present
    if ':' in spec:
        func_part, index_str = spec.rsplit(':', 1)
        if not index_str.isdigit():
            raise ValueError(
                f"Positional index must be an integer in spec: {spec}",
            )
        positional_index = int(index_str)
    else:
        func_part = spec
        positional_index = None

    # Parse the function part
    parts = func_part.split('.')
    if len(parts) < 2:
        raise ValueError(
            f"Function spec must be at least 'module.function': {spec}",
        )

    return ('.'.join(parts[:-1]), parts[-1]), positional_index


class Visitor(ast.NodeVisitor):
    def __init__(
            self,
            tracked_functions: set[tuple[str, str]],
            timeout_positional: dict[str, int],
    ) -> None:
        self.assignments: list[tuple[int, int]] = []
        # map local names to (module, attr) tuples
        # 'urlopen': ('urllib.request', 'urlopen')
        # 'request': ('urllib', 'request') for module imports
        self.imports: dict[str, tuple[str, str | None]] = {}
        self.tracked_functions = tracked_functions
        self.timeout_positional = timeout_positional

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            local_name = (
                alias.asname if alias.asname else alias.name.split('.')[-1]
            )
            self.imports[local_name] = (alias.name, None)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module is None:
            self.generic_visit(node)
            return

        for alias in node.names:
            local_name = alias.asname if alias.asname else alias.name
            self.imports[local_name] = (node.module, alias.name)
        self.generic_visit(node)

    def _check_timeout(
            self,
            node: ast.Call,
            func_spec: str | None = None,
    ) -> bool:
        # Check keyword arguments
        for kwarg in node.keywords:
            if (
                kwarg.arg == 'timeout' and
                isinstance(kwarg.value, ast.Constant) and
                kwarg.value.value is not None
            ):
                return True

        # Check posargs if function has a known positional timeout index
        if func_spec and func_spec in self.timeout_positional:
            pos_index = self.timeout_positional[func_spec]
            if len(node.args) > pos_index:
                return True

        return False

    def visit_Call(self, node: ast.Call) -> None:
        func_spec: str | None = None

        # direct function call
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self.imports:
                module, attr = self.imports[func_name]
                # attr should be the function name for 'from X import Y'
                if attr and (module, attr) in self.tracked_functions:
                    func_spec = f"{module}.{attr}"

        # attribute call
        elif isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr

            # Check if the base is a Name (requests.get or request.urlopen)
            if isinstance(node.func.value, ast.Name):
                base_name = node.func.value.id

                if base_name in self.imports:
                    module, imported_attr = self.imports[base_name]

                    # If imported_attr is None, it's a module import
                    if imported_attr is None:
                        # Check if module.attr is tracked
                        if (module, attr_name) in self.tracked_functions:
                            func_spec = f"{module}.{attr_name}"
                    else:
                        full_module = f"{module}.{imported_attr}"
                        if (full_module, attr_name) in self.tracked_functions:
                            func_spec = f"{full_module}.{attr_name}"

            # nested attribute: urllib.request.urlopen('url')
            elif isinstance(node.func.value, ast.Attribute):
                if isinstance(node.func.value.value, ast.Name):
                    base = node.func.value.value.id
                    middle = node.func.value.attr
                    func = attr_name
                    full_spec = f"{base}.{middle}.{func}"
                    module_part = f"{base}.{middle}"

                    if (module_part, func) in self.tracked_functions:
                        func_spec = full_spec

        if func_spec:
            if not self._check_timeout(node, func_spec):
                self.assignments.append((node.lineno, node.col_offset))

        self.generic_visit(node)


class Namespace(argparse.Namespace):
    timeout_funcs: list[str] = []
    timeout_extend_funcs: list[str] = []


class Plugin:
    name = __name__
    version = importlib_metadata.version(__name__)

    def __init__(self, tree: ast.AST):
        self._tree = tree
        self.tracked_functions = getattr(Plugin, 'tracked_functions', None)
        self.extend_tracked_functions = getattr(
            Plugin, 'extend_tracked_functions', [],
        )

    @classmethod
    def add_options(cls, option_manager: OptionManager) -> None:
        option_manager.add_option(
            '--timeout-funcs',
            default=DEFAULT_TRACKED_FUNCTIONS,
            parse_from_config=True,
            comma_separated_list=True,
            help=(
                'Comma-separated list of fully qualified function names to '
                'check for timeout. This OVERRIDES the defaults. '
                'Format: "module.function" or "module.function:index" where '
                'index is the positional argument index for timeout '
                '(e.g., "foo.bar.baz,my.func:2"). '
            ),
        )
        option_manager.add_option(
            '--timeout-extend-funcs',
            default='',
            parse_from_config=True,
            comma_separated_list=True,
            help=(
                'Comma-separated list of additional fully qualified function '
                'names to check for timeout. This EXTENDS the default list. '
                'Format: "module.function" or "module.function:index" where '
                'index is the positional argument index for timeout '
                '(e.g., "foo.bar.baz,my.func:2").'
            ),
        )

    @classmethod
    def parse_options(cls, options: Namespace) -> None:
        # Validate tracked_functions specs
        for spec in options.timeout_funcs:
            parse_function_spec(spec)

        # Validate extend_tracked_functions specs
        for spec in options.timeout_extend_funcs:
            parse_function_spec(spec)

        cls.tracked_functions = options.timeout_funcs
        cls.extend_tracked_functions = options.timeout_extend_funcs

    def _parse_tracked_functions(
            self,
            specs: list[str],
    ) -> tuple[set[tuple[str, str]], dict[str, int]]:
        tracked = set()
        positional = {}

        for spec in specs:
            (module, func), pos_index = parse_function_spec(spec)
            tracked.add((module, func))
            if pos_index is not None:
                positional[f"{module}.{func}"] = pos_index

        return tracked, positional

    def run(self) -> Generator[tuple[int, int, str, type[Any]], None, None]:
        # Determine which functions to track
        if self.extend_tracked_functions:
            # Extension mode: use defaults + extensions
            specs = list(DEFAULT_TRACKED_FUNCTIONS)
            specs.extend(self.extend_tracked_functions)
        elif self.tracked_functions is not None:
            # Override mode: use only specified functions
            specs = self.tracked_functions
        else:
            # Default mode: use defaults
            specs = list(DEFAULT_TRACKED_FUNCTIONS)

        tracked_functions, timeout_positional = self._parse_tracked_functions(
            specs,
        )

        visitor = Visitor(tracked_functions, timeout_positional)
        visitor.visit(self._tree)
        for line, col in visitor.assignments:
            yield line, col, MSG, type(self)
