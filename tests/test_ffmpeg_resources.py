import os
import subprocess
from pathlib import Path

import pytest


def test_ascii_resource_path_is_returned_without_copy(tmp_path, monkeypatch):
    from utils import ffmpeg_resources

    source = tmp_path / "vintage.cube"
    source.write_bytes(b"LUT_3D_SIZE 2\n")
    cache_root = tmp_path / "cache"
    monkeypatch.setattr(
        ffmpeg_resources, "_candidate_cache_roots", lambda: (cache_root,)
    )

    result = ffmpeg_resources.materialize_ascii_resource(source, "luts")

    assert result == str(source.resolve())
    assert not cache_root.exists()


def test_unicode_resource_is_copied_to_verified_ascii_cache(tmp_path, monkeypatch):
    from utils import ffmpeg_resources

    source_dir = tmp_path / "资源"
    source_dir.mkdir()
    source = source_dir / "vintage.cube"
    source.write_bytes(b"valid cube content")
    cache_root = tmp_path / "ascii-cache"
    monkeypatch.setattr(
        ffmpeg_resources, "_candidate_cache_roots", lambda: (cache_root,)
    )

    result = Path(ffmpeg_resources.materialize_ascii_resource(source, "luts"))

    assert str(result).isascii()
    assert result.is_file()
    assert result.read_bytes() == source.read_bytes()
    assert result.parent.name == "luts"


def test_damaged_cached_resource_is_repaired(tmp_path, monkeypatch):
    from utils import ffmpeg_resources

    source_dir = tmp_path / "资源"
    source_dir.mkdir()
    source = source_dir / "vintage.cube"
    source.write_bytes(b"authoritative cube content")
    cache_root = tmp_path / "ascii-cache"
    monkeypatch.setattr(
        ffmpeg_resources, "_candidate_cache_roots", lambda: (cache_root,)
    )

    first = Path(ffmpeg_resources.materialize_ascii_resource(source, "luts"))
    first.write_bytes(b"damaged")
    second = Path(ffmpeg_resources.materialize_ascii_resource(source, "luts"))

    assert second == first
    assert second.read_bytes() == source.read_bytes()


def test_unusable_cache_root_falls_back_to_next_candidate(tmp_path, monkeypatch):
    from utils import ffmpeg_resources

    source_dir = tmp_path / "资源"
    source_dir.mkdir()
    source = source_dir / "vintage.cube"
    source.write_bytes(b"valid cube content")
    blocked_root = tmp_path / "blocked"
    blocked_root.write_text("not a directory", encoding="ascii")
    fallback_root = tmp_path / "fallback-cache"
    monkeypatch.setattr(
        ffmpeg_resources,
        "_candidate_cache_roots",
        lambda: (blocked_root / "nested", fallback_root),
    )

    result = Path(ffmpeg_resources.materialize_ascii_resource(source, "luts"))

    assert result.is_file()
    assert result.is_relative_to(fallback_root)
    assert result.read_bytes() == source.read_bytes()


@pytest.mark.skipif(os.name != "nt", reason="The regression is Windows-specific")
def test_bundled_ffmpeg_reads_materialized_unicode_lut(tmp_path, monkeypatch):
    from utils import ffmpeg_resources

    project_root = Path(__file__).resolve().parents[1]
    ffmpeg = project_root / "ffmpeg" / "ffmpeg.exe"
    source_lut = project_root / "assets" / "luts" / "vintage.cube"
    if not ffmpeg.is_file():
        pytest.skip("Bundled FFmpeg is not available")

    unicode_dir = tmp_path / "路径_😀"
    unicode_dir.mkdir()
    unicode_lut = unicode_dir / "vintage.cube"
    unicode_lut.write_bytes(source_lut.read_bytes())
    cache_root = tmp_path / "ascii-cache"
    monkeypatch.setattr(
        ffmpeg_resources, "_candidate_cache_roots", lambda: (cache_root,)
    )

    def run_lut(path):
        escaped = str(path).replace("\\", "/").replace(":", "\\:")
        return subprocess.run(
            [
                str(ffmpeg),
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "color=c=red:s=64x64:d=0.1",
                "-vf",
                f"lut3d='{escaped}'",
                "-frames:v",
                "1",
                "-f",
                "null",
                "NUL",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )

    cached_lut = ffmpeg_resources.materialize_ascii_resource(unicode_lut, "luts")
    cached_result = run_lut(cached_lut)

    assert cached_lut.isascii()
    assert cached_result.returncode == 0, cached_result.stderr
