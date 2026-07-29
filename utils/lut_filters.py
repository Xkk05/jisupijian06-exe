from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from utils.ffmpeg_resources import materialize_ascii_resource


_FILTER_DEFINITIONS = [
    {"id": "vintage", "name": "复古", "aliases": ["Vintage"], "file": "vintage.cube"},
    {"id": "warm", "name": "暖色", "aliases": ["Warm"], "file": "warm.cube"},
    {"id": "cool", "name": "冷色", "aliases": ["Cool"], "file": "cool.cube"},
    {"id": "cinematic", "name": "电影感", "aliases": ["Cinematic"], "file": "cinematic.cube"},
    {"id": "bw", "name": "黑白", "aliases": ["Black & White", "Black White"], "file": "bw.cube"},
    {"id": "sepia", "name": "棕褐", "aliases": ["Sepia"], "file": "sepia.cube"},
    {"id": "cross_process", "name": "交叉处理", "aliases": ["Cross Process"], "file": "cross_process.cube"},
    {"id": "bleach_bypass", "name": "漂白旁路", "aliases": ["Bleach Bypass"], "file": "bleach_bypass.cube"},
    {"id": "teal_orange", "name": "青橙", "aliases": ["Teal & Orange"], "file": "teal_orange.cube"},
    {"id": "film_noir", "name": "黑色电影", "aliases": ["Film Noir"], "file": "film_noir.cube"},
    {"id": "high_contrast", "name": "高对比", "aliases": ["High Contrast"], "file": "high_contrast.cube"},
    {"id": "low_contrast", "name": "低对比", "aliases": ["Low Contrast"], "file": "low_contrast.cube"},
    {"id": "soft_light", "name": "柔光", "aliases": ["Soft Light"], "file": "soft_light.cube"},
    {"id": "hard_light", "name": "硬光", "aliases": ["Hard Light"], "file": "hard_light.cube"},
    {"id": "vivid", "name": "鲜艳", "aliases": ["Vivid"], "file": "vivid.cube"},
    {"id": "muted", "name": "柔和", "aliases": ["Muted"], "file": "muted.cube"},
    {"id": "pastel", "name": "粉彩", "aliases": ["Pastel"], "file": "pastel.cube"},
    {"id": "dramatic", "name": "戏剧", "aliases": ["Dramatic"], "file": "dramatic.cube"},
    {"id": "natural", "name": "自然", "aliases": ["Natural"], "file": "natural.cube"},
    {"id": "urban", "name": "都市", "aliases": ["Urban"], "file": "urban.cube"},
    {"id": "landscape", "name": "风景", "aliases": ["Landscape"], "file": "landscape.cube"},
    {"id": "portrait", "name": "人像", "aliases": ["Portrait"], "file": "portrait.cube"},
    {"id": "food", "name": "美食", "aliases": ["Food"], "file": "food.cube"},
    {"id": "travel", "name": "旅行", "aliases": ["Travel"], "file": "travel.cube"},
    {"id": "sunset", "name": "日落", "aliases": ["Sunset"], "file": "sunset.cube"},
    {"id": "night", "name": "夜景", "aliases": ["Night"], "file": "night.cube"},
    {"id": "day", "name": "白天", "aliases": ["Day"], "file": "day.cube"},
    {"id": "autumn", "name": "秋季", "aliases": ["Autumn"], "file": "autumn.cube"},
    {"id": "spring", "name": "春季", "aliases": ["Spring"], "file": "spring.cube"},
    {"id": "summer", "name": "夏季", "aliases": ["Summer"], "file": "summer.cube"},
    {"id": "winter", "name": "冬季", "aliases": ["Winter"], "file": "winter.cube"},
]


def get_lut_dir() -> str:
    source_root = Path(__file__).resolve().parents[1]
    roots = []
    if hasattr(sys, "_MEIPASS"):
        roots.append(Path(sys._MEIPASS))
    if getattr(sys, "frozen", False):
        executable_root = Path(sys.executable).resolve().parent
        roots.extend((executable_root / "_internal", executable_root))
    roots.append(source_root)

    seen = set()
    for root in roots:
        lut_dir = root / "assets" / "luts"
        key = os.path.normcase(os.path.abspath(str(lut_dir)))
        if key in seen:
            continue
        seen.add(key)
        if lut_dir.is_dir():
            return str(lut_dir)

    return str(source_root / "assets" / "luts")


def list_filters() -> List[Dict[str, str]]:
    return [{"id": item["id"], "name": item["name"]} for item in _FILTER_DEFINITIONS]


def _normalize(text: str) -> str:
    return "".join(ch for ch in text.lower().strip() if ch.isalnum())


def display_to_id(display_name: str) -> Optional[str]:
    if not display_name:
        return None
    normalized = _normalize(display_name)
    for item in _FILTER_DEFINITIONS:
        if normalized == _normalize(item["name"]):
            return item["id"]
        for alias in item.get("aliases", []):
            if normalized == _normalize(alias):
                return item["id"]
    return None


def id_to_display(filter_id: str) -> Optional[str]:
    for item in _FILTER_DEFINITIONS:
        if item["id"] == filter_id:
            return item["name"]
    return None


def id_to_file(filter_id: str) -> Optional[str]:
    for item in _FILTER_DEFINITIONS:
        if item["id"] == filter_id:
            return item["file"]
    return None


def resolve_lut_path(filter_id: str) -> Optional[str]:
    file_name = id_to_file(filter_id)
    if not file_name:
        return None
    return os.path.join(get_lut_dir(), file_name)


def resolve_ffmpeg_lut_path(filter_id: str) -> Optional[str]:
    """Resolve a LUT path that legacy Windows FFmpeg can open."""
    source_path = resolve_lut_path(filter_id)
    if not source_path or not os.path.isfile(source_path):
        return source_path
    return materialize_ascii_resource(source_path, "luts")
