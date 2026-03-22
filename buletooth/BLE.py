from winrt.windows.devices.bluetooth import BluetoothDevice, BluetoothLEDevice, BluetoothConnectionStatus
from winrt.windows.devices.enumeration import DeviceInformation
from winrt.windows.storage.streams import DataReader
import asyncio


class Bluetooth:
    def __init__(self):
        self._cached_devices = {}
        self._max_cache_size = 20

    def _cleanup_cache(self, max_size=20):
        if len(self._cached_devices) > max_size:
            keys_to_remove = list(self._cached_devices.keys())[:-max_size]
            for key in keys_to_remove:
                del self._cached_devices[key]

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
            device_id = device.id
            device_info = {
                "id": device_id,
                "name": device.name,
                "type": "BLE"
            }

            ble_device = None
            try:
                ble_device = await BluetoothLEDevice.from_id_async(device_id)
                if ble_device:
                    status = ble_device.connection_status
                    is_connected = status == BluetoothConnectionStatus.CONNECTED
                    device_info["connected"] = is_connected
                    device_info["address"] = ble_device.bluetooth_address

                    if is_connected and device_id in self._cached_devices:
                        device_info["battery"] = self._cached_devices[device_id]
                    else:
                        battery = await self.get_ble_battery_level(ble_device)
                        device_info["battery"] = battery
                        if is_connected:
                            self._cached_devices[device_id] = battery
            finally:
                if ble_device:
                    ble_device.close()

            devices_info.append(device_info)

        self._cleanup_cache(self._max_cache_size)
        return devices_info

    async def get_ble_battery_level(self, ble_device):
        """获取 BLE 设备的电量水平"""
        battery_level = -1
        services = None
        battery_service = None
        characteristics = None
        battery_level_char = None

        try:
            battery_service_uuid = "0000180F-0000-1000-8000-00805F9B34FB"
            battery_level_uuid = "00002A19-0000-1000-8000-00805F9B34FB"

            services = await ble_device.get_gatt_services_async()

            for service in services.services:
                if str(service.uuid) == battery_service_uuid.lower():
                    battery_service = service
                    break

            if not battery_service:
                return -1

            characteristics = await battery_service.get_characteristics_async()

            for char in characteristics.characteristics:
                if str(char.uuid) == battery_level_uuid.lower():
                    battery_level_char = char
                    break

            if not battery_level_char:
                return -2

            value = await battery_level_char.read_value_async()
            reader = DataReader.from_buffer(value.value)
            battery_level = reader.read_byte()

        except Exception as e:
            return -3
        finally:
            if battery_level_char:
                battery_level_char.close()
            if characteristics:
                for char in characteristics.characteristics:
                    char.close()
                characteristics.close()
            if battery_service:
                battery_service.close()
            if services:
                for service in services.services:
                    service.close()
                services.close()

        return battery_level


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
