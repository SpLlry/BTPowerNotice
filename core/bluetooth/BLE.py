from winrt.windows.devices.bluetooth import BluetoothDevice, BluetoothLEDevice, BluetoothConnectionStatus
from winrt.windows.devices.enumeration import DeviceInformation
from winrt.windows.storage.streams import DataReader
import asyncio
from collections import OrderedDict
from typing import List, Dict, Tuple, Union, Optional, Any


class Bluetooth:
    """蓝牙设备管理类
    
    负责扫描BLE设备、获取设备信息和管理电量缓存
    """
    
    # GATT标准UUID定义
    BATTERY_SERVICE_UUID = "0000180F-0000-1000-8000-00805F9B34FB"
    BATTERY_LEVEL_UUID = "00002A19-0000-1000-8000-00805F9B34FB"

    def __init__(self):
        """初始化蓝牙管理器"""
        self._cached_devices: OrderedDict[str, int] = OrderedDict()
        self._max_cache_size: int = 20

    def _update_cache(self, device_id: str, battery: int) -> None:
        """更新缓存（移动到最新位置）
        
        Args:
            device_id: 设备ID
            battery: 电量值
        """
        if device_id in self._cached_devices:
            self._cached_devices.move_to_end(device_id)
        self._cached_devices[device_id] = battery
        self._cleanup_cache()

    def _cleanup_cache(self) -> None:
        """LRU缓存清理：移除最旧的项直到缓存大小合适"""
        while len(self._cached_devices) > self._max_cache_size:
            self._cached_devices.popitem(last=False)

    def _is_device_connected(self, ble_device: BluetoothLEDevice) -> bool:
        """检查设备连接状态
        
        Args:
            ble_device: BLE设备实例
            
        Returns:
            bool: 是否已连接
        """
        try:
            return ble_device.connection_status == BluetoothConnectionStatus.CONNECTED
        except Exception as e:
            print(f"检查连接状态失败: {e}")
            return False

    async def _get_device_basic_info(self, device: DeviceInformation, ble_device: BluetoothLEDevice) -> Dict[str, Any]:
        """构建设备基本信息
        
        Args:
            device: 设备信息对象
            ble_device: BLE设备对象
            
        Returns:
            dict: 设备基本信息字典
        """
        return {
            "id": device.id,
            "name": device.name,
            "type": "BLE",
            "address": ble_device.bluetooth_address,
            "connected": self._is_device_connected(ble_device)
        }

    async def get_ble_battery_level(self, ble_device: BluetoothLEDevice) -> Tuple[int, str, int]:
        """获取BLE设备的电量水平
        
        Args:
            ble_device: BLE设备实例
            
        Returns:
            Tuple[int, str, int]: (状态码, 消息, 电量值)
                状态码: 0成功, -1未找到服务, -2未找到特征值, -3读取失败
        """
        battery_level = -1

        try:
            services = await ble_device.get_gatt_services_async()
            if not services or not services.services:
                print("无法获取GATT服务列表")
                return -1, "无法获取GATT服务", battery_level

            battery_service = None
            for service in services.services:
                if str(service.uuid).lower() == self.BATTERY_SERVICE_UUID.lower():
                    battery_service = service
                    break

            if not battery_service:
                print("未找到电池服务")
                return -1, "未找到电池服务", battery_level

            characteristics = await battery_service.get_characteristics_async()
            if not characteristics or not characteristics.characteristics:
                print("无法获取特征值列表")
                return -2, "无法获取特征值", battery_level

            battery_level_char = None
            for char in characteristics.characteristics:
                if str(char.uuid).lower() == self.BATTERY_LEVEL_UUID.lower():
                    battery_level_char = char
                    break

            if not battery_level_char:
                print("未找到电池电量特征值")
                return -2, "未找到电池电量特征值", battery_level

            value = await battery_level_char.read_value_async()
            if not value or not value.value:
                print("读取电量值失败：值为空")
                return -3, "读取电量值失败", battery_level

            reader = DataReader.from_buffer(value.value)
            battery_level = reader.read_byte()
            
            # 确保读取成功
            if battery_level < 0 or battery_level > 100:
                print(f"电量值异常: {battery_level}")
                battery_level = max(0, min(100, battery_level))

            return 0, "ok", battery_level

        except Exception as e:
            error_msg = f"获取电量失败: {str(e)}"
            print(error_msg)
            return -3, error_msg, battery_level

    async def _get_battery_with_cache(self, device_id: str, ble_device: BluetoothLEDevice) -> Tuple[int, str, int]:
        """带缓存的电量获取
        
        Args:
            device_id: 设备ID
            ble_device: BLE设备对象
            
        Returns:
            Tuple[int, str, int]: (状态码, 消息, 电量值)
        """
        if device_id in self._cached_devices:
            print(f"使用缓存电量: {device_id}")
            return 0, "已缓存电量", self._cached_devices[device_id]

        status, msg, battery = await self.get_ble_battery_level(ble_device)
        if status == 0:
            self._update_cache(device_id, battery)
            print(f"更新电量缓存: {device_id} -> {battery}%")

        return status, msg, battery

    async def _process_single_device(self, device: DeviceInformation) -> Optional[Dict[str, Any]]:
        """处理单个设备的完整信息获取
        
        Args:
            device: 设备信息对象
            
        Returns:
            Optional[Dict]: 处理结果，失败返回None
        """
        ble_device = None
        try:
            ble_device = await BluetoothLEDevice.from_id_async(device.id)
            if not ble_device:
                print(f"无法创建设备实例: {device.id}")
                return None

            device_info = await self._get_device_basic_info(device, ble_device)
            
            # 获取电量（带缓存）
            if device_info["connected"]:
                status, msg, battery = await self._get_battery_with_cache(device.id, ble_device)
                device_info["battery"] = battery
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
                    "type": "BLE",
                    "connected": False,
                    "battery": 0
                }
            }
        finally:
            if ble_device:
                try:
                    ble_device.close()
                except Exception as e:
                    print(f"关闭设备失败: {e}")

    async def scan_ble_devices(self) -> List[Dict[str, Any]]:
        """扫描所有BLE设备
        
        Returns:
            List[Dict]: BLE设备信息列表
        """
        devices_info = []
        
        try:
            print("开始扫描BLE设备...")
            ble_selector = BluetoothLEDevice.get_device_selector()
            ble_devices = await DeviceInformation.find_all_async_aqs_filter(ble_selector)

            if not ble_devices:
                print("未发现BLE设备")
                return devices_info

            print(f"发现 {len(ble_devices)} 个候选设备")

            for device in ble_devices:
                result = await self._process_single_device(device)
                if result:
                    devices_info.append(result)
                    print(f"设备处理完成: {device.name} -> code={result['code']}")

            print(f"扫描完成，成功处理 {len(devices_info)} 个设备")

        except Exception as e:
            print(f"扫描BLE设备失败: {str(e)}")

        return devices_info

    async def scan_single_device(self, address: Union[str, int]) -> Optional[Dict[str, Any]]:
        """扫描单个BLE设备
        
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

            print(f"BLE扫描指定设备: {hex(address)}")
            
            ble_selector = BluetoothLEDevice.get_device_selector()
            ble_devices = await DeviceInformation.find_all_async_aqs_filter(ble_selector)

            for device in ble_devices:
                ble_device = None
                try:
                    ble_device = await BluetoothLEDevice.from_id_async(device.id)
                    if not ble_device:
                        continue

                    if ble_device.bluetooth_address == address:
                        device_info = await self._get_device_basic_info(device, ble_device)
                        
                        # 获取电量（带缓存）
                        if device_info["connected"]:
                            status, msg, battery = await self._get_battery_with_cache(device.id, ble_device)
                            device_info["battery"] = battery
                        else:
                            device_info["battery"] = 0
                            status, msg = 0, "ok"

                        print(f"找到目标设备: {device.name}")
                        return {"code": 0, "msg": msg, "data": device_info}
                        
                except Exception as e:
                    print(f"检查设备失败: {device.id}, {str(e)}")
                    continue
                finally:
                    if ble_device:
                        try:
                            ble_device.close()
                        except Exception:
                            pass

            print(f"未找到指定设备: {hex(address)}")
            return None
            
        except Exception as e:
            print(f"扫描单个设备失败: {str(e)}")
            return None

    def clear_cache(self) -> None:
        """清除所有缓存"""
        self._cached_devices.clear()
        print("电量缓存已清除")

    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存状态信息
        
        Returns:
            Dict: 缓存统计信息
        """
        return {
            "size": len(self._cached_devices),
            "max_size": self._max_cache_size,
            "devices": list(self._cached_devices.keys())
        }


async def main():
    """主函数"""
    bluetooth = Bluetooth()
    
    # 扫描所有设备
    all_devices = await bluetooth.scan_ble_devices()
    print(f"扫描到 {len(all_devices)} 个设备:")
    for device in all_devices:
        print(f"  - {device['data']['name']}: {device['data']['battery']}% ({device['msg']})")


if __name__ == "__main__":
    asyncio.run(main())