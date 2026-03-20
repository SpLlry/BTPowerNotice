# -*- coding: utf-8 -*-
import os
import shutil  # 【重要】已添加缺失的导入
import subprocess
import sys

# ================= 【配置区】请在此修改 =================
# 1. 版本信息
MAJOR = 0
MINOR = 1
PATCH = 4
BUILD = 0

# 2. 程序信息
APP_NAME = "BTPowerNotice"
FILE_DESC = "一款轻松查看电脑蓝牙电量的工具"
EXE_NAME = "BTPowerNotice.exe"
COPYRIGHT = "Copyright © 2026 Spllry"
VERSION_FILE = "version_info.txt"  # 修正了变量名，保持前后一致

# 【新增】打包后需要复制到 dist 目录的文件/文件夹列表
NEED_FILES = [
    "icon",
    "ui",
    "config"
]

# 3. 打包配置
MAIN_SCRIPT = "main.py"
PYI_ARGS = [
    "-F",
    "-w",
    "-n", APP_NAME,
    "-i", ".\\icon\\icon.ico",
    "--add-data", "icon;icon",
    "--version-file", VERSION_FILE
]
# =========================================================

VERSION_TUPLE = (MAJOR, MINOR, PATCH, BUILD)
VERSION_STR = f"{MAJOR}.{MINOR}.{PATCH}.{BUILD}"
DIST_FOLDER = "./dist"

# --- 1. 生成 version-info.txt ---
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


# --- 2. 清理旧的 build/dist 目录 ---
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

# --- 3. 自动运行 PyInstaller ---
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


# --- 4. 【新增】复制 NEED_FILES 到 dist 目录 ---
def copy_files_to_dist():
    print(f"📦 [5/5] 正在复制依赖文件到 {DIST_FOLDER}...")

    for item in NEED_FILES:
        src_path = item
        dst_path = os.path.join(DIST_FOLDER, item)

        if not os.path.exists(src_path):
            print(f"   ⚠ 源文件不存在，跳过: {src_path}")
            continue

        # 确保目标目录的父文件夹存在
        dst_parent_dir = os.path.dirname(dst_path)
        if dst_parent_dir and not os.path.exists(dst_parent_dir):
            os.makedirs(dst_parent_dir, exist_ok=True)

        try:
            if os.path.isdir(src_path):
                # 如果是文件夹，且目标已存在，先删除旧的
                if os.path.exists(dst_path):
                    shutil.rmtree(dst_path)
                shutil.copytree(src_path, dst_path)
                print(f"   ✔ 已复制文件夹: {item}")
            else:
                # 如果是文件
                shutil.copy2(src_path, dst_path)
                print(f"   ✔ 已复制文件: {item}")
        except Exception as e:
            print(f"   ❌ 复制失败 ({item}): {e}")


# 执行复制
copy_files_to_dist()
print(f"\n🎉 全部流程完成！请查看 {DIST_FOLDER} 文件夹。")
