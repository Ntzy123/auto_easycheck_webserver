# get-easycheck-url API 文档

## 概述

`get-easycheck-url` 库提供两个函数，均通过手机号和密码自动完成 OAuth 登录流程：

| 函数 | 返回 |
|------|------|
| `get_easycheck_url()` | 完整可访问的 easycheck URL |
| `get_access_token()` | 仅 `accessToken` 的 JWT 字符串 |

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
def get_easycheck_url(mobile: str, password: str) -> str:
    ...

def get_access_token(mobile: str, password: str) -> str:
    ...
```

两者参数、异常完全相同，仅返回值不同。

### 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `mobile` | `str` | 手机号 |
| `password` | `str` | 密码 |

### 返回值

| 函数 | 返回 |
|------|------|
| `get_easycheck_url()` | `https://rm.vankeservice.com/easycheck/#/nightAnswer?accessToken=<JWT>` |
| `get_access_token()` | 原始 JWT 字符串（不含 URL 前缀与参数名） |

### 异常

| 异常 | 说明 |
|------|------|
| `requests.HTTPError` | HTTP 请求失败（非 2xx/3xx） |
| `RuntimeError` | 登录失败或响应解析异常 |

## 使用示例

### 获取完整 URL

```python
from get_easycheck_url import get_easycheck_url

url = get_easycheck_url("138xxxxxxxx", "your_password")
print(url)
```

### 仅获取 accessToken

```python
from get_easycheck_url import get_access_token

token = get_access_token("138xxxxxxxx", "your_password")
print(token)
# eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
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

`get_access_token()` 返回的就是上面 URL 中 `accessToken` 的值（不重新发起额外请求，只在内部流程结束后提取）。

> 注意：`accessToken` 位于 URL 的 fragment（`#` 之后），因此 `get_easycheck_url()` 的返回值用 `urlparse().query` 取不到，需要用 `get_access_token()` 或自行解析 fragment。

## 依赖

- Python >= 3.9
- requests >= 2.31.0
