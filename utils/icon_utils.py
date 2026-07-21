from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPainter, QPixmap


def _get_logo_path() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "logo.png"


def load_logo_pixmap() -> QPixmap:
    logo_path = _get_logo_path()
    if not logo_path.exists():
        return QPixmap()
    return QPixmap(str(logo_path))


def _square_pixmap(source: QPixmap, size: int) -> QPixmap:
    if source.isNull() or size <= 0:
        return QPixmap()
    target = QPixmap(size, size)
    target.fill(Qt.GlobalColor.transparent)
    scaled = source.scaled(
        QSize(size, size),
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    painter = QPainter(target)
    x = (size - scaled.width()) // 2
    y = (size - scaled.height()) // 2
    painter.drawPixmap(x, y, scaled)
    painter.end()
    return target


def build_app_logo_icon(sizes: Iterable[int] | None = None) -> QIcon:
    source = load_logo_pixmap()
    if source.isNull():
        return QIcon()
    icon = QIcon()
    icon_sizes = sizes or (16, 24, 32, 48, 64, 128, 256)
    for size in icon_sizes:
        square = _square_pixmap(source, int(size))
        if not square.isNull():
            icon.addPixmap(square)
    return icon
