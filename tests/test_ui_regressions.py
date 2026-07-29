# -*- coding: utf-8 -*-
"""本轮问题修复对应的无窗口界面回归测试。"""

import os
import time
import importlib

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def lightweight_window(qapp):
    from PyQt6.QtWidgets import QMainWindow, QTableWidget

    from ui.batch_video.left_panel import CheckableHeaderView
    from ui.batch_video.main_window import BatchVideoProcessorWindow

    window = BatchVideoProcessorWindow.__new__(BatchVideoProcessorWindow)
    QMainWindow.__init__(window)
    window.video_list = []
    window.video_table = QTableWidget(0, 5, window)
    window.header_view = CheckableHeaderView(
        window.video_table.horizontalHeader().orientation(), window.video_table
    )
    window.video_table.setHorizontalHeader(window.header_view)
    window.update_queue_status = lambda: None
    yield window
    window.close()


def _add_rows(window, count, checked=False):
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QTableWidgetItem

    window.video_table.setRowCount(count)
    for row in range(count):
        window.video_table.setItem(
            row, window.COL_CHECK, window._create_check_item(checked=checked)
        )
        number_item = QTableWidgetItem(str(row + 1))
        number_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        window.video_table.setItem(row, window.COL_NO, number_item)


def test_number_column_displays_multi_digit_indices(lightweight_window):
    from PyQt6.QtGui import QFontMetrics

    _add_rows(lightweight_window, 120)
    lightweight_window._adjust_number_column_width()

    width = lightweight_window.video_table.columnWidth(lightweight_window.COL_NO)
    text_width = QFontMetrics(lightweight_window.video_table.font()).horizontalAdvance("120")
    assert width >= 46
    assert width >= text_width + 20
    assert lightweight_window.video_table.item(119, lightweight_window.COL_NO).text() == "120"


def test_context_select_all_checks_every_video(lightweight_window):
    from PyQt6.QtCore import Qt

    _add_rows(lightweight_window, 12, checked=False)
    lightweight_window.select_all_videos()

    assert len(lightweight_window.video_table.selectionModel().selectedRows()) == 12
    assert all(
        lightweight_window.video_table.item(row, lightweight_window.COL_CHECK).checkState()
        == Qt.CheckState.Checked
        for row in range(12)
    )
    assert lightweight_window.header_view.get_check_state() == Qt.CheckState.Checked


def test_context_invert_reverses_every_video_check(lightweight_window):
    from PyQt6.QtCore import Qt

    _add_rows(lightweight_window, 3, checked=True)
    lightweight_window.video_table.item(1, lightweight_window.COL_CHECK).setCheckState(
        Qt.CheckState.Unchecked
    )

    lightweight_window.invert_selection()

    assert [
        lightweight_window.video_table.item(row, lightweight_window.COL_CHECK).checkState()
        for row in range(3)
    ] == [
        Qt.CheckState.Unchecked,
        Qt.CheckState.Checked,
        Qt.CheckState.Unchecked,
    ]
    assert lightweight_window.header_view.get_check_state() == Qt.CheckState.PartiallyChecked


def test_playback_speed_menu_shows_full_labels(qapp, monkeypatch, tmp_path):
    import cv2
    from PyQt6.QtCore import Qt

    from ui.video_player_window import SimpleVideoPlayer

    class FakeCapture:
        def isOpened(self):
            return True

        def get(self, prop):
            return {
                cv2.CAP_PROP_FPS: 30,
                cv2.CAP_PROP_FRAME_COUNT: 300,
                cv2.CAP_PROP_FRAME_WIDTH: 320,
                cv2.CAP_PROP_FRAME_HEIGHT: 240,
            }.get(prop, 0)

        def read(self):
            return False, None

        def set(self, *_args):
            return True

        def release(self):
            return None

    video_path = tmp_path / "speed-menu.mp4"
    video_path.write_bytes(b"test")
    monkeypatch.setattr(cv2, "VideoCapture", lambda _path: FakeCapture())

    player = SimpleVideoPlayer(str(video_path))
    labels = [player.speed_combo.itemText(index) for index in range(player.speed_combo.count())]
    longest_label = max(
        player.speed_combo.fontMetrics().horizontalAdvance(label) for label in labels
    )
    player.show()
    player.speed_combo.showPopup()
    qapp.processEvents()
    popup_text_width = player.speed_combo.view().viewport().width() - 20

    assert labels == ["0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x"]
    assert player.speed_combo.view().minimumWidth() >= longest_label + 24
    assert popup_text_width >= longest_label
    assert player.speed_combo.view().textElideMode() == Qt.TextElideMode.ElideNone
    player.speed_combo.hidePopup()
    player.close()


