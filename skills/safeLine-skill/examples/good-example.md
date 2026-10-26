# 使用示例：正确用法

本文档展示 safeLine-skill 的正确使用方式和最佳实践。

---

## 场景 1：基本封禁（使用 .env 配置）

**前提**：已在技能根目录创建 `.env` 文件并填写正确配置。

```python
from scripts.safeline_skill import SafeLineIPBan

# 无需传参，自动从 .env 读取配置
tool = SafeLineIPBan()

result = tool.append_ips(
    target_ips=["203.0.113.1"],
    group_id=1
)

if result["success"]:
    print(f"✓ 成功：{result['message']}")
else:
    print(f"✗ 失败：{result['message']} [{result.get('error_code')}]")
```

**预期输出**：
```json
{
  "success": true,
  "status_code": 200,
  "banned_ips": ["203.0.113.1"],
  "group_id": 1,
  "message": "成功封禁 1 个 IP 到组 1",
  "response": { "code": 0, "message": "success" }
}
```

---

## 场景 2：批量封禁 CIDR 网段

```python
from scripts.safeline_skill import SafeLineIPBan

tool = SafeLineIPBan()

malicious_ranges = [
    "198.51.100.0/24",   # 恶意网段 A
    "203.0.113.0/24",    # 恶意网段 B
    "192.0.2.100",       # 单个恶意 IP
]

result = tool.append_ips(
    target_ips=malicious_ranges,
    group_id=1
)

print(f"封禁了 {len(result['banned_ips'])} 个条目")
```

---

## 场景 3：从 IP 文件批量封禁（命令行）

创建 `ips.txt`：

```
# 以下是需要封禁的 IP 列表（# 开头为注释，自动忽略）
198.51.100.1
198.51.100.2
203.0.113.0/24
```

执行封禁：

```bash
python scripts/safeline_skill.py 1 --ip-file ips.txt
```

---

## 场景 4：与日志分析集成

```python
import re
from scripts.safeline_skill import SafeLineIPBan

# 从访问日志中提取发起 SQL 注入的 IP
log_file = "/var/log/nginx/access.log"
malicious_ips = set()

with open(log_file, 'r') as f:
    for line in f:
        if 'union select' in line.lower() or 'drop table' in line.lower():
            match = re.search(r'^(\d+\.\d+\.\d+\.\d+)', line)
            if match:
                malicious_ips.add(match.group(1))

if malicious_ips:
    tool = SafeLineIPBan()
    result = tool.append_ips(
        list(malicious_ips),
        group_id=1
    )
    print(f"已封禁 {len(malicious_ips)} 个攻击源 IP")
```

---

## 场景 5：验证配置是否正确

```bash
# 查看当前从 .env 中加载的配置（Token 脱敏显示）
python scripts/safeline_skill.py --show-config
```

**预期输出**：
```
当前配置：
  base_url: https://192.168.1.100:9443
  api_url: https://192.168.1.100:9443/api/open/ipgroup
  token: eyJh****cdef
```

---

## 最佳实践

1. **使用 `.env` 文件** 管理敏感配置，不要硬编码 Token 到代码中
2. **运行测试** 验证环境：`python scripts/safeline_skill.py --test`
3. **使用 CIDR** 封禁整个攻击网段，比逐个 IP 封禁更高效
4. **保留现有 IP**：由于 API 是覆盖式的，如需追加 IP，请先查询现有列表再合并提交
5. **添加有意义的 comment**，便于事后审计和追溯
