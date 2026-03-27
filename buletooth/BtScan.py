import buletooth.BLE
import buletooth.BTC
import asyncio
from PyQt6.QtCore import QThread, pyqtSignal

from tools import log


class BtScanThread(QThread):
    scan_finished = pyqtSignal(dict)

    def __init__(self, config=None):
        super().__init__()
        self.ble_scanner = None
        self.btc_scanner = None
        self.config = config

    def run(self):
        """在线程内创建 asyncio 循环，安全 await 异步蓝牙方法"""
        loop = asyncio.new_event_loop()

        asyncio.set_event_loop(loop)

        result = loop.run_until_complete(self.async_scan_devices())
        self.scan_finished.emit(result)
        loop.close()

    async def async_scan_devices(self):
        """真正的异步蓝牙扫描（支持 await）"""
        # try:
        if self.ble_scanner is None:
            self.ble_scanner = buletooth.BLE.Bluetooth()
        if self.btc_scanner is None:
            self.btc_scanner = buletooth.BTC.Bluetooth()

        ble_devices = await self.ble_scanner.scan_ble_devices()
        btc_devices = await self.btc_scanner.scan_btc_devices()

        devices = ble_devices + btc_devices
        # print(ble_devices)
        # print(btc_devices)
        log.info(devices)
        # ret = {device["address"]: device["data"] for device in devices}
        ret = {}
        for device in devices:
            if self.config.getVal("Debug", "debug") == 1:
                log.info(device)
            if device["code"] != 0:
                continue
            ret[device["data"]["address"]] = device["data"]

            # print(ret)
            # return {
            #     "123": {"name": "耳机", "battery": 100, "connected": True},
            #     "456": {
            #         "name": "键盘",
            #         "battery": random.randint(0, 100),
            #         "connected": True,
            #     },
            #     "789": {"name": "鼠标", "battery": 20, "connected": False},
            # }
        return ret

        # except Exception as e:
        #     print(f"蓝牙扫描异常: {e}")
        #     return {}
