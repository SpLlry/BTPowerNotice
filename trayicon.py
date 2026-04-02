import sys
from PyQt6.QtGui import QCursor, QIcon, QAction
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox, QWidget
from PyQt6.QtCore import QTimer, pyqtSignal
from Settings import SettingsWindow
from about import AboutCometDialog
from update import CheckUpdateDialog, NoUpdateDialog
from skin import SkinManager
from utils import (
    get_icon_path,
    check_win_notifi,
    http_request,
    dialog,
    add_startup,
    is_self_start,
    remove_startup,
)
from win11toast import toast
from tools import dc, log, config, settings, show_toast

# 兼容开发/打包的路径函数


class TrayIcon(QSystemTrayIcon):
    skin_changed = pyqtSignal(str)
    # 核心信号：移入 / 离开
    mouseEntered = pyqtSignal()
    mouseLeft = pyqtSignal()

    def __init__(self, parent=None, skin_manager=None):
        super().__init__(parent)
        # 移入移出检测（稳定方案）
        self._hover_timer = QTimer()
        self._hover_timer.setInterval(100)
        self._hover_timer.timeout.connect(self._check_hover)
        self._is_hover = False
        self._hover_timer.start()
        self.about = None
        self.set_app = None
        self.checkUpdateDialog = None
        self.noUpdateDialog = None
        self.skin_manager = skin_manager
        self.menu = QMenu()
        self.config = config
        self.device_info = {}

        # ============== 修复核心：预创建固定数量的设备Action（复用不重建） ==============
        self.MAX_DEVICES = 4  # 最大支持4个设备（和你的电量组件对应）
        self.device_actions = []  # 复用的Action列表，不删除、只更新
        for _ in range(self.MAX_DEVICES):
            act = QAction("")
            act.setVisible(False)  # 默认隐藏
            self.device_actions.append(act)
        # 固定菜单Action（永不改变）
        self.setAction = QAction("设置")
        self.aboutAction = QAction("关于")
        self.checkUpdateAction = QAction("检查更新")

        # print(self.skin_manager.getAll())
        self.taskSkin = QMenu("任务栏样式")
        self.skin_actions = {}
        for skin in self.skin_manager.getAll():
            actskin = skin
            act = QAction(f"{actskin}", self)
            act.setCheckable(True)
            act.setChecked(skin == self.config.getVal("Settings", "skin"))
            act.triggered.connect(lambda checked, s=skin: self.on_skin_selected(s))
            self.skin_actions[skin] = act
            self.taskSkin.addAction(act)
        # # 给二级菜单添加子项（三级）
        # self.setAction.addMenu(self.taskSkin)

        # self.debugAction = QAction("调试模式")
        # self.debugAction.setCheckable(True)
        # self.debugAction.setChecked(config.getVal("Debug", "window") == '1')
        # self.setAction.addAction(self.debugAction)

        # self.selfStartAction = QAction("开机自启")
        # self.selfStartAction.setCheckable(True)
        # self.selfStartAction.setChecked(is_self_start())
        # self.setAction.addAction(self.selfStartAction)

        self.rebootAction = QAction("重启")

        self.quitAction = QAction("退出")

        # 绑定信号
        self.setAction.triggered.connect(self.set_app_fn)
        self.aboutAction.triggered.connect(self.about_app)
        self.checkUpdateAction.triggered.connect(self.check_update)
        self.quitAction.triggered.connect(self.quit_app)
        # self.debugAction.triggered.connect(self.toggle_debug)
        # self.selfStartAction.triggered.connect(self.toggle_self_start)
        self.rebootAction.triggered.connect(self.reboot_app)

        self.setTrayIcon()
        dc.subscribe("devices", self.update_device_info)

    def _check_hover(self):

        cursor_pos = QCursor.pos()

        if not self.geometry().contains(cursor_pos):
            if self._is_hover:
                self._is_hover = False
                self.mouseLeft.emit()
        else:
            if not self._is_hover:
                self._is_hover = True
                self.mouseEntered.emit()

    def setTrayIcon(self):
        self.menu.clear()

        # 1. 添加复用的设备Action（固定位置）
        for act in self.device_actions:
            self.menu.addAction(act)
        self.menu.addSeparator()

        # 2. 添加固定菜单（结构永不改变）
        self.menu.addSeparator()
        self.menu.addAction(self.setAction)
        self.menu.addAction(self.aboutAction)
        self.menu.addAction(self.checkUpdateAction)
        self.menu.addSeparator()
        self.menu.addAction(self.rebootAction)
        self.menu.addAction(self.quitAction)
        self.setContextMenu(self.menu)

        # 加载图标
        try:
            icon_path = get_icon_path("icon/icon.ico")
            self.setIcon(QIcon(icon_path))
        except Exception as e:
            log.error(f"托盘图标加载失败：{e}")
            # 备用系统图标
            standard_icon = QApplication.style().standardIcon(
                QApplication.style().StandardIcon.SP_ComputerIcon
            )
            self.setIcon(standard_icon)
        attr_title = ""
        # log.info(f"调试模式：{config.getVal('Debug', 'window')}")
        if config.getVal("Debug", "window") == "1":
            attr_title = "-debug模式"
        self.setToolTip(settings.TRAY_ICON_TOOLTIP + attr_title)
        self.activated.connect(self.on_icon_clicked)

    # ========== 菜单点击事件 ==========
    def on_skin_selected(self, skin_name):
        log.info(f"✅ 选择皮肤：{skin_name}")
        old_skin = self.config.getVal("Settings", "skin")
        if old_skin in self.skin_actions:
            old_text = old_skin
            self.skin_actions[old_skin].setText(old_text)
        # 取消其他选择状态
        for skin in self.skin_manager.getAll():
            if skin != skin_name:
                self.skin_actions[skin].setChecked(False)
        self.config.setVal("Settings", "skin", skin_name)
        self.skin_changed.emit(skin_name)
        QMessageBox.information(self.parent(), "提示", "皮肤切换成功")

    def update_device_info(self, device_info):
        # print("设备信息更新:", device_info)
        """【无闪烁核心】仅更新Action文本/可见性，不重建菜单"""
        self.device_info = device_info
        tip_text = ""
        i = 0
        # 遍历更新复用的Action
        for mac, device in device_info.items():
            i += 1
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
        attr_title = ""
        if config.getVal("Debug", "window") == "1":
            attr_title = "-debug模式"
        self.setToolTip(settings.TRAY_ICON_TOOLTIP + attr_title + tip_text)

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

    def set_app_fn(self):
        if self.set_app is not None and self.set_app.isVisible():
            self.set_app.activateWindow()
            return
        self.set_app = SettingsWindow(None, self.device_info)
        self.set_app.show()

    def about_app(self):
        if self.about is not None and self.about.isVisible():
            self.about.activateWindow()
            return
        self.about = AboutCometDialog()
        self.about.show()

    def check_update(self):
        response = http_request("GET", settings.RELEASE_URL)
        # print(response)
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
                show_toast(
                    self.parent(),
                    "提示",
                    f"已经是最新版本了,当前版本: {settings.APP_VERSION}",
                    "info",
                )
        elif response["status_code"] == 404:
            show_toast(self.parent(), "提示", response["message"], "error")
        else:
            show_toast(self.parent(), "提示", "检查更新失败", "error")

    def quit_app(self):
        ret = dialog(
            self.parent(),
            "退出确认",
            "决定要退出了嘛?",
            icon=QMessageBox.Icon.NoIcon,
            buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        print(ret, QMessageBox.StandardButton.Yes)
        if ret == QMessageBox.StandardButton.Yes:
            self.setVisible(False)
            QApplication.quit()
            sys.exit()

    def toggle_debug(self):
        is_check = "0"
        if self.debugAction.isChecked():
            is_check = "1"
            dialog(
                self.parent(),
                "调试模式",
                "已开启调试模式, 请重启后在控制台查看调试信息",
                QMessageBox.Icon.NoIcon,
                QMessageBox.StandardButton.Ok,
            )

        self.debugAction.setChecked(is_check == "1")
        config.setVal("Debug", "window", is_check)

    def toggle_self_start(self):
        is_check = "0"
        if self.selfStartAction.isChecked():
            add_startup(settings.APP_NAME, "蓝牙电量监控工具 - 开机自动运行")
            is_check = "1"
        else:
            remove_startup(settings.APP_NAME)
        self.selfStartAction.setChecked(is_check == "1")
        config.setVal("Settings", "self_start", is_check)

    def reboot_app(self):
        ret = dialog(
            self.parent(),
            "重启确认",
            "决定要重启了嘛?",
            QMessageBox.Icon.NoIcon,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret == QMessageBox.StandardButton.Yes:
            self.parent().reboot()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    main_window = QWidget()
    main_window.setWindowTitle("蓝牙电量监控")
    main_window.resize(450, 50)

    tray = TrayIcon(main_window, SkinManager("ui/ring/", "Ring"))
    tray.show()

    sys.exit(app.exec())
