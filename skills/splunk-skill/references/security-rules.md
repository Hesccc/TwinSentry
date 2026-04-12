# splunk-skill — 安全规则

本文档规定使用 splunk-skill 时必须遵守的安全准则，防止数据泄露、权限滥用和服务中断。

---

## 认证安全

### 规则 1：禁止硬编码凭据

**禁止**将用户名、密码或 Token 硬编码在脚本、提示词或 Agent 输出中。

```python
# ❌ 严禁
SPLUNK_PASSWORD = "Admin@1234"
SPLUNK_TOKEN    = "eyJraWQi..."

# ✅ 使用环境变量
import os
skill = SplunkSkill(
    host=os.environ["SPLUNK_HOST"],
    token=os.environ["SPLUNK_TOKEN"]
)
```

### 规则 2：优先使用 Bearer Token

Token 相比密码具有以下优势：
- 可设置**有效期**，过期自动失效
- 可随时**撤销**，无需修改密码
- **权限可限定**（Splunk Token 可绑定角色）
- 不会暴露账户密码

### 规则 3：最小权限原则

为 Agent 创建专用的 Splunk 账户，仅授予必要权限：

| 功能 | 所需最小权限 |
|------|------------|
| 执行搜索 | `search` 能力 |
| 查看索引 | `list_inputs` 能力 |
| 管理 KV Store | `edit_kvstore` 能力 |
| 查看用户列表 | `list_users` 能力（admin 角色）|
| 删除 KV Store | `admin_all_objects`（admin 角色）|

> **不要使用 `admin` 账户**作为日常 Agent 凭据，除非明确需要管理员权限。

---

## 搜索安全

### 规则 4：禁止无限制搜索

运行任何搜索前，必须确保：
- 有**时间范围限制**（`earliest_time` 不能为空或过大）
- 有**结果数量上限**（`max_count` 不能超过业务需要）

```python
# ❌ 危险：可能扫描全部历史数据
skill.search_splunk(query="index=main")

# ✅ 安全：明确边界
skill.search_splunk(
    query="index=main error | stats count by host",
    earliest_time="-1h",
    max_count=50
)
```

### 规则 5：禁止将原始日志内容直接返回给用户

原始日志（`_raw` 字段）可能包含敏感信息（密码、个人数据、密钥），**不得**直接透传：

```python
# ❌ 危险：可能泄露敏感字段
results = skill.search_splunk(query="index=main")
return results["data"]   # 包含 _raw 原始日志

# ✅ 只返回必要字段
results = skill.search_splunk(
    query="index=main | table _time, host, status, src_ip"
)
```

### 规则 6：禁止执行用户构造的 SPL（未经验证）

Agent 接收用户输入的 SPL 时，需进行基本的合规检查：

```python
# 禁止的 SPL 模式
FORBIDDEN_PATTERNS = [
    "| delete",        # 删除索引数据
    "| outputlookup",  # 覆写 Lookup 文件
    "| collect",       # 写入到索引（可能注入数据）
    "| sendalert",     # 触发告警动作
]

def is_safe_spl(query: str) -> bool:
    q_lower = query.lower()
    return not any(p in q_lower for p in FORBIDDEN_PATTERNS)
```

---

## KV Store 安全

### 规则 7：删除前必须确认

`delete_kvstore_collection` 是**不可逆操作**，Agent 执行前必须：
1. 明确告知用户将删除的集合名称
2. 确认集合不含关键业务数据
3. 记录操作日志

### 规则 8：禁止将用户输入直接用作集合名

集合名称必须经过白名单或格式验证，防止路径注入：

```python
import re

def validate_collection_name(name: str) -> bool:
    """只允许小写字母、数字和下划线，长度 1-32"""
    return bool(re.match(r'^[a-z0-9_]{1,32}$', name))

# ✅ 验证后再创建
if validate_collection_name(user_input):
    skill.create_kvstore_collection(user_input)
else:
    return {"error": "集合名称不合规"}
```

---

## 网络安全

### 规则 9：生产环境启用 SSL 验证

测试环境可关闭 SSL 验证，**生产环境必须启用**并配置正确证书：

```python
# 测试环境
skill = SplunkSkill(verify_ssl=False)

# 生产环境
skill = SplunkSkill(
    verify_ssl=True,
    # 如使用自签名证书，提供 CA 证书路径
    # verify_ssl="/path/to/ca-bundle.crt"
)
```

### 规则 10：禁止在公网暴露 Splunk 管理端口

Splunk 管理端口（`8089`）仅应在内网可访问，Agent 应通过内网或 VPN 连接，不得直连公网 Splunk。

---

## 日志安全

### 规则 11：日志中不得出现凭据

脚本已配置 `logging` 模块，请**不要**在日志中打印认证相关信息：

```python
# ❌ 危险
logger.info(f"使用密码 {password} 连接 Splunk")

# ✅ 安全
logger.info(f"使用 Basic Auth 连接 {host}:{port}")
```

---

## 禁用命令清单（SPL）

以下 SPL 命令可能造成数据变更或安全风险，**禁止 Agent 自动执行**：

| 命令 | 风险 |
|------|------|
| `\| delete` | 永久删除索引中的事件 |
| `\| collect` | 向索引写入数据，可能污染数据 |
| `\| outputlookup` | 覆写 Lookup CSV 文件 |
| `\| sendalert` | 触发告警动作（如发邮件、调 Webhook）|
| `\| script` | 在 Splunk 服务器上执行外部脚本 |
| `\| map` | 可递归执行搜索，存在 DoS 风险 |
