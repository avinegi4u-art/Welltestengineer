"""Command-line interface for Defluffer."""

from __future__ import annotations

import argparse
import sys

from .core import Defluffer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="defluffer",
        description="Compress verbose LLM prompts by removing fluff and filler.",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="Prompt text to compress (reads stdin if omitted)",
    )
    parser.add_argument(
        "-p",
        "--profile",
        default="standard",
        choices=("safe", "standard", "standardGuardedDedupe"),
        help="Compression profile (default: standard)",
    )
    parser.add_argument(
        "-s",
        "--stats",
        action="store_true",
        help="Print token savings stats to stderr",
    )
    parser.add_argument(
        "--no-skip-sensitive",
        action="store_true",
        help="Do not skip legal/policy/exact-output prompts",
    )
    args = parser.parse_args(argv)

    if args.prompt is not None:
        prompt = args.prompt
    else:
        prompt = sys.stdin.read()

    engine = Defluffer(
        profile=args.profile,
        skip_sensitive=not args.no_skip_sensitive,
    )
    result = engine.compress_detailed(prompt)
    sys.stdout.write(result.text)
    if not result.text.endswith("\n") and "\n" in prompt:
        sys.stdout.write("\n")

    if args.stats:
        sys.stderr.write(
            f"tokens: {result.original_tokens} -> {result.defluffed_tokens} "
            f"(saved {result.saved_tokens}, {result.savings_pct:.1f}%)\n"
        )
        if result.reason:
            sys.stderr.write(f"note: {result.reason}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
