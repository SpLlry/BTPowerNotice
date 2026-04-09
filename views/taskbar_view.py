# 标准库导入
import sys
import win32con
import win32gui

# 第三方库导入
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QToolTip
from PyQt6.QtCore import Qt, QTimer

# 本地库导入
from utils.skin import SkinManager
from utils import (
    get_win11_taskbar_alignment,
    get_task_bar_w11,
    get_windows_system_theme
)
from utils.tools import log, config, dc


class RingWidget(QMainWindow):
    MAX_DEVICES = 4

    def __init__(self):
        super().__init__()
        # 必须先订阅，否则后续数据更新不会触发回调
        print("RingWidget 初始化")

        self.config = config
        self.scale = self.screen().devicePixelRatio()
        self.task_bar_hwnd = None
        self.sys_theme = "dark"
        # self.task_align = get_win11_taskbar_alignment()
        # self.task_bar = get_task_bar_w11(self.task_align)
        self.task_align = None
        self.task_bar = {}
        self.battery_items = {}
        self.progress_rings = []
        self.skin_manager = SkinManager("skin/ring/", "Ring")
        self.current_skin = self.config.getVal("Settings", "skin")

        self._init_layout()
        self._init_window()
        self._init_timer()
        self.init_rings()
        # self.update_taskbar_info(
        #     align=self.task_align, task_bar_sys=self.task_bar)
        self.update_taskbar_info(utils.get_win11_taskbar_alignment(
        ), utils.get_task_bar_w11(utils.get_win11_taskbar_alignment()))
        dc.subscribe("devices", self.update_device_data)
        dc.subscribe("system", self.update_system_info)
        dc.subscribe("config", self.update_config_info)

    # 定义一个回调

    def _init_layout(self):
        central_widget = QWidget()
        # 中央部件设置为完全透明，不捕获鼠标事件
        central_widget.setStyleSheet("background-color: rgba(255, 255, 255, 0);")

        # 创建一个水平布局作为主布局
        self.main_layout = QHBoxLayout(central_widget)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 创建背景部件，用于显示背景和捕获鼠标事件
        self.background_widget = QWidget()
        # 为背景部件设置透明背景色，确保鼠标事件能够被捕获
        self.background_widget.setStyleSheet(
            "background-color: rgba(255, 255, 255, 0.01);"
        )

        # 创建圆环布局，用于放置电量圆环
        self.rings_layout = QHBoxLayout(self.background_widget)
        self.rings_layout.setSpacing(4)
        self.rings_layout.setContentsMargins(0, 4, 0, 4)
        self.rings_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 将背景部件添加到主布局
        self.main_layout.addWidget(self.background_widget)

        self.setCentralWidget(central_widget)

    def _init_window(self):
        h = self.task_bar.get("h", 48) if self.task_bar else 48
        self.setFixedSize(int(320 / self.scale), h)
        # 保留WA_TranslucentBackground属性以实现透明效果
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
        h = self.task_bar.get("h", 48)  # 默认为 48
        w = int(self.width() / self.MAX_DEVICES)
        if w > h:
            w = h - 10
            if w < 0:
                w = 10  # 确保 w 不为负数
            self.setFixedSize(int(w) * 4, int(h))

        for i in range(self.MAX_DEVICES):
            ring_class = self.skin_manager.getSkin(self.current_skin)
            if ring_class:
                ring_size = (int(w - 2), int(h - 2))
                # 确保大小不为负数
                ring_size = (max(1, ring_size[0]), max(1, ring_size[1]))
                # print(ring_size, "ring_size")
                ring = ring_class({}, ring_size)
                ring.hide()
                self.progress_rings.append(ring)
                self.rings_layout.addWidget(ring)

    def update_config_info(self, config_info):
        show_task = config_info.get("Settings", {}).get("show_task", 0)
        if show_task == "0":
            self.hide()
        else:
            self.show()
        self.current_skin = config_info.get("Settings", {}).get(
            "skin", self.current_skin
        )
        self.reload_rings()

    def update_system_info(self, system_info):
        # print(system_info, 111)
        task_align = system_info.get("StartMenu", {}).get("align", 0)
        task_bar = system_info.get("task_bar", {})
        sys_theme = system_info.get("sys_theme", "light")
        self.update_taskbar_info(align=task_align, task_bar_sys=task_bar)
        self.set_theme(sys_theme)

    def update_taskbar_info(self, align=None, task_bar_sys=None):
        # 更新任务栏对齐方式
        # print(
        #     "update_taskbar_info", self.task_bar, task_bar_sys, align, self.task_align
        # )
        # self.update()
        if align is not None and self.task_align != align:
            log.info(f"更新任务栏对齐方式为: {align}")
            align_flag = (
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                if align == 0
                else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            self.main_layout.setAlignment(align_flag)
            self.main_layout.update()
            self.task_align = align
            # 当对齐方式改变时，重新获取任务栏信息
            self.task_bar = task_bar_sys
        # 直接更新任务栏信息
        elif task_bar_sys is not None and self.task_bar != task_bar_sys:
            log.info(f"更新任务栏信息为: {task_bar_sys}")
            self.task_bar = task_bar_sys
        # 如果没有需要更新的，直接返回
        else:
            return

        # 更新窗口位置并刷新
        # log.info(f"更新窗口位置: {task_bar_sys}")
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
            self.rings_layout.removeWidget(ring)
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
                log.info(f"设置父窗口为: {self.task_bar.get('handle')}")

            left = self.task_bar.get("l")
            if self.task_align == 0:
                left = int(left / self.scale) - int(self.width())
            top = -int(self.task_bar.get("t") / self.scale)
            # log.info(
            #     f"task_align:{self.task_align},left:{left},top:{top},width:{self.width()}"
            # )
            print(
                left, top, self.width(), self.height(), "position_window", self.task_bar
            )
            self.setGeometry(left, top, self.width(), self.height())
            # win32gui.SetWindowPos(
            #     self_hwnd,
            #     self.task_bar_hwnd,  # hWndInsertAfter (0 = HWND_TOP)
            #     self.task_bar.get("l")-self.width(),
            #     0,
            #     0, 0,
            #     win32con.SWP_NOZORDER
            #     | win32con.SWP_NOACTIVATE
            #     | win32con.SWP_SHOWWINDOW,
            # )
        except Exception as e:
            log.error(f"任务栏定位错误: {e}")

    def update_device_data(self, device_info):
        # print(device_info)
        self.battery_items = device_info

    def update_battery_ui(self):
        device_list = list(self.battery_items.values())

        # 计算实际显示的圆环数量
        visible_rings = min(len(device_list), self.MAX_DEVICES)

        # 计算每个圆环的宽度
        if visible_rings > 0:
            w = int(self.width() / self.MAX_DEVICES)
            h = self.task_bar.get("h", 0)
            if w > h:
                w = h - 10

            # 计算背景部件的宽度：圆环数量 * 圆环宽度 + (圆环数量 - 1) * 间距
            background_width = visible_rings * w + (visible_rings - 1) * 4  # 4是间距

            # 设置背景部件的大小：宽度为计算值，高度为窗口高度
            self.background_widget.setFixedSize(background_width, self.height())
        else:
            # 如果没有设备，设置背景部件为最小大小
            self.background_widget.setFixedSize(1, self.height())

        # 根据任务栏对齐方式设置背景部件在主布局中的对齐方式
        if self.task_align is not None:
            main_align_flag = (
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                if self.task_align == 0
                else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            self.main_layout.setAlignment(main_align_flag)
            self.main_layout.update()

        for i in range(self.MAX_DEVICES):
            ring = self.progress_rings[i]
            if i < len(device_list):
                ring.set_ring(device_list[i], self.sys_theme)
                ring.show()
            else:
                ring.hide()

    def paintEvent(self, event):
        # self.position_window()
        if self.screen().devicePixelRatio() != self.scale:
            self.scale = self.screen().devicePixelRatio()
        # self.position_window()
        super().paintEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RingWidget()
    window.update_device_data(
        {
            "123": {"name": "耳机", "battery": 100, "connected": True},
            "456": {"name": "键盘", "battery": 50, "connected": True},
        }
    )
    window.show()
    sys.exit(app.exec())
