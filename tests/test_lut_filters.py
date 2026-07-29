# -*- coding: utf-8 -*-
"""
LUT滤镜系统单元测试
"""
import pytest
import os


class TestFilterDefinitions:
    """滤镜定义测试"""
    
    def test_all_filters_have_required_fields(self):
        """测试所有滤镜都有必需字段"""
        from utils.lut_filters import _FILTER_DEFINITIONS
        
        for filter_def in _FILTER_DEFINITIONS:
            assert "id" in filter_def
            assert "name" in filter_def
            assert "aliases" in filter_def
            assert "file" in filter_def
            
            assert isinstance(filter_def["id"], str)
            assert isinstance(filter_def["name"], str)
            assert isinstance(filter_def["aliases"], list)
            assert isinstance(filter_def["file"], str)

    def test_unique_ids(self):
        """测试所有滤镜ID唯一"""
        from utils.lut_filters import _FILTER_DEFINITIONS
        
        ids = [f["id"] for f in _FILTER_DEFINITIONS]
        assert len(ids) == len(set(ids)), "滤镜ID必须唯一"

    def test_unique_names(self):
        """测试所有滤镜名称唯一"""
        from utils.lut_filters import _FILTER_DEFINITIONS
        
        names = [f["name"] for f in _FILTER_DEFINITIONS]
        assert len(names) == len(set(names)), "滤镜名称必须唯一"

    def test_cube_file_extension(self):
        """测试所有滤镜文件都有.cube扩展名"""
        from utils.lut_filters import _FILTER_DEFINITIONS
        
        for filter_def in _FILTER_DEFINITIONS:
            assert filter_def["file"].endswith(".cube"), \
                f"滤镜 {filter_def['id']} 的文件必须以.cube结尾"

    def test_popular_filters_exist(self):
        """测试常用滤镜存在"""
        from utils.lut_filters import _FILTER_DEFINITIONS
        
        ids = [f["id"] for f in _FILTER_DEFINITIONS]
        popular_filters = [
            "vintage", "bw", "cinematic", "warm", "cool",
            "sepia", "high_contrast", "low_contrast", "vivid"
        ]
        
        for filter_id in popular_filters:
            assert filter_id in ids, f"常用滤镜 {filter_id} 应该存在"


class TestGetLutDir:
    """LUT目录获取测试"""
    
    def test_returns_valid_path(self):
        """测试返回有效路径"""
        from utils.lut_filters import get_lut_dir
        
        lut_dir = get_lut_dir()
        
        assert isinstance(lut_dir, str)
        assert len(lut_dir) > 0
        assert "assets" in lut_dir
        assert "luts" in lut_dir

    def test_path_contains_luts(self):
        """测试路径包含luts目录"""
        from utils.lut_filters import get_lut_dir
        
        lut_dir = get_lut_dir()
        
        assert lut_dir.endswith("luts") or "luts" in lut_dir

    def test_prefers_packaged_meipass_resources(self, monkeypatch, tmp_path):
        """安装包运行时应从 PyInstaller 资源目录解析 LUT。"""
        import sys
        from utils.lut_filters import get_lut_dir

        packaged_luts = tmp_path / "assets" / "luts"
        packaged_luts.mkdir(parents=True)
        monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

        assert get_lut_dir() == str(packaged_luts)


class TestListFilters:
    """列出滤镜测试"""
    
    def test_returns_list(self):
        """测试返回列表"""
        from utils.lut_filters import list_filters
        
        filters = list_filters()
        
        assert isinstance(filters, list)
        assert len(filters) > 0

    def test_filter_format(self):
        """测试滤镜格式"""
        from utils.lut_filters import list_filters
        
        filters = list_filters()
        
        for filter_item in filters:
            assert "id" in filter_item
            assert "name" in filter_item
            assert isinstance(filter_item["id"], str)
            assert isinstance(filter_item["name"], str)

    def test_matches_definitions(self):
        """测试与定义匹配"""
        from utils.lut_filters import list_filters, _FILTER_DEFINITIONS
        
        filters = list_filters()
        
        assert len(filters) == len(_FILTER_DEFINITIONS)
        
        for i, filter_def in enumerate(_FILTER_DEFINITIONS):
            assert filters[i]["id"] == filter_def["id"]
            assert filters[i]["name"] == filter_def["name"]


