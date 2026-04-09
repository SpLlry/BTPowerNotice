import ctypes
import winreg
import os
import winshell
from typing import Any
import win32gui
from win32com.client import Dispatch
from .other import (
    get_exe_path
)
# Windows API 常量
HWND_DESKTOP = 0
ABSMONITOR = 0
SPI_GETWORKAREA = 48
SPI_GETDOCKINGRECT = 0x0030


class RECT(ctypes.Structure):
    """Windows RECT结构体"""
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long)
    ]


def get_task_bar_w11(task_align: int = 1):
    """获取任务栏位置：top/bottom/left/right"""
    task_bar = "Shell_TrayWnd"
    hwnd = win32gui.FindWindow(task_bar, None)
    h1 = hwnd
    if task_align == 0:
        h1 = win32gui.FindWindowEx(hwnd, None, "TrayNotifyWnd", None)
    if not hwnd:
        return None
    left, top, right, bottom = win32gui.GetWindowRect(h1)
    return {
        "handle": hwnd,
        "t": top,
        "l": left,
        "r": right,
        "b": bottom,
        "w": right - left,
        "h": bottom - top,
    }


def get_windows_system_theme() -> int:
    """
    获取当前系统主题（1: 浅色，0: 深色）
    """
    reg_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
    reg_key = "SystemUsesLightTheme"
    return get_reg_value(reg_path, reg_key)


def get_win11_taskbar_alignment() -> int:
    """
    获取Windows 11任务栏的对齐方式
    返回值：
        - 1居中 0左对齐
        - "居中对齐" / "左对齐"：成功获取
        - None：获取失败（非Win11/注册表项不存在）
    """
    # 注册表固定路径
    reg_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
    reg_key = "TaskbarAl"
    ret = get_reg_value(reg_path, reg_key)
    if ret is None:
        return 0
    return ret


def add_startup(app_name, description):
    """
    添加开机自启 + 友好说明（启动项列表可见）
    :param description: 你想显示的说明文字
    """

    startup_folder = winshell.startup()  # 获取用户开机启动文件夹
    shortcut_path = os.path.join(startup_folder, f"{app_name}.lnk")
    # 检查快捷方式是否存在
    print(shortcut_path)
    if os.path.exists(shortcut_path):
        print(f"⚠️ 已存在开机自启项：{app_name}")
        return True

    # 创建快捷方式
    shell = Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.TargetPath = get_exe_path()
    shortcut.WorkingDirectory = os.path.dirname(get_exe_path())
    shortcut.Description = description  # 任务管理器显示的描述
    shortcut.save()
    return True


def remove_startup(app_name):
    """删除开机自启（快捷方式方案，替换原注册表删除）"""
    try:
        # 获取用户开机启动文件夹
        startup_folder = winshell.startup()
        # 拼接快捷方式完整路径
        shortcut_path = os.path.join(startup_folder, f"{app_name}.lnk")

        # 如果快捷方式存在，执行删除
        if os.path.exists(shortcut_path):
            os.remove(shortcut_path)
            print(f"❌ 开机自启已删除：{app_name}")
        else:
            print(f"ℹ️ 未检测到开机自启项：{app_name}")

    except Exception as e:
        print(f"❌ 删除开机自启失败：{str(e)}")


# -------------------------- 【检查开机自启】适配快捷方式版本 --------------------------
def is_self_start() -> bool:
    """检查是否开机自启（快捷方式方案，替换原注册表检查）"""
    APP_NAME = "BTPowerNotice"  # 你的应用名称（保持和你原来的一致）
    try:
        # 获取开机启动文件夹
        startup_folder = winshell.startup()
        shortcut_path = os.path.join(startup_folder, f"{APP_NAME}.lnk")
        # 直接判断快捷方式文件是否存在 = 是否开机自启
        return os.path.exists(shortcut_path)

    except Exception as e:
        print(f"❌ 检查开机自启状态失败：{str(e)}")
        return False


def get_reg_value(reg_path: str, reg_key: str, default=None) -> Any:
    """
    通用：读取注册表值（推荐搭配使用）
    """
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path)
        value, _ = winreg.QueryValueEx(key, reg_key)
        winreg.CloseKey(key)
        return value
    except FileNotFoundError:
        return default
    except Exception as e:
        print(f"[读取注册表失败] {reg_key}：{str(e)}")
        return default


def set_reg_value(
    reg_path: str, reg_key: str, value: Any, value_type=winreg.REG_SZ
) -> bool:
    """
    通用：设置注册表值
    :param reg_path: 注册表路径，如 r"Software\Microsoft\Windows\CurrentVersion\Run"
    :param reg_key: 键名（项目名）
    :param value: 要写入的值
    :param value_type: 类型，默认字符串 REG_SZ，数字用 REG_DWORD
    :return: 成功 True / 失败 False
    """
    try:
        # 打开或创建注册表项
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path)
        winreg.SetValueEx(key, reg_key, 0, value_type, value)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[设置注册表失败] {reg_key}：{str(e)}")
        return False


def del_reg_value(reg_path: str, reg_key: str) -> bool:
    """
    通用：删除注册表值
    :param reg_path: 注册表路径
    :param reg_key: 要删除的键名
    :return: 成功 True / 失败 False
    """
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             reg_path, 0, winreg.KEY_WRITE)
        winreg.DeleteValue(key, reg_key)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        # 本来就不存在，也算成功
        return True
    except Exception as e:
        print(f"[删除注册表失败] {reg_key}：{str(e)}")
        return False
