from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("part", choices=["patch", "minor", "major"])
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    if not args.allow_dirty:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--", str(root)],
            check=False,
            text=True,
            capture_output=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            print("Working tree has changes under find-that-text. Commit or pass --allow-dirty.")
            return 1

    version_file = root / "VERSION"
    major, minor, patch = [int(part) for part in version_file.read_text(encoding="utf-8").strip().split(".")]
    if args.part == "patch":
        patch += 1
    elif args.part == "minor":
        minor += 1
        patch = 0
    else:
        major += 1
        minor = 0
        patch = 0
    new_version = f"{major}.{minor}.{patch}"
    version_file.write_text(f"{new_version}\n", encoding="utf-8")
    print(f"Updated VERSION to {new_version}")
    print(f"Create release tag with: git tag v{new_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
