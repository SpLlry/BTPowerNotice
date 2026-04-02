from PyQt6.QtWidgets import QApplication, QWidget, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from PyQt6.QtGui import QPainter, QColor, QFont, QPixmap, QPen
from PyQt6.QtCore import Qt


class BTDeviceCard(QFrame):
    def __init__(self, device_info, size, theme="light"):
        super().__init__()
        self.device_info = device_info
        width, height = size
        self.setFixedSize(int(width), int(height))
        self.theme = theme
        self.sys_theme = {
            "dark": {
                "backgroud": "#1d1e1f",
                "ring": "#gray",
                "text": "#FFFFFF",
                "power": "#03dc6c",
            },
            "light": {
                "backgroud": "#fff",
                "ring": "gray",
                "text": "#000000",
                "power": "#03dc6c",
            }
        }
        self.theme = self.sys_theme[theme]
        # print(self.theme)
        self.setStyleSheet(f"""
        QFrame {{
            background-color: {self.theme.get('backgroud', '#fff')};
            border-radius: 16px;
                }}
        """)
        # print(self.theme.get('background', '#fff'))
        self.setup_ui()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        # main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(5)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 左侧 B 图标（正常居中，不变）
        # icon_label = QLabel()
        # icon_label.setFixedSize(40, 40)
        # icon_label.setStyleSheet("background: transparent;")
        # pixmap = QPixmap(40, 40)
        # pixmap.fill(Qt.GlobalColor.transparent)
        # painter = QPainter(pixmap)
        # painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # painter.setBrush(QColor("#e8f4ff"))
        # painter.setPen(Qt.PenStyle.NoPen)
        # painter.drawEllipse(0, 0, 40, 40)
        # painter.setPen(QColor("#3080e8"))
        # painter.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        # painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "B")
        # painter.end()
        # icon_label.setPixmap(pixmap)
        # main_layout.addWidget(icon_label)

        # 信息区域
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.name_label = QLabel(self.device_info.get("name", "未知设备"))
        self.name_label.setStyleSheet(
            f"color: {self.theme.get('text', '#1a1a1a')}; font-size: 11pt; font-weight: bold; background: transparent;")
        info_layout.addWidget(self.name_label)

        row_layout = QHBoxLayout()
        self.addr_label = QLabel(f"{self.device_info.get('address', '未知地址')}")
        self.addr_label.setStyleSheet(
            "color: #3080e8; font-size: 9pt; background: transparent;")
        row_layout.addWidget(self.addr_label)
        row_layout.addStretch()
        info_layout.addLayout(row_layout)
        main_layout.addLayout(info_layout, 1)

        # ======================
        # 你的要求：电池容器 = 卡片高度（正方形）
        # ======================
        self.battery_container = QWidget()
        self.battery_container.setFixedSize(self.height()-20, self.height()-20)
        self.battery_container.setStyleSheet("background: transparent;")
        self.battery_container.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground)
        self.battery_container.paintEvent = self.battery_paintEvent

        # 🔥 关键修复：让容器在布局里垂直居中
        main_layout.addWidget(self.battery_container,
                              alignment=Qt.AlignmentFlag.AlignVCenter)

    def set_device_info(self, device_info):
        self.device_info = device_info
        self.battery_container.update()

    # ======================
    # 🔥 绝对居中绘制（无任何写死）
    # ======================
    def battery_paintEvent(self, event):
        painter = QPainter(self.battery_container)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. 获取容器大小（正方形）
        container_size = self.battery_container.width()

        # 2. 圆环大小（自动缩放，留10%边距）
        circle_radius = int(container_size * 0.4)   # 半径 = 容器的40%
        circle_diameter = circle_radius * 2

        # 3. 🔥 真正居中计算（和B图标完全一致）
        x = (container_size - circle_diameter) // 2
        y = (container_size - circle_diameter) // 2

        # 底环
        painter.setPen(QPen(QColor("#eaeaea"), 4))
        painter.setBrush(Qt.GlobalColor.transparent)
        painter.drawEllipse(x, y, circle_diameter, circle_diameter)

        # 电量环
        battery = self.device_info.get("battery", 0)
        if self.device_info.get("connected", False):
            color = self.theme.get("power", "#000")
            text = f"{battery}%"
        else:
            color = "red"
            text = "🚫"

        angle = int(360 * (battery / 100))
        painter.setPen(QPen(QColor(color), 3,
                       Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(x, y, circle_diameter,
                        circle_diameter, 90 * 16, -angle * 16)

        # 文字居中

        painter.setPen(QColor(color))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(self.battery_container.rect(),
                         Qt.AlignmentFlag.AlignCenter, text)


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    device1 = {"name": "耳机", "battery": 90, "connected": True}

    # 测试任意高度：65 / 135 / 100 全部完美居中！
    window = BTDeviceCard(device1, (300, 65), theme="dark")
    window.show()
    sys.exit(app.exec())
