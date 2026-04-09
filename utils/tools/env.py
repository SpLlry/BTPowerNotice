from pydantic_settings import BaseSettings


class Env(BaseSettings):
    APP_NAME: str = "BTPowerNotice"
    APP_VERSION: str = "0.2.0"
    APP_AUTHOR: str = "SpLlry"
    APP_DESCRIPTION: str = "一款轻松查看电脑蓝牙电量的工具"
    GITHUB_URL: str = "https://github.com/SpLlry/BTPowerNotice"
    GITEE_URL: str = "https://gitee.com/spllr/BTPowerNotice"
    COPYRIGHT_YEAR: int = 2026
    TRAY_ICON_TOOLTIP: str = "蓝牙设备电量"
    REWARD_URL: str = r"https://gitee.com/spllr/BTPowerNotice#%E6%8D%90%E8%B5%A0"
    RELEASE_URL: str = (
        "https://gitee.com/api/v5/repos/spllr/BTPowerNotice/releases/latest"
    )


# settings = Settings()
