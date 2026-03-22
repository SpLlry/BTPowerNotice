import asyncio
import sys
import random
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from PyQt6.QtCore import Qt, pyqtSlot, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont

from trayicon import TrayIcon
from taskbar import RingWidget
import buletooth.BLE
import buletooth.BTC
import utils
from config import create_config
from setting import settings

# from notification import show_island_notification


# ===================== 【蓝牙工作线程】=====================
class BtScanThread(QThread):
    scan_finished = pyqtSignal(dict)

    def __init__(self, ble_scanner=None, btc_scanner=None):
        super().__init__()
        self.ble_scanner = ble_scanner
        self.btc_scanner = btc_scanner

    def run(self):
        """在线程内创建 asyncio 循环，安全 await 异步蓝牙方法"""
        loop = asyncio.new_event_loop()

        asyncio.set_event_loop(loop)

        result = loop.run_until_complete(self.async_scan_devices())
        self.scan_finished.emit(result)
        loop.close()

    async def async_scan_devices(self):
        """真正的异步蓝牙扫描（支持 await）"""
        try:
            if self.ble_scanner is None:
                self.ble_scanner = buletooth.BLE.Bluetooth()
            if self.btc_scanner is None:
                self.btc_scanner = buletooth.BTC.Bluetooth()

            ble_devices = await self.ble_scanner.scan_ble_devices()
            btc_devices = await self.btc_scanner.scan_classic_devices()

            devices = ble_devices + btc_devices
            ret = {device["address"]: device for device in devices}
            # return {
            #     "123": {"name": "耳机", "battery": 100, "connected": True},
            #     "456": {
            #         "name": "键盘",
            #         "battery": random.randint(0, 100),
            #         "connected": True,
            #     },
            #     "789": {"name": "鼠标", "battery": 20, "connected": False},
            # }
            return ret

        except Exception as e:
            print(f"蓝牙扫描异常: {e}")
            return {
                "123": {"name": "耳机", "battery": 100, "connected": True},
                "456": {
                    "name": "键盘",
                    "battery": random.randint(0, 100),
                    "connected": True,
                },
                "789": {"name": "鼠标", "battery": 20, "connected": False},
            }


# ===================== 主窗口（零修改你的业务逻辑） =====================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = create_config()
        self.tray = None
        self.sys_theme = None
        self.task_bar = None
        self.showTaskBar = self.config.getVal("Settings", "task_bar")
        self.battery_items = {}
        self.prev_device_states = {}
        self.ble_scanner = None
        self.btc_scanner = None
        self.setFixedSize(0, 0)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setWindowTitle(f"{settings.APP_NAME}-{settings.APP_DESCRIPTION}")
        self.ini_ui()

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.start_scan_thread)
        self.update_timer.start(5000)

        self.scan_thread = None
        self.max_prev_states = 20

    def ini_ui(self):
        self.task_bar = RingWidget(config=self.config)
        self.tray = TrayIcon(self, self.task_bar.skin_manager, self.config)
        self.tray.setTrayIcon()
        self.tray.show()
        self.tray.skin_changed.connect(self.task_bar.change_skin)

        print(self.task_bar.skin_manager.getAll())

        if self.showTaskBar == "1":
            self.task_bar.show()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel("蓝牙电量显示工具")
        label.setFont(QFont("微软雅黑", 12))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn = QPushButton("测试")
        btn.clicked.connect(lambda: print("运行正常"))
        layout.addWidget(label)
        layout.addWidget(btn)

    def nativeEvent(self, event_type: bytes, message):
        if event_type == b"windows_generic_MSG":
            system_theme = utils.get_windows_system_theme()
            if self.sys_theme != system_theme:
                self.sys_theme = system_theme
                self.task_bar.set_theme(system_theme)
        ret, voidptr = super().nativeEvent(event_type, message)
        return ret, 0

    # ===================== 启动线程扫描（核心） =====================
    def start_scan_thread(self):
        if self.scan_thread and self.scan_thread.isRunning():
            self.scan_thread.wait()
            self.scan_thread.deleteLater()
        task_align_type = utils.get_win11_taskbar_alignment()
        self.task_bar.set_task_align(task_align_type)

        if self.ble_scanner is None:
            self.ble_scanner = buletooth.BLE.Bluetooth()
        if self.btc_scanner is None:
            self.btc_scanner = buletooth.BTC.Bluetooth()

        self.scan_thread = BtScanThread(self.ble_scanner, self.btc_scanner)
        self.scan_thread.scan_finished.connect(self.update_device_data)
        self.scan_thread.start()

    @pyqtSlot(dict)
    def update_device_data(self, device_info: dict):
        """主线程安全更新UI"""
        for addr, device in device_info.items():
            name = device.get("name", "未知设备")

            if addr not in self.prev_device_states:
                self.prev_device_states[addr] = device

                if device.get("connected"):
                    print("设备已连接", f"{name} 已连接到电脑")
                    # show_island_notification("设备已连接", f"{name} 已连接到电脑", 3000)
            else:
                prev_device = self.prev_device_states[addr]
                prev_connected = prev_device.get("connected", False)
                curr_connected = device.get("connected", False)

                if not prev_connected and curr_connected:
                    # show_island_notification("设备已连接", f"{name} 已连接到电脑", 3000)
                    print("设备已连接", f"{name} 已连接到电脑")
                elif prev_connected and not curr_connected:
                    # show_island_notification("设备已断开", f"{name} 已断开连接", 3000)
                    print("设备已断开", f"{name} 已断开连接")
                elif curr_connected:
                    prev_battery = prev_device.get("battery", 0)
                    curr_battery = device.get("battery", 0)
                    if prev_battery != curr_battery:
                        if curr_battery < 20:
                            emoji = "🪫⚠️"
                        elif curr_battery < 60:
                            emoji = "🪫"
                        else:
                            emoji = "🔋"
                        # show_island_notification(f"{emoji} 电量变化", f"{name}: {prev_battery}% → {curr_battery}%", 3000)
                        print(
                            f"{emoji} 电量变化",
                            f"{name}: {prev_battery}% → {curr_battery}%",
                        )

            self.prev_device_states[addr] = device

        offline = [addr for addr in self.battery_items if addr not in device_info]
        for addr in offline:
            self.battery_items.pop(addr)
            self.prev_device_states.pop(addr, None)

        for addr, device in device_info.items():
            self.battery_items[addr] = device

        if len(self.battery_items) > 4:
            self.battery_items = dict(list(self.battery_items.items())[-4:])

        if len(self.prev_device_states) > self.max_prev_states:
            keys_to_remove = list(self.prev_device_states.keys())[:-self.max_prev_states]
            for key in keys_to_remove:
                del self.prev_device_states[key]

        self.tray.update_device_info(device_info.values())
        self.task_bar.update_device_data(device_info)


def except_hook(exctype, value, tb):
    # 全局捕获崩溃，输出【精确位置】
    print("=" * 50)
    print("Error：")
    print("=" * 50)
    print(exctype)
    # 遍历堆栈，找到最后一行真正出错的代码
    while tb:
        filename = tb.tb_frame.f_code.co_filename
        lineno = tb.tb_lineno
        funcname = tb.tb_frame.f_code.co_name
        print(f"文件：{filename}")
        print(f"行号：第 {lineno} 行")
        print(f"函数：{funcname}")
        print(f"错误：{value}")
        tb = tb.tb_next

    print("=" * 50)


# =====================主程序入口 =====================
def main():
    # 全局捕获
    sys.excepthook = except_hook
    app = QApplication(sys.argv)
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    win = MainWindow()
    win.show()
    win.hide()
    # 标准Qt事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
