# splunk-skill — 详细配置与 API 参考

本文档为 `splunk_skill.py` 提供完整的配置说明、API 参考和错误处理指南。

---

## 配置参数全览

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `SPLUNK_HOST` | str | `"192.168.1.100"` | Splunk 主机 IP 或域名，不含 `http://` |
| `SPLUNK_PORT` | int | `8089` | 管理端口（REST API 端口，非 Web 端口 8000）|
| `SPLUNK_USERNAME` | str | `"admin"` | Basic Auth 用户名 |
| `SPLUNK_PASSWORD` | str | `""` | Basic Auth 密码 |
| `SPLUNK_TOKEN` | str | `""` | Bearer Token（优先级高于用户名/密码）|
| `SPLUNK_APP` | str | `"search"` | KV Store 操作绑定的 App 命名空间 |
| `VERIFY_SSL` | bool | `False` | 是否验证 SSL 证书（自签名证书需设 False）|
| `REQUEST_TIMEOUT` | int | `60` | 单次 HTTP 请求超时（秒）|
| `SEARCH_TIMEOUT` | int | `120` | 等待异步搜索作业完成的超时（秒）|

### 认证方式选择

```python
# 方式 1：Bearer Token（推荐，更安全）
SPLUNK_TOKEN = "eyJraWQiOiJzcGx1bmsuc2Vj..."

# 方式 2：Basic Auth（用户名 + 密码）
SPLUNK_USERNAME = "admin"
SPLUNK_PASSWORD = "yourpassword"
SPLUNK_TOKEN    = ""   # 留空则自动使用 Basic Auth
```

---

## API 参考

### `health_check()`

**描述**：检查与 Splunk 的连接，返回已安装应用列表。用于验证配置正确性。

**调用端点**：`GET /services/apps/local`

**参数**：无

**返回结构**：
```json
{
  "success": true,
  "data": {
    "total_apps": 30,
    "apps": [
      {"name": "search", "label": "Search & Reporting", "version": "10.2.2", "enabled": true},
      {"name": "splunk_httpinput", "label": "Splunk HEC", "version": "1.3.2", "enabled": true}
    ]
  }
}
```

---

### `current_user()`

**描述**：返回当前已认证用户的身份和权限详细信息。

**调用端点**：`GET /services/authentication/current-context`

**参数**：无

**返回结构**：
```json
{
  "success": true,
  "data": {
    "username": "admin",
    "roles": ["admin", "power"],
    "capabilities": ["search", "rest_apps_management"],
    "real_name": "",
    "email": "admin@example.com",
    "default_app": "launcher"
  }
}
```

---

### `list_users()`

**描述**：检索所有 Splunk 用户。需要 `admin` 角色。

**调用端点**：`GET /services/authentication/users`

**参数**：无

**返回结构**：
```json
{
  "success": true,
  "data": {
    "total": 2,
    "users": [
      {
        "name": "admin",
        "real_name": "",
        "email": "changeme@example.com",
        "roles": ["admin", "power"],
        "default_app": "launcher",
        "locked_out": false
      }
    ]
  }
}
```

---

### `list_indexes()`

**描述**：列出当前凭据可访问的所有 Splunk 索引。

**调用端点**：`GET /services/data/indexes`

**参数**：无

**返回结构**：
```json
{
  "success": true,
  "data": {
    "total": 26,
    "indexes": [
      {
        "name": "main",
        "total_event_count": 123456,
        "current_db_size_mb": 512,
        "max_total_data_size_mb": 500000,
        "home_path": "$SPLUNK_DB/main/db",
        "frozen_time_period_in_secs": 188697600,
        "disabled": false
      }
    ]
  }
}
```

---

### `get_index_info(index_name)`

**描述**：获取特定索引的详细配置和统计信息。

**调用端点**：`GET /services/data/indexes/{index_name}`

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `index_name` | str | ✅ | 索引名称，如 `"main"`、`"_internal"` |

**返回结构**：
```json
{
  "success": true,
  "data": {
    "name": "_audit",
    "total_event_count": 5000000,
    "current_db_size_mb": 863,
    "max_total_data_size_mb": 500000,
    "home_path": "$SPLUNK_DB/audit/db",
    "cold_path": "$SPLUNK_DB/audit/colddb",
    "thawed_path": "$SPLUNK_DB/audit/thaweddb",
    "frozen_time_period_in_secs": 188697600,
    "min_time": "2025-03-03T16:40:09+0800",
    "max_time": "2026-04-10T00:19:39+0800",
    "disabled": false,
    "is_internal": true
  }
}
```

---

### `indexes_and_sourcetypes()`

**描述**：返回所有索引及其关联 sourcetype 的映射。使用 `| tstats` 查询实现。

**调用端点**：`POST /services/search/jobs`（异步搜索）

