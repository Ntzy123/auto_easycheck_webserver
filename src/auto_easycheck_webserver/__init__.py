"""轻松夜答管理平台 - EasyCheck Web Server."""

from easycheck_manager.lib.webdriver_manager import WebDriverManager
from auto_easycheck_webserver.app import app


def main():
    wdmanager = WebDriverManager()
    wdmanager.start()
    try:
        app.run(host="0.0.0.0", port=3624)
    finally:
        from auto_easycheck_webserver.app import _shutdown
        _shutdown()
