# 电量相关常量
BATTERY_WARN_THRESHOLD = 20  # 电量警告阈值（%）
BATTERY_LOW_THRESHOLD = 10   # 电量极低阈值（%）

# 扫描间隔常量（秒）
SCAN_INTERVAL_DEFAULT = 5    # 默认扫描间隔（设备状态变化时）
SCAN_INTERVAL_EXTENDED = 10  # 无状态变化时延长间隔
SCAN_RETRY_TIMES = 2         # 扫描失败重试次数

# UI相关常量
MAX_DISPLAY_DEVICES = 4      # 最大显示设备数
MAX_PREV_STATES = 20  # 最大历史状态数
WINDOW_MIN_WIDTH = 400       # 主窗口最小宽度
WINDOW_MIN_HEIGHT = 300      # 主窗口最小高度


# 系统相关常量
WINDOWS_REGISTRY_AUTOSTART = (
    r"Software\Microsoft\Windows\CurrentVersion\Run"
)
