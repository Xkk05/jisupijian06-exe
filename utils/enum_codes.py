from __future__ import annotations

from typing import Dict, Iterable, Optional

LANG_ZH = "zh_CN"
LANG_EN = "en"


def _normalize_value(
    value: Optional[str], aliases: Dict[str, str], default_code: str
) -> str:
    if value is None:
        return default_code
    raw = str(value).strip()
    if raw in aliases:
        return aliases[raw]
    lower = raw.lower()
    if lower in aliases:
        return aliases[lower]
    return default_code


def _build_aliases(
    labels: Dict[str, Dict[str, str]], extra_aliases: Optional[Dict[str, Iterable[str]]] = None
) -> Dict[str, str]:
    aliases: Dict[str, str] = {}
    for code, lang_map in labels.items():
        aliases[code] = code
        aliases[code.lower()] = code
        for _lang, label in lang_map.items():
            aliases[label] = code
            aliases[label.lower()] = code
    if extra_aliases:
        for code, values in extra_aliases.items():
            for value in values:
                aliases[value] = code
                aliases[value.lower()] = code
    return aliases


def enum_label(labels: Dict[str, Dict[str, str]], code: str, lang: str = LANG_ZH) -> str:
    item = labels.get(code)
    if not item:
        return code
    return item.get(lang) or item.get(LANG_ZH) or code


CROP_MODE_LABELS = {
    "pixel": {LANG_ZH: "像素", LANG_EN: "Pixel"},
    "center": {LANG_ZH: "中间", LANG_EN: "Center"},
    "percent": {LANG_ZH: "百分比", LANG_EN: "Percent"},
}
CROP_MODE_ALIASES = _build_aliases(CROP_MODE_LABELS)


CROP_PERCENT_POSITION_LABELS = {
    "all": {LANG_ZH: "四边", LANG_EN: "All sides"},
    "top_left": {LANG_ZH: "左上", LANG_EN: "Top-left"},
    "top_right": {LANG_ZH: "右上", LANG_EN: "Top-right"},
    "bottom_left": {LANG_ZH: "左下", LANG_EN: "Bottom-left"},
    "bottom_right": {LANG_ZH: "右下", LANG_EN: "Bottom-right"},
    "top": {LANG_ZH: "上边", LANG_EN: "Top"},
    "bottom": {LANG_ZH: "下边", LANG_EN: "Bottom"},
    "left": {LANG_ZH: "左边", LANG_EN: "Left"},
    "right": {LANG_ZH: "右边", LANG_EN: "Right"},
    "vertical": {LANG_ZH: "上下", LANG_EN: "Vertical"},
    "horizontal": {LANG_ZH: "左右", LANG_EN: "Horizontal"},
    "random": {LANG_ZH: "随机", LANG_EN: "Random"},
}
CROP_PERCENT_POSITION_ALIASES = _build_aliases(CROP_PERCENT_POSITION_LABELS)


GRID_DIRECTION_LABELS = {
    "auto": {LANG_ZH: "自动", LANG_EN: "Auto"},
    "vertical": {LANG_ZH: "上下", LANG_EN: "Vertical"},
    "horizontal": {LANG_ZH: "左右", LANG_EN: "Horizontal"},
}
GRID_DIRECTION_ALIASES = _build_aliases(GRID_DIRECTION_LABELS)


TRIM_MODE_LABELS = {
    "trim_edges": {LANG_ZH: "去头尾", LANG_EN: "Trim Edges"},
    "clip_range": {LANG_ZH: "截取", LANG_EN: "Clip Range"},
}
TRIM_MODE_ALIASES = _build_aliases(
    TRIM_MODE_LABELS, extra_aliases={"clip_range": ["保留中间"]}
)


RESOLUTION_PRESET_LABELS = {
    "custom": {LANG_ZH: "自定义", LANG_EN: "Custom"},
    "swap": {LANG_ZH: "宽高互换", LANG_EN: "Swap Width/Height"},
    "p360": {LANG_ZH: "360P", LANG_EN: "360P"},
    "p480": {LANG_ZH: "480P", LANG_EN: "480P"},
    "p720": {LANG_ZH: "720P", LANG_EN: "720P"},
    "p1080": {LANG_ZH: "1080P", LANG_EN: "1080P"},
}
RESOLUTION_PRESET_ALIASES = _build_aliases(RESOLUTION_PRESET_LABELS)


