import uwp_bt_battery
import asyncio
import threading
import time
import configparser
import os
from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem
import tkinter as tk
from tkinter import ttk

# 导入你的蓝牙模块
import buletooth.BLE
import buletooth.BTC
import sys
# ========== 全局异步事件循环 ==========
async_loop = None
async_loop_thread = None


def start_async_loop():
    """在独立线程运行异步事件循环"""
    global async_loop
    async_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(async_loop)
    async_loop.run_forever()


class DeviceInfoWindow:
    """设备信息展示窗口类"""

    def __init__(self, parent, device_data):
        self.window = tk.Toplevel(parent)
        self.device_data = device_data
        self.setup_window()
        self.create_ui()

    def setup_window(self):
        """窗口基础设置"""
        # 安全获取设备名（增加异常处理）
        device_name = "未知设备"
        try:
            device_name = self.device_data.get('name', '未知设备')
        except:
            pass

        self.window.title(f"设备信息 - {device_name}")
        self.window.geometry("400x500")  # 适配布局的尺寸
     
        self.window.resizable(False, False)
        self.window.attributes('-topmost', True)

        # 居中显示
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - self.window.winfo_width()) // 2
        y = (self.window.winfo_screenheight() - self.window.winfo_height()) // 2
        self.window.geometry(f"+{x}+{y}")

    def create_ui(self):
        """创建界面元素，还原参考样式"""
        # 主容器（带边框）
        main_frame = ttk.Frame(self.window, relief="solid", borderwidth=1)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 内容框架
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # ========== 设备名 + 电量圆形区域 ==========
        top_frame = ttk.Frame(content_frame)
        top_frame.pack(fill=tk.X, pady=(0, 15))

        # 设备名标签
        device_name_label = ttk.Label(
            top_frame,
            text="设备名",
            font=("微软雅黑", 12)
        )
        device_name_label.pack(side=tk.LEFT, padx=(0, 20))

        # 电量圆形显示（增加异常处理）
        battery_value = "?"
        try:
            battery_value = self.device_data.get('battery', '?')
        except:
            pass

        battery_canvas = tk.Canvas(
            top_frame, width=60, height=60, highlightthickness=0)
        battery_canvas.pack(side=tk.RIGHT)

        # 绘制圆形和电量文字
        battery_canvas.create_oval(5, 5, 55, 55, outline="black", width=2)
        battery_canvas.create_text(
            30, 30,
            text=str(battery_value),
            font=("微软雅黑", 14, "bold")
        )

        # ========== MAC地址区域 ==========
        mac_frame = ttk.Frame(content_frame)
        mac_frame.pack(fill=tk.X, pady=(0, 15))

        # MAC地址标签
        mac_label = ttk.Label(
            mac_frame,
            text="MAC地址",
            font=("微软雅黑", 12)
        )
        mac_label.pack(anchor=tk.W)

        # 分割线（模拟参考样式的横线）
        separator = ttk.Frame(content_frame, height=2, relief="solid")
        separator.pack(fill=tk.X, pady=(0, 15))

        # 显示实际的MAC地址（增加异常处理）
        mac_address = "未知"
        try:
            device_id = self.device_data.get('id', '')
            mac_address = self.extract_mac_from_id(device_id)
        except:
            pass

        mac_value_label = ttk.Label(
            content_frame,
            text=mac_address if mac_address else "未知",
            font=("微软雅黑", 10)
        )
        mac_value_label.pack(anchor=tk.W, pady=(5, 0))

    def extract_mac_from_id(self, device_id):
        """从设备ID中提取MAC地址"""
        if not device_id:
            return ""
        # 提取ID中的MAC地址部分（适配BLE和Classic格式）
        parts = device_id.split('-')
        if len(parts) >= 2:
            return parts[-1]
        return device_id


