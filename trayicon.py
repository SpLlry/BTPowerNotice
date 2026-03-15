import os
import sys
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QAction, QMessageBox
)


# ✅ 万能路径函数：解决PyInstaller打包后资源丢失问题
def get_icon_path(relative_path):
    """获取图标绝对路径（兼容开发模式 + 打包exe）"""
    # 打包后：PyInstaller会将资源解压到临时文件夹 _MEIPASS
    # if hasattr(sys, '_MEIPASS'):
    #     return os.path.join(sys._MEIPASS, relative_path)
    # 开发时：直接读取本地文件
    return os.path.join(os.path.abspath("."), relative_path)


class TrayIcon(QSystemTrayIcon):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.quitAction = None
        self.showAction1 = None
        self.aboutAction = None
        self.ui = parent
        self.menu = QMenu()
        self.showDeviceAction = []
        # self.setTrayIcon()

    def setTrayIcon(self):
        self.menu.addSeparator()
        self.aboutAction = QAction("关于", triggered=self.about_app)
        self.quitAction = QAction("退出", triggered=self.quit_app)
        self.menu.addAction(self.showAction1)
        self.menu.addAction(self.aboutAction)
        self.menu.addSeparator()
        self.menu.addAction(self.quitAction)
        self.setContextMenu(self.menu)

        # show_action = QAction("显示", self)
        # hide_action = QAction("隐藏", self)
        # quit_action = QAction("退出", self)
        #
        # self.menu.addAction(show_action)
        # self.menu.addAction(hide_action)
        # self.menu.addSeparator()  # ← 分割线
        # self.menu.addAction(quit_action)
        #
        # self.setContextMenu(self.menu)
        #
        # # 连接信号（可选）
        # quit_action.triggered.connect(QApplication.quit)
        try:

            self.setIcon(QIcon(get_icon_path("icon/icon.ico")))
        except:
            self.setIcon(QIcon.fromTheme("bluetooth"))

    def update_device_info(self, device_info):
        # return
        # 【主线程安全更新托盘】
        print("更新设备信息111", device_info)
        self.showDeviceAction.clear()
        print("更新设备信息11221", device_info)
        tip_text = ""
        for device in device_info:
            status_icon = "✅" if device.get("connected") else "❌"
            tip_text += f"\n{status_icon}{device.get('name')}: {device.get('battery', '?')}%"
            self.showDeviceAction.append(QAction(f"{status_icon}{device['name']}|{device['battery']}%"))

        # 清空旧菜单
        for act in self.menu.actions():
            if act not in [self.showAction1, self.aboutAction, self.quitAction]:
                print(act)
                self.menu.removeAction(act)
        # 添加新设备
        for act in self.showDeviceAction:
            self.menu.insertAction(self.menu.actions()[0], act)
        self.menu.addSeparator()
        self.setToolTip("蓝牙设备电量" + tip_text)

    def on_icon_clicked(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.parent().setVisible(not self.parent().isVisible())

    # ===================== 核心：重写事件捕获移入/移出 =====================
    def about_app(self):

        QMessageBox.about(self.ui, "关于", "本程序由PyQt5开发\n开源地址：https://github.com/SpLlry/BTPowerNotice")

    def quit_app(self):
        check_flag = QMessageBox.information(self.ui, "退出确认", "是否确认退出？", QMessageBox.Yes | QMessageBox.No)
        print(check_flag, QMessageBox.Yes, QMessageBox.No)
        if check_flag == QMessageBox.Yes:
            self.setVisible(False)
            self.parent().close()
            QApplication.quit()
            sys.exit()
        else:
            pass
