from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QSizePolicy
from PyQt6.QtCore import (
    Qt,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    QRect,
    pyqtSignal,
    QPoint,
)
from PyQt6.QtGui import QFont, QPainter, QColor,  QPaintEvent

import utils


class IslandNotification(QWidget):
    """灵动岛通知窗口"""

    closed = pyqtSignal()

    # 存储所有活动的通知窗口
    _active_notifications = []

    def __init__(self, parent=None):
        super().__init__(parent)
        self.animation_duration = 300  # 动画持续时间(毫秒)
        self.display_duration = 3000  # 消息显示时长(毫秒)
        self.margin = 10  # 窗口距屏幕边缘距离
        self.is_dark = utils.get_windows_system_theme() == 0  # 检测系统深色模式

        self.setup_ui()
        self.setup_animation()

        # 添加到活动列表
        IslandNotification._active_notifications.append(self)
        self._update_positions()

    @classmethod
    def _update_positions(cls):
        """更新所有通知窗口的位置，防止重叠"""
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QScreen

        app = QApplication.instance()
        if not app:
            return
        screen: QScreen = app.primaryScreen()
        if not screen:
            return
        screen_geometry = screen.availableGeometry()

        # 从下往上排列，最新的在最下面
        for i, notification in enumerate(cls._active_notifications):
            x = screen_geometry.right() - notification.width() - notification.margin
            y = screen_geometry.top() + notification.margin + i * (notification.height() + notification.margin)
            notification.setGeometry(QRect(x, y, notification.width(), notification.height()))

    def paintEvent(self, event: QPaintEvent):
        """绘制圆角背景和边框"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 根据深浅色模式设置颜色
        if self.is_dark:
            bg_color = QColor(45, 45, 45, 245)
            border_color = QColor(255, 255, 255, 30)
        else:
            bg_color = QColor(255, 255, 255, 245)
            border_color = QColor(0, 0, 0, 30)

        # 绘制圆角矩形背景
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(self.rect(), 18, 18)

        # 绘制边框
        painter.setPen(border_color)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 18, 18)

    def setup_ui(self):
        """设置UI界面"""
        self.setFixedSize(320, 75)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint  # 无边框
            | Qt.WindowType.Tool  # 工具窗口
            | Qt.WindowType.WindowStaysOnTopHint  # 始终置顶
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # 透明背景
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)  # 关闭时删除

        # 根据深浅色模式设置颜色
        if self.is_dark:
            text_color = "white"
            subtext_color = "#A0A0A0"
        else:
            text_color = "#1F2937"
            subtext_color = "#6B7280"

        # 创建布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 12, 16, 12)
        self.main_layout.setSpacing(4)

        # 标题行
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)

        # 标题标签
        self.title_label = QLabel()
        self.title_label.setFont(QFont("微软雅黑", 12, QFont.Weight.Bold))
        self.title_label.setStyleSheet(f"color: {text_color}; background: transparent;")
        self.title_label.setMinimumWidth(280)
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        title_layout.addWidget(self.title_label)

        title_layout.addStretch()
        self.main_layout.addLayout(title_layout)

        # 内容行
        content_layout = QHBoxLayout()
        content_layout.setSpacing(8)

        # 内容标签
        self.content_label = QLabel()
        self.content_label.setFont(QFont("微软雅黑", 10))
        self.content_label.setStyleSheet(f"color: {subtext_color}; background: transparent;")
        self.content_label.setWordWrap(True)
        self.content_label.setMinimumWidth(280)
        self.content_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        content_layout.addWidget(self.content_label)

        content_layout.addStretch()
        self.main_layout.addLayout(content_layout)

        # 自动隐藏定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.hide_animation)

    def setup_animation(self):
        """设置滑入滑出动画"""
        self.slide_animation = QPropertyAnimation(self, b"pos")
        self.slide_animation.setDuration(self.animation_duration)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _is_fullscreen(self):
        """检查是否有窗口处于全屏模式"""
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        if not app:
            return False

        # 遍历所有窗口
        for window in app.allWidgets():
            try:
                if window and window.isVisible():
                    # 获取窗口状态
                    if window.windowState() & Qt.WindowState.WindowFullScreen:
                        return True
            except (RuntimeError, AttributeError):
                continue

        return False

    def show_message(self, title: str, content: str, duration: int = None):
        """显示通知消息

        Args:
            title: 通知标题
            content: 通知内容
            duration: 显示时长(毫秒)，默认3秒
        """
        # 检查是否全屏，如果是则不显示
        if self._is_fullscreen():
            self.close()
            return

        # 更新界面显示
        self.title_label.setText(title)
        self.content_label.setText(content)

        # 设置显示时长
        if duration is not None:
            self.display_duration = duration

        # 定位窗口并显示
        self.position_window()
        self.show()
        self.slide_in()

        # 启动自动隐藏定时器
        self.timer.start(self.display_duration)

    def position_window(self):
        """定位窗口到屏幕右上角"""
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QScreen

        app: QApplication = QApplication.instance()
        if not app:
            return
        screen: QScreen = app.primaryScreen()
        if not screen:
            return
        screen_geometry = screen.availableGeometry()

        # 获取当前窗口在列表中的位置
        idx = IslandNotification._active_notifications.index(self)
        x = screen_geometry.right() - self.width() - self.margin
        y = screen_geometry.top() + self.margin + idx * (self.height() + self.margin)
        self.setGeometry(QRect(x, y, self.width(), self.height()))

    def slide_in(self):
        """滑入动画：从上方滑入"""
        start_pos = QPoint(self.x(), self.y() - 30)
        end_pos = QPoint(self.x(), self.y())
        self.slide_animation.setStartValue(start_pos)
        self.slide_animation.setEndValue(end_pos)
        self.slide_animation.start()

    def slide_out(self):
        """滑出动画：向上滑出"""
        start_pos = self.pos()
        end_pos = QPoint(self.x(), self.y() - 30)
        self.slide_animation.setStartValue(start_pos)
        self.slide_animation.setEndValue(end_pos)
        self.slide_animation.finished.connect(self._do_close)
        self.slide_animation.start()

    def _do_close(self):
        """动画完成后执行关闭"""
        self.slide_animation.finished.disconnect(self._do_close)
        self.close()

    def hide_animation(self):
        """触发自动隐藏动画"""
        self.timer.stop()
        self.slide_out()

    def closeEvent(self, event):
        """关闭事件处理"""
        self.timer.stop()

        # 从活动列表中移除
        if self in IslandNotification._active_notifications:
            IslandNotification._active_notifications.remove(self)

        # 更新其他窗口位置
        IslandNotification._update_positions()

        self.closed.emit()
        super().closeEvent(event)


def show_island_notification(
    title: str, content: str, duration: int = 3000, parent=None
):
    """显示灵动岛通知的便捷函数

    Args:
        title: 通知标题
        content: 通知内容
        duration: 显示时长(毫秒)，默认3秒
        parent: 父窗口

    Returns:
        IslandNotification: 通知窗口对象，如果处于全屏模式则返回None
    """
    # 先检查是否全屏
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt

    app = QApplication.instance()
    if app:
        for window in app.allWidgets():
            try:
                if window and window.isVisible():
                    if window.windowState() & Qt.WindowState.WindowFullScreen:
                        return None
            except (RuntimeError, AttributeError):
                continue

    widget = IslandNotification(parent)
    widget.show_message(title, content, duration)
    return widget


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    show_island_notification("测试标题1", "这是第一条测试消息")
    show_island_notification("测试标题2", "这是第二条测试消息内容这是第二条测试消息内容这是第二条测试消息内容")
    show_island_notification("测试标题3", "这是第三条消息")
    sys.exit(app.exec())
