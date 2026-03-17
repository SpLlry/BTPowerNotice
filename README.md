# BTPowerNotice

一款轻松查看电脑蓝牙电量的工具

---

> *托盘*

> ---

> <img width="342" height="250" alt="image" src="https://github.com/user-attachments/assets/609624dd-9339-45b5-9310-14a891398d8f" />
> ---

> *任务栏(0.1.3发布)*

> ---

> <img width="398" height="92" alt="Snipaste_2026-03-17_17-19-54" src="https://github.com/user-attachments/assets/9b14bc1b-5e66-4b70-a814-66d231e17485" />

---

## 功能

实时显示已连接的设备电量信息

## 其他说明

最新版开发在win11机器上，win11基本没什么大问题，win10因为没时间装虚拟机，暂时未进行实测，建议使用0.1.2版本

## 开发

安装库

```
pip install -r requirements.txt
```

打包命令

```
pyinstaller -F -w -i .\icon\icon.ico --add-data "icon;icon" --version-file=version_info.txt main.py
```