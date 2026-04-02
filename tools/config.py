import configparser
import os.path
import threading
import time


class Config:
    def __init__(self, config_file_path):
        super().__init__()
        # 🔥 终极修复：用 RawConfigParser，支持 key 带 : = 等所有符号
        self.config = configparser.RawConfigParser(
            comment_prefixes=('/', '#'),
            strict=False
        )
        self.config.optionxform = str  # 保留大小写，不修改key

        self.file_path = config_file_path
        self._dirty = False
        self._save_timer = None
        self._save_delay = 1.0

        if not os.path.exists(os.path.dirname(self.file_path)):
            os.makedirs(os.path.dirname(self.file_path))

        # 兼容编码读取
        try:
            self.config.read(self.file_path, encoding="utf-8-sig")
        except:
            try:
                self.config.read(self.file_path, encoding="gbk")
            except:
                pass

    def getVal(self, section, key=None, default=None):
        if not self.config.has_section(section):
            return None
        if key is not None:
            if not self.config.has_option(section, key):
                return default
            return self.config.get(section, key)
        else:
            return self.config.items(section)

    def setVal(self, section, key, value):
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, str(value))
        self._mark_dirty()

    def has_section(self, section):
        return self.config.has_section(section)

    def has_option(self, section, key):
        return self.config.has_option(section, key)

    def items(self, section):
        if not self.config.has_section(section):
            return []
        return self.config.items(section)

    def del_Val(self, section, key=None):
        if not self.config.has_section(section):
            return
        if key is not None:
            if self.config.has_option(section, key):
                self.config.remove_option(section, key)
                self._mark_dirty()
        else:
            self.config.remove_section(section)
            self._mark_dirty()

    def all(self):
        ret = {}
        for section in self.config.sections():
            ret[section] = dict(self.config.items(section))
        return ret

    def _mark_dirty(self):
        self._dirty = True
        if self._save_timer is not None:
            self._save_timer.cancel()
        self._save_timer = threading.Timer(self._save_delay, self._flush)
        self._save_timer.daemon = True
        self._save_timer.start()

    def _flush(self):
        if self._dirty:
            with open(self.file_path, "w", encoding="utf-8-sig") as configfile:
                self.config.write(configfile)
            self._dirty = False

    def flush(self):
        if self._save_timer is not None:
            self._save_timer.cancel()
        self._flush()


if __name__ == "__main__":
    config = Config(r"E:\SuPing\py\BTPowerNotice\config\config.ini")

    print(config.all())
    # print("保存成功！")
    # time.sleep(3)
