# 自动易查Web服务管理平台 (easycheck-webserver)

轻松夜答管理平台 - 基于 Flask 的 Web 服务，用于监控和管理 EasyCheck 实例。

## 快速开始

```bash
# 创建虚拟环境并安装依赖
make setup

# 或手动安装
python -m venv .venv
.venv\Scripts\pip install -e .
```

## 运行

```bash
make run

# 或手动运行
python -m easycheck_webserver
```

服务默认监听 `0.0.0.0:3624`。

## 测试

```bash
make test
```

## 项目结构

```
src/easycheck_webserver/     # 源码包
  __init__.py                # 包入口，main()
  __main__.py                # python -m 入口
  app.py                     # Flask Web 应用
  webdriver_manager.py       # EdgeDriver 管理
  templates/                 # Jinja2 模板
tests/                       # 测试目录
```
