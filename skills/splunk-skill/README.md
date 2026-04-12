# splunk-skill

基于 Splunk 官方 REST API（v10.2）开发的 AI Agent 技能包，封装 11 个核心工具函数，供 Agent 框架（Dify、LangChain、OpenClaw 等）灵活调用，实现 SPL 搜索、索引管理、用户查询及 KV Store 操作。

---

## 在 OpenClaw 中安装

### 方法一：从 GitHub 安装（推荐）

在 OpenClaw 中执行以下命令，直接从 GitHub 克隆并注册本 Skill：

```bash
skill install https://github.com/Hesccc/SplunkSkills.git
```

OpenClaw 将自动完成以下步骤：
1. 克隆仓库到本地 Skill 目录
2. 解析 `SKILL.md` 元数据
3. 安装依赖项（`requests` 库）

### 方法二：本地手动安装

如果已将仓库克隆到本地，可手动注册到 OpenClaw：

```bash
# 1. 克隆仓库
git clone https://github.com/Hesccc/SplunkSkills.git ~/.openclaw/workspace-main/skills/splunk

# 2. 安装 Python 依赖
pip install requests

# 3. 在 OpenClaw 中刷新 Skill 列表
skill reload
```

### 配置 Splunk 连接

安装完成后，修改 Skill 目录下 `scripts/splunk_skill.py` 顶部的配置区：

```python
SPLUNK_HOST     = "192.168.1.100"   # Splunk 主机 IP 或域名
SPLUNK_PORT     = 8089              # 管理端口（默认 8089）
SPLUNK_USERNAME = "admin"           # 用户名
SPLUNK_PASSWORD = "yourpassword"    # 密码
SPLUNK_TOKEN    = ""                # Bearer Token（填写后优先使用，推荐）
```

### 验证安装

在 OpenClaw 中查看 Skill 是否已正确加载：

```bash
skill list
# 应看到 "Splunk" 出现在列表中
```

然后运行内置测试：

```bash
skill run splunk scripts/splunk_skill.py
```

或直接使用 Python 执行：

```bash
python3 ~/.openclaw/workspace-main/skills/splunk/scripts/splunk_skill.py
```

### 在 Agent 中调用

```python
import sys
sys.path.insert(0, '/root/.openclaw/workspace-main/skills/splunk/scripts')
from splunk_skill import SplunkSkill

skill = SplunkSkill()

# 执行 SPL 搜索 (默认异步模式)
result = skill.search_splunk(
    query="index=_internal | head 10",
    earliest_time="-1h",
    max_count=10
)
print(result)

# 执行同步验证搜索 (Oneshot 模式)
result_oneshot = skill.search_splunk(
    query='index=_internal | head 1',
    exec_mode="oneshot"
)
print(result_oneshot)
```

---


## 功能列表

| 方法 | 描述 | 所需权限 |
|------|------|----------|
| `health_check()` | 检查 Splunk 连接，返回已安装应用列表 | 普通用户 |
| `current_user()` | 获取当前认证用户的身份与权限 | 普通用户 |
| `list_users()` | 检索所有用户及其角色和状态 | **管理员** |
| `list_indexes()` | 列出可访问的所有 Splunk 索引 | 普通用户 |
| `get_index_info(index_name)` | 获取特定索引的详细配置信息 | 普通用户 |
| `indexes_and_sourcetypes()` | 返回所有索引及其 sourcetype 映射 | tstats 权限 |
| `search_splunk(query, ...)` | 执行 SPL 搜索，支持时间范围和结果数限制 | 普通用户 |
| `list_saved_searches()` | 列出所有已保存的搜索（包含 Alert/Report）| 普通用户 |
| `list_kvstore_collections()` | 检索当前 App 下的所有 KV Store 集合 | 普通用户 |
| `create_kvstore_collection(name)` | 在 Splunk 中创建新的 KV Store 集合 | 普通用户 |
| `delete_kvstore_collection(name)` | 删除指定的 KV Store 集合（不可逆）| **管理员** |

---

## 文件结构

```
Skills/Splunk/
├── README.md                        # 本文件（功能介绍与使用说明）
├── SKILL.md                         # Skill 元数据（供 Agent 框架解析）
├── reference.md                     # 详细 API 参考与配置说明
├── examples/
│   ├── good-example.md              # 推荐的正确使用示例
│   └── bad-example.md               # 应避免的反模式示例
├── references/
│   ├── naming-convention.md         # 命名规范（SPL、KV Store、变量）
│   └── security-rules.md            # 安全规则与禁用命令清单
└── scripts/
    └── splunk_skill.py              # 主技能类与内置测试
```

---


## 快速开始

### 第一步：配置连接参数

