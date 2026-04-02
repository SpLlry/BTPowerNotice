from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "BTPowerNotice"
    APP_VERSION: str = "0.1.9"
    APP_AUTHOR: str = "SpLlry"
    APP_DESCRIPTION: str = "一款轻松查看电脑蓝牙电量的工具"
    GITHUB_URL: str = "https://github.com/SpLlry/BTPowerNotice"
    GITEE_URL: str = "https://gitee.com/spllr/BTPowerNotice"
    COPYRIGHT_YEAR: int = 2026
    TRAY_ICON_TOOLTIP: str = "蓝牙设备电量"
    RELEASE_URL: str = (
        "https://gitee.com/api/v5/repos/spllr/BTPowerNotice/releases/latest"
    )


# settings = Settings()