def test_failed_row_double_click_opens_error_instead_of_preview(lightweight_window):
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QTableWidgetItem

    _add_rows(lightweight_window, 1)
    status_item = QTableWidgetItem()
    status_item.setData(Qt.ItemDataRole.UserRole, "failed")
    lightweight_window.video_table.setItem(0, lightweight_window.COL_STATUS, status_item)
    lightweight_window.video_list = [{"path": "failed.mp4", "process_error": "编码失败"}]
    calls = []
    lightweight_window.show_process_error_detail = lambda row: calls.append(("error", row))
    lightweight_window.preview_video = lambda row: calls.append(("preview", row))

    lightweight_window.on_video_double_clicked(0, lightweight_window.COL_NAME)

    assert calls == [("error", 0)]


def test_error_detail_dialog_uses_selectable_plain_text(lightweight_window, monkeypatch):
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QDialog, QLabel, QTableWidgetItem, QTextEdit
    from ui.i18n import get_language_manager

    manager = get_language_manager()
    previous_language = manager.language
    manager.set_language("zh_CN")
    _add_rows(lightweight_window, 1)
    status_item = QTableWidgetItem()
    status_item.setData(Qt.ItemDataRole.UserRole, "failed")
    lightweight_window.video_table.setItem(0, lightweight_window.COL_STATUS, status_item)
    detail = "FFmpeg处理失败：编码器不可用\n请检查显卡驱动"
    lightweight_window.video_list = [
        {"path": "C:/video/failed.mp4", "output_path": "C:/out/failed.mp4", "process_error": detail}
    ]
    observed = {}

    def fake_exec(dialog):
        editor = dialog.findChild(QTextEdit)
        observed["title"] = dialog.windowTitle()
        observed["detail"] = editor.toPlainText()
        observed["read_only"] = editor.isReadOnly()
        observed["labels"] = [label.text() for label in dialog.findChildren(QLabel)]
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QDialog, "exec", fake_exec)
    lightweight_window.show_process_error_detail(0)

    assert observed["title"] == "处理失败详情"
    assert observed["detail"] == detail
    assert observed["read_only"] is True
    assert "该文件处理失败" in observed["labels"]
    assert "文件：C:/video/failed.mp4" in observed["labels"]
    assert "输出：C:/out/failed.mp4" in observed["labels"]
    manager.set_language(previous_language)


def test_error_detail_dialog_uses_current_language(lightweight_window, monkeypatch):
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QDialog, QLabel, QTableWidgetItem
    from ui.i18n import get_language_manager

    manager = get_language_manager()
    previous_language = manager.language
    manager.set_language("en")
    _add_rows(lightweight_window, 1)
    status_item = QTableWidgetItem()
    status_item.setData(Qt.ItemDataRole.UserRole, "failed")
    lightweight_window.video_table.setItem(0, lightweight_window.COL_STATUS, status_item)
    lightweight_window.video_list = [
        {
            "path": "C:/video/failed.mp4",
            "output_path": "C:/out/failed.mp4",
            "process_error": "encoder unavailable",
        }
    ]
    observed = {}

    def fake_exec(dialog):
        observed["title"] = dialog.windowTitle()
        observed["labels"] = [label.text() for label in dialog.findChildren(QLabel)]
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QDialog, "exec", fake_exec)
    lightweight_window.show_process_error_detail(0)

    assert observed["title"] == "Processing failure details"
    assert "This file failed to process" in observed["labels"]
    assert "File: C:/video/failed.mp4" in observed["labels"]
    assert "Output: C:/out/failed.mp4" in observed["labels"]
    manager.set_language(previous_language)


