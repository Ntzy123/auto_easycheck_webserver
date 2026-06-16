# easycheck_manager.py

import os
from selenium import webdriver
from selenium.webdriver.edge.service import Service

class EasycheckManager:
    def __init__(self):
        USER_DATA_ROOT = r".\Edge User Profile"
        new_profile_name = str
        TARGET_URL = "https://rm.vankeservice.com/api/easycheck/web/index?wkwebview=true&rurl=/nightAnswer"

# 4. 要添加的初始 Cookie 数据 (格式为 Selenium 所需的字典)
# 注意：'domain' 必须与 TARGET_URL 的域匹配，否则 Cookie 将无法被设置。
initial_cookie = {
    'name': 'session_id',        # Cookie 名称
    'value': 'a1b2c3d4e5f6g7h8', # Cookie 值
    'domain': '.example.com',    # 域（通常以点开头以包含子域）
    'path': '/',                 # 路径
    'secure': True,              # 是否仅通过 HTTPS 传输
    'httpOnly': True             # 是否仅能通过 HTTP 访问 (建议为 False，但通常由服务器设置)
}
# ----------------------------------------------------------------------