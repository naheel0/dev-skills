#!/usr/bin/env python3
"""Humanize a dev.to draft: strip slop, invisible chars, bad typography.

Usage:
    python3 humanize.py draft.txt [--report] [-o clean.txt]
"""
import json
import re
import sys
from pathlib import Path

SLOT = Path(__file__).with_name("slop.json")
with SLOT.open("r", encoding="utf-8") as f:
    SLOP = json.load(f)

REPLACEMENTS = SLOP["replacements"]

# Invisible / format characters to delete (keep newlines/tabs).
INVISIBLE_RE = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff\u202a-\u202e\u2066-\u2069]")

# Narrow / non-breaking spaces -> normal space (except inside code fences handled loosely).
NBSP_RE = re.compile(r"[\u00a0\u202f\u205f\u3000]")

# Typography.
EM_DASH_RE = re.compile(r"\s*—\s*")
EN_DASH_RE = re.compile(r"\s*–\s*")
CURLY_OPEN_RE = re.compile(r"\u201c")
CURLY_CLOSE_RE = re.compile(r"\u201d")
CURLY_SINGLE_OPEN_RE = re.compile(r"\u2018")
CURLY_SINGLE_CLOSE_RE = re.compile(r"\u2019")
ELLIPSIS_RE = re.compile(r"\u2026")
BULLET_RE = re.compile(r"\u2022")


def strip_invisible(text: str) -> str:
    return INVISIBLE_RE.sub("", text)


def fix_typography(text: str) -> str:
    text = EM_DASH_RE.sub(", ", text)
    text = EN_DASH_RE.sub("-", text)
    text = CURLY_OPEN_RE.sub('"', text)
    text = CURLY_CLOSE_RE.sub('"', text)
    text = CURLY_SINGLE_OPEN_RE.sub("'", text)
    text = CURLY_SINGLE_CLOSE_RE.sub("'", text)
    text = ELLIPSIS_RE.sub("...", text)
    text = BULLET_RE.sub("-", text)
    # Collapse double spaces left by em-dash collapse.
    text = re.sub(r"  +", " ", text)
    return text


def fix_slop(text: str) -> list:
    hits = []
    for slop_word, plain in REPLACEMENTS.items():
        pattern = re.compile(re.escape(slop_word), re.IGNORECASE)
        def repl(m, plain=plain, slop_word=slop_word):
            hits.append(slop_word)
            original = m.group(0)
            if original.isupper():
                return plain.upper()
            if original[0].isupper():
                return plain.capitalize()
            return plain
        text = pattern.sub(repl, text)
    return text, hits


def humanize(text: str, report: bool = False):
    before = text
    text = strip_invisible(text)
    text = NBSP_RE.sub(" ", text)
    text = fix_typography(text)
    text, hits = fix_slop(text)
    if report:
        return text, {
            "slop_hits": hits,
            "slop_count": len(hits),
            "chars_before": len(before),
            "chars_after": len(text),
        }
    return text


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    path = Path(sys.argv[1])
    report = "--report" in sys.argv
    out = None
    if "-o" in sys.argv:
        i = sys.argv.index("-o")
        out = Path(sys.argv[i + 1])

    text = path.read_text(encoding="utf-8")
    result = humanize(text, report=report)

    if report:
        clean, info = result
        if out:
            out.write_text(clean, encoding="utf-8")
        print(f"Slop hits: {info['slop_count']} -> {info['slop_hits'][:10]}")
        print(f"Chars: {info['chars_before']} -> {info['chars_after']}")
        if out:
            print(f"Wrote {out}")
        else:
            print(clean)
    else:
        clean = result
        if out:
            out.write_text(clean, encoding="utf-8")
            print(f"Wrote {out}")
        else:
            print(clean)


if __name__ == "__main__":
    main()
