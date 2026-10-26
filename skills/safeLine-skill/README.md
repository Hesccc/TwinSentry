# safeLine-skill

> 向长亭雷池 (SafeLine) WAF 社区版的 IP 黑名单组中快速封禁恶意 IP 地址。

## 功能特性

- ✅ 支持单个或批量 IP 封禁
- ✅ 支持 CIDR 格式（如 `192.168.1.0/24`）
- ✅ 通过 `.env` 文件管理 WAF 连接参数
- ✅ 自动忽略自签名证书（社区版）
- ✅ 完善的错误处理与中文提示
- ✅ 命令行与 Python 模块两种调用方式

## 目录结构

```
safeLine-skill/
├── SKILL.md              # 核心：元数据 + AI 调用指令（必需）
├── reference.md          # 详细技术参考（API、配置、错误码）
├── README.md             # 本文件：人类可读说明
├── .env.example          # 环境变量配置模板
├── examples/             # 使用场景示例
│   ├── good-example.md   # 正确使用示例
│   └── bad-example.md    # 常见错误及解决方案
├── references/           # 参考资料
│   ├── API.md            # 雷池 API 接口文档
│   ├── EXAMPLES.md       # 详细代码示例
│   └── security-rules.md # 安全规则与最佳实践
└── scripts/              # 可执行脚本
    ├── safeline_skill.py            # 核心封禁脚本
    ├── requirements.txt  # Python 依赖
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r scripts/requirements.txt
```

### 2. 配置连接参数

复制配置模板并填写您的实际参数：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
SAFELINE_HOST=192.168.1.100    # 雷池管理后台 IP
SAFELINE_PORT=9443             # 管理后台端口（默认 9443）
SAFELINE_TOKEN=your_api_token  # API Bearer Token
SAFELINE_GROUP_ID=1            # 默认 IP 黑名单组 ID
SAFELINE_WHITELIST=127.0.0.1   # 白名单IP或CIDR，逗号隔开，匹配的IP会被忽略封禁
```

**获取 Token：** 登录雷池管理后台 → 账户设置 → API Token

**获取 IP 组 ID：** 雷池管理后台 → 防护配置 → IP 黑名单 → 找到目标 IP 组并记录其 ID

### 3. 使用

#### 命令行方式

```bash
# 查询雷池内现有的所有 IP 组
python scripts/safeline_skill.py --list-groups

# 查看特定 IP 组详情（已包含的 IP 列表）
python scripts/safeline_skill.py --show-group 1

# 封禁单个 IP（附加到原组）
python scripts/safeline_skill.py 1 1.1.1.1

# 封禁多个 IP
python scripts/safeline_skill.py 1 1.1.1.1 2.2.2.2

# 从文件批量封禁
python scripts/safeline_skill.py 1 --ip-file ips.txt

# 临时覆盖 .env 中的 URL 和 Token
python scripts/safeline_skill.py --url https://waf:9443 --token mytoken 1 1.1.1.1

# 查看当前配置和白名单（Token 已脱敏）
python scripts/safeline_skill.py --show-config
```

#### Python 模块方式

```python
from scripts.safeline_skill import SafeLineIPBan

# 配置自动从 .env 文件读取
tool = SafeLineIPBan()

# 执行查询
groups = tool.get_ipgroups()
print(groups)

# 执行附加操作
result = tool.append_ips(
    target_ips=["192.168.1.100", "10.0.0.0/24"],
    group_id=1
)

if result["success"]:
    print(f"✓ 封禁成功：{result['message']}")
else:
    print(f"✗ 封禁失败：{result['message']} [{result.get('error_code')}]")
```

## 运行测试

```bash
python scripts/safeline_skill.py --test
```

## 注意事项

- 雷池最新的 IP 组 API 已升级为**附加**（Append）和查询机制，本工具已重构支持增量添加，原有 IP 组不会丢失。
- `.env` 文件包含敏感信息，**不要提交到版本控制系统**，请将 `.env` 加入 `.gitignore`。
- 雷池社区版默认使用自签名 SSL 证书，本工具已自动禁用 SSL 验证（`verify=False`）。

## 参考资料

- [雷池 WAF 社区版文档](https://help.waf-ce.chaitin.cn/)
- [长亭科技官网](https://chaitin.cn/)
