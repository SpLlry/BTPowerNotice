# fmt: off
# 标准库导入
import sys
import os;sys.path.append(os.getcwd()) # 添加当前目录到 sys.path
# fmt: on
import webbrowser
import markdown
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QApplication,
)
from PyQt6.QtGui import QFont, QCursor, QIcon
from PyQt6.QtCore import Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView

# 原有导入
from utils.tools import env
from utils import get_icon_path


class CheckUpdateDialog(QDialog):
    def __init__(self, latest_info=None, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.latest_info = latest_info or {}
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"检查更新 - {env.APP_NAME}")
        self.setFixedSize(300, 400)
        self.setWindowIcon(QIcon(get_icon_path("icon/icon.ico")))

        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title_label = QLabel("🎉 发现新版本")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # 版本信息
        current_version_label = QLabel(f"当前版本: {env.APP_VERSION}")
        current_version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        new_version_label = QLabel(
            f"最新版本: {self.latest_info.get('tag_name', '未知')}")
        new_version_label.setFont(QFont("Microsoft YaHei", 14))
        new_version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(current_version_label)
        main_layout.addWidget(new_version_label)

        # ===================== 仅修改这里：替换为 QWebEngineView =====================
        # markdown 解析代码 100% 保留，完全没动！
        self.release_notes = QWebEngineView()
        self.release_notes.setMinimumHeight(150)

        # 👇 这部分和你原来的代码一模一样，没有任何修改
        md_content = self.latest_info.get("body", "暂无更新说明")
        html_content = markdown.markdown(md_content)

        # 原生方法渲染
        self.release_notes.setHtml(html_content)
        main_layout.addWidget(self.release_notes)
        # ============================================================================

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        download_btn = QPushButton("前往下载")
        download_btn.setFixedSize(120, 35)
        download_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        download_btn.clicked.connect(self.open_download_page)
        later_btn = QPushButton("稍后再说")
        later_btn.setFixedSize(100, 35)
        later_btn.clicked.connect(self.close)
        button_layout.addWidget(download_btn)
        button_layout.addWidget(later_btn)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def open_download_page(self):
        assets = self.latest_info.get("assets", [])
        url = assets[0]["browser_download_url"] if assets else env.GITHUB_URL
        webbrowser.open(url)
        self.close()


class NoUpdateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("检查更新")
        self.setFixedSize(350, 150)
        layout = QVBoxLayout()
        title = QLabel("✅ 已是最新版本")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(
            QLabel(f"当前版本: {env.APP_VERSION}", alignment=Qt.AlignmentFlag.AlignCenter))
        btn = QPushButton("确定")
        btn.clicked.connect(self.close)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 测试数据（标准Markdown + 图片）
    test_info = {
        "tag_name": "v1.0.0",
        "body": """## 更新日志
![展示图片](https://picsum.photos/280/100)
- 支持 Markdown 图片渲染
- 修复已知问题
- 优化 UI 显示效果
[查看详情](https://github.com/SpLlry/BTPowerNotice/releases)""",
        "assets": [{"browser_download_url": "https://github.com/SpLlry/BTPowerNotice/releases"}]
    }
    dialog = CheckUpdateDialog(test_info)
    dialog.show()
    dialog.finished.connect(app.quit)

    sys.exit(app.exec())
