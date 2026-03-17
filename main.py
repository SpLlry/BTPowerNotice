import asyncio
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QLabel, QPushButton, QVBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer
from PyQt6.QtGui import QFont

from trayicon import TrayIcon
from taskbar import RingWidget
import buletooth.BLE
import buletooth.BTC
import utils

# 全局异步锁：防止蓝牙并发扫描冲突
SCAN_LOCK = asyncio.Lock()


async def get_device_info():
    """异步获取设备数据（线程安全，仅做数据获取）"""
    async with SCAN_LOCK:
        try:
            ble = buletooth.BLE.Bluetooth()
            btc = buletooth.BTC.Bluetooth()
            devices = await ble.scan_ble_devices() + await btc.scan_classic_devices()
            ret = {}
            for device in devices:
                ret[device['address']] = device
            return ret
        except Exception as e:
            print(f"扫描异常: {e}")
            return {}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tray = None
        self.sys_theme = None
        self.task_bar = None
        self.battery_items = {}
        # 基础窗口设置（正常Windows窗口，无任何危险配置）
        self.setWindowTitle("BTPowerNotice-蓝牙电量轻松看")  # 窗口标题
        self.resize(500, 300)  # 窗口大小
        self.setMinimumSize(400, 250)  # 最小尺寸
        self.ini_ui()

        # 主线程定时器（最稳定，无事件循环报错）
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.sync_update)
        self.update_timer.start(1000)

    def ini_ui(self):
        self.tray = TrayIcon(self)
        self.tray.setTrayIcon()
        self.tray.show()
        self.task_bar = RingWidget(None)
        self.task_bar.show()
        # 创建中心部件（标准窗口必须）
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 布局
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        # 1. 文字标签
        label = QLabel("这是一个正常、稳定、无崩溃的 PyQt6 窗口")
        label.setFont(QFont("微软雅黑", 12))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 2. 按钮
        btn = QPushButton("点击测试")
        btn.setFont(QFont("微软雅黑", 11))
        btn.clicked.connect(self.on_btn_click)

        # 添加到布局
        layout.addWidget(label)
        layout.addWidget(btn)

    def nativeEvent(self, event_type: bytes, message):
        # 仅监听 Windows 系统设置变更消息
        # print(event_type)
        if event_type == b"windows_generic_MSG":
            system_theme = utils.get_windows_system_theme()
            if self.sys_theme is None:
                self.sys_theme = system_theme
                self.task_bar.set_theme(system_theme)
            if system_theme != self.sys_theme:
                self.sys_theme = system_theme
                self.task_bar.set_theme(system_theme)
        # print(self.sys_theme, 12312)
        ret, voidptr = super().nativeEvent(event_type, message)  # 正确！交给Qt默认处理

        return ret, 0

    def on_btn_click(self):
        print("按钮点击成功！窗口运行正常～")

    async def auto_update_battery(self):
        """仅获取数据，不修改UI"""
        try:
            device_info = await get_device_info()
            task_align_type = utils.get_win11_taskbar_alignment()
            self.task_bar.set_task_align(task_align_type)
            # print("仅获取数据，不修改UI", device_info)
            # 安全调度到主线程更新数据
            self.update_device_data(device_info)
        except Exception as e:
            print(f"更新失败: {e}")

    def sync_update(self):
        """主线程安全启动异步任务"""
        asyncio.ensure_future(self.auto_update_battery())

    @pyqtSlot(dict)
    def update_device_data(self, device_info: dict):
        """
        【唯一主线程修改数据】
        安全修改 battery_items
        """
        # 移除离线设备
        offline = [addr for addr in self.battery_items if addr not in device_info]
        for addr in offline:
            self.battery_items.pop(addr)
        # 更新/新增设备
        for addr, device in device_info.items():
            self.battery_items[addr] = device

        # 最多显示4个设备
        while len(self.battery_items) > 4:
            self.battery_items.popitem()

        # 更新托盘 + 重绘UI
        self.tray.update_device_info(device_info.values())
        self.task_bar.update_device_data(device_info)
        self.task_bar.update()


# ===================== 程序入口 =====================
async def main():
    # 捕获所有未处理异常，防止闪退
    sys.excepthook = lambda exctype, value, traceback: print(f"崩溃信息: {value}")
    app = QApplication(sys.argv)
    win = MainWindow()
    # win.show()
    # 标准运行方式
    while True:
        app.processEvents()
        await asyncio.sleep(0.01)


if __name__ == "__main__":
    print(utils.get_win11_taskbar_alignment())
    asyncio.run(main())
