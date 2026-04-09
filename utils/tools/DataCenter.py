from typing import Any, Callable, Dict, List, Optional
import threading
import time

class DataCenter:
    _instance: Optional['DataCenter'] = None
    _lock_init = threading.Lock()

    def __new__(cls) -> 'DataCenter':
        with cls._lock_init:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                # 核心存储
                cls._instance._store: Dict[str, Any] = {}
                cls._instance._expiration: Dict[str, float] = {}
                # 线程锁
                cls._instance._lock_data = threading.Lock()
                # 订阅者：强引用（PyQt项目专用，稳定不失效）
                cls._instance._subscribers: Dict[str, List[Callable]] = {}
                # 后台清理线程
                cls._instance._start_cleanup_thread()
            return cls._instance

    def _start_cleanup_thread(self):
        """后台定时清理过期数据"""
        def cleanup_loop():
            while True:
                time.sleep(10)
                self._cleanup_expired()
        thread = threading.Thread(target=cleanup_loop, daemon=True)
        thread.start()

    def _cleanup_expired(self):
        """清理过期数据"""
        with self._lock_data:
            now = time.time()
            expired = [k for k, t in self._expiration.items() if now > t]
            for k in expired:
                self._store.pop(k, None)
                self._expiration.pop(k, None)

    # ==================== 订阅系统（修复版，100%可用） ====================
    def subscribe(self, key: str, callback: Callable[[Any], None]) -> None:
        """订阅数据变化（稳定可用）"""
        if not callable(callback):
            return
        with self._lock_data:
            if key not in self._subscribers:
                self._subscribers[key] = []
            if callback not in self._subscribers[key]:
                self._subscribers[key].append(callback)

    def unsubscribe(self, key: str, callback: Callable[[Any], None]) -> None:
        """取消订阅（组件销毁时必须调用，防内存泄漏）"""
        with self._lock_data:
            if key in self._subscribers and callback in self._subscribers[key]:
                self._subscribers[key].remove(callback)
                if not self._subscribers[key]:
                    del self._subscribers[key]

    def unsubscribe_all(self, key: Optional[str] = None) -> None:
        """批量取消订阅"""
        with self._lock_data:
            if key:
                self._subscribers.pop(key, None)
            else:
                self._subscribers.clear()

    def _notify(self, key: str, value: Any) -> None:
        """通知订阅者（无失效问题）"""
        with self._lock_data:
            callbacks = self._subscribers.get(key, [])[:]
        
        for cb in callbacks:
            try:
                cb(value)
            except Exception as e:
                print(f"[DataCenter] 回调异常 {key}: {e}")

    # ==================== 数据操作（无改动，兼容原有代码） ====================
    def set(self, key: str, value: Any, expire_seconds: Optional[int] = None) -> None:
        with self._lock_data:
            self._store[key] = value
            if expire_seconds:
                self._expiration[key] = time.time() + expire_seconds
            else:
                self._expiration.pop(key, None)
        self._notify(key, value)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock_data:
            now = time.time()
            if key in self._expiration and now > self._expiration[key]:
                self._store.pop(key, None)
                self._expiration.pop(key, None)
                return default
            return self._store.get(key, default)

    def set_multi(self, data: Dict[str, Any], expire_seconds: Optional[int] = None) -> None:
        with self._lock_data:
            for k, v in data.items():
                self._store[k] = v
                if expire_seconds:
                    self._expiration[k] = time.time() + expire_seconds
                else:
                    self._expiration.pop(k, None)
                self._notify(k, v)

    def get_multi(self, keys: List[str]) -> Dict[str, Any]:
        res = {}
        with self._lock_data:
            now = time.time()
            for k in keys:
                if k in self._expiration and now > self._expiration[k]:
                    self._store.pop(k, None)
                    self._expiration.pop(k, None)
                else:
                    res[k] = self._store.get(k)
        return res

    def delete(self, key: str) -> bool:
        with self._lock_data:
            if key in self._store:
                self._store.pop(key)
                self._expiration.pop(key, None)
                return True
            return False

    def clear(self) -> None:
        with self._lock_data:
            self._store.clear()
            self._expiration.clear()

    def keys(self) -> List[str]:
        with self._lock_data:
            self._cleanup_expired()
            return list(self._store.keys())

    def exists(self, key: str) -> bool:
        with self._lock_data:
            now = time.time()
            if key in self._expiration and now > self._expiration[key]:
                self._store.pop(key, None)
                self._expiration.pop(key, None)
                return False
            return key in self._store