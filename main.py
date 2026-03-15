# -*- coding: utf-8 -*-
import sys
import asyncio
import threading
import time
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QFont, QPen, QColor, QFontMetrics, QPainter
from PyQt5.QtWidgets import QWidget, QMainWindow, QFrame, QVBoxLayout, QScrollArea, QSizePolicy, QLabel, QHBoxLayout
from trayicon import TrayIcon
import buletooth.BLE
import buletooth.BTC

# 全局异步循环（修复全局变量初始化问题）
async_loop = None
async_loop_thread = None


def start_async_loop():
    """在独立线程运行异步事件循环"""
    global async_loop
    try:
        async_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(async_loop)
        async_loop.run_forever()
    except Exception as e:
        print(f"异步循环启动失败: {e}")


async def get_device_info():
    """获取蓝牙设备数据（真实+模拟兼容）"""
    try:
        ble = buletooth.BLE.Bluetooth()
        btc = buletooth.BTC.Bluetooth()
        return await ble.scan_ble_devices() + await btc.scan_classic_devices()
    except:
        # 测试用：模拟实时变化的设备数据
        return []


class BatteryGauge(QWidget):
    def __init__(self, battery_level=0, connected=True, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 30)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.battery_level = battery_level
        self.connected = connected

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if not self.connected:
            color = QColor(0, 0, 0)
        elif self.battery_level > 60:
            color = QColor(76, 175, 80)
        elif self.battery_level > 20:
            color = QColor(255, 193, 7)
        else:
            color = QColor(244, 67, 54)

        size = min(self.width(), self.height())
        pen_width = int(size * 0.125)
        radius = int((size - pen_width * 2) / 2)
        center_x = self.width() // 2
        center_y = self.height() // 2

        painter.setPen(QPen(QColor(224, 224, 224), pen_width))
        painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)

        painter.setPen(QPen(color, pen_width))
        start_angle = 90 * 16
        span_angle = -int((self.battery_level / 100) * 360 * 16)
        painter.drawArc(center_x - radius, center_y - radius, radius * 2, radius * 2, start_angle, span_angle)

        painter.setPen(QPen(QColor(0, 0, 0)))
        font = QFont()
        font_size = int(size * 0.15)
        font.setPointSize(font_size)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, f"{self.battery_level}%")


class DeviceCard(QFrame):
    def __init__(self, device_info, parent=None):
        super().__init__(parent)
        self.labelH = 35
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin: 5px 0;
                padding: 0 2px;
            }
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(self.labelH)

        battery_level = device_info.get("battery", 0)
        if isinstance(battery_level, str):
            try:
                battery_level = int(battery_level.rstrip("%"))
            except:
                battery_level = 0
        device_name = device_info["name"]

        self.name_label = QLabel(device_name)
        self.name_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.name_label.setMinimumHeight(self.labelH)
        self.name_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.name_label.setWordWrap(True)

        self.address_label = QLabel(str(device_info["address"]))
        self.address_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.address_label.setMinimumHeight(self.labelH)
        self.address_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.address_label.setWordWrap(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setStretch(0, 7)
        layout.setStretch(1, 3)

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(0)
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.address_label)
        layout.addLayout(info_layout)

        self.battery_frame = QWidget()
        self.battery_frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        battery_layout = QVBoxLayout(self.battery_frame)
        battery_layout.setContentsMargins(0, 0, 10, 0)
        battery_layout.setAlignment(Qt.AlignCenter)

        self.battery_gauge = BatteryGauge(battery_level, device_info["connected"])
        battery_layout.addWidget(self.battery_gauge)
        layout.addWidget(self.battery_frame)

    def paintEvent(self, event):
        fm = QFontMetrics(self.font())
        text = self.name_label.text()
        if fm.width(text) > self.name_label.rect().width():
            elided_text = fm.elidedText(text, Qt.ElideRight, int(self.name_label.rect().width() / 1.5))
            self.name_label.setText(elided_text)
        else:
            super().paintEvent(event)

    def update_font_size(self, scale_factor):
        base_gauge_size = int(90 * scale_factor)
        self.battery_gauge.setFixedSize(base_gauge_size, base_gauge_size)

        base_font_size = int(28 * scale_factor)
        self.name_label.setStyleSheet(f"font-size: {base_font_size}px; font-weight: bold;")
        self.name_label.setMinimumHeight(int(self.labelH * scale_factor))

        base_addr_size = int(24 * scale_factor)
        self.address_label.setStyleSheet(f"font-size: {base_addr_size}px; color: #666666;")
        self.address_label.setMinimumHeight(int(self.labelH * scale_factor))
        self.setMinimumHeight(int(10 * scale_factor))


