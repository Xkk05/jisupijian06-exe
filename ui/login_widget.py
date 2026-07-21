"""
登录 UI 组件
在标题栏中显示登录按钮，登录后只显示头像，点击头像出现账户弹窗。
"""

from PyQt6.QtCore import (
    QEasingCurve,
    QEvent,
    QPoint,
    QRectF,
    QUrl,
    QVariantAnimation,
    pyqtProperty,
    pyqtSignal,
    Qt,
)
from PyQt6.QtGui import QColor, QCursor, QPainter, QPainterPath, QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.theme import Theme
from ui.i18n import t
from utils.unified_logger import logger


class CircleAvatar(QLabel):
    """圆形头像组件，支持悬浮动效。"""

    def __init__(self, size: int = 32, parent=None):
        super().__init__(parent)
        self._size = size
        self._pixmap = None
        self._hover_progress = 0.0
        self.setFixedSize(size, size)

    def set_image(self, pixmap: QPixmap):
        if pixmap and not pixmap.isNull():
            self._pixmap = pixmap.scaled(
                self._size,
                self._size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            self._pixmap = None
        self.update()

    def get_hover_progress(self) -> float:
        return self._hover_progress

    def set_hover_progress(self, value: float):
        self._hover_progress = max(0.0, min(1.0, float(value)))
        self.update()

    hoverProgress = pyqtProperty(float, fget=get_hover_progress, fset=set_hover_progress)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        scale = 1.0 + self._hover_progress * 0.06
        float_y = -self._hover_progress * 1.6
        cx = self._size / 2
        cy = self._size / 2
        painter.translate(cx, cy + float_y)
        painter.scale(scale, scale)
        painter.translate(-cx, -cy)

        path = QPainterPath()
        path.addEllipse(0, 0, self._size, self._size)
        painter.setClipPath(path)

        if self._pixmap:
            x = (self._size - self._pixmap.width()) // 2
            y = (self._size - self._pixmap.height()) // 2
            painter.drawPixmap(x, y, self._pixmap)
        else:
            painter.setClipping(False)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#E2E8F0"))
            painter.drawEllipse(0, 0, self._size, self._size)

            svg_data = """
                <svg width="16" height="16" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="8" cy="5.5" r="2.5" fill="#94A3B8"/>
                    <path d="M3 13.5C3 10.5 5 9 8 9C11 9 13 10.5 13 13.5" fill="#94A3B8"/>
                </svg>
            """
            renderer = QSvgRenderer(svg_data.encode("utf-8"))
            icon_size = self._size * 0.6
            icon_rect = QRectF(
                (self._size - icon_size) / 2,
                (self._size - icon_size) / 2,
                icon_size,
                icon_size,
            )
            renderer.render(painter, icon_rect)
        painter.end()


class AccountPopup(QFrame):
    """头像下方账户浮层弹窗。"""

    logout_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setObjectName("AccountPopup")
        self.setFixedWidth(240)

        shell = QFrame(self)
        shell.setObjectName("AccountPopupShell")
        shell.setStyleSheet(
            f"""
            #AccountPopupShell {{
                background-color: {Theme.Surface};
                border: 1px solid {Theme.Border};
                border-radius: 12px;
            }}
            """
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(shell)

        layout = QVBoxLayout(shell)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(10)

        info_row = QHBoxLayout()
        info_row.setSpacing(10)
        self.avatar = CircleAvatar(36, shell)
        info_row.addWidget(self.avatar)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self.nickname_label = QLabel(t("login_widget.status.not_logged_in", "未登录"), shell)
        self.nickname_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #0F172A;")
        text_col.addWidget(self.nickname_label)

        status = QLabel(t("login_widget.status.logged_in_dot", "● 已登录"), shell)
        status.setStyleSheet("font-size: 12px; color: #16A34A;")
        text_col.addWidget(status)
        info_row.addLayout(text_col, 1)
        layout.addLayout(info_row)

        divider = QFrame(shell)
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"border: none; border-top: 1px solid {Theme.Divider};")
        layout.addWidget(divider)

        self.logout_btn = QPushButton(t("login_widget.btn.logout", "退出登录"), shell)
        self.logout_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.logout_btn.setFixedHeight(34)
        self.logout_btn.setStyleSheet(
            """
            QPushButton {
                background: #FEF2F2;
                color: #DC2626;
                border: 1px solid #FECACA;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                text-align: left;
                padding-left: 14px;
            }
            QPushButton:hover { background: #FEE2E2; }
            QPushButton:pressed { background: #FECACA; }
            """
        )
        self.logout_btn.clicked.connect(self.logout_clicked.emit)
        layout.addWidget(self.logout_btn)
        self.adjustSize()


class LoginWidget(QWidget):
    """登录组件：未登录显示按钮，已登录仅显示头像。"""

    login_clicked = pyqtSignal()
    logout_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_logged_in = False
        self._nickname = ""
        self._avatar_url = ""
        self._nam = QNetworkAccessManager(self)
        self._nam.finished.connect(self._on_avatar_loaded)

        self.setFixedHeight(44)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("background: transparent; border: none;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._login_btn = QPushButton(t("login_widget.btn.login", "登录"), self)
        self._login_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._login_btn.setFixedHeight(32)
        
        # 微调样式：增加边框可见度，增强对比
        self._login_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: #F0F9FF;  /* 极浅蓝背景 */
                color: {Theme.Primary};     /* 主色蓝字 */
                border: 1px solid #BAE6FD;  /* 浅蓝边框 (Sky-200)，增加边界感 */
                border-radius: 16px;
                padding: 0 20px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{ 
                background-color: {Theme.Primary}; 
                color: white;
                border: 1px solid {Theme.Primary};
            }}
            QPushButton:pressed {{ 
                background-color: {Theme.PrimaryPressed}; 
                color: white;
                border: 1px solid {Theme.PrimaryPressed};
            }}
            """
        )
        self._login_btn.clicked.connect(self.login_clicked.emit)
        layout.addWidget(self._login_btn)

        self._avatar_btn = QPushButton(self)
        self._avatar_btn.setFixedSize(34, 34)
        self._avatar_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._avatar_btn.setStyleSheet("QPushButton { background: transparent; border: none; }")
        self._avatar_btn.clicked.connect(self._on_avatar_clicked)
        layout.addWidget(self._avatar_btn)

        avatar_layout = QHBoxLayout(self._avatar_btn)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        avatar_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._avatar = CircleAvatar(32, self._avatar_btn)
        avatar_layout.addWidget(self._avatar)

        shadow = QGraphicsDropShadowEffect(self._avatar_btn)
        shadow.setBlurRadius(12)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(15, 23, 42, 40))
        self._avatar_btn.setGraphicsEffect(shadow)
        self._avatar_shadow = shadow

        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.setDuration(180)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_anim.valueChanged.connect(self._avatar.set_hover_progress)
        self._avatar_btn.installEventFilter(self)

        self._popup = AccountPopup(None)
        self._popup.logout_clicked.connect(self._on_popup_logout)

        self._show_login_state()

    def eventFilter(self, obj, event):
        if obj is self._avatar_btn:
            if event.type() == QEvent.Type.Enter:
                self._start_hover_anim(1.0)
                self._avatar_shadow.setBlurRadius(18)
                self._avatar_shadow.setOffset(0, 4)
            elif event.type() == QEvent.Type.Leave:
                self._start_hover_anim(0.0)
                self._avatar_shadow.setBlurRadius(12)
                self._avatar_shadow.setOffset(0, 2)
        return super().eventFilter(obj, event)

    def _start_hover_anim(self, target: float):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._avatar.hoverProgress)
        self._hover_anim.setEndValue(target)
        self._hover_anim.start()

    def _show_login_state(self):
        self._is_logged_in = False
        self._login_btn.setVisible(True)
        self._avatar_btn.setVisible(False)
        self.setFixedWidth(self._login_btn.sizeHint().width() + 8)

    def _show_user_state(self):
        self._is_logged_in = True
        self._login_btn.setVisible(False)
        self._avatar_btn.setVisible(True)
        self.setFixedWidth(42)

    def set_user_info(self, nickname: str, avatar_url: str):
        self._nickname = nickname or "已登录用户"
        self._avatar_url = self._normalize_avatar_url(avatar_url)
        self._popup.nickname_label.setText(self._nickname)
        self._show_user_state()
        if self._avatar_url:
            self._load_avatar(self._avatar_url)
        else:
            self._avatar.set_image(QPixmap())
            self._popup.avatar.set_image(QPixmap())

    def clear_user_info(self):
        self._nickname = ""
        self._avatar_url = ""
        self._avatar.set_image(QPixmap())
        self._popup.avatar.set_image(QPixmap())
        self._popup.nickname_label.setText(t("login_widget.status.not_logged_in", "未登录"))
        self._popup.hide()
        self._show_login_state()

    @staticmethod
    def _normalize_avatar_url(url: str) -> str:
        if not url:
            return ""
        normalized = str(url).strip()
        if normalized.startswith("//"):
            normalized = f"https:{normalized}"
        return normalized

    def _load_avatar(self, url: str):
        qurl = QUrl(url)
        if not qurl.isValid() or qurl.scheme() not in ("http", "https"):
            logger.warning(f"[LoginWidget] 非法头像地址: {url}")
            self._avatar.set_image(QPixmap())
            self._popup.avatar.set_image(QPixmap())
            return
        request = QNetworkRequest(qurl)
        request.setAttribute(QNetworkRequest.Attribute.Http2AllowedAttribute, False)
        request.setRawHeader(b"User-Agent", b"VideoMate/1.0")
        self._nam.get(request)

    def _on_avatar_loaded(self, reply: QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = bytes(reply.readAll())
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            if not pixmap.isNull():
                self._avatar.set_image(pixmap)
                self._popup.avatar.set_image(pixmap)
        else:
            logger.warning(f"[LoginWidget] 头像加载失败: {reply.errorString()}")
        reply.deleteLater()

    def _on_avatar_clicked(self):
        if not self._is_logged_in:
            return
        global_pos = self._avatar_btn.mapToGlobal(QPoint(0, self._avatar_btn.height() + 8))

        # 约束弹窗位置，避免越界（先用当前屏幕，再兜底主屏）
        screen = self.screen()
        if screen is None:
            from PyQt6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()
        available = screen.availableGeometry()

        self._popup.adjustSize()
        popup_w = self._popup.width()
        popup_h = self._popup.height()

        # 优先右对齐（使弹窗向左偏移），避免超出窗口右边界
        # x = global_pos.x()  # 原左对齐
        x = global_pos.x() + self._avatar_btn.width() - popup_w
        y = global_pos.y()

        # 优先显示在头像下方，不够则显示在上方
        if y + popup_h > available.bottom() - 4:
            top_y = self._avatar_btn.mapToGlobal(QPoint(0, 0)).y()
            y = top_y - popup_h - 8

        # 水平方向边界约束
        min_x = available.left() + 4
        max_x = max(min_x, available.right() - popup_w - 4)
        x = min(max(x, min_x), max_x)

        # 垂直方向边界兜底
        min_y = available.top() + 4
        max_y = max(min_y, available.bottom() - popup_h - 4)
        y = min(max(y, min_y), max_y)

        self._popup.move(QPoint(x, y))
        self._popup.show()
        self._popup.raise_()

    def _on_popup_logout(self):
        self._popup.hide()
        self.logout_clicked.emit()
