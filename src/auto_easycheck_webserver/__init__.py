"""轻松夜答管理平台 - EasyCheck Web Server."""

import socket
from waitress import serve
from easycheck_manager import WebDriverManager
from auto_easycheck_webserver.app import app


def _get_lan_ip():
    """获取本机局域网 IP 地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "未知"


def main():
    wdmanager = WebDriverManager()
    wdmanager.start()
    try:
        lan_ip = _get_lan_ip()
        print(f"EasyCheck Web Server 已启动")
        print(f"  本地访问:   http://127.0.0.1:3624")
        print(f"  局域网访问: http://{lan_ip}:3624")
        serve(app, host="0.0.0.0", port=3624, threads=2)
    finally:
        from auto_easycheck_webserver.app import _shutdown
        _shutdown()
