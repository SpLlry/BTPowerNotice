class BluetoothBaseError(Exception):
    """蓝牙相关基础异常"""
    pass


class BluetoothScanError(BluetoothBaseError):
    """蓝牙扫描异常"""

    def __init__(self, device_mac: str = "", msg: str = ""):
        self.device_mac = device_mac
        self.msg = msg or f"蓝牙设备{device_mac}扫描失败"
        super().__init__(self.msg)


class BatteryFetchError(BluetoothBaseError):
    """设备电量获取异常"""

    def __init__(self, device_mac: str = "", msg: str = ""):
        self.device_mac = device_mac
        self.msg = msg or f"设备{device_mac}电量获取失败"
        super().__init__(self.msg)


class DeviceConnectError(BluetoothBaseError):
    """设备连接异常"""

    def __init__(self, device_mac: str = "", msg: str = ""):
        self.device_mac = device_mac
        self.msg = msg or f"设备{device_mac}连接失败"
        super().__init__(self.msg)


class ConfigReadError(Exception):
    """配置读取异常"""
    pass
