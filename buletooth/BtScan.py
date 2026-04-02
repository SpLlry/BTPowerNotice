import buletooth.BLE
import buletooth.BTC
import asyncio
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot

from tools import log


class BtScanThread(QThread):
    scan_finished = pyqtSignal(dict)
    start_scan = pyqtSignal()  # 新增信号，用于触发扫描

    def __init__(self, config=None):
        super().__init__()
        self.ble_scanner = None
        self.btc_scanner = None
        self.config = config
        self.loop = None
        self.is_running = False
        
        # 连接信号
        self.start_scan.connect(self._perform_scan)

    def run(self):
        """在线程内创建 asyncio 循环，安全 await 异步蓝牙方法"""
        self.is_running = True
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # 保持线程运行，等待扫描信号
        self.loop.run_forever()
        
        # 清理资源
        self.loop.close()
        self.is_running = False

    def int_to_mac(self, mac_int):
        try:
            # 转16进制 → 补零 → 大写 → 加冒号
            hex_str = f"{mac_int:012X}"
            mac = ":".join([hex_str[i:i+2] for i in range(0, 12, 2)])
            return mac
        except:
            return f"未知MAC:{mac_int}"

    @pyqtSlot()
    def _perform_scan(self):
        """执行扫描操作"""
        if not self.is_running or not self.loop:
            return
        
        # 在事件循环中执行扫描
        asyncio.run_coroutine_threadsafe(self.async_scan_devices(), self.loop)

    async def async_scan_devices(self):
        """真正的异步蓝牙扫描（支持 await）"""
        try:
            if self.ble_scanner is None:
                self.ble_scanner = buletooth.BLE.Bluetooth()
            if self.btc_scanner is None:
                self.btc_scanner = buletooth.BTC.Bluetooth()

            ble_devices = await self.ble_scanner.scan_ble_devices()
            btc_devices = await self.btc_scanner.scan_btc_devices()

            devices = ble_devices + btc_devices
            log.info(f"扫描到 {len(devices)} 个设备")
            log.info(devices)

            ret = {}
            for device in devices:
                if device["code"] != 0:
                    continue
                device["data"]["address"] = self.int_to_mac(
                    device["data"]["address"])
                ret[device["data"]["address"]] = device["data"]

            self.scan_finished.emit(ret)
        except Exception as e:
            print(f"蓝牙扫描异常: {e}")
            self.scan_finished.emit({})

    def stop(self):
        """停止线程"""
        if self.is_running and self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.wait()