STATUS_LABELS = {
    "pending": {LANG_ZH: "待处理", LANG_EN: "Pending"},
    "processing": {LANG_ZH: "处理中", LANG_EN: "Processing"},
    "done": {LANG_ZH: "完成", LANG_EN: "Done"},
    "failed": {LANG_ZH: "失败", LANG_EN: "Failed"},
    "skipped": {LANG_ZH: "跳过", LANG_EN: "Skipped"},
    "stopped": {LANG_ZH: "已停止", LANG_EN: "Stopped"},
}
STATUS_ALIASES = _build_aliases(
    STATUS_LABELS,
    extra_aliases={
        "failed": ["错误", "error"],
        "stopped": ["停止", "stopping"],
    },
)


TEXT_SOURCE_MODE_LABELS = {
    "filename": {LANG_ZH: "文件名模式", LANG_EN: "Filename Mode"},
    "folder": {LANG_ZH: "文件夹模式", LANG_EN: "Folder Mode"},
    "plain": {LANG_ZH: "文本模式", LANG_EN: "Text Mode"},
}
TEXT_SOURCE_MODE_ALIASES = _build_aliases(TEXT_SOURCE_MODE_LABELS)


TEXT_FILTER_ACTION_LABELS = {
    "keep": {LANG_ZH: "保留", LANG_EN: "Keep"},
    "remove": {LANG_ZH: "删除", LANG_EN: "Remove"},
}
TEXT_FILTER_ACTION_ALIASES = _build_aliases(TEXT_FILTER_ACTION_LABELS)


TEXT_FILTER_POSITION_LABELS = {
    "before": {LANG_ZH: "前", LANG_EN: "Before"},
    "after": {LANG_ZH: "后", LANG_EN: "After"},
    "between": {LANG_ZH: "间", LANG_EN: "Between"},
}
TEXT_FILTER_POSITION_ALIASES = _build_aliases(TEXT_FILTER_POSITION_LABELS)


TEXT_POSITION_LABELS = {
    "top": {LANG_ZH: "上边", LANG_EN: "Top"},
    "bottom": {LANG_ZH: "下边", LANG_EN: "Bottom"},
    "left": {LANG_ZH: "左边", LANG_EN: "Left"},
    "right": {LANG_ZH: "右边", LANG_EN: "Right"},
    "top_left": {LANG_ZH: "左上", LANG_EN: "Top-left"},
    "top_right": {LANG_ZH: "右上", LANG_EN: "Top-right"},
    "bottom_left": {LANG_ZH: "左下", LANG_EN: "Bottom-left"},
    "bottom_right": {LANG_ZH: "右下", LANG_EN: "Bottom-right"},
    "center": {LANG_ZH: "中间", LANG_EN: "Center"},
    "custom": {LANG_ZH: "自定义", LANG_EN: "Custom"},
    "random": {LANG_ZH: "随机", LANG_EN: "Random"},
}
TEXT_POSITION_ALIASES = _build_aliases(TEXT_POSITION_LABELS)


BG_STYLE_LABELS = {
    "default": {LANG_ZH: "默认", LANG_EN: "Default"},
    "fill": {LANG_ZH: "填充", LANG_EN: "Fill"},
}
BG_STYLE_ALIASES = _build_aliases(BG_STYLE_LABELS)


SCROLL_DIRECTION_LABELS = {
    "right": {LANG_ZH: "向右", LANG_EN: "Rightward"},
    "left": {LANG_ZH: "向左", LANG_EN: "Leftward"},
    "up": {LANG_ZH: "向上", LANG_EN: "Upward"},
    "down": {LANG_ZH: "向下", LANG_EN: "Downward"},
    "random": {LANG_ZH: "随机", LANG_EN: "Random"},
}
SCROLL_DIRECTION_ALIASES = _build_aliases(SCROLL_DIRECTION_LABELS)


VIDEO_REF_LABELS = {
    "height": {LANG_ZH: "高", LANG_EN: "Height"},
    "width": {LANG_ZH: "宽", LANG_EN: "Width"},
    "diagonal": {LANG_ZH: "对角", LANG_EN: "Diagonal"},
}
VIDEO_REF_ALIASES = _build_aliases(VIDEO_REF_LABELS)


TEXT_ARRANGE_LABELS = {
    "horizontal": {LANG_ZH: "水平", LANG_EN: "Horizontal"},
    "vertical": {LANG_ZH: "垂直", LANG_EN: "Vertical"},
    "slanted": {LANG_ZH: "倾斜", LANG_EN: "Slanted"},
}
TEXT_ARRANGE_ALIASES = _build_aliases(TEXT_ARRANGE_LABELS)


