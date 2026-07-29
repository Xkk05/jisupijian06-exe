# -*- coding: utf-8 -*-
"""BatchParamsProcessor 回归测试"""

from io import StringIO
from pathlib import Path

import pytest


def test_lut_filter_uses_ffmpeg_compatible_path(monkeypatch, tmp_path):
    from processor.batch_params_processor import BatchParamsProcessor
    from utils import lut_filters

    cached_lut = tmp_path / "vintage.cube"
    cached_lut.write_text("LUT_3D_SIZE 2\n", encoding="ascii")
    monkeypatch.setattr(
        lut_filters,
        "resolve_ffmpeg_lut_path",
        lambda _filter_id: str(cached_lut),
    )
    processor = BatchParamsProcessor(
        {"lut_filter": {"apply": True, "filters": ["vintage"]}}
    )

    filter_chain = processor._build_lut_filter()

    expected_path = str(cached_lut).replace("\\", "/").replace(":", "\\:")
    assert filter_chain == f"lut3d='{expected_path}'"


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


def test_speed_uses_same_value_for_video_and_audio_on_portrait(monkeypatch):
    """竖屏视频启用变速时，视频 setpts 和音频 atempo 必须共用同一倍率。"""
    from processor import batch_params_processor as module
    from processor.batch_params_processor import BatchParamsProcessor

    config = {
        "speed": {
            "enabled": True,
            "min": 1.0,
            "max": 1.05,
            "segment_enabled": False,
            "pitch_enabled": False,
        }
    }
    processor = BatchParamsProcessor(config)

    monkeypatch.setattr(module, "validate_video_for_processing", lambda _info: None)
    monkeypatch.setattr(
        processor,
        "get_video_info",
        lambda _path: {
            "width": 360,
            "height": 640,
            "duration": 3.0,
            "has_audio": True,
        },
    )

    cmd = processor.build_command("portrait.mp4", "output.mp4", variant=1)
    speed = processor._current_speed_value

    vf_index = cmd.index("-vf") + 1
    af_index = cmd.index("-af") + 1

    assert speed > 1.0
    assert f"setpts={1.0 / speed:.4f}*PTS" in cmd[vf_index]
    assert f"atempo={speed:.4f}" in cmd[af_index]


@pytest.mark.parametrize(
    "direction",
    [
        "auto",
        "vertical",
        "horizontal",
        "up",
        "down",
        "left",
        "right",
        "auto_close",
        "horizontal_close",
        "vertical_close",
    ],
)
def test_curtain_directions_use_stable_pixel_mask(direction):
    """所有开幕/收幕方向都应保持原尺寸，避免动态 crop 产生零宽高。"""
    from processor.batch_params_processor import BatchParamsProcessor

    processor = BatchParamsProcessor(
        {
            "more_effects": {
                "curtain_enabled": True,
                "curtain_direction": direction,
                "curtain_duration": 2.0,
                "curtain_color": "#123456",
            }
        }
    )

    filter_chain = processor._build_more_effects_filter(
        {"width": 720, "height": 1280, "duration": 8.0}
    )

    assert "format=rgb24,geq=" in filter_chain
    assert "format=yuv420p" in filter_chain
    assert "crop=" not in filter_chain
    assert ",18)'" in filter_chain
    assert ",52)'" in filter_chain
    assert ",86)'" in filter_chain


def test_formal_command_contains_curtain_animation(monkeypatch):
    """正式批处理与预览必须复用同一条开幕动画滤镜链。"""
    from processor import batch_params_processor as module
    from processor.batch_params_processor import BatchParamsProcessor

    processor = BatchParamsProcessor(
        {
            "more_effects": {
                "curtain_enabled": True,
                "curtain_direction": "horizontal_close",
                "curtain_duration": 2.0,
                "curtain_color": "#000000",
            }
        }
    )
    monkeypatch.setattr(module, "validate_video_for_processing", lambda _info: None)
    monkeypatch.setattr(
        processor,
        "get_video_info",
        lambda _path: {
            "width": 720,
            "height": 1280,
            "duration": 8.0,
            "has_audio": False,
        },
    )

    cmd = processor.build_command("input.mp4", "output.mp4")
    video_filter = cmd[cmd.index("-vf") + 1]

    assert "geq=" in video_filter
    assert "1-min(1,max(0,T/2.000))" in video_filter
    assert "crop=" not in video_filter


