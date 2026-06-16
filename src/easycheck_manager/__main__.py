# __main__.py

import os
import sys
import platform
import subprocess
from easycheck_manager.lib.webdriver_manager import WebDriverManager

if __name__ == '__main__':

    wd = WebDriverManager()
    wd.start()

    if platform.system() == 'Windows':
        subprocess.run("auto_easycheck.exe")
    else:
        print("auto_easycheck.exe 是 Windows 程序，Linux 下跳过。")