TEXT_ANIMATION_TYPE_LABELS = {
    "none": {LANG_ZH: "无", LANG_EN: "None"},
    "scroll": {LANG_ZH: "滚动", LANG_EN: "Scroll"},
    "fade_in_out": {LANG_ZH: "淡入淡出", LANG_EN: "Fade In/Out"},
    "scale": {LANG_ZH: "缩放", LANG_EN: "Scale"},
    "rotate": {LANG_ZH: "旋转", LANG_EN: "Rotate"},
    "bounce": {LANG_ZH: "弹跳", LANG_EN: "Bounce"},
}
TEXT_ANIMATION_TYPE_ALIASES = _build_aliases(TEXT_ANIMATION_TYPE_LABELS)


BORDER_STYLE_LABELS = {
    "all": {LANG_ZH: "四周", LANG_EN: "All around"},
    "vertical": {LANG_ZH: "上下", LANG_EN: "Vertical"},
    "horizontal": {LANG_ZH: "左右", LANG_EN: "Horizontal"},
    "top": {LANG_ZH: "上边", LANG_EN: "Top"},
    "bottom": {LANG_ZH: "下边", LANG_EN: "Bottom"},
    "left": {LANG_ZH: "左边", LANG_EN: "Left"},
    "right": {LANG_ZH: "右边", LANG_EN: "Right"},
}
BORDER_STYLE_ALIASES = _build_aliases(BORDER_STYLE_LABELS)


CURTAIN_DIRECTION_LABELS = {
    "auto": {LANG_ZH: "自动", LANG_EN: "Auto"},
    "vertical": {LANG_ZH: "上下", LANG_EN: "Vertical"},
    "horizontal": {LANG_ZH: "左右", LANG_EN: "Horizontal"},
    "up": {LANG_ZH: "上", LANG_EN: "Up"},
    "down": {LANG_ZH: "下", LANG_EN: "Down"},
    "left": {LANG_ZH: "左", LANG_EN: "Left"},
    "right": {LANG_ZH: "右", LANG_EN: "Right"},
    "auto_close": {LANG_ZH: "自动收", LANG_EN: "Auto close"},
    "horizontal_close": {LANG_ZH: "左右收", LANG_EN: "Close horizontally"},
    "vertical_close": {LANG_ZH: "上下收", LANG_EN: "Close vertically"}
}
CURTAIN_DIRECTION_ALIASES = _build_aliases(CURTAIN_DIRECTION_LABELS)


WATERMARK_PRESET_LABELS = {
    "custom": {LANG_ZH: "自定义", LANG_EN: "Custom"},
    "bilibili_top_right": {LANG_ZH: "B站 - 右上角", LANG_EN: "Bilibili - Top Right"},
    "douyin_bottom_right": {LANG_ZH: "抖音 - 右下角", LANG_EN: "Douyin - Bottom Right"},
    "xiaohongshu_bottom_right": {LANG_ZH: "小红书 - 右下角", LANG_EN: "Xiaohongshu - Bottom Right"},
    "iqiyi_top_right": {LANG_ZH: "爱奇艺 - 右上角", LANG_EN: "iQIYI - Top Right"},
    "youtube_bottom_left": {LANG_ZH: "YouTube - 左下角", LANG_EN: "YouTube - Bottom Left"},
    "tiktok_bottom_right": {LANG_ZH: "TikTok - 右下角", LANG_EN: "TikTok - Bottom Right"},
    "weibo_bottom_right": {LANG_ZH: "微博 - 右下角", LANG_EN: "Weibo - Bottom Right"},
    "tencent_video_top_right": {LANG_ZH: "腾讯视频 - 右上角", LANG_EN: "Tencent Video - Top Right"},
    "kuaishou_bottom_right": {LANG_ZH: "快手 - 右下角", LANG_EN: "Kuaishou - Bottom Right"},
    "xigua_top_right": {LANG_ZH: "西瓜视频 - 右上角", LANG_EN: "Xigua Video - Top Right"},
    "toutiao_bottom_right": {LANG_ZH: "今日头条 - 右下角", LANG_EN: "Toutiao - Bottom Right"},
    "netease_music_bottom_left": {LANG_ZH: "网易云音乐 - 左下角", LANG_EN: "NetEase Music - Bottom Left"},
    "youku_top_right": {LANG_ZH: "优酷 - 右上角", LANG_EN: "Youku - Top Right"},
    "sohu_bottom_right": {LANG_ZH: "搜狐视频 - 右下角", LANG_EN: "Sohu Video - Bottom Right"},
    "letv_top_right": {LANG_ZH: "乐视视频 - 右上角", LANG_EN: "LeTV - Top Right"},
    "migu_bottom_right": {LANG_ZH: "咪咕视频 - 右下角", LANG_EN: "Migu Video - Bottom Right"},
    "acfun_top_right": {LANG_ZH: "AcFun - 右上角", LANG_EN: "AcFun - Top Right"},
    "bilibili_bottom_left": {LANG_ZH: "哔哩哔哩 - 左下角", LANG_EN: "Bilibili - Bottom Left"},
    "zhihu_bottom_right": {LANG_ZH: "知乎 - 右下角", LANG_EN: "Zhihu - Bottom Right"},
    "douban_top_right": {LANG_ZH: "豆瓣 - 右上角", LANG_EN: "Douban - Top Right"}
}
WATERMARK_PRESET_ALIASES = _build_aliases(WATERMARK_PRESET_LABELS)


