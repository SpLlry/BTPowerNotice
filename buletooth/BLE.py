from winrt.windows.devices.bluetooth import BluetoothDevice, BluetoothLEDevice, BluetoothConnectionStatus
from winrt.windows.devices.enumeration import DeviceInformation
from winrt.windows.storage.streams import DataReader
import asyncio


class Bluetooth:
    def __init__(self):

        pass

    async def scan_ble_devices(self):
        """
        扫描 BLE 设备

        Returns:
            list: BLE 设备信息列表
        """
        devices_info = []
        ble_selector = BluetoothLEDevice.get_device_selector()
        ble_devices = await DeviceInformation.find_all_async_aqs_filter(ble_selector)

        for device in ble_devices:
            device_info = {
                "id": device.id,
                "name": device.name,
                "type": "BLE"
            }

            # 获取设备实例
            ble_device = await BluetoothLEDevice.from_id_async(device.id)
            if ble_device:
                # 获取连接状态
                status = ble_device.connection_status
                is_connected = status == BluetoothConnectionStatus.CONNECTED
                device_info["connected"] = is_connected
                device_info["address"] = ble_device.bluetooth_address
                device_info["battery"] = await self.get_ble_battery_level(ble_device)

            devices_info.append(device_info)

        return devices_info

    async def get_ble_battery_level(self, ble_device):
        """获取 BLE 设备的电量水平"""
        try:
            # 直接使用字符串表示 UUID，避免导入 Guid
            battery_service_uuid = "0000180F-0000-1000-8000-00805F9B34FB"
            battery_level_uuid = "00002A19-0000-1000-8000-00805F9B34FB"

            # 获取设备服务
            services = await ble_device.get_gatt_services_async()
            battery_service = None

            # 查找电池服务
            for service in services.services:

                if str(service.uuid) == battery_service_uuid.lower():
                    battery_service = service
                    break
            if not battery_service:
                # return "设备不支持电池服务"
                return -1
            # 获取电池电量特征
            characteristics = await battery_service.get_characteristics_async()
            battery_level_char = None

            for char in characteristics.characteristics:
                if str(char.uuid) == battery_level_uuid.lower():
                    battery_level_char = char
                    break

            if not battery_level_char:
                # return "设备不支持电池电量特征"
                return -2

            # 读取电量值
            value = await battery_level_char.read_value_async()
            reader = DataReader.from_buffer(value.value)
            battery_level = reader.read_byte()

            return battery_level

        except Exception as e:
            return f"获取电量失败: {e}"


async def main():
    """主函数"""
    bluetooth = Bluetooth()

    # 扫描所有设备
    all_devices = await bluetooth.scan_ble_devices()
    print(all_devices)
    # 打印设备信息
    # bluetooth.print_devices_info(all_devices)


if __name__ == "__main__":
    asyncio.run(main())
