from PyQt6.QtWidgets import QMainWindow, QPushButton
from pyqttoast import Toast, ToastPreset, ToastPosition
from qtpy.QtCore import QSize


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.button = QPushButton("Show toast", self)
        self.button.clicked.connect(self.show_toast)

    def show_toast(self):
        show_toast(
            parent=self,
            title="Success!",
            text="Check your email to complete signup.",
            duration=5000,
        )


def show_toast(parent, title, text, preset="success", duration=5000, bind=False):
    toast = Toast(parent)
    toast.setDuration(duration)  # 5秒后自动消失
    toast.setFixedSize(QSize(280, 80))
    toast.setTitle(title)
    toast.setText(text)
    preset_list = {
        "success": ToastPreset.SUCCESS,
        "error": ToastPreset.ERROR,
        "info": ToastPreset.INFORMATION,
        "warning": ToastPreset.WARNING,
    }
    if preset not in preset_list:
        preset = ToastPreset.SUCCESS
    else:
        preset = preset_list[preset]

    toast.applyPreset(preset)
    toast.setPosition(ToastPosition.BOTTOM_RIGHT)  # Default: ToastPosition.BOTTOM_RIGHT
    if bind:
        toast.setPositionRelativeToWidget(parent)
    toast.setMinimumHeight(50)
    toast.setMaximumHeight(120)
    toast.show()


# 注意：每个 Toast 实例只能显示一次，重复显示需新建实例
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())
