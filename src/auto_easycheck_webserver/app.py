from flask import Flask, render_template, request, redirect, url_for
from waitress import serve
import os
import json
import time
import threading
import signal
from datetime import datetime
import atexit

app = Flask(__name__)

# 存储运行实例的数据
instances_file = "cache/instances.json"
# 日志目录路径（相对于运行目录）
logs_dir = "log"
# 操作日志文件路径
operation_log_file = os.path.join(logs_dir, "main.log")

# 内存中追踪运行中的线程（线程对象不可序列化）
_runtime = {}  # {instance_id: {"thread": Thread, "stop_event": Event, "restart_count": int, "name": str, "url": str}}
_runtime_lock = threading.Lock()
_stop_monitor = threading.Event()  # 通知监控线程退出

# 确保日志目录存在
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)


def log_operation(action, detail=""):
    """记录操作日志到main.log"""
    try:
        # 获取真实的客户端IP（支持反向代理），无请求上下文时用回退值
        try:
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                client_ip = forwarded_for.split(",")[0].strip()
            elif request.headers.get("X-Real-IP"):
                client_ip = request.headers.get("X-Real-IP")
            elif request.headers.get("CF-Connecting-IP"):
                client_ip = request.headers.get("CF-Connecting-IP")
            elif request.headers.get("X-Forwarded"):
                client_ip = request.headers.get("X-Forwarded")
            else:
                client_ip = request.remote_addr or "0.0.0.0"
        except RuntimeError:
            client_ip = "0.0.0.0"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"{timestamp}  [INFO]  [{client_ip}] {action}"
        if detail:
            log_message += f" - {detail}"
        log_message += "\n"

        with open(operation_log_file, "a", encoding="utf-8") as f:
            f.write(log_message)
    except Exception as e:
        print(f"记录操作日志失败: {e}")


def reset_instances_file():
    """启动时清空实例文件（线程状态无法跨进程恢复）"""
    cache_dir = os.path.dirname(instances_file)
    if cache_dir and not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    with open(instances_file, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)


reset_instances_file()


