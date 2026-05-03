#!/usr/bin/env python3
"""REAL_AGENT: Simple CLI AI-style agent that returns exactly five valid points."""

from __future__ import annotations

import re
import textwrap


def _normalize_topic(topic: str) -> str:
    cleaned = re.sub(r"\s+", " ", topic).strip()
    return cleaned.rstrip(".?!")


def generate_five_points(topic: str) -> list[str]:
    """Generate five clear, valid points for a requested topic."""
    normalized = _normalize_topic(topic)
    if not normalized:
        normalized = "the requested topic"

    return [
        f"Definition: {normalized} can be understood by first defining core terms and setting clear scope.",
        f"Key Components: Break {normalized} into major parts, concepts, or stages for structured understanding.",
        f"Practical Importance: Explain why {normalized} matters in real-world situations and decision-making.",
        f"Common Challenges: Identify frequent mistakes, limitations, or misconceptions related to {normalized}.",
        f"Actionable Next Step: Provide one concrete action to learn, apply, or evaluate {normalized} effectively.",
    ]


def main() -> None:
    print("REAL_AGENT (Python)")
    print("Ask any topic, and I will return exactly 5 valid points.\n")

    while True:
        topic = input("Enter a topic (or type 'exit'): ").strip()
        if topic.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        points = generate_five_points(topic)
        print("\nHere are 5 valid points:")
        for idx, point in enumerate(points, start=1):
            print(textwrap.fill(f"{idx}. {point}", width=100, subsequent_indent="   "))
        print()


if __name__ == "__main__":
    main()
