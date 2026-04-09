from . import BLE, BTC
import asyncio
import time
import concurrent.futures
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot, QObject

from utils.tools import log


class BtScanManager(QObject):
    """蓝牙扫描管理器，使用线程池管理扫描任务"""
    scan_finished = pyqtSignal(dict)
    
    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self.ble_scanner = None
        self.btc_scanner = None
        self.thread_pool = None
        self.is_running = False
        
        # 动态扫描间隔相关
        self.base_scan_interval = 2000  # 基础扫描间隔（毫秒）
        self.min_scan_interval = 1000  # 最小扫描间隔（毫秒）
        self.max_scan_interval = 10000  # 最大扫描间隔（毫秒）
        self.last_scan_time = 0  # 上次扫描时间
        self.connected_devices_count = 0  # 已连接设备数量
        self.full_scan_interval = 30000  # 全量扫描间隔（毫秒）
        self.last_full_scan_time = 0  # 上次全量扫描时间
        
        # 设备状态缓存
        self.connected_devices = set()  # 已连接设备地址集合
        self.last_device_states = {}  # 上次扫描的设备状态
        self.device_cache = {}  # 设备信息缓存
        
        # 线程状态监控
        self.current_task = None
        self.task_count = 0
        self.error_count = 0
        
        # 初始化线程池
        self._init_thread_pool()
    
    def _init_thread_pool(self):
        """初始化线程池"""
        try:
            # 创建线程池，最多2个线程
            self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
            log.info("线程池初始化成功")
        except Exception as e:
            log.error(f"线程池初始化失败: {e}")
            self.thread_pool = None
    
    def start(self):
        """启动扫描管理器"""
        self.is_running = True
        log.info("蓝牙扫描管理器已启动")
    
    def stop(self):
        """停止扫描管理器"""
        self.is_running = False
        
        # 取消当前任务
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
        
        # 关闭线程池
        if self.thread_pool:
            self.thread_pool.shutdown(wait=True)
            log.info("线程池已关闭")
    
    def get_scan_interval(self):
        """根据设备状态获取扫描间隔"""
        if self.connected_devices_count == 0:
            # 无设备连接，使用最大间隔
            return self.max_scan_interval
        elif self.connected_devices_count <= 2:
            # 1-2个设备连接，使用基础间隔
            return self.base_scan_interval
        else:
            # 3个以上设备连接，使用最小间隔
            return self.min_scan_interval
    
    def perform_scan(self):
        """执行扫描操作"""
        if not self.is_running or not self.thread_pool:
            return
        
        # 检查是否需要扫描
        current_time = time.time() * 1000  # 转换为毫秒
        if current_time - self.last_scan_time < self.get_scan_interval():
            return
        
        # 提交扫描任务到线程池
        self.task_count += 1
        self.current_task = self.thread_pool.submit(self._scan_task)
        self.current_task.add_done_callback(self._scan_task_done)
    
    def _scan_task(self):
        """扫描任务"""
        try:
            # 创建事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 执行异步扫描
            result = loop.run_until_complete(self.async_scan_devices())
            
            # 关闭事件循环
            loop.close()
            
            return result
        except Exception as e:
            log.error(f"扫描任务执行失败: {e}")
            self.error_count += 1
            return {}
    
    def _scan_task_done(self, future):
        """扫描任务完成回调"""
        try:
            result = future.result()
            self.scan_finished.emit(result)
        except Exception as e:
            log.error(f"扫描任务回调失败: {e}")
            self.error_count += 1
            self.scan_finished.emit({})
    
    def int_to_mac(self, mac_int):
        try:
            # 转16进制 → 补零 → 大写 → 加冒号
            hex_str = f"{mac_int:012X}"
            mac = ":".join([hex_str[i:i+2] for i in range(0, 12, 2)])
            return mac
        except:
            return f"未知MAC:{mac_int}"
    
    async def async_scan_devices(self):
        """真正的异步蓝牙扫描（支持 await）"""
        try:
            if self.ble_scanner is None:
                self.ble_scanner = BLE.Bluetooth()
            if self.btc_scanner is None:
                self.btc_scanner = BTC.Bluetooth()

            current_time = time.time() * 1000  # 转换为毫秒
            is_full_scan = current_time - self.last_full_scan_time >= self.full_scan_interval

            if is_full_scan:
                # 执行全量扫描
                ble_devices = await self.ble_scanner.scan_ble_devices()
                btc_devices = await self.btc_scanner.scan_btc_devices()
                self.last_full_scan_time = current_time
            else:
                # 执行增量扫描，只扫描已连接的设备
                ble_devices = []
                btc_devices = []
                
                for address in self.connected_devices:
                    # 扫描单个BLE设备
                    ble_result = await self.ble_scanner.scan_single_device(address)
                    if ble_result:
                        ble_devices.append(ble_result)
                    
                    # 扫描单个BTC设备
                    btc_result = await self.btc_scanner.scan_single_device(address)
                    if btc_result:
                        btc_devices.append(btc_result)

            devices = ble_devices + btc_devices
            log.info(f"扫描到 {len(devices)} 个设备")
            log.info(devices)

            ret = {}
            current_connected_devices = set()
            
            for device in devices:
                if device["code"] != 0:
                    continue
                
                device["data"]["address"] = self.int_to_mac(
                    device["data"]["address"])
                address = device["data"]["address"]
                
                # 检查设备状态是否变化
                if address in self.last_device_states:
                    last_state = self.last_device_states[address]
                    current_state = device["data"]
                    
                    # 只在状态变化时更新
                    if last_state.get("connected") != current_state.get("connected") or \
                       (current_state.get("connected") and last_state.get("battery") != current_state.get("battery")):
                        ret[address] = current_state
                        self.last_device_states[address] = current_state
                        self.device_cache[address] = current_state
                else:
                    # 新设备，直接添加
                    ret[address] = device["data"]
                    self.last_device_states[address] = device["data"]
                    self.device_cache[address] = device["data"]
                
                # 记录已连接设备
                if device["data"].get("connected"):
                    current_connected_devices.add(address)

            # 更新已连接设备集合
            self.connected_devices = current_connected_devices
            self.connected_devices_count = len(current_connected_devices)
            
            # 更新上次扫描时间
            self.last_scan_time = time.time() * 1000

            # 如果没有新数据，使用缓存数据
            if not ret and self.device_cache:
                ret = self.device_cache.copy()

            return ret
        except Exception as e:
            log.error(f"蓝牙扫描异常: {e}")
            self.error_count += 1
            return {}
    
    def get_status(self):
        """获取线程状态"""
        return {
            "is_running": self.is_running,
            "task_count": self.task_count,
            "error_count": self.error_count,
            "connected_devices_count": self.connected_devices_count,
            "last_scan_time": self.last_scan_time,
            "thread_pool_size": 2
        }


class BtScanThread(QThread):
    """兼容旧代码的扫描线程"""
    scan_finished = pyqtSignal(dict)
    start_scan = pyqtSignal()  # 新增信号，用于触发扫描

    def __init__(self, config=None):
        super().__init__()
        self.scan_manager = BtScanManager(config)
        self.scan_manager.scan_finished.connect(self.scan_finished)
        
        # 连接信号
        self.start_scan.connect(self._perform_scan)

    def run(self):
        """启动扫描管理器"""
        self.scan_manager.start()
        
        # 保持线程运行
        while self.isRunning():
            time.sleep(0.1)

    def _perform_scan(self):
        """执行扫描操作"""
        self.scan_manager.perform_scan()

    def stop(self):
        """停止线程"""
        self.scan_manager.stop()
        self.quit()
        self.wait()
    
    def get_status(self):
        """获取线程状态"""
        return self.scan_manager.get_status()
