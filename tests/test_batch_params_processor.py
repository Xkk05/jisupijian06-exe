# -*- coding: utf-8 -*-
"""BatchParamsProcessor 回归测试"""

from io import StringIO


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
