from flask import Flask, jsonify, render_template, request, redirect, url_for
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
_runtime = {}  # {instance_id: {"thread": Thread, "stop_event": Event, "restart_count": int, "name": str, "url": str, "driver_pid": int | None}}
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


def _kill_browser_processes(instance_id=None):
    """跨平台强制清理浏览器和 driver 进程。

    Args:
        instance_id: 如果提供，优先精准杀该实例对应的 driver 进程树；
                     否则只杀 msedgedriver.exe（不碰用户自开的 msedge）。
    """
    import subprocess
    import platform

    driver_pid = None
    if instance_id:
        with _runtime_lock:
            rt = _runtime.get(instance_id)
            if rt:
                driver_pid = rt.get("driver_pid")

    if platform.system() == "Windows":
        if driver_pid:
            # 精准杀：只杀本项目启动的 driver 及其子进程（msedge）
            subprocess.run(["taskkill", "/F", "/PID", str(driver_pid), "/T"], capture_output=True)
        else:
            # 兜底：没有 PID 时只杀 msedgedriver，不碰用户自开的 msedge
            subprocess.run(["taskkill", "/F", "/IM", "msedgedriver.exe"], capture_output=True)
    else:
        if driver_pid:
            subprocess.run(["kill", "-9", str(driver_pid)], capture_output=True)
        else:
            try:
                subprocess.run(["pkill", "-f", "msedgedriver"], capture_output=True)
            except FileNotFoundError:
                pass


def _run_instance(url, log_name, stop_event, instance_id):
    """在子线程中运行自动夜答，支持通过 stop_event 停止"""
    from auto_easycheck import create_driver, auto_click

    driver = create_driver()
    # 记录 driver 进程 PID，用于精准清理
    try:
        driver_pid = driver.service.process.pid if driver.service else None
    except Exception:
        driver_pid = None
    with _runtime_lock:
        if instance_id in _runtime:
            _runtime[instance_id]["driver_pid"] = driver_pid

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
                    args=(rt["url"], rt["name"], new_stop_event, instance_id),
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
    for instance_id, rt in items:
        rt["stop_event"].set()
    # 等待线程结束（最多等 35 秒，覆盖 auto_click 内部等待）
    for instance_id, rt in items:
        rt["thread"].join(timeout=35)
        if rt["thread"].is_alive():
            # 仍活着 → 强制 kill 浏览器及 driver 进程
            _kill_browser_processes(instance_id)
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


def _start_instance(name, url):
    """启动一个自动夜答实例并注册到 _runtime 和持久化文件。

    Returns:
        (instance_id, instance_dict) 成功
        (None, error_message) 失败
    """
    instances = load_instances()
    instance_id = str(int(time.time()))

    try:
        stop_event = threading.Event()
        thread = threading.Thread(
            target=_run_instance,
            args=(url, name, stop_event, instance_id),
            daemon=True,
        )
        thread.start()

        instance_data = {
            "id": instance_id,
            "name": name,
            "url": url,
            "running": True,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "logs": [f"实例启动成功", f"开始监控: {url}"],
        }
        instances[instance_id] = instance_data

        with _runtime_lock:
            _runtime[instance_id] = {
                "thread": thread,
                "stop_event": stop_event,
                "restart_count": 0,
                "name": name,
                "url": url,
                "driver_pid": None,
            }

        save_instances(instances)
        log_operation("创建实例", f"实例名: {name}, URL: {url}")
        return instance_id, instance_data
    except Exception as e:
        print(f"启动失败: {e}")
        return None, str(e)


@app.route("/create", methods=["GET", "POST"])
def create_instance():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        url = request.form.get("url", "").strip()

        if not name or not url:
            return render_template("create.html", error="名称和URL不能为空")

        instance_id, result = _start_instance(name, url)
        if instance_id:
            return redirect(url_for("index"))
        else:
            return render_template("create.html", error=f"启动失败: {result}")

    return render_template("create.html")


@app.route("/api/create", methods=["POST"])
def api_create_instance():
    """API: 通过 JSON 请求体创建自动夜答实例。

    Request body (JSON):
        {
            "instance_name": "my-instance",
            "easycheck_url": "https://example.com/check"
        }
    """
    if not request.is_json:
        return jsonify({"code": 1, "success": False, "msg": "请求体必须是 JSON"}), 400

    data = request.get_json()
    name = (data.get("instance_name") or "").strip()
    url = (data.get("easycheck_url") or "").strip()

    if not name:
        return jsonify({"code": 1, "success": False, "msg": "instance_name 不能为空"}), 400
    if not url:
        return jsonify({"code": 1, "success": False, "msg": "easycheck_url 不能为空"}), 400

    instance_id, result = _start_instance(name, url)
    if instance_id:
        return jsonify({"code": 0, "success": True, "msg": "请求成功", "instance_id": instance_id}), 201
    else:
        return jsonify({"code": 2, "success": False, "msg": f"启动失败: {result}"}), 500


@app.route("/api/get-easycheck-url", methods=["POST"])
def api_get_easycheck_url():
    """API: 通过手机号和密码获取 easycheck 授权 URL。

    Request body (JSON):
        {
            "mobile": "138xxxxxxxx",
            "password": "your_password"
        }
    """
    if not request.is_json:
        return jsonify({"code": 1, "success": False, "msg": "请求体必须是 JSON"}), 400

    data = request.get_json()
    mobile = (data.get("mobile") or "").strip()
    password = (data.get("password") or "").strip()

    if not mobile:
        return jsonify({"code": 1, "success": False, "msg": "mobile 不能为空"}), 400
    if not password:
        return jsonify({"code": 1, "success": False, "msg": "password 不能为空"}), 400

    try:
        from get_easycheck_url import get_easycheck_url
        url = get_easycheck_url(mobile, password)
    except Exception as e:
        log_operation("获取 easycheck URL 失败", f"手机号: {mobile}, 错误: {e}")
        return jsonify({"code": 2, "success": False, "msg": f"获取失败: {e}"}), 500

    log_operation("获取 easycheck URL", f"手机号: {mobile}")
    return jsonify({
        "code": 0,
        "success": True,
        "msg": "请求成功",
        "easycheck_url": url,
    })


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
            # 等待线程自然退出（最多等 70 秒，覆盖 auto_click 中 60s wait）
            rt["thread"].join(timeout=70)
            if rt["thread"].is_alive():
                # 线程卡死 → 强制杀浏览器进程
                _kill_browser_processes(instance_id)

        if instance_id in instances:
            del instances[instance_id]
            save_instances(instances)
            log_operation("停止实例", f"实例名: {instance['name']}, URL: {instance['url']}")

    return redirect(url_for("index"))


@app.route("/api/status", methods=["GET", "POST"])
def api_status():
    instances = load_instances()

    # POST 请求支持通过 id 筛选
    target_id = None
    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            target_id = (data.get("id") or "").strip()
        else:
            return jsonify({"code": 1, "msg": "请求体必须是 JSON", "status": "error"}), 400

    for instance_id, instance in instances.items():
        with _runtime_lock:
            rt = _runtime.get(instance_id)
        if rt and rt["thread"].is_alive():
            instance["running"] = True
        else:
            instance["running"] = False

    save_instances(instances)

    if target_id:
        if target_id in instances:
            return {"code": 0, "msg": "请求成功", "status": "ok", "instance": instances[target_id]}
        else:
            return {"code": 1, "msg": "实例不存在", "status": "error", "instance": None}

    return {"code": 0, "msg": "请求成功", "status": "ok", "instances": instances}


if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=5000, threads=2)
