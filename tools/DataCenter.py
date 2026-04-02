from typing import Any, Callable, Dict, List, Optional, Union
import threading
import time
from datetime import datetime, timedelta


class DataCenter:
    _instance: Optional['DataCenter'] = None
    _lock_init = threading.Lock()

    def __new__(cls) -> 'DataCenter':
        with cls._lock_init:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._store: Dict[str, Any] = {}
                cls._instance._lock_data = threading.Lock()
                # { key: [callback1, callback2] }
                cls._instance._subscribers: Dict[str, List[Callable[[Any], None]]] = {}
                # { key: expiration_time }
                cls._instance._expiration: Dict[str, float] = {}
            return cls._instance

    # 订阅数据变化
    def subscribe(self, key: str, callback: Callable[[Any], None]) -> None:
        """订阅指定键的数据变化
        
        Args:
            key: 数据键名
            callback: 数据变化时的回调函数
        """
        with self._lock_data:
            if key not in self._subscribers:
                self._subscribers[key] = []
            if callback not in self._subscribers[key]:
                self._subscribers[key].append(callback)

    # 取消订阅
    def unsubscribe(self, key: str, callback: Callable[[Any], None]) -> None:
        """取消订阅指定键的数据变化
        
        Args:
            key: 数据键名
            callback: 要取消的回调函数
        """
        with self._lock_data:
            if key in self._subscribers and callback in self._subscribers[key]:
                self._subscribers[key].remove(callback)
                # 如果没有订阅者了，清理订阅列表
                if not self._subscribers[key]:
                    del self._subscribers[key]

    # 通知所有订阅者
    def _notify(self, key: str, value: Any) -> None:
        """通知指定键的所有订阅者
        
        Args:
            key: 数据键名
            value: 新的数据值
        """
        # 必须复制一份，防止遍历时被修改
        with self._lock_data:
            callbacks = self._subscribers.get(key, [])[:]

        for cb in callbacks:
            try:
                cb(value)
            except Exception as e:
                # 记录错误但不中断通知
                print(f"DataCenter: 回调执行错误 for key '{key}': {e}")

    # 写入数据 → 自动通知
    def set(self, key: str, value: Any, expire_seconds: Optional[int] = None) -> None:
        """设置数据并自动通知订阅者
        
        Args:
            key: 数据键名
            value: 数据值
            expire_seconds: 数据过期时间（秒），None表示永不过期
        """
        with self._lock_data:
            self._store[key] = value
            # 设置过期时间
            if expire_seconds is not None:
                self._expiration[key] = time.time() + expire_seconds
            elif key in self._expiration:
                del self._expiration[key]
        self._notify(key, value)

    # 读取数据
    def get(self, key: str, default: Any = None) -> Any:
        """获取数据
        
        Args:
            key: 数据键名
            default: 键不存在时的默认值
            
        Returns:
            数据值或默认值
        """
        with self._lock_data:
            # 检查数据是否过期
            if key in self._expiration and time.time() > self._expiration[key]:
                del self._store[key]
                del self._expiration[key]
                return default
            return self._store.get(key, default)

    # 批量获取数据
    def get_multi(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取多个键的数据
        
        Args:
            keys: 键名列表
            
        Returns:
            键值对字典
        """
        result = {}
        with self._lock_data:
            for key in keys:
                # 检查数据是否过期
                if key in self._expiration and time.time() > self._expiration[key]:
                    del self._store[key]
                    del self._expiration[key]
                else:
                    result[key] = self._store.get(key)
        return result

    # 批量设置数据
    def set_multi(self, data: Dict[str, Any], expire_seconds: Optional[int] = None) -> None:
        """批量设置多个键的数据
        
        Args:
            data: 键值对字典
            expire_seconds: 数据过期时间（秒），None表示永不过期
        """
        with self._lock_data:
            for key, value in data.items():
                self._store[key] = value
                # 设置过期时间
                if expire_seconds is not None:
                    self._expiration[key] = time.time() + expire_seconds
                elif key in self._expiration:
                    del self._expiration[key]
                # 通知订阅者
                self._notify(key, value)

    # 删除数据
    def delete(self, key: str) -> bool:
        """删除指定键的数据
        
        Args:
            key: 数据键名
            
        Returns:
            是否成功删除
        """
        with self._lock_data:
            if key in self._store:
                del self._store[key]
                if key in self._expiration:
                    del self._expiration[key]
                return True
            return False

    # 清空
    def clear(self) -> None:
        """清空所有数据"""
        with self._lock_data:
            self._store.clear()
            self._expiration.clear()

    # 获取所有键
    def keys(self) -> List[str]:
        """获取所有键名
        
        Returns:
            键名列表
        """
        with self._lock_data:
            # 先清理过期数据
            expired_keys = [key for key, exp_time in self._expiration.items() if time.time() > exp_time]
            for key in expired_keys:
                del self._store[key]
                del self._expiration[key]
            return list(self._store.keys())

    # 检查键是否存在
    def exists(self, key: str) -> bool:
        """检查键是否存在
        
        Args:
            key: 数据键名
            
        Returns:
            是否存在
        """
        with self._lock_data:
            # 检查数据是否过期
            if key in self._expiration and time.time() > self._expiration[key]:
                del self._store[key]
                del self._expiration[key]
                return False
            return key in self._store