打开 `scripts/splunk_skill.py`，修改文件顶部 **配置区**：

```python
SPLUNK_HOST     = "192.168.1.100"   # Splunk 主机 IP 或域名
SPLUNK_PORT     = 8089              # 管理端口（默认 8089）
SPLUNK_USERNAME = "admin"           # 用户名
SPLUNK_PASSWORD = "yourpassword"    # 密码
SPLUNK_TOKEN    = ""                # Bearer Token（填写后优先使用，推荐）
SPLUNK_APP      = "search"          # KV Store 操作的 App 上下文
VERIFY_SSL      = False             # 自签名证书请保持 False
```

> **认证优先级**：`SPLUNK_TOKEN`（Bearer Token）> Basic Auth（用户名/密码）

### 第二步：在代码中调用

```python
import sys
sys.path.insert(0, r'e:\Code\Development Project\Skills\Splunk\scripts')
from splunk_skill import SplunkSkill

skill = SplunkSkill()

# 连接检测
print(skill.health_check())

# 执行 SPL 搜索 (异步)
result = skill.search_splunk(
    query="index=_internal | head 20",
    earliest_time="-1h",
    latest_time="now",
    max_count=20
)
print(result)

# 执行验证搜索 (同步)
result_oneshot = skill.search_splunk(
    query="index=_internal | head 1",
    exec_mode="oneshot"
)
print(result_oneshot)

# 查看索引与 sourcetype 映射
print(skill.indexes_and_sourcetypes())

# KV Store 操作
skill.create_kvstore_collection("my_collection")
skill.list_kvstore_collections()
skill.delete_kvstore_collection("my_collection")
```

### 返回值格式

所有方法统一返回 `dict`：

```python
# 成功
{"success": True, "data": { ... }}

# 失败
{"success": False, "error": "错误描述"}
```

---

## 测试验证

### 方法一：内置自动测试（推荐）

直接运行 `splunk_skill.py` 脚本，将按顺序自动调用所有 11 个方法并打印结果：

```powershell
cd "e:\Code\Development Project\Skills\Splunk\scripts"
python splunk_skill.py
```

测试输出示例：

```
============================================================
   splunk-skill — 功能自动测试
   目标: https://192.168.1.100:8089
   认证: Basic Auth (admin)
============================================================

──────────────────────────────────────────────────────────
[health_check — 连接检测] ✅ 成功
  total_apps: 12
  apps: [{"name": "search", "label": "Search & Reporting", ...}]

──────────────────────────────────────────────────────────
[current_user — 当前用户] ✅ 成功
  username: admin
  roles: ["admin", "power", "user"]
...
```

> 测试过程会创建并自动删除一个名为 `skill_test_collection_tmp` 的临时 KV Store 集合。

### 方法二：语法检查

验证脚本无语法错误：

```powershell
cd "e:\Code\Development Project\Skills\Splunk\scripts"
python -m py_compile splunk_skill.py; if ($?) { "SYNTAX OK" }
```

---

## `search_splunk` 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `query` | str | 必填 | SPL 查询语句，例如 `index=main error \| stats count by host` |
| `earliest_time` | str | `"-24h"` | 起始时间，支持相对（`-1h`、`-7d`）和绝对时间 |
| `latest_time` | str | `"now"` | 结束时间 |
| `max_count` | int | `100` | 最大返回结果数 |
| `exec_mode` | str | `"async"` | 执行模式，支持 `"async"` (大批量分析，默认) 或 `"oneshot"` (同步阻塞，少量快速) |

---

## 注意事项

1. **管理端口**：Splunk REST API 使用管理端口 `8089`，与 Web 界面端口 `8000` 不同。
2. **SSL 证书**：绝大多数 Splunk 实例使用自签名证书，`VERIFY_SSL` 保持 `False` 即可。
3. **搜索超时**：`search_splunk` 最长等待搜索完成 120 秒（可在代码中调整 `SEARCH_TIMEOUT`）。
4. **tstats 权限**：`indexes_and_sourcetypes()` 需要角色具有 `run_collect_command` 或 `tstats` 相关能力。
5. **KV Store 隔离**：KV Store 操作绑定到 `SPLUNK_APP`（默认 `search`），跨 App 数据不互通。

---

## 相关文档

- [Splunk REST API 参考（10.2）](https://help.splunk.com/en/splunk-enterprise/leverage-rest-apis/rest-api-reference/10.2/input-endpoints/input-endpoint-descriptions)
- [REST API 基本概念](https://help.splunk.com/en/splunk-enterprise/leverage-rest-apis/rest-api-user-manual/10.2/rest-api-user-manual/basic-concepts-about-the-splunk-platform-rest-api)
