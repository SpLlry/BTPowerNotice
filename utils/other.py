import os

import sys

from typing import Dict, Optional, Any
import requests
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import Qt
import winshell
import win32gui


def dialog(
    parent,
    title,
    text,
    icon=QMessageBox.Icon.Question,
    buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
):
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setIcon(icon)
    # msg_box.setStandardButtons(QMessageBox.StandardButton.Close)
    msg_box.setWindowFlag(
        Qt.WindowType.Window
        | Qt.WindowType.WindowTitleHint
        | Qt.WindowType.CustomizeWindowHint
        | Qt.WindowType.WindowCloseButtonHint
    )

    # msg_box.setText(f"<b>{title}</b>")

    msg_box.setInformativeText(text)

    # msg_box.setFixedSize(300, 200)
    msg_box.setStandardButtons(buttons)

    return msg_box.exec()


def get_exe_path() -> str:
    """获取当前程序的真实路径（开发环境 / 打包 exe 都通用）"""
    if getattr(sys, "frozen", False):
        # 打包成 exe 后运行
        return sys.executable
    else:
        # 开发环境运行（.py 文件）
        return os.getcwd()


def get_exe_run_dir():
    """
    获取EXE文件所在的运行目录（兼容开发环境+打包后环境）
    """
    # # 判断是否为PyInstaller打包后的EXE程序
    # if getattr(sys, "frozen", False):
    #     # 打包为EXE：获取EXE的绝对路径
    #     app_path = os.path.dirname(sys.executable)
    # else:
    #     # print(os.path.dirname(sys.executable))
    #     # 开发环境：获取当前.py文件的绝对路径
    #     app_path = os.path.dirname(os.path.abspath(__file__))

    # # 获取文件所在的文件夹路径（即运行目录）
    # # exe_dir = os.path.dirname(app_path)
    app_path = os.getcwd()
    return app_path


def get_icon_path(relative_path):
    """
    获取资源绝对路径，兼容：开发环境 / PyInstaller打包环境
    """
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller打包后，临时解压路径
        base_path = sys._MEIPASS
    else:
        # 开发环境，当前项目路径
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def check_win_notifi():
    """
    检查 Windows 系统通知权限
    返回 (is_system_enabled: bool, is_app_enabled: bool)
    """
    try:
        # 1. 检查系统级通知总开关
        reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\PushNotifications"

        system_enabled = get_reg_value(reg_path, "ToastEnabled") == 1
    except:
        system_enabled = False

    # 2. 检查是否开启专注助手（请勿打扰）
    try:
        reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Notifications\Settings"

        silent = get_reg_value(reg_path, "SuppressToast") != 1
    except:
        silent = False

    return system_enabled, silent




if __name__ == "__main__":
    APP_NAME = "BTPowerNotice"
    # add_startup(APP_NAME, "test")

    # print("utils.py")
