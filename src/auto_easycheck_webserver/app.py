from flask import Flask, render_template, request, redirect, url_for
import os
import json
import time
import threading
from datetime import datetime

app = Flask(__name__)

# 存储运行实例的数据
instances_file = "cache/instances.json"
# 日志目录路径（相对于运行目录）
logs_dir = "log"
# 操作日志文件路径
operation_log_file = os.path.join(logs_dir, "main.log")

# 内存中追踪运行中的线程（线程对象不可序列化）
_runtime = {}  # {instance_id: {"thread": Thread, "stop_event": Event}}

# 确保日志目录存在
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)


def log_operation(action, detail=""):
    """记录操作日志到main.log"""
    try:
        # 获取真实的客户端IP（支持反向代理）
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
            client_ip = request.remote_addr

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
    from auto_easycheck import setup_logging, create_driver, auto_click

    setup_logging(log_name)
    driver = create_driver()
    try:
        while not stop_event.is_set():
            auto_click(driver, url)
            # 每秒检查一次 stop_event，最多等待 60 秒进入下一轮
            for _ in range(60):
                if stop_event.is_set():
                    break
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        driver.quit()


@app.route("/")
def index():
    instances = load_instances()

    for instance_id, instance in instances.items():
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
            _runtime[instance_id] = {"thread": thread, "stop_event": stop_event}

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
        rt = _runtime.get(instance_id)
        if rt:
            rt["stop_event"].set()
            _runtime.pop(instance_id, None)

        if instance_id in instances:
            del instances[instance_id]
            save_instances(instances)
            log_operation("停止实例", f"实例名: {instance['name']}, URL: {instance['url']}")

    return redirect(url_for("index"))


@app.route("/api/status")
def api_status():
    instances = load_instances()

    for instance_id, instance in instances.items():
        rt = _runtime.get(instance_id)
        if rt and rt["thread"].is_alive():
            instance["running"] = True
        else:
            instance["running"] = False

    save_instances(instances)
    return {"status": "ok", "instances": instances}


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
