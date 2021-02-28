# sympy_clone_expression

Simple clone (aka deepcopy) function that supports `evaluate==False`.

Originally submitted as [PR](https://github.com/sympy/sympy/pull/20665) to fix longstanding issue but considered too complicated as uses Python AST. It worked well for me and might be useful to others so I have created this module.

# Installation
```bash
$ poetry add git+https://github.com/bsdz/sympy_clone_expression.git#main
```

# Usage

To clone (aka deepcopy) expression do something along the lines of:

```python
import sympy as sp
from sympy_clone_expression import clone, to_ast
expr = sp.Add(
    sp.Pow(sp.Integer(2), 2, evaluate=False),
    sp.Pow(sp.Float(3.1), 2, evaluate=False),
    evaluate=False,
)
expr_copy = clone(expr)
assert expr_copy == expr
```

To generate Python AST for expression (this could be used for pickling for example):

```python
ast_expression, symbols = to_ast(expr)
roundtrip_expr = eval(compile(ast_expr, filename="<ast>", mode="eval"), symbols)
```