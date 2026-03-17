import os
import subprocess
import sys
import winreg
import yaml


def get_exe_run_dir():
    """
    获取EXE文件所在的运行目录（兼容开发环境+打包后环境）
    """
    # 判断是否为PyInstaller打包后的EXE程序
    if getattr(sys, 'frozen', False):
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
    with open(config_path, 'r', encoding='utf-8') as f:
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
            encoding='utf-8',
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


if __name__ == '__main__':
    print()
