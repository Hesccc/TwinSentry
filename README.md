# TwinSentry

TwinSentry 是一个基于 Flask + SQLAlchemy 的安全告警分析处置平台，支持 **告警接入 → 分析智能体 → 处置智能体 → 审计追踪** 的完整闭环，并提供可视化仪表盘、系统配置、技能包下载与 API 文档。

## 核心功能

- **告警接入（Webhook）**
  - 通过 `/api/webhook/receiver` 接收外部系统告警（SIEM / EDR / 自定义系统）
  - 自动解析 `text` 为行级结构化内容
  - 支持去重策略（仅标题 / 标题+内容）

- **双阶段 Agent 工作流**
  - 分析智能体：`/analysis/fetch`、`/analysis/submit`
  - 处置智能体：`/disposition/fetch`、`/disposition/submit`
  - Agent 通过 `X-Agent-Key` 鉴权
  - 使用数据库行级锁（`SKIP LOCKED`）避免并发抢同一任务

- **告警管理**
  - 告警列表、状态筛选、详情弹窗
  - 软删除（`is_delete=1`），默认列表隐藏已删除告警

- **仪表盘分析**
  - 24h 趋势（采集/生成/处置）
  - 状态分布、Top 告警、最近活动

- **系统设置**
  - 超时通知阈值
  - SMTP 配置
  - 通知渠道配置（Email / 企业微信 / 飞书 / Webhook）
  - 渠道“测试连接”真实调用后端测试接口
  - Agent Key 配置

- **审计监控**
  - 审计日志列表
  - 审计趋势图
  - Agent API 登录失败统计（分析/处置智能体）

- **Skills Center**
  - 在线预览 analysis/disposition skill 脚本、LangChain wrapper、Dify YAML
  - 下载 Skills ZIP 时动态写入：
    - `TWINSENTRY_BASE_URL`
    - `ANALYSIS_AGENT_KEY`
    - `DISPOSITION_AGENT_KEY`

- **用户与认证**
  - 用户登录/登出
  - 个人资料修改
  - 头像上传

---

## 技术栈

- Python 3.11+
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- Flask-Bcrypt
- Flask-APScheduler
- PostgreSQL（推荐）
- 前端：Jinja2 + 原生 JS + Chart.js

---

## 快速开始

### 1) 安装依赖

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

### 2) 配置环境变量

```bash
cp .env.example .env
```

至少确认以下配置：

- `DATABASE_URL`
- `SECRET_KEY`
- `JWT_SECRET_KEY`

### 3) 启动服务

```bash
python run.py
```

默认监听：`http://127.0.0.1:5000`（或 `0.0.0.0:5000`）

---

## Docker 启动

```bash
docker compose up --build
```

---

## 首次启动初始化

应用首次启动会自动执行初始化：

- 创建数据库表
- 创建默认管理员账号
- 初始化系统配置（Agent Key / 通知超时 / SMTP / 去重配置）
- 初始化通知渠道
- 无告警时写入 mock 告警数据

默认管理员：

- 用户名：`admin`
- 密码：`admin@123`

> 建议上线前立即修改默认密码。

---

## 页面路由

- `/login` 登录页
- `/` 仪表盘
- `/alerts` 告警管理
- `/settings` 系统设置
- `/audit` 审计监控
- `/profile` 个人中心
- `/api-docs-page` API 文档页
- `/skills-page` Skill 中心

---

## 主要 API

### 认证

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET/PUT /api/auth/profile`
- `POST /api/auth/avatar`

### 告警接入与管理

- `POST /api/webhook/receiver`
- `GET /api/alerts`
- `DELETE /api/alerts/<alert_id>`

### Agent 接口

- `GET /analysis/fetch`
- `POST /analysis/submit`
- `GET /disposition/fetch`
- `POST /disposition/submit`

### 统计与审计

- `GET /api/stats/dashboard`
- `GET /api/audit/logs`
- `GET /api/audit/stats`

### 系统配置

- `GET/PUT /api/settings/system`
- `GET/PUT /api/settings/notifications`
- `POST /api/settings/notifications/test`

### 文档与技能包

- `GET /api-docs`
- `GET /api/skills/config`
- `GET /api/skills/download`

### 健康检查

- `GET /api/status`
- `GET /api/health`

---

## 鉴权说明

- **Web 管理接口**：`Authorization: Bearer <token>`
- **Agent 接口**：`X-Agent-Key: <agent_key>`

---

## Webhook 请求示例

```json
{
  "title": "[严重] 恶意进程执行告警",
  "text": "主机名: WS-01\n进程名: mimikatz.exe\n用户: SYSTEM"
}
```

---

## 测试与开发命令

```bash
python -m flask --app run.py routes
python -m flask --app run.py shell
python -m pytest
```

---

## 目录结构（简版）

```text
TwinSentry/
├─ app/
│  ├─ routes/          # 业务路由（auth/main/agents/webhook/settings/audit/docs）
│  ├─ services/        # 工具与调度服务
│  ├─ templates/       # 页面模板
│  └─ static/          # 静态资源（css/js/images/uploads）
├─ Skills/TwinSentry/  # Skills 包及脚本模板
├─ run.py              # 应用入口
├─ config.py           # 配置加载
└─ requirements.txt
```

---

## 上线建议

- 使用 PostgreSQL（项目包含 `date_trunc` 与 `skip_locked`）
- 禁用默认账号/密码，替换为安全凭据
- 通过环境变量注入密钥，不在仓库存储真实 `.env`
- 为上传目录和日志目录配置备份与权限控制
- 配置反向代理（Nginx）与 HTTPS
