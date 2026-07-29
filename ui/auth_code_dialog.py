# -*- coding: utf-8 -*-
"""授权码验证弹窗。"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.components import ModernButton, ModernInput
from ui.i18n import t
from ui.theme import Theme
from utils.auth_code_service import AuthCodeService, DEFAULT_AUTH_CODE_URL
from utils.icon_utils import load_logo_pixmap


class AuthCodeDialog(QDialog):
    """输入并验证鲲穹工具箱授权码。"""

    def __init__(
        self,
        auth_service: AuthCodeService,
        auth_code_url: str = DEFAULT_AUTH_CODE_URL,
        parent=None,
    ):
        super().__init__(parent)
        self._auth_service = auth_service
        self._auth_code_url = auth_code_url or DEFAULT_AUTH_CODE_URL
        self._is_verifying = False

        self.setWindowTitle(t("auth_code_dialog.title", "鲲穹AI工具箱・软件授权验证"))
        self.setModal(True)
        self.setFixedWidth(480)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"QDialog {{ background-color: {Theme.Background}; }}")

        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(18)

        shell = QFrame(self)
        shell.setObjectName("auth_code_shell")
        shell.setStyleSheet(
            f"""
            QFrame#auth_code_shell {{
                background-color: {Theme.Surface};
                border: 1px solid {Theme.Border};
                border-radius: 10px;
            }}
            QLabel {{
                background: transparent;
            }}
            """
        )
        outer.addWidget(shell)

        layout = QVBoxLayout(shell)
        layout.setContentsMargins(28, 28, 28, 24)
        layout.setSpacing(18)

        header = QHBoxLayout()
        header.setSpacing(10)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo_label = QLabel(shell)
        pixmap = load_logo_pixmap()
        if isinstance(pixmap, QPixmap) and not pixmap.isNull():
            logo_label.setPixmap(
                pixmap.scaled(
                    30,
                    30,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        header.addWidget(logo_label)

        title = QLabel(t("auth_code_dialog.title", "鲲穹AI工具箱・软件授权验证"), shell)
        title.setStyleSheet(
            """
            font-size: 18px;
            font-weight: 600;
            color: #111827;
            """
        )
        header.addWidget(title)
        layout.addLayout(header)

        description = QLabel(
            t(
                "auth_code_dialog.description",
                "您当前安装的工具为鲲穹AI工具箱生态应用，需通过工具箱授权码完成激活，以启用完整功能。",
            ),
            shell,
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setStyleSheet(
            f"""
            font-size: 14px;
            line-height: 1.5;
            color: {Theme.TextSecondary};
            """
        )
        layout.addWidget(description)

        self.code_input = QLineEdit(shell)
        self.code_input.setPlaceholderText(
            t("auth_code_dialog.placeholder.code", "请输入鲲穹AI工具箱授权码")
        )
        self.code_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.code_input.returnPressed.connect(self._verify)
        ModernInput.apply_style(self.code_input)
        self.code_input.setMinimumHeight(42)
        layout.addWidget(self.code_input)

        self.error_label = QLabel("", shell)
        self.error_label.setWordWrap(True)
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setStyleSheet(
            """
            font-size: 13px;
            color: #B91C1C;
            """
        )
        self.error_label.hide()
        layout.addWidget(self.error_label)

        self.verify_btn = ModernButton(
            t("auth_code_dialog.btn.verify", "验证并激活"),
            ModernButton.Style.Primary,
            shell,
        )
        self.verify_btn.setMinimumHeight(42)
        self.verify_btn.clicked.connect(self._verify)
        layout.addWidget(self.verify_btn)

        footer = QWidget(shell)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 2, 0, 0)
        footer_layout.setSpacing(4)
        footer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        footer_text = QLabel(t("auth_code_dialog.footer.no_code", "未获取授权码？"), footer)
        footer_text.setStyleSheet(f"font-size: 13px; color: {Theme.TextDisabled};")
        footer_layout.addWidget(footer_text)

        get_code_btn = QPushButton(
            t("auth_code_dialog.btn.get_code", "点击此处获取"), footer
        )
        get_code_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        get_code_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {Theme.Primary};
                font-size: 13px;
                font-weight: 500;
                padding: 0;
            }}
            QPushButton:hover {{
                color: {Theme.PrimaryHover};
                text-decoration: underline;
            }}
            """
        )
        get_code_btn.clicked.connect(self._open_auth_code_page)
        footer_layout.addWidget(get_code_btn)
        layout.addWidget(footer)

    def _set_busy(self, busy: bool) -> None:
        self._is_verifying = busy
        self.code_input.setEnabled(not busy)
        self.verify_btn.setEnabled(not busy)
        self.verify_btn.setText(
            t("auth_code_dialog.btn.verifying", "正在验证...")
            if busy
            else t("auth_code_dialog.btn.verify", "验证并激活")
        )

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.setVisible(bool(message))

    def _verify(self) -> None:
        if self._is_verifying:
            return
        auth_code = self.code_input.text().strip()
        if not auth_code:
            self._show_error(t("auth_code_dialog.error.empty_code", "请输入授权码"))
            return

        self._set_busy(True)
        self._show_error("")
        try:
            result = self._auth_service.verify_auth_code(auth_code)
            if result.success and result.is_valid:
                self.accept()
                return
            self._show_error(
                result.message
                or t("auth_code_dialog.error.invalid_code", "授权码无效或已过期")
            )
        finally:
            self._set_busy(False)

    def _open_auth_code_page(self) -> None:
        try:
            self._auth_service.open_get_auth_code_page(self._auth_code_url)
            self._show_error("")
        except Exception as exc:
            self._show_error(
                t(
                    "auth_code_dialog.error.open_page_failed",
                    "打开授权码页面失败: {error}",
                    error=exc,
                )
            )
