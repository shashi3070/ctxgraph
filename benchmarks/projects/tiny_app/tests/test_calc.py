"""Basic tests for calculator functions."""

import math
import pytest

from calc.core import add, sub, mul, div, power, sqrt
from calc.parser import tokenize, parse, evaluate


class TestCore:
    def test_add(self) -> None:
        assert add(2, 3) == 5
        assert add(-1, 1) == 0

    def test_sub(self) -> None:
        assert sub(10, 3) == 7
        assert sub(5, 10) == -5

    def test_mul(self) -> None:
        assert mul(4, 3) == 12
        assert mul(0, 100) == 0

    def test_div(self) -> None:
        assert div(10, 2) == 5
        assert div(7, 3) == pytest.approx(2.333_333_3)

    def test_div_by_zero(self) -> None:
        with pytest.raises(ZeroDivisionError):
            div(5, 0)

    def test_power(self) -> None:
        assert power(2, 3) == 8
        assert power(9, 0.5) == 3.0

    def test_sqrt(self) -> None:
        assert sqrt(9) == 3.0
        assert sqrt(0) == 0.0

    def test_sqrt_negative(self) -> None:
        with pytest.raises(ValueError, match="negative"):
            sqrt(-4)


class TestParser:
    def test_tokenize_simple(self) -> None:
        assert tokenize("3 + 4") == ["3", "+", "4"]

    def test_tokenize_complex(self) -> None:
        assert tokenize("sqrt(9)") == ["sqrt", "(", "9", ")"]

    def test_parse_addition(self) -> None:
        tree = parse(tokenize("2 + 3"))
        assert tree.evaluate() == 5.0

    def test_parse_precedence(self) -> None:
        tree = parse(tokenize("2 + 3 * 4"))
        assert tree.evaluate() == 14.0

    def test_parse_parentheses(self) -> None:
        tree = parse(tokenize("(2 + 3) * 4"))
        assert tree.evaluate() == 20.0

    def test_parse_sqrt(self) -> None:
        tree = parse(tokenize("sqrt(16)"))
        assert tree.evaluate() == 4.0

    def test_evaluate_string(self) -> None:
        assert evaluate("3 + 5") == 8.0
        assert evaluate("2 ^ 3") == 8.0

    def test_invalid_token(self) -> None:
        with pytest.raises(ValueError, match="unexpected character"):
            tokenize("3 @ 4")


class TestE2E:
    def test_pipeline(self) -> None:
        from calc.parser import tokenize, parse

        tokens = tokenize("((1 + 2) * 3) - 4")
        tree = parse(tokens)
        assert tree.evaluate() == 5.0
