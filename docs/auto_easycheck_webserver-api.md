# auto-easycheck-webserver API

供其他项目或软件调用的 HTTP API，用于启动和管理自动夜答实例。

所有响应均包含 `code` 字段用于快速判断状态：

| code | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 参数错误 |
| 2 | 服务端异常 |

---

## 启动服务

```bash
auto-easycheck-webserver
```

服务默认监听 `http://0.0.0.0:5000`。

---

## 接口列表

### 创建实例

`POST /api/create`

创建一个新的自动夜答实例并立即启动。

**请求头：** `Content-Type: application/json`

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `instance_name` | string | 是 | 实例名称，用于标识和日志文件名 |
| `easycheck_url` | string | 是 | `auto-easycheck` 要自动答题的目标 URL |

**示例：**

```bash
curl -X POST http://localhost:5000/api/create \
  -H "Content-Type: application/json" \
  -d '{"instance_name": "monitor-douyin", "easycheck_url": "https://live.douyin.com/123456"}'
```

**成功响应 (201):**

```json
{
  "code": 0,
  "success": true,
  "msg": "请求成功",
  "instance_id": "1712345678"
}
```

**失败响应：**

| HTTP 状态码 | 场景 |
|---|---|
| 400 | 缺少 `instance_name` 或 `easycheck_url` |
| 500 | 启动实例时发生异常 |

```json
{
  "code": 1,
  "success": false,
  "msg": "instance_name 不能为空"
}
```

```json
{
  "code": 2,
  "success": false,
  "msg": "启动失败: ..."
}
```

---

### 查询实例状态

`GET /api/status`

查询所有实例。

`POST /api/status`

按 `id` 查询单个实例，不传 `id` 则返回全部实例。

**请求体（POST，可选）：** `Content-Type: application/json`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 否 | 实例 ID，不传则返回全部实例 |

**GET 示例：**

```bash
curl http://localhost:5000/api/status
```

**POST 示例（查单个）：**

```bash
curl -X POST http://localhost:5000/api/status \
  -H "Content-Type: application/json" \
  -d '{"id": "1712345678"}'
```

**GET / POST 不传 id 响应 (200):**

```json
{
  "code": 0,
  "msg": "请求成功",
  "status": "ok",
  "instances": {
    "1712345678": {
      "id": "1712345678",
      "name": "monitor-douyin",
      "url": "https://live.douyin.com/123456",
      "running": true,
      "created_at": "2026-07-07 04:00:00"
    }
  }
}
```

**POST 传 id 响应（实例存在，200）：**

```json
{
  "code": 0,
  "msg": "请求成功",
  "status": "ok",
  "instance": {
    "id": "1712345678",
    "name": "monitor-douyin",
    "url": "https://live.douyin.com/123456",
    "running": true,
    "created_at": "2026-07-07 04:00:00"
  }
}
```

**POST 传 id 响应（实例不存在，200）：**

```json
{
  "code": 1,
  "msg": "实例不存在",
  "status": "error",
  "instance": null
}
```

其中 `running: true` 表示实例正常运行中，`running: false` 表示已停止。

---

## 注意事项

- 服务重启后之前创建的实例**不会**自动恢复（线程状态无法跨进程保存），需重新调用 `/api/create` 创建
- 每个实例的浏览器进程使用 PID 精准终止，不会误杀其他 Edge 窗口
- 实例相关日志文件位于 `log/<instance_name>.log`，操作审计日志位于 `log/main.log`
