# 常见错误及解决方案

本文档列举使用 safeLine-skill 时常见的错误、原因及修复方法。

---

## 错误 1：未配置 .env 文件

**症状**：运行后出现警告，封禁失败报 `CONNECTION_ERROR`：

```
警告：检测到默认占位符配置。
请在技能根目录的 .env 文件中设置 SAFELINE_HOST、SAFELINE_PORT 和 SAFELINE_TOKEN
错误代码：CONNECTION_ERROR
```

**原因**：`.env` 文件不存在或变量名拼写错误。

**✅ 修复**：

```bash
cp .env.example .env
# 然后编辑 .env，填写真实的 IP、端口和 Token
```

---

## 错误 2：Token 鉴权失败（401）

**症状**：
```json
{
  "success": false,
  "status_code": 401,
  "message": "错误：鉴权失败，请检查 Bearer Token"
}
```

**原因**：
- Token 已过期
- Token 复制时多了空格或换行符
- 使用了错误的 Token

**✅ 修复**：
1. 登录雷池管理后台重新生成 Token
2. 确保 `.env` 中 `SAFELINE_TOKEN=` 后面没有多余空格
3. 运行 `python scripts/safeline_skill.py --show-config` 确认 Token 前4位是否正确

---

## 错误 3：IP 组 ID 无效（404）

**症状**：
```json
{
  "success": false,
  "status_code": 404,
  "message": "错误：接口不存在或 IP 组 ID 无效"
}
```

**原因**：`group_id` 对应的 IP 组不存在。

**✅ 修复**：
1. 登录雷池管理后台 → 防护配置 → IP 黑名单
2. 确认 IP 组实际存在并记录其 ID
3. 更新 `.env` 中的 `SAFELINE_GROUP_ID`

---

## 错误 4：覆盖式 API 清空了原有 IP

**症状**：封禁成功，但原先已有的 IP 都消失了。

**原因**：雷池 IP 组 API 是**覆盖式**接口，每次 PUT 请求会替换组内所有 IP。

**✅ 修复**（需自行实现）：
```python
# 伪代码：先获取现有 IP，再合并提交
existing_ips = get_existing_ips(group_id)  # 查询现有 IP（需额外实现）
new_ips = existing_ips + ["1.2.3.4"]
tool.append_ips(new_ips, group_id)
```

> ⚠️ 当前版本不内置获取现有 IP 的功能，请在雷池管理后台手动确认。

---

## 错误 5：python-dotenv 未安装

**症状**：`.env` 文件不生效，配置未被加载。

**原因**：未安装 `python-dotenv` 依赖（静默跳过不报错）。

**✅ 修复**：

```bash
pip install -r scripts/requirements.txt
```

或单独安装：

```bash
pip install python-dotenv
```

---

## 错误 6：EXAMPLES.md 中的代码错误（已修复）

**原始错误代码**（`references/EXAMPLES.md` 第65行）：
```python
# ❌ 错误：tool.b.append_ips 不存在
result = tool.b.append_ips(ips_to_ban, 5)
```

**✅ 正确代码**：
```python
result = tool.append_ips(ips_to_ban, 5)
```

---

## 错误 7：group_id 传入了字符串

**症状**：
```json
{
  "success": false,
  "error_code": "INVALID_GROUP_ID"
}
```

**原因**：`group_id` 必须是整数类型，传入了字符串 `"1"` 或 `"group1"`。

**✅ 修复**：
```python
# ❌ 错误
tool.append_ips(["1.2.3.4"], group_id="1")

# ✅ 正确
tool.append_ips(["1.2.3.4"], group_id=1)
```
