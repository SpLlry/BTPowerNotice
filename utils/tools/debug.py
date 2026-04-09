import sys
import time
import os
import logging
from collections import deque
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QVBoxLayout,
    QWidget, QHBoxLayout, QPushButton, QComboBox, QSpinBox
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer  # 仅用PyQt自带库
from PyQt6.QtGui import QFont, QIcon


def get_icon_path(icon_name):
    return ""


# 全局单例
_app = None
LOG_SUCCESS = 25
logging.addLevelName(LOG_SUCCESS, "SUCCESS")

# ===================== Qt日志Handler =====================


class QtLogHandler(logging.Handler, QObject):
    log_signal = pyqtSignal(logging.LogRecord)

    def __init__(self, parent=None):
        logging.Handler.__init__(self)
        QObject.__init__(self, parent=parent)

    def emit(self, record):
        self.log_signal.emit(record)

# ===================== GUI日志窗口 =====================


class ColoredDebugWindow(QMainWindow):
    def __init__(self, max_cache_size=10000):
        super().__init__()
        self.setWindowIcon(QIcon(get_icon_path("icon/icon.ico")))
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.current_filter = "all"
        self.log_cache = deque(maxlen=max_cache_size)
        self.cache_clean_timer = QTimer(self)
        self.cache_clean_timer.setInterval(300000)
        self.cache_clean_timer.timeout.connect(self._clean_expired_cache)
        self.cache_clean_timer.start()
        self.text_edit = QTextEdit()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("调试窗口")
        self.setGeometry(100, 100, 900, 650)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        tool_layout = QHBoxLayout()
        self.clear_btn = QPushButton("清空日志")
        self.clear_btn.clicked.connect(self.clear_log)
        self.clean_expired_btn = QPushButton("清理过期日志")
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部日志", "只看信息", "只看警告", "只看错误"])
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 20)
        self.font_size.setValue(12)
        self.top_btn = QPushButton("窗口置顶")
        self.top_btn.setCheckable(True)
        self.top_btn.clicked.connect(self._toggle_topmost)

        tool_layout.addWidget(self.clear_btn)
        tool_layout.addWidget(self.clean_expired_btn)
        tool_layout.addWidget(self.filter_combo)
        tool_layout.addWidget(self.top_btn)
        tool_layout.addWidget(self.font_size)
        tool_layout.addStretch()

        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Consolas", 10))
        self.text_edit.setStyleSheet(
            "background-color:#000;color:#D4D4D4;border:1px solid #555;padding:5px;")
        layout.addLayout(tool_layout)
        layout.addWidget(self.text_edit)
        self.filter_combo.currentTextChanged.connect(self._on_filter_change)
        self.font_size.valueChanged.connect(self._change_font_size)
        self.clean_expired_btn.clicked.connect(self._clean_expired_cache)

    def _get_level_color(self, level_name):
        return {"DEBUG": "#808080", "INFO": "#D4D4D4", "WARNING": "#FFCC00", "ERROR": "#FF4444", "SUCCESS": "#00FF00"}.get(level_name, "#D4D4D4")

    def append_log(self, record):
        log_text = f"{record.asctime} [{record.levelname}] {record.getMessage()}"
        color = self._get_level_color(record.levelname)
        html = f'<span style="color:{color};">{log_text}</span>'
        self.log_cache.append((html, record.levelname.lower()))
        if self.current_filter == "all" or self.current_filter == record.levelname.lower():
            self.text_edit.append(html)
            self.text_edit.verticalScrollBar().setValue(
                self.text_edit.verticalScrollBar().maximum())

    def _refresh_display(self):
        self.text_edit.clear()
        for html, level in self.log_cache:
            if self.current_filter == "all" or self.current_filter == level:
                self.text_edit.append(html)

    def clear_log(self):
        self.log_cache.clear()
        self.text_edit.clear()

    def _clean_expired_cache(self):
        self.log_cache = deque(self.log_cache, maxlen=self.log_cache.maxlen)
        self._refresh_display()

    def _on_filter_change(self, text):
        self.current_filter = {"全部日志": "all", "只看信息": "info",
                               "只看警告": "warning", "只看错误": "error"}[text]
        self._refresh_display()

    def _change_font_size(self, size):
        self.text_edit.setFont(QFont("Consolas", size))

    def _toggle_topmost(self, checked):
        if checked:
            self.setWindowFlags(self.windowFlags() |
                                Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~
                                Qt.WindowType.WindowStaysOnTopHint)
        self.top_btn.setText("取消置顶" if checked else "窗口置顶")
        self.show()

    def closeEvent(self, event):
        self.cache_clean_timer.stop()
        self.log_cache.clear()
        event.accept()

