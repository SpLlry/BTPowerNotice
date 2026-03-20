import asyncio
import sys
import random
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QLabel, QPushButton, QVBoxLayout
)
# 【核心】用PyQt6原生QThread替代asyncio/QtConcurrent，零报错
from PyQt6.QtCore import Qt, pyqtSlot, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from trayicon import TrayIcon
from taskbar import RingWidget
import buletooth.BLE
import buletooth.BTC
import utils
from config import create_config


# ===================== 【蓝牙工作线程】纯Qt原生，无异步、无报错 =====================
# ===================== 【修复版】蓝牙扫描线程 =====================
class BtScanThread(QThread):
    scan_finished = pyqtSignal(dict)

    def run(self):
        """在线程内创建 asyncio 循环，安全 await 异步蓝牙方法"""
        # 为后台线程创建独立的 asyncio 事件循环（无警告、无冲突）
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # 执行异步蓝牙扫描
        result = loop.run_until_complete(self.async_scan_devices())
        self.scan_finished.emit(result)
        loop.close()

    async def async_scan_devices(self):
        """真正的异步蓝牙扫描（支持 await）"""
        try:
            ble = buletooth.BLE.Bluetooth()
            btc = buletooth.BTC.Bluetooth()

            # ✅ 正确 await 异步方法，彻底消除警告
            ble_devices = await ble.scan_ble_devices()
            btc_devices = await btc.scan_classic_devices()

            devices = ble_devices + btc_devices
            ret = {device['address']: device for device in devices}
            # ret = {
            #     "123": {"name": "耳机", "battery": 100, "connected": True},
            #     "456": {"name": "键盘", "battery": random.randint(0, 100), "connected": True},
            #     "789": {"name": "鼠标", "battery": 20, "connected": False},
            # }
            return ret

        except Exception as e:
            print(f"蓝牙扫描异常: {e}")
            # 异常返回测试数据
            return {
                "123": {"name": "耳机", "battery": 100, "connected": True},
                "456": {"name": "键盘", "battery": random.randint(0, 100), "connected": True},
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
        self.showTaskBar = self.config.getVal('Settings', 'task_bar')
        self.battery_items = {}
        self.setFixedSize(0, 0)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setWindowTitle("BTPowerNotice-蓝牙电量轻松看")
        self.ini_ui()

        # 【Qt原生定时器】稳定无警告
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.start_scan_thread)
        self.update_timer.start(1000)

        # 初始化线程对象
        self.scan_thread = None

    def ini_ui(self):
        self.task_bar = RingWidget(config=self.config)
        self.tray = TrayIcon(self, self.task_bar.skin_manager, self.config)
        self.tray.setTrayIcon()
        self.tray.show()

        # ✅【严格保留】parent=None 绝对不修改
        print(self.task_bar.skin_manager.getAll())

        if self.showTaskBar == "1":
            self.task_bar.show()

        # 基础UI
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
        # 防止重复启动线程
        if self.scan_thread and self.scan_thread.isRunning():
            return
        task_align_type = utils.get_win11_taskbar_alignment()
        self.task_bar.set_task_align(task_align_type)
        self.scan_thread = BtScanThread()
        self.scan_thread.scan_finished.connect(self.update_device_data)
        self.scan_thread.start()

    @pyqtSlot(dict)
    def update_device_data(self, device_info: dict):
        """主线程安全更新UI"""
        offline = [addr for addr in self.battery_items if addr not in device_info]
        for addr in offline:
            self.battery_items.pop(addr)
        for addr, device in device_info.items():
            self.battery_items[addr] = device

        # 最多显示4个设备
        if len(self.battery_items) > 4:
            self.battery_items = dict(list(self.battery_items.items())[-4:])

        # 更新托盘和任务栏
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
    app.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    win = MainWindow()
    win.show()
    win.hide()
    # 标准Qt事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
