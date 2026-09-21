from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-missing-tag", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    if not SEMVER.match(version):
        print(f"VERSION is not semantic version MAJOR.MINOR.PATCH: {version}", file=sys.stderr)
        return 1

    ref_name = os.environ.get("GITHUB_REF_NAME")
    if ref_name and ref_name.startswith("v") and ref_name[1:] != version:
        print(f"Git tag {ref_name} does not match VERSION {version}", file=sys.stderr)
        return 1
    if ref_name is None and not args.allow_missing_tag:
        return 0

    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    if "dynamic = [\"version\"]" not in pyproject:
        print("pyproject.toml must derive version dynamically from VERSION.", file=sys.stderr)
        return 1

    print(f"Release check passed for {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