def test_fade_out_uses_fixed_start_time_supported_by_bundled_ffmpeg():
    """正式渐出不能使用旧版 FFmpeg 无法解析的 duration 表达式。"""
    from processor.batch_params_processor import BatchParamsProcessor

    processor = BatchParamsProcessor(
        {
            "more_effects": {
                "fade_out_enabled": True,
                "fade_out_duration": 0.3,
            }
        }
    )

    filter_chain = processor._build_more_effects_filter({"duration": 3.0})

    assert filter_chain == "fade=out:st=2.700:d=0.300"
    assert "duration" not in filter_chain


def test_fade_out_uses_trimmed_preview_timeline():
    """预览和正式处理应按裁剪后的实际滤镜时间轴计算渐出位置。"""
    from processor.batch_params_processor import BatchParamsProcessor

    processor = BatchParamsProcessor(
        {
            "trim": {
                "enabled": True,
                "mode": "trim_edges",
                "head": 0.5,
                "tail": 0.5,
            },
            "more_effects": {
                "fade_out_enabled": True,
                "fade_out_duration": 0.5,
            },
        }
    )
    processor.preview_mode = True
    processor.preview_duration = 10.0

    filter_chain = processor._build_more_effects_filter({"duration": 3.0})

    assert filter_chain == "fade=out:st=1.500:d=0.500"


def test_fade_out_duration_is_clamped_to_short_video():
    from processor.batch_params_processor import BatchParamsProcessor

    processor = BatchParamsProcessor(
        {
            "more_effects": {
                "fade_out_enabled": True,
                "fade_out_duration": 1.5,
            }
        }
    )

    filter_chain = processor._build_more_effects_filter({"duration": 0.4})

    assert filter_chain == "fade=out:st=0.000:d=0.400"


@pytest.mark.parametrize(
    ("audio_speed", "has_audio", "expected_audio_filter"),
    [
        (
            True,
            True,
            "aresample=44100,asetrate=44100*5.0000,aresample=44100",
        ),
        (False, True, None),
        (True, False, None),
    ],
)
def test_frame_extract_audio_speed_uses_selected_interval(
    monkeypatch, audio_speed, has_audio, expected_audio_filter
):
    """声音变速必须与本次抽帧间隔一致，并忽略无音轨输入。"""
    from processor import batch_params_processor as module
    from processor.batch_params_processor import BatchParamsProcessor

    processor = BatchParamsProcessor(
        {
            "frame_extract": {
                "enabled": True,
                "min": 5,
                "max": 5,
                "audio_speed": audio_speed,
            }
        }
    )
    monkeypatch.setattr(module, "validate_video_for_processing", lambda _info: None)
    monkeypatch.setattr(
        processor,
        "get_video_info",
        lambda _path: {
            "width": 320,
            "height": 240,
            "duration": 3.0,
            "fps": 25.0,
            "has_audio": has_audio,
        },
    )

    cmd = processor.build_command("input.mp4", "output.mp4")

    assert "select='not(mod(n,5))',setpts=N/FRAME_RATE/TB" in cmd
    if expected_audio_filter:
        assert cmd[cmd.index("-af") + 1] == expected_audio_filter
    else:
        assert "-af" not in cmd


