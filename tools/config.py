import configparser
import os.path
import threading



class Config:
    def __init__(self, config_file_path):
        super().__init__()
        self.config = configparser.ConfigParser()
        self.file_path = config_file_path
        self._dirty = False
        self._save_timer = None
        self._save_delay = 2.0

        if not os.path.exists(os.path.dirname(self.file_path)):
            os.makedirs(os.path.dirname(self.file_path))
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w") as configfile:
                self.config.write(configfile)
        self.config.read(self.file_path, encoding="utf-8")

    def getVal(self, section, key=None):
        if not self.config.has_section(section):
            return None
        if key is not None:
            if not self.config.has_option(section, key):
                return None
            return self.config.get(section, key)
        else:
            return self.config.items(section)

    def setVal(self, section, key, value):
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, value)
        self._mark_dirty()

    def removeVal(self, section, key=None):
        if self.config.has_section(section):
            if key is not None:
                self.config.remove_option(section, key)
            else:
                self.config.remove_section(section)
            self._mark_dirty()

    def _mark_dirty(self):
        self._dirty = True
        if self._save_timer is not None:
            self._save_timer.cancel()
        self._save_timer = threading.Timer(self._save_delay, self._flush)
        self._save_timer.daemon = True
        self._save_timer.start()

    def _flush(self):
        if self._dirty:
            with open(self.file_path, "w") as configfile:
                self.config.write(configfile)
            self._dirty = False

    def flush(self):
        if self._save_timer is not None:
            self._save_timer.cancel()
        self._flush()





if __name__ == "__main__":
    Config = Config(get_exe_run_dir() + "\\config\\config.ini")
    print(Config.getVal("Settings", "task_bar"))
    Config.setVal("Settings", "task_bar", "1")
    Config.removeVal("Setting1s", "1")
    Config.removeVal("Setting1s")
    import time

    time.sleep(3)
