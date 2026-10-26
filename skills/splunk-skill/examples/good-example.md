# Good Example — 正确的 splunk-skill 使用示例

本文档展示 Agent 调用 splunk-skill 的**推荐模式**，包括参数选择、结果处理和错误检查。

---

## 示例 1：安全事件分析

**场景**：分析过去 1 小时内的登录失败事件，统计来源 IP。

```python
from splunk_skill import SplunkSkill

skill = SplunkSkill()

# ✅ 好的做法：先检查连接再执行查询
health = skill.health_check()
if not health["success"]:
    print(f"Splunk 连接失败: {health['error']}")
    exit(1)

# ✅ 好的做法：精确指定时间范围，避免全量扫描
result = skill.search_splunk(
    query="index=_audit action=login status=failure | stats count by src_ip | sort -count | head 10",
    earliest_time="-1h",
    latest_time="now",
    max_count=10
)

if result["success"]:
    events = result["data"]["results"]
    for row in events:
        print(f"来源 IP: {row.get('src_ip')} — 失败次数: {row.get('count')}")
else:
    print(f"搜索失败: {result['error']}")
```

**输出示例**：
```
来源 IP: 10.0.0.55 — 失败次数: 247
来源 IP: 192.168.1.88 — 失败次数: 34
来源 IP: 172.16.0.1 — 失败次数: 12
```

---

## 示例 2：索引状态巡检

**场景**：定期检查所有索引的存储使用情况，找出超过 80% 容量的索引。

```python
from splunk_skill import SplunkSkill

skill = SplunkSkill()

# ✅ 好的做法：使用 list_indexes 获取全量索引，再过滤
result = skill.list_indexes()
if not result["success"]:
    print(f"获取索引失败: {result['error']}")
    exit(1)

alert_indexes = []
for idx in result["data"]["indexes"]:
    current = idx["current_db_size_mb"]
    max_size = idx["max_total_data_size_mb"]
    if max_size > 0:
        usage_pct = current / max_size * 100
        if usage_pct > 80:
            alert_indexes.append({
                "name": idx["name"],
                "usage": f"{usage_pct:.1f}%",
                "current_mb": current,
                "max_mb": max_size
            })

if alert_indexes:
    print("⚠️ 以下索引存储使用率超过 80%：")
    for idx in alert_indexes:
        print(f"  {idx['name']}: {idx['usage']} ({idx['current_mb']} / {idx['max_mb']} MB)")
else:
    print("✅ 所有索引存储使用正常")
```

---

## 示例 3：KV Store 威胁情报管理

**场景**：创建威胁情报集合，写入并查询数据。

```python
from splunk_skill import SplunkSkill

skill = SplunkSkill()
collection = "threat_intel_ioc"

# ✅ 好的做法：创建前先检查是否已存在
existing = skill.list_kvstore_collections()
names = [c["name"] for c in existing["data"]["collections"]] if existing["success"] else []

if collection not in names:
    result = skill.create_kvstore_collection(collection)
    if result["success"]:
        print(f"✅ 集合 '{collection}' 已创建")
    else:
        print(f"❌ 创建失败: {result['error']}")
else:
    print(f"ℹ️ 集合 '{collection}' 已存在，跳过创建")
```

---

## 示例 4：索引与数据源探索

**场景**：在开始调查前，先了解 Splunk 中有哪些数据源可用。

```python
from splunk_skill import SplunkSkill

skill = SplunkSkill()

# ✅ 好的做法：先了解数据结构，再决定搜索策略
result = skill.indexes_and_sourcetypes()
if result["success"]:
    mapping = result["data"]["mapping"]
    print(f"共发现 {len(mapping)} 个索引：\n")
    for index_name, sourcetypes in sorted(mapping.items()):
        if not index_name.startswith("_"):  # 过滤内部索引
            st_list = ", ".join(sourcetypes[:5])
            print(f"  [{index_name}] → {st_list}")
```

**输出示例**：
```
共发现 12 个索引：

  [firewall] → paloalto, cisco_asa, fortinet
  [main] → syslog, access_combined, linux_secure
  [windows] → WinEventLog:Security, WinEventLog:System
```
