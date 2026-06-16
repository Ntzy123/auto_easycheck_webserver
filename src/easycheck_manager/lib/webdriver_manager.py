# webdriver_manager.py

import os
import sys
import time
import platform
import re
import shutil
import subprocess
import zipfile
import requests


class WebDriverManager:
    def __init__(self):
        self.is_windows = platform.system() == 'Windows'

        if self.is_windows:
            # Windows 路径
            self.EDGE_PATH = os.environ.get(
                'EDGE_PATH',
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
            )
            self.BASE_DIR = os.environ.get(
                'WEBDRIVER_DIR',
                r"D:\Program Files\WebDriver"
            )
            self.OLD_FOLDER_NAME = "edgedriver_win64"
            self.ZIP_FILENAME = "edgedriver_win64.zip"
            self.DRIVER_EXE = "msedgedriver.exe"
            self.EDGEDRIVER_PATH = os.path.join(
                self.BASE_DIR, self.OLD_FOLDER_NAME, self.DRIVER_EXE
            )
        else:
            # Linux 路径
            self.EDGE_PATH = self._find_edge_linux()
            self.CACHE_DIR = "/tmp/msedgedriver"
            self.EDGEDRIVER_PATH = "/usr/local/bin/msedgedriver"

        self.edge_version = None

    # ── 辅助：Linux 下查找 Edge 可执行文件 ──────────────────────────

    def _find_edge_linux(self):
        """Linux 下查找 Edge 可执行文件路径"""
        for name in ["microsoft-edge", "microsoft-edge-stable"]:
            path = shutil.which(name)
            if path:
                return path
        return None

    # ── 版本号获取 ──────────────────────────────────────────────────

    def get_file_version(self, name, path):
        """跨平台获取文件版本号"""
        if self.is_windows:
            return self._get_file_version_win(name, path)
        else:
            return self._get_file_version_linux(name, path)

    def _get_file_version_win(self, name, path):
        """Windows：使用 win32api 获取文件版本"""
        import win32api
        if not os.path.exists(path):
            return f"没有找到 {name} -> {path}"
        try:
            info = win32api.GetFileVersionInfo(path, '\\')
            ms = info['FileVersionMS']
            ls = info['FileVersionLS']
            version = (
                f"{win32api.HIWORD(ms)}.{win32api.LOWORD(ms)}."
                f"{win32api.HIWORD(ls)}.{win32api.LOWORD(ls)}"
            )
            return version
        except Exception as e:
            return f"读取 {name} 文件版本时出错: {e}"

    def _get_file_version_linux(self, name, path):
        """Linux：通过 --version 参数获取版本号"""
        if not path or (not os.path.exists(path) and not shutil.which(path)):
            return f"没有找到 {name}"
        try:
            result = subprocess.run(
                [path, '--version'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return f"执行 {name} --version 失败"
            match = re.search(r'(\d+\.\d+\.\d+\.\d+)', result.stdout.strip())
            if match:
                return match.group(1)
            return f"无法解析 {name} 版本: {result.stdout.strip()}"
        except Exception as e:
            return f"读取 {name} 版本时出错: {e}"

    # ── 设置 PATH 环境变量 ─────────────────────────────────────────

    def set_permanent_path(self):
        """Windows 下设置 EdgeDriver 到 PATH，Linux 无需设置"""
        if self.is_windows:
            self._set_permanent_path_win(os.path.dirname(self.EDGEDRIVER_PATH))

    def _set_permanent_path_win(self, driver_dir):
        """Windows：通过注册表设置 PATH"""
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, 'Environment',
            0, winreg.KEY_ALL_ACCESS
        )
        try:
            try:
                current_path, _ = winreg.QueryValueEx(key, "PATH")
            except FileNotFoundError:
                current_path = ""
            if driver_dir in current_path:
                print("EdgeDriver 环境变量已配置")
                return
            final_path = f"{current_path};{driver_dir}" if current_path else driver_dir
            winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, final_path)
            print(f"EdgeDriver 环境变量已生效: {driver_dir}")
            print("请重启终端以生效")
        finally:
            winreg.CloseKey(key)

    # ── 下载 / 解压 EdgeDriver ─────────────────────────────────────

    def download_edgedriver(self):
        """跨平台下载并安装最新版 EdgeDriver"""
        # 根据平台选择压缩包名称
        zip_name = "edgedriver_win64.zip" if self.is_windows else "edgedriver_linux64.zip"
        URL_TEMPLATE = f"https://msedgedriver.microsoft.com/{self.edge_version}/{zip_name}"

        if self.is_windows:
            self._download_edgedriver_win(URL_TEMPLATE)
        else:
            self._download_edgedriver_linux(URL_TEMPLATE)

    def _download_edgedriver_win(self, url):
        """Windows 版下载与安装"""
        DOWNLOAD_PATH = os.path.join(self.BASE_DIR, self.ZIP_FILENAME)
        OLD_DRIVER_PATH = os.path.join(self.BASE_DIR, self.OLD_FOLDER_NAME)

        print(f"--- EdgeDriver 更新工具 (版本: {self.edge_version}) ---")

        # 步骤 1：确保目录存在
        try:
            os.makedirs(self.BASE_DIR, exist_ok=True)
            print(f"目标目录已就绪: {self.BASE_DIR}")
        except Exception as e:
            print(f"无法创建目录，请检查权限: {e}")
            sys.exit(1)

        # 步骤 2：下载
        self._download_file(url, DOWNLOAD_PATH)

        # 步骤 3：删除旧的 Driver 文件夹
        print(f"正在检查并删除旧文件夹: {OLD_DRIVER_PATH}")
        if os.path.exists(OLD_DRIVER_PATH):
            try:
                shutil.rmtree(OLD_DRIVER_PATH)
                print("旧 EdgeDriver 文件夹删除成功。")
            except Exception as e:
                print(f"删除旧文件夹失败: {e}")
                sys.exit(1)
        else:
            print("旧 Driver 文件夹不存在，跳过删除。")

        # 步骤 4：解压
        print(f"正在解压 {DOWNLOAD_PATH} 到 {OLD_DRIVER_PATH}...")
        try:
            shutil.unpack_archive(DOWNLOAD_PATH, OLD_DRIVER_PATH)
            print("Driver 文件解压成功。")
        except Exception as e:
            print(f"解压失败: {e}")
            sys.exit(1)

        # 步骤 5：清理压缩包
        self._cleanup_zip(DOWNLOAD_PATH)

        print("\nEdgeDriver 已完成更新！")

    def _download_edgedriver_linux(self, url):
        """Linux 版：下载 zip 到 /usr/local/bin，解压出 msedgedriver 二进制，清理 zip"""
        zip_path = os.path.join(self.CACHE_DIR, "edgedriver_linux64.zip")
        driver_exe = "msedgedriver"

        print(f"--- EdgeDriver 更新工具 (版本: {self.edge_version}) ---")

        # 步骤 1：确保目录存在
        try:
            os.makedirs(self.CACHE_DIR, exist_ok=True)
            print(f"目标目录已就绪: {self.CACHE_DIR}")
        except Exception as e:
            print(f"无法创建目录: {e}")
            sys.exit(1)

        # 步骤 2：下载
        self._download_file(url, zip_path)

        # 步骤 3：从 zip 中直接解压 msedgedriver 到 CACHE_DIR
        print(f"正在从压缩包中提取 msedgedriver...")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for info in zf.infolist():
                    # 跳过目录项，只匹配文件名（兼容有/无目录前缀的情况）
                    if info.is_dir():
                        continue
                    if os.path.basename(info.filename) == driver_exe:
                        # 去掉目录前缀，只保留文件名
                        info.filename = driver_exe
                        zf.extract(info, self.CACHE_DIR)
                        break
                else:
                    print(f"压缩包中未找到 {driver_exe}")
                    sys.exit(1)

            # 复制到最终位置 /usr/local/bin/
            src = os.path.join(self.CACHE_DIR, driver_exe)
            shutil.copy2(src, self.EDGEDRIVER_PATH)
            os.chmod(self.EDGEDRIVER_PATH, 0o755)
            print(f"msedgedriver 已安装至 {self.EDGEDRIVER_PATH}")
        except PermissionError:
            print("权限不足！请使用 sudo 运行此脚本")
            sys.exit(1)
        except Exception as e:
            print(f"解压失败: {e}")
            sys.exit(1)

        # 步骤 4：清理压缩包
        self._cleanup_zip(zip_path)

        print("\nEdgeDriver 已完成更新！")

    def _download_file(self, url, save_path):
        """下载文件到指定路径"""
        print(f"正在从 {url} 下载...")
        try:
            response = requests.get(url, stream=True, timeout=30)
            if response.status_code != 200:
                print(f"下载失败，HTTP 状态码: {response.status_code}")
                sys.exit(1)
            with open(save_path, 'wb') as file:
                shutil.copyfileobj(response.raw, file)
            print(f"下载成功并保存至: {save_path}")
        except requests.exceptions.RequestException as e:
            print(f"网络请求失败: {e}")
            sys.exit(1)

    def _cleanup_zip(self, zip_path):
        """清理下载的压缩包"""
        print(f"正在清理压缩包: {zip_path}")
        try:
            os.remove(zip_path)
            print("压缩包清理完成。")
        except Exception as e:
            print(f"清理失败，请手动删除 {zip_path}: {e}")

    # ── 主入口 ──────────────────────────────────────────────────────

    def start(self):
        print("--- EdgeDriver Manager 启动 ---")
        self.set_permanent_path()

        # 获取 Edge 版本号
        self.edge_version = self.get_file_version("Edge", self.EDGE_PATH)
        print(f"Edge 版本号: {self.edge_version}")

        # 获取 EdgeDriver 版本号
        edgedriver_version = self.get_file_version("EdgeDriver", self.EDGEDRIVER_PATH)
        print(f"EdgeDriver 版本号: {edgedriver_version}")

        # 版本不匹配则下载
        if self.edge_version != edgedriver_version:
            self.download_edgedriver()
        else:
            print("版本号一致")
            for _ in range(50):
                print("=", end='')
                sys.stdout.flush()
                time.sleep(0.01)
            time.sleep(0.3)
            os.system('cls' if self.is_windows else 'clear')