def load_instances():
    if os.path.exists(instances_file):
        with open(instances_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_instances(instances):
    with open(instances_file, "w", encoding="utf-8") as f:
        json.dump(instances, f, ensure_ascii=False, indent=2)


def get_instance_logs(name, lines=10):
    log_file = os.path.join(logs_dir, f"{name}.log")
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                logs = f.readlines()
                logs = [log.strip() for log in logs if log.strip()]
                return logs[-lines:] if len(logs) > lines else logs
        except Exception:
            pass
    return ["暂无日志"]


def _run_instance(url, log_name, stop_event):
    """在子线程中运行 auto_easycheck，支持通过 stop_event 停止"""
    from auto_easycheck import create_driver, auto_click

    driver = create_driver()
    try:
        while not stop_event.is_set():
            auto_click(driver, url, log_name=log_name)
            # 每秒检查一次 stop_event，最多等待 60 秒进入下一轮
            for _ in range(60):
                if stop_event.is_set():
                    break
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        driver.quit()


def _monitor_instances():
    """后台监控：检测意外停止的实例，自动重启最多3次，仍失败则删除"""
    while not _stop_monitor.is_set():
        # 每 10 秒检查一轮
        if _stop_monitor.wait(10):
            break

        with _runtime_lock:
            to_restart = []
            to_delete = []
            for instance_id, rt in list(_runtime.items()):
                if not rt["thread"].is_alive():
                    if rt["restart_count"] < 3:
                        to_restart.append(instance_id)
                    else:
                        to_delete.append(instance_id)

            for instance_id in to_restart:
                rt = _runtime[instance_id]
                rt["restart_count"] += 1
                print(f"实例 [{rt['name']}] 意外停止，第 {rt['restart_count']}/3 次重启...")
                new_stop_event = threading.Event()
                new_thread = threading.Thread(
                    target=_run_instance,
                    args=(rt["url"], rt["name"], new_stop_event),
                    daemon=True,
                )
                new_thread.start()
                rt["thread"] = new_thread
                rt["stop_event"] = new_stop_event

            for instance_id in to_delete:
                rt = _runtime.pop(instance_id, None)
                if rt:
                    print(f"实例 [{rt['name']}] 重启3次均失败（可能URL错误），已自动删除")

        # 在锁外清理持久化文件
        for instance_id in to_delete:
            instances = load_instances()
            if instance_id in instances:
                del instances[instance_id]
                save_instances(instances)


def _shutdown():
    """优雅关闭：通知所有实例停止，等待线程退出，清理浏览器进程"""
    if _shutdown.done:
        return
    _shutdown.done = True
    print("正在关闭所有实例...")
    _stop_monitor.set()  # 停止监控线程
    items = list(_runtime.items())
    if not items:
        print("没有运行中的实例。")
        return
    for _, rt in items:
        rt["stop_event"].set()
    # 等待线程结束（最多等 10 秒，避免 hang 死）
    for _, rt in items:
        rt["thread"].join(timeout=10)
        if rt["thread"].is_alive():
            # 仍活着 → 强制 kill 浏览器及 driver 进程（pkill 默认只杀同用户进程）
            try:
                import subprocess
                subprocess.run(["pkill", "-f", "msedgedriver"], capture_output=True)
                subprocess.run(["pkill", "-f", "chromedriver"], capture_output=True)
                subprocess.run(["pkill", "-f", "chrome"], capture_output=True)
                subprocess.run(["pkill", "-f", "msedge"], capture_output=True)
            except FileNotFoundError:
                print("警告: pkill 未安装，跳过强制清理浏览器进程")
    _runtime.clear()
    print("所有实例已关闭。")


_shutdown.done = False


def _handle_sigterm(sig, frame):
    """SIGTERM 处理器：即使 _shutdown 抛异常也确保进程退出"""
    try:
        _shutdown()
    finally:
        os._exit(0)


atexit.register(_shutdown)
signal.signal(signal.SIGTERM, _handle_sigterm)
signal.signal(signal.SIGINT, _handle_sigterm)

# 启动后台监控线程（自动重启意外停止的实例）
_monitor_thread = threading.Thread(target=_monitor_instances, daemon=True)
_monitor_thread.start()


@app.route("/")
def index():
    instances = load_instances()

    for instance_id, instance in instances.items():
        with _runtime_lock:
            rt = _runtime.get(instance_id)
        if rt and rt["thread"].is_alive():
            instance["running"] = True
            instance["logs"] = get_instance_logs(instance["name"], 3)
        else:
            instance["running"] = False
            instance["logs"] = ["已停止"]

    save_instances(instances)
    log_operation("访问首页", f"当前实例数量: {len(instances)}")
    return render_template("index.html", instances=instances)


@app.route("/create", methods=["GET", "POST"])
def create_instance():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        url = request.form.get("url", "").strip()

        if not name or not url:
            return render_template("create.html", error="名称和URL不能为空")

        instances = load_instances()
        instance_id = str(int(time.time()))

        try:
            stop_event = threading.Event()
            thread = threading.Thread(
                target=_run_instance,
                args=(url, name, stop_event),
                daemon=True,
            )
            thread.start()

            instances[instance_id] = {
                "id": instance_id,
                "name": name,
                "url": url,
                "running": True,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "logs": [f"实例启动成功", f"开始监控: {url}"],
            }
            with _runtime_lock:
                _runtime[instance_id] = {
                    "thread": thread,
                    "stop_event": stop_event,
                    "restart_count": 0,
                    "name": name,
                    "url": url,
                }

            save_instances(instances)
            log_operation("创建实例", f"实例名: {name}, URL: {url}")
            return redirect(url_for("index"))
        except Exception as e:
            print(f"启动失败: {e}")
            return render_template("create.html", error=f"启动失败: {str(e)}")

    return render_template("create.html")


@app.route("/instance/<instance_id>")
def instance_detail(instance_id):
    instances = load_instances()
    instance = instances.get(instance_id)

    if not instance:
        return redirect(url_for("index"))

    instance["full_logs"] = get_instance_logs(instance["name"], 50)
    log_operation("查看实例详情", f"实例名: {instance['name']}, URL: {instance['url']}")
    return render_template("instance_detail.html", instance=instance)


@app.route("/stop/<instance_id>", methods=["POST"])
def stop_instance(instance_id):
    instances = load_instances()
    instance = instances.get(instance_id)

    if instance:
        with _runtime_lock:
            rt = _runtime.pop(instance_id, None)
        if rt:
            rt["stop_event"].set()

        if instance_id in instances:
            del instances[instance_id]
            save_instances(instances)
            log_operation("停止实例", f"实例名: {instance['name']}, URL: {instance['url']}")

    return redirect(url_for("index"))


@app.route("/api/status")
def api_status():
    instances = load_instances()

    for instance_id, instance in instances.items():
        with _runtime_lock:
            rt = _runtime.get(instance_id)
        if rt and rt["thread"].is_alive():
            instance["running"] = True
        else:
            instance["running"] = False

    save_instances(instances)
    return {"status": "ok", "instances": instances}


if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=5000, threads=2)
