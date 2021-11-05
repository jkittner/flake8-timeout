import ast
import importlib.metadata as importlib_metadata
from typing import Any
from typing import Generator
from typing import List
from typing import Tuple
from typing import Type

MSG = 'TIM100 request call has no timeout'

METHODS = [
    'request', 'get', 'head', 'post',
    'patch', 'put', 'delete', 'options',
]


class Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.assignments: List[Tuple[int, int]] = []

    def visit_Call(self, node: ast.Call) -> None:
        if (
                isinstance(node, ast.Call) and
                isinstance(node.func, ast.Attribute) and
                isinstance(node.func.value, ast.Name) and
                node.func.value.id == 'requests' and
                node.func.attr in METHODS
        ):
            for kwarg in node.keywords:
                if (
                        kwarg.arg == 'timeout' and
                        isinstance(kwarg.value, ast.Constant) and
                        kwarg.value.value is not None
                ):
                    break
            else:
                self.assignments.append((node.lineno, node.col_offset))
        elif (
            isinstance(node, ast.Call) and
            isinstance(node.func, ast.Attribute) and
            isinstance(node.func.value, ast.Attribute) and
            isinstance(node.func.value.value, ast.Name) and
            node.func.value.value.id == 'urllib' and
            node.func.value.attr == 'request' and
            node.func.attr == 'urlopen'
        ):
            for kwarg in node.keywords:
                if (
                    kwarg.arg == 'timeout' and
                    isinstance(kwarg.value, ast.Constant) and
                    kwarg.value.value is not None
                ):
                    break
            else:
                # check if it was passed as a positional argument instead
                # args are: (url, data=None, [timeout, ]*, cafile=None ...
                if len(node.args) < 3:
                    self.assignments.append((node.lineno, node.col_offset))

        self.generic_visit(node)


class Plugin:
    name = __name__
    version = importlib_metadata.version(__name__)

    def __init__(self, tree: ast.AST):
        self._tree = tree

    def run(self) -> Generator[Tuple[int, int, str, Type[Any]], None, None]:
        visitor = Visitor()
        visitor.visit(self._tree)
        for line, col in visitor.assignments:
            yield line, col, MSG, type(self)
