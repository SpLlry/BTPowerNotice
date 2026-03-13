from winrt.windows.devices.bluetooth import BluetoothDevice, BluetoothLEDevice, BluetoothConnectionStatus
from winrt.windows.devices.enumeration import DeviceInformation
from winrt.windows.storage.streams import DataReader
import asyncio
import ctypes
from ctypes import wintypes


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8)
    ]


class DEVPROPKEY(ctypes.Structure):
    _fields_ = [
        ("fmtid", GUID),
        ("pid", wintypes.DWORD)
    ]


class SP_DEVINFO_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("ClassGuid", GUID),
        ("DevInst", wintypes.DWORD),
        ("Reserved", wintypes.LPVOID)
    ]


def string_to_guid(guid_str):
    """将字符串格式的 GUID 转换为 GUID 结构"""
    # 移除大括号并分割
    guid_str = guid_str.strip('{}')
    parts = guid_str.split('-')
    if len(parts) != 5:
        raise ValueError("Invalid GUID format")

    data1 = int(parts[0], 16)
    data2 = int(parts[1], 16)
    data3 = int(parts[2], 16)
    data4 = bytes.fromhex(''.join(parts[3:]))

    return GUID(
        Data1=data1,
        Data2=data2,
        Data3=data3,
        Data4=(wintypes.BYTE * 8).from_buffer_copy(data4)
    )


# 定义 Windows API 常量和结构
CM_LOCATE_DEVNODE_NORMAL = 0x00000000
CR_SUCCESS = 0x00000000
DEVPROP_TYPE_BYTE = 0x00000001
DEVPKEY_BLUETOOTH_BATTERY = DEVPROPKEY(
    fmtid=GUID(0x104EA319, 0x6EE2, 0x4701, (0xBD, 0x47, 0x8D, 0xDB, 0xF4, 0x25, 0xBB, 0xE5)),
    pid=2
)

# 定义 Windows API 常量
GUID_DEVCLASS_SYSTEM = "{4d36e97d-e325-11ce-bfc1-08002be10318}"
DIGCF_PRESENT = 0x00000002
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value


