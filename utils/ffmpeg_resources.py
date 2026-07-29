"""Compatibility paths for resources opened by FFmpeg filters."""

from __future__ import annotations

import ctypes
import hashlib
import os
import tempfile
import threading
from pathlib import Path
from typing import Iterable, Optional


class FFmpegResourceError(RuntimeError):
    """Raised when no FFmpeg-compatible path can be prepared."""


_CACHE_LOCK = threading.RLock()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _get_short_path(path: Path) -> Optional[str]:
    if os.name != "nt":
        return None

    try:
        get_short_path = ctypes.windll.kernel32.GetShortPathNameW
        get_short_path.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
        get_short_path.restype = ctypes.c_uint
        required = get_short_path(str(path), None, 0)
        if not required:
            return None
        buffer = ctypes.create_unicode_buffer(required + 1)
        written = get_short_path(str(path), buffer, len(buffer))
        if not written:
            return None
        return buffer.value
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def _ascii_alias(path: Path) -> Optional[str]:
    absolute = str(path.resolve())
    if absolute.isascii():
        return absolute

    short_path = _get_short_path(path)
    if short_path and short_path.isascii():
        return short_path
    return None


def _candidate_cache_roots() -> Iterable[Path]:
    yield Path(tempfile.gettempdir()) / "kq-video" / "ffmpeg-resources"

    program_data = os.environ.get("PROGRAMDATA")
    if program_data:
        yield Path(program_data) / "KQVideo" / "ffmpeg-resources"


def _safe_cache_name(source: Path, digest: str) -> str:
    stem = "".join(
        char if char.isascii() and (char.isalnum() or char in "-_") else "_"
        for char in source.stem
    ).strip("_")
    if not stem:
        stem = "resource"
    suffix = source.suffix.lower() if source.suffix.isascii() else ".bin"
    return f"{stem}-{digest[:16]}{suffix}"


def _copy_verified(source: Path, destination: Path, expected_hash: str) -> None:
    if destination.is_file() and _file_sha256(destination) == expected_hash:
        return

    temp_name = f".{destination.name}.{os.getpid()}.{threading.get_ident()}.tmp"
    temp_path = destination.with_name(temp_name)
    try:
        with source.open("rb") as source_handle, temp_path.open("wb") as temp_handle:
            for chunk in iter(lambda: source_handle.read(1024 * 1024), b""):
                temp_handle.write(chunk)
            temp_handle.flush()
            os.fsync(temp_handle.fileno())

        if _file_sha256(temp_path) != expected_hash:
            raise FFmpegResourceError(f"FFmpeg资源缓存校验失败: {source}")
        os.replace(temp_path, destination)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def materialize_ascii_resource(source_path, namespace: str = "resources") -> str:
    """Return a path that legacy Windows FFmpeg filters can open reliably."""
    source = Path(source_path).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"FFmpeg资源文件不存在: {source}")

    source_text = str(source)
    if os.name != "nt" or source_text.isascii():
        return source_text

    if not namespace or not namespace.isascii() or Path(namespace).name != namespace:
        raise ValueError(f"无效的FFmpeg资源缓存命名空间: {namespace!r}")

    source_hash = _file_sha256(source)
    cache_name = _safe_cache_name(source, source_hash)
    failures = []

    with _CACHE_LOCK:
        for cache_root in _candidate_cache_roots():
            cache_dir = Path(cache_root) / namespace
            try:
                cache_dir.mkdir(parents=True, exist_ok=True)
                cache_dir_alias = _ascii_alias(cache_dir)
                if not cache_dir_alias:
                    failures.append(f"缓存路径不是纯英文路径: {cache_dir}")
                    continue

                destination = cache_dir / cache_name
                _copy_verified(source, destination, source_hash)
                ffmpeg_path = str(Path(cache_dir_alias) / cache_name)
                if not ffmpeg_path.isascii():
                    failures.append(f"缓存文件路径不是纯英文路径: {ffmpeg_path}")
                    continue
                return ffmpeg_path
            except (OSError, FFmpegResourceError) as exc:
                failures.append(f"{cache_dir}: {exc}")

    detail = "; ".join(failures) or "没有可用的缓存目录"
    raise FFmpegResourceError(f"无法为FFmpeg准备兼容路径: {source}。{detail}")