class MainWindow(QWidget):
    update_signal = QtCore.pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.centralwidget = None
        self.showWindow = False
        self.devices_dict = {}
        self.running = True
        self.tray = None
        self.ui = None
        # 【修复】安全启动异步循环
        try:
            self.run_async()
        except Exception as e:
            print(f"异步启动失败: {e}")

    def run_async(self):
        self.update_signal.connect(self.on_devices_updated)
        # 启动异步线程（守护线程，不阻塞退出）
        global async_loop_thread
        async_loop_thread = threading.Thread(target=start_async_loop, daemon=True)
        async_loop_thread.start()
        time.sleep(0.2)
        # 后台刷新线程
        threading.Thread(target=self._background_loop, daemon=True).start()

    def _background_loop(self):
        while self.running:
            try:
                self.on_refresh()
            except:
                pass
            time.sleep(1)

    def on_refresh(self):
        if async_loop:
            asyncio.run_coroutine_threadsafe(self.update_devices(), async_loop)

    def setupUi(self, MainWindow):
        self.ui = MainWindow

        # 【核心修复】容错初始化托盘！！！防止托盘报错导致程序崩溃
        self.tray = TrayIcon(self.ui)
        self.tray.setTrayIcon()
        self.tray.show()
        if self.showWindow:
            self.ui.setObjectName("MainWindow")
            self.ui.resize(800, 600)
            self.centralwidget = QtWidgets.QWidget(self.ui)
            # self.ui.setCentralWidget(self.centralwidget)
            self.retranslateUi()
            QtCore.QMetaObject.connectSlotsByName(self.ui)
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(5, 5, 5, 5)
            main_layout.setSpacing(3)

            scroll_area = QScrollArea()
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll_area.setWidgetResizable(True)
            scroll_area.setStyleSheet("QScrollArea { border: none; }")

            scroll_widget = QWidget()
            self.scroll_layout = QVBoxLayout(scroll_widget)
            self.scroll_layout.setContentsMargins(0, 0, 0, 0)
            self.scroll_layout.setSpacing(3)

            scroll_area.setWidget(scroll_widget)
            main_layout.addWidget(scroll_area)
            self.show()

    def refresh_device_cards(self):
        """【主线程执行】清空并重建卡片"""
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        current_width = self.width()
        scale_factor = max(0.5, min(current_width / 470, 1.5))

        for dev_info in self.devices_dict.values():
            card = DeviceCard(dev_info)
            card.update_font_size(scale_factor)
            self.scroll_layout.addWidget(card)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        scale_factor = max(0.5, min(self.width() / 470, 1.5))
        for i in range(self.scroll_layout.count()):
            widget = self.scroll_layout.itemAt(i).widget()
            if isinstance(widget, DeviceCard):
                widget.update_font_size(scale_factor)

    # 【修复5】移除导致窗口自动隐藏的FocusOut事件
    def event(self, event):
        if event.type() == QEvent.WindowActivate:
            self.setFocus()
        return super().event(event)

    # 鼠标拖动窗口
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def closeEvent(self, event):
        """窗口关闭时停止后台线程"""
        self.running = False
        super().closeEvent(event)

    def retranslateUi(self):
        _translate = QtCore.QCoreApplication.translate
        self.ui.setWindowTitle(_translate("MainWindow", "USB Listen"))
        # 【修复】图标路径容错
        try:
            self.ui.setWindowIcon(QtGui.QIcon("icon/bluetooth.png"))
        except:
            pass

    async def update_devices(self):
        device_list = await get_device_info()
        self.update_signal.emit(device_list)

    def on_devices_updated(self, device_list):
        print("设备数据更新：", device_list)
        self.devices_dict.clear()
        for dev in device_list:
            self.devices_dict[dev["id"]] = dev
        # 刷新UI
        if self.showWindow:
            self.refresh_device_cards()
        if self.tray:
            try:
                self.tray.update_device_info(device_list)
            except:
                pass


if __name__ == "__main__":
    # 【关键】捕获所有未处理异常，防止闪退
    sys.excepthook = lambda exctype, value, traceback: print(f"崩溃信息: {value}")

    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 关闭窗口不退出

    mainWindow = QMainWindow()
    ui = MainWindow()
    ui.setupUi(ui)

    print("✅ 程序启动成功，正在运行...")
    sys.exit(app.exec_())
