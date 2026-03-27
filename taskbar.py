import sys
import win32gui
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QToolTip
from PyQt6.QtCore import Qt, QTimer

import utils
from skin import SkinManager
from tools import log, config


class RingWidget(QMainWindow):
    MAX_DEVICES = 4

    def __init__(self):
        super().__init__()
        self.config = config
        self.scale = self.screen().devicePixelRatio()
        self.task_bar_hwnd = None
        self.sys_theme = "light"
        self.task_align = None
        self.task_bar = self.get_task_bar_w11()
        self.battery_items = {}
        self.progress_rings = []
        self.skin_manager = SkinManager("ui/ring/")
        self.current_skin = self.config.getVal("Settings", "skin")

        self._init_layout()
        self._init_window()
        self._init_timer()
        self.init_rings()
        self.set_task_align(utils.get_win11_taskbar_alignment())

    def _init_layout(self):
        central_widget = QWidget()
        self.main_layout = QHBoxLayout(central_widget)
        self.main_layout.setSpacing(4)
        self.main_layout.setContentsMargins(0, 4, 0, 4)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.setCentralWidget(central_widget)

    def _init_window(self):
        h = self.task_bar.get("h", 40) if self.task_bar else 40
        self.setFixedSize(int(320 / self.scale), h)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setMouseTracking(True)
        QToolTip.setFont(QFont("Microsoft YaHei", 9))
        self.setToolTipDuration(5000)

    def _init_timer(self):
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_battery_ui)
        self.update_timer.start(2000)

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update_tooltip()
        if self.toolTip():
            QToolTip.showText(QCursor.pos(), self.toolTip(), self)
        event.accept()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        QToolTip.hideText()
        event.accept()

    def update_tooltip(self):
        if not self.battery_items:
            self.setToolTip("暂无设备连接")
            return

        tip_content = "📊 设备电量详情\n"
        for addr, device in self.battery_items.items():
            name = device.get("name", "未知设备")
            battery = device.get("battery", 0)
            status = "✅ 已连接" if device.get("connected", True) else "🚫 未连接"
            tip_content += f"{name}：{battery}% | {status}\n"

        self.setToolTip(tip_content.strip())

    def init_rings(self):
        w = int(self.width() / self.MAX_DEVICES)
        h = self.task_bar.get("h", 0)
        if w > h:
            w = h - 10

        for i in range(self.MAX_DEVICES):
            ring_class = self.skin_manager.getSkin(self.current_skin)
            if ring_class:
                ring = ring_class({}, (int(w - 4), int(h - 4)))
                ring.hide()
                self.progress_rings.append(ring)
                self.main_layout.addWidget(ring)

    def set_task_align(self, align):
        if self.task_align == align:
            return

        align_flag = (
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            if align == 0
            else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.main_layout.setAlignment(align_flag)
        self.main_layout.update()

        self.task_align = align
        self.task_bar = self.get_task_bar_w11()
        self.position_window()
        self.update()

    def set_theme(self, theme):
        new_theme = "dark" if theme == 0 else "light"
        if self.sys_theme == new_theme:
            return
        self.sys_theme = new_theme
        self.update()

    def change_skin(self, skin_name):
        if skin_name == self.current_skin:
            return
        self.current_skin = skin_name
        self.reload_rings()

    def reload_rings(self):
        for ring in self.progress_rings:
            self.main_layout.removeWidget(ring)
            ring.deleteLater()
        self.progress_rings.clear()
        self.init_rings()
        self.update_battery_ui()

    def position_window(self):
        try:
            self_hwnd = int(self.winId())
            if self.task_bar_hwnd != self.task_bar.get("handle"):
                self.task_bar_hwnd = self.task_bar.get("handle")
                win32gui.SetParent(self_hwnd, self.task_bar.get("handle"))

            left = self.task_bar.get("l")
            if self.task_align == 0:
                left = int(left / self.scale) - self.width()

            self.move(left, -int(self.task_bar.get("t") / self.scale))
        except Exception as e:
            log.error(f"任务栏定位错误: {e}")

    def get_task_bar_w11(self):
        task_bar = "Shell_TrayWnd"
        hwnd = win32gui.FindWindow(task_bar, None)
        h1 = hwnd
        if self.task_align == 0:
            h1 = win32gui.FindWindowEx(hwnd, None, "TrayNotifyWnd", None)
        if not hwnd:
            return None
        left, top, right, bottom = win32gui.GetWindowRect(h1)
        return {
            "handle": hwnd,
            "t": top,
            "l": left,
            "r": right,
            "b": bottom,
            "w": right - left,
            "h": bottom - top,
        }

    def update_device_data(self, device_info):
        self.battery_items = device_info

    def update_battery_ui(self):
        device_list = list(self.battery_items.values())

        for i in range(self.MAX_DEVICES):
            ring = self.progress_rings[i]
            if i < len(device_list):
                ring.set_ring(device_list[i], self.sys_theme)
                ring.show()
            else:
                ring.hide()

    def paintEvent(self, event):
        super().paintEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RingWidget()
    window.update_device_data({
        "123": {"name": "耳机", "battery": 100, "connected": True},
        "456": {"name": "键盘", "battery": 50, "connected": True},
    })
    window.show()
    sys.exit(app.exec())
