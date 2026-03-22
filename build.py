# -*- coding: utf-8 -*-
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from setting import settings

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
EXE_NAME = f"{APP_NAME}.exe"
COPYRIGHT = f"Copyright © {settings.COPYRIGHT_YEAR} {settings.APP_AUTHOR}"
VERSION_FILE = "version_info.txt"

NEED_FILES = ["icon", "ui", "config"]

MAIN_SCRIPT = "main.py"
PYI_ARGS = [
    "-F",
    "-w",
    "-n",APP_NAME,
    "-i",
    ".\\icon\\icon.ico",
    "--add-data",
    "icon;icon",
    "--version-file",
    VERSION_FILE,
]

VERSION_TUPLE = (MAJOR, MINOR, PATCH, BUILD)
VERSION_STR = f"{MAJOR}.{MINOR}.{PATCH}.{BUILD}"
DIST_FOLDER = "./dist"

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


def clean_folder(path):
    if os.path.exists(path):
        try:
            shutil.rmtree(path)
            print(f"   ✔ 已清理: {path}")
            return True
        except PermissionError:
            print(f"   ⚠ 无法清理 '{path}' (文件被占用或权限不足)，跳过清理...")
            return False
        except Exception as e:
            print(f"   ⚠ 清理 '{path}' 时出错: {e}，跳过清理...")
            return False
    else:
        print(f"   ℹ 目录不存在，无需清理: {path}")
        return True


print(f"🧹 [2/5] 正在清理旧文件...")
clean_folder("./build")
clean_folder("./dist")

print(f"🚀 [3/5] 正在启动 PyInstaller...")
command = [sys.executable, "-m", "PyInstaller"] + PYI_ARGS + [MAIN_SCRIPT]

try:
    result = subprocess.run(command, check=True)
    print(f"✅ [4/5] 编译成功！")
except subprocess.CalledProcessError as e:
    print(f"❌ 打包失败 (错误码: {e.returncode})")
    sys.exit(1)
except FileNotFoundError:
    print("❌ 未找到 PyInstaller，请先安装: pip install pyinstaller")
    sys.exit(1)


def copy_files_to_dist():
    print(f"📦 [5/5] 正在复制依赖文件到 {DIST_FOLDER}...")

    for item in NEED_FILES:
        src_path = item
        dst_path = os.path.join(DIST_FOLDER, item)

        if not os.path.exists(src_path):
            print(f"   ⚠ 源文件不存在，跳过: {src_path}")
            continue

        dst_parent_dir = os.path.dirname(dst_path)
        if dst_parent_dir and not os.path.exists(dst_parent_dir):
            os.makedirs(dst_parent_dir, exist_ok=True)

        try:
            if os.path.isdir(src_path):
                if os.path.exists(dst_path):
                    shutil.rmtree(dst_path)
                shutil.copytree(src_path, dst_path)
                print(f"   ✔ 已复制文件夹: {item}")
            else:
                shutil.copy2(src_path, dst_path)
                print(f"   ✔ 已复制文件: {item}")
        except Exception as e:
            print(f"   ❌ 复制失败 ({item}): {e}")


copy_files_to_dist()
print(f"\n🎉 全部流程完成！请查看 {DIST_FOLDER} 文件夹。")