def normalize_crop_mode(value: Optional[str], default_code: str = "pixel") -> str:
    return _normalize_value(value, CROP_MODE_ALIASES, default_code)


def normalize_crop_percent_position(
    value: Optional[str], default_code: str = "all"
) -> str:
    return _normalize_value(value, CROP_PERCENT_POSITION_ALIASES, default_code)


def normalize_grid_direction(value: Optional[str], default_code: str = "auto") -> str:
    return _normalize_value(value, GRID_DIRECTION_ALIASES, default_code)


def normalize_trim_mode(value: Optional[str], default_code: str = "trim_edges") -> str:
    return _normalize_value(value, TRIM_MODE_ALIASES, default_code)


def normalize_resolution_preset(
    value: Optional[str], default_code: str = "custom"
) -> str:
    return _normalize_value(value, RESOLUTION_PRESET_ALIASES, default_code)


def normalize_status_code(value: Optional[str], default_code: str = "pending") -> str:
    return _normalize_value(value, STATUS_ALIASES, default_code)


def normalize_text_source_mode(
    value: Optional[str], default_code: str = "plain"
) -> str:
    return _normalize_value(value, TEXT_SOURCE_MODE_ALIASES, default_code)


def normalize_text_filter_action(
    value: Optional[str], default_code: str = "keep"
) -> str:
    return _normalize_value(value, TEXT_FILTER_ACTION_ALIASES, default_code)


def normalize_text_filter_position(
    value: Optional[str], default_code: str = "before"
) -> str:
    return _normalize_value(value, TEXT_FILTER_POSITION_ALIASES, default_code)


def normalize_text_position(value: Optional[str], default_code: str = "center") -> str:
    return _normalize_value(value, TEXT_POSITION_ALIASES, default_code)


def normalize_bg_style(value: Optional[str], default_code: str = "default") -> str:
    return _normalize_value(value, BG_STYLE_ALIASES, default_code)


def normalize_scroll_direction(
    value: Optional[str], default_code: str = "right"
) -> str:
    return _normalize_value(value, SCROLL_DIRECTION_ALIASES, default_code)


def normalize_video_ref(value: Optional[str], default_code: str = "height") -> str:
    return _normalize_value(value, VIDEO_REF_ALIASES, default_code)


def normalize_text_arrange(
    value: Optional[str], default_code: str = "horizontal"
) -> str:
    return _normalize_value(value, TEXT_ARRANGE_ALIASES, default_code)


def normalize_text_animation_type(
    value: Optional[str], default_code: str = "none"
) -> str:
    return _normalize_value(value, TEXT_ANIMATION_TYPE_ALIASES, default_code)


def normalize_border_style(value: Optional[str], default_code: str = "all") -> str:
    return _normalize_value(value, BORDER_STYLE_ALIASES, default_code)


def normalize_curtain_direction(
    value: Optional[str], default_code: str = "auto"
) -> str:
    return _normalize_value(value, CURTAIN_DIRECTION_ALIASES, default_code)


def normalize_watermark_preset(
    value: Optional[str], default_code: str = "custom"
) -> str:
    return _normalize_value(value, WATERMARK_PRESET_ALIASES, default_code)
