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
    fmtid=GUID(0x104EA319, 0x6EE2, 0x4701,
               (0xBD, 0x47, 0x8D, 0xDB, 0xF4, 0x25, 0xBB, 0xE5)),
    pid=2
)

# 定义 Windows API 常量
GUID_DEVCLASS_SYSTEM = "{4d36e97d-e325-11ce-bfc1-08002be10318}"
DIGCF_PRESENT = 0x00000002
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value


class Bluetooth:
    def __init__(self):
        self.ble_devices = []
        self._setupapi = None
        self._setupapi_initialized = False
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

    def _init_setupapi(self):
        if self._setupapi_initialized:
            return
        self._setupapi = ctypes.WinDLL("setupapi.dll", use_last_error=True)
        self._setupapi.SetupDiGetClassDevsW.argtypes = [
            ctypes.POINTER(GUID),
            wintypes.LPCWSTR,
            wintypes.HWND,
            wintypes.DWORD
        ]
        self._setupapi.SetupDiGetClassDevsW.restype = wintypes.HANDLE

        self._setupapi.SetupDiEnumDeviceInfo.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            ctypes.POINTER(SP_DEVINFO_DATA)
        ]
        self._setupapi.SetupDiEnumDeviceInfo.restype = wintypes.BOOL

        self._setupapi.SetupDiGetDeviceInstanceIdW.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(SP_DEVINFO_DATA),
            wintypes.LPWSTR,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD)
        ]
        self._setupapi.SetupDiGetDeviceInstanceIdW.restype = wintypes.BOOL

        self._setupapi.SetupDiDestroyDeviceInfoList.argtypes = [
            wintypes.HANDLE]
        self._setupapi.SetupDiDestroyDeviceInfoList.restype = wintypes.BOOL

        self._setupapi_initialized = True

    async def scan_btc_devices(self):
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
                "type": "BTC"
            }

            btc_device = None
            try:
                btc_device = await BluetoothDevice.from_id_async(device.id)
                if btc_device:
                    status = btc_device.connection_status
                    is_connected = status == BluetoothConnectionStatus.CONNECTED
                    device_info["connected"] = is_connected
                    device_info["address"] = btc_device.bluetooth_address

                    status, msg, ida = self.enumerate_bluetooth_system_device(
                        btc_device.bluetooth_address)
                    if status != 0:
                        device_info["battery"] = 0
                        continue
                    status, msg, battery = self.get_classic_battery_level(ida)
                    if status == 0:
                        device_info["battery"] = battery
            except Exception as e:
                status = -1
                msg = str(e)
            finally:
                if btc_device:
                    btc_device.close()

            devices_info.append(
                {"code": status, "msg": msg, "data": device_info})

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
                    # return f"无法定位设备节点: {result}"、
                    return -4, f"无法定位设备节点: {result}", {}
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
                    return 0, "ok", battery.value
                else:
                    # return "设备不支持电池属性"
                    return -1, "设备不支持电池属性", {}
            else:
                # return "不是经典蓝牙设备"
                return -2, "不是经典蓝牙设备", {}
        except Exception as e:
            # return f"获取电量失败: {e}"
            return -3, f"获取电量失败: {e}", {}

    def enumerate_bluetooth_system_device(self, bt_address: int) -> str | None:
        self._init_setupapi()
        setupapi = self._setupapi

        class_guid = string_to_guid(GUID_DEVCLASS_SYSTEM)

        hdevinfo = setupapi.SetupDiGetClassDevsW(
            ctypes.byref(class_guid),
            None,
            0,
            DIGCF_PRESENT,
        )

        if hdevinfo == INVALID_HANDLE_VALUE:
            print(f"获取设备信息集失败，错误码: {ctypes.get_last_error()}")
            return -4, f"获取设备信息集失败，错误码: {ctypes.get_last_error()}", {}

        devinfo = SP_DEVINFO_DATA()
        devinfo.cbSize = ctypes.sizeof(SP_DEVINFO_DATA)
        index = 0

        addr_hex = f"{bt_address:012X}".upper()

        while setupapi.SetupDiEnumDeviceInfo(hdevinfo, index, ctypes.byref(devinfo)):
            devid = ctypes.create_unicode_buffer(256)
            result = setupapi.SetupDiGetDeviceInstanceIdW(
                hdevinfo, ctypes.byref(devinfo), devid, 256, None
            )

            if result:
                instance_id = devid.value

                if "BTHENUM\\" in instance_id and addr_hex in instance_id:
                    setupapi.SetupDiDestroyDeviceInfoList(hdevinfo)
                    return 0, "ok", instance_id

            index += 1

        setupapi.SetupDiDestroyDeviceInfoList(hdevinfo)
        print("未找到匹配的蓝牙设备")
        return -2, "error", "未找到匹配的蓝牙设备"

    async def scan_single_device(self, address: str):
        """扫描单个BTC设备"""
        try:
            # 将地址转换为整数
            if isinstance(address, str):
                # 处理带冒号的地址格式，如 "E0:51:7F:67:A3:88"
                if ":" in address:
                    address = address.replace(":", "")
                address = int(address, 16)
            
            # 使用winrt API获取设备信息
            btc_selector = BluetoothDevice.get_device_selector()
            btc_devices = await DeviceInformation.find_all_async_aqs_filter(btc_selector)
            
            for device in btc_devices:
                btc_device = None
                try:
                    btc_device = await BluetoothDevice.from_id_async(device.id)
                    if btc_device and btc_device.bluetooth_address == address:
                        device_info = {
                            "id": device.id,
                            "name": device.name,
                            "type": "BTC",
                            "address": btc_device.bluetooth_address
                        }

                        status = btc_device.connection_status
                        is_connected = status == BluetoothConnectionStatus.CONNECTED
                        device_info["connected"] = is_connected

                        if is_connected:
                            # 获取设备实例ID
                            status, msg, instance_id = self.enumerate_bluetooth_system_device(address)
                            if status == 0:
                                # 获取电量
                                status_code, msg, battery = self.get_classic_battery_level(instance_id)
                                device_info["battery"] = battery if status_code == 0 else 0
                            else:
                                device_info["battery"] = 0
                        else:
                            device_info["battery"] = 0

                        return {"code": 0, "msg": "ok", "data": device_info}
                except Exception as e:
                    continue
                finally:
                    if btc_device:
                        btc_device.close()

            return None
        except Exception as e:
            return None


async def main():
    btc = Bluetooth()
    all_devices = await btc.scan_btc_devices()
    print(all_devices)


if __name__ == "__main__":
    asyncio.run(main())
