from tools.config import Config
from tools.setting import Settings
from tools.debug import logger
from utils import get_exe_run_dir

print(get_exe_run_dir() + "\\config\\config.ini")
config = Config(get_exe_run_dir() + "\\config\\config.ini")
settings = Settings()
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
