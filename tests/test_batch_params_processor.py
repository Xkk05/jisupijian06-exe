# -*- coding: utf-8 -*-
"""BatchParamsProcessor 回归测试"""

from io import StringIO
from pathlib import Path


def test_process_video_sets_current_video_info_before_building_command(monkeypatch):
    """正式处理应使用真实视频尺寸构建去水印区域。"""
    from processor.batch_params_processor import BatchParamsProcessor

    config = {
        "remove_watermark": {
            "enabled": True,
            "method": "ffmpeg",
            "regions": [
                (8, 16, 232, 165),
                (490, 1104, 218, 162),
            ],
        }
    }
    processor = BatchParamsProcessor(config)
    observed = {}

    def fake_get_video_info(_path):
        return {"width": 720, "height": 1280, "duration": 9.9}

    def fake_build_command(_input_file, output_file, _variant, preview=False):
        observed["video_info"] = processor.config.get("_current_video_info")
        observed["filter"] = processor._build_delogo_filter()
        return ["ffmpeg", "-y", "-i", "input.mp4", output_file]

    class FakeProcess:
        def __init__(self):
            self.stderr = StringIO("")
            self.stdout = StringIO("")

        def poll(self):
            return 0

        def wait(self, timeout=None):
            return 0

    monkeypatch.setattr(processor, "get_video_info", fake_get_video_info)
    monkeypatch.setattr(processor, "build_command", fake_build_command)
    monkeypatch.setattr(
        "processor.batch_params_processor.subprocess.Popen",
        lambda *args, **kwargs: FakeProcess(),
    )

    assert processor.process_video("input.mp4", "output.mp4") is True
    assert observed["video_info"] == {"width": 720, "height": 1280, "duration": 9.9}
    assert "delogo=x=490:y=1104:w=218:h=162" in observed["filter"]


def test_head_tail_concat_file_uses_stable_windows_file_uri(tmp_path):
    """片头片尾拼接应写出可被 FFmpeg 在 Windows 上稳定解析的 concat 列表。"""
    from processor.batch_params_processor import BatchParamsProcessor

    head_file = tmp_path / "head clip.mp4"
    tail_file = tmp_path / "tail clip.mp4"
    head_file.write_bytes(b"head")
    tail_file.write_bytes(b"tail")

    config = {
        "add_head_tail": {
            "head_enabled": True,
            "head_file": str(head_file),
            "head_mode": "file",
            "tail_enabled": True,
            "tail_file": str(tail_file),
            "tail_mode": "file",
        }
    }
    processor = BatchParamsProcessor(config)

    cmd = processor._build_head_tail_concat_command(
        str(tmp_path / "input.mp4"), str(tmp_path / "output.mp4"), variant=0
    )

    assert cmd is not None
    concat_file = processor._temp_files[-1]
    content = Path(concat_file).read_text(encoding="utf-8")

    assert content.startswith("ffconcat version 1.0")
    assert "file 'file:" in content
    assert "head clip.mp4" in content
    assert "tail clip.mp4" in content
