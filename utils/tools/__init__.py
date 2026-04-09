from .config import Config
from .env import Env
from .DataCenter import DataCenter
from .debug import logger,set_log_file,set_log_window
from utils.other import get_exe_run_dir
from .toast import show_toast


print(get_exe_run_dir() + "\config\config.ini")
config = Config(get_exe_run_dir() + "\config\config.ini")
env = Env()
dc = DataCenter()
show_window = config.getVal("Debug", "window") == "1"
output = config.getVal("Debug", "output") == "1"
# 全局单例（只初始化一次）
log = logger(show_window=show_window, output=output)

# print(log, config.getVal("Debug", "window"), output)
if show_window:
    log.debug("调试窗口已开启")
if output:
    log.debug("输出调试已开启")
print("工具模块调用")

# 导出模块内容
__all__ = [
    "config",
    "settings",
    "dc",
    "log",
    "show_toast",
    "set_log_file",
    "set_log_window",
    "show_success_toast",
    "show_error_toast",
    "show_info_toast",
    "show_warning_toast",
]
