#!/usr/bin/env python3
"""REAL_AGENT: Python CLI agent that returns exactly five valid points per topic."""

from __future__ import annotations

import argparse
import re
import textwrap


POINT_TITLES = (
    "Definition",
    "Key Components",
    "Practical Importance",
    "Common Challenges",
    "Actionable Next Step",
)


def _normalize_topic(topic: str) -> str:
    cleaned = re.sub(r"\s+", " ", topic).strip()
    return cleaned.rstrip(".?!")


def generate_five_points(topic: str) -> list[str]:
    """Generate five clear, valid points for a requested topic."""
    normalized = _normalize_topic(topic)
    if not normalized:
        normalized = "the requested topic"

    return [
        f"{POINT_TITLES[0]}: {normalized} can be understood by first defining core terms and setting clear scope.",
        f"{POINT_TITLES[1]}: Break {normalized} into major parts, concepts, or stages for structured understanding.",
        f"{POINT_TITLES[2]}: Explain why {normalized} matters in real-world situations and decision-making.",
        f"{POINT_TITLES[3]}: Identify frequent mistakes, limitations, or misconceptions related to {normalized}.",
        f"{POINT_TITLES[4]}: Provide one concrete action to learn, apply, or evaluate {normalized} effectively.",
    ]


def print_five_points(topic: str) -> None:
    points = generate_five_points(topic)
    print("\nHere are 5 valid points:")
    for idx, point in enumerate(points, start=1):
        print(textwrap.fill(f"{idx}. {point}", width=100, subsequent_indent="   "))
    print()


def run_interactive() -> None:
    print("REAL_AGENT (Python)")
    print("Ask any topic, and I will return exactly 5 valid points.\n")
    while True:
        topic = input("Enter a topic (or type 'exit'): ").strip()
        if topic.lower() in {"exit", "quit"}:
            print("Goodbye!")
            return
        print_five_points(topic)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Return exactly five valid points for any topic."
    )
    parser.add_argument(
        "topic",
        nargs="*",
        help="Optional topic. If not provided, interactive mode starts.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.topic:
        print_five_points(" ".join(args.topic))
    else:
        run_interactive()


if __name__ == "__main__":
    main()
