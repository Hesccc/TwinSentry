---
name: Splunk
description: Splunk 平台数据搜索与管理工具。支持执行 SPL 搜索、管理索引、查询用户信息及操作 KV Store，可供 AI Agent 灵活调用以完成日志分析和安全运营任务。
metadata:
  openclaw:
    requires:
      bins: [python3, pip]
    install:
      - id: pip
        kind: pip
        package: requests
        label: Install Python requests library
---

# splunk-skill — Splunk 平台搜索与管理

本 Skill 提供与 Splunk 平台 REST API（v10.2）的完整集成能力，封装了 11 个核心工具函数，适用于 AI Agent 框架（如 Dify、LangChain、OpenClaw 等）。

## 功能列表

| 方法 | 描述 |
|------|------|
| `health_check()` | 检查与 Splunk 的连接，返回已安装应用列表 |
| `current_user()` | 返回当前认证用户的身份和权限详细信息 |
| `list_users()` | 检索所有 Splunk 用户及其角色和状态 |
| `list_indexes()` | 列出可访问的所有 Splunk 索引 |
| `get_index_info(index_name)` | 获取特定索引的详细信息 |
| `indexes_and_sourcetypes()` | 返回所有索引及其 sourcetype 的映射关系 |
| `search_splunk(query, ...)` | 执行 SPL 搜索，支持时间范围和结果数限制 |
| `list_saved_searches()` | 列出所有保存的搜索作业 |
| `list_kvstore_collections()` | 检索所有 KV Store 集合 |
| `create_kvstore_collection(name)` | 创建新的 KV Store 集合 |
| `delete_kvstore_collection(name)` | 删除指定的 KV Store 集合 |

## 配置方式

在 `scripts/splunk_skill.py` 顶部 **「配置区」** 中修改以下参数：

```python
SPLUNK_HOST     = "192.168.1.100"   # Splunk 主机 IP 或域名
SPLUNK_PORT     = 8089              # 管理端口（默认 8089）
SPLUNK_USERNAME = "admin"           # 用户名（Basic Auth）
SPLUNK_PASSWORD = "your-password"   # 密码（Basic Auth）
SPLUNK_TOKEN    = ""                # Bearer Token（填写后优先于用户名/密码）
SPLUNK_APP      = "search"          # App 上下文（用于 KV Store 操作）
VERIFY_SSL      = False             # 是否验证 SSL 证书
```

> **认证优先级**：填写 `SPLUNK_TOKEN` 后将优先使用 Bearer Token 认证；留空则使用 Basic Auth（用户名/密码）。

## 快速使用示例

```python
import sys
sys.path.insert(0, '/path/to/skills/splunk/scripts')
from splunk_skill import SplunkSkill

skill = SplunkSkill()

# 1. 检查连接
result = skill.health_check()
print(result)

# 2. 执行 SPL 搜索 (Async模式，默认)
result = skill.search_splunk(
    query="index=_internal | head 10",
    earliest_time="-15m",
    latest_time="now",
    max_count=10
)
print(result)

# 2.1 执行同步短查询 (Oneshot模式)
result2 = skill.search_splunk(
    query="index=_internal | head 1",
    exec_mode="oneshot"
)
print(result2)

# 3. 查询索引列表
result = skill.list_indexes()
print(result)

# 4. 获取索引与 sourcetype 映射
result = skill.indexes_and_sourcetypes()
print(result)

# 5. 操作 KV Store
skill.create_kvstore_collection("my_collection")
skill.list_kvstore_collections()
skill.delete_kvstore_collection("my_collection")
```

## 返回值格式

所有方法统一返回 `dict`：

```python
# 成功时
{"success": True, "data": <结果数据>}

# 失败时
{"success": False, "error": "<错误描述>"}
```

## search_splunk 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `query` | str | 必填 | SPL 查询语句，如 `index=main | head 20` |
| `earliest_time` | str | `"-24h"` | 搜索起始时间，支持相对时间（如 `-1h`、`-7d`）|
| `latest_time` | str | `"now"` | 搜索结束时间 |
| `max_count` | int | `100` | 最大返回结果数 |
| `exec_mode` | str | `"async"` | 执行模式，支持 `"async"` (大批量异步) 和 `"oneshot"` (同步阻塞，适合少量) |

## 运行内置测试

直接执行脚本以验证所有功能：

```bash
cd /path/to/skills/splunk/scripts
python3 splunk_skill.py
```

脚本将按顺序调用所有 11 个方法，逐一打印执行结果，帮助确认 Splunk 连接和权限配置是否正确。

## 注意事项

1. **SSL 证书**：绝大多数 Splunk 实例使用自签名证书，建议将 `VERIFY_SSL` 保持为 `False`，否则会出现 SSL 验证错误。
2. **端口**：Splunk REST API 默认管理端口为 `8089`，与前端端口（8000）不同。
3. **权限**：`list_users` 和 `delete_kvstore_collection` 需要管理员权限；`indexes_and_sourcetypes` 需要 `tstats` 命令执行权限。
4. **搜索超时**：`search_splunk` 最长等待搜索完成时间为 120 秒，可在代码中调整。
5. **KV Store 隔离**：KV Store 操作与 `SPLUNK_APP` 参数绑定，默认为 `search` App。
