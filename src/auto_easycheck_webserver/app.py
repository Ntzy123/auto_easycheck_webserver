from flask import Flask, render_template, request, redirect, url_for
import subprocess
import psutil
import os
import json
import time
from datetime import datetime

app = Flask(__name__)

# 存储运行实例的数据
instances_file = "cache/instances.json"
# 日志目录路径（相对于运行目录）
logs_dir = "log"
# 操作日志文件路径
operation_log_file = os.path.join(logs_dir, "main.log")

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
    """启动时重置instances.json，清理残留的实例数据"""
    cache_dir = os.path.dirname(instances_file)
    if cache_dir and not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    if not os.path.exists(instances_file):
        with open(instances_file, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        return

    try:
        with open(instances_file, "r", encoding="utf-8") as f:
            instances = json.load(f)

        active_instances = {}
        for instance_id, instance in instances.items():
            if "pid" in instance:
                try:
                    process = psutil.Process(instance["pid"])
                    if process.is_running():
                        active_instances[instance_id] = instance
                except Exception:
                    pass

        if not active_instances:
            with open(instances_file, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            print("已重置instances.json文件")
        else:
            with open(instances_file, "w", encoding="utf-8") as f:
                json.dump(active_instances, f, ensure_ascii=False, indent=2)
            print(f"保留 {len(active_instances)} 个仍在运行的实例")
    except Exception as e:
        print(f"重置instances.json时出错: {e}")
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


@app.route("/")
def index():
    instances = load_instances()

    for instance_id, instance in instances.items():
        if "pid" in instance:
            try:
                process = psutil.Process(instance["pid"])
                instance["running"] = process.is_running()
                instance["logs"] = get_instance_logs(instance["name"], 3)
            except Exception:
                instance["running"] = False
                instance["logs"] = ["进程已停止"]

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
            exe_path = os.path.join("app", "auto_easycheck.exe")
            if not os.path.exists(exe_path):
                return render_template("create.html", error="auto_easycheck.exe文件不存在")

            process = subprocess.Popen([exe_path, "--name", name, "--url", url])

            instances[instance_id] = {
                "id": instance_id,
                "name": name,
                "url": url,
                "pid": process.pid,
                "running": True,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "logs": [f"进程启动成功 - PID: {process.pid}", f"开始监控: {url}"],
            }

            save_instances(instances)
            log_operation("创建实例", f"实例名: {name}, URL: {url}, PID: {process.pid}")
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

    if instance and "pid" in instance:
        try:
            def terminate_process_tree(pid):
                try:
                    parent = psutil.Process(pid)
                    children = parent.children(recursive=True)
                    for child in children:
                        try:
                            child.terminate()
                        except psutil.NoSuchProcess:
                            pass
                    if children:
                        psutil.wait_procs(children, timeout=3)
                    parent.terminate()
                    parent.wait(timeout=3)
                except psutil.NoSuchProcess:
                    pass

            terminate_process_tree(instance["pid"])
        except Exception as e:
            print(f"终止进程时出错: {e}")

        if instance_id in instances:
            del instances[instance_id]
            save_instances(instances)
            log_operation("停止实例", f"实例名: {instance['name']}, URL: {instance['url']}")

    return redirect(url_for("index"))


@app.route("/api/status")
def api_status():
    instances = load_instances()

    for instance_id, instance in instances.items():
        if "pid" in instance:
            try:
                process = psutil.Process(instance["pid"])
                instance["running"] = process.is_running()
            except Exception:
                instance["running"] = False

    save_instances(instances)
    return {"status": "ok", "instances": instances}


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
