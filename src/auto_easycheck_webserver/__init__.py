"""轻松夜答管理平台 - EasyCheck Web Server."""

from waitress import serve
from easycheck_manager import WebDriverManager
from auto_easycheck_webserver.app import app


def main():
    wdmanager = WebDriverManager()
    wdmanager.start()
    try:
        print(f"EasyCheck Web Server 已启动：http://0.0.0.0:3624")
        serve(app, host="0.0.0.0", port=3624, threads=2)
    finally:
        from auto_easycheck_webserver.app import _shutdown
        _shutdown()
