# 雷池 WAF API 参考文档

## IP 组管理 API

### 更新 IP 组

**接口地址**: `/api/open/ipgroup`

**请求方法**: `PUT`

**请求头**:

```
Content-Type: application/json
authorization: Bearer {token}
```

**请求体参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| id | int | 是 | IP 组的唯一 ID |
| reference | string | 是 | 引用标识，通常为空字符串 |
| comment | string | 否 | 备注信息 |
| ips | array | 是 | IP 地址列表 |

**请求体示例**:

```json
{
  "id": 5,
  "reference": "",
  "comment": "自定义黑名单",
  "ips": ["192.168.1.100", "10.0.0.0/24"]
}
```

**成功响应 (200)**:

```json
{
  "code": 0,
  "message": "success",
  "data": {
    // 雷池返回的数据
  }
}
```

**错误响应示例**:

- 400: 参数错误
- 401: 鉴权失败
- 403: 权限不足
- 404: 资源不存在
- 500: 服务器错误

## IP 格式支持

- IPv4 地址: `192.168.1.1`
- IPv6 地址: `2001:0db8:85a3::8a2e:0370:7334`
- CIDR 格式: `192.168.1.0/24`
- IPv6 CIDR: `2001:db8::/32`
