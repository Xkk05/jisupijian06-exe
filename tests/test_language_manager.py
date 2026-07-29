# -*- coding: utf-8 -*-
"""
i18n 语言管理器测试
"""

from ui.i18n.language_manager import LanguageManager


class TestLanguageManager:
    def test_load_default_language(self):
        manager = LanguageManager()
        assert manager.language == "zh_CN"
        assert manager.t("language.name.en") == "English"

    def test_switch_language(self):
        manager = LanguageManager()
        manager.set_language("en")
        assert manager.language == "en"
        assert manager.t("language.name.zh_CN") == "Simplified Chinese"

    def test_missing_key_fallback(self):
        manager = LanguageManager()
        assert manager.t("missing.key", default="fallback") == "fallback"

    def test_source_text_translation(self):
        manager = LanguageManager()
        manager.set_language("en")
        assert manager.translate_source_text("选项") == "Options"
        manager.set_language("zh_CN")
        assert manager.translate_source_text("Options") == "选项"

    def test_formatted_source_text_translation(self):
        manager = LanguageManager()
        manager.set_language("en")

        assert manager.translate_source_text("区域 2") == "Region 2"
        assert manager.translate_source_text("水印 #1") == "Watermark #1"
        assert manager.translate_source_text("文本轨道 3") == "Text track 3"
        assert manager.translate_source_text("总数: 0 | 已勾选: 0") == "Total: 0 | Selected: 0"
        assert manager.translate_source_text("上:") == "Top:"
