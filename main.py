# format: off
# 标准库导入
import sys
import os
import subprocess
import ctypes
import tracemalloc
import gc

# 第三方库导入
from PyQt6.QtCore import Qt


from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

# 必须在 QApplication 创建前设置，否则 QtWebEngineWidgets 会报错
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
# format: on
from PyQt6.QtCore import pyqtSlot, QTimer
from PyQt6.QtGui import QFont, QIcon


# 本地库导入
from core.config.constants import MAX_DISPLAY_DEVICES, MAX_PREV_STATES
from core import bluetooth
from views.dashboard_view import BluetoothBatteryApp
from views.tray_icon import TrayIcon
from views.taskbar_view import RingWidget
from views.components.high_dpi import setup_high_dpi
from utils import (
    get_icon_path,
    get_exe_path,
    get_exe_run_dir,
    get_windows_system_theme,
    get_win11_taskbar_alignment,
    get_task_bar_w11,
)
from utils.tools import log, config, env, dc

setup_high_dpi()


sys.argv += ["--no-sandbox"]  # 核心：关闭Qt沙箱

# ===================== 主窗口（ =====================


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.MUTEX_NAME = f"{env.APP_NAME}"
        if not self._check_single_instance():
            print("已运行实例，退出")
            sys.exit(0)
        self.setWindowIcon(QIcon(get_icon_path("icon/icon.ico")))
        self.config = config
        self.tray = None
        self.sys_theme = None
        self.task_bar = None
        self.bluetooth_battery_app = None
        self.showTaskBar = self.config.getVal("Settings", "task_bar")
        self.battery_items = {}
        self.prev_device_states = {}
        self.scan_thread = None
        self.max_prev_states = MAX_PREV_STATES
        self.setFixedSize(0, 0)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.ini_ui()
        self.setWindowTitle(f"{env.APP_NAME}-{env.APP_DESCRIPTION}")

        # 创建并初始化扫描线程，实现线程重用
        self.scan_thread = bluetooth.BtScan.BtScanThread(self.config)
        self.scan_thread.scan_finished.connect(self.update_device_data)
        # 从配置读取扫描间隔，默认2000ms
        try:
            # print(self.config.getVal("Settings", "scan_interval", "2000"))
            scan_interval = int(self.config.getVal("Settings", "scan_interval", "2000"))
        except ValueError:
            scan_interval = 3000
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.start_scan_thread)
        self.update_timer.start(scan_interval)

        # 启动第一次扫描
        self.start_scan_thread()

        dc.set("config", config.all())

    def _check_single_instance(self):
        """
        Windows 互斥体检查：确保应用只能运行一个实例
        返回 True=可以启动，False=已运行
        """
        ERROR_ALREADY_EXISTS = 183  # 定义常量
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        mutex = kernel32.CreateMutexA(None, False, self.MUTEX_NAME.encode("utf-8"))
        mutex = kernel32.CreateMutexA(None, False, self.MUTEX_NAME.encode("utf-8"))

        # 检查互斥体创建失败
        if not mutex:
            log.error(f"创建互斥体失败，错误码：{ctypes.get_last_error()}")
            return False  # 创建失败则不启动

        last_error = ctypes.get_last_error()
        # 释放互斥体句柄（避免泄漏）
        kernel32.CloseHandle(mutex)
        return last_error != ERROR_ALREADY_EXISTS

    def ini_ui(self):
        self.bluetooth_battery_app = BluetoothBatteryApp()
        self.bluetooth_battery_app.hide()

        self.task_bar = RingWidget()
        self.tray = TrayIcon(self, self.task_bar.skin_manager)
        self.tray.setTrayIcon()
        self.tray.show()
        self.tray.skin_changed.connect(self.task_bar.change_skin)
        # 绑定信号（不变）
        # 绑定信号（不变）
        self.tray.mouseEntered.connect(self.show_bluetooth_window)
        # self.tray.mouseLeft.connect(self.hide_bluetooth_window)
        # log.info(self.task_bar.skin_manager.getAll())

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

    def show_bluetooth_window(self):
        show_win = self.config.getVal("Settings", "show_main") == "1"
        if self.bluetooth_battery_app.isHidden() and show_win:
            # 屏幕右下角定位
            screen = QApplication.instance().primaryScreen()
            screen_geo = screen.availableGeometry()
            win_w = self.bluetooth_battery_app.width()
            win_h = self.bluetooth_battery_app.height()

            # 右下角，距离边缘 10px
            x = screen_geo.right() - win_w - 1
            y = screen_geo.bottom() - win_h - 1

            self.bluetooth_battery_app.move(x, y)
            self.bluetooth_battery_app.show()
            self.bluetooth_battery_app.setFocus()
            self.bluetooth_battery_app.activateWindow()

    def nativeEvent(self, event_type: bytes, message):
        if event_type == b"windows_generic_MSG":
            system_theme = get_windows_system_theme()
            if self.sys_theme != system_theme:
                self.sys_theme = system_theme
                # self.task_bar.set_theme(system_theme)
                # 发布系统主题变化
                # dc.set("sys_theme", self.sys_theme)
        ret, voidptr = super().nativeEvent(event_type, message)
        return ret, 0

    # ===================== 启动线程扫描（核心） =====================
    def start_scan_thread(self):
        """启动蓝牙扫描线程（线程安全）"""
        try:
            if not self.scan_thread:
                # 重新创建线程（如果之前被销毁）
                self.scan_thread = bluetooth.BtScan.BtScanThread(self.config)
                self.scan_thread.scan_finished.connect(self.update_device_data)
                # 绑定线程结束信号，避免内存泄漏
                self.scan_thread.finished.connect(self.on_scan_thread_finished)

            if not self.scan_thread.isRunning():
                print("启动扫描线程")
                print("启动扫描线程")
                self.scan_thread.start()
            else:
                # 线程已运行，触发扫描信号
                self.scan_thread.start_scan.emit()
        except Exception as e:
            log.error(f"启动扫描线程失败：{str(e)}")

    def on_scan_thread_finished(self):
        """扫描线程结束回调（清理资源）"""
        self.scan_thread.deleteLater()  # PyQt线程必须调用deleteLater释放
        self.scan_thread = None

    @pyqtSlot(dict)
    def update_device_data(self, device_info: dict):
        """主线程安全更新UI"""
        taskbar_alignment = get_win11_taskbar_alignment()
        dc.set(
            "system",
            {
                "StartMenu": {"align": taskbar_alignment},
                "task_bar": get_task_bar_w11(taskbar_alignment),
                "sys_theme": self.sys_theme,
            },
        )
        # log.info(f"更新设备数据: {device_info}")
        for addr, device in device_info.items():
            # print(1231, addr.upper().replace(":", ""), device)

            clean_addr = addr.upper().replace(":", "")
            name = config.getVal(
                "CustomDeviceName", clean_addr, device.get("name", "未知设备")
            )
            show_device = config.getVal("CustomDeviceShow", clean_addr, "1") == "1"
            name = config.getVal(
                "CustomDeviceName", clean_addr, device.get("name", "未知设备")
            )
            show_device = config.getVal("CustomDeviceShow", clean_addr, "1") == "1"
            device["name"] = name
            device["show"] = show_device
            # print(
            #     1232,
            #     name,
            #     addr,
            #     show_device,
            #     config.getVal("CustomDeviceShow", clean_addr, "1"),
            # )
            # print(
            #     1232,
            #     name,
            #     addr,
            #     show_device,
            #     config.getVal("CustomDeviceShow", clean_addr, "1"),
            # )
            if addr not in self.prev_device_states:
                self.prev_device_states[addr] = device

                if device.get("connected"):
                    log.info(f"设备{name} 已连接到电脑")
                    # show_island_notification("设备已连接", f"{name} 已连接到电脑", 3000)
            else:
                prev_device = self.prev_device_states[addr]
                prev_connected = prev_device.get("connected", False)
                curr_connected = device.get("connected", False)

                if not prev_connected and curr_connected:
                    # show_island_notification("设备已连接", f"{name} 已连接到电脑", 3000)
                    log.info(f"设备{name} 已连接到电脑")
                elif prev_connected and not curr_connected:
                    # show_island_notification("设备已断开", f"{name} 已断开连接", 3000)
                    log.info(f"设备{name} 已断开连接")
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
                        log.info(
                            f"{emoji} 电量变化: {prev_battery}% → {curr_battery}%",
                        )

            self.prev_device_states[addr] = device

        offline = [addr for addr in self.battery_items if addr not in device_info]
        for addr in offline:
            self.battery_items.pop(addr)
            self.prev_device_states.pop(addr, None)

        for addr, device in device_info.items():
            self.battery_items[addr] = device

        if len(self.battery_items) > MAX_DISPLAY_DEVICES:
            # 直接截断，避免转换为列表再转字典的开销
            self.battery_items = {
                k: v
                for i, (k, v) in enumerate(self.battery_items.items())
                if i >= len(self.battery_items) - MAX_DISPLAY_DEVICES
            }
            self.battery_items = {
                k: v
                for i, (k, v) in enumerate(self.battery_items.items())
                if i >= len(self.battery_items) - MAX_DISPLAY_DEVICES
            }

        if len(self.prev_device_states) > MAX_PREV_STATES:
            # 批量删除，减少循环次数
            remove_count = len(self.prev_device_states) - MAX_PREV_STATES
            keys_to_remove = list(self.prev_device_states.keys())[:remove_count]
            keys_to_remove = list(self.prev_device_states.keys())[:remove_count]
            for key in keys_to_remove:
                self.prev_device_states.pop(key, None)  # pop加默认值，避免KeyError

        # print(f"更新设备数据: {device_info}")
        # print(device_info.values())
        # 过滤出 show 为 True 的设备
        # filtered_devices = {
        #     addr: device for addr, device in device_info.items() if device["show"]
        # }

        dc.set("devices", device_info)

        # self.tray.update_device_info(device_info)
        # self.task_bar.update_device_data(device_info)
        # self.bluetooth_battery_app.update_devices(device_info)


    def closeEvent(self, event):
        """程序退出时清理资源"""
        log.info("开始清理资源...")

        # 停止定时器
        if self.update_timer and self.update_timer.isActive():
            self.update_timer.stop()
            self.update_timer.deleteLater()

        # 停止扫描线程
        if self.scan_thread:
            if self.scan_thread.isRunning():
                self.scan_thread.stop()
            self.scan_thread.deleteLater()
            self.scan_thread = None

        # 销毁托盘图标
        if self.tray:
            self.tray.hide()
            if hasattr(self.tray, "cleanup"):
                self.tray.cleanup()
            self.tray.deleteLater()
            self.tray = None

        # 销毁UI组件
        if self.bluetooth_battery_app:
            self.bluetooth_battery_app.close()
            self.bluetooth_battery_app.deleteLater()
            self.bluetooth_battery_app = None

        if self.task_bar:
            self.task_bar.close()
            self.task_bar.deleteLater()
            self.task_bar = None

        # 清理字典和缓存
        self.battery_items.clear()
        self.prev_device_states.clear()

        # 强制垃圾回收
        gc.collect()

        log.info("资源清理完成")

        # 停止内存监控
        tracemalloc.stop()

        log.info("程序正常退出，资源已清理")
        event.accept()


    def reboot(self):
        """
        用 BAT 脚本中转重启（终极兜底方案）
        解决：临时目录删除失败/DLL加载失败/winrt模块缺失/Qt插件初始化失败
        """
        try:
            if not getattr(sys, "frozen", False):
                log.warning("当前环境为开发环境,不支持重启")
                return

            # ========== 你原有的代码 完全不动 ==========
            exe_path = get_exe_path()
            app_path = get_exe_run_dir()
            log.info(f"app_path: {app_path}")
            log.info(f"exe_path: {exe_path}")

            # ========== 🔥 核心：自动生成 BAT 重启脚本 ==========
            # 1. 临时 BAT 路径（和 EXE 同目录，重启后自动删除）
            bat_path = os.path.join(app_path, "temp_restart.bat")
            exe_name = os.path.basename(exe_path)
            # 2. 编写 BAT 内容（等待1秒→启动EXE→删除自身）
            bat_content = f"""
            @echo off
            chcp 936 >nul
            :: 强制结束旧EXE进程（/f 强制杀，/im 按进程名杀，/t 杀子进程）
            taskkill /f /im "{exe_name}" /t >nul 2>&1
            :: 等待1秒，确保进程完全退出+释放所有资源
            timeout /t 1 /nobreak >nul
            :: 启动新EXE（指定工作目录，依赖目录生效）
            start "" /D "{app_path}" "{exe_path}"
            :: 删除BAT自身，无残留
            del /f /q "%~f0"
            """.strip()

            # 3. 写入 BAT 文件
            with open(bat_path, "w", encoding="gbk") as f:  # Windows BAT 必须用gbk编码
                f.write(bat_content)

            # 4. 执行 BAT 脚本（后台运行，无黑窗）
            subprocess.Popen(
                [bat_path],
                creationflags=subprocess.CREATE_NO_WINDOW,
                shell=True,
            )

            # 5. 退出旧 EXE（不触发PyInstaller目录清理）
            log.info("✅ BAT重启脚本已执行，旧进程退出...")
            os._exit(0)

        except Exception as e:
            log.error(f"❌ 重启失败：{str(e)}")


