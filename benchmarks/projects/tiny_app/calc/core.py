"""Core calculation functions for the tiny_app calculator."""

import math
from typing import Union

Number = Union[int, float]


def add(a: Number, b: Number) -> Number:
    """Return the sum of a and b."""
    return a + b


def sub(a: Number, b: Number) -> Number:
    """Return the difference of a and b."""
    return a - b


def mul(a: Number, b: Number) -> Number:
    """Return the product of a and b."""
    return a * b


def div(a: Number, b: Number) -> Number:
    """Return the quotient of a divided by b.

    Raises:
        ZeroDivisionError: If b is zero.
    """
    if b == 0:
        raise ZeroDivisionError("division by zero is not allowed")
    return a / b


def power(a: Number, b: Number) -> Number:
    """Return a raised to the power of b."""
    return a ** b


def sqrt(a: Number) -> Number:
    """Return the square root of a.

    Raises:
        ValueError: If a is negative.
    """
    if a < 0:
        raise ValueError("cannot compute square root of a negative number")
    return math.sqrt(a)