def test_frame_extract_audio_speed_joins_video_filter_complex(monkeypatch):
    """画中画等复杂视频滤镜启用时，声音变速应进入同一 filter_complex。"""
    from processor import batch_params_processor as module
    from processor.batch_params_processor import BatchParamsProcessor

    processor = BatchParamsProcessor(
        {
            "frame_extract": {
                "enabled": True,
                "min": 5,
                "max": 5,
                "audio_speed": True,
            },
            "pip": {
                "enabled": True,
                "mode": "video",
                "video_margin_top": 10,
                "video_margin_left": 10,
            },
        }
    )
    monkeypatch.setattr(module, "validate_video_for_processing", lambda _info: None)
    monkeypatch.setattr(
        processor,
        "get_video_info",
        lambda _path: {
            "width": 320,
            "height": 240,
            "duration": 3.0,
            "fps": 25.0,
            "has_audio": True,
        },
    )

    cmd = processor.build_command("input.mp4", "output.mp4")
    filter_graph = cmd[cmd.index("-filter_complex") + 1]

    assert (
        "[0:a]aresample=44100,asetrate=44100*5.0000,"
        "aresample=44100[aextract]"
    ) in filter_graph
    assert "[aextract]" in cmd
    assert "-af" not in cmd


def test_frame_extract_audio_speed_runs_after_bgm_mix(monkeypatch, tmp_path):
    """背景音乐混音后再统一变速，避免简单滤镜与复杂滤镜互斥。"""
    from processor import batch_params_processor as module
    from processor.batch_params_processor import BatchParamsProcessor

    bgm_file = tmp_path / "bgm.m4a"
    bgm_file.write_bytes(b"audio")
    processor = BatchParamsProcessor(
        {
            "frame_extract": {
                "enabled": True,
                "min": 5,
                "max": 5,
                "audio_speed": True,
            },
            "audio": {
                "bgm_enabled": True,
                "bgm_path": str(bgm_file),
                "bgm_volume": 0.2,
            },
        }
    )
    monkeypatch.setattr(module, "validate_video_for_processing", lambda _info: None)
    monkeypatch.setattr(
        processor,
        "get_video_info",
        lambda _path: {
            "width": 320,
            "height": 240,
            "duration": 3.0,
            "fps": 25.0,
            "has_audio": True,
        },
    )

    cmd = processor.build_command("input.mp4", "output.mp4")
    filter_graph = cmd[cmd.index("-filter_complex") + 1]

    assert "[a0][a1]amix=" in filter_graph
    assert (
        "[0:a]aresample=44100,asetrate=44100*5.0000,aresample=44100[a0]"
    ) in filter_graph
    assert (
        "[1:a]volume=0.2,aresample=44100,asetrate=44100*5.0000,"
        "aresample=44100[a1]"
    ) in filter_graph
    assert "[aout]" in cmd
    assert "-af" not in cmd


def test_preview_mode_is_restored_when_command_build_fails(monkeypatch, tmp_path):
    from processor.batch_params_processor import BatchParamsProcessor

    processor = BatchParamsProcessor({})

    def fail_build(*_args, **_kwargs):
        raise RuntimeError("broken preview command")

    monkeypatch.setattr(processor, "build_command", fail_build)

    assert (
        processor.generate_preview(
            "input.mp4", str(tmp_path / "preview.mp4")
        )
        is False
    )
    assert processor.preview_mode is False
    assert processor.last_preview_error == "broken preview command"


def test_diagonal_text_motion_ignores_normal_direction_and_speed(monkeypatch):
    from processor.batch_params_processor import BatchParamsProcessor

    processor = BatchParamsProcessor({})
    monkeypatch.setattr(processor, "_resolve_font_path", lambda _font: None)
    common = {
        "font_enabled": False,
        "position": "top_left",
        "scroll_enabled": True,
        "diagonal": True,
    }

    first = processor._build_single_text_filter(
        "demo",
        {
            **common,
            "scroll_direction": "left",
            "scroll_speed": 20.0,
            "random_speed": True,
        },
        {"width": 720, "height": 1280},
        False,
    )
    second = processor._build_single_text_filter(
        "demo",
        {
            **common,
            "scroll_direction": "down",
            "scroll_speed": 0.1,
            "random_speed": False,
        },
        {"width": 720, "height": 1280},
        False,
    )

    assert first == second
    assert first.count("t*40.0") == 2
