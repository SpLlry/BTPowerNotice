import sys
from PyQt6.QtWidgets import (
    QApplication, QDialog, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFrame
)
from PyQt6.QtGui import QFont, QCursor, QIcon, QPixmap
from PyQt6.QtCore import Qt

from utils import get_icon_path


class AboutCometDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.appConfig = {
            "appName": "BTPowerNotice",
            "author": "SpLlry",
            "version": "0.1.3",
            "description": "一款轻松查看电脑蓝牙电量的工具"
        }
        # 窗口基础设置
        self.setWindowTitle(f"关于 {self.appConfig.get('appName')}")
        self.setFixedSize(500, 300)
        self.setWindowIcon(QIcon(get_icon_path("icon/icon.ico")))
        # 主布局（垂直）
        main_layout = QVBoxLayout()
        main_layout.setSpacing(18)
        main_layout.setContentsMargins(25, 25, 25, 25)

        # --------------------------
        # 顶部：图标 + 标题 + 版本信息
        # --------------------------
        top_layout = QHBoxLayout()
        top_layout.setSpacing(25)

        # ========== 核心修改：加载本地ICO图标 ==========
        icon_path = get_icon_path("icon/icon.ico")
        icon_label = QLabel()
        # 加载图标并缩放（适配界面大小，可修改64,64调整尺寸）
        pixmap = QPixmap(icon_path).scaled(72, 72, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation)
        icon_label.setPixmap(pixmap)
        top_layout.addWidget(icon_label)

        # 标题 + 版本 垂直布局
        title_layout = QVBoxLayout()
        title_layout.setSpacing(8)

        title_label = QLabel(self.appConfig.get('appName'))
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_layout.addWidget(title_label)

        top_layout.addLayout(title_layout)
        main_layout.addLayout(top_layout)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line)

        auth_layout = QVBoxLayout()
        auth_layout.setSpacing(10)
        auth_text = (f'{self.appConfig.get("appName")} v{self.appConfig.get("version")}\n'
                     f'{self.appConfig.get("description")}'
                     f'\nCopyright(C) 2026 By {self.appConfig.get("author")}')
        auth_content_label = QLabel(auth_text)
        # 用等宽字体模拟原图像素感
        auth_content_label.setFont(QFont("Courier New", 16))
        auth_content_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        auth_layout.addWidget(auth_content_label)

        main_layout.addLayout(auth_layout)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line)
        # --------------------------
        # 链接区域（主页 + 技术支持）
        # --------------------------
        links_layout = QVBoxLayout()
        links_layout.setSpacing(15)
        home_layout = QHBoxLayout()
        githublink = QLabel(
            '<a href="https://github.com/SpLlry/BTPowerNotice" style="color: blue; text-decoration: underline;">'
            'GitHub</a>'
        )
        githublink.setFont(QFont("Microsoft YaHei", 13))
        githublink.setOpenExternalLinks(True)
        githublink.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        home_layout.addWidget(githublink)

        giteelink = QLabel(
            '<a href="https://gitee.com/spllr/BTPowerNotice" style="color: blue; text-decoration: underline;">'
            'Gitee</a>'
        )
        giteelink.setFont(QFont("Microsoft YaHei", 13))
        giteelink.setOpenExternalLinks(True)
        giteelink.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        home_layout.addWidget(giteelink)
        home_layout.addStretch()
        links_layout.addLayout(home_layout)

        main_layout.addLayout(links_layout)

        # --------------------------
        # 底部按钮区域
        # --------------------------
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        close_btn.setFixedSize(130, 38)
        buttons_layout.addWidget(close_btn)

        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))
    dialog = AboutCometDialog()
    dialog.show()
    sys.exit(app.exec())
