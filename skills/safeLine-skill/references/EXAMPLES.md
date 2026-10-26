# 使用示例

## Python 模块调用示例

### 示例 1: 封禁单个 IP

```python
from scripts.safeline_skill import SafeLineIPBan

tool = SafeLineIPBan("https://waf.example.com:9443", "YOUR_TOKEN")

result = tool.append_ips(
    target_ips=["192.168.1.100"],
    group_id=5
)

print(result)
```

### 示例 2: 封禁多个 IP

```python
from scripts.safeline_skill import SafeLineIPBan

tool = SafeLineIPBan("https://waf.example.com:9443", "YOUR_TOKEN")

result = tool.append_ips(
    target_ips=[
        "192.168.1.101",
        "192.168.1.102",
        "192.168.1.103"
    ],
    group_id=5
)

print(result)
```

### 示例 3: 封禁 IP 网段 (CIDR)

```python
from scripts.safeline_skill import SafeLineIPBan

tool = SafeLineIPBan("https://waf.example.com:9443", "YOUR_TOKEN")

result = tool.append_ips(
    target_ips=["10.0.0.0/24"],
    group_id=5
)

print(result)
```

### 示例 4: 带结果检查

```python
from scripts.safeline_skill import SafeLineIPBan

tool = SafeLineIPBan("https://waf.example.com:9443", "YOUR_TOKEN")

ips_to_ban = ["8.8.8.8"]
result = tool.append_ips(ips_to_ban, 5)

if result["success"]:
    print(f"✓ 成功封禁: {result['banned_ips']}")
    print(f"✓ IP 组 ID: {result['group_id']}")
else:
    print(f"✗ 封禁失败: {result['message']}")
    if "error_code" in result:
        print(f"✗ 错误代码: {result['error_code']}")
```

## 命令行调用示例

### 基本用法

```bash
# 封禁单个 IP
python scripts/safeline_skill.py https://waf.example.com:9443 YOUR_TOKEN 5 1.1.1.1

# 封禁多个 IP
python scripts/safeline_skill.py https://waf.example.com:9443 YOUR_TOKEN 5 1.1.1.1 2.2.2.2 3.3.3.3
```

### 带备注信息

# （旧版的附加备注功能主要针对组进行配置，新的附加 IP 逻辑不再针对单次请求记录额外备注，本功能为保持命令行向下兼容处理保留该参数）
python scripts/safeline_skill.py https://waf.example.com:9443 YOUR_TOKEN 5 1.1.1.1 --comment "恶意扫描"
```

### 从文件读取 IP 列表

创建文件 `ips.txt`:

```
192.168.1.100
192.168.1.101
10.0.0.0/24
```

然后执行：

```bash
python scripts/safeline_skill.py https://waf.example.com:9443 YOUR_TOKEN 5 --ip-file ips.txt
```

## 常见使用场景

### 场景 1: 日志分析后封禁

```python
import re
from scripts.safeline_skill import SafeLineIPBan

# 从日志中提取恶意 IP
log_file = "access.log"
malicious_ips = set()

with open(log_file, 'r') as f:
    for line in f:
        # 检测 SQL 注入攻击
        if 'union select' in line.lower():
            match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
            if match:
                malicious_ips.add(match.group(1))

# 批量封禁
if malicious_ips:
    tool = SafeLineIPBan("https://waf.example.com:9443", "YOUR_TOKEN")
    result = tool.append_ips(
        list(malicious_ips),
        group_id=5
    )
    print(result)
```

### 场景 2: 与监控系统集成

```python
import time
from scripts.safeline_skill import SafeLineIPBan

tool = SafeLineIPBan("https://waf.example.com:9443", "YOUR_TOKEN")

def handle_security_event(event):
    """处理安全事件"""
    if event['severity'] == 'critical':
        result = tool.append_ips(
            target_ips[0],
            group_id=5
        )
        return result
    return None
```