class BTBattery:
    def __init__(self):
        self.config_file = "bluegauge.ini"
        self.config = self.load_config()
        self.devices = []
        self.icon = None
        self.running = True

        # Tkinter 主线程初始化
        self.tk_root = None
        self.about_window = None
        self.device_info_window = None

        # 应用信息
        self.APP_INFO = {
            "name": "BTPowerNotice",
            "version": "0.0.1",
            "author": "SpLlry",
            "github_url": "https://github.com/SpLlry/BTPowerNotice"
        }

    def load_config(self):
        config = configparser.ConfigParser()
        if os.path.exists(self.config_file):
            config.read(self.config_file)
        else:
            config['General'] = {
                'update_interval': '5',
                'icon_style': 'numeric',
                'show_lowest_battery': 'false'
            }
            config['DeviceAliases'] = {}
            with open(self.config_file, 'w') as f:
                config.write(f)
        return config

    def get_tray_icon(self):
        try:
            return Image.open("icon\\icon.ico")
        except:
            return Image.new('RGBA', (32, 32), (0, 0, 0, 0))

    def build_device_menu(self):
        """构建托盘菜单，设备项可点击查看详情"""
        items = []
        for idx, dev in enumerate(self.devices):
            name = dev.get("name", "未知设备")
            bat = dev.get("battery", "?")
            connected = dev.get("connected", False)
            status = "✅" if connected else "❌"
            text = f"{status}{name}|{bat}%"

            # ========== 核心修复：修正pystray菜单回调参数 ==========
            # 使用闭包确保正确传递设备数据，避免Icon对象污染
            def create_device_callback(device_data):
                def callback(icon, item):
                    self.show_device_info(device_data)

                return callback

            # 绑定正确的回调函数
            items.append(MenuItem(
                text,
                create_device_callback(dev),  # 替换原来的lambda方式
                enabled=True
            ))

        items.append(Menu.SEPARATOR)
        items.append(MenuItem("刷新", self.on_refresh))
        items.append(MenuItem("关于", self.show_about))
        items.append(Menu.SEPARATOR)
        items.append(MenuItem("退出", self.on_exit))
        return Menu(*items)

    def show_device_info(self, device_data):
        """打开设备信息详情窗口"""
        try:
            # 初始化Tk根窗口
            if self.tk_root is None:
                self.tk_root = tk.Tk()
                self.tk_root.withdraw()
                self.tk_root.update_idletasks()

            # 关闭已有设备窗口
            if self.device_info_window and hasattr(self.device_info_window, 'window'):
                try:
                    if self.device_info_window.window.winfo_exists():
                        self.device_info_window.window.destroy()
                except:
                    pass

            # 创建新的设备信息窗口
            self.device_info_window = DeviceInfoWindow(
                self.tk_root, device_data)
        except Exception as e:
            print(f"打开设备信息窗口失败: {e}")

    # ========== 刷新功能 ==========
    def on_refresh(self):
        """安全的刷新调用"""
        if async_loop:
            asyncio.run_coroutine_threadsafe(self.update_devices(), async_loop)

    async def update_devices(self):
        """异步更新设备数据"""
        try:
            self.devices = await get_device_info()
            print(self.devices)
            self.update_icon_tooltip()
            self.icon.menu = self.build_device_menu()
        except Exception as e:
            print(f"更新设备失败: {e}")

    # ========== 后台循环 ==========
    def _background_loop(self):
        """安全的后台更新循环"""
        while self.running:
            self.on_refresh()
            time.sleep(int(self.config['General']['update_interval']))

    def update_icon_tooltip(self):
        if not self.devices:
            self.icon.title = "未找到蓝牙设备"
            return

        tip_text = ""
        for device in self.devices:
            status_icon = "✅" if device.get("connected") else "❌"
            tip_text += f"{status_icon}{device.get('name')}: {device.get('battery', '?')}%\n"

        self.icon.title = "蓝牙设备电量\n" + tip_text

    # ========== 关于窗口 ==========
    def show_about(self):
        """在主线程创建关于窗口"""
        try:
            # 初始化Tk
            if self.tk_root is None:
                self.tk_root = tk.Tk()
                self.tk_root.withdraw()
                self.tk_root.update_idletasks()

            # 关闭已有窗口
            if self.about_window and self.about_window.winfo_exists():
                self.about_window.destroy()

            # 创建关于窗口
            self.about_window = tk.Toplevel(self.tk_root)
            self.about_window.title(f"关于 {self.APP_INFO['name']}")
            self.about_window.geometry("450x240")
            self.about_window.overrideredirect(True) # 隐藏窗口边框
            self.about_window.resizable(False, False)
            self.about_window.attributes('-topmost', True)
            self.about_window.attributes('-alpha', 0.0)

            # 居中显示
            self.about_window.update_idletasks()
            x = (self.about_window.winfo_screenwidth() -
                 self.about_window.winfo_width()) // 2
            y = (self.about_window.winfo_screenheight() -
                 self.about_window.winfo_height()) // 2
            self.about_window.geometry(f"+{x}+{y}")

            # 强制渲染
            self.about_window.update_idletasks()
            self.about_window.lift()
            self.about_window.focus_force()

            # 主框架
            main_frame = ttk.Frame(self.about_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            main_frame.update_idletasks()

            # 标题
            title_label = ttk.Label(
                main_frame,
                text=self.APP_INFO['name'],
                font=("微软雅黑", 18, "bold"),
                foreground="#0066cc"
            )
            title_label.pack(anchor=tk.W, pady=(0, 15))
            title_label.update_idletasks()

            # 信息文本
            info = f"版本: {self.APP_INFO['version']}\n作者: {self.APP_INFO['author']}\n网站: {self.APP_INFO['github_url']}"
            info_label = ttk.Label(main_frame, text=info, font=("微软雅黑", 10))
            info_label.pack(anchor=tk.W, pady=(0, 20))
            info_label.update_idletasks()

            # 分割线
            separator = ttk.Separator(main_frame, orient='horizontal')
            separator.pack(fill=tk.X, pady=(0, 15))
            separator.update_idletasks()
            # 取消按钮（核心：绑定关闭逻辑）
            # 按钮框架
            btn_frame = ttk.Frame(main_frame)
            btn_frame.pack(anchor=tk.E)
            ttk.Button(
                btn_frame,
                text="确定",
                command=self.about_window.destroy  # 点击即销毁窗口
            ).pack(side=tk.LEFT)

            # 显示窗口
            self.about_window.attributes('-alpha', 1.0)
            self.about_window.update()
            self.about_window.deiconify()
            self.about_window.mainloop()

        except Exception as e:
            print(f"创建关于窗口失败: {e}")

    # ========== 退出功能 ==========
    def on_exit(self):
        self.running = False

        # 停止异步循环
        if async_loop:
            async_loop.call_soon_threadsafe(async_loop.stop)

        # 关闭所有窗口
        try:
            if self.about_window and self.about_window.winfo_exists():
                self.about_window.destroy()
        except:
            pass

        try:
            if self.device_info_window and hasattr(self.device_info_window, 'window'):
                if self.device_info_window.window.winfo_exists():
                    self.device_info_window.window.destroy()
        except:
            pass

        if self.tk_root:
            self.tk_root.quit()
            self.tk_root.destroy()

        # 停止托盘
        self.icon.stop()

    # ========== 主程序 ==========
    def run(self):
        # 启动异步循环线程
        global async_loop_thread
        async_loop_thread = threading.Thread(
            target=start_async_loop, daemon=True)
        async_loop_thread.start()

        # 初始化托盘
        self.icon = Icon(
            "BlueGauge",
            self.get_tray_icon(),
            "蓝牙设备电量",
            menu=self.build_device_menu()
        )

        # 启动后台更新
        threading.Thread(target=self._background_loop, daemon=True).start()

        # 运行托盘
        self.icon.run()


async def get_device_info():
    ble = buletooth.BLE.Bluetooth()
    btc = buletooth.BTC.Bluetooth()
    return await ble.scan_ble_devices() + await btc.scan_classic_devices()


if __name__ == "__main__":
    app = BTBattery()
    app.run()