**执行的 SPL**：
```
| tstats count WHERE index=* BY index, sourcetype
```

**参数**：无

**返回结构**：
```json
{
  "success": true,
  "data": {
    "total_combinations": 45,
    "mapping": {
      "_internal": ["splunkd", "scheduler", "metrics"],
      "main": ["syslog", "access_combined"],
      "_audit": ["audittrail"]
    }
  }
}
```

> **注意**：此方法执行聚合搜索，耗时取决于数据量，可能需要数十秒。

---

### `search_splunk(query, earliest_time, latest_time, max_count, exec_mode)`

**描述**：执行用户提供的 SPL 查询，支持异步轮询模式(`"async"`)和一键同步阻塞模式(`"oneshot"`)。

**调用端点**：`POST /services/search/jobs` → `GET /services/search/jobs/{sid}/results`

**参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `query` | str | 必填 | SPL 语句，如 `index=main error \| stats count by host` |
| `earliest_time` | str | `"-60m"` | 起始时间（相对：`-1h`、`-7d`；绝对：`2026-01-01T00:00:00`）|
| `latest_time` | str | `"now"` | 结束时间 |
| `max_count` | int | `100` | 最大返回结果条数（上限受 `SEARCH_TIMEOUT` 约束）|
| `exec_mode` | str | `"async"` | 执行模式，支持 `"async"` (作业轮询，大数据) 和 `"oneshot"` (等待结果，少量数据) |

**返回结构**：
```json
{
  "success": true,
  "data": {
    "sid": "1712345678.1",
    "count": 5,
    "results": [
      {"_time": "2026-04-10T01:00:00+0800", "_raw": "...", "host": "server01"},
      {"_time": "2026-04-10T01:00:01+0800", "_raw": "...", "host": "server02"}
    ]
  }
}
```

---

### `list_saved_searches()`

**描述**：列出所有已保存的搜索（包括 Alert 和 Report）。

**调用端点**：`GET /services/saved/searches`

**参数**：无

**返回结构**：
```json
{
  "success": true,
  "data": {
    "total": 54,
    "searches": [
      {
        "name": "Failed Login Alert",
        "search": "index=_audit action=login status=failure | stats count by user",
        "description": "检测登录失败次数异常",
        "is_scheduled": true,
        "cron_schedule": "*/5 * * * *",
        "is_alert": true,
        "dispatch_app": "search",
        "author": "admin"
      }
    ]
  }
}
```

---

### `list_kvstore_collections()`

**描述**：检索当前 App（`SPLUNK_APP`）命名空间下所有 KV Store 集合。

**调用端点**：`GET /servicesNS/nobody/{app}/storage/collections/config`

**参数**：无

**返回结构**：
```json
{
  "success": true,
  "data": {
    "total": 5,
    "collections": [
      {
        "name": "threat_intel",
        "app": "search",
        "owner": "admin",
        "fields": {"ip": "string", "score": "number"},
        "accelerated": {}
      }
    ]
  }
}
```

---

### `create_kvstore_collection(collection_name)`

**描述**：创建新的 KV Store 集合。集合名称需唯一，已存在时返回错误。

**调用端点**：`POST /servicesNS/nobody/{app}/storage/collections/config`

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `collection_name` | str | ✅ | 集合名称，建议使用下划线分隔，如 `threat_intel` |

**返回结构**：
```json
{
  "success": true,
  "data": {
    "collection_name": "threat_intel",
    "message": "集合 'threat_intel' 创建成功"
  }
}
```

---

### `delete_kvstore_collection(collection_name)`

**描述**：删除指定的 KV Store 集合及其所有数据。操作不可逆，需要管理员权限。

**调用端点**：`DELETE /servicesNS/nobody/{app}/storage/collections/config/{name}`

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `collection_name` | str | ✅ | 要删除的集合名称 |

**返回结构**：
```json
{
  "success": true,
  "data": {
    "collection_name": "threat_intel",
    "message": "集合 'threat_intel' 已成功删除"
  }
}
```

---

## 错误响应参考

所有方法失败时统一返回：
```json
{"success": false, "error": "<错误描述>"}
```

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| `连接失败: ...WinError 10061...` | Splunk 主机不可达 | 检查 `SPLUNK_HOST` 和 `SPLUNK_PORT` |
| `认证失败：用户名/密码或 Token 不正确` | HTTP 401 | 检查凭据配置 |
| `权限不足：需要管理员权限` | HTTP 403 | 使用具有 `admin` 角色的账户 |
| `索引 '{name}' 不存在` | HTTP 404 | 确认索引名称拼写正确 |
| `集合 '{name}' 已存在` | HTTP 409 | 集合名已被使用，换一个名称 |
| `搜索作业超时（>{n}s）` | 搜索执行时间过长 | 增大 `SEARCH_TIMEOUT` 或缩短时间范围 |
