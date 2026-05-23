"""Expression tokenizer and parser for arithmetic expressions."""

from __future__ import annotations

import re
from typing import List, Optional, Union


class Expression:
    """Base class for all parsed expression nodes."""

    def evaluate(self) -> float:
        """Evaluate the expression and return the result."""
        raise NotImplementedError


class Number(Expression):
    """A literal number in the expression tree."""

    def __init__(self, value: Union[int, float]) -> None:
        self.value = value

    def evaluate(self) -> float:
        return float(self.value)

    def __repr__(self) -> str:
        return f"Number({self.value})"


class BinOp(Expression):
    """A binary operation between two sub-expressions."""

    def __init__(self, left: Expression, op: str, right: Expression) -> None:
        self.left = left
        self.op = op
        self.right = right

    def evaluate(self) -> float:
        from .core import add, sub, mul, div, power

        lv = self.left.evaluate()
        rv = self.right.evaluate()
        dispatch = {"+": add, "-": sub, "*": mul, "/": div, "^": power}
        fn = dispatch.get(self.op)
        if fn is None:
            raise ValueError(f"unknown operator: {self.op}")
        return fn(lv, rv)

    def __repr__(self) -> str:
        return f"BinOp({self.left}, {self.op!r}, {self.right})"


class UnaryOp(Expression):
    """A unary operation applied to a sub-expression."""

    def __init__(self, op: str, operand: Expression) -> None:
        self.op = op
        self.operand = operand

    def evaluate(self) -> float:
        val = self.operand.evaluate()
        if self.op == "-":
            return -val
        if self.op == "sqrt":
            from .core import sqrt
            return sqrt(val)
        raise ValueError(f"unknown unary operator: {self.op}")

    def __repr__(self) -> str:
        return f"UnaryOp({self.op!r}, {self.operand})"


TOKEN_RE = re.compile(r"\s*(?:(\d+\.?\d*|\.\d+)|([+\-*/^()])|(sqrt))\s*")


def tokenize(text: str) -> List[str]:
    """Split an expression string into a list of tokens.

    Args:
        text: A raw expression string, e.g. "3 + 4 * 2".

    Returns:
        A list of token strings.

    Raises:
        ValueError: On unrecognized characters.
    """
    tokens: List[str] = []
    pos = 0
    while pos < len(text):
        m = TOKEN_RE.match(text, pos)
        if m is None:
            raise ValueError(f"unexpected character at position {pos}: {text[pos]!r}")
        if m.group(1):
            tokens.append(m.group(1))
        elif m.group(2):
            tokens.append(m.group(2))
        elif m.group(3):
            tokens.append(m.group(3))
        pos = m.end()
    return tokens


def _to_rpn(tokens: List[str]) -> List[str]:
    """Convert infix tokens to RPN via the Shunting-yard algorithm."""
    precedence = {"+": 1, "-": 1, "*": 2, "/": 2, "^": 3}
    output: List[str] = []
    ops: List[str] = []

    for tok in tokens:
        if tok.replace(".", "", 1).lstrip("-").isdigit():
            output.append(tok)
        elif tok == "sqrt":
            ops.append(tok)
        elif tok == "(":
            ops.append(tok)
        elif tok == ")":
            while ops and ops[-1] != "(":
                output.append(ops.pop())
            ops.pop()
        else:
            while (ops and ops[-1] != "(" and
                   precedence.get(ops[-1], 0) >= precedence.get(tok, 0)):
                output.append(ops.pop())
            ops.append(tok)

    while ops:
        output.append(ops.pop())
    return output


def parse(tokens: List[str]) -> Expression:
    """Parse a list of tokens into an expression tree.

    Uses the Shunting-yard algorithm internally.

    Args:
        tokens: Token list from tokenize().

    Returns:
        An Expression tree (Number, BinOp, or UnaryOp).

    Raises:
        ValueError: If tokens cannot be parsed.
    """
    rpn = _to_rpn(tokens)
    stack: List[Expression] = []

    for tok in rpn:
        if tok.replace(".", "", 1).lstrip("-").isdigit():
            stack.append(Number(float(tok)))
        elif tok == "sqrt":
            if not stack:
                raise ValueError("not enough operands for sqrt")
            stack.append(UnaryOp("sqrt", stack.pop()))
        else:
            if len(stack) < 2:
                raise ValueError(f"not enough operands for operator {tok!r}")
            right = stack.pop()
            left = stack.pop()
            stack.append(BinOp(left, tok, right))

    if len(stack) != 1:
        raise ValueError("invalid expression")
    return stack[0]


def evaluate(expr_str: str) -> float:
    """Convenience: tokenize, parse, and evaluate an expression string.

    Args:
        expr_str: e.g. "3 + 4 * 2".

    Returns:
        The numeric result.
    """
    tokens = tokenize(expr_str)
    tree = parse(tokens)
    return tree.evaluate()
