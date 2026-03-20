import sys

import win32gui
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QToolTip
)
from PyQt6.QtCore import Qt, QTimer

import utils
from config import create_config
# 导入皮肤管理器
from skin import SkinManager


class RingWidget(QMainWindow):
    def __init__(self, config):
        super().__init__()

        # 模拟蓝牙设备电量数据
        self.scale = self.screen().devicePixelRatio()
        self.task_bar_hwnd = None
        self.sys_theme = 'light'
        self.task_algin = None
        self.task_bar = self.get_task_bar_w11()
        self.config = config

        # 初始数据为空
        self.battery_items = {}

        # 1. 初始化布局【完全不变】
        central_widget = QWidget()
        self.main_layout = QHBoxLayout(central_widget)
        self.main_layout.setSpacing(4)

        self.setCentralWidget(central_widget)
        self.main_layout.setContentsMargins(0, 4, 0, 4)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.main_layout.setStretch(0, 0)

        # 2. 存储所有圆环控件
        self.progress_rings = []

        # 3. 初始化皮肤管理器
        self.skin_manager = SkinManager("ui/ring/")
        self.current_skin = self.config.getVal("setting", "skin")

        # 4. 定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_battery_ui)
        self.update_timer.start(1000)

        # 窗口配置【完全不变】
        self.setFixedSize(int(320 / self.scale), self.task_bar.get('h', 0))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.Tool |
                            Qt.WindowType.WindowStaysOnTopHint)

        self.setMouseTracking(True)
        QToolTip.setFont(QFont("Microsoft YaHei", 9))
        self.setToolTipDuration(5000)

        # ======================
        # ✅ 初始化创建4个组件 → 默认全部隐藏
        # ======================
        self.init_rings()

        self.set_task_align(utils.get_win11_taskbar_alignment())

    # ===================== 新增：手动控制鼠标进入/离开事件 =====================
    def enterEvent(self, event):
        super().enterEvent(event)
        # 鼠标进入窗口任意区域（包括透明背景）时，立即显示ToolTip
        self.update_tooltip()
        if self.toolTip():
            # 在鼠标当前位置显示Tip
            QToolTip.showText(QCursor.pos(), self.toolTip(), self)
        event.accept()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        # 鼠标离开窗口时，隐藏ToolTip
        QToolTip.hideText()
        event.accept()

    # ===================== 原有ToolTip生成逻辑 =====================
    def update_tooltip(self):
        """生成设备电量信息，用于鼠标悬浮显示"""
        if not self.battery_items:
            self.setToolTip("暂无设备连接")
            return

        tip_content = "📊 设备电量详情\n"
        for addr, device in self.battery_items.items():
            name = device.get("name", "未知设备")
            battery = device.get("battery", 0)
            connect_status = "✅ 已连接" if device.get("connected", True) else "🚫 未连接"
            tip_content += f"{name}：{battery}% | {connect_status}\n"

        self.setToolTip(tip_content.strip())

    # ======================
    # 新增：一次性创建4个圆环 → 全部隐藏
    # 完全用你的尺寸逻辑：w = int(self.width() /4)*self.scale
    # ======================
    def init_rings(self):
        w = int(self.width() / 4)
        h = self.task_bar.get('h', 0)
        if w > h:
            w = h - 10
        print("w", w, h)
        # 创建4个，全部隐藏
        for i in range(4):
            # 使用皮肤管理器获取当前皮肤的Ring类
            ring_class = self.skin_manager.getSkin(self.current_skin)
            # print(ring_class)
            if ring_class:
                ring = ring_class({}, (int(w - 4), int(h - 4)))
                # PyQt6.QtCore.QRectF(10.0, 5.0, 30.0, 30.0) 40 48
                # PyQt6.QtCore.QRectF(5.0, 5.0, 30.0, 30.0) 40 96
                ring.hide()  # 默认隐藏
                self.progress_rings.append(ring)
                self.main_layout.addWidget(ring)
            else:
                print(f"无法加载皮肤: {self.current_skin}")

    def set_task_align(self, align):
        if self.task_algin == align:
            return
        if align == 0:
            self.main_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        else:
            self.main_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.main_layout.update()
        self.task_algin = align
        self.task_bar = self.get_task_bar_w11()
        self.position_window()
        self.update()

    def set_theme(self, theme):
        if theme == 0:
            if self.sys_theme == 'dark':
                return
            self.sys_theme = 'dark'
        else:
            if self.sys_theme == 'light':
                return
            self.sys_theme = 'light'
        self.update()

    def position_window(self):
        try:
            self_hwnd = int(self.winId())
            if self.task_bar_hwnd != self.task_bar.get('handle'):
                self.task_bar_hwnd = self.task_bar.get('handle')
                win32gui.SetParent(self_hwnd, self.task_bar.get('handle'))
            left = self.task_bar.get('l')
            # print(self.scale)
            if self.task_algin == 0:
                left = int(left / self.scale) - self.width()

            self.move(left, -int(self.task_bar.get('t') / self.scale))
        except Exception as e:
            print(f"position error {e}")

    def get_task_bar_w11(self):
        task_bar = "Shell_TrayWnd"
        hwnd = win32gui.FindWindow(task_bar, None)
        h1 = hwnd
        if self.task_algin == 0:
            h1 = win32gui.FindWindowEx(hwnd, None, "TrayNotifyWnd", None)
        if not hwnd:
            return None
        left, top, right, bottom = win32gui.GetWindowRect(h1)
        return {"handle": hwnd, "t": top, "l": left, "r": right, "b": bottom, "w": right - left, "h": bottom - top}

    # ======================
    # ✅ 外部调用更新数据
    # ======================
    def update_device_data(self, device_info):
        self.battery_items = device_info

    # ======================
    # ✅ 刷新：有数据显示，没数据隐藏
    # // 不重建、不重启动画

    # ======================
    def update_battery_ui(self):
        device_list = list(self.battery_items.values())

        for i in range(4):  # 固定4个控件
            ring = self.progress_rings[i]
            if i < len(device_list):
                # 有数据 → 显示 + 更新
                ring.set_ring(device_list[i], self.sys_theme)
                ring.show()
            else:
                # 没数据 → 隐藏
                ring.hide()

    def paintEvent(self, event):
        super().paintEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RingWidget(create_config())

    # 外部调用刷新数据（测试）
    window.update_device_data({
        "123": {"name": "耳机", "battery": 100, "connected": True},
        "456": {"name": "键盘", "battery": 50, "connected": True},
        "1": {"name": "键盘", "battery": 90, "connected": True},
    })

    window.show()
    sys.exit(app.exec())
