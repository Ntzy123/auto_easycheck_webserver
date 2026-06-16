# auto-easycheck API 参考

`auto-easycheck` 是一个一键自动答题的 Python 库，基于 Selenium 控制 Edge 浏览器完成轻松夜答任务。本文档面向将 auto-easycheck 作为 **pip 库集成** 的开发者。

---

## 安装

```bash
pip install auto-easycheck
```

依赖：Python >= 3.9，需要系统已安装 [Microsoft Edge 浏览器](https://www.microsoft.com/edge)。

---

## 快速使用

```python
from auto_easycheck import run

# 一行启动，自动循环答题
run(url="https://rm.vankeservice.com/api/easycheck/web/index?wkwebview=true&rurl=/nightAnswer")
```

---

## 公共 API

包级导出（`from auto_easycheck import ...`）：

| 函数 | 说明 |
|------|------|
| `run()` | **一键启动**（推荐），自动完成日志、浏览器、答题循环全流程 |
| `auto_click()` | 单次答题核心逻辑，需自行管理 driver |
| `create_driver()` | 创建预配置的 headless Edge 浏览器实例 |
| `setup_logging()` | 配置日志系统 |

---

### `run(url, log_name="auto_easycheck")`

一键启动答题循环，内部自动完成：配置日志 → 创建浏览器 → 循环答题（每 60 秒一次）→ 异常/中断自动清理。

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `url` | `str` | — | 轻松夜答网页完整 URL |
| `log_name` | `str` | `"auto_easycheck"` | 日志文件名称（不含路径），自动写入 `./log/<log_name>.log` |

**返回值：** 无。函数以无限循环方式运行，直到用户中断（Ctrl+C）或发生未捕获异常。

**示例：**

```python
from auto_easycheck import run

# 基本用法
run(url="https://example.com/nightAnswer")

# 自定义日志名
run(url="https://example.com/nightAnswer", log_name="my_project")

# 在子线程中运行（需自行处理信号）
import threading

t = threading.Thread(target=run, args=("https://example.com/nightAnswer",), daemon=True)
t.start()
```

---

### `auto_click(driver, url)`

执行单次答题操作：打开网页 → 等待题目加载 → 选择第一个选项 → 提交答案。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `driver` | `selenium.webdriver.Edge` | 已初始化的 Edge WebDriver 实例 |
| `url` | `str` | 轻松夜答网页完整 URL |

**返回值：** 无。

**抛出：** 可能抛出 Selenium 超时/元素未找到等异常，建议调用方自行 try/except。

**示例：**

```python
from auto_easycheck import auto_click, create_driver
from selenium.webdriver import Edge

driver = create_driver()
try:
    auto_click(driver, "https://example.com/nightAnswer")
finally:
    driver.quit()
```

---

### `create_driver() -> selenium.webdriver.Edge`

创建一个预配置的 **headless** Microsoft Edge 浏览器实例。配置包括：

- `--headless`：无头模式（不显示浏览器窗口）
- `--disable-gpu`：禁用 GPU 加速
- `--no-sandbox`：禁用沙盒模式

**参数：** 无。

**返回值：** `selenium.webdriver.Edge` 实例，可直接用于 `auto_click()`。

**示例：**

```python
from auto_easycheck import create_driver

driver = create_driver()
driver.get("https://example.com")
# ... 执行操作 ...
driver.quit()
```

---

### `setup_logging(name="auto_easycheck") -> str`

配置日志系统，同时输出到文件和控制台。日志格式：

```
2025-06-16  12:00:00  [INFO]  打开夜答网页
2025-06-16  12:00:05  [INFO]  提交答案
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | `str` | `"auto_easycheck"` | 日志文件名称（不含后缀），文件位于 `./log/<name>.log` |

**返回值：** `str` — 日志文件的完整路径。

**示例：**

```python
from auto_easycheck import setup_logging

log_path = setup_logging("my_task")
print(f"日志路径: {log_path}")  # ./log/my_task.log
```

---

## 进阶用法

### 自定义浏览器配置

```python
from auto_easycheck import auto_click, setup_logging
from selenium import webdriver
from selenium.webdriver.edge.options import Options

# 自定义浏览器选项
options = Options()
options.add_argument("--headless")
options.add_argument("--window-size=1920,1080")
# 不启用 --no-sandbox，保留更高安全性
driver = webdriver.Edge(options=options)

setup_logging("custom_driver")
try:
    auto_click(driver, "https://example.com/nightAnswer")
finally:
    driver.quit()
```

### 定时答题（非永久循环）

```python
from auto_easycheck import create_driver, auto_click
import time

driver = create_driver()
try:
    for _ in range(5):  # 只答 5 次
        auto_click(driver, "https://example.com/nightAnswer")
        time.sleep(60)
finally:
    driver.quit()
```

### 多任务场景

```python
from auto_easycheck import run
import threading

urls = [
    "https://example.com/room/1",
    "https://example.com/room/2",
]

threads = []
for i, url in enumerate(urls):
    t = threading.Thread(
        target=run,
        args=(url, f"room_{i}"),
        daemon=True,
    )
    t.start()
    threads.append(t)

for t in threads:
    t.join()
```

---

## CLI 命令

安装后可通过命令行调用：

```bash
# 交互式输入 URL
auto-easycheck

# 直接指定 URL
auto-easycheck -u "https://..."

# 指定日志名称
auto-easycheck -n "my_log"

# 组合使用
auto-easycheck -u "https://..." -n "my_log"
```

或通过 Python 模块方式运行：

```bash
python -m auto_easycheck -u "https://..."
```
