import os
import subprocess
import sys
import winreg
import yaml
from typing import Dict, Optional, Any
import requests


def get_exe_run_dir():
    """
    获取EXE文件所在的运行目录（兼容开发环境+打包后环境）
    """
    # 判断是否为PyInstaller打包后的EXE程序
    if getattr(sys, "frozen", False):
        # 打包为EXE：获取EXE的绝对路径
        app_path = os.path.dirname(sys.executable)
    else:
        print(os.path.dirname(sys.executable))
        # 开发环境：获取当前.py文件的绝对路径
        app_path = os.path.dirname(os.path.abspath(__file__))

    # 获取文件所在的文件夹路径（即运行目录）
    # exe_dir = os.path.dirname(app_path)
    return app_path


def get_config(config_path: str):
    """
    从 config.json 文件读取配置
    :return: 配置字典
    """
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def run_powershell_command(ps_script: str, to_json: bool = False) -> str:
    """
    执行 PowerShell 脚本并返回标准输出
    :param ps_script: PowerShell 脚本内容
    :return: 脚本执行结果（标准输出）
    """
    try:
        if to_json:
            ps_script += " | ConvertTo-Json -Depth 3"
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.stderr:
            print(f"PowerShell 执行错误: {result.stderr}")
            return None
        return result.stdout.strip()
    except Exception as e:
        print(f"Python 调用失败: {str(e)}")
        return None


def get_reg_value(reg_path: str, reg_key: str):
    """
    获取注册表项的值
    :param reg_path: 注册表项路径
    :param reg_key: 注册表项键名
    :return: 注册表项的值
    """
    try:
        # 打开当前用户的注册表项
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
            # 读取TaskbarAl的DWORD值
            value, _ = winreg.QueryValueEx(key, reg_key)
            # print(value)

            # 根据值判断对齐方式
            return value

    except FileNotFoundError:
        # 非Windows 11系统，无此注册表项
        return -1
    except Exception as e:
        # 其他异常（权限/系统错误）
        print(f"获取失败：{str(e)}")
        return -2


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
    return get_reg_value(reg_path, reg_key)


def get_windows_system_theme() -> int:
    """
    获取当前系统主题（1: 浅色，0: 深色）
    """
    reg_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
    reg_key = "SystemUsesLightTheme"
    return get_reg_value(reg_path, reg_key)


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


def http_request(
    method: str,
    url: str,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    json: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 10,
) -> Dict[str, Any]:
    """
    通用的HTTP请求工具方法，支持GET/POST请求

    Args:
        method: 请求方法，支持'GET'/'POST'（大小写不敏感）
        url: 请求的URL地址
        params: URL查询参数（GET请求专用），默认为None
        data: POST表单数据（application/x-www-form-urlencoded），默认为None
        json: POST JSON数据（application/json），默认为None
        headers: 请求头，默认为None
        timeout: 请求超时时间（秒），默认为10秒

    Returns:
        字典格式的响应结果，包含：
        - success: 布尔值，请求是否成功
        - status_code: HTTP状态码（成功时返回，失败时为None）
        - response: 响应内容（JSON/文本，成功时返回，失败时为None）
        - error: 错误信息（失败时返回，成功时为None）
    """
    # 初始化返回结果
    result = {"success": False, "status_code": None, "response": None, "error": None}
    if headers is None:
        headers = {}
    if headers.get("User-Agent") is None:
        headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        )
    # 统一请求方法为大写
    method = method.upper()

    # 校验请求方法是否支持
    if method not in ["GET", "POST"]:
        result["error"] = f"不支持的请求方法：{method}，仅支持GET/POST"
        return result

    try:
        # 根据请求方法发送请求
        if method == "GET":
            response = requests.get(
                url=url, params=params, headers=headers, timeout=timeout
            )
        elif method == "POST":
            response = requests.post(
                url=url,
                params=params,  # POST也支持URL参数
                data=data,
                json=json,
                headers=headers,
                timeout=timeout,
            )

        # 检查HTTP状态码，4xx/5xx会抛出异常
        response.raise_for_status()

        # 尝试解析JSON响应，失败则返回文本
        try:
            response_data = response.json()
        except ValueError:
            response_data = response.text

        # 更新成功的返回结果
        result["success"] = True
        result["status_code"] = response.status_code
        result["response"] = response_data

    except requests.exceptions.Timeout:
        result["error"] = f"请求超时（超时时间：{timeout}秒）"
    except requests.exceptions.ConnectionError:
        result["error"] = "网络连接错误（无法连接到服务器）"
    except requests.exceptions.HTTPError as e:
        result["error"] = f"HTTP请求错误：{str(e)}"
        result["status_code"] = response.status_code if "response" in locals() else None
    except Exception as e:
        result["error"] = f"未知错误：{str(e)}"

    return result


if __name__ == "__main__":
    print("utils.py")
