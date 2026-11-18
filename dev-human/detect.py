#!/usr/bin/env python3
"""Score a dev.to draft for human-likeness using five local heuristics.

Usage:
    python3 detect.py draft.txt
    python3 detect.py before.txt after.txt   # prove the delta
"""
import json
import re
import sys
from pathlib import Path

SLOT = Path(__file__).with_name("slop.json")
with SLOT.open("r", encoding="utf-8") as f:
    SLOP = json.load(f)

REPLACEMENTS = SLOP["replacements"]


def load(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def sentences(text: str) -> list:
    return [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]


def burstiness(text: str) -> int:
    """Sentence-length variation. Higher = more human."""
    sents = sentences(text)
    if not sents:
        return 0
    lengths = [len(s.split()) for s in sents]
    mean = sum(lengths) / len(lengths)
    if mean == 0:
        return 0
    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    # Scale 0-100; more variation = higher score.
    return min(100, int((variance ** 0.5) / mean * 200)) if mean else 0


def specificity(text: str) -> int:
    """Numbers, names, concrete markers per 100 words."""
    words = text.split()
    if not words:
        return 0
    numbers = len(re.findall(r"\b\d[\d,.%]*\b", text))
    # Capitalized mid-sentence words as proxy for names/concrete markers.
    names = len(re.findall(r"(?<=\s)[A-Z][a-z]+(?=\s|[.!?,])", text))
    score = (numbers + names) / len(words) * 100
    return min(100, int(score * 10))


def slop_density(text: str) -> int:
    """Inverse: fewer slop hits = higher score."""
    words = text.split()
    if not words:
        return 100
    hits = 0
    for slop_word in REPLACEMENTS:
        hits += len(re.findall(r"\b" + re.escape(slop_word) + r"\b", text, re.IGNORECASE))
    density = hits / len(words) * 100
    # Inverse scale: 0 hits = 100, high density = 0.
    return max(0, 100 - int(density * 40))


def fingerprint(text: str) -> int:
    """Invisible chars, em dashes, curly quotes per 1k chars. Fewer = higher."""
    if not text:
        return 100
    bad = len(re.findall(r"[\u200b\u200c\u200d\u2060\ufeff\u2014\u2013\u201c\u201d\u2018\u2019\u2026\u2022\u00a0]", text))
    per_1k = bad / len(text) * 1000
    return max(0, 100 - int(per_1k * 50))


def voice(text: str) -> int:
    """Contractions, first person, varied structure. Higher = more human."""
    if not text:
        return 0
    contractions = len(re.findall(r"\b(?:don't|can't|won't|it's|you're|we're|i'm|let's|isn't|aren't)\b", text, re.IGNORECASE))
    first_person = len(re.findall(r"\b(?:I|me|my|myself|we|us|our)\b", text, re.IGNORECASE))
    words = text.split()
    if not words:
        return 0
    score = (contractions + first_person) / len(words) * 100
    return min(100, int(score * 8))


def score(text: str) -> dict:
    return {
        "BURSTINESS": burstiness(text),
        "SPECIFICITY": specificity(text),
        "SLOP DENSITY": slop_density(text),
        "FINGERPRINT": fingerprint(text),
        "VOICE": voice(text),
    }


def verdict(scores: dict) -> str:
    mean = sum(scores.values()) / len(scores)
    weakest = min(scores.values())
    if mean >= 70 and weakest >= 55:
        return "PASS"
    if mean >= 55 and weakest >= 40:
        return "REVIEW"
    return "FAIL"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    before_path = sys.argv[1]
    after_path = sys.argv[2] if len(sys.argv) > 2 else None

    before = load(before_path)
    s_before = score(before)
    v_before = verdict(s_before)

    print(f"BEFORE: {before_path}")
    for k, v in s_before.items():
        print(f"  {k}: {v}")
    print(f"  verdict: {v_before}")

    if after_path:
        after = load(after_path)
        s_after = score(after)
        v_after = verdict(s_after)
        print(f"\nAFTER: {after_path}")
        for k, v in s_after.items():
            print(f"  {k}: {v}")
        print(f"  verdict: {v_after}")
        print(f"\nDelta: mean {sum(s_before.values())/5:.0f} -> {sum(s_after.values())/5:.0f}")


if __name__ == "__main__":
    main()
