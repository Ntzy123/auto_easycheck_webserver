# get-easycheck-url API 文档

## 概述

`get_easycheck_url()` 是 `get-easycheck-url` 库提供的一个核心函数，用于通过手机号和密码自动完成 OAuth 登录流程，最终获取 easycheck 授权的可访问 URL。

## 安装

```bash
pip install get-easycheck-url
```

或从本地源码安装：

```bash
pip install -e .
```

## 函数签名

```python
def get_easycheck_url(
    mobile: str,
    password: str,
) -> str:
    ...
```

### 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `mobile` | `str` | 手机号 |
| `password` | `str` | 密码 |

### 返回值

返回 `str`，格式为 `https://rm.vankeservice.com/easycheck/#/nightAnswer?accessToken=<JWT>`。

### 异常

| 异常 | 说明 |
|------|------|
| `requests.HTTPError` | HTTP 请求失败（非 2xx/3xx） |
| `RuntimeError` | 登录失败或响应解析异常 |

## 使用示例

### 基本用法

```python
from get_easycheck_url import get_easycheck_url

url = get_easycheck_url("138xxxxxxxx", "your_password")
print(url)
```

### 异常处理

```python
from get_easycheck_url import get_easycheck_url

try:
    url = get_easycheck_url("138xxxxxxxx", "wrong_password")
except RuntimeError as e:
    print(f"登录失败：{e}")
```

## 返回值说明

返回的 URL 可直接在浏览器中打开。URL 中的 `accessToken` 参数即是 easycheck 的 JWT token，也可用于后续的 API 鉴权。

示例返回值：

```
https://rm.vankeservice.com/easycheck/#/nightAnswer?accessToken=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

## 依赖

- Python >= 3.9
- requests >= 2.31.0
