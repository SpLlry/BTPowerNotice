import sys
import webbrowser
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QScrollArea,
)
from PyQt6.QtGui import QFont, QCursor, QIcon
from PyQt6.QtCore import Qt, QUrl

from setting import settings
from utils import get_icon_path


class CheckUpdateDialog(QDialog):
    def __init__(self, latest_info=None, parent=None):
        super().__init__(parent)
        self.latest_info = latest_info or {}
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"检查更新 - {settings.APP_NAME}")
        self.setFixedSize(300, 400)
        self.setWindowIcon(QIcon(get_icon_path("icon/icon.ico")))

        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel(f"🎉 发现新版本")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        version_layout = QHBoxLayout()
        version_layout.addStretch()
        current_version_label = QLabel(f"当前版本: {settings.APP_VERSION}")
        version_layout.addWidget(current_version_label)
        version_layout.addStretch()
        main_layout.addLayout(version_layout)

        new_version_label = QLabel(
            f"最新版本: {self.latest_info.get('tag_name', '未知')}"
        )
        new_version_font = QFont()
        new_version_font.setPointSize(14)
        new_version_label.setFont(new_version_font)
        new_version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(new_version_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(150)

        release_notes = QTextBrowser()
        print(self.latest_info.get("body", "暂无更新说明"))
        release_notes.setMarkdown(self.latest_info.get("body", "暂无更新说明"))
        release_notes.setOpenExternalLinks(True)
        scroll_area.setWidget(release_notes)
        main_layout.addWidget(scroll_area)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        download_btn = QPushButton("前往下载")
        download_btn.setFixedSize(120, 35)
        download_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        download_btn.clicked.connect(self.open_download_page)
        button_layout.addWidget(download_btn)

        later_btn = QPushButton("稍后再说")
        later_btn.setFixedSize(100, 35)
        later_btn.clicked.connect(self.close)
        button_layout.addWidget(later_btn)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def open_download_page(self):
        assets = self.latest_info.get("assets", [])
        if assets and "browser_download_url" in assets[0]:
            url = assets[0]["browser_download_url"]
        else:
            url = settings.GITHUB_URL
        webbrowser.open(url)
        self.close()


class NoUpdateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("检查更新")
        self.setFixedSize(350, 150)
        self.setWindowIcon(QIcon(get_icon_path("icon/icon.ico")))

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        title_label = QLabel("✅ 已是最新版本")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        version_label = QLabel(f"当前版本: {settings.APP_VERSION}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        ok_btn = QPushButton("确定")
        ok_btn.setFixedSize(100, 30)
        ok_btn.clicked.connect(self.close)
        layout.addWidget(ok_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    test_info = {
        "tag_name": "v0.2.0",
        "body": "## 更新内容\n\n- 新增功能1\n- 修复bug\n- 优化性能",
        "assets": [
            {"browser_download_url": "https://github.com/SpLlry/BTPowerNotice/releases"}
        ],
    }

    dialog = CheckUpdateDialog(test_info)
    dialog.show()

    sys.exit(app.exec())
