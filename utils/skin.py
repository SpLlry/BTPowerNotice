import os
import importlib.util


class SkinManager:
    """皮肤管理器，用于动态加载和管理皮肤"""

    def __init__(self, skin_dir, module_name):
        self.skins = {}

        # 使用绝对路径，确保在不同工作目录下都能找到皮肤文件
        self.skin_dir = os.path.abspath(skin_dir)
        self.module = module_name
        self.load()
        # print(self.skin_dir, self.module)
        # skin_dir = os.path.join(os.path.dirname(__file__))

    def load(self):
        """加载所有皮肤模块"""
        # 获取皮肤目录路径

        # 遍历目录中的所有.py文件
        for filename in os.listdir(self.skin_dir):
            if filename.endswith('.py'):
                # 模块名（去掉.py后缀）
                module_name = filename[:-3]
                # 模块路径
                module_path = os.path.join(self.skin_dir, filename)

                try:
                    # 动态导入模块
                    spec = importlib.util.spec_from_file_location(
                        module_name, module_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # 检查模块是否包含Ring类
                    if hasattr(module, self.module):
                        self.skins[module_name] = getattr(module, self.module)
                        # print(f"加载皮肤: {module_name}")
                except Exception as e:
                    print(f"加载皮肤 {module_name} 失败: {e}")

    def getSkin(self, skin_name):
        """获取指定名称的皮肤类"""
        return self.skins.get(skin_name)

    def getAll(self):
        """列出所有可用的皮肤"""
        return list(self.skins.keys())

    def reload(self):
        """重新加载所有皮肤"""
        self.skins.clear()
        self.load()
