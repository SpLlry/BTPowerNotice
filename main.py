import sys
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

# 1. 启用高DPI适配 - 必须在所有QApplication实例创建之前调用
QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)

sys.argv += ["--no-sandbox"]  # 核心：关闭Qt沙箱

from tools import log, config, settings
import utils
import buletooth.BtScan
from taskbar import RingWidget
from trayicon import TrayIcon
from utils import del_reg_value, get_icon_path, get_exe_path, get_exe_run_dir
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import pyqtSlot, QTimer
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
import ctypes
import subprocess
import os


# ===================== 主窗口（ =====================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.MUTEX_NAME = f"{settings.APP_NAME}"
        if not self._check_single_instance():
            sys.exit(0)
        self.setWindowIcon(QIcon(get_icon_path("icon/icon.ico")))
        self.config = config
        self.tray = None
        self.sys_theme = None
        self.task_bar = None
        self.showTaskBar = self.config.getVal("Settings", "task_bar")
        self.battery_items = {}
        self.prev_device_states = {}
        self.scan_thread = None
        self.max_prev_states = 20
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
        self.start_scan_thread()

    def _check_single_instance(self):
        """
        Windows 互斥体检查：确保应用只能运行一个实例
        返回 True=可以启动，False=已运行
        """
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        # 创建系统级互斥体
        mutex = kernel32.CreateMutexA(None, False, self.MUTEX_NAME.encode("utf-8"))
        # 获取错误码：183 = 互斥体已存在（应用已运行）
        last_error = ctypes.get_last_error()
        return last_error != 183

    def ini_ui(self):
        self.task_bar = RingWidget()
        self.tray = TrayIcon(self, self.task_bar.skin_manager)
        self.tray.setTrayIcon()
        self.tray.show()
        self.tray.skin_changed.connect(self.task_bar.change_skin)

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

        self.scan_thread = buletooth.BtScan.BtScanThread(self.config)
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

        if len(self.battery_items) > 4:
            self.battery_items = dict(list(self.battery_items.items())[-4:])

        if len(self.prev_device_states) > self.max_prev_states:
            keys_to_remove = list(self.prev_device_states.keys())[
                : -self.max_prev_states
            ]
            for key in keys_to_remove:
                del self.prev_device_states[key]

        self.tray.update_device_info(device_info.values())
        self.task_bar.update_device_data(device_info)

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


# =====================主程序入口 =====================
def main():

    # ##此处是为了兼容0.1.6版本添加的开机启动
    # del_reg_value(f"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", settings.APP_NAME)
    # del_reg_value(
    #     f"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run",
    #     settings.APP_NAME,
    # )
    # 全局捕获

    sys.excepthook = except_hook

    app = QApplication(sys.argv)

    win = MainWindow()
    win.show()
    win.hide()
    # 标准Qt事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
