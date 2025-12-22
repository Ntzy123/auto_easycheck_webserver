from flask import Flask, render_template, request, redirect, url_for
import subprocess
import psutil
import os
import json
import time
from datetime import datetime

app = Flask(__name__)

# 存储运行实例的数据
instances_file = 'instances.json'
# 日志目录路径
logs_dir = os.path.join(os.path.dirname(__file__), 'log')

# 确保日志目录存在
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# 启动时重置instances.json，清理残留的实例数据
def reset_instances_file():
    if os.path.exists(instances_file):
        try:
            # 检查是否有实际运行的进程
            with open(instances_file, 'r', encoding='utf-8') as f:
                instances = json.load(f)
            
            # 过滤掉实际还在运行的进程
            active_instances = {}
            for instance_id, instance in instances.items():
                if 'pid' in instance:
                    try:
                        process = psutil.Process(instance['pid'])
                        if process.is_running():
                            # 进程仍在运行，保留该实例
                            active_instances[instance_id] = instance
                    except:
                        # 进程不存在，跳过
                        pass
            
            # 如果所有进程都已停止，则清空文件
            if not active_instances:
                with open(instances_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
                print("已重置instances.json文件")
            else:
                # 保存仍在运行的实例
                with open(instances_file, 'w', encoding='utf-8') as f:
                    json.dump(active_instances, f, ensure_ascii=False, indent=2)
                print(f"保留 {len(active_instances)} 个仍在运行的实例")
                
        except Exception as e:
            print(f"重置instances.json时出错: {e}")
            # 如果文件损坏或读取失败，直接重置为空
            with open(instances_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

# 应用启动时执行重置
reset_instances_file()

# 加载实例数据
def load_instances():
    if os.path.exists(instances_file):
        with open(instances_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# 保存实例数据
def save_instances(instances):
    with open(instances_file, 'w', encoding='utf-8') as f:
        json.dump(instances, f, ensure_ascii=False, indent=2)

# 获取实例的日志文件内容
def get_instance_logs(name, lines=10):
    log_file = os.path.join(logs_dir, f"{name}.log")
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = f.readlines()
                # 返回最后几行，去除空行
                logs = [log.strip() for log in logs if log.strip()]
                return logs[-lines:] if len(logs) > lines else logs
        except:
            pass
    return ["暂无日志"]

@app.route('/')
def index():
    instances = load_instances()
    
    # 更新运行状态和日志
    for instance_id, instance in instances.items():
        if 'pid' in instance:
            try:
                process = psutil.Process(instance['pid'])
                instance['running'] = process.is_running()
                # 获取真实的日志文件内容
                instance['logs'] = get_instance_logs(instance['name'], 3)
            except:
                instance['running'] = False
                instance['logs'] = ["进程已停止"]
    
    save_instances(instances)
    
    return render_template('index.html', instances=instances)

@app.route('/create', methods=['GET', 'POST'])
def create_instance():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        url = request.form.get('url', '').strip()
        
        if not name or not url:
            return render_template('create.html', error='名称和URL不能为空')
        
        instances = load_instances()
        
        # 生成实例ID
        instance_id = str(int(time.time()))
        
        # 启动真实的auto_easycheck.exe程序
        try:
            exe_path = os.path.join('app', 'auto_easycheck.exe')
            if not os.path.exists(exe_path):
                return render_template('create.html', error='auto_easycheck.exe文件不存在')
            
            # 使用--name和--url参数启动程序
            process = subprocess.Popen([exe_path, '--name', name, '--url', url])
            
            instances[instance_id] = {
                'id': instance_id,
                'name': name,
                'url': url,
                'pid': process.pid,
                'running': True,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'logs': [f"进程启动成功 - PID: {process.pid}", f"开始监控: {url}"]
            }
            
            save_instances(instances)
            return redirect(url_for('index'))
            
        except Exception as e:
            print(f"启动失败: {e}")
            return render_template('create.html', error=f'启动失败: {str(e)}')
    
    return render_template('create.html')

@app.route('/instance/<instance_id>')
def instance_detail(instance_id):
    instances = load_instances()
    instance = instances.get(instance_id)
    
    if not instance:
        return redirect(url_for('index'))
    
    # 获取完整的真实日志
    instance['full_logs'] = get_instance_logs(instance['name'], 50)
    
    return render_template('instance_detail.html', instance=instance)

@app.route('/stop/<instance_id>', methods=['POST'])
def stop_instance(instance_id):
    instances = load_instances()
    instance = instances.get(instance_id)
    
    if instance and 'pid' in instance:
        try:
            process = psutil.Process(instance['pid'])
            process.terminate()
            process.wait(timeout=5)  # 等待进程结束
        except:
            pass
        
        # 删除实例
        if instance_id in instances:
            del instances[instance_id]
            save_instances(instances)
    
    return redirect(url_for('index'))

@app.route('/api/status')
def api_status():
    instances = load_instances()
    
    # 更新所有实例状态
    for instance_id, instance in instances.items():
        if 'pid' in instance:
            try:
                process = psutil.Process(instance['pid'])
                instance['running'] = process.is_running()
            except:
                instance['running'] = False
    
    save_instances(instances)
    
    return {
        'status': 'ok',
        'instances': instances
    }

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)