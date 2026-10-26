# SafeLine-Ban-Skills 技术参考文档

## 配置参数

### .env 文件配置（推荐）

| 变量名 | 类型 | 必需 | 说明 | 示例 |
|--------|------|------|------|------|
| `SAFELINE_HOST` | string | * | 雷池管理后台 IP 地址或域名（无需协议） | `192.168.1.100` |
| `SAFELINE_PORT` | int | 否 | 管理后台端口，默认 `9443` | `9443` |
| `SAFELINE_TOKEN` | string | * | API Bearer Token | `eyJhbGci...` |
| `SAFELINE_GROUP_ID` | int | 否 | 默认 IP 黑名单组 ID，默认 `1` | `1` |
| `SAFELINE_WHITELIST` | string | 否 | 白名单 IP 或 CIDR 列表（逗号分隔） | `127.0.0.1,10.0.0.0/8` |

> **注**: 也可使用 `SAFELINE_BASE_URL` 直接设置完整 URL（如 `https://192.168.1.100:9443`），优先级高于 HOST+PORT 组合。

### 配置优先级（从高到低）

1. 命令行参数 `--url` / `--token`
2. 系统环境变量（`SAFELINE_*`）
3. 技能根目录下的 `.env` 文件
4. `scripts/` 目录下的 `.env` 文件

---

## SafeLineIPBan 类 API

### 构造函数

```python
SafeLineIPBan(base_url: str = SAFELINE_BASE_URL, token: str = SAFELINE_TOKEN)
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `base_url` | str | WAF 管理后台访问地址，含协议和端口 |
| `token` | str | Bearer Token |

### append_ips()

```python
append_ips(
    target_ips: List[str],
    group_id: int
) -> Dict[str, Any]
```

**参数：**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `target_ips` | List[str] | 是 | IP 地址列表，支持 IPv4、IPv6、CIDR |
| `group_id` | int | 是 | 黑名单 IP 组的唯一 ID（正整数） |

**成功返回示例：**

```json
{
  "success": true,
  "status_code": 200,
  "banned_ips": ["192.168.1.100"],
  "group_id": 1,
  "message": "成功封禁 1 个 IP 到组 1",
  "response": { "code": 0, "message": "success", "data": {} }
}
```

**失败返回示例：**

```json
{
  "success": false,
  "status_code": 401,
  "banned_ips": ["192.168.1.100"],
  "group_id": 1,
  "message": "错误：鉴权失败，请检查 Bearer Token",
  "error_response": { "code": 401, "message": "unauthorized" }
}
```

### get_config_info()

```python
get_config_info() -> Dict[str, str]
```

返回当前配置信息（Token 自动脱敏）：

```json
{
  "base_url": "https://192.168.1.100:9443",
  "api_url": "https://192.168.1.100:9443/api/open/ipgroup",
  "token": "eyJh****789a"
}
```

---

## 错误代码参考

| 错误代码 | 触发条件 | 建议排查 |
|----------|----------|----------|
| `EMPTY_IP_LIST` | `target_ips` 为空列表 | 确保传入至少一个 IP |
| `INVALID_GROUP_ID` | `group_id` 不是正整数 | 确认 group_id 值正确 |
| `SSL_ERROR` | SSL 握手失败 | 确认使用 HTTPS 协议 |
| `CONNECTION_ERROR` | 无法建立连接 | 检查 HOST/PORT 是否正确且可达 |
| `TIMEOUT` | 连接超时（默认 30s） | 检查网络连通性 |
| `REQUEST_ERROR` | 其他 requests 异常 | 查看 `error` 字段详情 |
| `UNKNOWN_ERROR` | 非 requests 异常 | 查看 `message` 字段 |

## HTTP 状态码参考

| 状态码 | 含义 | 建议操作 |
|--------|------|----------|
| `200` | 成功 | — |
| `400` | 请求参数格式错误 | 检查请求体格式 |
| `401` | 鉴权失败 | 检查 Token 是否正确且未过期 |
| `403` | 权限不足 | 检查 API Token 的权限范围 |
| `404` | 接口不存在或 IP 组 ID 无效 | 检查 group_id 和 API 路径 |
| `405` | 请求方法不允许 | 仅支持 PUT 方法 |
| `500` | 服务器内部错误 | 检查雷池服务状态 |
| `502` | 网关错误 | 检查代理或负载均衡配置 |
| `503` | 服务不可用 | 等待服务恢复 |

---

## 命令行参数参考

```
usage: safeline_skill.py [-h] [--ip-file IP_FILE] [--comment COMMENT] [--url BASE_URL]
              [--token TOKEN] [--show-config]
              group_id [ips ...]

位置参数：
  group_id              黑名单 IP 组 ID
  ips                   需要封禁的 IP 地址（空格分隔）

可选参数：
  --ip-file IP_FILE     从文件读取 IP 列表（每行一个，# 开头为注释）
  --comment COMMENT     备注信息（默认："自定义黑名单"）
  --url BASE_URL        覆盖 .env 中的 SAFELINE_BASE_URL
  --token TOKEN         覆盖 .env 中的 SAFELINE_TOKEN
  --show-config         打印当前配置信息后退出
```

---

## 底层 API 说明

**接口**: `POST {base_url}/api/open/ipgroup/append`

**附加式接口**: 增量追加。保留原有 IP。

**请求头**:
```
Content-Type: application/json
X-SLCE-API-TOKEN: {token}
```

**请求体**:
```json
{
  "ip_group_ids": [1],
  "ips": ["192.168.1.1", "10.0.0.0/24"]
}
```
