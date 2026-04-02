import sys
from PyQt6.QtWidgets import (
    QApplication, QDialog, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFrame
)
from PyQt6.QtGui import QFont, QCursor, QIcon, QPixmap
from PyQt6.QtCore import Qt, QTimer

from utils import get_icon_path
from tools import settings


class AboutCometDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 🚀 优化1：加速窗口渲染属性
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setWindowFlags(Qt.WindowType.Window |
                            Qt.WindowType.CustomizeWindowHint |
                            Qt.WindowType.WindowCloseButtonHint)
        self.setWindowTitle(f"关于 {settings.APP_NAME}")
        self.setFixedSize(500, 300)
        
        # 🚀 优化2：窗口图标预加载（极快）
        self.setWindowIcon(QIcon(get_icon_path("icon/icon.ico")))
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(18)
        main_layout.setContentsMargins(25, 25, 25, 25)
        self.setLayout(main_layout)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(25)

        # 🚀 优化3：先创建空标签，延迟加载图片（不阻塞窗口）
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(43, 43)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_layout.addWidget(self.icon_label)

        # 标题区域
        title_layout = QVBoxLayout()
        title_layout.setSpacing(8)
        title_label = QLabel(settings.APP_NAME)
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_layout.addWidget(title_label)
        top_layout.addLayout(title_layout)
        main_layout.addLayout(top_layout)

        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        main_layout.addWidget(line)

        # 版权信息
        auth_layout = QVBoxLayout()
        auth_text = (f'{settings.APP_NAME} v{settings.APP_VERSION}\n'
                     f'{settings.APP_DESCRIPTION}'
                     f'\nCopyright(C) {settings.COPYRIGHT_YEAR} By {settings.APP_AUTHOR}')
        auth_content_label = QLabel(auth_text)
        auth_content_label.setFont(QFont("Microsoft YaHei", 11)) # 🚀 优化4：替换卡顿字体
        auth_content_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        auth_layout.addWidget(auth_content_label)
        main_layout.addLayout(auth_layout)

        main_layout.addWidget(line)

        # 链接
        links_layout = QVBoxLayout()
        home_layout = QHBoxLayout()
        githublink = QLabel(f'<a href="{settings.GITHUB_URL}">GitHub</a>')
        githublink.setFont(QFont("Microsoft YaHei", 13))
        githublink.setOpenExternalLinks(True)
        githublink.setCursor(Qt.CursorShape.PointingHandCursor)
        
        giteelink = QLabel(f'<a href="{settings.GITEE_URL}">Gitee</a>')
        giteelink.setFont(QFont("Microsoft YaHei", 13))
        giteelink.setOpenExternalLinks(True)
        giteelink.setCursor(Qt.CursorShape.PointingHandCursor)
        
        home_layout.addWidget(githublink)
        home_layout.addWidget(giteelink)
        home_layout.addStretch()
        links_layout.addLayout(home_layout)
        main_layout.addLayout(links_layout)

        # 按钮
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        close_btn.setFixedSize(130, 38)
        buttons_layout.addWidget(close_btn)
        main_layout.addLayout(buttons_layout)

        # 🚀 优化5：窗口显示后，再异步加载图片（窗口秒开）
        QTimer.singleShot(10, self.load_icon)

    # 🚀 异步加载图标，不阻塞窗口启动
    def load_icon(self):
        icon_path = get_icon_path("icon/icon.ico")
        # 快速加载，降低性能消耗
        pixmap = QIcon(icon_path).pixmap(43, 43)
        self.icon_label.setPixmap(pixmap)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))
    dialog = AboutCometDialog()
    dialog.show()
    sys.exit(app.exec())