# ===================== 核心：单例日志管理器（无threading，纯Qt） =====================


class LoggerManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        global _app
        _app = QApplication.instance() or QApplication(sys.argv)
        self.logger = logging.getLogger("AppLogger")
        self.logger.handlers.clear()
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        self.formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")

        # 状态管理
        self._show_window = False
        self._output_file = False
        # 组件实例
        self._window = None
        self._qt_handler = None
        self._file_handler = None

        # 默认控制台输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)

        # 扩展 success 方法
        self.logger.success = lambda msg, * \
            args, **kw: self.logger.log(LOG_SUCCESS, msg, *args, **kw)

    # ===================== 动态配置核心API =====================
    def set_show_window(self, show: bool):
        """运行时动态显示/隐藏日志窗口"""
        if self._show_window == show:
            return
        self._show_window = show

        if show:
            # 显示窗口：创建GUI
            self._window = ColoredDebugWindow()
            self._qt_handler = QtLogHandler(self._window)
            self._qt_handler.setFormatter(self.formatter)
            self._qt_handler.log_signal.connect(self._window.append_log)
            self.logger.addHandler(self._qt_handler)
            self._window.show()
        else:
            # 隐藏窗口：销毁GUI（无内存泄漏）
            if self._qt_handler:
                self.logger.removeHandler(self._qt_handler)
                self._qt_handler.deleteLater()
                self._qt_handler = None
            if self._window:
                self._window.close()
                self._window.deleteLater()
                self._window = None

    def set_output_file(self, output: bool):
        """运行时动态开启/关闭文件日志"""
        if self._output_file == output:
            return
        self._output_file = output

        if output:
            # 开启文件写入
            os.makedirs("logs", exist_ok=True)
            log_file = os.path.join("logs", f"{time.strftime('%Y-%m-%d')}.log")
            self._file_handler = logging.FileHandler(
                log_file, encoding="utf-8")
            self._file_handler.setFormatter(self.formatter)
            self.logger.addHandler(self._file_handler)
        else:
            # 关闭文件写入
            if self._file_handler:
                self.logger.removeHandler(self._file_handler)
                self._file_handler.close()
                self._file_handler = None

# ===================== 对外接口（兼容原有调用） =====================


def logger(show_window: bool = True, output: bool = False):
    log_mgr = LoggerManager()
    log_mgr.set_show_window(show_window)
    log_mgr.set_output_file(output)
    return log_mgr.logger

# 全局动态配置函数（运行中随时调用）


def set_log_window(show: bool):
    LoggerManager().set_show_window(show)


def set_log_file(output: bool):
    LoggerManager().set_output_file(output)


# ===================== 测试（纯QTimer实现，无threading） =====================
if __name__ == "__main__":
    # 初始化：无窗口 + 不写文件
    log = logger(show_window=False, output=False)
    log.info("初始化完成：无窗口 + 无文件日志")

    # 使用 PyQt 自带 QTimer 替代线程延时（主线程执行，安全无冲突）
    # 3秒后显示窗口
    QTimer.singleShot(3000, lambda: (
        set_log_window(True), log.info("动态开启：显示日志窗口")))
    # 6秒后写入文件
    QTimer.singleShot(6000, lambda: (
        set_log_file(True), log.info("动态开启：写入文件日志")))
    # 9秒后隐藏窗口
    QTimer.singleShot(9000, lambda: (
        set_log_window(False), log.info("动态关闭：隐藏日志窗口")))

    sys.exit(_app.exec())
