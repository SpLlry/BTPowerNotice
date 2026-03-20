from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
from PyQt6.QtCore import Qt, QRectF


# --------------------------
# 1. 环形进度条（内部封装44×44）
# --------------------------
class Ring(QWidget):
    def __init__(self, device, size, theme="light"):
        super().__init__()
        width, height = size
        self.setFixedSize(int(width), int(height))
        self.setContentsMargins(0, 0, 0, 0)

        self.sys_theme = {
            "dark": {
                "backgroud": "#000",
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
        # 正圆直径 = 宽度
        # 设备名（可外部修改）
        self.device = device
        self.device_name = device.get("name", "")

        self.percentage = max(0, min(100, device.get("battery", 0)))
        #  # 正圆直径
        self.radius = width - 10
        self.font_size = int(width / 6)
        print("Ring", width, height, self.font_size)
        self.bar_width = int(self.radius / 7)

    def set_percentage(self, value):
        self.percentage = max(0, min(100, value))
        self.update()

    def set_ring(self, device: dict, theme: str):
        # print(device)
        self.percentage = max(0, min(100, device.get("battery", 0)))
        self.device_name = device.get("name", "")
        self.device = device
        self.theme = self.sys_theme[theme]
        self.update()

    def paintEvent(self, event):
        # print("paintEvent", self.theme)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = self.radius
        circle_x = (self.width() - side) / 2
        circle_y = 2  # 距离顶部一点间距
        circle_rect = QRectF(circle_x, circle_y, side, side)

        # 背景圆
        painter.setPen(Qt.PenStyle.NoPen)
        # painter.setBrush(QColor(self.theme.get("backgroud")))
        painter.drawEllipse(circle_rect)

        # 灰色背景环
        bg_pen = QPen(QColor(self.theme.get("ring")), self.bar_width, Qt.PenStyle.SolidLine)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(circle_rect, 0, 360 * 16)

        # 进度环
        if self.percentage > 0:
            # 3. 电量环颜色逻辑
            if not self.device.get("connected", 0):
                col = QColor("#919191")
            elif self.device.get("battery", 0) < 10:
                col = QColor("#F30303")
            elif self.device.get("battery", 0) < 50:
                col = QColor("#F39603")
            elif self.device.get("battery", 0) < 80:
                col = QColor("#F3ED03")
            else:
                col = QColor(self.theme.get("power"))
            # print(col, self.device)
            progress_pen = QPen(QColor(col), self.bar_width, Qt.PenStyle.SolidLine)
            progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(progress_pen)
            span = int(self.percentage * 360 * 16 / 100)
            painter.drawArc(circle_rect, 90 * 16, span)

        # 文字
        painter.setPen(QColor(self.theme.get("text")))
        # print(self.font_size, self.radius)
        font = QFont("Arial", self.font_size, QFont.Weight.Normal)
        painter.setFont(font)
        powertext = f"{self.percentage}%"
        if not self.device.get("connected", 0):
            powertext = "🚫"
        painter.drawText(circle_rect, Qt.AlignmentFlag.AlignCenter, f"{powertext}")

        # ==========================
        # 3. ✅ 设备名：整框底部居中显示
        # ==========================
        painter.setPen(QColor(self.theme.get("text")))
        painter.setFont(QFont("Arial", 7, QFont.Weight.Normal))
        # 设备名区域：和圆环等宽，正下方水平居中
        name_rect = QRectF(circle_x, circle_y + side + 2, side, 12)
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignCenter, self.device_name)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QHBoxLayout, QWidget

    app = QApplication(sys.argv)
    win = QWidget()
    win.resize(320, 48)

    layout = QHBoxLayout(win)
    device1 = {"name": "耳机", "battery": 90, "connected": True}
    ring1 = Ring(device1, (38, 48))
    device2 = {"name": "耳机", "battery": 22, "connected": True}
    ring2 = Ring(device2, (38, 48))

    layout.addWidget(ring1)
    layout.addWidget(ring2)
    win.show()
    sys.exit(app.exec())
