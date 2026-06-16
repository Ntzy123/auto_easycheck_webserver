"""轻松夜答管理平台 - EasyCheck Web Server."""

from easycheck_webserver.webdriver_manager import WebDriverManager
from easycheck_webserver.app import app


def main():
    wd = WebDriverManager()
    wd.start()
    app.run(debug=True, host="0.0.0.0", port=3624)
