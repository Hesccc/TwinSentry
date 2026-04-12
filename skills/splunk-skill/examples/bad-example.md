# Bad Example — 错误的 splunk-skill 使用方式

本文档展示 Agent 调用 splunk-skill 时应**避免的反模式**，并说明每种做法的风险和正确替代方案。

---

## 反模式 1：不检查返回值直接使用数据

```python
# ❌ 错误：直接访问 data 而不检查 success
skill = SplunkSkill()
result = skill.search_splunk(query="index=main | head 10")
events = result["data"]["results"]   # 若连接失败，此处会 KeyError
for e in events:
    print(e["_raw"])
```

**风险**：当 Splunk 不可达或认证失败时，`result["data"]` 不存在，导致程序崩溃。

**正确做法**：
```python
# ✅ 始终先检查 success
if result["success"]:
    for e in result["data"]["results"]:
        print(e["_raw"])
else:
    print(f"搜索失败: {result['error']}")
```

---

## 反模式 2：不指定时间范围执行大范围搜索

```python
# ❌ 错误：对包含海量数据的索引不加时间约束
result = skill.search_splunk(
    query="index=main",       # 无过滤条件，返回所有数据
    # earliest_time 使用默认 "-60m"，但没有 | head 或统计限制
    max_count=10000           # 试图获取 10000 条原始日志
)
```

**风险**：占用 Splunk 大量计算资源，极易超时，影响其他用户。

**正确做法**：
```python
# ✅ 使用具体条件 + 聚合 + 合理结果数
result = skill.search_splunk(
    query="index=main error | stats count by host | sort -count",
    earliest_time="-1h",
    max_count=20
)
```

---

## 反模式 3：硬编码凭据到代码中并提交

```python
# ❌ 错误：凭据硬编码，容易泄露到日志或版本控制中
skill = SplunkSkill(
    host="192.168.0.243",
    username="admin",
    password="Hesc1007."    # 明文密码！
)
```

**风险**：密码可能被记录在日志、提交到 Git 或暴露在 Agent 输出中。

**正确做法**：
```python
# ✅ 使用环境变量或 Token
import os
skill = SplunkSkill(
    host=os.environ["SPLUNK_HOST"],
    token=os.environ["SPLUNK_TOKEN"]   # Bearer Token，可设置有效期
)
```

---

## 反模式 4：不确认就删除 KV Store 集合

```python
# ❌ 错误：直接删除，无任何确认或备份逻辑
skill.delete_kvstore_collection("threat_intel")
# 集合和其中的所有数据将永久丢失
```

**风险**：KV Store 删除操作不可逆，可能删除包含重要数据的集合。

**正确做法**：
```python
# ✅ 删除前确认集合存在，并在日志中记录
result = skill.list_kvstore_collections()
names = [c["name"] for c in result["data"]["collections"]]

target = "threat_intel"
if target in names:
    print(f"警告：即将删除集合 '{target}' 及其所有数据，操作不可逆！")
    # 此处应有人工确认步骤
    del_result = skill.delete_kvstore_collection(target)
    print(f"删除结果: {del_result}")
else:
    print(f"集合 '{target}' 不存在，无需删除")
```

---

## 反模式 5：无限重试导致 Splunk 过载

```python
# ❌ 错误：失败后无间隔地无限重试
while True:
    result = skill.search_splunk(query="index=main | head 1")
    if result["success"]:
        break
    # 没有 sleep，失败时立即重试，可能每秒发送数百个请求
```

**风险**：在 Splunk 繁忙或故障时，无限重试会加剧负载，可能导致服务不可用。

**正确做法**：
```python
# ✅ 有退避的有限重试
import time

max_retries = 3
for attempt in range(max_retries):
    result = skill.search_splunk(query="index=main | head 1")
    if result["success"]:
        break
    wait = 2 ** attempt   # 指数退避：1s, 2s, 4s
    print(f"第 {attempt+1} 次失败，{wait}s 后重试...")
    time.sleep(wait)
else:
    print("达到最大重试次数，放弃")
```
