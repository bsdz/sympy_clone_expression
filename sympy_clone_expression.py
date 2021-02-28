import ast
import importlib

import sympy as sp
import sympy.core.numbers


class _Node:
    """Used to store representation of expression graph
    for conversion to AST."""

    def __init__(self, expr, pos, parent_node):
        self.expr = expr
        self.pos = pos
        self.parent_node = parent_node
        self.child_nodes = []
        self.ast = None

    def __repr__(self):
        return "Node%s %s: [%s]: n:%s, p:%s, c:%s" % (
            "*" if self.ast is not None else "",
            self.pos,
            self.expr,
            self.expr.func.__name__,
            self.parent_node.pos if self.parent_node else None,
            [c.pos for c in self.child_nodes],
        )


def _traverse_expression(e, depth, nodes, pos=(), parent_node=None):
    """Recursive function to generate representation of expression graph."""
    n = _Node(e, pos, parent_node)
    if parent_node:
        parent_node.child_nodes.append(n)
    nodes.append(n)
    for i, arg in enumerate(e.args):
        if isinstance(arg, sp.Basic):
            _traverse_expression(arg, depth + 1, nodes, pos + (i,), n)


def _to_ast_call(module_name, func_name, args=[], kwds=[]):
    """Creates an AST equivalent sympy call."""
    # if module_name not in globals():
    #     globals()[module_name] = importlib.import_module(module_name)
    return ast.Call(
        func=ast.Attribute(
            value=ast.Name(id=module_name, ctx=ast.Load()),
            attr=func_name,
            ctx=ast.Load(),
        ),
        args=args,
        keywords=kwds,
    )


def to_ast(expr):
    """Return the AST for expr."""

    # generate tree that mirrors expression
    nodes = []
    _traverse_expression(expr, 0, nodes)

    # capture symbols for globals
    # TODO: encapsulate to_ast into class?
    symbols = {}

    def capture_module_symbol(module_name):
        if module_name not in symbols:
            symbols[module_name] = importlib.import_module(module_name)

    # find leaf nodes and convert to ast.Num
    for n in nodes:
        if not n.child_nodes:
            if isinstance(n.expr, (int, float)):
                n.ast = ast.Num(n=n.expr)
            if isinstance(
                n.expr,
                (
                    sympy.core.numbers.IntegerConstant,
                    sympy.core.numbers.RationalConstant,
                    sympy.core.numbers.Infinity,
                ),
            ):
                n.ast = _to_ast_call(
                    n.expr.func.__module__,
                    n.expr.func.__name__,
                )
                capture_module_symbol(n.expr.func.__module__)
            elif isinstance(n.expr, sp.Integer):
                n.ast = _to_ast_call(
                    n.expr.func.__module__,
                    n.expr.func.__name__,
                    [ast.Constant(value=int(n.expr))],
                )
                capture_module_symbol(n.expr.func.__module__)
            elif isinstance(n.expr, sp.Float):
                n.ast = _to_ast_call(
                    n.expr.func.__module__,
                    n.expr.func.__name__,
                    [ast.Constant(value=float(n.expr))],
                )
                capture_module_symbol(n.expr.func.__module__)
            elif isinstance(n.expr, sp.Symbol):
                n.ast = _to_ast_call(
                    n.expr.func.__module__,
                    n.expr.func.__name__,
                    [ast.Constant(value=str(n.expr))],
                    [
                        ast.keyword(arg=kw, value=ast.Constant(value=v))
                        for kw, v in n.expr.assumptions0.items()
                    ],
                )
                capture_module_symbol(n.expr.func.__module__)
            elif isinstance(n.expr, sp.Rational):
                n.ast = _to_ast_call(
                    n.expr.func.__module__,
                    n.expr.func.__name__,
                    [
                        ast.Constant(value=int(n.expr.numerator())),
                        ast.Constant(value=int(n.expr.denominator())),
                    ],
                )
                capture_module_symbol(n.expr.func.__module__)
            else:
                raise RuntimeError("Unsupported type")

    # find nodes where all children have ast generated
    while True:
        unchecked_nodes = [n for n in nodes if n.ast is None]
        if not unchecked_nodes:
            break
        for n in unchecked_nodes:
            if n.child_nodes and all([m.ast is not None for m in n.child_nodes]):
                n.ast = _to_ast_call(
                    n.expr.func.__module__,
                    n.expr.func.__name__,
                    [m.ast for m in n.child_nodes],
                    [ast.keyword(arg="evaluate", value=ast.Constant(value=False))],
                )
                capture_module_symbol(n.expr.func.__module__)

    # wrap in Expression and fix locations
    ast_expr = ast.Expression(body=nodes[0].ast)
    ast.fix_missing_locations(ast_expr)

    return ast_expr, symbols


def clone(expr):
    """Clone the sympy expr using intermediate AST.
    Preserves non-evaluation."""
    ast_expr, symbols = to_ast(expr)
    comp = compile(ast_expr, filename="<ast>", mode="eval")
    return eval(comp, symbols)
