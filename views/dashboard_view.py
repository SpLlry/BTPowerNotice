# fmt: off
# 标准库导入
import sys
import os;sys.path.append(os.getcwd()) # 添加当前目录到 sys.path
# fmt: on
from turtle import bgcolor
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QMainWindow,
    QApplication,
    QPushButton,
    QLabel,
    QScrollArea,
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QTimer
from utils.tools import dc
from utils import get_icon_path
from utils.skin import SkinManager


class BluetoothBatteryApp(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = "light"
        self.sys_theme = {
            "dark": {
                "backgroud": "#141414",

            },
            "light": {
                "backgroud": "#f5f7fa",

            }
        }
        self.skin_manager = SkinManager("skin/device/", "BTDeviceCard")
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setWindowIcon(QIcon(get_icon_path("icon/icon.ico")))
        self.setWindowTitle("蓝牙设备电量")

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        central = QWidget()
        self.setCentralWidget(central)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.sys_theme[self.theme].get('backgroud', '#f5f7fa')};
                border-radius: 5px;
            }}
        """)
        # print(self.styleSheet())
        self.main_layout = QVBoxLayout(central)
        self.main_layout.setContentsMargins(5, 5, 5, 0)
        self.main_layout.setSpacing(0)

        # ========================
        # 标题栏
        # ========================
        title_bar = QWidget()
        title_bar.setFixedHeight(32)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(5, 0, 0, 0)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff; color: #555; font-size:16px;
                border: none; border-radius: 12px;
            }
            QPushButton:hover { background-color: #ff5c5c; color: white; }
        """)
        close_btn.clicked.connect(self.hide)
        title_layout.addStretch()
        title_layout.addWidget(close_btn)
        self.main_layout.addWidget(title_bar)

        # ========================
        # 滚动区域（核心）
        # ========================
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
            }

            /* 滚动条整体 */
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0px;
            }

            /* 滑块 */
            QScrollBar::handle:vertical {
                background: #c9cdd4;
                border-radius: 3px;
                min-height: 30px;
            }

            /* 滑块 hover */
            QScrollBar::handle:vertical:hover {
                background: #86909c;
            }

            /* 上下箭头 - 隐藏 */
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }

            /* 滑道 - 透明 */
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(2)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area)

        self.device_cards = {}

        dc.subscribe("devices", self.update_devices)
        dc.subscribe("system", self.update_system)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_with_animation)
        self.hide_timer_interval = 3000

    def update_system(self, system):
        system_theme = {0: "dark", 1: "light"}
        self.theme = system_theme[system["sys_theme"]]
        self.set_theme(self.theme)

    def set_theme(self, theme):
        self.theme = theme
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.sys_theme[self.theme].get('backgroud', '#f5f7fa')};
                border-radius: 5px;
            }}
        """)

    def focusOutEvent(self, event):
        pass

    def showEvent(self, event):
        self.hide_timer.start(self.hide_timer_interval)
        super().showEvent(event)

    def enterEvent(self, event):
        self.hide_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hide_timer.start(self.hide_timer_interval)
        super().leaveEvent(event)

    def hide_with_animation(self):
        self.hide()

    # ========================
    # 🔥 固定窗口高度：只显示 3 个卡片，每个 135，无多余计算
    # ========================
    def adjust_window_size(self):
        # 固定：窗口高度 = 标题32 + 3张卡片 × 135
        WINDOW_WIDTH = 320
        TITLE_HEIGHT = 32
        CARD_HEIGHT = 65
        MAX_VISIBLE_CARDS = 3

        # 窗口高度固定死：只显示 3 张卡片的高度
        total_height = TITLE_HEIGHT + CARD_HEIGHT * MAX_VISIBLE_CARDS

        self.setFixedSize(WINDOW_WIDTH, total_height)

    def update_devices(self, device_dict):
        current_dev_ids = set(device_dict.keys())

        for dev_id, info in device_dict.items():
            if dev_id in self.device_cards:
                card = self.device_cards[dev_id]
                card.set_device_info(info)
            else:
                device_card = self.skin_manager.getSkin("Default")
                card = device_card(
                    info, (285, 65), self.theme)  # 每张卡固定 135
                self.content_layout.addWidget(card)
                self.device_cards[dev_id] = card

        # 移除离线设备
        for dev_id in list(self.device_cards.keys()):
            if dev_id not in current_dev_ids:
                card = self.device_cards.pop(dev_id)
                card.hide()
                self.content_layout.removeWidget(card)
                card.deleteLater()

        self.adjust_window_size()


# ===================== 测试 =====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BluetoothBatteryApp()
    window.show()
    window.finished.connect(app.quit)

    devices = {
        "123": {"name": "耳机", "battery": 100, "connected": True},
        "456": {"name": "键盘", "battery": 50, "connected": True},
        "789": {"name": "鼠标", "battery": 75, "connected": True},
        "000": {"name": "手柄", "battery": 30, "connected": True},
        "001": {"name": "音响", "battery": 80, "connected": False},
    }
    window.update_devices(devices)
    
    sys.exit(app.exec())
