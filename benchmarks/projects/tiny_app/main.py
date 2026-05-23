#!/usr/bin/env python3
"""Entry point for the tiny_app CLI calculator."""

import argparse
import sys
from typing import List, Optional

from calc.core import add, sub, mul, div, power, sqrt
from calc.parser import evaluate
from calc.plugins import PluginRegistry, HistoryPlugin, LoggingPlugin


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tiny_app",
        description="A tiny CLI calculator with plugin support.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    eval_p = sub.add_parser("eval", help="Evaluate an arithmetic expression")
    eval_p.add_argument("expression", type=str, help="Expression to evaluate, e.g. '3 + 4 * 2'")
    eval_p.add_argument("--no-plugins", action="store_true", help="Disable plugins")

    op_p = sub.add_parser("op", help="Perform a single arithmetic operation")
    op_p.add_argument("op", type=str, choices=["add", "sub", "mul", "div", "power", "sqrt"],
                      help="Operation name")
    op_p.add_argument("a", type=float, help="First operand")
    op_p.add_argument("b", type=float, nargs="?", default=None,
                      help="Second operand (not used for sqrt)")

    return parser


def dispatch_op(args: argparse.Namespace) -> Optional[float]:
    ops = {"add": add, "sub": sub, "mul": mul, "div": div, "power": power}
    if args.op == "sqrt":
        return sqrt(args.a)
    fn = ops.get(args.op)
    if fn is None:
        raise ValueError(f"unknown operation: {args.op}")
    if args.b is None:
        raise ValueError(f"{args.op} requires two arguments")
    return fn(args.a, args.b)


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "eval":
        registry = PluginRegistry()
        if not args.no_plugins:
            registry.register(HistoryPlugin())
            registry.register(LoggingPlugin())

        try:
            expr = registry.run_before(args.expression)
            result = evaluate(expr)
            registry.run_after(args.expression, result)
            print(result)
        except Exception as exc:
            registry.run_error(args.expression, exc)
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    elif args.command == "op":
        try:
            result = dispatch_op(args)
            print(result)
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
