# splunk-skill — 命名规范

本文档规定 splunk-skill 在使用过程中涉及的各类命名约定，确保配置和数据的一致性与可维护性。

---

## SPL 查询命名规范

### 搜索变量

使用描述性的变量名，避免单字母变量：

```python
# ✅ 好的命名
failed_login_query = "index=_audit action=login status=failure | stats count by user"
network_traffic_query = "index=firewall | stats sum(bytes) by src_ip, dest_ip"

# ❌ 避免
q = "index=_audit ..."
s = "index=firewall ..."
```

### 时间参数

相对时间使用标准 Splunk 格式：

| 用途 | 写法 | ❌ 避免 |
|------|------|--------|
| 最近 1 小时 | `-1h` | `-60m`（语义不直观）|
| 最近 24 小时 | `-24h` 或 `-1d` | — |
| 最近 7 天 | `-7d` | — |
| 本月至今 | `@mon` | — |

---

## KV Store 集合命名规范

### 命名模式

```
{用途}_{数据类型}
```

**示例**：

| 用途 | 推荐名称 | ❌ 避免 |
|------|----------|--------|
| 威胁情报 IP | `threat_intel_ip` | `ThreatIntel`、`ti`、`data1` |
| 用户白名单 | `user_whitelist` | `whitelist`（过于宽泛）|
| 告警规则 | `alert_rules` | `rules`（过于宽泛）|
| 资产信息 | `asset_inventory` | `assets_2024`（含年份，不利维护）|

### 命名规则

- 使用**小写字母和下划线**（snake_case）
- 长度建议不超过 **32 个字符**
- 不使用空格、连字符（`-`）、点（`.`）
- 临时集合加 `_tmp` 后缀，及时清理
- 测试集合加 `_test` 后缀

```python
# ✅ 合规的集合名
"threat_intel_ip"
"user_whitelist"
"skill_test_collection_tmp"   # 测试完成后应删除

# ❌ 不合规的集合名
"Threat Intel"       # 含空格
"threat-intel-ip"   # 含连字符
"ThreatIntelIP"     # 首字母大写（CamelCase）
"data"              # 含义不明确
```

---

## 索引名称识别规范

Splunk 内置索引以 `_` 开头，业务索引不应以 `_` 开头：

| 前缀 | 含义 | 示例 |
|------|------|------|
| `_` 开头 | Splunk 内部索引，通常不写入业务数据 | `_internal`、`_audit` |
| 无前缀 | 业务数据索引 | `main`、`firewall`、`windows` |
| `idx` 开头 | 常见的业务数据索引 | `idx_net_firewall`、`idx_os_windows`、`idx_web_nginx` |

在 SPL 中排除内部索引的写法：
```
index=* NOT index=_* | ...
```

---

## 结果字段引用规范

访问搜索结果字段时使用 `.get()` 而非直接下标，避免 KeyError：

```python
# ✅ 安全访问
for row in results:
    src_ip = row.get("src_ip", "unknown")
    count  = int(row.get("count", 0))

# ❌ 不安全访问
for row in results:
    src_ip = row["src_ip"]   # 字段不存在时抛出 KeyError
```

---

## 变量命名约定（Python）

| 类型 | 命名风格 | 示例 |
|------|----------|------|
| Skill 实例 | `skill` | `skill = SplunkSkill()` |
| 查询结果 | `result` / `{名词}_result` | `search_result`, `index_result` |
| 结果数据 | `data` / `{名词}_data` | `data = result["data"]` |
| 索引列表 | `indexes` | `indexes = data["indexes"]` |
| 集合名称 | `collection_name` | `collection_name = "threat_intel"` |
| SPL 语句 | `{名词}_spl` 或 `{名词}_query` | `login_query`, `stats_spl` |
