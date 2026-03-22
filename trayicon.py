import os
import sys
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox, QWidget
from PyQt6.QtCore import QTimer, pyqtSignal

from about import AboutCometDialog
from update import CheckUpdateDialog, NoUpdateDialog
from setting import settings
from skin import SkinManager
from utils import get_icon_path, check_win_notifi, http_request
from config import create_config
from win11toast import toast


# 兼容开发/打包的路径函数


class TrayIcon(QSystemTrayIcon):
    skin_changed = pyqtSignal(str)

    def __init__(self, parent=None, skin_manager=None, config=None):
        super().__init__(parent)
        self.about = None
        self.checkUpdateDialog = None
        self.noUpdateDialog = None
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
        self.checkUpdateAction = QAction("检查更新")

        # print(self.skin_manager.getAll())
        self.taskSkin = QMenu("任务栏样式")
        self.skin_actions = {}
        for skin in self.skin_manager.getAll():
            actskin = skin
            if self.config.getVal("setting", "skin") == skin:
                actskin = f"✅{skin}"
            act = QAction(f"{actskin}", self)
            act.triggered.connect(lambda checked, s=skin: self.on_skin_selected(s))
            self.skin_actions[skin] = act
            self.taskSkin.addAction(act)
        #  关键修复：必须用 QAction

        # # 给二级菜单添加子项（三级）
        self.setAction.addMenu(self.taskSkin)

        self.quitAction = QAction("退出")

        # 绑定信号
        self.aboutAction.triggered.connect(self.about_app)
        self.checkUpdateAction.triggered.connect(self.check_update)
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
        self.menu.addAction(self.checkUpdateAction)
        self.menu.addSeparator()
        self.menu.addAction(self.quitAction)

        self.setContextMenu(self.menu)

        # 加载图标
        try:
            icon_path = get_icon_path("icon/icon.ico")
            self.setIcon(QIcon(icon_path))
        except Exception as e:
            print(f"托盘图标加载失败：{e}")
            # 备用系统图标
            standard_icon = QApplication.style().standardIcon(
                QApplication.style().StandardIcon.SP_ComputerIcon
            )
            self.setIcon(standard_icon)

        self.setToolTip(settings.TRAY_ICON_TOOLTIP)
        self.activated.connect(self.on_icon_clicked)

    # ========== 菜单点击事件 ==========
    def on_skin_selected(self, skin_name):
        print(f"✅ 选择皮肤：{skin_name}")
        old_skin = self.config.getVal("setting", "skin")
        if old_skin in self.skin_actions:
            old_text = old_skin
            self.skin_actions[old_skin].setText(old_text)

        self.config.setVal("setting", "skin", skin_name)
        new_text = f"✅{skin_name}"
        self.skin_actions[skin_name].setText(new_text)

        self.skin_changed.emit(skin_name)
        QMessageBox.information(self.ui, "提示", "皮肤切换成功")

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
        self.setToolTip(settings.TRAY_ICON_TOOLTIP + tip_text)

    def show_main_window(self):
        if self.parent():
            self.parent().show()
            self.parent().activateWindow()

    def on_icon_clicked(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            if not self.parent():
                return
            self.parent().setVisible(not self.parent().isVisible())

    def about_app(self):
        if self.about is not None and self.about.isVisible():
            self.about.activateWindow()
            return
        self.about = AboutCometDialog()
        self.about.show()

    def check_update(self):
        response = http_request("GET", settings.RELEASE_URL)
        if response["status_code"] == 200:
            latest_info = response["response"]
            latest_version = latest_info.get("tag_name", "").lstrip("v")
            current_version = settings.APP_VERSION.lstrip("v")
            print(
                f"最新版本: {latest_version}, 当前版本: {current_version}",
                latest_version > current_version,
            )
            if latest_version > current_version:
                self.checkUpdateDialog = CheckUpdateDialog(latest_info)
                self.checkUpdateDialog.show()
            else:
                self.noUpdateDialog = NoUpdateDialog()
                self.noUpdateDialog.show()
        elif response["status_code"] == 404:
            QMessageBox.information(self.ui, "提示", "404")
        else:
            QMessageBox.information(self.ui, "提示", "检查更新失败")

    def quit_app(self):
        if (
            QMessageBox.information(
                self.ui,
                "退出确认",
                "是否确认退出？",
                QMessageBox.StandardButton.Yes,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.setVisible(False)
            QApplication.quit()
            sys.exit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    main_window = QWidget()
    main_window.setWindowTitle("蓝牙电量监控")
    main_window.resize(450, 50)

    tray = TrayIcon(main_window, SkinManager("ui/ring/"), create_config())
    tray.show()

    sys.exit(app.exec())