def test_lut_preview_falls_back_when_ffmpeg_cannot_start(qapp):
    from ui.lut_filter_dialog import LUTFilterDialog

    dialog = LUTFilterDialog()
    assert dialog._original_pixmap is not None
    assert not dialog._original_pixmap.isNull()

    for index, checkbox in enumerate(dialog.filter_checkboxes):
        checkbox.blockSignals(True)
        checkbox.setChecked(index == 0)
        checkbox.blockSignals(False)
    dialog.apply_switch.blockSignals(True)
    dialog.apply_switch.setChecked(True)
    dialog.apply_switch.blockSignals(False)
    dialog._preview_timer.stop()
    dialog._find_ffmpeg = lambda: "definitely-missing-ffmpeg-for-regression-test"

    dialog.update_preview_from_selection()
    deadline = time.monotonic() + 5
    while dialog._preview_inflight and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)
    qapp.processEvents()

    assert dialog._preview_inflight is False
    assert dialog._sample_pixmap is not None
    assert not dialog._sample_pixmap.isNull()
    assert dialog.sample_label.text() != "预览生成失败"
    dialog.close()


def test_options_dialog_parallel_label_uses_current_language(qapp):
    from PyQt6.QtWidgets import QLabel

    from ui.i18n import get_language_manager
    from ui.options_dialog import OptionsDialog

    manager = get_language_manager()
    previous_language = manager.language
    manager.set_language("en")
    dialog = OptionsDialog(config={"ui_language": "en"})

    labels = [label.text() for label in dialog.findChildren(QLabel)]

    assert "Parallel tasks:" in labels
    assert "Version 1.0.9" in labels
    assert "并行任务数量:" not in labels
    assert "版本 1.0.9" not in labels
    dialog.close()
    manager.set_language(previous_language)


def test_options_dialog_language_combo_applies_immediately(qapp):
    from ui.i18n import get_language_manager
    from ui.options_dialog import OptionsDialog

    manager = get_language_manager()
    previous_language = manager.language
    manager.set_language("zh_CN")
    dialog = OptionsDialog(config={"ui_language": "zh_CN"})
    idx = dialog.language_combo.findData("en")
    assert idx >= 0

    dialog.language_combo.setCurrentIndex(idx)
    qapp.processEvents()

    assert manager.language == "en"
    assert dialog.windowTitle() == "Options"
    dialog.close()
    manager.set_language(previous_language)


def test_options_dialog_tabs_are_compact(qapp):
    from ui.options_dialog import OptionsDialog

    dialog = OptionsDialog(config={"ui_language": "zh_CN"})
    button_width = sum(button.width() for button in dialog.tab_control.buttons)

    assert dialog.tab_control.width() == button_width + 8
    assert dialog.tab_control.width() < 260
    dialog.close()


def test_lut_filter_names_use_current_language(qapp):
    from ui.i18n import get_language_manager
    from ui.lut_filter_dialog import LUTFilterDialog

    manager = get_language_manager()
    previous_language = manager.language
    manager.set_language("en")
    dialog = LUTFilterDialog()
    labels = [checkbox.text() for checkbox in dialog.filter_checkboxes]

    assert "Vintage" in labels
    assert "Warm" in labels
    assert "复古" not in labels
    dialog.close()
    manager.set_language(previous_language)


def test_login_popup_retranslates_with_login_widget(qapp):
    from ui.i18n import apply_language_to_widget, get_language_manager
    from ui.login_widget import LoginWidget

    manager = get_language_manager()
    previous_language = manager.language
    manager.set_language("zh_CN")
    widget = LoginWidget()
    widget.set_user_info("", "")

    manager.set_language("en")
    apply_language_to_widget(widget)

    assert widget._login_btn.text() == "Log in"
    assert widget._popup.status_label.text() == "● Logged in"
    assert widget._popup.logout_btn.text() == "Log out"
    assert widget._popup.nickname_label.text() == "Logged-in user"
    widget.close()
    manager.set_language(previous_language)


