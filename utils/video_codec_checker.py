# -*- coding: utf-8 -*-
"""
视频编码兼容性检测器
检测视频编码是否支持，提前发现不支持的格式
"""

from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass

from utils.exceptions import VideoCodecException
from utils.unified_logger import logger


# 支持的视频编码白名单（常见且 FFmpeg 通常支持的编码）
SUPPORTED_VIDEO_CODECS = {
    # H.264/AVC
    'h264', 'libx264', 'libx264rgb', 'h264_nvenc', 'hevc_nvenc',
    # H.265/HEVC
    'hevc', 'libx265', 'h265_nvenc',
    # VP 系列
    'vp8', 'libvpx', 'vp9', 'libvpx-vp9',
    # AV1
    'av1', 'libaom-av1', 'libsvtav1',
    # MPEG 系列
    'mpeg4', 'libxvid', 'mpeg2video', 'mpeg1video',
    # 其他常见编码
    'prores_ks',  # ProRes 有条件支持
    'hap',
    'magicyuv',
}

# 不支持或有限支持的视频编码（需要特殊处理或转换）
UNSUPPORTED_VIDEO_CODECS = {
    # 职业后期格式（通常需要转码）
    'prores', 'prores_aw', 'prores_ks',
    # 烧录 RAW 格式
    'rawvideo',
    # 专业编码（需要特殊硬件/授权）
    'dnxhd', 'dnxhd_hq', 'dnxhd_lb',
    # 电影胶片格式
    'cinepak',
    # 苹果专属格式（需要特殊处理）
    'apch', 'apcn', 'apcs', 'apco', 'ap4h', 'ap4x',
}

# 音频编码白名单
SUPPORTED_AUDIO_CODECS = {
    'aac', 'libfdk_aac', 'libfaac',
    'mp3', 'libmp3lame',
    'ac3',
    'eac3',
    'flac',
    'alac',
    'opus', 'libopus',
    'vorbis', 'libvorbis',
    'pcm_s16le', 'pcm_s24le', 'pcm_s32le',
    'wavpack',
}

# 不支持或有限支持的音频编码
UNSUPPORTED_AUDIO_CODECS = {
    'truehd',  # 需要 eac3 转换
    'dts', 'dts-hd',  # 需要转换
    'speex',
    'mp2',
}


@dataclass
class CodecCheckResult:
    """编码检查结果"""
    is_compatible: bool
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    unsupported_video: bool = False
    unsupported_audio: bool = False
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


def _get_codec_suggestions(codec: str, codec_type: str = 'video') -> List[str]:
    """获取编码替代建议"""
    suggestions = []

    if codec_type == 'video':
        suggestions.extend([
            'H.264 (libx264) - 最广泛的兼容性',
            'H.265/HEVC (libx265) - 更好的压缩率',
            'VP9 (libvpx-vp9) - 开源免费',
            'AV1 (libsvtav1) - 最新一代压缩标准',
        ])
    elif codec_type == 'audio':
        suggestions.extend([
            'AAC - 最广泛的兼容性',
            'MP3 - 通用兼容',
            'Opus - 更好的压缩率',
            'FLAC - 无损格式',
        ])

    return suggestions


def check_video_codec_compatibility(
    video_info: Dict,
    strict_mode: bool = False
) -> CodecCheckResult:
    """
    检查视频编码是否兼容

    Args:
        video_info: 视频信息字典，应包含 'codec_name' 等字段
        strict_mode: 是否启用严格模式（对不支持的编码抛出异常）

    Returns:
        CodecCheckResult: 检查结果

    Raises:
        VideoCodecException: 当检测到不支持的编码时（strict_mode=True）
    """
    warnings = []
    unsupported_video = False
    unsupported_audio = False

    # 提取视频编码信息
    video_codec = video_info.get('codec_name', '').lower()
    audio_codec = video_info.get('audio_codec_name', '').lower()

    logger.debug(f"[CodecChecker] 检查编码: 视频={video_codec}, 音频={audio_codec}")

    # 检查视频编码
    if video_codec:
        if video_codec in UNSUPPORTED_VIDEO_CODECS:
            unsupported_video = True
            warnings.append(f"不支持的视频编码: {video_codec}，建议转换为 H.264 或 H.265")
            logger.warning(f"[CodecChecker] 不支持的视频编码: {video_codec}")

            if strict_mode:
                suggestions = _get_codec_suggestions(video_codec, 'video')
                raise VideoCodecException(
                    message=f"不支持的视频编码: {video_codec}",
                    codec_name=video_codec,
                    codec_type='video',
                    suggestions=suggestions
                )
        elif video_codec not in SUPPORTED_VIDEO_CODECS:
            # 未明确列出的编码，给出警告但不阻止
            warnings.append(f"未明确支持的视频编码: {video_codec}，处理可能失败")

    # 检查音频编码
    if audio_codec:
        if audio_codec in UNSUPPORTED_AUDIO_CODECS:
            unsupported_audio = True
            warnings.append(f"不支持的音频编码: {audio_codec}，建议转换为 AAC 或 MP3")
            logger.warning(f"[CodecChecker] 不支持的音频编码: {audio_codec}")
        elif audio_codec not in SUPPORTED_AUDIO_CODECS:
            # 未明确列出的编码，给出警告
            warnings.append(f"未明确支持的音频编码: {audio_codec}，处理可能失败")

    # 检查封装格式
    container = video_info.get('format_name', '').lower()
    unsupported_containers = {'rtmp', 'rtsp', 'mxf', 'gxf'}  # 可能需要特殊处理

    if container in unsupported_containers:
        warnings.append(f"非标准封装格式: {container}，可能需要额外处理")

    is_compatible = not unsupported_video and not unsupported_audio

    return CodecCheckResult(
        is_compatible=is_compatible,
        video_codec=video_codec,
        audio_codec=audio_codec,
        unsupported_video=unsupported_video,
        unsupported_audio=unsupported_audio,
        warnings=warnings
    )


def check_codec_from_stream_info(stream_info: Dict) -> Tuple[Optional[str], Optional[str]]:
    """
    从 FFprobe 流信息中提取视频和音频编码名称

    Args:
        stream_info: FFprobe 返回的流信息

    Returns:
        (video_codec, audio_codec) 元组
    """
    video_codec = None
    audio_codec = None

    for stream in stream_info.get('streams', []):
        codec_type = stream.get('codec_type')
        codec_name = stream.get('codec_name', '').lower()

        if codec_type == 'video' and not video_codec:
            video_codec = codec_name
        elif codec_type == 'audio' and not audio_codec:
            audio_codec = codec_name

    return video_codec, audio_codec


def validate_video_for_processing(video_info: Dict) -> None:
    """
    验证视频是否可用于处理，如果不支持则抛出异常

    Args:
        video_info: 视频信息字典

    Raises:
        VideoCodecException: 当视频编码不支持时
    """
    # 如果 video_info 已经包含编码信息（来自 get_video_info）
    if video_info.get('codec_name'):
        codec_info = {
            'codec_name': video_info.get('codec_name'),
            'audio_codec_name': video_info.get('audio_codec_name'),
            'format_name': video_info.get('format_name'),
        }
    else:
        # 从 FFprobe 流信息提取
        video_codec, audio_codec = check_codec_from_stream_info(video_info)
        codec_info = {
            'codec_name': video_codec,
            'audio_codec_name': audio_codec,
            'format_name': video_info.get('format', {}).get('format_name', ''),
        }

    # 使用严格模式检查
    check_video_codec_compatibility(codec_info, strict_mode=True)