class TestDisplayToId:
    """显示名称转ID测试"""
    
    def test_exact_match(self):
        """测试精确匹配"""
        from utils.lut_filters import display_to_id
        
        assert display_to_id("复古") == "vintage"
        assert display_to_id("黑白") == "bw"
        assert display_to_id("暖色") == "warm"

    def test_alias_match(self):
        """测试别名匹配"""
        from utils.lut_filters import display_to_id
        
        assert display_to_id("Vintage") == "vintage"
        assert display_to_id("Black & White") == "bw"
        assert display_to_id("Black White") == "bw"
        assert display_to_id("Cinematic") == "cinematic"

    def test_case_insensitive(self):
        """测试大小写不敏感"""
        from utils.lut_filters import display_to_id
        
        assert display_to_id("VINTAGE") == "vintage"
        assert display_to_id("vintage") == "vintage"
        assert display_to_id("Vintage") == "vintage"

    def test_whitespace_handling(self):
        """测试空白字符处理"""
        from utils.lut_filters import display_to_id
        
        assert display_to_id(" 复古 ") == "vintage"
        assert display_to_id("  Vintage  ") == "vintage"

    def test_no_match_returns_none(self):
        """测试无匹配返回None"""
        from utils.lut_filters import display_to_id
        
        assert display_to_id("不存在的滤镜") is None
        assert display_to_id("") is None
        assert display_to_id("unknown_filter") is None

    def test_empty_string(self):
        """测试空字符串"""
        from utils.lut_filters import display_to_id
        
        assert display_to_id("") is None
        assert display_to_id("   ") is None

    def test_special_characters(self):
        """测试特殊字符"""
        from utils.lut_filters import display_to_id
        
        # &符号应该被正确处理
        assert display_to_id("Teal & Orange") == "teal_orange"


class TestIdToDisplay:
    """ID转显示名称测试"""
    
    def test_valid_ids(self):
        """测试有效ID"""
        from utils.lut_filters import id_to_display
        
        assert id_to_display("vintage") == "复古"
        assert id_to_display("bw") == "黑白"
        assert id_to_display("warm") == "暖色"
        assert id_to_display("cinematic") == "电影感"

    def test_invalid_id_returns_none(self):
        """测试无效ID返回None"""
        from utils.lut_filters import id_to_display
        
        assert id_to_display("invalid_id") is None
        assert id_to_display("") is None
        assert id_to_display("nonexistent") is None

    def test_case_sensitive(self):
        """测试大小写敏感"""
        from utils.lut_filters import id_to_display
        
        # ID应该是大小写敏感的
        assert id_to_display("VINTAGE") is None
        assert id_to_display("Vintage") is None


class TestIdToFile:
    """ID转文件名测试"""
    
    def test_valid_ids(self):
        """测试有效ID"""
        from utils.lut_filters import id_to_file
        
        assert id_to_file("vintage") == "vintage.cube"
        assert id_to_file("bw") == "bw.cube"
        assert id_to_file("warm") == "warm.cube"

    def test_invalid_id_returns_none(self):
        """测试无效ID返回None"""
        from utils.lut_filters import id_to_file
        
        assert id_to_file("invalid") is None
        assert id_to_file("") is None

    def test_file_extension(self):
        """测试文件扩展名"""
        from utils.lut_filters import id_to_file, _FILTER_DEFINITIONS
        
        for filter_def in _FILTER_DEFINITIONS:
            result = id_to_file(filter_def["id"])
            assert result.endswith(".cube")


class TestResolveLutPath:
    """解析LUT路径测试"""
    
    def test_valid_filter_ids(self):
        """测试有效滤镜ID"""
        from utils.lut_filters import resolve_lut_path
        
        path = resolve_lut_path("vintage")
        
        assert path is not None
        assert path.endswith("vintage.cube")
        assert "assets" in path
        assert "luts" in path

    def test_invalid_filter_id(self):
        """测试无效滤镜ID"""
        from utils.lut_filters import resolve_lut_path
        
        assert resolve_lut_path("invalid") is None
        assert resolve_lut_path("") is None
        assert resolve_lut_path("nonexistent") is None

    def test_path_format(self):
        """测试路径格式"""
        from utils.lut_filters import resolve_lut_path
        
        path = resolve_lut_path("bw")
        
        # 验证路径使用正确的分隔符
        assert ".cube" in path
        assert "bw.cube" in path

    def test_ffmpeg_resolver_uses_compatibility_layer(self, monkeypatch):
        from utils import lut_filters

        observed = {}

        def fake_materialize(path, namespace):
            observed["path"] = path
            observed["namespace"] = namespace
            return "C:/ascii-cache/vintage.cube"

        monkeypatch.setattr(lut_filters, "materialize_ascii_resource", fake_materialize)

        result = lut_filters.resolve_ffmpeg_lut_path("vintage")

        assert result == "C:/ascii-cache/vintage.cube"
        assert observed["path"].endswith("vintage.cube")
        assert observed["namespace"] == "luts"


class TestNormalize:
    """归一化函数测试"""
    
    def test_lowercase_conversion(self):
        """测试小写转换"""
        from utils.lut_filters import _normalize
        
        assert _normalize("VINTAGE") == "vintage"
        assert _normalize("Vintage") == "vintage"
        assert _normalize("vintage") == "vintage"

    def test_whitespace_removal(self):
        """测试空白字符移除"""
        from utils.lut_filters import _normalize
        
        assert _normalize("  vintage  ") == "vintage"
        assert _normalize("black & white") == "blackwhite"

    def test_special_chars_removal(self):
        """测试特殊字符移除"""
        from utils.lut_filters import _normalize
        
        assert _normalize("Black & White") == "blackwhite"
        assert _normalize("Teal & Orange") == "tealorange"
        assert _normalize("A/B Test") == "abtest"

    def test_unicode_support(self):
        """测试Unicode支持"""
        from utils.lut_filters import _normalize
        
        # 中文字符应该保留
        assert _normalize("复古") == "复古"
        assert _normalize(" 复古 ") == "复古"
