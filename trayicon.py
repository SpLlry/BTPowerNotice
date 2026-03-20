import os
import sys
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu,
    QMessageBox, QWidget
)

from about import AboutCometDialog
from skin import SkinManager
from utils import get_icon_path, check_win_notifi
from config import create_config
from win11toast import toast


# 兼容开发/打包的路径函数


class TrayIcon(QSystemTrayIcon):
    def __init__(self, parent=None, skin_manager=None, config=None):
        super().__init__(parent)
        self.about = None
        self.ui = parent
        self.skin_manager = skin_manager
        self.menu = QMenu()
        self.config = config

        # ============== 修复核心：预创建固定数量的设备Action（复用不重建） ==============
        self.MAX_DEVICES = 4  # 最大支持4个设备（和你的电量组件对应）
        self.device_actions = []  # 复用的Action列表，不删除、只更新
        for _ in range(self.MAX_DEVICES):
            act = QAction("")
            act.setVisible(False)  # 默认隐藏
            self.device_actions.append(act)
        # 固定菜单Action（永不改变）
        self.setAction = QMenu("设置")
        self.aboutAction = QAction("关于")

        # print(self.skin_manager.getAll())
        self.taskSkin = QMenu("任务栏样式")
        # self.taskSkin.addAction(QAction("默认", self))
        for skin in self.skin_manager.getAll():
            actskin = skin
            if self.config.getVal("setting", "skin") == skin:
                actskin = f"✅{skin}"
            act = QAction(f"{actskin}", self)
            act.triggered.connect(lambda checked, s=skin: self.on_skin_selected(s))
            self.taskSkin.addAction(act)
        #  关键修复：必须用 QAction

        # # 给二级菜单添加子项（三级）
        self.setAction.addMenu(self.taskSkin)

        self.quitAction = QAction("退出")

        # 绑定信号
        self.aboutAction.triggered.connect(self.about_app)
        self.quitAction.triggered.connect(self.quit_app)

        self.setTrayIcon()

    def setTrayIcon(self):
        self.menu.clear()

        # 1. 添加复用的设备Action（固定位置）
        for act in self.device_actions:
            self.menu.addAction(act)
        self.menu.addSeparator()

        # 2. 添加固定菜单（结构永不改变）
        self.menu.addSeparator()
        self.menu.addMenu(self.setAction)
        self.menu.addAction(self.aboutAction)
        self.menu.addSeparator()
        self.menu.addAction(self.quitAction)

        self.setContextMenu(self.menu)

        # 加载图标
        try:
            icon_path = get_icon_path("icon/icon.ico")
            self.setIcon(QIcon(icon_path))
        except  Exception as e:
            print(f"托盘图标加载失败：{e}")
            # 备用系统图标
            standard_icon = QApplication.style().standardIcon(QApplication.style().StandardIcon.SP_ComputerIcon)
            self.setIcon(standard_icon)

        self.setToolTip("蓝牙设备电量通知")
        self.activated.connect(self.on_icon_clicked)

    # ========== 菜单点击事件 ==========
    def on_skin_selected(self, skin_name):

        print(f"✅ 选择皮肤：{skin_name}")
        self.config.setVal("setting", "skin", skin_name)
        # 原生消息弹窗
        system_enabled, silent = check_win_notifi()
        print(system_enabled, silent)
        if system_enabled and silent:
            toast(
                "切换成功",
                "需要重启应用才能生效",
                icon=os.path.abspath(get_icon_path("icon/icon.ico")),
                duration="short",
                app_id="BTPowerNotice"
            )
        else:
            QMessageBox.information(self.ui, "提示", "皮肤切换成功，重启应用生效")

    def update_device_info(self, device_info):
        # print("设备信息更新:", device_info)
        """【无闪烁核心】仅更新Action文本/可见性，不重建菜单"""
        tip_text = ""
        # 遍历更新复用的Action
        for i, device in enumerate(device_info):
            if i >= self.MAX_DEVICES:
                break
            connected = device.get("connected")
            status_icon = "✅" if connected else "🚫"
            name = device.get("name", "未知设备")
            battery = device.get("battery", "?")
            # 仅更新文本，不重建对象
            if connected:
                icon_path = get_icon_path("icon/connect.png")
            else:
                icon_path = get_icon_path("icon/disconnect.png")
            # self.device_actions[i].setIcon(QIcon(get_icon_path(icon_path)))
            self.device_actions[i].setText(f"{name} | {battery}%")
            # self.device_actions[i].setVisible(True)
            tip_text += f"\n{status_icon}{name}: {battery}%"

        # 隐藏多余的Action
        for i in range(len(device_info), self.MAX_DEVICES):
            self.device_actions[i].setVisible(False)

        # 更新托盘提示文字
        self.setToolTip("蓝牙设备电量" + tip_text)

    def show_main_window(self):
        if self.parent():
            self.parent().show()
            self.parent().activateWindow()

    def on_icon_clicked(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            if not self.parent():
                return
            self.parent().setVisible(not self.parent().isVisible())

    def about_app(self):
        self.about = AboutCometDialog()
        self.about.show()

    def quit_app(self):
        if QMessageBox.information(self.ui, "退出确认", "是否确认退出？",
                                   QMessageBox.StandardButton.Yes,
                                   QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.setVisible(False)
            QApplication.quit()
            sys.exit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    main_window = QWidget()
    main_window.setWindowTitle("蓝牙电量监控")
    main_window.resize(450, 50)

    tray = TrayIcon(main_window, SkinManager("ui/ring/"), create_config())
    tray.show()

    # 测试循环更新（模拟你的异步/定时刷新，无闪烁）
    import random
    import time
    from PyQt6.QtCore import QTimer


    def test_update():
        if random.random() < 0.5:
            test_devices = [
                {"name": "设备1", "battery": random.randint(0, 100), "connected": True},
                {"name": "设备2", "battery": random.randint(0, 100), "connected": False},
                {"name": "设备3", "battery": random.randint(0, 100), "connected": True},
                {"name": "设备4", "battery": random.randint(0, 100), "connected": False},
            ]
        else:
            test_devices = [
                {"name": "蓝牙耳机", "connected": True, "battery": random.randint(50, 100)},
                {"name": "蓝牙键盘", "connected": random.choice([True, False]), "battery": random.randint(20, 80)},
                {"name": "蓝牙鼠标", "connected": True, "battery": random.randint(30, 90)}
            ]
        tray.update_device_info(test_devices)


    # 定时循环测试（1秒刷新一次，完全不闪）
    timer = QTimer()
    timer.timeout.connect(test_update)
    timer.start(1000)

    sys.exit(app.exec())
