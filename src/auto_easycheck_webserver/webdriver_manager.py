# webdriver_manager.py

import os
import sys
import time
import winreg
import win32api
import requests
import shutil


class WebDriverManager:
    def __init__(self):
        self.EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        self.EDGEDRIVER_PATH = r"D:\Program Files\WebDriver\edgedriver_win64\msedgedriver.exe"

    def set_permanent_path(self):
        """设置EdgeDrive环境变量PATH"""
        path = r"D:\Program Files\WebDriver\edgedriver_win64"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS)
        try:
            try:
                current_path, _ = winreg.QueryValueEx(key, "PATH")
            except FileNotFoundError:
                current_path = ""
            if path in current_path:
                print("EdgeDrive环境变量已配置")
                return
            final_path = f"{current_path};{path}" if current_path else path
            winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, final_path)
            print(f"EdgeDrive环境变量已生效: {path}")
            print("请重启终端以生效\n\n")
        finally:
            winreg.CloseKey(key)

    def get_file_version(self, name, path):
        """获取指定文件的版本号"""
        if not os.path.exists(path):
            return f"没有找到{name} -> {path}"
        try:
            info = win32api.GetFileVersionInfo(path, "\\")
            ms = info["FileVersionMS"]
            ls = info["FileVersionLS"]
            version = f"{win32api.HIWORD(ms)}.{win32api.LOWORD(ms)}.{win32api.HIWORD(ls)}.{win32api.LOWORD(ls)}"
            return version
        except Exception as e:
            return f"读取{name}文件版本时出错: {e}"

    def download_edgedriver(self):
        """下载最新版EdgeDriver"""
        BASE_DIR = r"D:\Program Files\WebDriver"
        URL_TEMPLATE = f"https://msedgedriver.microsoft.com/{self.edge_version}/edgedriver_win64.zip"
        ZIP_FILENAME = "edgedriver_win64.zip"
        OLD_FOLDER_NAME = "edgedriver_win64"
        DOWNLOAD_PATH = os.path.join(BASE_DIR, ZIP_FILENAME)
        OLD_DRIVER_PATH = os.path.join(BASE_DIR, OLD_FOLDER_NAME)

        print(f"--- EdgeDriver 更新工具 (版本: {self.edge_version}) ---")

        try:
            os.makedirs(BASE_DIR, exist_ok=True)
            print(f"目标目录已就绪: {BASE_DIR}")
        except Exception as e:
            print(f"无法创建目录，请检查权限: {e}")
            sys.exit(1)

        print(f"正在从 {URL_TEMPLATE} 下载...")
        try:
            response = requests.get(URL_TEMPLATE, stream=True, timeout=10)
            if response.status_code != 200:
                print(f"下载失败，HTTP 状态码: {response.status_code}")
                sys.exit(1)
            with open(DOWNLOAD_PATH, "wb") as file:
                shutil.copyfileobj(response.raw, file)
            print(f"下载成功并保存至: {DOWNLOAD_PATH}")
        except requests.exceptions.RequestException as e:
            print(f"网络请求失败。请检查网络连接或URL。退出: {e}")
            sys.exit(1)

        print(f"正在检查并删除旧文件夹: {OLD_DRIVER_PATH}")
        if os.path.exists(OLD_DRIVER_PATH):
            try:
                shutil.rmtree(OLD_DRIVER_PATH)
                print("旧 EdgeDriver 文件夹删除成功。")
            except Exception as e:
                print(f"删除旧文件夹失败，请确保没有程序占用该文件夹。退出: {e}")
                sys.exit(1)
        else:
            print("旧 Driver 文件夹不存在，跳过删除。")

        print(f"正在解压 {DOWNLOAD_PATH} 到 {OLD_DRIVER_PATH}...")
        try:
            shutil.unpack_archive(DOWNLOAD_PATH, OLD_DRIVER_PATH)
            print("Driver 文件解压成功。")
        except Exception as e:
            print(f"解压失败: {e}")
            sys.exit(1)

        print(f"正在清理压缩包: {DOWNLOAD_PATH}")
        try:
            os.remove(DOWNLOAD_PATH)
            print("压缩包清理完成。")
        except Exception as e:
            print(f"清理失败，请手动删除 {DOWNLOAD_PATH}: {e}")

        print("\nEdgeDriver 已完成更新！")

    def start(self):
        print("--- EdgeDriver Manager 启动 ---")
        self.set_permanent_path()
        self.edge_version = self.get_file_version("Edge", self.EDGE_PATH)
        print(f"Edge 版本号：{self.edge_version}")
        edgedriver_version = self.get_file_version("EdgeDriver", self.EDGEDRIVER_PATH)
        print(f"EdgeDriver 版本号：{edgedriver_version}")

        if self.edge_version != edgedriver_version:
            self.download_edgedriver()
        else:
            print("版本号一致")
            for i in range(50):
                print("=", end="")
                sys.stdout.flush()
                time.sleep(0.01)
            time.sleep(0.3)
            os.system("cls")