class Bluetooth:
    def __init__(self):
        self.ble_devices = []
        """初始化蓝牙管理器"""
        # 加载 CfgMgr32.dll
        self.cfgmgr32 = ctypes.WinDLL("CfgMgr32.dll")
        # 设置函数参数和返回类型
        self.cfgmgr32.CM_Locate_DevNodeW.argtypes = [
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPCWSTR,
            wintypes.DWORD
        ]
        self.cfgmgr32.CM_Locate_DevNodeW.restype = wintypes.DWORD

        self.cfgmgr32.CM_Get_DevNode_PropertyW.argtypes = [
            wintypes.DWORD,
            ctypes.POINTER(DEVPROPKEY),
            ctypes.POINTER(wintypes.DWORD),
            ctypes.c_void_p,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.DWORD
        ]
        self.cfgmgr32.CM_Get_DevNode_PropertyW.restype = wintypes.DWORD

    async def scan_classic_devices(self):
        """
        扫描经典蓝牙设备

        Returns:
            list: 经典蓝牙设备信息列表
        """
        devices_info = []
        btc_selector = BluetoothDevice.get_device_selector()
        btc_devices = await DeviceInformation.find_all_async_aqs_filter(btc_selector)

        for device in btc_devices:
            device_info = {
                "id": device.id,
                "name": device.name,
                "type": "Classic"
            }

            # 获取设备实例
            btc_device = await BluetoothDevice.from_id_async(device.id)
            if btc_device:
                # 获取连接状态

                status = btc_device.connection_status
                is_connected = status == BluetoothConnectionStatus.CONNECTED
                device_info["connected"] = is_connected
                device_info["address"] = btc_device.bluetooth_address

                # print(self.get_bluetooth_instance_id(btc_device.bluetooth_address), 111)
                ida = self.enumerate_bluetooth_system_device(btc_device.bluetooth_address)
                device_info["battery"] = self.get_classic_battery_level(ida)

            devices_info.append(device_info)

        return devices_info

    def get_classic_battery_level(self, device_id):
        """
        获取经典蓝牙设备的电量水平

        Args:
            device_id: 设备 ID

        Returns:
            str: 电量百分比或错误信息
        """
        try:
            # 从设备 ID 中提取设备实例 ID
            # 设备 ID 格式通常为: \\?\BTHENUM#{...}#{...}
            # 我们需要提取 BTHENUM\\{...} 部分
            if "BTHENUM\\" in device_id:
                # 定位设备节点
                devnode = wintypes.DWORD()
                result = self.cfgmgr32.CM_Locate_DevNodeW(
                    ctypes.byref(devnode),
                    device_id,
                    CM_LOCATE_DEVNODE_NORMAL
                )

                if result != CR_SUCCESS:
                    return f"无法定位设备节点: {result}"
                # 获取电池属性
                battery = wintypes.BYTE()
                prop_type = wintypes.DWORD()
                size = wintypes.DWORD(ctypes.sizeof(battery))

                result = self.cfgmgr32.CM_Get_DevNode_PropertyW(
                    devnode.value,
                    ctypes.byref(DEVPKEY_BLUETOOTH_BATTERY),
                    ctypes.byref(prop_type),
                    ctypes.byref(battery),
                    ctypes.byref(size),
                    0
                )
                # print(battery.value)
                if result == CR_SUCCESS:
                    return battery.value
                else:
                    return "设备不支持电池属性"
            else:
                return "不是经典蓝牙设备"
        except Exception as e:
            return f"获取电量失败: {e}"

    def enumerate_bluetooth_system_device(self, bt_address: int) -> str | None:
        # 枚举 System 类设备
        try:
            setupapi = ctypes.WinDLL("setupapi.dll", use_last_error=True)

            # 设置函数参数和返回类型
            setupapi.SetupDiGetClassDevsW.argtypes = [
                ctypes.POINTER(GUID),
                wintypes.LPCWSTR,
                wintypes.HWND,
                wintypes.DWORD
            ]
            setupapi.SetupDiGetClassDevsW.restype = wintypes.HANDLE

            setupapi.SetupDiEnumDeviceInfo.argtypes = [
                wintypes.HANDLE,
                wintypes.DWORD,
                ctypes.POINTER(SP_DEVINFO_DATA)
            ]
            setupapi.SetupDiEnumDeviceInfo.restype = wintypes.BOOL

            setupapi.SetupDiGetDeviceInstanceIdW.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(SP_DEVINFO_DATA),
                wintypes.LPWSTR,
                wintypes.DWORD,
                ctypes.POINTER(wintypes.DWORD)
            ]
            setupapi.SetupDiGetDeviceInstanceIdW.restype = wintypes.BOOL

            setupapi.SetupDiDestroyDeviceInfoList.argtypes = [wintypes.HANDLE]
            setupapi.SetupDiDestroyDeviceInfoList.restype = wintypes.BOOL

            # 转换 GUID 字符串为 GUID 结构
            class_guid = string_to_guid(GUID_DEVCLASS_SYSTEM)

            # 获取设备信息集
            hdevinfo = setupapi.SetupDiGetClassDevsW(
                ctypes.byref(class_guid),
                None,
                0,
                DIGCF_PRESENT,
            )

            if hdevinfo == INVALID_HANDLE_VALUE:
                print(f"获取设备信息集失败，错误码: {ctypes.get_last_error()}")
                return None

            devinfo = SP_DEVINFO_DATA()
            devinfo.cbSize = ctypes.sizeof(SP_DEVINFO_DATA)
            index = 0

            # 转为 12 位大写地址（和设备实例ID一致）
            addr_hex = f"{bt_address:012X}".upper()
            # print(f"查找蓝牙地址: {addr_hex}")

            # 遍历设备
            while setupapi.SetupDiEnumDeviceInfo(hdevinfo, index, ctypes.byref(devinfo)):
                devid = ctypes.create_unicode_buffer(256)
                result = setupapi.SetupDiGetDeviceInstanceIdW(
                    hdevinfo, ctypes.byref(devinfo), devid, 256, None
                )

                if result:
                    instance_id = devid.value
                    # print(f"检查设备: {instance_id}")

                    # 筛选：BTHENUM 且 包含蓝牙地址
                    if "BTHENUM\\" in instance_id and addr_hex in instance_id:
                        setupapi.SetupDiDestroyDeviceInfoList(hdevinfo)
                        # print(f"找到匹配设备: {instance_id}")
                        return instance_id

                index += 1

            setupapi.SetupDiDestroyDeviceInfoList(hdevinfo)
            print("未找到匹配的蓝牙设备")
            return None
        except Exception as e:
            print(f"错误: {e}")
            return None


async def main():
    btc = Bluetooth()
    all_devices = await btc.scan_classic_devices()
    print(all_devices)


if __name__ == "__main__":
    asyncio.run(main())