def except_hook(exctype, value, tb):
    # 全局捕获崩溃，输出【精确位置】
    log.error("=" * 50)
    log.error("Error：")
    log.error("=" * 50)
    log.error(exctype)
    # 遍历堆栈，找到最后一行真正出错的代码
    while tb:
        filename = tb.tb_frame.f_code.co_filename
        lineno = tb.tb_lineno
        funcname = tb.tb_frame.f_code.co_name
        log.error(f"    文件：{filename}")
        log.error(f"    行号：第 {lineno} 行")
        log.error(f"    函数：{funcname}")
        log.error(f"    错误：{value}")
        tb = tb.tb_next

    log.error("=" * 50)


# =====================内存使用监控 =====================
def monitor_memory_usage():
    """监控内存使用情况"""
    current, peak = tracemalloc.get_traced_memory()
    log.info(
        f"内存使用: 当前 {current / 1024 / 1024:.2f} MB; 峰值 {peak / 1024 / 1024:.2f} MB"
    )

    # 显示前5个内存使用最多的对象
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics("lineno")
    log.info("内存使用最多的前5个对象:")
    for stat in top_stats[:5]:
        log.info(stat)


# =====================主程序入口 =====================


def main():
    # 启动内存监控
    tracemalloc.start()

    # 定期内存监控
    memory_timer = QTimer()
    memory_timer.timeout.connect(monitor_memory_usage)
    memory_timer.start(2000)  # 每分钟监控一次

    # ##此处是为了兼容0.1.6版本添加的开机启动
    # del_reg_value(f"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", settings.APP_NAME)
    # del_reg_value(
    #     f"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run",
    #     settings.APP_NAME,
    # )
    # 全局捕获

    sys.excepthook = except_hook

    app = QApplication(sys.argv)
    setup_high_dpi()
    win = MainWindow()
    win.show()
    win.hide()
    # 标准Qt事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
