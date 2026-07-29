from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern, Tuple

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QTabWidget,
    QWidget,
)

DEFAULT_LANGUAGE = "zh_CN"
LANGUAGE_ALIASES: Dict[str, str] = {
    "en_us": "en",
    "en-us": "en",
    "english_us": "en",
}

def _resolve_locales_dir() -> Path:
    candidates = []
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        candidates.append(Path(bundle_root) / "ui" / "i18n" / "locales")
    candidates.append(Path(__file__).resolve().parent / "locales")

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


_LOCALES_DIR = _resolve_locales_dir()


def _discover_supported_languages() -> Tuple[str, ...]:
    preferred_order = ("zh_CN", "en")
    discovered = {
        locale_path.stem
        for locale_path in _LOCALES_DIR.glob("*.json")
        if locale_path.is_file()
    }
    discovered.add(DEFAULT_LANGUAGE)

    ordered: list[str] = []
    for code in preferred_order:
        if code in discovered:
            ordered.append(code)
            discovered.remove(code)
    ordered.extend(sorted(discovered))
    return tuple(ordered)


SUPPORTED_LANGUAGES = _discover_supported_languages()

NATIVE_LANGUAGE_NAME_FALLBACKS: Dict[str, str] = {
    "zh_CN": "简体中文",
    "zh_TW": "繁體中文",
    "en": "English",
    "ar": "العربية",
    "bn": "বাংলা",
    "de": "Deutsch",
    "es": "Español",
    "fa": "فارسی",
    "fr": "Français",
    "he": "עברית",
    "hi": "हिन्दी",
    "id": "Bahasa Indonesia",
    "it": "Italiano",
    "ja": "日本語",
    "ko": "한국어",
    "ms": "Bahasa Melayu",
    "nl": "Nederlands",
    "pl": "Polski",
    "pt": "Português",
    "pt_BR": "Português (Brasil)",
    "ru": "Русский",
    "sw": "Kiswahili",
    "ta": "தமிழ்",
    "th": "ไทย",
    "tl": "Tagalog",
    "tr": "Türkçe",
    "uk": "Українська",
    "ur": "اردو",
    "vi": "Tiếng Việt",
}


