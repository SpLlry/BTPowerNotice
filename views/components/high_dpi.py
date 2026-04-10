from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt


def setup_high_dpi():
    """配置高DPI适配"""
    # 设置缩放因子（可选）
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
