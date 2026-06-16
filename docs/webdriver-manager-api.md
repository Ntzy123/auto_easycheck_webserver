# WebDriverManager API 参考

> 模块路径：`easycheck_manager`（推荐） / `easycheck_manager.lib.webdriver_manager`

`WebDriverManager` 是项目的核心类，提供 EdgeDriver 的全生命周期管理：自动检测 Edge 版本 → 比对现有 Driver → 下载匹配版本 → 安装并配置环境。

---

## 导入

```python
from easycheck_manager import WebDriverManager

manager = WebDriverManager()
manager.start()
```

## 构造函数

```python
WebDriverManager()
```

初始化时自动检测操作系统并设置平台相关的默认路径。

### 实例属性

| 属性 | 类型 | 说明 | Windows 默认值 | Linux 默认值 |
|------|------|------|----------------|--------------|
| `is_windows` | `bool` | 当前是否为 Windows | `True` | `False` |
| `EDGE_PATH` | `str` | Edge 浏览器可执行文件路径 | `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` | `shutil.which("microsoft-edge")` 结果 |
| `EDGEDRIVER_PATH` | `str` | EdgeDriver 最终安装路径 | `{BASE_DIR}\edgedriver_win64\msedgedriver.exe` | `/usr/local/bin/msedgedriver` |
| `BASE_DIR` | `str` | EdgeDriver 存放目录（仅 Windows） | `D:\Program Files\WebDriver` | — |
| `CACHE_DIR` | `str` | 下载缓存目录（仅 Linux） | — | `/tmp/msedgedriver` |
| `edge_version` | `str \| None` | 最后一次获取到的 Edge 版本号，初始为 `None` | — | — |

> **Windows 环境变量覆盖**：设置 `EDGE_PATH` 可自定义 Edge 路径，设置 `WEBDRIVER_DIR` 可自定义驱动存放目录。

---

## 公共方法

### `start()`

一键执行完整流程：配置 PATH → 获取 Edge 版本 → 获取 EdgeDriver 版本 → 按需下载。

```python
wdmanager = WebDriverManager()
wdmanager.start()
```

**执行步骤**：

1. 调用 `set_permanent_path()` 配置环境变量
2. 调用 `get_file_version("Edge", EDGE_PATH)` 获取 Edge 版本号，存入 `edge_version`
3. 调用 `get_file_version("EdgeDriver", EDGEDRIVER_PATH)` 获取 Driver 版本号
4. 若两个版本号不一致，调用 `download_edgedriver()` 下载并安装
5. 若一致，打印进度条后清屏

---

### `get_file_version(name, path)`

获取指定文件的版本号。

```python
version = manager.get_file_version("Edge", r"C:\Program Files\...\msedge.exe")
# 返回: "149.0.4022.69"
```

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 文件显示名称（仅用于错误提示） |
| `path` | `str` | 文件路径 |

**返回值**：版本号字符串（如 `"149.0.4022.69"`），若失败则返回以中文描述的错误信息字符串。

**平台差异**：

| 平台 | 实现方式 |
|------|----------|
| Windows | 调用 `win32api.GetFileVersionInfo()` 读取 PE 文件头 |
| Linux | 执行 `{path} --version`，正则提取 `(\d+\.\d+\.\d+\.\d+)` |

---

### `set_permanent_path()`

将 EdgeDriver 所在目录添加到系统 PATH 中。

- **Windows**：通过注册表 `HKCU\Environment` 写入，重启终端生效。若已存在则跳过。
- **Linux**：无操作（`/usr/local/bin` 默认已在 PATH 中）。

---

### `download_edgedriver()`

下载与当前 Edge 版本匹配的 EdgeDriver 并安装。

```python
manager.edge_version = "149.0.4022.69"
manager.download_edgedriver()
```

> **前置条件**：`edge_version` 属性必须已设置（可通过 `start()` 或手动调用 `get_file_version("Edge", ...)` 设置）。

**Windows 下载流程**：

```
步骤 1  mkdir -p D:\Program Files\WebDriver
步骤 2  下载 https://msedgedriver.microsoft.com/{version}/edgedriver_win64.zip
步骤 3  删除旧目录 D:\Program Files\WebDriver\edgedriver_win64\
步骤 4  解压到 D:\Program Files\WebDriver\edgedriver_win64\
步骤 5  删除压缩包
```

**Linux 下载流程**：

```
步骤 1  mkdir -p /tmp/msedgedriver
步骤 2  下载 https://msedgedriver.microsoft.com/{version}/edgedriver_linux64.zip
步骤 3  从 zip 解压出 msedgedriver → /tmp/msedgedriver/msedgedriver
步骤 4  copy2 → /usr/local/bin/msedgedriver
步骤 5  chmod 755 /usr/local/bin/msedgedriver
步骤 6  删除 /tmp/msedgedriver/edgedriver_linux64.zip
```

> **权限**：Linux 下 `/usr/local/bin/` 写入需要 `sudo` 权限，若权限不足会退出并提示使用 `sudo` 重新运行。

---

## 私有/保护方法

以下方法以下划线开头，通常不直接调用，但了解其行为有助于理解整体逻辑。

### `_find_edge_linux()`

```python
path = manager._find_edge_linux()
# 返回: "/usr/bin/microsoft-edge" 或 None
```

依次尝试 `shutil.which()` 查找 `microsoft-edge` 和 `microsoft-edge-stable`，返回第一个找到的路径。

### `_get_file_version_win(name, path)`

Windows 专用。使用 `win32api.GetFileVersionInfo` 从 PE 文件头读取版本信息。

### `_get_file_version_linux(name, path)`

Linux 专用。执行 `{path} --version` 并解析输出中的版本号。

### `_set_permanent_path_win(driver_dir)`

Windows 专用。通过注册表 `HKCU\Environment` 设置用户级 PATH 变量。

### `_download_edgedriver_win(url)`

Windows 专用。执行 Windows 下的下载、解压与安装流程。

### `_download_edgedriver_linux(url)`

Linux 专用。执行 Linux 下的下载、解压、复制与安装流程。

### `_download_file(url, save_path)`

通用 HTTP 文件下载。使用 `requests.get(stream=True)` 流式下载到本地文件。

### `_cleanup_zip(zip_path)`

通用 zip 压缩包清理。删除指定文件，失败时仅打印警告不退出。

---

## CLI 入口

通过包模块直接运行：

```bash
python -m easycheck_manager
```

或通过已安装的命令行工具：

```bash
easycheck-manager
```

CLI 执行流程：

1. 创建 `WebDriverManager` 实例
2. 调用 `start()` 完成 EdgeDriver 管理
3. （仅 Windows）启动 `auto_easycheck.exe`

---

## 从源码运行

```bash
git clone <repo-url>
cd easycheck_manager
pip install -e .
make run        # 或: python -m easycheck_manager
make test       # 运行测试
```
