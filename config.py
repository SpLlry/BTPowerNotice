import configparser
import os.path

from utils import get_exe_run_dir


class Config:
    def __init__(self, config_file_path):
        super().__init__()
        self.config = configparser.ConfigParser()  # 初始化一个configparser类对象
        self.file_path = config_file_path
        # 多级目录创建
        if not os.path.exists(os.path.dirname(self.file_path)):
            os.makedirs(os.path.dirname(self.file_path))
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as configfile:
                self.config.write(configfile)
        self.config.read(self.file_path, encoding='utf-8')  # 读取config.ini文件内容

    def getVal(self, section, key=None):
        # 检查配置段是否存在
        if not self.config.has_section(section):
            return None
        if key is not None:
            if not self.config.has_option(section, key):
                return None
            return self.config.get(section, key)  # 获取某个section下面的某个key的值
        else:
            return self.config.items(section)  # 或者某个section下面的所有值

    def setVal(self, section, key, value):
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, value)
        with open(self.file_path, 'w') as configfile:
            self.config.write(configfile)

    def removeVal(self, section, key=None):
        if self.config.has_section(section):
            if key is not None:
                self.config.remove_option(section, key)  # 获取某个section下面的某个key的值
            else:
                self.config.remove_section(section)  # 或者某个section下面的所有值
            with open(self.file_path, 'w') as configfile:
                self.config.write(configfile)


def create_config():
    return Config(get_exe_run_dir() + '\\config\\config.ini')


if __name__ == "__main__":
    Config = Config(get_exe_run_dir() + '\\config\\config.ini')
    print(Config.getVal('Settings', 'task_bar'))  # 结果为 https://www.baidu..com/
    Config.setVal('Settings', 'task_bar', "1")
    Config.removeVal('Setting1s', "1")
    Config.removeVal('Setting1s')
    # 结果为[('host', 'smtp.163.com'), ('account', '12345678@163.com'), ('password', '12345678')]