def test_main_window_retranslates_segmented_tabs_without_clipping(qapp, monkeypatch):
    from PyQt6.QtWidgets import QLabel, QComboBox

    from ui.batch_video.main_window import BatchVideoProcessorWindow
    from ui.i18n import get_language_manager

    manager = get_language_manager()
    previous_language = manager.language
    manager.set_language("zh_CN")
    monkeypatch.setattr(BatchVideoProcessorWindow, "_init_services", lambda _self: None)
    window = BatchVideoProcessorWindow()

    manager.set_language("en")
    qapp.processEvents()
    tab_labels = [button.text() for button in window.tab_control.buttons]
    labels = [label.text() for label in window.findChildren(QLabel)]
    combo_items = [
        combo.itemText(index)
        for combo in window.findChildren(QComboBox)
        for index in range(combo.count())
    ]

    assert "Image adjustment" in tab_labels
    assert "画面调整" not in tab_labels
    assert "Region 1" in labels
    assert "Watermark #1" in labels
    assert "Text track 1" in labels
    assert "Top:" in labels
    assert "Total: 0 | Selected: 0" in labels
    assert "Center" in combo_items
    assert "区域 1" not in labels
    assert "水印 #1" not in labels
    assert "文本轨道 1" not in labels
    assert "上:" not in labels
    assert "总数: 0 | 已勾选: 0" not in labels
    assert "中间" not in combo_items
    assert "Software startup" in window.process_log.toPlainText()
    assert "软件启动" not in window.process_log.toPlainText()
    for button in window.tab_control.buttons:
        text_width = button.fontMetrics().horizontalAdvance(button.text())
        assert button.minimumWidth() >= text_width + 20
    window.close()
    manager.set_language(previous_language)


def test_batch_runner_preserves_processor_error_detail(monkeypatch, tmp_path):
    from processor import batch_video_runner

    class FailedProcessor:
        def __init__(self, _config):
            self.last_process_error = "FFmpeg返回码 1：测试编码器不可用"

        def process_video(self, *_args, **_kwargs):
            return False

    monkeypatch.setattr(batch_video_runner, "BatchParamsProcessor", FailedProcessor)
    video_path = tmp_path / "input.mp4"
    video_path.write_bytes(b"video")
    video_info = {"path": str(video_path), "row_index": 7}
    statuses = []

    batch_video_runner.process_batch(
        [video_info],
        {"output": {"path": str(tmp_path / "out")}},
        progress_callback=lambda *_args: None,
        status_callback=lambda row, status: statuses.append((row, status)),
        is_running_callback=lambda: True,
    )

    assert statuses == [(7, "processing"), (7, "failed")]
    assert video_info["process_error"] == "FFmpeg返回码 1：测试编码器不可用"


def test_all_application_modules_import(qapp, project_root_path):
    """逐个导入应用模块，发现仅在运行时暴露的缺失依赖或循环导入。"""
    module_names = []
    for package_name in ("config", "processor", "ui", "utils"):
        package_dir = project_root_path / package_name
        for file_path in package_dir.rglob("*.py"):
            relative = file_path.relative_to(project_root_path).with_suffix("")
            parts = list(relative.parts)
            if parts[-1] == "__init__":
                parts.pop()
            if parts:
                module_names.append(".".join(parts))

    for module_name in sorted(set(module_names)):
        importlib.import_module(module_name)


def test_main_window_constructs_without_online_services(qapp, monkeypatch):
    """主界面离线构造应完整，不依赖更新、广告或登录网络请求。"""
    from ui.batch_video.main_window import BatchVideoProcessorWindow

    monkeypatch.setattr(BatchVideoProcessorWindow, "_init_services", lambda _self: None)
    window = BatchVideoProcessorWindow()
    window.show()
    qapp.processEvents()

    assert window.video_table.columnCount() == 5
    assert window.minimumWidth() >= 1200
    assert window.start_btn.isEnabled()
    assert window.process_thread is None
    window.close()
