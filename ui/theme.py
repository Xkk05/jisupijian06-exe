from enum import Enum

class Theme:
    """Slate + Blue 主题系统"""
    
    # 配色方案
    Background = "#F8FAFC"      # Slate-50: 全局背景
    Surface = "#FFFFFF"         # White: 卡片背景
    
    # 主色调
    Primary = "#3B82F6"         # Blue-500: 主按钮、选中、焦点
    PrimaryHover = "#2563EB"    # Blue-600: 悬停
    PrimaryPressed = "#1D4ED8"  # Blue-700: 按下
    PrimaryLight = "#EFF6FF"    # Blue-50: 浅色背景（选中项背景等）
    
    # 文本颜色
    TextPrimary = "#0F172A"     # Slate-900: 主要文本
    TextSecondary = "#64748B"   # Slate-500: 次要文本、说明
    TextDisabled = "#94A3B8"    # Slate-400: 禁用文本
    TextOnPrimary = "#FFFFFF"   # 主色上的文本
    
    # 边框与分割线
    Border = "#E2E8F0"          # Slate-200: 边框
    BorderFocus = "#3B82F6"     # 焦点边框
    Divider = "#F1F5F9"         # Slate-100: 分割线
    
    # 功能色
    Success = "#10B981"         # Emerald-500
    Warning = "#F59E0B"         # Amber-500
    Error = "#EF4444"           # Red-500
    
    # 字体配置 (可以根据系统调整)
    FontFamily = "Microsoft YaHei UI, Segoe UI, Microsoft YaHei, sans-serif"
    
    @staticmethod
    def global_stylesheet() -> str:
        """全局样式表，应用于 QApplication"""
        return f"""
            QWidget {{
                color: {Theme.TextPrimary};
            }}
            
            QMainWindow, QDialog {{
                background-color: {Theme.Background};
            }}

            /* 强制所有 ScrollArea 和 Viewport 使用正确背景 */
            QScrollArea, QAbstractScrollArea {{
                background-color: transparent;
                border: none;
            }}
            
            /* 滚动条美化 */
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: #CBD5E1;
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #94A3B8;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            
            QScrollBar:horizontal {{
                background: transparent;
                height: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background: #CBD5E1;
                min-width: 20px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: #94A3B8;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            
            /* Tooltip */
            QToolTip {{
                background-color: {Theme.TextPrimary};
                color: {Theme.Surface};
                border: none;
                padding: 5px;
                border-radius: 4px;
            }}
            
            /* ComboBox */
            QComboBox {{
                background-color: {Theme.Surface};
                color: {Theme.TextPrimary};
                border: 1px solid {Theme.Border};
                border-radius: 8px;
                padding: 6px 12px;
                padding-right: 30px;
                min-height: 24px;
                font-size: 13px;
            }}
            
            QComboBox:hover {{
                border-color: {Theme.Primary};
            }}
            
            QComboBox:focus {{
                border: 2px solid {Theme.Primary};
                padding: 5px 11px;
                padding-right: 29px;
                border-radius: 8px;
            }}
            
            QComboBox:disabled {{
                background-color: {Theme.Background};
                color: {Theme.TextDisabled};
                border-color: {Theme.Divider};
            }}
            
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 24px;
                border: none;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                background-color: transparent;
                border-left: 1px solid {Theme.Divider};
            }}
            
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {Theme.TextSecondary};
                width: 0px;
                height: 0px;
                margin-right: 6px;
            }}
            
            QComboBox::down-arrow:hover {{
                border-top-color: {Theme.Primary};
            }}
            
            QComboBox::down-arrow:disabled {{
                border-top-color: {Theme.TextDisabled};
            }}
            
            QComboBox QAbstractItemView {{
                background-color: {Theme.Surface};
                color: {Theme.TextPrimary};
                border: 1px solid {Theme.Border};
                border-radius: 8px;
                padding: 4px;
                selection-background-color: {Theme.PrimaryLight};
                selection-color: {Theme.Primary};
                outline: none;
            }}
            
            QComboBox QAbstractItemView::item {{
                padding: 8px 12px;
                border-radius: 4px;
                min-height: 24px;
            }}
            
            QComboBox QAbstractItemView::item:hover {{
                background-color: {Theme.PrimaryLight};
                color: {Theme.Primary};
            }}
            
            QComboBox QAbstractItemView::item:selected {{
                background-color: {Theme.Primary};
                color: {Theme.Surface};
            }}
            
            /* Menu */
            QMenu {{
                background-color: {Theme.Surface};
                color: {Theme.TextPrimary};
                border: 1px solid {Theme.Border};
                border-radius: 8px;
                padding: 4px;
            }}
            
            QMenu::item {{
                padding: 8px 30px 8px 12px;
                border-radius: 4px;
                min-height: 24px;
            }}
            
            QMenu::item:selected {{
                background-color: {Theme.Primary};
                color: {Theme.Surface};
            }}
            
            QMenu::item:disabled {{
                color: {Theme.TextDisabled};
            }}
            
            QMenu::separator {{
                height: 1px;
                background-color: {Theme.Divider};
                margin: 4px 8px;
            }}
            
            QMenu::icon {{
                padding-left: 8px;
            }}
        """
