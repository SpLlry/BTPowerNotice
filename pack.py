# -*- coding: utf-8 -*-
import os
import shutil
import subprocess
import sys

# 导入配置
sys.path.insert(0, os.path.dirname(__file__))
from tools.setting import Settings
settings = Settings()

# ===================== 核心配置（自动读取） =====================
# 解析版本号
MAJOR, MINOR, PATCH, BUILD = 0, 0, 0, 0
version_parts = settings.APP_VERSION.split(".")
if len(version_parts) >= 1:
    MAJOR = int(version_parts[0]) if version_parts[0] else 0
if len(version_parts) >= 2:
    MINOR = int(version_parts[1]) if version_parts[1] else 0
if len(version_parts) >= 3:
    PATCH = int(version_parts[2]) if version_parts[2] else 0

APP_NAME = settings.APP_NAME
FILE_DESC = settings.APP_DESCRIPTION
APP_AUTHOR = settings.APP_AUTHOR
EXE_NAME = f"{APP_NAME}.exe"
COPYRIGHT = f"Copyright © {settings.COPYRIGHT_YEAR} {APP_AUTHOR}"
VERSION_FILE = "version_info.txt"
MAIN_SCRIPT = "main.py"

# 需要复制的资源文件夹
NEED_FILES = ["icon", "ui", "config"]

# ===================== PyInstaller 打包参数 =====================
# 自由切换：-F=单文件模式 / -D=单目录模式，脚本会自动识别！
PYI_ARGS = [
    "--disable-windowed-traceback",
    "-D",          # 单目录模式（改为 -F 就是单文件模式）
    "-w",
    "-n", APP_NAME,
    "-i", os.path.join("icon", "icon.ico"),
    "--add-data", "icon;icon" if sys.platform == "win32" else "icon:icon",
    "--version-file", VERSION_FILE,
   # 🔥 启用UPX压缩（关键参数）
    # "--upx-dir", "./upx",  # UPX工具路径（upx.exe所在目录）
    # "--upx-exclude", "vcruntime140.dll",  # 排除系统DLL，避免签名验证失败
    # "--upx-exclude", "msvcp140.dll",      # 微软C++运行时，建议排除
]

# ===================== 【核心功能】自动检测打包模式 =====================
def get_build_mode_and_target():
    """
    自动检测打包模式：
    -F (单文件) → 资源复制到 dist/ 根目录
    -D (单目录) → 资源复制到 dist/APP_NAME/ 子目录
    """
    args = PYI_ARGS
    is_one_file = "-F" in args or "--onefile" in args
    is_one_dir = "-D" in args or "--onedir" in args

    if is_one_file:
        mode = "单文件模式"
        target_path = "./dist"
    elif is_one_dir:
        mode = "单目录模式"
        target_path = os.path.join("./dist", APP_NAME)
    else:
        # 默认单目录模式
        mode = "默认单目录模式"
        target_path = os.path.join("./dist", APP_NAME)
    return mode, target_path

# 自动获取模式和目标复制路径
BUILD_MODE, TARGET_COPY_PATH = get_build_mode_and_target()

VERSION_TUPLE = (MAJOR, MINOR, PATCH, BUILD)
VERSION_STR = f"{MAJOR}.{MINOR}.{PATCH}.{BUILD}"

# ===================== 版本文件生成 =====================
TEMPLATE = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={VERSION_TUPLE},
    prodvers={VERSION_TUPLE},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'FileDescription', u'{FILE_DESC}'),
        StringStruct(u'FileVersion', u'{VERSION_STR}'),
        StringStruct(u'InternalName', u'{APP_NAME}'),
        StringStruct(u'LegalCopyright', u'{COPYRIGHT}'),
        StringStruct(u'OriginalFilename', u'{EXE_NAME}'),
        StringStruct(u'ProductName', u'{APP_NAME}'),
        StringStruct(u'ProductVersion', u'{VERSION_STR}')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""

try:
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(TEMPLATE)
    print(f"✅ [1/5] 版本文件生成成功: {VERSION_FILE} (v{VERSION_STR})")
except Exception as e:
    print(f"❌ 生成版本文件失败: {e}")
    sys.exit(1)

# ===================== 清理旧文件 =====================
def clean_folder(path):
    if os.path.exists(path):
        try:
            shutil.rmtree(path)
            print(f"   ✔ 已清理: {path}")
            return True
        except PermissionError:
            print(f"   ⚠ 无法清理 '{path}' (文件被占用)，跳过...")
            return False
        except Exception as e:
            print(f"   ⚠ 清理 '{path}' 出错: {e}，跳过...")
            return False
    print(f"   ℹ 目录不存在，无需清理: {path}")
    return True

print(f"🧹 [2/5] 正在清理旧文件...")
clean_folder("./build")
clean_folder("./dist")

# ===================== 启动PyInstaller打包 =====================
print(f"🚀 [3/5] 当前打包模式：{BUILD_MODE}")
print(f"🚀 正在启动 PyInstaller 打包...")
command = [sys.executable, "-m", "PyInstaller"] + PYI_ARGS + [MAIN_SCRIPT]

try:
    if not os.path.exists(MAIN_SCRIPT):
        raise FileNotFoundError(f"未找到主程序文件: {MAIN_SCRIPT}")
        
    result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
    print(f"✅ [4/5] 编译成功！")
except subprocess.CalledProcessError as e:
    print(f"❌ 打包失败 (错误码: {e.returncode})")
    print(f"错误信息: {e.stderr}")
    sys.exit(1)
except FileNotFoundError as e:
    print(f"❌ {e}")
    print("请先安装依赖: pip install pyinstaller")
    sys.exit(1)

# ===================== 【自动适配】复制资源文件 =====================
def copy_files_to_dist():
    print(f"📦 [5/5] 正在复制资源文件到 → {TARGET_COPY_PATH}")

    for item in NEED_FILES:
        src_path = item
        dst_path = os.path.join(TARGET_COPY_PATH, item)

        if not os.path.exists(src_path):
            print(f"   ⚠ 跳过不存在的资源: {src_path}")
            continue

        os.makedirs(os.path.dirname(dst_path), exist_ok=True)

        try:
            if os.path.isdir(src_path):
                if os.path.exists(dst_path):
                    shutil.rmtree(dst_path)
                shutil.copytree(src_path, dst_path)
                print(f"   ✔ 复制文件夹: {item}")
            else:
                shutil.copy2(src_path, dst_path)
                print(f"   ✔ 复制文件: {item}")
        except Exception as e:
            print(f"   ❌ 复制失败 {item}: {e}")

copy_files_to_dist()

# ===================== 清理临时文件 =====================
if os.path.exists(VERSION_FILE):
    os.remove(VERSION_FILE)
    print(f"\n🧹 已清理临时版本文件: {VERSION_FILE}")

print(f"\n🎉 打包完成！程序目录：\n{os.path.abspath(TARGET_COPY_PATH)}")