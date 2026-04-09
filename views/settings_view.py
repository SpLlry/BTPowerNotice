# fmt: off
# 标准库导入
import sys
import os;sys.path.append(os.getcwd()) # 添加当前目录到 sys.path
# fmt: on


# 第三方库导入
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QCheckBox,
    QListWidget,
    QPushButton,
    QApplication,
    QLineEdit,
    QFormLayout,
    QStyledItemDelegate,
)

# 本地库导入
from utils import get_icon_path, is_self_start, add_startup, remove_startup
from utils.skin import SkinManager
from utils.tools import config, dc, env, show_toast, set_log_file, set_log_window


class ComboBoxFontDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        option.font = QFont("Microsoft YaHei", 10)
        super().paint(painter, option, index)

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(24)  # 下拉选项高度
        return size


class DeviceEditDialog(QDialog):
    def __init__(self, parent=None, mac="", name="", show_device=True, title="编辑设备"):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.setMinimumWidth(280)
        self.setWindowFlags(Qt.WindowType.Window |  # 基础窗口
                            Qt.WindowType.WindowCloseButtonHint |  # 仅显示关闭按钮
                            Qt.WindowType.MSWindowsFixedSizeDialogHint  # 固定大小，禁用最大化/最小化
                            )

        self.mac = mac
        self.name = name

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        form = QFormLayout()
        self.mac_edit = QLineEdit(mac)
        self.mac_edit.setReadOnly(True)
        self.name_edit = QLineEdit(name)
        self.show_device = QCheckBox("显示设备")
        form.addRow("MAC 地址", self.mac_edit)
        form.addRow("设备名称", self.name_edit)
        form.addRow("", self.show_device)
        layout.addLayout(form)
        self.show_device.setChecked(show_device)

        btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("取消")
        self.ok_btn = QPushButton("确认")

        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #eeeeee;
            }
        """)
        # 确认按钮样式（蓝色主色调，突出显示）
        self.ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #3080e8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #2668c7;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        self.ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.ok_btn)
        layout.addLayout(btn_layout)

    def getValues(self):
        return self.mac_edit.text().strip(), self.name_edit.text().strip(), self.show_device.isChecked()


class SettingsWindow(QDialog):
    def __init__(self, parent=None, device_info=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setWindowFlags(Qt.WindowType.Window |  # 基础窗口
                            Qt.WindowType.WindowCloseButtonHint |  # 仅显示关闭按钮
                            Qt.WindowType.MSWindowsFixedSizeDialogHint  # 固定大小，禁用最大化/最小化
                            )
        self.device_info = device_info or {}
        # 全局字体设置（确保所有控件字体统一）
        self.setFont(QFont("Microsoft YaHei", 10))

        # 全局样式表（核心：统一所有控件的显示样式）
        self.setStyleSheet(
            """
            QDialog {
                background-color: #ffffff;
            }
            QLabel {
                font-family: "Microsoft YaHei";
                font-size: 10pt;
                padding: 2px 0;  # 给标签增加上下内边距，避免文字挤压
            }
            QLabel[style*="font-size:14px"] {  # 标题标签特殊样式
                font-size: 14pt;
                font-weight: bold;
                margin-bottom: 8px;
            }
            QComboBox {
                font-family: "Microsoft YaHei";
                font-size: 20pt;
                height: 34px;  // 固定高度（替代min-height，更精准）
                padding: 2px 10px;  // 上下内边距增加，让文字垂直居中
                padding:  10;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: #000;
            }
            QComboBox::drop-down {
                width: 36px;
                border-left: 1px solid #e0e0e0;
            }
            QCheckBox {
                font-family: "Microsoft YaHei";
                font-size: 10pt;
                min-height: 38px;  # 加大复选框高度
                spacing: 8px;  # 复选框和文字之间的间距
                padding: 2px 0;
            }
            QPushButton {
                font-family: "Microsoft YaHei";
                font-size: 10pt;
                background-color: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #eeeeee;
            }
            QListWidget {
                font-family: "Microsoft YaHei";
                font-size: 10pt;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
            }
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
            }
            QTabBar::tab {
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #f0f0f0;
            }
        """
        )

        self.setWindowTitle("设置中心")
        self.setFixedSize(480, 460)
        self.setWindowIcon(QIcon(get_icon_path("icon/icon.ico")))

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)  # 调整主布局间距

        self.tab = QTabWidget()
        main_layout.addWidget(self.tab)

        self.tab1 = self.create_tab1()
        self.tab2 = self.create_tab2()
        self.tab3 = self.create_tab3()

        self.tab.addTab(self.tab1, "基础设置")
        self.tab.addTab(self.tab2, "设备自定义")
        # self.tab.addTab(self.tab3, "关于")

        close_btn = QPushButton("关闭")
        close_btn.setFixedSize(90, 36)
        close_btn.clicked.connect(self._close)
        main_layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.load_config()

    def _close(self):
        self.close()
        dc.set("config", config.all())

    def create_tab1(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(20)  # 加大模块之间的间距

        # ========== 样式设置 ==========
        title1 = QLabel("🎨 样式设置")
        title1.setFixedHeight(24)
        title1.setStyleSheet("font-size:14px; font-weight:bold;")
        lay.addWidget(title1)

        # 任务栏样式 - 标签+下拉框组合（优化对齐）
        task_layout = QHBoxLayout()
        task_layout.setSpacing(10)
        task_label = QLabel("任务栏样式")
        task_label.setFixedWidth(80)  # 固定标签宽度，对齐更整齐
        task_label.setFixedHeight(24)  # 代码强制固定高度，保持与下拉框一致高度
        self.task_combo = QComboBox()
        self.task_combo.addItems(SkinManager(
            "skin/ring/", "Ring").getAll())
        self.task_combo.setFixedHeight(24)  # 代码强制固定高度
        self.task_combo.setItemDelegate(ComboBoxFontDelegate())
        task_layout.addWidget(task_label)
        task_layout.addWidget(self.task_combo)
        lay.addLayout(task_layout)

        # 主窗口样式 - 标签+下拉框组合
        main_layout = QHBoxLayout()
        main_layout.setSpacing(10)
        main_label = QLabel("主窗口样式")
        main_label.setFixedWidth(80)  # 固定标签宽度，对齐更整齐
        main_label.setFixedHeight(24)  # 代码强制固定高度，保持与下拉框一致高度
        self.main_combo = QComboBox()
        self.main_combo.addItems(SkinManager(
            "skin/device/", "BTDeviceCard").getAll())
        self.main_combo.setItemDelegate(ComboBoxFontDelegate())
        self.main_combo.setFixedHeight(24)  # 代码强制固定高度
        main_layout.addWidget(main_label)
        main_layout.addWidget(self.main_combo)
        lay.addLayout(main_layout)

        # ========== 显示设置 ==========
        title2 = QLabel("👁 显示设置")
        title2.setFixedHeight(24)
        title2.setStyleSheet("font-size:14px; font-weight:bold;")
        lay.addWidget(title2)

        self.show_task = QCheckBox("显示任务栏图标")
        self.show_task.setFixedHeight(24)
        self.show_main = QCheckBox("显示主窗口")
        self.show_main.setFixedHeight(24)
        self.show_debug = QCheckBox("开启调试模式")
        self.show_debug.setFixedHeight(24)
        self.output_log = QCheckBox("打开日志记录")
        self.output_log.setFixedHeight(24)
        lay.addWidget(self.show_task)
        lay.addWidget(self.show_main)
        lay.addWidget(self.show_debug)
        lay.addWidget(self.output_log)

        # ========== 启动设置 ==========
        title3 = QLabel("🚀 启动设置")
        title3.setFixedHeight(24)
        title3.setStyleSheet("font-size:14px; font-weight:bold;")
        lay.addWidget(title3)

        self.startup_check = QCheckBox("开机自动启动")
        self.startup_check.setFixedHeight(24)
        lay.addWidget(self.startup_check)

        lay.addWidget(self.startup_check)

        lay.addStretch()
        return w

    def create_tab2(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)  # 统一和tab1的边距
        lay.setSpacing(12)

        self.device_list = QListWidget()
        lay.addWidget(self.device_list)
        self.device_list.itemDoubleClicked.connect(self.on_double_click_edit)
        self.load_device_from_data()
        return w

    def create_tab3(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        title = QLabel("ℹ️ 关于")
        title.setStyleSheet(
            "font-size:14px; font-weight:bold; margin-bottom:8px;")
        lay.addWidget(title)

        info_label = QLabel("蓝牙设备电量监控\nVersion 1.0\n\n© 2026 版权所有")
        info_label.setStyleSheet("font-size:10pt; line-height:1.5;")
        lay.addWidget(info_label, alignment=Qt.AlignmentFlag.AlignTop)
        return w

    def load_config(self):
        # 加载皮肤
        skin = config.getVal("Settings", "skin", "Default")
        idx = self.task_combo.findText(skin)
        if idx >= 0:
            self.task_combo.setCurrentIndex(idx)

        d_skin = config.getVal("Settings", "device_skin", "Default")
        idx2 = self.main_combo.findText(d_skin)
        if idx2 >= 0:
            self.main_combo.setCurrentIndex(idx2)

        # 加载开机自启
        self.startup_check.setChecked(is_self_start())

        # 加载显示配置
        self.show_task.setChecked(config.getVal(
            "Settings", "show_task", "1") == "1")
        self.show_main.setChecked(config.getVal(
            "Settings", "show_main", "1") == "1")
        self.show_debug.setChecked(
            config.getVal("Debug", "window", "0") == "1")
        self.output_log.setChecked(
            config.getVal("Debug", "output", "0") == "1")

        # 绑定保存
        self.task_combo.currentTextChanged.connect(
            lambda t: config.setVal("Settings", "skin", t)
        )
        self.main_combo.currentTextChanged.connect(
            lambda t: config.setVal("Settings", "device_skin", t)
        )
        self.startup_check.clicked.connect(self.save_startup)
        self.show_task.clicked.connect(
            lambda v: config.setVal("Settings", "show_task", "1" if v else "0")
        )
        self.show_main.clicked.connect(
            lambda v: config.setVal("Settings", "show_main", "1" if v else "0")
        )
        self.show_debug.clicked.connect(lambda v: self.show_debug_set(v))
        self.output_log.clicked.connect(lambda v: self.output_log_set(v))

    def show_debug_set(self, checked):
        config.setVal("Debug", "window", "1" if checked else "0")

        set_log_window(checked)
        if checked:
            show_toast(self, "提示", "调试模式已开启")

    def output_log_set(self, checked):
        config.setVal("Debug", "output", "1" if checked else "0")
        set_log_file(checked)
        if checked:
            show_toast(self, "提示", "日志记录已开启")

    def save_startup(self, checked):
        if checked:
            add_startup(env.APP_NAME, "蓝牙电量监控工具 - 开机自动运行")
        else:
            remove_startup(env.APP_NAME)
        config.setVal("Settings", "self_start", "1" if checked else "0")

    def load_device_from_data(self):
        self.device_list.clear()
        custom = (
            dict(config.items("CustomDeviceName"))
            if config.has_section("CustomDeviceName")
            else {}
        )
        for mac, dev in self.device_info.items():
            key = mac.replace(":", "").upper()
            name = custom.get(key, dev.get("name", "未知"))
            self.device_list.addItem(f"{name} [{mac}]")

    def on_double_click_edit(self, item):
        txt = item.text()
        mac = txt.split("[")[-1].replace("]", "").strip()
        name = txt.split(" [")[0].strip()
        show_device = config.getVal(
            "CustomDeviceShow", mac.replace(":", "").upper(), "1") == "1"
        dlg = DeviceEditDialog(self, mac, name, show_device)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_mac, new_name, show_device = dlg.getValues()
            if new_mac:
                config.setVal(
                    "CustomDeviceName", new_mac.replace(
                        ":", "").upper(), new_name
                )
                config.setVal(
                    "CustomDeviceShow", new_mac.replace(
                        ":", "").upper(), "1" if show_device else "0"
                )
                self.load_device_from_data()


if __name__ == "__main__":

    app = QApplication(sys.argv)
    # 给应用设置全局字体，避免系统字体干扰
    app.setFont(QFont("Microsoft YaHei", 10))
    test_dev = {"AA:BB:CC:DD:EE:FF": {"name": "测试耳机"}}
    win = SettingsWindow(device_info=test_dev)
    win.show()
    sys.exit(app.exec())
