#!/usr/bin/env python
"""
dev-to self-improvement learn() script.

Reads ~/.claude/devto/log.md, computes per-post metrics, and updates:
  - dev-post/title-formulas.json  (promote/demote formula weights)
  - dev-post/tag-suggestions.json  (promote/demote tag weights)
  - dev-human/slop.json            (add recurring slop words)
  - dev-profile/rubric.json        (re-weight rubric items)

Usage:
    python3 dev-learn.py audit   # after dev-audit has been run
    python3 dev-learn.py status  # show current weights

Safety:
  - Requires >= min_sample (10) audited posts before any promote/demote.
  - Proposes changes; does not write unless --apply is passed.
  - Never deletes formulas/tags/items; demotes weight to 0 and archives.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ponytail: env override so the published copy works when installed to another host's skills dir
SKILLS = Path(os.environ.get("DEVTO_SKILLS_DIR", "~/.config/opencode/skills")).expanduser()
DEVTO = Path.home() / ".claude" / "devto"
LOG = DEVTO / "log.md"
MIN_SAMPLE = 10


def fail(msg: str):
    print(f"ERROR: {msg}")
    sys.exit(1)


def read_log() -> list:
    if not LOG.exists():
        fail(f"Log not found: {LOG}. Run dev-post first to create it.")
    text = LOG.read_text(encoding="utf-8")
    lines = [l for l in text.splitlines() if l.startswith("|") and "------" not in l]
    if len(lines) < 2:
        return []
    header = lines[0]
    cols = [c.strip() for c in header.strip("|").split("|")]
    rows = []
    for line in lines[1:]:
        vals = [v.strip() for v in line.strip("|").split("|")]
        rows.append(dict(zip(cols, vals)))
    return rows


def to_pct(val: str) -> float:
    """Convert '8.1%' or '8.1' to float 8.1."""
    if not val or val in ("-", "", "N/A"):
        return 0.0
    return float(val.replace("%", "").strip())


def load_json(path: Path):
    if not path.exists():
        fail(f"Missing config: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict, apply: bool):
    if apply:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"  updated {path}")
    else:
        print(f"  (dry-run) would update {path}")


def learn_formulas(rows: list, apply: bool):
    path = SKILLS / "dev-post" / "title-formulas.json"
    data = load_json(path)
    n = len(rows)
    if n < data.get("min_sample", MIN_SAMPLE):
        print(f"formulas: only {n} audited posts (need {data.get('min_sample', MIN_SAMPLE)}). Skipping weight updates.")
        return

    # Compute mean engagement rate
    rates = [to_pct(r.get("engagement_rate", "0")) for r in rows if r.get("engagement_rate")]
    if not rates:
        print("formulas: no engagement_rate data in log. Skipping.")
        return
    mean_rate = sum(rates) / len(rates)

    promoted = demoted = 0
    for f in data["formulas"]:
        f_posts = [r for r in rows if r.get("formula_id") == f["id"] and r.get("engagement_rate")]
        if not f_posts:
            continue
        f_rate = sum(to_pct(r.get("engagement_rate", "0")) for r in f_posts) / len(f_posts)
        f["uses"] = f.get("uses", 0) + len(f_posts)
        if f_rate >= mean_rate:
            f["wins"] = f.get("wins", 0) + 1
            f["weight"] = round(min(2.0, f.get("weight", 1.0) + 0.1), 2)
            promoted += 1
        elif f_rate <= mean_rate * 0.5:
            f["weight"] = round(max(0.0, f.get("weight", 1.0) - 0.1), 2)
            demoted += 1
        f["learned_at"] = datetime.utcnow().isoformat() + "Z"

    # Archive demoted-to-zero formulas
    to_archive = [f for f in data["formulas"] if f.get("weight", 1.0) <= 0.0]
    for f in to_archive:
        data["formulas"].remove(f)
        data.setdefault("archive", []).append(f)

    data["learned_at"] = datetime.utcnow().isoformat() + "Z"
    save_json(path, data, apply)
    print(f"formulas: promoted={promoted} demoted={demoted} archived={len(to_archive)} (n={n}, mean_rate={mean_rate:.2f}%)")


def learn_tags(rows: list, apply: bool):
    path = SKILLS / "dev-post" / "tag-suggestions.json"
    data = load_json(path)
    n = len(rows)
    if n < data.get("min_sample", MIN_SAMPLE):
        print(f"tags: only {n} audited posts (need {data.get('min_sample', MIN_SAMPLE)}). Skipping weight updates.")
        return

    rates = [to_pct(r.get("engagement_rate", "0")) for r in rows if r.get("engagement_rate")]
    if not rates:
        print("tags: no engagement_rate data. Skipping.")
        return
    mean_rate = sum(rates) / len(rates)

    def update_tag_list(tag_list, key):
        nonlocal promoted, demoted
        for entry in tag_list:
            tag = entry["tag"]
            tag_posts = [r for r in rows if r.get("tags") and tag in r.get("tags", "") and r.get("engagement_rate")]
            if not tag_posts:
                continue
            tag_rate = sum(to_pct(r.get("engagement_rate", "0")) for r in tag_posts) / len(tag_posts)
            entry["uses"] = entry.get("uses", 0) + len(tag_posts)
            if tag_rate >= mean_rate:
                entry["wins"] = entry.get("wins", 0) + 1
                entry["weight"] = round(min(2.0, entry.get("weight", 1.0) + 0.1), 2)
                promoted += 1
            elif tag_rate <= mean_rate * 0.5:
                entry["weight"] = round(max(0.0, entry.get("weight", 1.0) - 0.1), 2)
                demoted += 1
            entry["learned_at"] = datetime.utcnow().isoformat() + "Z"

    promoted = demoted = 0
    update_tag_list(data["broad"], "broad")
    update_tag_list(data["niche"], "niche")

    to_archive = []
    for key in ("broad", "niche"):
        zero = [e for e in data[key] if e.get("weight", 1.0) <= 0.0]
        for e in zero:
            data[key].remove(e)
            to_archive.append(e)
    data.setdefault("archive", []).extend(to_archive)
    data["learned_at"] = datetime.utcnow().isoformat() + "Z"
    save_json(path, data, apply)
    print(f"tags: promoted={promoted} demoted={demoted} archived={len(to_archive)} (n={n}, mean_rate={mean_rate:.2f}%)")


def learn_slop(apply: bool):
    """dev-human: slop.json learns from repeated humanize runs.
    This is a stub that records the intent; actual slop expansion happens
    when the user runs humanize.py and reports recurring words."""
    path = SKILLS / "dev-human" / "slop.json"
    data = load_json(path)
    print(f"slop: {len(data.get('replacements', {}))} replacements tracked. "
          f"Run humanize.py on drafts to surface recurring slop words for manual addition.")
    # No automatic changes to slop.json without user review — slop words are
    # voice-specific and should not be auto-added.


def learn_rubric(rows: list, apply: bool):
    path = SKILLS / "dev-profile" / "rubric.json"
    data = load_json(path)
    n = len(rows)
    if n < data.get("min_sample", MIN_SAMPLE):
        print(f"rubric: only {n} audited profiles (need {data.get('min_sample', MIN_SAMPLE)}). Skipping weight updates.")
        return
    print(f"rubric: {n} profiles audited. Weight rebalancing requires follower-growth correlation data not yet captured in log.md.")
    print("rubric: manual review recommended — adjust item points based on which fixes users actually apply.")


def status(apply: bool):
    print("=== dev-to self-improvement status ===")
    rows = read_log()
    print(f"Audited posts in log: {len(rows)}")
    if rows:
        rates = [to_pct(r.get("engagement_rate", "0")) for r in rows if r.get("engagement_rate")]
        if rates:
            print(f"Mean engagement rate: {sum(rates)/len(rates):.2f}% (n={len(rates)})")
    print()
    learn_formulas(rows, apply)
    print()
    learn_tags(rows, apply)
    print()
    learn_slop(apply)
    print()
    learn_rubric(rows, apply)


def main():
    apply = "--apply" in sys.argv
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "status":
        status(apply)
    elif cmd == "audit":
        status(apply)
    else:
        fail(f"Unknown command: {cmd}. Use 'status' or 'audit'.")

    if not apply:
        print("\nDry-run complete. Re-run with --apply to write changes.")


if __name__ == "__main__":
    main()
