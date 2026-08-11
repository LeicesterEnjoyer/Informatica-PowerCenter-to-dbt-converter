import sys
import argparse
from collections.abc import Sequence

from .converter import write_model


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert a supported PowerCenter XML target to a dbt SQL model."
    )
    parser.add_argument("xml", help="PowerCenter XML export path")
    parser.add_argument("--mapping", required=True, help="PowerCenter mapping name")
    parser.add_argument("--target", required=True, help="PowerCenter target name")
    parser.add_argument("--output", required=True, help="Output dbt SQL file")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        write_model(
            arguments.xml,
            arguments.mapping,
            arguments.target,
            arguments.output,
        )
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    return 0
