import sys
import asyncio
import win32gui
from PyQt6.QtWidgets import QApplication, QMainWindow, QToolTip
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QCursor, QGuiApplication
from PyQt6.QtCore import Qt, QPoint, QRect


class RingWidget(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        # UI数据：仅主线程可修改
        self.card_size = 44
        self.battery_items = {}
        self.tray = None
        self.scale = self.screen().devicePixelRatio()
        self.task_algin = 0
        self.task_bar = self.get_task_bar_w11()
        self.sys_theme = "dark"
        self.theme = {
            "dark": {
                "background": "#1E1E1E",
                "ring": "#919191",
                "text": "#FFFFFF",
                "power": "#03dc6c",
            },
            "light": {
                "background": "#1E1E1E",
                "ring": "gray",
                "text": "#000000",
                "power": "#03dc6c",
            }
        }
        # 窗口配置
        self.setFixedSize(200, 48)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.Tool |
                            Qt.WindowType.WindowStaysOnTopHint)

        # ===================== 关键修复：开启鼠标追踪 + ToolTip配置 =====================
        self.setMouseTracking(True)  # 开启全局鼠标追踪
        QToolTip.setFont(QFont("Microsoft YaHei", 9))  # 自定义Tip字体
        self.setToolTipDuration(5000)  # Tip显示时长

        self.position_window()

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
            connect_status = "✅ 已连接" if device.get("connected", True) else "❌ 未连接"
            tip_content += f"{name}：{battery}% | {connect_status}\n"

        self.setToolTip(tip_content.strip())

    def set_task_align(self, align):
        if self.task_algin == align:
            return
        print("任务栏变化", align)
        self.task_algin = align
        self.task_bar = self.get_task_bar_w11()
        self.position_window()

    def set_theme(self, theme):
        print("主题变化", theme)
        if theme == 0:
            if self.sys_theme == 'dark':
                return
            self.sys_theme = 'dark'
        else:
            if self.sys_theme == 'light':
                return
            self.sys_theme = 'light'
        self.update()

    def update_device_data(self, device_info: dict):
        self.battery_items = device_info
        self.update_tooltip()
        self.update()

    def paintEvent(self, event):
        theme = self.theme.get(self.sys_theme)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # ===================== 关键修复：绘制全透明背景，防止鼠标穿透 =====================
        # 填充整个窗口为透明（alpha=0），让Qt认为整个窗口都有像素内容，从而接收鼠标事件
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))

        self.card_size = 44
        DEVICE_NAME_HEIGHT = 12
        RADIUS = 12
        RING_WIDTH = 4
        POWER_FONT_SIZE = 5

        center_y = self.height() // 2
        start_x = 2
        for i, (address, device) in enumerate(self.battery_items.items()):
            card_x = start_x + i * self.card_size
            card_y = center_y - self.card_size // 2
            ring_center_x = card_x + self.card_size // 2
            ring_center_y = card_y + (self.card_size - DEVICE_NAME_HEIGHT) // 2

            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(ring_center_x, ring_center_y), RADIUS, RADIUS)

            pen = QPen(QColor(theme.get('ring')), RING_WIDTH)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawEllipse(QPoint(ring_center_x, ring_center_y), RADIUS, RADIUS)

            battery_color = theme.get('power')
            battery = f"{device.get('battery', 0)}%"
            if not device.get("connected", True):
                battery = "🚫"
                battery_color = QColor(0, 0, 0)
            elif device.get("battery", 0) < 80:
                battery_color = "#F3ED03"
            elif device.get("battery", 0) < 50:
                battery_color = "#F39603"
            elif device.get("battery", 0) < 10:
                battery_color = "#F30303"
            pen = QPen(QColor(battery_color), RING_WIDTH)
            painter.setPen(pen)
            angle = int(int(device.get("battery", 0)) * 3.6)
            arc_rect = QRect(ring_center_x - RADIUS, ring_center_y - RADIUS, RADIUS * 2, RADIUS * 2)
            painter.drawArc(arc_rect, 90 * 16, -angle * 16)

            painter.setPen(QColor(theme.get('text')))
            painter.setFont(QFont("Microsoft YaHei", POWER_FONT_SIZE))
            painter.drawText(QRect(ring_center_x - 10, ring_center_y - 7, 20, 14), Qt.AlignmentFlag.AlignCenter,
                             f"{battery}")
            painter.setFont(QFont("Microsoft YaHei", 7))
            name_rect = QRect(card_x, card_y + self.card_size - DEVICE_NAME_HEIGHT, self.card_size, DEVICE_NAME_HEIGHT)
            painter.drawText(name_rect, Qt.AlignmentFlag.AlignCenter, device.get('name', '未知设备'))

    def position_window(self):
        try:
            self_hwnd = int(self.winId())
            win32gui.SetParent(self_hwnd, self.task_bar.get('handle'))
            left = self.task_bar.get('l')
            if self.task_algin == 0:
                left = int(left / self.scale) - self.width()
            print(self.task_algin, "position_window", left, self.task_bar.get('l'),
                  -int(self.task_bar.get('t') / self.scale))
            self.move(left, -int(self.task_bar.get('t') / self.scale))
        except  Exception as e:
            print(f"get_task_bar_w11 error{e}")
            screen = QGuiApplication.primaryScreen().geometry()
            self.move(10, screen.height() - 50 if screen.height() > 1080 else screen.height() - 45)

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


async def main():
    sys.excepthook = lambda exctype, value, traceback: print(f"崩溃信息: {value}")
    app = QApplication(sys.argv)
    win = RingWidget()
    win.battery_items = {
        "123": {"name": "耳机", "battery": 100, "connected": True},
        "456": {"name": "键盘", "battery": 50, "connected": True},
        "789": {"name": "鼠标", "battery": 20, "connected": False},
    }
    win.update_tooltip()
    win.show()
    while True:
        app.processEvents()
        await asyncio.sleep(0.01)


if __name__ == "__main__":
    asyncio.run(main())
