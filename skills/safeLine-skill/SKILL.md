---
name: safeLine-skill
description: 用于向长亭雷池 (SafeLine) WAF 社区版的 IP 组中添加恶意 IP 地址的封禁工具。支持单个或批量 IP 封禁，兼容 CIDR 格式，自动处理自签名证书。
license: MIT
compatibility: Python 3.7+, requests>=2.31.0
metadata:
  version: 1.1.0
  author: SafeLine Integration
  category: security
  tags: [waf, safeline, ip-ban, security]
---

# 长亭雷池 IP 封禁工具

## 功能概述

本技能提供与长亭雷池 (SafeLine) WAF 社区版的 API 集成能力，用于快速将恶意 IP 地址添加到指定的 IP 黑名单组中。

**主要特性：**
- 支持单个或批量 IP 封禁
- 支持 CIDR 格式（如 `192.168.1.0/24`）
- 自动处理自签名证书（社区版）
- 完善的错误处理和状态码解析
- 命令行和模块化调用两种方式

## 何时使用

在以下场景中使用此技能：
- 需要快速封禁已识别的恶意 IP 地址
- 需要批量封禁攻击源 IP
- 需要封禁特定网段（使用 CIDR 格式）
- 需要 API 方式管理雷池 WAF 的 IP 黑名单

## 使用步骤

### 1. 准备环境

安装依赖：

```bash
pip install -r scripts/requirements.txt
```

### 2. 配置连接参数

复制配置模板并填写真实参数：

```bash
cp .env.example .env
```

编辑 `.env` 文件（位于技能根目录）：

```env
SAFELINE_HOST=192.168.1.100    # 雷池管理后台 IP
SAFELINE_PORT=9443             # 端口（默认 9443）
SAFELINE_TOKEN=your_api_token  # API Bearer Token
SAFELINE_GROUP_ID=1            # 默认 IP 黑名单组 ID
SAFELINE_WHITELIST=127.0.0.1   # 白名单IP或CIDR网段，逗号分隔，匹配项直接跳过封禁
```

**获取 Bearer Token：** 登录雷池管理后台 → 账户设置 → API Token

**获取 IP 组 ID：** 雷池管理后台 → 防护配置 → IP 黑名单 → 目标 IP 组的 ID

### 3. 使用方式

#### 方式一：命令行调用

```bash
# 封禁单个 IP（配置从 .env 自动读取）
python scripts/safeline_skill.py 1 1.1.1.1

# 封禁多个 IP
python scripts/safeline_skill.py 1 1.1.1.1 2.2.2.2

# 从文件读取 IP 列表
python scripts/safeline_skill.py 1 --ip-file ips.txt

# 临时覆盖 .env 配置
python scripts/safeline_skill.py --url https://waf:9443 --token YOUR_TOKEN 1 1.1.1.1

# 查看当前配置（Token 脱敏）
python scripts/safeline_skill.py --show-config
```

#### 方式二：作为 Python 模块

```python
from scripts.safeline_skill import SafeLineIPBan

# 配置自动从 .env 文件读取，无需手动传参
tool = SafeLineIPBan()

# 封禁 IP
result = tool.append_ips(
    target_ips=["192.168.1.100", "10.0.0.0/24"],
    group_id=1
)

if result["success"]:
    print(f"封禁成功：{result['message']}")
else:
    print(f"封禁失败：{result['message']} [{result.get('error_code')}]")
```

## 参数说明

### append_ips() 方法参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `target_ips` | List[str] | 是 | 需要封禁的 IP 地址列表，支持 CIDR 格式 |
| `group_id` | int | 是 | 黑名单 IP 组的唯一 ID（正整数） |

### 返回值格式

成功响应：

```json
{
  "success": true,
  "status_code": 200,
  "banned_ips": ["192.168.1.100"],
  "group_id": 5,
  "message": "成功封禁 1 个 IP 到组 5",
  "response": { /* API 原始响应 */ }
}
```

失败响应：

```json
{
  "success": false,
  "status_code": 401,
  "message": "错误：鉴权失败，请检查 Bearer Token",
  "error_code": "AUTH_ERROR"
}
```

## 错误处理

### 错误代码

| 错误代码 | 说明 | 建议排查 |
|----------|------|----------|
| `EMPTY_IP_LIST` | IP 列表为空 | 检查 target_ips 参数 |
| `INVALID_GROUP_ID` | 无效的组 ID | 确保 group_id 为正整数 |
| `SSL_ERROR` | SSL 连接错误 | 确保使用 HTTPS 协议 |
| `CONNECTION_ERROR` | 连接失败 | 检查 base_url 是否正确且可访问 |
| `TIMEOUT` | 请求超时 | 检查网络连接或增加超时时间 |
| `REQUEST_ERROR` | 请求异常 | 检查请求参数格式 |
| `UNKNOWN_ERROR` | 未知错误 | 查看详细错误信息 |

### HTTP 状态码处理

| 状态码 | 说明 | 建议操作 |
|--------|------|----------|
| 200 | 成功 | - |
| 400 | 请求参数格式不正确 | 检查请求体格式 |
| 401 | 鉴权失败 | 检查 Bearer Token 是否正确 |
| 403 | 权限不足 | 检查 API Token 权限 |
| 404 | 接口不存在或 IP 组 ID 无效 | 检查 group_id 和 API 版本 |
| 500 | 服务器内部错误 | 检查雷池服务状态 |

## 边界情况处理

### 1. 增量更新与查询

该 API 是增量附加接口，会保留组内原有的 IP。

1. 如果需查看目前存在的IP（`--show-group`）
2. 任何提交的IP直接进入附加(`append`)逻辑

### 2. IP 格式验证

工具不验证 IP 格式的有效性，雷池 API 会进行验证：
- 支持 IPv4 地址
- 支持 IPv6 地址
- 支持 CIDR 格式（如 `192.168.1.0/24`）

### 3. 自签名证书

雷池社区版默认使用自签名证书，工具已自动处理 (`verify=False`)。

## 示例

### 封禁单个恶意 IP

```python
tool = SafeLineIPBan("https://waf.example.com:9443", "TOKEN")
result = tool.append_ips(["203.0.113.1"], 5)
```

### 批量封禁攻击源

```python
malicious_ips = ["203.0.113.1", "203.0.113.2", "203.0.113.3"]
result = tool.append_ips(malicious_ips, 5)
```

### 封禁整个网段

```python
result = tool.append_ips(["203.0.113.0/24"], 5)
```

## 参考资料

- [雷池 WAF 社区版 API 文档](https://help.waf-ce.chaitin.cn/)
- [长亭科技官网](https://chaitin.cn/)

更多技术细节请参阅 `references/` 目录中的文档。
