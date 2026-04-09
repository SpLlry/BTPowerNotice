import math

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QFont, QPainterPath
from PyQt6.QtCore import Qt, QRectF, QTimer


# --------------------------
# 水波纹圆环 + 底部设备名（外环=circle_size | 内环=circle_size-8）
# --------------------------
class Ring(QWidget):
    def __init__(self, device, size, theme="light"):
        super().__init__()
        width, height = size
        # print(width, height)
        # ✅ 完全保留原始setFixedSize布局
        self.setFixedSize(int(width), int(height))
        self.setContentsMargins(0, 0, 0, 0)

        self.sys_theme = {
            "dark": {
                "ring": "#444444",
                "text": "#FFFFFF",
                "power": "#03dc6c",
            },
            "light": {
                "ring": "gray",
                "text": "#000000",
                "power": "#03dc6c",
            }
        }
        self.theme = self.sys_theme[theme]
        self.circle_diameter = width
        self.font_size = max(int(width / 5), 8)  # 最小字体8
        self.device_name = device.get("name", "")
        self.device = device

        self.percentage = str(max(0, min(100, device.get("battery", 0)))) + "%"
        self.wave_amplitude = 3  # 波浪振幅
        self.wave_speed = 0.08  # 波浪速度
        self.wave_offset = 1.0  # 波浪偏移
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_wave)
        self.set_ring(device, theme)

    def set_ring(self, device: dict, theme: str):
        self.device = device
        self.percentage = str(max(0, min(100, device.get("battery", 0)))) + "%"
        self.device_name = device.get("name", "")
        self.theme = self.sys_theme[theme]
        # print(self.timer.isActive())
        if self.device.get("connected", 0) and (0 < self.device.get("battery", 0) < 100):
            # print("波浪启动")
            if not self.timer.isActive():
                self.timer.start(30)
        else:
            if self.timer.isActive():
                self.timer.stop()
            # print("波浪停止")
        self.update()

    def _update_wave(self):
        self.wave_offset += self.wave_speed
        if self.wave_offset > 2 * math.pi:
            self.wave_offset = 0.0
        if self.isVisible():
            self.update()

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)  # 关闭默认画笔

        # 基础尺寸计算
        w, h = self.width(), self.height()
        circle_size = max(w - 10, 16)  # 外环尺寸=circle_size
        outer_width = 4
        inner_size = circle_size - outer_width  # 内环尺寸=circle_size-outer_width
        wave_expand = 0  # 水波纹扩展像素

        # 坐标计算
        circle_x = (w - circle_size) / 2
        circle_y = 2
        inner_x = circle_x + int(outer_width) / 2
        inner_y = circle_y + int(outer_width) / 2

        # 水波纹绘制区域
        wave_rect = QRectF(
            inner_x,
            inner_y,
            inner_size,
            inner_size
        )
        # 文字居中用的原始内环区域（不扩展）
        text_rect = QRectF(inner_x, inner_y, inner_size, inner_size)
        if self.device.get("battery", 0) < 10 or not self.device.get("connected", 0):
            col = QColor("red")
        elif self.device.get("battery", 0) < 50:
            col = QColor("#F39603")
        elif self.device.get("battery", 0) < 80:
            col = QColor(self.theme.get("power"))
        else:
            col = QColor(self.theme.get("power"))
        # ==========================
        # 步骤1：绘制灰色底圆（原始内环尺寸）
        # ==========================
        # painter.setBrush(QColor(self.theme.get("ring")))
        painter.drawEllipse(QRectF(inner_x, inner_y, inner_size, inner_size))

        # ==========================
        # 步骤2：绘制绿色外环边框（8px宽度）
        # ==========================
        painter.setBrush(col)
        outer_path = QPainterPath()
        outer_path.addEllipse(QRectF(circle_x, circle_y, circle_size, circle_size))
        outer_path.addEllipse(QRectF(inner_x, inner_y, inner_size, inner_size))
        painter.drawPath(outer_path)

        # ==========================
        # 步骤3：绘制扩展2px的水波纹/100%填充
        # ==========================
        # print(self.device)
        if not self.device.get("connected", 0):
            self.percentage = "🚫"
        elif self.device.get("battery", 0) <= 0:
            pass  # 不绘制任何填充，仅显示外环
        elif self.device.get("battery", 0) >= 100:

            # 100%：扩展2px填充，覆盖灰色边
            painter.setBrush(QColor(self.theme.get("power")))
            painter.drawEllipse(wave_rect)
        else:
            # 非100%：裁剪到扩展后的区域，绘制更大的水波纹
            # 3. 电量环颜色逻辑

            clip_path = QPainterPath()
            clip_path.addEllipse(wave_rect)
            painter.setClipPath(clip_path)

            # 水位计算（基于原始内环，保证比例正确）
            water_level = inner_size * (1.0 - self.device.get("battery", 0) / 100.0)
            # 水波纹Y坐标也扩展2px，对齐扩展区域
            water_y = inner_y - wave_expand + water_level

            # ✅ 核心调整2：水波纹路径扩展2px绘制
            wave_path = QPainterPath()
            # 起始点左移2px
            wave_path.moveTo(inner_x - wave_expand, water_y)
            # 步数增加，保证扩展后平滑
            steps = max(int(inner_size) + wave_expand * 2, 1)
            for i in range(steps + 1):
                # 横坐标覆盖扩展后的全部宽度
                px = inner_x - wave_expand + (i / steps) * (inner_size + wave_expand * 2)
                sin_val = math.sin((i / 8.0) + self.wave_offset)
                py = water_y + self.wave_amplitude * sin_val
                wave_path.lineTo(px, py)
            # 闭合路径：右下和左下都扩展2px，完全覆盖灰色底
            wave_path.lineTo(inner_x + inner_size + wave_expand, inner_y + inner_size + wave_expand)
            wave_path.lineTo(inner_x - wave_expand, inner_y + inner_size + wave_expand)
            wave_path.closeSubpath()

            painter.setBrush(col)
            painter.drawPath(wave_path)

        # ==========================
        # 绘制百分比文字（居中不变）
        # ==========================
        painter.setClipping(False)
        painter.setPen(QColor(self.theme.get("text")))
        safe_font_size = min(self.font_size, int(inner_size / 3))
        font = QFont("Arial", safe_font_size, QFont.Weight.Normal)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)  # 优先抗锯齿
        font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)  # 全量提示，更平滑
        painter.setFont(font)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, f"{self.percentage}")

        # ==========================
        # 绘制设备名
        # ==========================
        painter.setPen(QColor(self.theme.get("text")))
        painter.setFont(font)
        name_rect = QRectF(circle_x, circle_y + circle_size + 2, circle_size, 12)
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignCenter, self.device_name)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QHBoxLayout, QWidget

    app = QApplication(sys.argv)
    win = QWidget()
    win.setWindowTitle("水波纹大2像素（无灰色细边）")
    win.resize(320, 48)

    layout = QHBoxLayout(win)
    device1 = {"name": "设备1", "battery": 100}
    ring1 = Ring(device1, (38, 48))
    device2 = {"name": "设备2", "battery": 22, "connected": True}
    ring2 = Ring(device2, (38, 48))

    layout.addWidget(ring1)
    layout.addWidget(ring2)
    win.show()
    sys.exit(app.exec())
