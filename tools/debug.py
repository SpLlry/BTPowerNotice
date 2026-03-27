import sys
import time
import os
import logging
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QComboBox,
    QSpinBox,
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from utils import get_icon_path
# 全局单例
_app = None
_logger_instance = None
_window_instance = None

# ===================== 自定义 SUCCESS 日志级别 =====================
LOG_SUCCESS = 25
logging.addLevelName(LOG_SUCCESS, "SUCCESS")


# ===================== 自定义Qt日志Handler =====================
class QtLogHandler(logging.Handler, QObject):
    log_signal = pyqtSignal(logging.LogRecord)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record):
        self.log_signal.emit(record)


# ===================== GUI日志窗口 =====================
class ColoredDebugWindow(QMainWindow):
    def __init__(self, output_to_file: bool):
        super().__init__()
        self.setWindowIcon(QIcon(get_icon_path("icon/icon.ico")))
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.output_to_file = output_to_file
        self.current_filter = "all"
        self.log_cache = []
        self.show_window = True

        self.text_edit = QTextEdit()
        self.init_ui()
        self._init_logging()

    def _init_logging(self):
        # 1. 屏蔽系统/第三方库冗余日志
        logging.getLogger("asyncio").setLevel(logging.WARNING)  # 屏蔽asyncio底层DEBUG
        logging.getLogger("PyQt6").setLevel(logging.WARNING)  # 屏蔽Qt冗余日志
        logging.getLogger("").setLevel(logging.DEBUG)

        # 2. 使用自定义命名日志器（避免污染根日志器）
        self.logger = logging.getLogger("AppLogger")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()
        self.logger.propagate = False  # 禁止向上传递日志，彻底杜绝冗余

        # 统一日志格式
        log_formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

        # 控制台输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_formatter)
        console_handler.setLevel(logging.DEBUG)
        self.logger.addHandler(console_handler)

        # GUI 窗口处理器
        self.qt_handler = QtLogHandler()
        self.qt_handler.setFormatter(log_formatter)
        self.qt_handler.setLevel(logging.DEBUG)
        self.qt_handler.log_signal.connect(self._append_filtered_text)
        self.logger.addHandler(self.qt_handler)

        # 文件输出处理器
        if self.output_to_file:
            log_dir = "logs"
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, f"{time.strftime('%Y-%m-%d')}.log")
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(log_formatter)
            self.logger.addHandler(file_handler)

        # 兼容 success 方法
        def success(msg, *args, **kwargs):
            self.logger.log(LOG_SUCCESS, msg, *args, **kwargs)

        self.logger.success = success

    def init_ui(self):
        self.setWindowTitle("调试窗口")
        self.setGeometry(100, 100, 900, 650)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        tool_layout = QHBoxLayout()
        self.clear_btn = QPushButton("清空日志")
        self.clear_btn.clicked.connect(self.clear_log)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部日志", "只看信息", "只看警告", "只看错误"])
        self.filter_combo.currentTextChanged.connect(self._on_filter_change)

        self.font_size = QSpinBox()
        self.font_size.setRange(8, 20)
        self.font_size.setValue(12)
        self.font_size.valueChanged.connect(self._change_font_size)

        self.top_btn = QPushButton("窗口置顶")
        self.top_btn.setCheckable(True)
        self.top_btn.clicked.connect(self._toggle_topmost)

        tool_layout.addWidget(self.clear_btn)
        tool_layout.addWidget(self.filter_combo)
        tool_layout.addWidget(self.top_btn)
        tool_layout.addWidget(self.font_size)
        tool_layout.addStretch()

        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Consolas", 10))
        self.text_edit.setStyleSheet(
            "background-color: #000; color: #D4D4D4;"
            "border: 1px solid #555; padding: 5px;"
        )

        layout.addLayout(tool_layout)
        layout.addWidget(self.text_edit)

    def _get_level_color(self, level_name: str) -> str:
        color_map = {
            "DEBUG": "#808080",
            "INFO": "#D4D4D4",
            "WARNING": "#FFCC00",
            "ERROR": "#FF4444",
            "SUCCESS": "#00FF00",
        }
        return color_map.get(level_name, "#D4D4D4")

    def _append_filtered_text(self, record: logging.LogRecord):
        log_text = self.qt_handler.format(record)
        level = record.levelname.lower()
        color = self._get_level_color(record.levelname)
        html = f'<span style="color:{color};">{log_text}</span>'

        self.log_cache.append((html, level))
        if not self.show_window or not self.text_edit:
            return

        try:
            if self.current_filter == "all" or self.current_filter == level:
                self.text_edit.append(html)
                self.text_edit.verticalScrollBar().setValue(
                    self.text_edit.verticalScrollBar().maximum()
                )
        except:
            pass

    def _refresh_display(self):
        if not self.show_window or not self.text_edit:
            return
        try:
            self.text_edit.clear()
            for html, level in self.log_cache:
                if self.current_filter == "all" or self.current_filter == level:
                    self.text_edit.append(html)
        except:
            pass

    def clear_log(self):
        self.log_cache.clear()
        if self.show_window and self.text_edit:
            try:
                self.text_edit.clear()
            except:
                pass

    def set_filter(self, level: str):
        self.current_filter = level
        self._refresh_display()

    def _on_filter_change(self, text):
        level_map = {
            "全部日志": "all",
            "只看信息": "info",
            "只看警告": "warning",
            "只看错误": "error",
        }
        self.set_filter(level_map[text])

    def _change_font_size(self, size):
        self.text_edit.setFont(QFont("Consolas", size))

    def _toggle_topmost(self, checked):
        if checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            self.top_btn.setText("取消置顶")
        else:
            self.setWindowFlags(
                self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint
            )
            self.top_btn.setText("窗口置顶")
        self.show()


# ===================== 核心接口 =====================
def logger(show_window: bool = True, output: bool = False):
    global _app, _logger_instance, _window_instance

    if _logger_instance:
        return _logger_instance

    _app = QApplication.instance() or QApplication(sys.argv)
    _window_instance = ColoredDebugWindow(output_to_file=output)
    _logger_instance = _window_instance.logger
    _window_instance.show_window = show_window

    if show_window:
        _window_instance.show()

    return _logger_instance


# ===================== 测试 =====================
if __name__ == "__main__":
    log = logger(show_window=True, output=True)
    log.debug("调试测试")
    log.info("日志工具启动成功")
    log.warning("警告测试")
    log.error("错误测试")
    log.success("成功测试")
    sys.exit(_app.exec())
