import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wait_for_process(pid: int, timeout: int = 90) -> None:
    if pid <= 0:
        return

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            return
        time.sleep(1)


def download_file(url: str, target: Path) -> None:
    with urllib.request.urlopen(url, timeout=60) as response:
        with target.open("wb") as fh:
            shutil.copyfileobj(response, fh)


def validate_zip_member(member: zipfile.ZipInfo, target_dir: Path) -> Path:
    destination = (target_dir / member.filename).resolve()
    target_root = target_dir.resolve()
    if destination != target_root and target_root not in destination.parents:
        raise RuntimeError(f"Unsafe update entry: {member.filename}")
    return destination


def extract_update(zip_path: Path, target_dir: Path) -> None:
    with zipfile.ZipFile(zip_path, "r") as archive:
        for member in archive.infolist():
            destination = validate_zip_member(member, target_dir)
            if member.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue

            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member, "r") as src, destination.open("wb") as dst:
                shutil.copyfileobj(src, dst)


def restart_app(app_dir: Path, exe_name: str) -> None:
    exe_path = app_dir / exe_name
    if exe_path.exists() and exe_path.suffix.lower() == ".exe":
        subprocess.Popen(
            [str(exe_path)],
            cwd=str(app_dir),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="极速批剪 updater")
    parser.add_argument("--url", required=True, help="Update package URL")
    parser.add_argument("--dir", required=True, help="Application directory")
    parser.add_argument("--exe", required=True, help="Main executable name")
    parser.add_argument("--pid", type=int, default=0, help="Main process id")
    parser.add_argument("--hash", default="", help="Expected package SHA256")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app_dir = Path(args.dir).resolve()
    app_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="jisupijian_update_") as tmp:
        package = Path(tmp) / "update.zip"
        download_file(args.url, package)

        if args.hash:
            actual_hash = sha256_file(package)
            if actual_hash.lower() != args.hash.lower():
                raise RuntimeError("Update package hash mismatch")

        wait_for_process(args.pid)
        extract_update(package, app_dir)

    restart_app(app_dir, args.exe)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        log_path = Path(tempfile.gettempdir()) / "jisupijian_updater_error.log"
        log_path.write_text(str(exc), encoding="utf-8")
        raise SystemExit(1)
