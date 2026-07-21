import re
import sys
from pathlib import Path


APP_INFO_PATH = Path(__file__).resolve().parents[1] / "config" / "app_info.py"
VERSION_PATTERN = re.compile(r'^(APP_VERSION\s*=\s*")(\d+)\.(\d+)\.(\d+)(")\s*$')


def _parse_version_line(lines):
    for idx, line in enumerate(lines):
        match = VERSION_PATTERN.match(line.strip())
        if match:
            major = int(match.group(2))
            minor = int(match.group(3))
            patch = int(match.group(4))
            return idx, major, minor, patch
    return None


def _bump_version(major, minor, patch, part):
    if part == "patch":
        return major, minor, patch + 1
    if part == "minor":
        return major, minor + 1, 0
    if part == "major":
        return major + 1, 0, 0
    raise ValueError(f"Unknown bump part: {part}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python tools/bump_version.py patch|minor|major")
        return 1

    part = sys.argv[1].strip().lower()
    if part not in {"patch", "minor", "major"}:
        print("Error: part must be one of patch|minor|major")
        return 1

    if not APP_INFO_PATH.exists():
        print(f"Error: app info file not found: {APP_INFO_PATH}")
        return 1

    lines = APP_INFO_PATH.read_text(encoding="utf-8").splitlines()
    parsed = _parse_version_line(lines)
    if not parsed:
        print("Error: APP_VERSION not found or not in X.Y.Z format")
        return 1

    idx, major, minor, patch = parsed
    new_major, new_minor, new_patch = _bump_version(major, minor, patch, part)
    new_version = f'{new_major}.{new_minor}.{new_patch}'
    lines[idx] = f'APP_VERSION = "{new_version}"'
    APP_INFO_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Updated APP_VERSION: {major}.{minor}.{patch} -> {new_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
