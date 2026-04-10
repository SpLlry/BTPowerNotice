from winrt.windows.devices.bluetooth import BluetoothDevice, BluetoothConnectionStatus
from winrt.windows.devices.enumeration import DeviceInformation
import asyncio
import ctypes
from ctypes import wintypes
from typing import List, Dict, Tuple, Union, Optional, Any


class GUID(ctypes.Structure):
    """GUID 结构"""
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8)
    ]


class DEVPROPKEY(ctypes.Structure):
    """设备属性键结构"""
    _fields_ = [
        ("fmtid", GUID),
        ("pid", wintypes.DWORD)
    ]


class SP_DEVINFO_DATA(ctypes.Structure):
    """设备信息数据结构"""
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("ClassGuid", GUID),
        ("DevInst", wintypes.DWORD),
        ("Reserved", wintypes.LPVOID)
    ]


def string_to_guid(guid_str: str) -> GUID:
    """将字符串格式的 GUID 转换为 GUID 结构
    
    Args:
        guid_str: 字符串格式的 GUID
        
    Returns:
        GUID: GUID 结构
        
    Raises:
        ValueError: GUID 格式无效
    """
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
    """经典蓝牙设备管理类
    
    负责扫描经典蓝牙设备、获取设备信息和电量
    """
    
    def __init__(self):
        """初始化蓝牙管理器"""
        self._setupapi = None
        self._setupapi_initialized = False
        self._cached_battery = {}
        self._max_cache_size = 20
        
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

    def _init_setupapi(self) -> None:
        """初始化 setupapi.dll"""
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

    def _is_device_connected(self, btc_device: BluetoothDevice) -> bool:
        """检查设备连接状态
        
        Args:
            btc_device: 蓝牙设备实例
            
        Returns:
            bool: 是否已连接
        """
        try:
            return btc_device.connection_status == BluetoothConnectionStatus.CONNECTED
        except Exception as e:
            print(f"检查连接状态失败: {e}")
            return False

    def _get_device_basic_info(self, device: DeviceInformation, btc_device: BluetoothDevice) -> Dict[str, Any]:
        """构建设备基本信息
        
        Args:
            device: 设备信息对象
            btc_device: 蓝牙设备对象
            
        Returns:
            dict: 设备基本信息字典
        """
        return {
            "id": device.id,
            "name": device.name,
            "type": "BTC",
            "address": btc_device.bluetooth_address,
            "connected": self._is_device_connected(btc_device)
        }

    def _cleanup_cache(self) -> None:
        """清理缓存，保持缓存大小在合理范围内"""
        if len(self._cached_battery) > self._max_cache_size:
            # 移除最旧的缓存项
            oldest_keys = list(self._cached_battery.keys())[:-self._max_cache_size]
            for key in oldest_keys:
                self._cached_battery.pop(key, None)

    def _get_battery_from_cache(self, device_id: str) -> Optional[int]:
        """从缓存获取电量
        
        Args:
            device_id: 设备ID
            
        Returns:
            Optional[int]: 电量值或 None
        """
        if device_id in self._cached_battery:
            print(f"使用缓存电量: {device_id}")
            return self._cached_battery[device_id]
        return None

    def _update_battery_cache(self, device_id: str, battery: int) -> None:
        """更新电量缓存
        
        Args:
            device_id: 设备ID
            battery: 电量值
        """
        self._cached_battery[device_id] = battery
        self._cleanup_cache()
        print(f"更新电量缓存: {device_id} -> {battery}%")

    def get_classic_battery_level(self, device_id: str) -> Tuple[int, str, int]:
        """获取经典蓝牙设备的电量水平
        
        Args:
            device_id: 设备 ID
            
        Returns:
            Tuple[int, str, int]: (状态码, 消息, 电量值)
                状态码: 0成功, -1不支持电池属性, -2不是经典蓝牙设备, -3获取失败, -4无法定位设备
        """
        # 尝试从缓存获取
        cached_battery = self._get_battery_from_cache(device_id)
        if cached_battery is not None:
            return 0, "已缓存电量", cached_battery

        try:
            # 从设备 ID 中提取设备实例 ID
            if "BTHENUM\\" in device_id:
                # 定位设备节点
                devnode = wintypes.DWORD()
                result = self.cfgmgr32.CM_Locate_DevNodeW(
                    ctypes.byref(devnode),
                    device_id,
                    CM_LOCATE_DEVNODE_NORMAL
                )

                if result != CR_SUCCESS:
                    error_msg = f"无法定位设备节点: {result}"
                    print(error_msg)
                    return -4, error_msg, 0
                    
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
                
                if result == CR_SUCCESS:
                    battery_value = battery.value
                    # 确保电量值在有效范围内
                    if 0 <= battery_value <= 100:
                        self._update_battery_cache(device_id, battery_value)
                        return 0, "ok", battery_value
                    else:
                        print(f"电量值异常: {battery_value}")
                        return -1, "电量值异常", 0
                else:
                    print("设备不支持电池属性")
                    return -1, "设备不支持电池属性", 0
            else:
                print("不是经典蓝牙设备")
                return -2, "不是经典蓝牙设备", 0
        except Exception as e:
            error_msg = f"获取电量失败: {e}"
            print(error_msg)
            return -3, error_msg, 0

    def enumerate_bluetooth_system_device(self, bt_address: int) -> Tuple[int, str, str]:
        """枚举蓝牙系统设备
        
        Args:
            bt_address: 蓝牙地址（整数形式）
            
        Returns:
            Tuple[int, str, str]: (状态码, 消息, 设备实例ID)
                状态码: 0成功, -2未找到设备, -4获取设备信息失败
        """
        self._init_setupapi()
        setupapi = self._setupapi

        try:
            class_guid = string_to_guid(GUID_DEVCLASS_SYSTEM)

            hdevinfo = setupapi.SetupDiGetClassDevsW(
                ctypes.byref(class_guid),
                None,
                0,
                DIGCF_PRESENT,
            )

            if hdevinfo == INVALID_HANDLE_VALUE:
                error_code = ctypes.get_last_error()
                error_msg = f"获取设备信息集失败，错误码: {error_code}"
                print(error_msg)
                return -4, error_msg, ""

            devinfo = SP_DEVINFO_DATA()
            devinfo.cbSize = ctypes.sizeof(SP_DEVINFO_DATA)
            index = 0

            addr_hex = f"{bt_address:012X}".upper()
            print(f"查找蓝牙地址: {addr_hex}")

            while setupapi.SetupDiEnumDeviceInfo(hdevinfo, index, ctypes.byref(devinfo)):
                devid = ctypes.create_unicode_buffer(256)
                result = setupapi.SetupDiGetDeviceInstanceIdW(
                    hdevinfo, ctypes.byref(devinfo), devid, 256, None
                )

                if result:
                    instance_id = devid.value
                    print(f"检查设备: {instance_id}")

                    if "BTHENUM\\" in instance_id and addr_hex in instance_id:
                        setupapi.SetupDiDestroyDeviceInfoList(hdevinfo)
                        print(f"找到匹配设备: {instance_id}")
                        return 0, "ok", instance_id

                index += 1

            setupapi.SetupDiDestroyDeviceInfoList(hdevinfo)
            print("未找到匹配的蓝牙设备")
            return -2, "未找到匹配的蓝牙设备", ""
            
        except Exception as e:
            error_msg = f"枚举设备失败: {e}"
            print(error_msg)
            return -4, error_msg, ""

    async def _process_single_device(self, device: DeviceInformation) -> Optional[Dict[str, Any]]:
        """处理单个经典蓝牙设备
        
        Args:
            device: 设备信息对象
            
        Returns:
            Optional[Dict]: 处理结果，失败返回None
        """
        btc_device = None
        try:
            btc_device = await BluetoothDevice.from_id_async(device.id)
            if not btc_device:
                print(f"无法创建设备实例: {device.id}")
                return None

            device_info = self._get_device_basic_info(device, btc_device)
            
            # 获取电量
            if device_info["connected"]:
                # 获取设备实例ID
                status, msg, instance_id = self.enumerate_bluetooth_system_device(device_info["address"])
                if status == 0:
                    # 获取电量
                    status_code, msg, battery = self.get_classic_battery_level(instance_id)
                    device_info["battery"] = battery if status_code == 0 else 0
                else:
                    device_info["battery"] = 0
                    msg = "未找到系统设备"
            else:
                device_info["battery"] = 0
                status, msg = 0, "ok"

            return {"code": status, "msg": msg, "data": device_info}

        except Exception as e:
            print(f"处理设备失败: {device.id}, 错误: {str(e)}")
            return {
                "code": -1,
                "msg": str(e),
                "data": {
                    "id": device.id,
                    "name": device.name,
                    "type": "BTC",
                    "connected": False,
                    "battery": 0
                }
            }
        finally:
            if btc_device:
                try:
                    btc_device.close()
                except Exception as e:
                    print(f"关闭设备失败: {e}")

    async def scan_btc_devices(self) -> List[Dict[str, Any]]:
        """扫描经典蓝牙设备
        
        Returns:
            List[Dict]: 经典蓝牙设备信息列表
        """
        devices_info = []
        
        try:
            print("开始扫描经典蓝牙设备...")
            btc_selector = BluetoothDevice.get_device_selector()
            btc_devices = await DeviceInformation.find_all_async_aqs_filter(btc_selector)

            if not btc_devices:
                print("未发现经典蓝牙设备")
                return devices_info

            print(f"发现 {len(btc_devices)} 个候选设备")

            for device in btc_devices:
                result = await self._process_single_device(device)
                if result:
                    devices_info.append(result)
                    print(f"设备处理完成: {device.name} -> code={result['code']}")

            print(f"扫描完成，成功处理 {len(devices_info)} 个设备")

        except Exception as e:
            print(f"扫描经典蓝牙设备失败: {str(e)}")

        return devices_info

    async def scan_single_device(self, address: Union[str, int]) -> Optional[Dict[str, Any]]:
        """扫描单个经典蓝牙设备
        
        Args:
            address: 设备蓝牙地址，支持字符串(如"E0:51:7F:67:A3:88")或整数
            
        Returns:
            Optional[Dict]: 设备信息，失败返回None
        """
        try:
            # 地址格式转换
            if isinstance(address, str):
                if ":" in address:
                    address = address.replace(":", "")
                address = int(address, 16)
            elif not isinstance(address, int):
                print(f"地址格式错误: {type(address)}")
                return None

            print(f"BTC扫描指定设备: {hex(address)}")
            
            btc_selector = BluetoothDevice.get_device_selector()
            btc_devices = await DeviceInformation.find_all_async_aqs_filter(btc_selector)

            for device in btc_devices:
                btc_device = None
                try:
                    btc_device = await BluetoothDevice.from_id_async(device.id)
                    if not btc_device:
                        continue

                    if btc_device.bluetooth_address == address:
                        device_info = self._get_device_basic_info(device, btc_device)
                        
                        # 获取电量
                        if device_info["connected"]:
                            # 获取设备实例ID
                            status, msg, instance_id = self.enumerate_bluetooth_system_device(address)
                            if status == 0:
                                # 获取电量
                                status_code, msg, battery = self.get_classic_battery_level(instance_id)
                                device_info["battery"] = battery if status_code == 0 else 0
                            else:
                                device_info["battery"] = 0
                                msg = "未找到系统设备"
                        else:
                            device_info["battery"] = 0
                            msg = "ok"

                        print(f"找到目标设备: {device.name}")
                        return {"code": 0, "msg": msg, "data": device_info}
                        
                except Exception as e:
                    print(f"检查设备失败: {device.id}, {str(e)}")
                    continue
                finally:
                    if btc_device:
                        try:
                            btc_device.close()
                        except Exception:
                            pass

            print(f"未找到指定设备: {hex(address)}")
            return None
            
        except Exception as e:
            print(f"扫描单个设备失败: {str(e)}")
            return None

    def clear_cache(self) -> None:
        """清除所有缓存"""
        self._cached_battery.clear()
        print("电量缓存已清除")

    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存状态信息
        
        Returns:
            Dict: 缓存统计信息
        """
        return {
            "size": len(self._cached_battery),
            "max_size": self._max_cache_size,
            "devices": list(self._cached_battery.keys())
        }


async def main():
    """主函数"""
    btc = Bluetooth()
    all_devices = await btc.scan_btc_devices()
    print(f"扫描到 {len(all_devices)} 个经典蓝牙设备:")
    print(all_devices)
    for device in all_devices:
        print(f"  - {device['data']['name']}: {device['data']['battery']}% ({device['msg']})")


if __name__ == "__main__":
    asyncio.run(main())