def _discover_native_language_names() -> Dict[str, str]:
    names: Dict[str, str] = {}
    for lang in SUPPORTED_LANGUAGES:
        locale_file = _LOCALES_DIR / f"{lang}.json"
        if not locale_file.exists():
            continue
        try:
            data = json.loads(locale_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        strings = data.get("strings", {})
        if not isinstance(strings, dict):
            continue
        key = f"language.name.{lang}"
        value = strings.get(key)
        if isinstance(value, str) and value.strip():
            names[lang] = value.strip()
    return names


SUPPORTED_LANGUAGE_NATIVE_NAMES = _discover_native_language_names()


class LanguageManager(QObject):
    language_changed = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._language = DEFAULT_LANGUAGE
        self._strings: Dict[str, str] = {}
        self._default_strings: Dict[str, str] = {}
        self._source_map: Dict[str, str] = {}
        self._source_text_to_key: Dict[str, str] = self._build_source_text_index()
        self._source_templates = self._build_source_text_templates()
        self._load_default_strings()
        self._load_locale(DEFAULT_LANGUAGE)

    def _load_default_strings(self) -> None:
        locale_file = _LOCALES_DIR / f"{DEFAULT_LANGUAGE}.json"
        if not locale_file.exists():
            self._default_strings = {}
            return
        try:
            data = json.loads(locale_file.read_text(encoding="utf-8"))
            strings = data.get("strings", {})
            if isinstance(strings, dict):
                self._default_strings = {str(k): str(v) for k, v in strings.items()}
            else:
                self._default_strings = {}
        except Exception:
            self._default_strings = {}

    def _build_source_text_index(self) -> Dict[str, str]:
        index: Dict[str, str] = {}
        for lang in SUPPORTED_LANGUAGES:
            locale_file = _LOCALES_DIR / f"{lang}.json"
            if not locale_file.exists():
                continue
            try:
                data = json.loads(locale_file.read_text(encoding="utf-8"))
            except Exception:
                continue
            strings = data.get("strings", {})
            if not isinstance(strings, dict):
                continue
            for key, text in strings.items():
                text_s = str(text)
                if not text_s or text_s in index:
                    continue
                index[text_s] = str(key)
        return index

    def _build_source_text_templates(
        self,
    ) -> List[Tuple[Pattern[str], str, Tuple[str, ...]]]:
        templates: List[Tuple[Pattern[str], str, Tuple[str, ...]]] = []
        placeholder_re = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
        for lang in SUPPORTED_LANGUAGES:
            locale_file = _LOCALES_DIR / f"{lang}.json"
            if not locale_file.exists():
                continue
            try:
                data = json.loads(locale_file.read_text(encoding="utf-8"))
            except Exception:
                continue
            strings = data.get("strings", {})
            if not isinstance(strings, dict):
                continue
            for key, text in strings.items():
                text_s = str(text)
                matches = list(placeholder_re.finditer(text_s))
                if not matches:
                    continue

                parts: list[str] = []
                names: list[str] = []
                cursor = 0
                for match in matches:
                    parts.append(re.escape(text_s[cursor:match.start()]))
                    parts.append("(.+?)")
                    names.append(match.group(1))
                    cursor = match.end()
                parts.append(re.escape(text_s[cursor:]))
                try:
                    templates.append((re.compile("^" + "".join(parts) + "$"), str(key), tuple(names)))
                except re.error:
                    continue
        return templates

    @property
    def language(self) -> str:
        return self._language

    def _load_locale(self, language: str) -> bool:
        locale_file = _LOCALES_DIR / f"{language}.json"
        if not locale_file.exists():
            return False

        data = json.loads(locale_file.read_text(encoding="utf-8"))
        strings = data.get("strings", {})
        source_map = data.get("source_map", {})
        if not isinstance(strings, dict) or not isinstance(source_map, dict):
            return False

        self._strings = {str(k): str(v) for k, v in strings.items()}
        self._source_map = {str(k): str(v) for k, v in source_map.items()}
        return True

    def set_language(self, lang_code: Optional[str]) -> None:
        normalized = (lang_code or DEFAULT_LANGUAGE).strip()
        mapped = LANGUAGE_ALIASES.get(normalized.lower())
        if mapped:
            normalized = mapped
        if normalized not in SUPPORTED_LANGUAGES:
            normalized = DEFAULT_LANGUAGE

        if normalized == self._language and self._strings:
            return

        if not self._load_locale(normalized):
            if normalized != DEFAULT_LANGUAGE:
                self._load_locale(DEFAULT_LANGUAGE)
            normalized = DEFAULT_LANGUAGE

        self._language = normalized
        self.language_changed.emit(normalized)

    def t(self, key: str, default: Optional[str] = None, **kwargs: Any) -> str:
        text: Optional[str] = None
        if key in self._strings:
            text = self._strings[key]
        elif default is not None:
            text = default
        elif key in self._default_strings:
            # 缺失目标语言文案时，回退到默认中文，避免界面显示 i18n key
            text = self._default_strings[key]
        else:
            text = key
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text

    def translate_source_text(self, text: str) -> str:
        if not text:
            return text
        # Backward compatibility: allow explicit source_map overrides when present.
        if text in self._source_map:
            return self._source_map[text]
        key = self._source_text_to_key.get(text)
        if key:
            return self.t(key, default=text)
        for pattern, template_key, names in self._source_templates:
            match = pattern.match(text)
            if not match:
                continue
            values = match.groups()
            if len(values) != len(names):
                continue
            return self.t(
                template_key,
                default=text,
                **{name: value for name, value in zip(names, values)},
            )
        for suffix in (":", "："):
            if text.endswith(suffix) and len(text) > len(suffix):
                prefix = text[: -len(suffix)]
                translated_prefix = self.translate_source_text(prefix)
                if translated_prefix != prefix:
                    return f"{translated_prefix}:"
        return text


_language_manager: Optional[LanguageManager] = None


def get_language_manager() -> LanguageManager:
    global _language_manager
    if _language_manager is None:
        _language_manager = LanguageManager()
    return _language_manager


def t(key: str, default: Optional[str] = None, **kwargs: Any) -> str:
    return get_language_manager().t(key, default=default, **kwargs)


def get_supported_languages() -> Tuple[str, ...]:
    return SUPPORTED_LANGUAGES


def get_native_language_name(lang_code: str) -> str:
    if lang_code == "en":
        return "English"
    if lang_code in SUPPORTED_LANGUAGE_NATIVE_NAMES:
        return SUPPORTED_LANGUAGE_NATIVE_NAMES[lang_code]
    return NATIVE_LANGUAGE_NAME_FALLBACKS.get(lang_code, lang_code)


def _translate_widget_texts(widget: QWidget) -> None:
    manager = get_language_manager()

    if widget.windowTitle():
        widget.setWindowTitle(manager.translate_source_text(widget.windowTitle()))

    for obj in widget.findChildren(QWidget):
        if hasattr(obj, "retranslate_ui") and callable(getattr(obj, "retranslate_ui")):
            obj.retranslate_ui()

        if isinstance(obj, (QLabel, QPushButton, QCheckBox, QRadioButton, QGroupBox)):
            text = obj.text()
            if text:
                obj.setText(manager.translate_source_text(text))

        if isinstance(obj, QLineEdit):
            placeholder = obj.placeholderText()
            if placeholder:
                obj.setPlaceholderText(manager.translate_source_text(placeholder))
            tooltip = obj.toolTip()
            if tooltip:
                obj.setToolTip(manager.translate_source_text(tooltip))

        if isinstance(obj, QComboBox):
            for i in range(obj.count()):
                label = obj.itemText(i)
                if label:
                    obj.setItemText(i, manager.translate_source_text(label))

        if isinstance(obj, QTabWidget):
            for i in range(obj.count()):
                text = obj.tabText(i)
                if text:
                    obj.setTabText(i, manager.translate_source_text(text))

        tooltip = obj.toolTip()
        if tooltip:
            obj.setToolTip(manager.translate_source_text(tooltip))


def apply_language_to_widget(widget: QWidget) -> None:
    # Prefer explicit widget-level retranslation when available.
    if hasattr(widget, "retranslate_ui") and callable(getattr(widget, "retranslate_ui")):
        widget.retranslate_ui()
    _translate_widget_texts(widget)
