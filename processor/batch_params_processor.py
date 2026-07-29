"""
极速批剪 - 批量参数处理器
负责将UI参数转换为FFmpeg命令并执行
"""

import os
import sys
import random
import math
import time
import subprocess
import tempfile
import copy
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from fractions import Fraction
from PIL import Image, ImageFont

from utils.unified_logger import logger
from utils.exceptions import VideoCodecException
from utils.video_codec_checker import (
    check_video_codec_compatibility,
    check_codec_from_stream_info,
    validate_video_for_processing,
)
from utils.enum_codes import (
    normalize_bg_style,
    normalize_border_style,
    normalize_crop_mode,
    normalize_crop_percent_position,
    normalize_curtain_direction,
    normalize_grid_direction,
    normalize_resolution_preset,
    normalize_scroll_direction,
    normalize_text_animation_type,
    normalize_text_arrange,
    normalize_text_filter_action,
    normalize_text_filter_position,
    normalize_text_position,
    normalize_text_source_mode,
    normalize_trim_mode,
    normalize_video_ref,
    normalize_watermark_preset,
)


class BatchParamsProcessor:
    """批量参数处理器 - 将UI参数应用到视频"""

    IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}

    def __init__(self, config: Dict):
        """
        初始化处理器

        Args:
            config: UI收集的配置字典
        """
        self.config = config
        self.ffmpeg_path = self._find_ffmpeg()
        self.ffprobe_path = self._find_ffprobe()
        self._font_cache: Dict[str, Optional[str]] = {}
        self._temp_files: List[str] = []
        self._current_input_file: Optional[str] = None  # 当前处理的输入文件
        self._current_video_index: int = 0  # 当前处理的视频索引（用于文件夹顺序选择）
        self.last_preview_error = ""
        self.last_process_error = ""

    def _find_ffmpeg(self) -> str:
        """查找FFmpeg可执行文件"""
        # 1. 检查app/ffmpeg目录
        app_dir = Path(__file__).parent.parent
        bundled_ffmpeg = app_dir / "ffmpeg" / "ffmpeg.exe"
        if bundled_ffmpeg.exists():
            return str(bundled_ffmpeg)

        # 2. 检查processor目录
        processor_ffmpeg = app_dir / "processor" / "ffmpeg.exe"
        if processor_ffmpeg.exists():
            return str(processor_ffmpeg)

        # 3. 使用系统PATH中的ffmpeg
        return "ffmpeg"

    def _get_global_options(self) -> Dict:
        return self.config.get("global_options", {})

    def _get_video_codec_settings(self) -> Tuple[str, Optional[str], str]:
        global_options = self._get_global_options()
        use_h265 = bool(global_options.get("use_h265"))
        gpu_accel = bool(global_options.get("gpu_accel"))
        nvidia_opt = bool(global_options.get("nvidia_optimize"))
        intel_opt = bool(global_options.get("intel_optimize"))

        if not gpu_accel:
            nvidia_opt = False
            intel_opt = False

        if nvidia_opt and intel_opt:
            logger.warning("同时启用N卡/I卡优化，已回退到软件编码")
            nvidia_opt = False
            intel_opt = False

        if nvidia_opt:
            codec = "hevc_nvenc" if use_h265 else "h264_nvenc"
            hwaccel = "cuda"
        elif intel_opt:
            codec = "hevc_qsv" if use_h265 else "h264_qsv"
            hwaccel = "qsv"
        else:
            codec = "libx265" if use_h265 else "libx264"
            hwaccel = None

        if codec in ("libx264", "libx265"):
            quality_param = "-crf"
        elif codec.endswith("_nvenc"):
            quality_param = "-cq"
        elif codec.endswith("_qsv"):
            quality_param = "-global_quality"
        else:
            quality_param = "-crf"

        return codec, hwaccel, quality_param

    def _append_video_codec(
        self, cmd: List[str], codec: str, preset: Optional[str] = None
    ) -> None:
        cmd.extend(["-c:v", codec])
        if preset:
            cmd.extend(["-preset", preset])

    def _append_quality_params(
        self,
        cmd: List[str],
        codec: str,
        quality_param: str,
        quality_value: int,
        preset: Optional[str] = None,
    ) -> None:
        self._append_video_codec(cmd, codec, preset)
        cmd.extend([quality_param, str(quality_value)])

    def _add_background_audio_input(self, cmd: List[str], variant: int = 0) -> tuple:
        """添加背景音乐输入，返回(文件路径, 是否启用)"""
        audio_config = self.config.get("audio", {})
        if not audio_config.get("bgm_enabled"):
            return None, False

        bgm_path = audio_config.get("bgm_path", "")
        if not bgm_path or not os.path.exists(bgm_path):
            return None, False

        # 选择背景音乐文件
        bgm_file = None
        if os.path.isfile(bgm_path):
            bgm_file = bgm_path
        elif os.path.isdir(bgm_path):
            # 目录模式
            import random

            audio_extensions = [".mp3", ".wav", ".aac", ".m4a", ".flac", ".ogg"]
            audio_files = []
            for file in os.listdir(bgm_path):
                if os.path.splitext(file)[1].lower() in audio_extensions:
                    audio_files.append(os.path.join(bgm_path, file))

            if not audio_files:
                return None, False

            audio_files = sorted(audio_files)

            # 随机或顺序选择
            if audio_config.get("enable_random"):
                rng = random.Random(variant)
                bgm_file = rng.choice(audio_files)
            else:
                bgm_file = audio_files[variant % len(audio_files)]

        if not bgm_file:
            return None, False

        # 如果启用循环，添加-stream_loop
        if audio_config.get("enable_loop"):
            cmd.extend(["-stream_loop", "-1"])

        # 添加输入
        cmd.extend(["-i", self._normalize_cmd_path(bgm_file)])
        return bgm_file, True

    def _find_ffprobe(self) -> str:
        """查找FFprobe可执行文件"""
        # 1. 检查app/ffmpeg目录
        app_dir = Path(__file__).parent.parent
        bundled_ffprobe = app_dir / "ffmpeg" / "ffprobe.exe"
        if bundled_ffprobe.exists():
            return str(bundled_ffprobe)

        # 2. 检查processor目录
        processor_ffprobe = app_dir / "processor" / "ffprobe.exe"
        if processor_ffprobe.exists():
            return str(processor_ffprobe)

        # 3. 使用系统PATH中的ffprobe
        return "ffprobe"

    def get_video_info(self, video_path: str) -> Optional[Dict]:
        """获取视频信息"""
        try:
            cmd = [
                self.ffprobe_path,
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                video_path,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            if result.returncode == 0:
                import json

                data = json.loads(result.stdout)

                # 提取视频流信息
                video_stream = next(
                    (
                        s
                        for s in data.get("streams", [])
                        if s.get("codec_type") == "video"
                    ),
                    None,
                )

                # 检测音频流
                has_audio = any(
                    s.get("codec_type") == "audio" for s in data.get("streams", [])
                )

                # 提取编码信息
                video_codec, audio_codec = check_codec_from_stream_info(data)

                if video_stream:
                    duration = float(data.get("format", {}).get("duration", 0) or 0)
                    if duration <= 0:
                        stream_duration = video_stream.get("duration")
                        if stream_duration:
                            try:
                                duration = float(stream_duration)
                            except (TypeError, ValueError):
                                duration = 0

                    r_frame_rate = video_stream.get("r_frame_rate", "30/1")
                    if "/" in r_frame_rate:
                        try:
                            fps_value = float(Fraction(r_frame_rate))
                        except (ValueError, ZeroDivisionError):
                            fps_value = 30.0
                    else:
                        try:
                            fps_value = float(r_frame_rate) if r_frame_rate else 30.0
                        except ValueError:
                            fps_value = 30.0
                    if duration <= 0:
                        duration_ts = video_stream.get("duration_ts")
                        time_base = video_stream.get("time_base")
                        if (
                            duration_ts
                            and time_base
                            and isinstance(time_base, str)
                            and "/" in time_base
                        ):
                            try:
                                num, den = time_base.split("/", 1)
                                time_base_value = float(num) / float(den)
                                duration = float(duration_ts) * time_base_value
                            except (TypeError, ValueError, ZeroDivisionError):
                                duration = 0

                    if duration <= 0:
                        nb_frames = video_stream.get("nb_frames")
                        if nb_frames:
                            try:
                                duration = float(nb_frames) / float(fps_value or 30)
                            except (TypeError, ValueError, ZeroDivisionError):
                                duration = 0

                    return {
                        "width": video_stream.get("width", 0),
                        "height": video_stream.get("height", 0),
                        "duration": duration,
                        "bit_rate": int(data.get("format", {}).get("bit_rate", 0) or 0),
                        "fps": fps_value,
                        "has_audio": has_audio,
                        "codec_name": video_codec,
                        "audio_codec_name": audio_codec,
                        "format_name": data.get("format", {}).get("format_name", ""),
                    }
        except Exception as e:
            logger.error(f"获取视频信息失败: {e}")

        return None

    def _build_add_head_tail_command(
        self, input_file: str, output_file: str, variant: int
    ) -> Optional[List[str]]:
        """
        构建加头尾/边框专用命令（不叠加其他功能）

        Args:
            input_file: 主视频文件路径
            output_file: 输出文件路径
            variant: 变体索引

        Returns:
            FFmpeg命令列表，如果无需处理则返回None
        """
        config = self.config.get("add_head_tail", {})
        codec, hwaccel, quality_param = self._get_video_codec_settings()

        use_head = config.get("head_enabled") and config.get("head_file")
        use_tail = config.get("tail_enabled") and config.get("tail_file")
        use_border = config.get("border_enabled") and config.get("border_file")

        if not use_head and not use_tail and not use_border:
            return None

        # 收集所有视频片段
        segments = []

        if use_head:
            head_file = self._select_media_file(
                config["head_file"],
                config.get("head_mode", "file"),
                config.get("head_random", False),
                variant,
            )
            if head_file and os.path.exists(head_file):
                segments.append(head_file)
                print(f"添加片头: {head_file}")

        segments.append(input_file)

        if use_tail:
            tail_file = self._select_media_file(
                config["tail_file"],
                config.get("tail_mode", "file"),
                config.get("tail_random", False),
                variant,
            )
            if tail_file and os.path.exists(tail_file):
                segments.append(tail_file)
                print(f"添加片尾: {tail_file}")

        use_concat = len(segments) > 1

        # 构建命令
        cmd = [self.ffmpeg_path, "-y"]
        if hwaccel:
            cmd.extend(["-hwaccel", hwaccel])

        if use_concat:
            # 使用concat demuxer拼接
            concat_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8"
            )
            concat_file.write("ffconcat version 1.0\n")
            for segment in segments:
                concat_file.write(f"file '{self._format_concat_file_path(segment)}'\n")
            concat_file.close()
            self._temp_files.append(concat_file.name)

            cmd.extend(
                [
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    self._normalize_cmd_path(concat_file.name),
                ]
            )
        else:
            cmd.extend(["-i", self._normalize_cmd_path(input_file)])

        # 边框处理
        border_file = None
        if use_border:
            border_file = self._select_media_file(
                config["border_file"],
                config.get("border_mode", "file"),
                config.get("border_random", False),
                variant,
            )
            if not border_file or not os.path.exists(border_file):
                logger.warning(f"边框文件不存在: {border_file}")
                border_file = None
            else:
                ext = os.path.splitext(border_file)[1].lower()
                if ext not in {".png", ".jpg", ".jpeg", ".bmp", ".gif"}:
                    logger.warning(f"不支持的边框格式: {ext}")
                    border_file = None

        if border_file:
            cmd.extend(["-i", self._normalize_cmd_path(border_file)])

            video_info = self.get_video_info(input_file) or {}
            video_w = video_info.get("width", 1920)
            video_h = video_info.get("height", 1080)

            opacity_min = config.get(
                "border_opacity_min", config.get("border_opacity", 1.0)
            )
            opacity_max = config.get("border_opacity_max", opacity_min)
            margin_x = config.get("border_margin_x", 0)
            margin_y = config.get("border_margin_y", 0)
            remove_bg = config.get("border_remove_bg", False)
            bg_method = config.get("border_bg_method", "video_color")
            bg_similarity = config.get("border_bg_similarity", 0.10)
            bg_blend = config.get("border_bg_blend", 0.30)

            if opacity_min > opacity_max:
                opacity_min, opacity_max = opacity_max, opacity_min
            if opacity_min == opacity_max:
                opacity = opacity_min
            else:
                random.seed(variant)
                opacity = random.uniform(opacity_min, opacity_max)

            border_filters = [f"[1:v]scale={video_w}:{video_h}", "format=rgba"]

            if remove_bg:
                if bg_method == "specified":
                    bg_color = config.get("border_bg_color", "#00FF00").lstrip("#")
                    border_filters.append(
                        f"chromakey=0x{bg_color}:{bg_similarity:.2f}:{bg_blend:.2f}"
                    )
                else:
                    border_filters.append(
                        f"chromakey=0x00FF00:{bg_similarity:.2f}:{bg_blend:.2f}"
                    )

            if opacity < 1.0:
                border_filters.append(f"colorchannelmixer=aa={opacity:.3f}")

            border_chain = ",".join(border_filters) + "[border]"
            overlay_chain = f"[0:v][border]overlay={margin_x}:{margin_y}[vout]"
            filter_graph = f"{border_chain};{overlay_chain}"

            cmd.extend(["-filter_complex", filter_graph])
            cmd.extend(["-map", "[vout]"])
            cmd.extend(["-map", "0:a?"])
        else:
            cmd.extend(["-map", "0:v"])
            cmd.extend(["-map", "0:a?"])

        # 编码参数
        self._append_quality_params(cmd, codec, quality_param, 23, preset="medium")
        cmd.extend(["-c:a", "aac", "-b:a", "128k"])

        cmd.append(self._normalize_cmd_path(output_file))
        return cmd

    def build_filter_complex(self, video_info: Dict, variant: int = 0) -> List[str]:
        """
        构建复杂滤镜链

        Args:
            video_info: 视频信息字典
            variant: 变体索引(用于随机参数)

        Returns:
            滤镜列表
        """
        filters = []
        if getattr(self, "preview_mode", False):
            random.seed(time.time_ns())
        else:
            random.seed(variant)  # 设置随机种子,保证可重复性

        global_options = self._get_global_options()
        if global_options.get("hdr_to_sdr"):
            filters.append(
                "zscale=transfer=linear:npl=100,"
                "tonemap=tonemap=hable:desat=0,"
                "zscale=transfer=bt709:matrix=bt709:primaries=bt709"
            )

        # 1. 画面调整(亮度、对比度、饱和度、锐度、降噪)
        frame_adjust_filter = self._build_frame_adjust_filter()
        if frame_adjust_filter:
            filters.append(frame_adjust_filter)

        # 2. 色调调整(对话框)
        color_tone_filter = self._build_color_tone_filter()
        if color_tone_filter:
            filters.append(color_tone_filter)

        # 3. LUT滤镜(对话框)
        lut_filter = self._build_lut_filter()
        if lut_filter:
            filters.append(lut_filter)

        # 4. 去水印（先于裁剪执行，避免裁剪后 delogo 区域越界）
        delogo_filter = self._build_delogo_filter()
        if delogo_filter:
            filters.append(delogo_filter)

        # 5. 裁剪
        crop_filter = self._build_crop_filter()
        if crop_filter:
            filters.append(crop_filter)

        # 6. 分辨率调整
        resolution_filter = self._build_resolution_filter(video_info)
        if resolution_filter:
            filters.append(resolution_filter)

        # 7. 旋转翻转
        rotate_filter = self._build_rotate_filter(video_info)
        if rotate_filter:
            filters.append(rotate_filter)

        # 8. 宫格分屏
        grid_filter = self._build_grid_split_filter()
        if grid_filter:
            filters.append(grid_filter)

        # 9. 动态缩放
        zoom_filter = self._build_dynamic_zoom_filter(video_info)
        if zoom_filter:
            filters.append(zoom_filter)

        # 10. 抽帧
        extract_filter = self._build_frame_extract_filter()
        if extract_filter:
            filters.append(extract_filter)

        # 11. 更多效果(渐入渐出、虚化、马赛克等)
        more_effects_filter = self._build_more_effects_filter(video_info)
        if more_effects_filter:
            filters.append(more_effects_filter)

        # 12. 变速（非分段）
        speed_filter = self._build_speed_filter(video_info, variant)
        if speed_filter:
            filters.append(speed_filter)

        # 13. 文本（传入 video_info 用于位置计算）
        text_filter = self._build_text_filter(video_info)
        if text_filter:
            filters.append(text_filter)

        return filters

    def _build_frame_adjust_filter(self) -> str:
        """构建画面调整滤镜"""
        if not self.config.get("frame_adjust", {}).get("enabled"):
            return ""

        adj = self.config["frame_adjust"]
        filters = []

        # 随机选择参数值
        brightness = random.uniform(adj["brightness_min"], adj["brightness_max"])
        contrast = random.uniform(adj["contrast_min"], adj["contrast_max"])
        saturation = random.uniform(adj["saturation_min"], adj["saturation_max"])

        # eq滤镜: 调整亮度、对比度、饱和度
        eq_params = []
        if abs(brightness) > 0.01:
            eq_params.append(f"brightness={brightness:.3f}")
        if abs(contrast - 1.0) > 0.01:
            eq_params.append(f"contrast={contrast:.3f}")
        if abs(saturation - 1.0) > 0.01:
            eq_params.append(f"saturation={saturation:.3f}")

        if eq_params:
            filters.append(f"eq={':'.join(eq_params)}")

        # 锐度调整
        sharpness = random.uniform(adj["sharpness_min"], adj["sharpness_max"])
        if sharpness > 0.01:
            # unsharp滤镜: luma_msize:chroma_msize:luma_amount
            filters.append(f"unsharp=5:5:{sharpness:.2f}")

        # 降噪
        denoise = random.randint(adj["denoise_min"], adj["denoise_max"])
        if denoise > 0:
            # hqdn3d滤镜: 高质量3D降噪
            filters.append(f"hqdn3d={denoise}")

        return ",".join(filters) if filters else ""

    def _build_resolution_filter(self, video_info: Dict) -> str:
        """构建分辨率调整滤镜"""
        if not self.config.get("resolution", {}).get("enabled"):
            return ""

        res = self.config["resolution"]
        mode = self.config["mode"]

        width = res["width"]
        height = res["height"]

        # 根据模式选择缩放方式
        if mode["stretch"]:
            # 拉伸模式: 直接缩放到目标尺寸
            scale_filter = f"scale={width}:{height}"

        elif mode["crop"]:
            # 裁切模式: 保持比例放大后裁切
            scale_filter = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"

        elif mode["original"]:
            # 原比例模式: 保持比例,添加黑边或背景
            filters = []

            # 先缩放到目标尺寸内(保持比例)
            scale_filter = (
                f"scale={width}:{height}:force_original_aspect_ratio=decrease"
            )
            filters.append(scale_filter)

            # 添加背景(黑边)
            pad_filter = f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"

            # 如果启用背景虚化
            if mode.get("background_blur"):
                # 使用split和overlay实现背景虚化效果
                # [0:v]split[orig][bg];[bg]scale={width}:{height},gblur=sigma=20[blurred];[blurred][orig]overlay=(W-w)/2:(H-h)/2
                bg_filter = f"split[orig][bg];[bg]scale={width}:{height},gblur=sigma=20[blurred];[blurred][orig]overlay=(W-w)/2:(H-h)/2"
                return bg_filter

            # 如果启用倒影
            if mode.get("reflection"):
                opacity = mode.get("reflection_opacity", 0.5)
                # 添加倒影效果 (仅在横转竖时有效)
                if video_info["width"] > video_info["height"]:  # 横屏视频
                    # 修复：使用简单可靠的方法实现倒影透明度
                    # 1. 分离原视频为主画面和倒影
                    # 2. 倒影部分：竖直翻转 + 调整亮度模拟透明度
                    # 3. 用vstack上下叠加
                    # 使用curves滤镜调整整体亮度来模拟透明效果
                    brightness_factor = opacity  # 透明度越低，亮度越低
                    reflection_filter = (
                        f"{scale_filter}[scaled];"
                        f"[scaled]split[main][refl];"
                        f"[refl]vflip,eq=brightness={-1 + brightness_factor * 2}:contrast={brightness_factor}[reflected];"
                        f"[main][reflected]vstack"
                    )
                    return reflection_filter

            filters.append(pad_filter)
            return ",".join(filters)

        else:
            scale_filter = f"scale={width}:{height}"

        return scale_filter

    def _build_rotate_filter(self, video_info: Dict) -> str:
        """构建旋转翻转滤镜"""
        if not self.config.get("rotate_flip", {}).get("enabled"):
            return ""

        rot = self.config["rotate_flip"]
        random_direction = rot.get("random_direction", False)
        random_angle = rot.get("random_angle", rot.get("random", False))

        if rot.get("left90"):
            return "transpose=2"  # 逆时针90度
        elif rot.get("right90"):
            return "transpose=1"  # 顺时针90度
        elif rot.get("horizontal"):
            return "hflip"  # 水平翻转
        elif rot.get("vertical"):
            return "vflip"  # 垂直翻转
        elif random_direction:
            # 随机方向翻转/旋转（离散）
            return random.choice(["transpose=2", "transpose=1", "hflip", "vflip"])
        elif random_angle:
            # 随机角度旋转
            angle_min = rot.get("random_angle_min", -1.0)
            angle_max = rot.get("random_angle_max", 1.0)
            angle = random.uniform(angle_min, angle_max)

            # rotate滤镜: 角度(弧度)
            angle_rad = angle * math.pi / 180.0
            rotate_filter = f"rotate={angle_rad:.6f}"

            complete_display = rot.get("complete_display")
            black_edge_remove = rot.get("black_edge_remove")
            if complete_display or black_edge_remove:
                rotate_filter = (
                    f"rotate={angle_rad:.6f}:"
                    f"ow=rotw({angle_rad:.6f}):oh=roth({angle_rad:.6f}):fillcolor=black"
                )

            if black_edge_remove:
                base_size = self._get_rotate_base_size(video_info)
                crop_filter = ""
                if base_size:
                    crop_w, crop_h = self._rotated_rect_with_max_area(
                        base_size[0], base_size[1], angle_rad
                    )
                    if crop_w > 0 and crop_h > 0:
                        crop_w = int(max(1, round(crop_w)))
                        crop_h = int(max(1, round(crop_h)))
                        crop_filter = (
                            f"crop={crop_w}:{crop_h}:(iw-{crop_w})/2:(ih-{crop_h})/2"
                        )
                else:
                    logger.warning("无法计算黑边裁切尺寸，已跳过黑边去除")

                if crop_filter:
                    rotate_filter = f"{rotate_filter},{crop_filter}"

            return rotate_filter

        return ""

    def _get_rotate_base_size(self, video_info: Dict) -> Optional[Tuple[int, int]]:
        """估算旋转前的画面尺寸（用于黑边去除裁切）"""
        if not video_info:
            return None

        width = int(video_info.get("width", 0) or 0)
        height = int(video_info.get("height", 0) or 0)
        if width <= 0 or height <= 0:
            return None

        # 如果开启分辨率调整，则旋转前尺寸以目标分辨率为准
        resolution = self.config.get("resolution", {})
        if resolution.get("enabled"):
            width = int(resolution.get("width", width))
            height = int(resolution.get("height", height))
            mode = self.config.get("mode", {})
            if mode.get("reflection"):
                height = int(height * 2)
            return width, height

        # 未开启分辨率调整时，尝试应用裁剪配置
        crop_cfg = self.config.get("crop", {})
        if crop_cfg.get("enabled"):
            mode = normalize_crop_mode(crop_cfg.get("mode", "pixel"))
            if mode == "pixel":
                top = crop_cfg.get("pixel_top", 0)
                bottom = crop_cfg.get("pixel_bottom", 0)
                left = crop_cfg.get("pixel_left", 0)
                right = crop_cfg.get("pixel_right", 0)
                width = max(1, int(width - left - right))
                height = max(1, int(height - top - bottom))
            elif mode == "center":
                ratio_str = crop_cfg.get("aspect_ratio", "1:1")
                try:
                    if ":" in ratio_str:
                        w_ratio, h_ratio = map(float, ratio_str.split(":"))
                        aspect_ratio = w_ratio / h_ratio if h_ratio else 1.0
                    else:
                        aspect_ratio = float(ratio_str) if ratio_str else 1.0
                except Exception:
                    aspect_ratio = 1.0

                if height > 0 and width / height > aspect_ratio:
                    width = max(1, int(round(height * aspect_ratio)))
                else:
                    height = (
                        max(1, int(round(width / aspect_ratio)))
                        if aspect_ratio
                        else height
                    )
            elif mode == "percent":
                percent_value = float(crop_cfg.get("percent_value", 50.0))
                position = normalize_crop_percent_position(
                    crop_cfg.get("percent_crop_mode", "all")
                )
                if position in ["all", "vertical", "horizontal"]:
                    ratio = max(1.0, 100.0 - percent_value / 2.0) / 100.0
                    if position != "vertical":
                        width = max(1, int(round(width * ratio)))
                    if position != "horizontal":
                        height = max(1, int(round(height * ratio)))
                elif position in ["top_left", "top_right", "bottom_left", "bottom_right", "random"]:
                    ratio = max(1.0, percent_value) / 100.0
                    width = max(1, int(round(width * ratio)))
                    height = max(1, int(round(height * ratio)))
                elif position in ["left", "right"]:
                    ratio = max(1.0, percent_value) / 100.0
                    width = max(1, int(round(width * ratio)))
                elif position in ["top", "bottom"]:
                    ratio = max(1.0, percent_value) / 100.0
                    height = max(1, int(round(height * ratio)))

        return width, height

    def _rotated_rect_with_max_area(
        self, width: int, height: int, angle_rad: float
    ) -> Tuple[float, float]:
        """计算旋转后最大内接矩形尺寸"""
        if width <= 0 or height <= 0:
            return 0.0, 0.0

        if abs(angle_rad) < 1e-6 or abs(abs(angle_rad) - math.pi / 2) < 1e-6:
            return float(width), float(height)

        width_is_longer = width >= height
        side_long, side_short = (width, height) if width_is_longer else (height, width)

        sin_a = abs(math.sin(angle_rad))
        cos_a = abs(math.cos(angle_rad))
        if sin_a < 1e-10 or cos_a < 1e-10:
            return float(width), float(height)

        if side_short <= 2 * sin_a * cos_a * side_long or abs(sin_a - cos_a) < 1e-10:
            x = 0.5 * side_short
            if width_is_longer:
                wr = x / sin_a
                hr = x / cos_a
            else:
                wr = x / cos_a
                hr = x / sin_a
        else:
            cos_2a = cos_a * cos_a - sin_a * sin_a
            if abs(cos_2a) < 1e-10:
                return float(width), float(height)
            wr = (width * cos_a - height * sin_a) / cos_2a
            hr = (height * cos_a - width * sin_a) / cos_2a

        return max(1.0, wr), max(1.0, hr)

    def _build_grid_split_filter(self) -> str:
        """构建宫格分屏滤镜"""
        if not self.config.get("grid_split", {}).get("enabled"):
            return ""

        grid = self.config["grid_split"]
        count = grid["count"]
        direction = normalize_grid_direction(grid.get("direction", "auto"))

        # 根据方向确定行列数
        if direction == "vertical":
            rows = count
            cols = 1
        elif direction == "horizontal":
            rows = 1
            cols = count
        else:  # 自动 - 根据视频分辨率智能选择
            # 获取当前视频信息(从配置中传递进来)
            video_info = self.config.get("_current_video_info", {})
            width = video_info.get("width", 1920)
            height = video_info.get("height", 1080)

            # 智能判断：根据宽高比决定排列方向
            # 宽高比 = 宽度 / 高度
            aspect_ratio = width / height if height > 0 else 1.0

            # 核心逻辑（反向思维）：
            # - 横屏视频(宽>高) -> 上下排列 -> 每个小画面保持横屏
            #   例如：1920x1080 上下3个 = 每个1920x360（还是横屏）✓
            # - 竖屏视频(高>宽) -> 左右排列 -> 每个小画面保持竖屏
            #   例如：1080x1920 左右3个 = 每个360x1920（还是竖屏）✓

            if aspect_ratio > 1.2:
                # 横屏视频 -> 上下排列（保持横屏）
                rows = count
                cols = 1
                print(f"\n[AUTO] 智能判断: 横屏视频")
                print(f"[AUTO]   分辨率: {width}x{height}")
                print(f"[AUTO]   宽高比: {aspect_ratio:.2f}")
                print(f"[AUTO]   选择方向: 上下排列 ({count}宫格)")
                print(f"[AUTO]   每个画面: {width}x{height // count} (保持横屏)\n")
            elif aspect_ratio < 0.8:
                # 竖屏视频 -> 左右排列（保持竖屏）
                rows = 1
                cols = count
                print(f"\n[AUTO] 智能判断: 竖屏视频")
                print(f"[AUTO]   分辨率: {width}x{height}")
                print(f"[AUTO]   宽高比: {aspect_ratio:.2f}")
                print(f"[AUTO]   选择方向: 左右排列 ({count}宫格)")
                print(f"[AUTO]   每个画面: {width // count}x{height} (保持竖屏)\n")
            else:
                # 接近正方形 -> 根据宫格数选择最佳布局
                if count <= 2:
                    # 2宫格以下，优先横向
                    rows = 1
                    cols = count
                    print(f"\n[AUTO] 智能判断: 接近正方形")
                    print(f"[AUTO]   分辨率: {width}x{height}")
                    print(f"[AUTO]   宽高比: {aspect_ratio:.2f}")
                    print(
                        f"[AUTO]   选择方向: 左右排列 ({count}宫格, 小数量优先横向)\n"
                    )
                else:
                    # 3宫格以上，选择网格布局
                    import math

                    rows = int(math.sqrt(count))
                    cols = (count + rows - 1) // rows
                    print(f"\n[AUTO] 智能判断: 接近正方形")
                    print(f"[AUTO]   分辨率: {width}x{height}")
                    print(f"[AUTO]   宽高比: {aspect_ratio:.2f}")
                    print(f"[AUTO]   选择方向: 网格布局 ({rows}行 x {cols}列)\n")

        # 使用split和xstack滤镜创建宫格
        # 关键：每个宫格保持较大尺寸，不过度缩小
        # 策略：让每个宫格保持原始尺寸的合理比例，最终输出视频会更大但更清晰

        # 步骤1: split成多份
        parts = []
        parts.append(f"split={count}")
        for i in range(count):
            parts.append(f"[v{i}]")
        split_filter = "".join(parts)

        # 步骤2: 等比缩放每一份
        # 关键优化：不缩小太多，保持每个宫格的清晰度
        # 策略：
        # - 上下排列：每个画面高度为原高的70%（而不是1/3=33%），更清晰
        # - 左右排列：每个画面宽度为原宽的70%（而不是1/3=33%），更清晰
        # - 这样最终输出视频会比原视频大，但每个画面更清晰好看
        # 重要：使用-2参数确保宽高都是偶数（H.264要求）

        scale_filters = []

        if rows > 1 and cols == 1:
            # 上下排列：不过度缩小高度，保持70%的高度
            # 这样3宫格最终高度 = 原高 × 0.7 × 3 = 原高 × 2.1（会变大，但画面清晰）
            scale_ratio = 0.9  # 从70%提升到90%，显著增大宫格尺寸，提升用户体验
            for i in range(count):
                # 关键修复：两个维度都强制偶数
                # floor(ih*0.7/2)*2 确保高度是偶数，-2确保宽度是偶数
                scale_filters.append(
                    f"[v{i}]scale=-2:'floor(ih*{scale_ratio}/2)*2'[s{i}]"
                )
            print(
                f"[SCALE] 上下排列{count}宫格，每个高度保持{scale_ratio * 100}%，宽高均强制偶数"
            )

        elif cols > 1 and rows == 1:
            # 左右排列：不过度缩小宽度，保持70%的宽度
            # 这样3宫格最终宽度 = 原宽 × 0.7 × 3 = 原宽 × 2.1（会变大，但画面清晰）
            scale_ratio = 0.9  # 从70%提升到90%，显著增大宫格尺寸，提升用户体验
            for i in range(count):
                # 关键修复：两个维度都强制偶数
                # floor(iw*0.7/2)*2 确保宽度是偶数，-2确保高度是偶数
                scale_filters.append(
                    f"[v{i}]scale='floor(iw*{scale_ratio}/2)*2':-2[s{i}]"
                )
            print(
                f"[SCALE] 左右排列{count}宫格，每个宽度保持{scale_ratio * 100}%，宽高均强制偶数"
            )

        else:
            # 网格布局：同时缩小到70%
            scale_ratio = 0.7
            for i in range(count):
                # 两个维度都强制偶数：floor(iw*0.7/2)*2
                scale_filters.append(
                    f"[v{i}]scale='floor(iw*{scale_ratio}/2)*2':'floor(ih*{scale_ratio}/2)*2'[s{i}]"
                )
            print(
                f"[SCALE] 网格布局{rows}x{cols}，每个保持{scale_ratio * 100}%尺寸（强制偶数）"
            )

        # 步骤3: 使用xstack组合
        # xstack layout格式: x0_y0|x1_y1|x2_y2...
        # 例如左右排列3个: 0_0|w0_0|w0+w1_0
        # 例如上下排列3个: 0_0|0_h0|0_h0+h1
        inputs = "".join([f"[s{i}]" for i in range(count)])

        layout_parts = []
        if cols > 1 and rows == 1:  # 水平排列(左右)
            for i in range(count):
                if i == 0:
                    layout_parts.append("0_0")
                else:
                    # 累加左侧所有宽度
                    x_expr = "+".join([f"w{j}" for j in range(i)])
                    layout_parts.append(f"{x_expr}_0")
        elif rows > 1 and cols == 1:  # 垂直排列(上下)
            for i in range(count):
                if i == 0:
                    layout_parts.append("0_0")
                else:
                    # 累加上方所有高度
                    y_expr = "+".join([f"h{j}" for j in range(i)])
                    layout_parts.append(f"0_{y_expr}")
        else:  # 网格布局(不应该出现，但保留兼容)
            for i in range(count):
                row = i // cols
                col = i % cols
                if row == 0 and col == 0:
                    layout_parts.append("0_0")
                elif row == 0:
                    # 第一行，只累加宽度
                    x_expr = "+".join([f"w{j}" for j in range(col)])
                    layout_parts.append(f"{x_expr}_0")
                elif col == 0:
                    # 第一列，只累加高度
                    y_expr = "+".join([f"h{j * cols}" for j in range(row)])
                    layout_parts.append(f"0_{y_expr}")
                else:
                    # 既累加宽度又累加高度
                    x_expr = "+".join([f"w{j}" for j in range(col)])
                    y_expr = "+".join([f"h{j * cols}" for j in range(row)])
                    layout_parts.append(f"{x_expr}_{y_expr}")

        layout = "|".join(layout_parts)
        xstack_filter = f"{inputs}xstack=inputs={count}:layout={layout}"

        # 组合所有滤镜
        all_filters = [split_filter] + scale_filters + [xstack_filter]
        result = ";".join(all_filters)

        # 如果启用两端虚化(给整个效果添加模糊)
        if grid.get("blur"):
            result += ",gblur=sigma=5"

        return result

    def _build_dynamic_zoom_filter(self, video_info: Dict) -> str:
        """构建动态缩放滤镜"""
        if not self.config.get("dynamic_zoom", {}).get("enabled"):
            return ""

        zoom = self.config["dynamic_zoom"]
        zoom_min = zoom["min"]
        zoom_max = zoom["max"]

        duration = video_info.get("duration", 10)
        fps = video_info.get("fps", 30)

        # zoompan滤镜: z表达式从min到max平滑过渡
        # z='min(max(zoom,pzoom+0.0015),1.5)'
        zoom_expr = f"'if(lte(zoom,{zoom_min}),{zoom_min},if(gte(zoom,{zoom_max}),{zoom_max},zoom+{(zoom_max - zoom_min) / (duration * fps):.6f}))'"

        return f"zoompan=z={zoom_expr}:d={int(duration * fps)}:s={video_info['width']}x{video_info['height']}"

    def _build_frame_extract_filter(self) -> str:
        """构建抽帧滤镜"""
        if not self.config.get("frame_extract", {}).get("enabled"):
            self._current_frame_extract_interval = 1
            return ""

        extract = self.config["frame_extract"]
        frame_min = max(1, int(extract.get("min", 1)))
        frame_max = max(1, int(extract.get("max", frame_min)))
        if frame_min > frame_max:
            frame_min, frame_max = frame_max, frame_min

        # 随机选择抽帧间隔
        interval = random.randint(frame_min, frame_max)
        self._current_frame_extract_interval = interval

        # select滤镜: 每隔N帧选择一帧
        return f"select='not(mod(n,{interval}))',setpts=N/FRAME_RATE/TB"

    def _build_color_tone_filter(self) -> str:
        """构建色调调整滤镜(对话框)"""
        tone_config = self.config.get("color_tone", {})
        if not tone_config:
            return ""

        filters = []

        # 伽玛值
        gamma = tone_config.get("gamma", 1.0)
        if abs(gamma - 1.0) > 0.01:
            filters.append(f"eq=gamma={gamma:.2f}")

        # RGB调整
        red = tone_config.get("red", 1.0)
        green = tone_config.get("green", 1.0)
        blue = tone_config.get("blue", 1.0)
        if abs(red - 1.0) > 0.01 or abs(green - 1.0) > 0.01 or abs(blue - 1.0) > 0.01:
            filters.append(f"colorbalance=rs={red:.2f}:gs={green:.2f}:bs={blue:.2f}")

        # 色温调整 (保留随机，映射到FFmpeg colorbalance的rm/bm范围[-1,1])
        temp_min = tone_config.get("color_temp_min", 6500)
        temp_max = tone_config.get("color_temp_max", 6500)
        temp = random.randint(temp_min, temp_max)
        if temp != 6500:
            # 使用更平滑的非线性映射，确保极端色温不越界
            # 1000K-6500K (暖色): 映射到 rm:-1~0, bm:1~0
            # 6500K-20000K (冷色): 映射到 rm:0~1, bm:0~-1
            if temp < 6500:
                # 暖色区域 (1000K-6500K)
                normalized = (temp - 1000) / (6500 - 1000)  # 0~1
                rm_value = -1.0 + normalized  # -1~0
                bm_value = 1.0 - normalized  # 1~0
            else:
                # 冷色区域 (6500K-20000K)
                normalized = (temp - 6500) / (20000 - 6500)  # 0~1
                rm_value = min(normalized, 1.0)  # 0~1
                bm_value = max(-normalized, -1.0)  # 0~-1

            # 二次保险：夹紧到FFmpeg允许范围[-1, 1]
            rm_value = max(-1.0, min(1.0, rm_value))
            bm_value = max(-1.0, min(1.0, bm_value))

            if abs(rm_value) > 0.01 or abs(bm_value) > 0.01:
                filters.append(f"colorbalance=rm={rm_value:.3f}:bm={bm_value:.3f}")

        return ",".join(filters) if filters else ""

    def _build_lut_filter(self) -> str:
        """构建LUT滤镜(对话框)"""
        from utils.lut_filters import (
            display_to_id,
            id_to_file,
            resolve_ffmpeg_lut_path,
        )

        lut_config = self.config.get("lut_filter", {})
        if not lut_config.get("apply"):
            return ""

        selected_filters = lut_config.get("filters", [])
        if not selected_filters:
            return ""

        normalized_ids = []
        for item in selected_filters:
            if not isinstance(item, str):
                continue
            if id_to_file(item):
                if item not in normalized_ids:
                    normalized_ids.append(item)
                continue
            mapped_id = display_to_id(item)
            if mapped_id and mapped_id not in normalized_ids:
                normalized_ids.append(mapped_id)

        if not normalized_ids:
            return ""

        # 随机选取只保留一个滤镜
        if lut_config.get("random_apply") and len(normalized_ids) > 1:
            normalized_ids = [random.choice(normalized_ids)]

        lut_filters = []
        for filter_id in normalized_ids:
            lut_path = resolve_ffmpeg_lut_path(filter_id)
            if lut_path and os.path.exists(lut_path):
                escaped = self._escape_ffmpeg_path(lut_path)
                lut_filters.append(f"lut3d='{escaped}'")
            else:
                logger.warning(f"LUT文件不存在: {filter_id} -> {lut_path}")

        return ",".join(lut_filters) if lut_filters else ""

    def _build_crop_filter(self) -> str:
        """构建裁剪滤镜 - 统一三种裁剪模式"""
        if not self.config.get("crop", {}).get("enabled"):
            return ""

        crop_cfg = self.config["crop"]
        mode = normalize_crop_mode(crop_cfg.get("mode", "pixel"))

        # 像素模式
        if mode == "pixel":
            top = crop_cfg.get("pixel_top", 0)
            bottom = crop_cfg.get("pixel_bottom", 0)
            left = crop_cfg.get("pixel_left", 0)
            right = crop_cfg.get("pixel_right", 0)

            if top > 0 or bottom > 0 or left > 0 or right > 0:
                return f"crop=iw-{left + right}:ih-{top + bottom}:{left}:{top}"

        # 中间比例模式
        elif mode == "center":
            ratio_str = crop_cfg.get("aspect_ratio", "16:9")
            try:
                if ":" in ratio_str:
                    w_ratio, h_ratio = map(float, ratio_str.split(":"))
                    aspect_ratio = w_ratio / h_ratio
                else:
                    aspect_ratio = 1.0
            except:
                aspect_ratio = 1.0

            # 从视频中心裁剪出指定比例的区域
            crop_expr = "crop='if(gt(a,{aspect_ratio}),ih*{aspect_ratio},iw)':'if(gt(a,{aspect_ratio}),ih,iw/{aspect_ratio})':(iw-ow)/2:(ih-oh)/2".format(
                aspect_ratio=aspect_ratio
            )
            return crop_expr

        # 百分比模式
        elif mode == "percent":
            percent_value = crop_cfg.get("percent_value", 50.0)
            position = normalize_crop_percent_position(
                crop_cfg.get("percent_crop_mode", "all")
            )

            # 根据位置裁剪对应区域
            if position == "all":
                return f"crop='max(1, iw*(100-{percent_value}/2)/100)':'max(1, ih*(100-{percent_value}/2)/100)':iw*{percent_value}/400:ih*{percent_value}/400"
            elif position == "top_left":
                return f"crop='max(1, iw*{percent_value}/100)':'max(1, ih*{percent_value}/100)':0:0"
            elif position == "top_right":
                return f"crop='max(1, iw*{percent_value}/100)':'max(1, ih*{percent_value}/100)':'max(0, iw-iw*{percent_value}/100)':0"
            elif position == "bottom_left":
                return f"crop='max(1, iw*{percent_value}/100)':'max(1, ih*{percent_value}/100)':0:'max(0, ih-ih*{percent_value}/100)'"
            elif position == "bottom_right":
                return f"crop='max(1, iw*{percent_value}/100)':'max(1, ih*{percent_value}/100)':'max(0, iw-iw*{percent_value}/100)':'max(0, ih-ih*{percent_value}/100)'"
            elif position == "top":
                return f"crop=iw:'max(1, ih*{percent_value}/100)':0:0"
            elif position == "bottom":
                return f"crop=iw:'max(1, ih*{percent_value}/100)':0:'max(0, ih-ih*{percent_value}/100)'"
            elif position == "left":
                return f"crop='max(1, iw*{percent_value}/100)':ih:0:0"
            elif position == "right":
                return f"crop='max(1, iw*{percent_value}/100)':ih:'max(0, iw-iw*{percent_value}/100)':0"
            elif position == "vertical":
                return f"crop=iw:'max(1, ih*(100-{percent_value}/2)/100)':0:ih*{percent_value}/400"
            elif position == "horizontal":
                return f"crop='max(1, iw*(100-{percent_value}/2)/100)':ih:iw*{percent_value}/400:0"
            elif position == "random":
                # 随机裁剪（保留百分比的区域）
                return f"crop='max(1, iw*{percent_value}/100)':'max(1, ih*{percent_value}/100)':random(1)*(iw-iw*{percent_value}/100):random(1)*(ih-ih*{percent_value}/100)"
            else:
                # 默认四边
                return f"crop='max(1, iw*(100-{percent_value}/2)/100)':'max(1, ih*(100-{percent_value}/2)/100)':iw*{percent_value}/400:ih*{percent_value}/400"

        return ""

    def _build_delogo_filter(self) -> str:
        """构建delogo去水印滤镜"""
        if not self.config.get("remove_watermark", {}).get("enabled"):
            return ""

        wm = self.config["remove_watermark"]

        # 只有FFmpeg DELOGO方法才使用delogo滤镜
        method = wm.get("method", "ffmpeg")
        if method not in ["ffmpeg", "multidelogo"]:
            return ""  # 其他方法不支持

        # 获取水印区域列表
        regions = wm.get("regions", [])
        if not regions:
            # 向后兼容旧配置
            regions = []
            for i in range(1, 4):
                region_key = f"region{i}"
                if region_key in wm:
                    r = wm[region_key]
                    if r.get("w", 0) > 0 and r.get("h", 0) > 0:
                        regions.append((r["x"], r["y"], r["w"], r["h"]))

        # 如果regions仍然为空，尝试根据预设平台自动获取区域（用于预览）
        if not regions:
            preset_name = normalize_watermark_preset(wm.get("watermark_preset", "custom"))
            if preset_name and preset_name != "custom":
                # 尝试从配置中获取视频信息（预览时已设置）
                video_info = self.config.get("_current_video_info")
                if video_info:
                    video_width = video_info.get("width", 1920)
                    video_height = video_info.get("height", 1080)
                    # 根据预设名称获取区域（需要映射到ffmpeg_builder中的预设区域）
                    preset_region = self._get_preset_region_from_name(
                        preset_name, video_width, video_height
                    )
                    if preset_region:
                        regions = [preset_region]

        if not regions:
            return ""

        # 获取视频宽高用于边界夹紧（防止预设贴边导致 delogo 报错）
        video_info = self.config.get("_current_video_info")
        video_width = video_info.get("width", 1920) if video_info else 1920
        video_height = video_info.get("height", 1080) if video_info else 1080

        # 构建delogo滤镜链
        filters = []
        for x, y, w, h in regions:
            # 边界夹紧：确保区域不超出画面范围
            x = max(0, min(x, video_width - 1))
            y = max(0, min(y, video_height - 1))
            # delogo 对右/下边界敏感，确保不贴边
            w = min(w, video_width - x - 1)
            h = min(h, video_height - y - 1)

            # 跳过无效区域（宽或高为0或负数）
            if w <= 0 or h <= 0:
                logger.warning(f"跳过无效去水印区域 (x={x}, y={y}, w={w}, h={h})")
                continue

            # delogo参数：x, y, w, h, show(0=不显示检测框)
            delogo_filter = f"delogo=x={x}:y={y}:w={w}:h={h}:show=0"

            # 检查是否启用了时间段去水印
            time_period_enabled = wm.get("time_period_enabled", False)
            time_period_start = wm.get("time_period_start", 0.0)
            time_period_end = wm.get("time_period_end", 0.0)

            # 如果启用了时间段去水印，为每个滤镜单独添加时间段限制
            if time_period_enabled and time_period_end > 0:
                delogo_filter = f"{delogo_filter}:enable='between(t,{time_period_start},{time_period_end})'"

            filters.append(delogo_filter)

        return ",".join(filters) if filters else ""

    def _get_preset_region_from_name(
        self, preset_name: str, video_width: int, video_height: int
    ) -> tuple:
        """根据预设名称获取区域（用于预览时的自动获取）"""
        preset_code = normalize_watermark_preset(preset_name)
        # 将预设 code 映射到简短的方案名称
        preset_mapping = {
            "bilibili_top_right": "B站",
            "douyin_bottom_right": "抖音",
            "xiaohongshu_bottom_right": "小红书",
            "iqiyi_top_right": "爱奇艺",
            "tencent_video_top_right": "腾讯视频",
            "youku_top_right": "优酷视频",
            "xigua_top_right": "西瓜视频",
            "weibo_bottom_right": "微博",
            "toutiao_bottom_right": "小红书",  # 使用小红书预设（右下角）
            "kuaishou_bottom_right": "快手",
            "zhihu_bottom_right": "知乎视频",  # 使用知乎预设
            "netease_music_bottom_left": None,  # 暂时没有预设
            "tiktok_bottom_right": "TikTok",
            "youtube_bottom_left": "YouTube",
            "acfun_top_right": "B站",  # 使用B站预设
            "bilibili_bottom_left": "B站",  # 使用B站预设
            "douban_top_right": "B站",  # 使用B站预设
            "sohu_bottom_right": "小红书",  # 使用小红书预设
            "letv_top_right": "腾讯视频",  # 使用腾讯视频预设
            "migu_bottom_right": "小红书",  # 使用小红书预设
        }

        # 获取简短的方案名称
        scheme = preset_mapping.get(preset_code)
        if not scheme:
            return ()  # 返回空元组而不是None

        # 基于视频宽高的动态计算变量
        W = video_width
        H = video_height
        Margin = int(W * 0.05)
        Watermark_W = int(W * 0.30)
        Watermark_H = int(Watermark_W / 3)

        # 使用比例计算的平台（右上角：B站、爱奇艺、腾讯视频）
        if scheme in ["B站", "爱奇艺", "腾讯视频"]:
            x = int(W - Watermark_W - Margin)
            y = int(Margin)
            w = int(Watermark_W)
            h = int(Watermark_H)
            return (x, y, w, h)

        # 使用比例计算的平台（右下角：抖音、小红书、TikTok、微博、快手）
        if scheme in ["抖音", "小红书", "TikTok", "微博", "快手"]:
            x = int(W - Watermark_W - Margin)
            y = int(H - Watermark_H - Margin)
            w = int(Watermark_W)
            h = int(Watermark_H)
            return (x, y, w, h)

        # 使用比例计算的平台（左下角：YouTube）
        if scheme == "YouTube":
            x = int(Margin)
            y = int(H - Watermark_H - Margin)
            w = int(Watermark_W)
            h = int(Watermark_H)
            return (x, y, w, h)

        # 其他平台使用固定像素值（基于1920x1080分辨率并缩放）
        BASE_WIDTH = 1920
        BASE_HEIGHT = 1080
        scale_x = video_width / BASE_WIDTH if video_width > 0 else 1.0
        scale_y = video_height / BASE_HEIGHT if video_height > 0 else 1.0

        presets = {
            "优酷视频": (1820, 10, 100, 50),
            "西瓜视频": (1830, 10, 90, 50),
            "知乎视频": (1870, 10, 50, 50),
        }

        # 获取预设区域
        if scheme in presets:
            base_x, base_y, base_w, base_h = presets[scheme]
            # 应用缩放
            x = int(base_x * scale_x)
            y = int(base_y * scale_y)
            w = int(base_w * scale_x)
            h = int(base_h * scale_y)
            return (x, y, w, h)
        return ()  # 返回空元组而不是None

    def _build_watermark_filter(self) -> str:
        """构建加水印滤镜"""
        if not self.config.get("add_watermark", {}).get("enabled"):
            return ""

        wm = self.config["add_watermark"]
        wm_file = wm.get("file", "")

        if not wm_file or not os.path.exists(wm_file):
            return ""

        position = normalize_text_position(wm.get("position", "bottom_right"))
        offset_x = wm.get("offset_x", 10)
        offset_y = wm.get("offset_y", 10)
        opacity = wm.get("opacity", 1.0)

        # 位置映射
        pos_map = {
            "top_left": f"{offset_x}:{offset_y}",
            "top_right": f"W-w-{offset_x}:{offset_y}",
            "bottom_left": f"{offset_x}:H-h-{offset_y}",
            "bottom_right": f"W-w-{offset_x}:H-h-{offset_y}",
            "center": "(W-w)/2:(H-h)/2",
        }

        pos_expr = pos_map.get(position, f"W-w-{offset_x}:H-h-{offset_y}")

        # overlay滤镜需要使用-i多个输入,这里返回空，在build_command中处理
        return ""

    def _get_effective_filter_duration(self, video_info: Dict) -> float:
        """计算进入更多效果滤镜时的有效时间轴长度。"""
        duration = max(0.0, float(video_info.get("duration", 0) or 0))

        trim_config = self.config.get("trim", {})
        if duration > 0 and trim_config.get("enabled"):
            mode = normalize_trim_mode(trim_config.get("mode", "trim_edges"))
            if mode == "trim_edges":
                head = max(0.0, float(trim_config.get("head", 0) or 0))
                tail = max(0.0, float(trim_config.get("tail", 0) or 0))
                duration = max(0.0, duration - head - tail)
            else:
                start = max(0.0, float(trim_config.get("start", 0) or 0))
                remaining = max(0.0, duration - start)
                requested = max(0.0, float(trim_config.get("duration", 0) or 0))
                duration = min(remaining, requested) if requested > 0 else remaining

        if getattr(self, "preview_mode", False):
            preview_duration = max(
                0.0, float(getattr(self, "preview_duration", 10.0) or 0)
            )
            if preview_duration > 0:
                duration = min(duration, preview_duration)

        extract_config = self.config.get("frame_extract", {})
        if extract_config.get("enabled"):
            interval = max(
                1, int(getattr(self, "_current_frame_extract_interval", 1) or 1)
            )
            duration /= interval

        effects = self.config.get("more_effects", {})
        if effects.get("delay_enabled"):
            duration += max(0.0, float(effects.get("delay_time", 0) or 0))

        return duration

    def _build_more_effects_filter(self, video_info: Dict = None) -> str:
        """构庻更多效果滤镜(对话框)"""
        effects = self.config.get("more_effects", {})
        if not effects:
            return ""

        filters = []
        video_info = video_info or {}

        def _format_color_with_opacity(color_value: str, opacity: float) -> str:
            if not isinstance(color_value, str) or not color_value:
                return color_value
            color_hex = color_value.lstrip("#")
            if len(color_hex) == 6:
                alpha = max(0.0, min(1.0, float(opacity)))
                return f"0x{color_hex}@{alpha:.2f}"
            return color_value

        def _build_curtain_filter(
            duration: float, direction: str, color_value: str
        ) -> str:
            if duration <= 0:
                duration = float(video_info.get("duration", 0) or 0)
            if duration <= 0:
                return ""

            direction_code = normalize_curtain_direction(direction)
            if direction_code in ("auto", "auto_close"):
                width = video_info.get("width", 0) or 0
                height = video_info.get("height", 0) or 0
                if width and height:
                    auto_axis = "horizontal" if width >= height else "vertical"
                else:
                    auto_axis = "horizontal"
                direction_code = (
                    "horizontal_close" if direction_code == "auto_close" else auto_axis
                )

            duration_expr = f"{float(duration):.3f}"

            # 旧版 FFmpeg 对动态 crop 的宽高求值不稳定，收幕到最后一帧时
            # 会出现宽度为 0 的错误。geq 直接按像素生成幕布，避免改变画面尺寸。
            color_hex = str(color_value or "#000000").lstrip("#")
            if len(color_hex) >= 6:
                try:
                    red, green, blue = (
                        int(color_hex[0:2], 16),
                        int(color_hex[2:4], 16),
                        int(color_hex[4:6], 16),
                    )
                except ValueError:
                    red, green, blue = 0, 0, 0
            else:
                red, green, blue = 0, 0, 0

            progress = f"min(1,max(0,T/{duration_expr}))"
            if direction_code in ("horizontal", "horizontal_close"):
                if direction_code == "horizontal":
                    visible = f"lte(abs(X-W/2),W/2*{progress})"
                else:
                    visible = (
                        f"lte(abs(X-W/2),W/2*(1-{progress}))"
                    )
            elif direction_code in ("vertical", "vertical_close"):
                if direction_code == "vertical":
                    visible = f"lte(abs(Y-H/2),H/2*{progress})"
                else:
                    visible = f"lte(abs(Y-H/2),H/2*(1-{progress}))"
            elif direction_code == "left":
                visible = f"lte(X,W*{progress})"
            elif direction_code == "right":
                visible = f"gte(X,W*(1-{progress}))"
            elif direction_code == "up":
                visible = f"lte(Y,H*{progress})"
            elif direction_code == "down":
                visible = f"gte(Y,H*(1-{progress}))"
            else:
                visible = f"lte(abs(X-W/2),W/2*{progress})"

            return (
                "format=rgb24,"
                "geq="
                f"r='if({visible},r(X,Y),{red})':"
                f"g='if({visible},g(X,Y),{green})':"
                f"b='if({visible},b(X,Y),{blue})',"
                "format=yuv420p"
            )

        # 延时（整体后移）
        if effects.get("delay_enabled"):
            delay_time = float(effects.get("delay_time", 0.0))
            if delay_time > 0:
                filters.append(f"tpad=start_duration={delay_time:.3f}")

        # 渐入渐出
        if effects.get("fade_in_enabled"):
            duration = effects.get("fade_in_duration", 1.5)
            filters.append(f"fade=in:0:{int(duration * 25)}")

        if effects.get("fade_out_enabled"):
            configured_duration = max(
                0.0, float(effects.get("fade_out_duration", 1.5) or 0)
            )
            timeline_duration = self._get_effective_filter_duration(video_info)
            if configured_duration > 0 and timeline_duration > 0:
                fade_duration = min(configured_duration, timeline_duration)
                start_time = max(0.0, timeline_duration - fade_duration)
                filters.append(
                    f"fade=out:st={start_time:.3f}:d={fade_duration:.3f}"
                )
            else:
                logger.warning(
                    "跳过渐出：无法确定有效时长或渐出时长无效 duration=%s fade=%s",
                    timeline_duration,
                    configured_duration,
                )

        # 边框
        if effects.get("border_enabled"):
            color = effects.get("border_color", "#FFFFFF")
            opacity = effects.get("border_opacity", 1.0)
            width = effects.get("border_width", 3)
            style = normalize_border_style(effects.get("border_style", "all"))
            color_expr = _format_color_with_opacity(color, opacity)

            # 根据样式添加边框
            if style == "all":
                filters.append(
                    f"drawbox=x=0:y=0:w=iw:h=ih:color={color_expr}:t={width}"
                )
            elif style == "vertical":
                filters.append(
                    f"drawbox=x=0:y=0:w=iw:h={width}:color={color_expr}:t=fill"
                )
                filters.append(
                    f"drawbox=x=0:y=ih-{width}:w=iw:h={width}:color={color_expr}:t=fill"
                )
            elif style == "horizontal":
                filters.append(
                    f"drawbox=x=0:y=0:w={width}:h=ih:color={color_expr}:t=fill"
                )
                filters.append(
                    f"drawbox=x=iw-{width}:y=0:w={width}:h=ih:color={color_expr}:t=fill"
                )

        # 网格
        if effects.get("grid_enabled"):
            grid_color = effects.get("grid_color", "#FFFFFF")
            grid_opacity = effects.get("grid_opacity", 1.0)
            grid_width = effects.get("grid_width", 100)
            grid_height = effects.get("grid_height", 100)
            line_width = effects.get("grid_line", 1.0)
            grid_color_expr = _format_color_with_opacity(grid_color, grid_opacity)

            # 使用drawgrid滤镜
            filters.append(
                f"drawgrid=w={grid_width}:h={grid_height}:t={int(line_width)}:c={grid_color_expr}"
            )

        # 蒙版倒置
        if effects.get("mask_invert_enabled"):
            threshold = max(
                0.0, min(1.0, float(effects.get("mask_invert_value", 0.05)))
            )
            threshold_val = int(threshold * 255)
            filters.append(
                "lutrgb="
                f"r='if(gte(val,{threshold_val}),255-val,val)':"
                f"g='if(gte(val,{threshold_val}),255-val,val)':"
                f"b='if(gte(val,{threshold_val}),255-val,val)'"
            )

        # 虚化
        if effects.get("blur_enabled"):
            blur_value = effects.get("blur_value", 0.5)
            filters.append(f"gblur=sigma={blur_value}")

        # 马赛克
        if effects.get("mosaic_enabled"):
            size = effects.get("mosaic_size", 24)
            filters.append(
                f"scale=iw/{size}:ih/{size},scale={size}*iw:{size}*ih:flags=neighbor"
            )

        # 特效滤镜
        if effects.get("glow_enabled"):
            filters.append("gblur=sigma=2:steps=2,eq=brightness=0.05:contrast=1.05")

        if effects.get("bw_enabled"):
            filters.append("hue=s=0")

        if effects.get("negative_enabled"):
            filters.append("negate")

        if effects.get("cartoon_enabled"):
            filters.append(
                "edgedetect=mode=colormix:high=0.4,eq=contrast=1.1:saturation=1.2"
            )

        if effects.get("emboss_enabled"):
            filters.append("convolution=-2 -1 0 -1 1 1 0 1 2")

        if effects.get("smart_blur_enabled"):
            filters.append("smartblur=1.0:0.5:-1.0")

        # 开幕动画(使用xfade效果)
        if effects.get("curtain_enabled"):
            duration = effects.get("curtain_duration", 2.0)
            direction = effects.get("curtain_direction", "auto")
            color = effects.get("curtain_color", "#000000")
            curtain_filter = _build_curtain_filter(float(duration), direction, color)
            if curtain_filter:
                filters.append(curtain_filter)

        return ",".join(filters) if filters else ""

    def _resolve_speed_value(self, video_info: Dict, variant: int) -> float:
        """为单个视频解析一次变速倍率，供视频和音频滤镜共用。"""
        speed_config = self.config.get("speed", {})
        if not speed_config.get("enabled") or speed_config.get("segment_enabled"):
            return 1.0

        speed_min = float(speed_config.get("min", 1.0))
        speed_max = float(speed_config.get("max", 1.0))
        if speed_min > speed_max:
            speed_min, speed_max = speed_max, speed_min

        if getattr(self, "preview_mode", False):
            rng = random.Random(time.time_ns())
        else:
            rng = random.Random(variant)

        original_speed = rng.uniform(speed_min, speed_max)
        speed_value = original_speed

        if speed_config.get("min_duration_enabled"):
            min_duration = float(speed_config.get("min_duration", 10))
            video_duration = float(video_info.get("duration", 0) or 0)

            if video_duration > 0 and min_duration > 0:
                expected_duration = video_duration / speed_value
                if expected_duration < min_duration:
                    speed_value = video_duration / min_duration
                    speed_value = max(0.5, min(4.0, speed_value))
                    print(
                        f"变速保护: 调整速度从 {original_speed:.2f} 到 {speed_value:.2f} 以满足最短时长 {min_duration}秒"
                    )

        return speed_value

    def _build_audio_speed_filters(
        self, speed_value: float, pitch_enabled: bool
    ) -> List[str]:
        """构建与视频共用倍率的音频变速滤镜。"""
        if abs(speed_value - 1.0) <= 0.001:
            return []

        if pitch_enabled:
            return [f"asetrate=44100*{speed_value:.4f}", "aresample=44100"]

        filters = []
        current_speed = speed_value
        while current_speed > 2.0:
            filters.append("atempo=2.0")
            current_speed /= 2.0
        while current_speed < 0.5:
            filters.append("atempo=0.5")
            current_speed /= 0.5
        if abs(current_speed - 1.0) > 0.001:
            filters.append(f"atempo={current_speed:.4f}")
        return filters

    def _build_frame_extract_audio_filters(self, video_info: Dict) -> List[str]:
        """按本次抽帧间隔同步压缩音频时间轴。"""
        extract_config = self.config.get("frame_extract", {})
        if (
            not extract_config.get("enabled")
            or not extract_config.get("audio_speed")
            or not video_info.get("has_audio", True)
        ):
            return []

        interval = max(
            1, int(getattr(self, "_current_frame_extract_interval", 1) or 1)
        )
        if interval == 1:
            return []

        # 内置旧版 FFmpeg 在 filter_complex 中串联多级 atempo 会丢尾帧。
        # 先统一输入采样率，再通过 asetrate 可靠压缩时间轴。
        return [
            "aresample=44100",
            f"asetrate=44100*{float(interval):.4f}",
            "aresample=44100",
        ]

    def _build_speed_filter(self, video_info: Dict, variant: int = 0) -> str:
        """构建变速滤镜（仅处理非分段变速）"""
        speed_config = self.config.get("speed", {})

        # 如果未启用或启用了分段变速，返回空（分段变速在 build_command 中单独处理）
        if not speed_config.get("enabled") or speed_config.get("segment_enabled"):
            return ""

        speed_value = getattr(self, "_current_speed_value", None)
        if speed_value is None:
            speed_value = self._resolve_speed_value(video_info, variant)

        # 视频变速使用 setpts
        if abs(speed_value - 1.0) > 0.001:
            return f"setpts={1.0 / speed_value:.4f}*PTS"

        return ""

    def _build_text_filter(self, video_info: Dict = None) -> str:
        """构建文本滤镜（支持三轨道配置）"""
        text_config = self.config.get("text", {})
        filters = []

        # 处理三个文本轨道
        for i in range(1, 4):
            if text_config.get(f"text{i}_enabled"):
                track_config = text_config.get(f"text{i}_config")
                if not track_config:
                    continue

                # 构建该轨道的 drawtext 滤镜
                drawtext = self._build_text_track_filter(
                    track_config, video_info or {}, self._current_input_file or ""
                )
                if drawtext:
                    filters.append(drawtext)

        return ",".join(filters) if filters else ""

    def _build_text_track_filter(
        self, config: Dict, video_info: Dict, input_file: str
    ) -> str:
        """构建单个文本轨道的 drawtext 滤镜"""
        # 1. 获取文本内容
        text = self._get_text_content(config, input_file)
        if not text:
            return ""

        # 检查是否启用行显模式
        line_display = config.get("line_display", False)
        loop = config.get("loop", False)

        if line_display:
            # 行显模式：拆分为多行，为每行生成独立的 drawtext 滤镜
            return self._build_line_display_filter(text, config, video_info, input_file)
        else:
            # 单文本模式
            return self._build_single_text_filter(text, config, video_info, loop)

    def _build_single_text_filter(
        self, text: str, config: Dict, video_info: Dict, loop: bool
    ) -> str:
        """构建单个文本的 drawtext 滤镜"""
        # 转义特殊字符
        escaped_text = (
            text.replace("\\", "\\\\\\\\").replace(":", "\\:").replace("'", "\\'")
        )

        # 2. 获取字体配置
        font_size = (
            config.get("font_size", 24) if config.get("font_enabled", True) else 24
        )
        font_family = config.get("font_family", "微软雅黑")
        font_path = self._resolve_font_path({"family": font_family})

        if font_path:
            font_spec = f":fontfile='{self._escape_ffmpeg_path(font_path)}'"
        else:
            font_spec = f":font='{font_family}'"

        # 3. 颜色与透明度
        font_color = config.get("font_color", "#FFFFFF")
        font_opacity = config.get("font_opacity", 1.0)
        fontcolor_hex = font_color.lstrip("#")
        fontcolor = f"0x{fontcolor_hex}"
        fontcolor_expr = f"{fontcolor}@{font_opacity:.3f}"

        # 4. 位置计算
        position_name = normalize_text_position(config.get("position", "center"))

        # 随机位置：从九宫格中随机选择
        if position_name == "random":
            position_name = random.choice(
                [
                    "top",
                    "bottom",
                    "left",
                    "right",
                    "top_left",
                    "top_right",
                    "bottom_left",
                    "bottom_right",
                    "center",
                ]
            )

        margin_x = config.get("margin_x", 0)
        margin_y = config.get("margin_y", 0)
        unit = config.get("unit", "p")

        # 位置映射
        position_map = {
            "top": ("(w-text_w)/2", "0"),
            "bottom": ("(w-text_w)/2", "h-text_h"),
            "left": ("0", "(h-text_h)/2"),
            "right": ("w-text_w", "(h-text_h)/2"),
            "top_left": ("0", "0"),
            "top_right": ("w-text_w", "0"),
            "bottom_left": ("0", "h-text_h"),
            "bottom_right": ("w-text_w", "h-text_h"),
            "center": ("(w-text_w)/2", "(h-text_h)/2"),
        }

        x_base, y_base = position_map.get(position_name, position_map["center"])

        # 应用边距
        if unit == "%":
            # 百分比单位
            video_w = video_info.get("width", 1920)
            video_h = video_info.get("height", 1080)
            x_offset = int(margin_x * video_w / 100)
            y_offset = int(margin_y * video_h / 100)
        else:
            # 像素单位
            x_offset = margin_x
            y_offset = margin_y

        if x_offset != 0:
            x_expr = f"({x_base})+{x_offset}"
        else:
            x_expr = x_base

        if y_offset != 0:
            y_expr = f"({y_base})+{y_offset}"
        else:
            y_expr = y_base

        # 5. 滚动效果
        if config.get("scroll_enabled"):
            diagonal = bool(config.get("diagonal", False))
            if diagonal:
                # 对角模式使用独立的固定运动参数，不再读取普通方向和速度。
                px_per_sec = 40.0
                x_expr = f"(mod((t*{px_per_sec})+{x_expr},w+text_w)-text_w)"
                y_expr = f"(mod((t*{px_per_sec})+{y_expr},h+text_h)-text_h)"
            else:
                direction = normalize_scroll_direction(
                    config.get("scroll_direction", "right")
                )
                if direction == "random":
                    direction = random.choice(["right", "left", "up", "down"])

                speed = config.get("scroll_speed", 1.0)
                if config.get("random_speed", False):
                    speed = random.uniform(0, speed)
                px_per_sec = 40.0 * speed

                # 常规单向滚动
                if direction == "right":
                    x_expr = f"(mod((t*{px_per_sec})+{x_expr},w+text_w)-text_w)"
                elif direction == "left":
                    x_expr = f"(w-mod((t*{px_per_sec}),w+text_w))"
                elif direction == "up":
                    y_expr = f"(h-mod((t*{px_per_sec}),h+text_h))"
                elif direction == "down":
                    y_expr = f"(mod((t*{px_per_sec})+{y_expr},h+text_h)-text_h)"

        # 6. 转义表达式中的逗号（避免与滤镜分隔符冲突）
        def _escape_expr(expr: str) -> str:
            return expr.replace(",", "\\,")

        x_expr_esc = _escape_expr(x_expr)
        y_expr_esc = _escape_expr(y_expr)

        # 7. 构建 drawtext 命令
        line_spacing = config.get("line_spacing", 10)
        drawtext = (
            f"drawtext=text='{escaped_text}'"
            f":fontsize={font_size}"
            f"{font_spec}"
            f":fontcolor={fontcolor_expr}"
            f":x={x_expr_esc}"
            f":y={y_expr_esc}"
            f":line_spacing={line_spacing}"
        )

        # 8. 描边
        if config.get("stroke_enabled"):
            stroke_width = config.get("stroke_width", 1)
            stroke_color = config.get("stroke_color", "#FFFFFF")
            stroke_hex = stroke_color.lstrip("#")
            drawtext += f":borderw={stroke_width}:bordercolor=0x{stroke_hex}@1.0"

        # 9. 阴影
        if config.get("shadow_enabled"):
            shadow_depth = config.get("shadow_depth", 2)
            shadow_color = config.get("shadow_color", "#000000")
            shadow_hex = shadow_color.lstrip("#")
            drawtext += f":shadowx={shadow_depth}:shadowy={shadow_depth}:shadowcolor=0x{shadow_hex}@0.6"

        # 10. 背景
        if config.get("bg_enabled"):
            bg_color = config.get("bg_color", "#808080")
            bg_opacity = config.get("bg_opacity", 0.8)
            bg_padding = max(0, int(config.get("bg_padding", 5)))
            bg_hex = bg_color.lstrip("#")
            bg_style = normalize_bg_style(config.get("bg_style", "default"))

            if bg_style == "fill":
                # 填充模式：背景框宽度设为视频宽度
                video_w = video_info.get("width", 1920)
                drawtext += f":box=1:boxcolor=0x{bg_hex}@{bg_opacity:.3f}:boxborderw={bg_padding}:boxw={video_w}"
            else:
                # 默认模式：背景框宽度等于文字宽度
                drawtext += f":box=1:boxcolor=0x{bg_hex}@{bg_opacity:.3f}:boxborderw={bg_padding}"

        # 11. 时序控制
        delay = config.get("delay", 0)
        duration = config.get("duration", 0)

        if loop:
            # 循环模式：持续显示直到视频结束
            if delay > 0:
                drawtext += f":enable=gte(t\\,{delay})"
        else:
            # 非循环模式：按延时和持续时间控制
            if delay > 0 or duration > 0:
                if delay > 0 and duration > 0:
                    drawtext += f":enable=between(t\\,{delay}\\,{delay + duration})"
                elif delay > 0:
                    drawtext += f":enable=gte(t\\,{delay})"
                elif duration > 0:
                    drawtext += f":enable=lt(t\\,{duration})"

        return drawtext

    def _build_line_display_filter(
        self, text: str, config: Dict, video_info: Dict, input_file: str
    ) -> str:
        """构建行显模式的多个 drawtext 滤镜（每行独立显示）"""
        # 拆分文本为多行（FFmpeg 格式的换行符是 \n）
        lines = text.split("\\n")
        lines = [line.strip() for line in lines if line.strip()]

        if not lines:
            return ""

        delay = config.get("delay", 0)
        interval = config.get("interval", 1)
        duration = config.get("duration", 5)
        loop = config.get("loop", False)

        filters = []

        # 为每行生成独立的 drawtext 滤镜
        for i, line in enumerate(lines):
            # 复制配置并修改文本内容
            line_config = config.copy()
            line_config["text_content"] = line
            line_config["line_display"] = False  # 避免递归

            # 计算该行的显示时间
            start_time = delay + i * (duration + interval)
            end_time = start_time + duration

            # 构建该行的基础滤镜（不含时序控制）
            line_filter = self._build_single_text_filter(
                line, line_config, video_info, False
            )

            if loop:
                # 循环模式：使用 mod() 实现周期循环
                total_cycle = len(lines) * (duration + interval)
                # 计算当前行在循环中的相对时间
                line_filter += f":enable='between(mod(t-{delay}\\,{total_cycle})\\,{i * (duration + interval)}\\,{i * (duration + interval) + duration})'"
            else:
                # 非循环模式：按绝对时间控制
                line_filter += f":enable=between(t\\,{start_time}\\,{end_time})"

            filters.append(line_filter)

        return ",".join(filters)

    def _get_text_content(self, config: Dict, input_file: str) -> str:
        """根据配置获取文本内容"""
        mode = normalize_text_source_mode(config.get("source_mode", "plain"))

        if mode == "filename":
            return self._get_filename_text(config, input_file)
        elif mode == "folder":
            return self._get_folder_text(config)
        elif mode == "plain":
            return self._get_direct_text(config, input_file)

        return ""

    def _get_filename_text(self, config: Dict, input_file: str) -> str:
        """从文件名提取文本"""
        if not input_file:
            return ""

        # 获取文件基础名称（不含路径和扩展名）
        basename = os.path.splitext(os.path.basename(input_file))[0]

        # 断行处理
        if config.get("break_by_punct"):
            symbols = config.get("punct_symbols", "。；：？！")
            include_punct = config.get("include_punct", False)

            # 按标点符号分割
            lines = []
            current_line = ""
            for char in basename:
                current_line += char
                if char in symbols:
                    if not include_punct:
                        current_line = current_line[:-1]  # 移除标点
                    lines.append(current_line.strip())
                    current_line = ""
            if current_line:
                lines.append(current_line.strip())

            basename = "\\n".join(lines)

        # 内容筛选
        filter_keyword = config.get("filter_keyword", "")
        if filter_keyword:
            filter_action = normalize_text_filter_action(
                config.get("filter_action", "keep")
            )
            filter_position = normalize_text_filter_position(
                config.get("filter_position", "before")
            )

            if filter_keyword in basename:
                idx = basename.find(filter_keyword)

                if filter_position == "before":
                    if filter_action == "remove":
                        basename = basename[idx + len(filter_keyword) :]
                    else:  # 保留
                        basename = basename[: idx + len(filter_keyword)]
                elif filter_position == "after":
                    if filter_action == "remove":
                        basename = basename[:idx]
                    else:  # 保留
                        basename = basename[idx:]
                elif filter_position == "between":
                    # 查找两个关键词之间的内容
                    if filter_action == "keep":
                        # 简化处理：保留第一次出现到第二次出现之间
                        second_idx = basename.find(
                            filter_keyword, idx + len(filter_keyword)
                        )
                        if second_idx != -1:
                            basename = basename[idx : second_idx + len(filter_keyword)]

        return basename

    def _get_folder_text(self, config: Dict) -> str:
        """从文件夹中的文本文件获取内容"""
        folder_path = config.get("folder_path", "")
        if not folder_path or not os.path.exists(folder_path):
            return ""

        # 获取所有 txt 文件
        import glob

        txt_files = glob.glob(os.path.join(folder_path, "*.txt"))
        if not txt_files:
            return ""

        # 随机或顺序选择
        if config.get("folder_random"):
            import random

            selected_file = random.choice(txt_files)
        else:
            # 顺序选择：按视频索引取模
            sorted_files = sorted(txt_files)
            selected_file = sorted_files[self._current_video_index % len(sorted_files)]

        # 读取文件内容
        try:
            with open(selected_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 单行抽取
            if config.get("single_line"):
                lines = [line.strip() for line in content.split("\n") if line.strip()]
                if lines:
                    import random

                    selected_line = random.choice(lines)

                    # 空格换行
                    if config.get("space_break"):
                        selected_line = selected_line.replace(" ", "\\n")

                    return selected_line

            return content.replace("\n", "\\n")
        except Exception as e:
            print(f"读取文本文件失败: {e}")
            return ""

    def _get_direct_text(self, config: Dict, input_file: str) -> str:
        """获取直接输入的文本（支持宏变量替换）"""
        text = config.get("text_content", "")

        # 替换 %{title} 宏变量为文件名（不含扩展名）
        if "%{title}" in text and input_file:
            basename = os.path.splitext(os.path.basename(input_file))[0]
            text = text.replace("%{title}", basename)

        # 替换换行符为 FFmpeg 格式
        return text.replace("\n", "\\n")

    def _prepare_watermarks_for_video(
        self, video_info: Dict, variant: int
    ) -> Dict[str, List[dict]]:
        """为当前视频准备水印配置（拆分图片/文字，解析资源）"""
        add_wm = self.config.get("add_watermark", {})
        if not add_wm.get("enabled"):
            return {"image": [], "text": []}

        results = {"image": [], "text": []}
        video_w = max(1, video_info.get("width", 1920))
        video_h = max(1, video_info.get("height", 1080))

        for wm in add_wm.get("watermarks", []):
            wm_type = wm.get("type")
            if wm_type == "image":
                source_path = self._select_watermark_source(wm, variant)
                if not source_path:
                    continue

                base_config = copy.deepcopy(wm)
                base_config["resolved_path"] = source_path
                base_config["target_size"] = self._compute_image_dimensions(
                    base_config, source_path, video_w, video_h
                )
                base_config["extra_offset"] = (0, 0)
                results["image"].append(base_config)

                if base_config.get("diagonal"):
                    results["image"].extend(
                        self._generate_diagonal_clones(base_config, video_w, video_h)
                    )
            elif wm_type == "text":
                results["text"].append(copy.deepcopy(wm))

        return results

    def _select_watermark_source(self, wm_config: dict, variant: int) -> str:
        """选择水印文件（支持随机/轮询）"""
        candidates = wm_config.get("file_candidates") or []
        if not candidates and wm_config.get("file_path"):
            candidates = [wm_config["file_path"]]

        normalized = [
            os.path.abspath(path)
            for path in candidates
            if path
            and os.path.exists(path)
            and Path(path).suffix.lower() in self.IMAGE_EXTS
        ]

        if not normalized:
            return ""

        if (
            wm_config.get("file_mode") == "folder"
            and wm_config.get("random_select")
            and len(normalized) > 1
        ):
            seed = (variant + wm_config.get("id", 0) * 131) ^ hash(normalized[0])
            rng = random.Random(seed)
            return normalized[rng.randint(0, len(normalized) - 1)]

        if wm_config.get("file_mode") == "folder" and len(normalized) > 1:
            index = variant % len(normalized)
            return normalized[index]

        return normalized[0]

    def _get_image_dimensions(self, path: str) -> Tuple[int, int]:
        """获取图片尺寸"""
        try:
            with Image.open(path) as img:
                return img.width, img.height
        except Exception:
            return (0, 0)

    def _compute_image_dimensions(
        self, wm_config: dict, source_path: str, video_w: int, video_h: int
    ) -> Tuple[int, int]:
        """根据配置计算目标尺寸"""
        base_w, base_h = self._get_image_dimensions(source_path)
        if base_w == 0 or base_h == 0:
            base_w, base_h = 100, 100

        if wm_config.get("custom_width") and wm_config.get("custom_height"):
            return int(wm_config["custom_width"]), int(wm_config["custom_height"])

        style = wm_config.get("style_config", {})
        size_cfg = style.get("size", {}) if style else {}
        mode = size_cfg.get("mode")

        if mode == "custom":
            width = size_cfg.get("width", base_w)
            height = size_cfg.get("height", base_h)
            return max(1, int(width)), max(1, int(height))

        if mode == "ratio":
            scale = size_cfg.get("scale", 100) / 100.0
            return max(1, int(base_w * scale)), max(1, int(base_h * scale))

        if mode == "video":
            ratio = size_cfg.get("video_ratio", 15) / 100.0
            ref = normalize_video_ref(size_cfg.get("video_ref", "height"))
            if ref == "height":
                target_h = video_h * ratio
                scale = target_h / max(1, base_h)
            elif ref == "width":
                target_w = video_w * ratio
                scale = target_w / max(1, base_w)
            else:  # 对角
                diag_video = (video_w**2 + video_h**2) ** 0.5
                diag_img = (base_w**2 + base_h**2) ** 0.5
                scale = (diag_video * ratio) / max(1, diag_img)
            return max(1, int(base_w * scale)), max(1, int(base_h * scale))

        return base_w, base_h

    def _generate_diagonal_clones(
        self, wm_config: dict, video_w: int, video_h: int
    ) -> List[dict]:
        """生成对角线铺设的额外水印"""
        clones = []
        step = max(100, min(video_w, video_h) // 4)
        for delta in range(-2, 3):
            if delta == 0:
                continue
            clone = copy.deepcopy(wm_config)
            clone["extra_offset"] = (delta * step, delta * step)
            clone["diagonal_clone"] = True
            clones.append(clone)
        return clones

    def _compute_overlay_position_expr(
        self, wm_config: dict, wm_w: int, wm_h: int, video_w: int, video_h: int
    ) -> Tuple[str, str]:
        """计算FFmpeg overlay位置表达式"""
        preset = normalize_text_position(wm_config.get("image_position", "top_right"))
        offset_x = wm_config.get("offset_x", 0)
        offset_y = wm_config.get("offset_y", 0)
        extra_x, extra_y = wm_config.get("extra_offset", (0, 0))
        custom_pos = wm_config.get("custom_position")

        def _signed(value: int) -> str:
            value = int(value)
            return f"+{value}" if value >= 0 else str(value)

        def _escape_filter_expr(expr: str) -> str:
            # 逗号在 filtergraph 中是分隔符，需要转义
            return expr.replace(",", "\\,")

        # 使用 W/H 动态表达式而非输入分辨率常量，避免裁剪后坐标错位
        if preset == "custom" and custom_pos:
            base_x_expr = str(int(custom_pos[0]) + int(extra_x))
            base_y_expr = str(int(custom_pos[1]) + int(extra_y))
        else:
            total_x = int(offset_x) + int(extra_x)
            total_y = int(offset_y) + int(extra_y)
            mapping = {
                "top_left": (str(total_x), str(total_y)),
                "top_right": (f"W-w{_signed(-total_x)}", str(total_y)),
                "bottom_left": (str(total_x), f"H-h{_signed(-total_y)}"),
                "bottom_right": (f"W-w{_signed(-total_x)}", f"H-h{_signed(-total_y)}"),
                "center": (f"(W-w)/2{_signed(total_x)}", f"(H-h)/2{_signed(total_y)}"),
            }
            base_x_expr, base_y_expr = mapping.get(preset, mapping["top_right"])

        # 统一夹紧到主画面边界，避免滤镜链中出现极端越界坐标
        base_x_expr = f"max(-{wm_w},min(W,{base_x_expr}))"
        base_y_expr = f"max(-{wm_h},min(H,{base_y_expr}))"

        style = wm_config.get("style_config", {})
        if wm_config.get("scroll"):
            speed = style.get("scroll_speed", 40)
            direction = style.get("scroll_direction", "horizontal")
            if direction == "vertical":
                x_expr = base_x_expr
                y_expr = f"(mod((t*{speed}) + {base_y_expr}, H + {wm_h}) - {wm_h})"
            else:
                x_expr = f"(mod((t*{speed}) + {base_x_expr}, W + {wm_w}) - {wm_w})"
                y_expr = base_y_expr
        else:
            x_expr = base_x_expr
            y_expr = base_y_expr

        return _escape_filter_expr(x_expr), _escape_filter_expr(y_expr)

    def _escape_ffmpeg_path(self, path: str) -> str:
        """转义FFmpeg路径（转换为正斜杠格式，兼容中文与盘符）"""
        # 统一使用正斜杠（Windows FFmpeg也支持）
        normalized = path.replace("\\", "/")
        # 转义冒号与单引号
        escaped = normalized.replace(":", "\\:").replace("'", "\\'")
        return escaped

    def _normalize_cmd_path(self, path: str) -> str:
        """规范化命令行路径，避免混用斜杠导致FFmpeg解析失败"""
        if not path:
            return path
        return path.replace("\\", "/")

    def _hex_to_ffmpeg_color(self, color: str, opacity: float) -> Tuple[str, float]:
        """转换为FFmpeg颜色表达式"""
        cleaned = (color or "#FFFFFF").lstrip("#")
        if len(cleaned) == 3:
            cleaned = "".join(ch * 2 for ch in cleaned)
        try:
            int(cleaned, 16)
        except ValueError:
            cleaned = "FFFFFF"
        alpha = max(0.0, min(1.0, opacity))
        return f"0x{cleaned.upper()}", alpha

    def _resolve_font_path(self, font_cfg: dict) -> Optional[str]:
        """解析字体路径（优先Windows注册表查询）"""
        family = font_cfg.get("family", "Microsoft YaHei")
        normalized_family = family.strip().lower().replace(" ", "")
        if normalized_family in self._font_cache:
            return self._font_cache[normalized_family]

        fonts_dir = Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts"

        # 步骤1：查询 Windows 注册表字体映射
        registry_path = self._query_registry_font(family)
        if registry_path and os.path.isfile(registry_path):
            self._font_cache[normalized_family] = registry_path
            return registry_path

        # 步骤2：常见字体映射（保留原逻辑作为回退）
        common_font_map = {
            "microsoftyahei": ["msyh.ttc", "msyhbd.ttc"],
            "微软雅黑": ["msyh.ttc", "msyhbd.ttc"],
            "yahei": ["msyh.ttc", "msyhbd.ttc"],
            "microsoftyaheiu": ["msyh.ttc", "msyhbd.ttc"],
            "microsoftjhenghei": ["msjh.ttc", "msjhbd.ttc"],
            "微软雅黑ui": ["msyh.ttc", "msyhbd.ttc"],
            "simsun": ["simsun.ttc", "simsunb.ttf"],
            "宋体": ["simsun.ttc", "simsunb.ttf"],
            "simhei": ["simhei.ttf"],
            "黑体": ["simhei.ttf"],
            "simkai": ["simkai.ttf"],
            "楷体": ["simkai.ttf"],
            "fangsong": ["simfang.ttf"],
            "仿宋": ["simfang.ttf"],
            "dengxian": ["deng.ttf", "dengb.ttf", "dengl.ttf"],
            "等线": ["deng.ttf", "dengb.ttf", "dengl.ttf"],
            "arial": ["arial.ttf"],
        }

        candidates = []
        mapped = common_font_map.get(normalized_family) or common_font_map.get(family)
        if mapped:
            candidates.extend([fonts_dir / name for name in mapped])

        if "yahei" in normalized_family or "微软雅黑" in family:
            candidates.append(fonts_dir / "msyh.ttc")
            candidates.append(fonts_dir / "msyhbd.ttc")

        name = family.replace(" ", "")
        candidates.append(fonts_dir / f"{name}.ttf")
        candidates.append(fonts_dir / f"{name}.ttc")
        candidates.append(fonts_dir / "arial.ttf")

        for path in candidates:
            if path.exists():
                self._font_cache[normalized_family] = str(path)
                return str(path)

        # 步骤3：扫描字体目录匹配字体族名（PIL 回退）
        try:
            font_files = (
                list(fonts_dir.glob("*.ttf"))
                + list(fonts_dir.glob("*.ttc"))
                + list(fonts_dir.glob("*.otf"))
            )
            for path in font_files:
                try:
                    font = ImageFont.truetype(str(path), 16)
                    name_tuple = font.getname()
                    if name_tuple and name_tuple[0].lower() == family.lower():
                        self._font_cache[normalized_family] = str(path)
                        return str(path)
                except Exception:
                    continue
        except Exception:
            pass

        self._font_cache[normalized_family] = None
        return None

    def _query_registry_font(self, family_name: str) -> Optional[str]:
        """从 Windows 注册表查询字体文件路径"""
        try:
            import winreg
        except ImportError:
            return None

        # 规范化字体族名（去空格、转小写）
        normalized = family_name.strip().lower().replace(" ", "")
        fonts_dir = Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts"

        # 尝试从 HKLM 和 HKCU 查询
        for root_key in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            try:
                key = winreg.OpenKey(
                    root_key, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
                )
                idx = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, idx)
                        idx += 1

                        # 移除 "(TrueType)", "(OpenType)" 等后缀
                        display_name = name
                        for suffix in [
                            " (TrueType)",
                            " (OpenType)",
                            " (TTC)",
                            " (OTF)",
                        ]:
                            display_name = display_name.replace(suffix, "")

                        # 规范化显示名并匹配
                        norm_display = display_name.strip().lower().replace(" ", "")
                        if normalized in norm_display or norm_display in normalized:
                            # value 可能是相对路径或绝对路径
                            if os.path.isabs(value):
                                font_path = value
                            else:
                                font_path = str(fonts_dir / value)

                            if os.path.isfile(font_path):
                                return font_path
                    except OSError:
                        break
                winreg.CloseKey(key)
            except Exception:
                continue

        return None

    def _build_drawtext_filter(
        self, wm_config: dict, input_file: str, duration: float
    ) -> str:
        """构建文字水印的drawtext滤镜"""
        text = wm_config.get("text_content", "").strip()
        if not text:
            return ""

        style = wm_config.get("style_config", {})
        dynamic = style.get("dynamic", {})
        text = self._compose_dynamic_text(text, dynamic, input_file)
        text = self._apply_text_arrange(text, style)

        escaped_text = (
            text.replace("\\", "\\\\\\\\").replace(":", "\\:").replace("'", "\\'")
        )
        style = wm_config.get("style_config", {})
        font_cfg = style.get("font", {})
        font_size = font_cfg.get("size", 36)

        # 优先使用明确的字体文件路径
        font_path = font_cfg.get("path")
        if font_path and os.path.isfile(font_path):
            font_spec = f":fontfile='{self._escape_ffmpeg_path(font_path)}'"
        else:
            # 回退到字体族名解析
            font_path = self._resolve_font_path(font_cfg)
            if font_path:
                font_spec = f":fontfile='{self._escape_ffmpeg_path(font_path)}'"
            else:
                font_spec = ""
                if font_cfg.get("family"):
                    family_escaped = font_cfg["family"].replace("'", "\\'")
                    font_spec = f":font='{family_escaped}'"

        font_color, opacity = self._hex_to_ffmpeg_color(
            style.get("color", "#FFFFFF"),
            wm_config.get("text_opacity", style.get("opacity", 1.0)),
        )
        fontcolor_expr = f"{font_color}@{opacity:.3f}"

        stroke_cfg = style.get("stroke", {})
        stroke_enabled = stroke_cfg.get("enabled", stroke_cfg.get("width", 0) > 0)
        stroke_color, _ = self._hex_to_ffmpeg_color(
            stroke_cfg.get("color", "#000000"), 1.0
        )
        stroke_width = int(stroke_cfg.get("width", 0)) if stroke_enabled else 0

        shadow_cfg = style.get("shadow", {})
        shadow_enabled = shadow_cfg.get(
            "enabled", (shadow_cfg.get("x", 0) != 0 or shadow_cfg.get("y", 0) != 0)
        )
        shadow_color, shadow_opacity = self._hex_to_ffmpeg_color(
            shadow_cfg.get("color", "#000000"), wm_config.get("text_opacity", 1.0) * 0.6
        )
        shadow_x = int(shadow_cfg.get("x", 0)) if shadow_enabled else 0
        shadow_y = int(shadow_cfg.get("y", 0)) if shadow_enabled else 0
        shadow_blur = int(shadow_cfg.get("blur", 0)) if shadow_enabled else 0

        background_cfg = style.get("background", {})
        background_enabled = background_cfg.get(
            "enabled", background_cfg.get("color") not in (None, "", "#00000000")
        )
        box_enabled = background_enabled and background_cfg.get("color") not in (
            None,
            "",
            "#00000000",
        )
        box_color, box_opacity = self._hex_to_ffmpeg_color(
            background_cfg.get("color", "#000000"),
            wm_config.get("text_opacity", 1.0) * 0.3,
        )

        position = normalize_text_position(
            wm_config.get("text_position", wm_config.get("position", "top_right"))
        )
        custom_pos = wm_config.get("custom_position")

        if position == "custom" and custom_pos:
            x_expr = str(int(custom_pos[0]))
            y_expr = str(int(custom_pos[1]))
        else:
            mapping = {
                "top_left": ("0", "0"),
                "top_right": ("W-text_w", "0"),
                "bottom_left": ("0", "H-text_h"),
                "bottom_right": ("W-text_w", "H-text_h"),
                "center": ("(W-text_w)/2", "(H-text_h)/2"),
            }
            x_expr, y_expr = mapping.get(position, mapping["top_right"])

        animation_cfg = style.get("animation", {})
        alpha_expr = None
        if normalize_text_animation_type(animation_cfg.get("type")) == "scroll":
            speed = float(animation_cfg.get("speed", 1.0))
            px_per_sec = max(10.0, 40.0 * speed)
            if normalize_text_arrange(style.get("arrange")) == "vertical":
                y_expr = f"(mod((t*{px_per_sec}) + {y_expr}, H+text_h)-text_h)"
            else:
                x_expr = f"(mod((t*{px_per_sec}) + {x_expr}, W+text_w)-text_w)"
        if normalize_text_animation_type(animation_cfg.get("type")) == "fade_in_out":
            speed = float(animation_cfg.get("speed", 1.0))
            fade_duration = max(0.5, min(3.0, 1.0 * speed))
            if duration and duration > 0:
                alpha_expr = f"if(lt(t\\,{fade_duration}),t/{fade_duration},if(gt(t\\,{duration - fade_duration}),({duration}-t)/{fade_duration},1))"
            else:
                alpha_expr = f"if(lt(t\\,{fade_duration}),t/{fade_duration},1)"

        def build_drawtext_for_color(
            color_expr: str,
            x_val: str,
            y_val: str,
            alpha_expr_override: Optional[str] = None,
        ):
            dt = (
                f"drawtext=text='{escaped_text}'"
                f":fontsize={font_size}"
                f"{font_spec}"
                f":fontcolor={color_expr}"
                f":x={x_val}"
                f":y={y_val}"
            )
            if alpha_expr_override:
                dt += f":alpha={alpha_expr_override}"
            return dt

        drawtext = (
            f"drawtext=text='{escaped_text}'"
            f":fontsize={font_size}"
            f"{font_spec}"
            f":fontcolor={fontcolor_expr}"
            f":x={x_expr}"
            f":y={y_expr}"
        )

        if stroke_width > 0:
            drawtext += f":borderw={stroke_width}:bordercolor={stroke_color}@1.0"

        shadow_filters: List[str] = []
        if shadow_enabled and (shadow_x != 0 or shadow_y != 0 or shadow_blur > 0):
            if shadow_blur > 0:
                step = max(1, shadow_blur // 2)
                offsets = [
                    (-step, -step),
                    (0, -step),
                    (step, -step),
                    (-step, 0),
                    (0, 0),
                    (step, 0),
                    (-step, step),
                    (0, step),
                    (step, step),
                ]
                per_alpha = max(0.05, shadow_opacity / len(offsets))
                shadow_color_expr = f"{shadow_color}@{per_alpha:.3f}"
                for dx, dy in offsets:
                    x_val = f"({x_expr}+{shadow_x + dx})"
                    y_val = f"({y_expr}+{shadow_y + dy})"
                    shadow_filters.append(
                        build_drawtext_for_color(shadow_color_expr, x_val, y_val)
                    )
            else:
                drawtext += f":shadowx={shadow_x}:shadowy={shadow_y}:shadowcolor={shadow_color}@{shadow_opacity:.3f}"

        if box_enabled:
            drawtext += f":box=1:boxcolor={box_color}@{box_opacity:.3f}:boxborderw={int(background_cfg.get('padding', 4))}"

        angle = style.get("angle", 0)
        if normalize_text_arrange(style.get("arrange")) == "slanted" and not angle:
            angle = -15
        if angle:
            drawtext += f":angle={angle * 3.1415926 / 180.0:.4f}"

        if alpha_expr:
            drawtext += f":alpha={alpha_expr}"

        if shadow_filters:
            return ",".join(shadow_filters + [drawtext])
        return drawtext

    def _compose_dynamic_text(
        self, base_text: str, dynamic_cfg: dict, input_file: str
    ) -> str:
        """拼接动态文字（时间戳/文件名/帧号）"""
        parts = [base_text] if base_text else []
        if dynamic_cfg.get("timestamp"):
            parts.append("%{localtime\\:%Y-%m-%d %H\\:%M\\:%S}")
        if dynamic_cfg.get("filename") and input_file:
            parts.append(os.path.basename(input_file))
        if dynamic_cfg.get("frame_number"):
            parts.append("%{n}")
        return " ".join(p for p in parts if p)

    def _apply_text_arrange(self, text: str, style: dict) -> str:
        """应用文字排列（水平/垂直/倾斜）"""
        arrange = normalize_text_arrange(style.get("arrange"))
        if arrange == "vertical":
            return "\\n".join(list(text))
        return text

    def _build_pip_graph(
        self, current_label: str, video_info: Dict, pip_bg_index: int = None
    ) -> Tuple[str, List[str]]:
        """构建画中画滤镜图"""
        pip_config = self.config.get("pip", {})
        if not pip_config.get("enabled"):
            return current_label, []

        commands: List[str] = []
        mode = pip_config.get("mode", "video")
        video_w = max(1, video_info.get("width", 1920))
        video_h = max(1, video_info.get("height", 1080))

        if mode == "video":
            # 视频模式：以自身视频为背景，添加边距和虚化
            margin_top = pip_config.get("video_margin_top", 50)
            margin_left = pip_config.get("video_margin_left", 50)
            blur_enabled = pip_config.get("video_blur_enabled", False)
            blur_strength = pip_config.get("video_blur_strength", 10)
            opacity = pip_config.get("video_opacity", 1.0)
            size_percent = pip_config.get("video_size_percent", 80)

            # 计算前景视频尺寸：优先按边距保证上下/左右一致
            if margin_top > 0 or margin_left > 0:
                fg_w = max(1, video_w - (margin_left * 2))
                fg_h = max(1, video_h - (margin_top * 2))
            else:
                fg_w = int(video_w * size_percent / 100)
                fg_h = int(video_h * size_percent / 100)

            # split生成背景和前景
            commands.append(f"{current_label}split[fg][bg]")

            # 背景处理
            if blur_enabled:
                # 背景虚化：scale到原尺寸后应用模糊
                commands.append(
                    f"[bg]scale={video_w}:{video_h},gblur=sigma={blur_strength}[bg_blurred]"
                )
                bg_label = "[bg_blurred]"
            else:
                commands.append(f"[bg]scale={video_w}:{video_h}[bg_scaled]")
                bg_label = "[bg_scaled]"

            # 前景处理：缩放+可选透明度
            fg_filter = f"[fg]scale={fg_w}:{fg_h}"
            if opacity < 1.0:
                fg_filter += f",format=rgba,colorchannelmixer=aa={opacity:.3f}"
            fg_filter += "[fg_scaled]"
            commands.append(fg_filter)

            # overlay叠加，考虑边距
            overlay_x = margin_left
            overlay_y = margin_top
            commands.append(
                f"{bg_label}[fg_scaled]overlay={overlay_x}:{overlay_y}[pip_out]"
            )
            current_label = "[pip_out]"

        elif mode == "background" and pip_bg_index is not None:
            # 背景模式：使用外部图片/视频作为背景
            bg_path = pip_config.get("background_path", "")
            if not bg_path or not os.path.exists(bg_path):
                return current_label, []

            offset_x = pip_config.get("background_offset_x", 0)
            offset_y = pip_config.get("background_offset_y", 0)
            opacity = pip_config.get("background_opacity", 1.0)
            size_percent = pip_config.get("background_size_percent", 60)

            # 计算前景视频尺寸
            fg_w = int(video_w * size_percent / 100)
            fg_h = int(video_h * size_percent / 100)

            # 背景处理：scale到视频尺寸
            commands.append(f"[{pip_bg_index}:v]scale={video_w}:{video_h}[bg]")

            # 前景处理：缩放主视频+可选透明度
            fg_filter = f"{current_label}scale={fg_w}:{fg_h}"
            if opacity < 1.0:
                fg_filter += f",format=rgba,colorchannelmixer=aa={opacity:.3f}"
            fg_filter += "[fg]"
            commands.append(fg_filter)

            # overlay叠加，居中+偏移
            overlay_x = f"(W-w)/2+{offset_x}"
            overlay_y = f"(H-h)/2+{offset_y}"
            commands.append(f"[bg][fg]overlay={overlay_x}:{overlay_y}[pip_out]")
            current_label = "[pip_out]"

        return current_label, commands

    def _build_image_watermark_graph(
        self, image_watermarks: List[dict], current_label: str, video_info: Dict
    ) -> Tuple[str, List[str]]:
        """构建图片水印的滤镜图"""
        commands: List[str] = []
        video_w = max(1, video_info.get("width", 1920))
        video_h = max(1, video_info.get("height", 1080))

        for idx, wm in enumerate(image_watermarks):
            wm_label = f"[wm{idx}]"
            escaped_path = self._escape_ffmpeg_path(wm.get("resolved_path", ""))
            target_w, target_h = wm.get("target_size", (100, 100))
            opacity = max(0.0, min(1.0, float(wm.get("opacity", 1.0))))

            movie_cmd = (
                f"movie='{escaped_path}',scale={target_w}:{target_h},format=rgba"
            )
            if opacity < 1.0:
                movie_cmd += f",colorchannelmixer=aa={opacity:.3f}"
            movie_cmd += wm_label
            commands.append(movie_cmd)

            x_expr, y_expr = self._compute_overlay_position_expr(
                wm, target_w, target_h, video_w, video_h
            )

            next_label = f"[overlay{idx}]"
            overlay_cmd = f"{current_label}{wm_label}overlay={x_expr}:{y_expr}:format=auto{next_label}"
            commands.append(overlay_cmd)
            current_label = next_label

        return current_label, commands

    def build_command(
        self, input_file: str, output_file: str, variant: int = 0, preview: bool = False
    ) -> List[str]:
        """
        构建完整的FFmpeg命令

        Args:
            input_file: 输入视频路径
            output_file: 输出视频路径
            variant: 变体索引(用于随机参数)
            preview: 是否为预览模式(已废弃,现在预览也处理完整视频)

        Returns:
            FFmpeg命令列表
        """
        # 保存当前处理的文件路径和索引（供文本过滤器使用）
        self._current_input_file = input_file
        self._current_video_index = variant  # 使用 variant 作为视频索引

        # 获取视频信息
        video_info = self.get_video_info(input_file)
        if not video_info:
            raise Exception(f"无法获取视频信息: {input_file}")

        # 检查视频编码兼容性
        try:
            validate_video_for_processing(video_info)
        except VideoCodecException as e:
            logger.error(f"视频编码不支持: {e.message}")
            raise Exception(
                f"视频编码不支持: {e.message}\n建议: "
                + "; ".join(e.details.get("suggestions", []))
            )

        # 检查是否需要加头尾/边框（优先处理）
        head_tail_config = self.config.get("add_head_tail", {})
        need_head_tail = (
            head_tail_config.get("head_enabled") and head_tail_config.get("head_file")
        ) or (
            head_tail_config.get("tail_enabled") and head_tail_config.get("tail_file")
        )
        need_border = head_tail_config.get("border_enabled") and head_tail_config.get(
            "border_file"
        )

        if need_head_tail or need_border:
            head_tail_cmd = self._build_add_head_tail_command(
                input_file, output_file, variant
            )
            if head_tail_cmd:
                print("使用加头尾/边框专用处理模式")
                return head_tail_cmd
            else:
                print("加头尾/边框处理失败，使用标准处理流程")

        # 检查是否启用分段变速（需要特殊处理）
        speed_config = self.config.get("speed", {})
        if speed_config.get("enabled") and speed_config.get("segment_enabled"):
            return self._build_segment_speed_command(
                input_file, output_file, video_info, variant
            )
        self._current_speed_value = self._resolve_speed_value(video_info, variant)

        codec, hwaccel, quality_param = self._get_video_codec_settings()

        # 构建命令
        cmd = [self.ffmpeg_path, "-y"]  # -y覆盖输出文件
        if hwaccel:
            cmd.extend(["-hwaccel", hwaccel])

        # 输入文件
        cmd.extend(["-i", self._normalize_cmd_path(input_file)])

        # 背景音乐输入
        bgm_file, bgm_enabled = self._add_background_audio_input(cmd, variant)
        bgm_input_index = 1 if bgm_file else None

        # 画中画背景输入
        pip_bg_index = None
        pip_config = self.config.get("pip", {})
        if pip_config.get("enabled") and pip_config.get("mode") == "background":
            bg_path = pip_config.get("background_path", "")
            if bg_path and os.path.exists(bg_path):
                # 判断是图片还是视频
                ext = os.path.splitext(bg_path)[1].lower()
                bg_path_cmd = self._normalize_cmd_path(bg_path)
                if ext in self.IMAGE_EXTS:
                    # 图片需要循环输入
                    cmd.extend(["-loop", "1", "-i", bg_path_cmd])
                else:
                    # 视频直接输入
                    cmd.extend(["-i", bg_path_cmd])
                # 计算输入索引（0是主视频，1是bgm（如果有），接下来是画中画背景）
                pip_bg_index = 1 if not bgm_file else 2

        # 去头尾/截取处理（使用 -ss 和 -t 参数）
        trim_config = self.config.get("trim", {})
        if trim_config.get("enabled"):
            mode = normalize_trim_mode(trim_config.get("mode", "trim_edges"))
            video_duration = video_info.get("duration", 0)

            if mode == "trim_edges":
                # 去头尾模式
                head = trim_config.get("head", 0)
                tail = trim_config.get("tail", 0)

                if head > 0:
                    cmd.extend(["-ss", str(head)])

                if video_duration > 0:
                    duration = video_duration - head - tail
                    if duration > 0:
                        cmd.extend(["-t", str(duration)])
                    else:
                        print(f"警告：去头尾后时长为 {duration}，跳过裁剪")
                else:
                    if tail > 0:
                        print("警告：无法获取视频时长，去尾参数将被忽略")
            else:
                # 截取模式
                start = trim_config.get("start", 0)
                duration = trim_config.get("duration", 0)

                if start > 0:
                    cmd.extend(["-ss", str(start)])

                if duration > 0:
                    cmd.extend(["-t", str(duration)])

        # 预览模式不再限制时长,处理完整视频
        # if preview:
        #     cmd.extend(['-t', '10'])

        # 构建滤镜链与水印
        base_filters = self.build_filter_complex(video_info, variant)
        watermark_sets = self._prepare_watermarks_for_video(video_info, variant)
        drawtext_filters = [
            self._build_drawtext_filter(
                text_wm, input_file, float(video_info.get("duration", 0) or 0)
            )
            for text_wm in watermark_sets["text"]
        ]
        drawtext_filters = [f for f in drawtext_filters if f]

        image_watermarks = watermark_sets["image"]
        pip_enabled = pip_config.get("enabled", False)
        use_filter_complex = len(image_watermarks) > 0 or pip_enabled

        filters = (
            base_filters if use_filter_complex else (base_filters + drawtext_filters)
        )
        base_chain = ",".join(f for f in filters if f)

        filter_complex_cmd = []
        current_label = "[0:v]"
        final_video_label = None

        if base_chain:
            if use_filter_complex:
                filter_complex_cmd.append(f"{current_label}{base_chain}[base0]")
                current_label = "[base0]"
            else:
                cmd.extend(["-vf", base_chain])

        # 画中画处理（在base_filters之后、水印之前）
        if use_filter_complex and pip_enabled:
            pip_label, pip_cmds = self._build_pip_graph(
                current_label, video_info, pip_bg_index
            )
            if pip_cmds:
                filter_complex_cmd.extend(pip_cmds)
                current_label = pip_label

        delay_applied_in_filter_complex = False
        audio_processed = False
        if use_filter_complex:
            final_video_label, overlay_cmds = self._build_image_watermark_graph(
                image_watermarks, current_label, video_info
            )
            filter_complex_cmd.extend(overlay_cmds)
            current_label = final_video_label  # 更新为图片水印输出标签，确保文字水印在其之后链式连接

            for idx, drawtext in enumerate(drawtext_filters):
                next_label = f"[text_overlay{idx}]"
                filter_complex_cmd.append(f"{current_label}{drawtext} {next_label}")
                current_label = next_label

            filter_graph = ";".join(filter_complex_cmd)

            # 如果有背景音乐，添加音频混音滤镜
            if bgm_input_index is not None:
                audio_mix_filter = self._build_audio_mix_filter(
                    bgm_input_index, video_info
                )
                filter_graph += ";" + audio_mix_filter
                audio_map_label = "[aout]"
                audio_processed = True
            else:
                audio_map_label = "0:a?"

            # 延时设置（整体后移）- filter_complex 内处理音频
            delay_config = self.config.get("more_effects", {})
            delay_enabled = delay_config.get("delay_enabled")
            delay_time = float(delay_config.get("delay_time", 0.0))
            has_audio = video_info.get("has_audio", True)
            if delay_enabled and delay_time > 0 and has_audio:
                delay_ms = int(delay_time * 1000)
                if audio_map_label == "[aout]":
                    filter_graph += f";[aout]adelay={delay_ms}|{delay_ms}[adelay]"
                    audio_map_label = "[adelay]"
                else:
                    filter_graph += f";[0:a]adelay={delay_ms}|{delay_ms}[adelay]"
                    audio_map_label = "[adelay]"
                delay_applied_in_filter_complex = True
                audio_processed = True

            frame_extract_audio_filters = self._build_frame_extract_audio_filters(
                video_info
            )
            if frame_extract_audio_filters and bgm_input_index is None:
                audio_source = (
                    audio_map_label if audio_map_label != "0:a?" else "[0:a]"
                )
                filter_graph += (
                    f";{audio_source}{','.join(frame_extract_audio_filters)}"
                    "[aextract]"
                )
                audio_map_label = "[aextract]"
                audio_processed = True

            cmd.extend(["-filter_complex", filter_graph])
            final_video_label = current_label
            cmd.extend(["-map", final_video_label])
            cmd.extend(["-map", audio_map_label])

        # 无filter_complex但有背景音乐时，单独构建音频混音滤镜
        if not use_filter_complex and bgm_input_index is not None:
            audio_mix_filter = self._build_audio_mix_filter(bgm_input_index, video_info)
            # 延时设置（整体后移）- 音频混音后处理
            delay_config = self.config.get("more_effects", {})
            delay_enabled = delay_config.get("delay_enabled")
            delay_time = float(delay_config.get("delay_time", 0.0))
            has_audio = video_info.get("has_audio", True)
            if delay_enabled and delay_time > 0 and has_audio:
                delay_ms = int(delay_time * 1000)
                audio_mix_filter += f";[aout]adelay={delay_ms}|{delay_ms}[adelay]"
                audio_map_label = "[adelay]"
                delay_applied_in_filter_complex = True
            else:
                audio_map_label = "[aout]"
            audio_processed = True
            cmd.extend(["-filter_complex", audio_mix_filter])
            cmd.extend(["-map", "0:v"])
            cmd.extend(["-map", audio_map_label])

        # 音频变速处理（非分段）
        audio_filters = []
        delay_config = self.config.get("more_effects", {})
        delay_enabled = delay_config.get("delay_enabled")
        delay_time = float(delay_config.get("delay_time", 0.0))
        has_audio = video_info.get("has_audio", True)
        if (
            delay_enabled
            and delay_time > 0
            and has_audio
            and not delay_applied_in_filter_complex
        ):
            delay_ms = int(delay_time * 1000)
            audio_filters.append(f"adelay={delay_ms}|{delay_ms}")

        if not audio_processed:
            audio_filters.extend(self._build_frame_extract_audio_filters(video_info))

        speed_config = self.config.get("speed", {})
        if speed_config.get("enabled") and not speed_config.get("segment_enabled"):
            speed_value = getattr(self, "_current_speed_value", 1.0)
            audio_filters.extend(
                self._build_audio_speed_filters(
                    speed_value, bool(speed_config.get("pitch_enabled"))
                )
            )

        if audio_filters:
            cmd.extend(["-af", ",".join(audio_filters)])
            audio_processed = True

        # 帧率调整
        fps_config = self.config.get("fps", {})
        if fps_config.get("enabled"):
            fps = random.uniform(fps_config["min"], fps_config["max"])
            cmd.extend(["-r", f"{fps:.1f}"])

        # 码率调整（优先级：去水印配置 > 普通码率配置 > 默认配置）
        watermark_config = self.config.get("remove_watermark", {})
        if (
            watermark_config.get("enabled")
            and watermark_config.get("method") == "ffmpeg"
        ):
            # 使用去水印的高质量配置
            crf = watermark_config.get("ffmpeg_crf", 18)
            preset = watermark_config.get("ffmpeg_preset", "medium")
            self._append_quality_params(cmd, codec, quality_param, crf, preset=preset)
        else:
            # 使用普通码率配置
            bitrate_config = self.config.get("bitrate", {})
            if bitrate_config.get("enabled"):
                if bitrate_config.get("mode_dynamic"):
                    # 动态码率(质量模式)
                    crf = bitrate_config["dynamic_value"]
                    self._append_quality_params(cmd, codec, quality_param, crf)
                else:
                    # 定值码率
                    bitrate_value = bitrate_config["fixed_value"]
                    self._append_video_codec(cmd, codec)
                    if str(bitrate_value) in ("保持原值", "keep_original"):
                        # 使用原视频码率
                        if video_info.get("bit_rate"):
                            bitrate_kbps = video_info["bit_rate"] // 1000
                            cmd.extend(["-b:v", f"{bitrate_kbps}k"])
                    else:
                        # 应用倍率随机
                        base_bitrate = int(bitrate_value)
                        ratio = random.uniform(
                            bitrate_config["ratio_min"], bitrate_config["ratio_max"]
                        )
                        final_bitrate = int(base_bitrate * ratio)
                        cmd.extend(["-b:v", f"{final_bitrate}k"])
            else:
                # 默认使用合理的编码参数
                self._append_quality_params(cmd, codec, quality_param, 23)

        # 强制输出标准像素格式，确保播放兼容性
        # lut3d等滤镜会将像素格式提升为浮点/高位深(如gbrpf32le)，
        # 导致libx264编码为Hi10P/High 4:4:4 profile，Windows内置播放器无法解码
        cmd.extend(["-pix_fmt", "yuv420p"])

        # 音频处理（仅在未做音频滤镜时允许 copy）
        if (
            watermark_config.get("enabled")
            and watermark_config.get("method") == "ffmpeg"
            and not audio_processed
        ):
            cmd.extend(["-c:a", "copy"])  # 音频无损复制
        else:
            cmd.extend(["-c:a", "aac", "-b:a", "128k"])

        # 输出文件
        cmd.append(self._normalize_cmd_path(output_file))

        return cmd

    def _build_segment_speed_command(
        self, input_file: str, output_file: str, video_info: Dict, variant: int
    ) -> List[str]:
        """构建分段变速的FFmpeg命令

        注意：分段变速走独立处理路径，不支持同时应用其他复杂滤镜（如去水印、裁剪等）。
        如需同时使用，请先应用其他滤镜，再对结果进行分段变速。
        """
        print("⚠️  注意：分段变速模式下，其他滤镜（去水印、裁剪、画面调整等）将不生效")

        speed_config = self.config.get("speed", {})
        codec, hwaccel, quality_param = self._get_video_codec_settings()
        segment_duration = speed_config.get("segment_duration", 10)
        video_duration = video_info.get("duration", 0)
        if getattr(self, "preview_mode", False):
            preview_duration = getattr(self, "preview_duration", None)
            if preview_duration and preview_duration > 0:
                video_duration = min(video_duration, preview_duration)

        if video_duration <= 0:
            raise Exception("无法获取视频时长")

        # 计算分段数量和每段时长
        num_segments = int(video_duration / segment_duration) + 1
        segments = []

        random.seed(variant)

        for i in range(num_segments):
            start = i * segment_duration
            end = min((i + 1) * segment_duration, video_duration)
            duration = end - start

            if duration <= 0:
                break

            # 从 min~max 范围随机生成速度
            speed_min = speed_config.get("min", 1.0)
            speed_max = speed_config.get("max", 1.0)
            speed = random.uniform(speed_min, speed_max)
            segments.append(
                {"start": start, "end": end, "duration": duration, "speed": speed}
            )

        # 计算期望总时长
        expected_duration = sum(seg["duration"] / seg["speed"] for seg in segments)

        # 最短时长保护
        if speed_config.get("min_duration_enabled"):
            min_duration = speed_config.get("min_duration", 10)
            if expected_duration < min_duration:
                # 需要降低所有段的速度
                scale_factor = expected_duration / min_duration
                for seg in segments:
                    seg["speed"] *= scale_factor
                    seg["speed"] = max(0.5, min(4.0, seg["speed"]))
                print(f"分段变速保护: 调整速度以满足最短时长 {min_duration}秒")

        # 构建命令
        cmd = [self.ffmpeg_path, "-y"]
        if hwaccel:
            cmd.extend(["-hwaccel", hwaccel])
        cmd.extend(["-i", self._normalize_cmd_path(input_file)])

        # 构建 filter_complex
        filter_parts = []
        pitch_enabled = speed_config.get("pitch_enabled", False)

        # 视频滤镜：每段 trim + setpts
        for i, seg in enumerate(segments):
            # 视频部分
            v_filter = f"[0:v]trim=start={seg['start']:.2f}:end={seg['end']:.2f},setpts={1.0 / seg['speed']:.4f}*PTS[v{i}]"
            filter_parts.append(v_filter)

            # 音频部分
            if pitch_enabled:
                # 变调
                a_filter = f"[0:a]atrim=start={seg['start']:.2f}:end={seg['end']:.2f},asetrate=44100*{seg['speed']:.4f},aresample=44100[a{i}]"
            else:
                # 不变调：使用 atempo
                atempo_chain = []
                current_speed = seg["speed"]

                # atempo 限制在 0.5-2.0，需要级联
                while current_speed > 2.0:
                    atempo_chain.append("atempo=2.0")
                    current_speed /= 2.0
                while current_speed < 0.5:
                    atempo_chain.append("atempo=0.5")
                    current_speed /= 0.5
                if abs(current_speed - 1.0) > 0.01:
                    atempo_chain.append(f"atempo={current_speed:.4f}")

                atempo_str = ",".join(atempo_chain) if atempo_chain else ""
                if atempo_str:
                    a_filter = f"[0:a]atrim=start={seg['start']:.2f}:end={seg['end']:.2f},{atempo_str},asetpts=PTS-STARTPTS[a{i}]"
                else:
                    a_filter = f"[0:a]atrim=start={seg['start']:.2f}:end={seg['end']:.2f},asetpts=PTS-STARTPTS[a{i}]"

            filter_parts.append(a_filter)

        # concat 所有段（按 v,a 成对输入）
        concat_inputs = "".join([f"[v{i}][a{i}]" for i in range(len(segments))])
        concat_filter = f"{concat_inputs}concat=n={len(segments)}:v=1:a=1[vout][aout]"
        filter_parts.append(concat_filter)

        # 添加 filter_complex
        filter_graph = ";".join(filter_parts)
        cmd.extend(["-filter_complex", filter_graph])

        # 映射输出
        cmd.extend(["-map", "[vout]", "-map", "[aout]"])

        # 编码参数
        self._append_quality_params(cmd, codec, quality_param, 23, preset="medium")
        cmd.extend(["-c:a", "aac", "-b:a", "128k"])

        # 输出文件
        cmd.append(self._normalize_cmd_path(output_file))

        return cmd

    def _select_media_file(
        self, path: str, mode: str, random_select: bool, variant: int
    ) -> Optional[str]:
        """
        根据模式选择媒体文件

        Args:
            path: 文件路径或目录路径
            mode: 'file' 或 'folder'
            random_select: 是否随机选择
            variant: 变体索引（用于确定性随机）

        Returns:
            选中的文件路径，如果无效则返回None
        """
        if not path or not os.path.exists(path):
            return None

        if mode == "file":
            # 文件模式：直接返回路径
            if os.path.isfile(path):
                return path
            return None

        elif mode == "folder":
            # 目录模式：从目录中选择文件
            if not os.path.isdir(path):
                return None

            # 获取所有视频文件
            video_files = []
            for file in os.listdir(path):
                file_path = os.path.join(path, file)
                if os.path.isfile(file_path):
                    ext = os.path.splitext(file)[1].lower()
                    if ext in {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".flv"}:
                        video_files.append(file_path)

            if not video_files:
                print(f"警告：目录 {path} 中没有找到视频文件")
                return None

            # 根据random_select决定选择方式
            if random_select:
                # 随机选择（使用variant作为种子保证可重复性）
                random.seed(variant)
                return random.choice(video_files)
            else:
                # 顺序选择
                return sorted(video_files)[variant % len(video_files)]

        return None

    def _format_concat_file_path(self, path: str) -> str:
        """返回 FFmpeg concat demuxer 可稳定读取的绝对 file URI。"""
        resolved = Path(path).resolve().as_posix()
        file_uri = f"file:{resolved}"
        return file_uri.replace("'", "'\\''")

    def _build_head_tail_concat_command(
        self, input_file: str, output_file: str, variant: int
    ) -> Optional[List[str]]:
        """
        构建加头尾的concat命令

        Args:
            input_file: 主视频文件路径
            output_file: 输出文件路径
            variant: 变体索引

        Returns:
            FFmpeg命令列表，如果不需要拼接则返回None
        """
        config = self.config.get("add_head_tail", {})
        codec, hwaccel, quality_param = self._get_video_codec_settings()

        # 收集所有视频片段
        segments = []

        # 片头
        if config.get("head_enabled") and config.get("head_file"):
            head_file = self._select_media_file(
                config["head_file"],
                config.get("head_mode", "file"),
                config.get("head_random", False),
                variant,
            )
            if head_file and os.path.exists(head_file):
                segments.append(head_file)
                print(f"添加片头: {head_file}")

        # 主视频
        segments.append(input_file)

        # 片尾
        if config.get("tail_enabled") and config.get("tail_file"):
            tail_file = self._select_media_file(
                config["tail_file"],
                config.get("tail_mode", "file"),
                config.get("tail_random", False),
                variant,
            )
            if tail_file and os.path.exists(tail_file):
                segments.append(tail_file)
                print(f"添加片尾: {tail_file}")

        # 如果只有主视频，不需要拼接
        if len(segments) == 1:
            return None

        # 使用concat demuxer拼接视频
        # 创建临时文件列表
        import tempfile

        concat_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        )
        try:
            concat_file.write("ffconcat version 1.0\n")
            for segment in segments:
                concat_file.write(f"file '{self._format_concat_file_path(segment)}'\n")
            concat_file.close()
            self._temp_files.append(concat_file.name)

            # 构建FFmpeg命令
            cmd = [self.ffmpeg_path, "-y"]
            if hwaccel:
                cmd.extend(["-hwaccel", hwaccel])
            cmd.extend(
                [
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    self._normalize_cmd_path(concat_file.name),
                ]
            )

            # 添加编码参数
            self._append_quality_params(cmd, codec, quality_param, 23, preset="medium")
            cmd.extend(["-c:a", "aac", "-b:a", "128k"])

            # 输出文件
            cmd.append(self._normalize_cmd_path(output_file))

            return cmd
        except Exception as e:
            print(f"创建concat文件失败: {e}")
            if os.path.exists(concat_file.name):
                os.remove(concat_file.name)
            return None

    def _build_border_overlay_filter(
        self, video_info: Dict, variant: int
    ) -> Tuple[List[str], str]:
        """
        构建边框叠加滤镜

        Args:
            video_info: 视频信息字典
            variant: 变体索引

        Returns:
            (额外输入列表, 滤镜字符串) 的元组
        """
        config = self.config.get("add_head_tail", {})

        if not config.get("border_enabled") or not config.get("border_file"):
            return ([], "")

        # 选择边框文件
        border_file = self._select_media_file(
            config["border_file"],
            config.get("border_mode", "file"),
            config.get("border_random", False),
            variant,
        )

        if not border_file or not os.path.exists(border_file):
            print(f"警告：边框文件不存在: {border_file}")
            return ([], "")

        # 检查边框文件格式
        ext = os.path.splitext(border_file)[1].lower()
        if ext not in {".png", ".jpg", ".jpeg", ".bmp", ".gif"}:
            print(f"警告：不支持的边框格式: {ext}")
            return ([], "")

        print(f"使用边框: {border_file}")

        # 构建边框处理滤镜链
        video_w = video_info.get("width", 1920)
        video_h = video_info.get("height", 1080)

        # 边框配置
        opacity_min = config.get(
            "border_opacity_min", config.get("border_opacity", 1.0)
        )
        opacity_max = config.get("border_opacity_max", opacity_min)
        margin_x = config.get("border_margin_x", 0)
        margin_y = config.get("border_margin_y", 0)
        remove_bg = config.get("border_remove_bg", False)
        bg_method = config.get("border_bg_method", "video_color")
        bg_similarity = config.get("border_bg_similarity", 0.10)
        bg_blend = config.get("border_bg_blend", 0.30)

        if opacity_min > opacity_max:
            opacity_min, opacity_max = opacity_max, opacity_min
        if opacity_min == opacity_max:
            opacity = opacity_min
        else:
            random.seed(variant)
            opacity = random.uniform(opacity_min, opacity_max)

        # 转义边框文件路径
        escaped_border = self._escape_ffmpeg_path(border_file)

        # 构建滤镜
        border_filters = []

        # 1. 加载边框并缩放到视频尺寸
        border_filters.append(f"movie='{escaped_border}'")
        border_filters.append(f"scale={video_w}:{video_h}")
        border_filters.append("format=rgba")

        # 2. 背景色消除（如果启用）
        if remove_bg:
            if bg_method == "specified":
                # 使用指定颜色
                bg_color = config.get("border_bg_color", "#00FF00")
                # 转换十六进制颜色到FFmpeg格式
                bg_color = bg_color.lstrip("#")
                border_filters.append(
                    f"chromakey=0x{bg_color}:{bg_similarity:.2f}:{bg_blend:.2f}"
                )
            else:
                # 使用视频背景色（取色点方法）
                # 注意：这个方法比较复杂，需要先提取视频帧，这里简化处理
                # 默认使用绿色作为背景色
                border_filters.append(
                    f"chromakey=0x00FF00:{bg_similarity:.2f}:{bg_blend:.2f}"
                )

        # 3. 透明度调整
        if opacity < 1.0:
            border_filters.append(f"colorchannelmixer=aa={opacity:.3f}")

        border_filters.append("[border]")

        # 构建overlay滤镜
        overlay_x = margin_x
        overlay_y = margin_y
        overlay_filter = f"overlay={overlay_x}:{overlay_y}"

        # 完整的滤镜链
        filter_chain = ",".join(border_filters[:-1]) + border_filters[-1]

        # 返回边框文件路径（作为额外输入）和滤镜
        return (
            ["-i", self._normalize_cmd_path(border_file)],
            filter_chain + ";" + overlay_filter,
        )

    def process_video(
        self,
        input_file: str,
        output_file: str,
        variant: int = 0,
        progress_callback=None,
        should_stop=None,
    ) -> bool:
        """
        处理视频

        Args:
            input_file: 输入视频路径
            output_file: 输出视频路径
            variant: 变体索引
            progress_callback: 进度回调函数 callback(percent, message)

        Returns:
            是否成功
        """
        try:
            self.last_process_error = ""
            # 检查去水印配置
            watermark_config = self.config.get("remove_watermark", {})
            temp_file = None  # 初始化临时文件变量

            if watermark_config.get("enabled"):
                method = watermark_config.get("method", "ffmpeg")

                # 如果使用delogo方法，先进行单独处理，然后再应用其他效果
                # FFmpeg方法通过滤镜链处理，无需预处理
                if method in ["multidelogo"]:
                    # 创建临时文件用于去水印后的视频
                    temp_file = tempfile.NamedTemporaryFile(
                        suffix=".mp4", delete=False
                    ).name

                    # 执行去水印处理
                    success = self._process_watermark_removal(
                        input_file,
                        temp_file,
                        method,
                        watermark_config,
                        progress_callback,
                    )

                    if not success:
                        # 去水印失败，删除临时文件
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                        print("去水印处理失败，将继续使用原视频")
                        temp_file = None

                    # 使用去水印后的视频作为输入，继续处理其他效果
                    input_file_for_effects = temp_file if temp_file else input_file
                else:
                    # FFmpeg方法通过滤镜链处理，无需预处理
                    input_file_for_effects = input_file
            else:
                input_file_for_effects = input_file

            # 获取视频总时长（用于计算进度百分比）
            _progress_video_info = self.get_video_info(input_file_for_effects)
            if _progress_video_info:
                self.config["_current_video_info"] = _progress_video_info

            total_duration = (
                _progress_video_info.get("duration", 0) if _progress_video_info else 0
            )

            # 构建FFmpeg命令（包括FFmpeg去水印滤镜和其他效果）
            cmd = self.build_command(
                input_file_for_effects, output_file, variant, preview=False
            )

            # 打印命令(用于调试)
            print(f"FFmpeg命令: {' '.join(cmd)}")

            # 执行命令
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding="utf-8",
                errors="ignore",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            # 累积stderr输出（修复错误输出为空的问题）
            stderr_lines = []
            stop_requested = False

            def terminate_process():
                try:
                    process.terminate()
                except Exception:
                    pass
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    try:
                        process.kill()
                    except Exception:
                        pass

            def read_stderr():
                if not process.stderr:
                    return
                for line in process.stderr:
                    stderr_lines.append(line)
                    if progress_callback and "time=" in line:
                        try:
                            time_str = line.split("time=")[1].split()[0]
                            if total_duration > 0:
                                # 解析 HH:MM:SS.ms 为秒数
                                parts = time_str.split(":")
                                current_seconds = (
                                    float(parts[0]) * 3600
                                    + float(parts[1]) * 60
                                    + float(parts[2])
                                )
                                # 计算百分比，上限99（100留给完成时设置）
                                percent = min(
                                    99, int(current_seconds / total_duration * 100)
                                )
                                progress_callback(percent, f"处理中... {time_str}")
                            else:
                                # 无法获取总时长时，仅显示时间文字
                                progress_callback(0, f"处理中... {time_str}")
                        except:
                            pass

            import threading

            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            stderr_thread.start()

            # 等待完成或被停止
            while True:
                if should_stop and should_stop():
                    stop_requested = True
                    terminate_process()
                    break
                if process.poll() is not None:
                    break
                time.sleep(0.2)

            try:
                returncode = process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                terminate_process()
                returncode = process.wait()

            if stderr_thread.is_alive():
                stderr_thread.join(timeout=1)

            # 清理临时文件
            if (
                temp_file is not None
                and temp_file != input_file
                and os.path.exists(temp_file)
            ):
                os.remove(temp_file)

            # 清理concat临时文件
            for temp_path in list(self._temp_files):
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
            self._temp_files = []

            if stop_requested:
                if progress_callback:
                    progress_callback(0, "已停止")
                self.last_process_error = "用户停止处理"
                return False

            if returncode == 0:
                if progress_callback:
                    progress_callback(100, "处理完成")
                return True
            else:
                # 兜底读取剩余stderr，避免丢失错误信息
                if process.stderr:
                    try:
                        remaining = process.stderr.read()
                        if remaining:
                            stderr_lines.append(remaining)
                    except Exception:
                        pass
                error_output = "".join(stderr_lines).strip()
                if error_output:
                    print(f"FFmpeg错误: {error_output}")
                    self.last_process_error = (
                        f"FFmpeg处理失败，返回码 {returncode}\n\n{error_output[-4000:]}"
                    )
                else:
                    print(f"FFmpeg错误: 返回码 {returncode}，无stderr输出")
                    self.last_process_error = f"FFmpeg处理失败，返回码 {returncode}，无stderr输出"
                return False

        except Exception as e:
            print(f"处理视频失败: {e}")
            self.last_process_error = str(e)
            return False

    def _process_watermark_removal(
        self,
        input_file: str,
        output_file: str,
        method: str,
        config: Dict,
        progress_callback=None,
    ) -> bool:
        """
        执行去水印处理（仅支持FFmpeg DELOGO方法）

        Args:
            input_file: 输入视频
            output_file: 输出视频
            method: 处理方法 (ffmpeg/multidelogo)
            config: 去水印配置
            progress_callback: 进度回调

        Returns:
            是否成功
        """
        try:
            # 只支持FFmpeg DELOGO方法
            if method in ["ffmpeg", "multidelogo"]:
                return self._process_watermark_delogo(
                    input_file, output_file, config, progress_callback
                )
            else:
                print(f"不支持的去水印方法: {method}，仅支持FFmpeg DELOGO")
                return False
        except Exception as e:
            print(f"去水印处理失败: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _process_watermark_delogo(
        self, input_file: str, output_file: str, config: Dict, progress_callback=None
    ) -> bool:
        """使用FFmpeg DELOGO去水印"""
        try:
            print("🎯 使用FFmpeg DELOGO去水印...")

            regions = config.get("regions", [])
            if not regions:
                print("未指定水印区域")
                return False

            import subprocess

            # 获取视频信息用于边界夹紧
            video_info = self.get_video_info(input_file)
            video_width = video_info.get("width", 1920) if video_info else 1920
            video_height = video_info.get("height", 1080) if video_info else 1080
            print(f"视频分辨率: {video_width}x{video_height}")

            # 构建delogo滤镜链（支持多个区域）
            delogo_filters = []
            for i, (x, y, w, h) in enumerate(regions):
                # 边界夹紧：确保区域不超出画面范围
                x = max(0, min(x, video_width - 1))
                y = max(0, min(y, video_height - 1))
                # delogo 对右/下边界敏感，确保不贴边
                w = min(w, video_width - x - 1)
                h = min(h, video_height - y - 1)

                # 跳过无效区域
                if w <= 0 or h <= 0:
                    print(
                        f"警告: 跳过无效去水印区域 {i + 1} (x={x}, y={y}, w={w}, h={h})"
                    )
                    continue

                delogo_filters.append(f"delogo=x={x}:y={y}:w={w}:h={h}")
                print(f"添加去水印区域 {i + 1}: x={x}, y={y}, w={w}, h={h}")

            # 组合所有滤镜
            vf_filter = ",".join(delogo_filters)

            cmd = [
                "ffmpeg",
                "-i",
                input_file,
                "-vf",
                vf_filter,
                "-c:a",
                "copy",
                "-y",
                output_file,
            ]

            # 获取视频总时长用于实时进度计算
            delogo_duration = video_info.get("duration", 0) if video_info else 0

            if progress_callback:
                progress_callback(0, "FFmpeg DELOGO处理中...")

            import threading as _delogo_threading

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding="utf-8",
                errors="ignore",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            # 实时读取stderr解析进度
            delogo_stderr_lines = []

            def _read_delogo_stderr():
                if not process.stderr:
                    return
                for line in process.stderr:
                    delogo_stderr_lines.append(line)
                    if progress_callback and "time=" in line and delogo_duration > 0:
                        try:
                            time_str = line.split("time=")[1].split()[0]
                            parts = time_str.split(":")
                            current_seconds = (
                                float(parts[0]) * 3600
                                + float(parts[1]) * 60
                                + float(parts[2])
                            )
                            percent = min(
                                99, int(current_seconds / delogo_duration * 100)
                            )
                            progress_callback(percent, f"DELOGO处理中... {time_str}")
                        except:
                            pass

            stderr_t = _delogo_threading.Thread(target=_read_delogo_stderr, daemon=True)
            stderr_t.start()
            process.wait()
            stderr_t.join(timeout=2)

            if progress_callback:
                progress_callback(100, "FFmpeg DELOGO处理完成")

            return process.returncode == 0

        except Exception as e:
            print(f"❌ FFmpeg DELOGO处理失败: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _build_audio_mix_filter(self, bgm_input_index: int, video_info: Dict) -> str:
        """构建背景音乐混音滤镜"""
        audio_config = self.config.get("audio", {})

        # 检查原视频是否有音轨
        has_original_audio = video_info.get("has_audio", True)

        # 构建背景音处理链
        bgm_filters = []

        # 背景音量
        bgm_vol = audio_config.get("bgm_volume", 0.5)
        bgm_filters.append(f"volume={bgm_vol}")

        # 背景音淡入淡出
        if audio_config.get("bgm_fade_enabled"):
            fade_dur = audio_config.get("bgm_fade_duration", 3.0)
            if fade_dur > 0:
                bgm_filters.append(f"afade=t=in:d={fade_dur}")
                bgm_filters.append(f"afade=t=out:d={fade_dur}")

        # 背景音延迟
        if audio_config.get("bgm_delay_enabled"):
            delay = audio_config.get("bgm_delay", 0.0)
            if delay > 0:
                delay_ms = int(delay * 1000)
                bgm_filters.append(f"adelay={delay_ms}|{delay_ms}")

        # 如果原视频没有音轨，只使用背景音乐
        if not has_original_audio:
            bgm_chain = ",".join(bgm_filters) if bgm_filters else "anull"
            return f"[{bgm_input_index}:a]{bgm_chain}[aout]"

        # 构建原音处理链
        original_filters = []

        # 原音音量
        if audio_config.get("original_volume_enabled"):
            orig_vol = audio_config.get("original_volume", 1.0)
            original_filters.append(f"volume={orig_vol}")

        # 原音淡入淡出（如果启用同步）
        if audio_config.get("original_fade_sync"):
            if audio_config.get("bgm_fade_enabled"):
                fade_dur = audio_config.get("bgm_fade_duration", 3.0)
                if fade_dur > 0:
                    original_filters.append(f"afade=t=in:d={fade_dur}")
                    original_filters.append(f"afade=t=out:d={fade_dur}")

        # 旧版 FFmpeg 在 amix 后串联多级 atempo 时可能丢失尾部音频。
        # 先将两路音频压缩到相同时间轴，再执行混音。
        frame_extract_filters = self._build_frame_extract_audio_filters(video_info)
        if frame_extract_filters:
            original_filters.extend(frame_extract_filters)
            bgm_filters.extend(frame_extract_filters)

        bgm_chain = ",".join(bgm_filters) if bgm_filters else "anull"
        original_chain = ",".join(original_filters) if original_filters else "anull"

        return (
            f"[0:a]{original_chain}[a0];"
            f"[{bgm_input_index}:a]{bgm_chain}[a1];"
            f"[a0][a1]amix=inputs=2:duration=first:dropout_transition=0[aout]"
        )

    def generate_preview(
        self, input_file: str, output_file: str, variant: int = 0
    ) -> bool:
        """
        生成预览视频(只处理10秒，提升速度)

        Args:
            input_file: 输入视频路径
            output_file: 输出预览文件路径
            variant: 变体索引

        Returns:
            是否成功
        """
        self.last_preview_error = ""
        try:
            # 设置预览模式标志（影响渐出时间计算）
            self.preview_mode = True
            self.preview_duration = 10.0

            # 复用build_command构建完整命令（包含水印）
            try:
                cmd = self.build_command(input_file, output_file, variant, preview=False)
            finally:
                # 预览标志只影响命令构建，不能泄漏到后续正式处理。
                self.preview_mode = False

            # 在命令中插入时长限制与快速编码参数
            # 找到-i参数后的输入文件位置
            try:
                input_index = cmd.index("-i")
                # 在输入文件后插入-t 10
                cmd.insert(input_index + 2, "10")
                cmd.insert(input_index + 2, "-t")
            except (ValueError, IndexError):
                pass

            # 替换编码参数为快速预览模式
            # 查找并替换-preset和-crf
            for i, arg in enumerate(cmd):
                if arg == "-preset" and i + 1 < len(cmd):
                    cmd[i + 1] = "ultrafast"
                elif arg == "-crf" and i + 1 < len(cmd):
                    cmd[i + 1] = "28"

            logger.info("预览命令: %s", " ".join(cmd))

            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            if result.returncode != 0:
                stderr = (result.stderr or "").strip()
                self.last_preview_error = "FFmpeg处理失败"
                logger.error(
                    "预览失败 input=%s output=%s returncode=%s stderr=%s",
                    input_file,
                    output_file,
                    result.returncode,
                    stderr[-4000:],
                )
                return False

            if not os.path.exists(output_file) or os.path.getsize(output_file) <= 0:
                self.last_preview_error = "FFmpeg未生成有效预览文件"
                logger.error(
                    "预览失败：输出文件为空 input=%s output=%s",
                    input_file,
                    output_file,
                )
                return False

            return True

        except Exception as e:
            self.last_preview_error = str(e)
            logger.error(
                "生成预览失败 input=%s output=%s",
                input_file,
                output_file,
                exc_info=True,
            )
            return False
        finally:
            # 清理concat临时文件
            for temp_path in list(self._temp_files):
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError as cleanup_error:
                        logger.warning(
                            "预览临时文件清理失败 file=%s error=%s",
                            temp_path,
                            cleanup_error,
                        )
            self._temp_files = []
