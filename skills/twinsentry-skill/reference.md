# TwinSentry Skill — 详细配置与 API 参考

本文档为 TwinSentry 的 `analysis_agent_skill.py`（分析队列）和 `action_agent_skill.py`（处置队列）提供完整的配置说明、API 参考和错误处理指南。

---

## 配置参数全览

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `TWINSENTRY_BASE_URL` | str | `"http://192.168.0.2:5000"` | TwinSentry 管理控制台服务的 HTTP(S) 地址 |
| `ANALYSIS_AGENT_KEY` | str | `"your-...-key"` | 专用于分析型 Agent 任务鉴权的全局 Key（分析脚本专用）|
| `ACTION_AGENT_KEY` | str | `"your-...-key"` | 专用于处置型 Agent 下发动作指令的全局 Key（处置脚本专用）|
| `REQUEST_TIMEOUT` | int | `30` | 单次 HTTP 请求与轮询的超时判定时间（单位：秒）|

### 配置方式读取优先级

两个脚本均统一集成了强大的 `.env` 加载与环境变量适配方案：

```python
# 默认回退逻辑，如果在真实 OS 层未设置，框架会转而在当前进程尝试寻找根目录下生成的 .env
import os
TWINSENTRY_BASE_URL = os.environ.get("TWINSENTRY_BASE_URL", "http://192.168.0.2:5000")
```

---

## API 参考

TwinSentry 的基础核心通信 SDK 分为两类基座（Analysis 类与 Action 类），二者代码模型虽然高度一致，但职责和操作的目标阶段队列严丝合缝截然不同。

---

### 1. `TwinSentryAnalysisSkill` (智能分析工作流)

类 `TwinSentryAnalysisSkill` 位于 `analysis_agent_skill.py`。专门用于对接系统的 `/analysis/fetch` 和 `/analysis/submit`。

#### `fetch_task(alert_id=None)`

**描述**：从 TwinSentry 获取一条处于挂起（Pending）状态的待分析告警。TwinSentry 数据库利用了原生的 `SELECT FOR UPDATE SKIP LOCKED` 面向微服务作了队列排他锁，并发获取无惧重试或撞车。

**参数**：
- `alert_id` (int): 选填。如果有提供具体的待分析告警 ID，服务端将精准锁定这条指定 ID 告警下发。


**返回结构**：
成功获取到任务时返回一个含详细告警数据的字典：
```json
{
  "id": 13,
  "title": "[严重] 发现短时间内大量端口扫描",
  "priority": "high",
  "raw_text": "源文本日志流...",
  "text_lines": ["line 1", "line 2"]
}
```
> *若队列为空或获取失败，方法直接返回 `None`。*

#### `submit_result(alert_id, analysis_log, enrichment_data)`

**描述**：将分析结论推回至系统，推回后该告警自动流转为 `analyzed` 状态。

**参数**：
- `alert_id` (int)：必填。`fetch_task()` 返回的唯一告警 ID。
- `analysis_log` (str)：必填。经 LLM 分析得出的多行版智能研判结论文本块。
- `enrichment_data` (dict)：选填 (Optional)。注入给告警的结构化富化数据，支持任意层级嵌套。

**返回结果**：`bool`，成功为 `True`，失败或超时为 `False`。

#### `run_once(analyze_func, alert_id=None)`

**描述**：封装好的大一统“抓取→下派传参分析→组装发回”全生命周期回调包装函数，极其适合放在 `while True:` 主循环。
**参数**：
- `analyze_func` (Callable)：回调函数句柄。必须接收 `alert: dict`。其返回的 dict 中**必须含有** `"analysis_log"` 的 Key，以及选填 `"enrichment_data"`。
- `alert_id` (int): 选填。指定定向提取处理的 ID。


---

### 2. `TwinSentryActionSkill` (智能安全处置工作流)

类 `TwinSentryActionSkill` 位于 `action_agent_skill.py`。专门用于对接系统的 `/disposition/fetch` 和 `/disposition/submit`，主要负责安全设备的封禁动作闭环。

#### `fetch_task(alert_id=None)`

**描述**：获取一条处于已通过智能分析待处置任务阶段的告警。

**参数**：
- `alert_id` (int): 选填。如果有提供具体的告警 ID，服务端将尝试定向拦截该目标 ID 下发。


**返回结构**：跟分析任务结构类似，但额外含有智能分析产生的高级推断数据字段：
```json
{
  "id": 13,
  "title": "[严重] 发现短时间内大量端口扫描",
  "priority": "high",
  "analysis_log": "分析结论提示：这是一个明显的扫描动作，结合威胁情报，确认该来源 IP 为高风险...",
  "enrichment_data": {"threat_score": 98}
}
```

#### `submit_result(alert_id, action_log)`

**描述**：提交实际的修复/设备封禁操作日志。推回后告警自动流转为 `disposed` 状态，生命周期闭环彻底结束。

**参数**：
- `alert_id` (int)：必填。告警的唯一 ID。
- `action_log` (str)：必填。记录所执行的全部安全设备的响应与拦截操作记录，用以呈现于网页版。

#### `run_once(dispose_func, alert_id=None)`

**描述**：执行一次完整的提取、触发外围防火墙或蜜罐封禁配置，最后反向回传闭环过程。
**参数**：
- `dispose_func` (Callable)：必须包含对传入 dict 的解析，并返回内含 `"action_log"` 字段的回包。
- `alert_id` (int): 选填。如果希望脱流水线只处理指定单号，可以利用此参数。

---

## 错误响应参考

以上提供的核心请求函数体内，均完整考虑并铺设了基于时间轴的高频断连异常处理控制流捕获 (`try-except`)。发生故障时脚本仅在控制台打印 `logger.error(…)` 或 `logger.warning(…)` 留下错误印记，接着温和返回 `None` / `False`，这极大提高了无监管服务器模式下程序的容灾级别，防止全盘崩溃抛错（如 `NameError`）。

| 错误触发特征 | 常见原因 | 解决方案 |
|----------|----------|----------|
| `fetch 失败: 401 Unauthorized` | 身份验证未通过 | 请优先检查本地的 `.env` 下属对应 Token 值是否被撤销或输入有误 |
| `请求超时，请检查服务器连接` | 服务端断网或被安全组掐断 | 检测 TwinSentry 服务进程是否活着以及宿主 OS 防火墙拦截 |
| `暂无待分析/处置任务` | 告警队列消费排空 | 该提示意为请求得到 404 返回信号，属于纯纯的正常现象 |
| `submit 异常: TypeError...` | 数据格式异常 | 通常是 `enrichment_data` 参数传入了不可被 `json.dumps()` 简单转化的怪异 Python 对象导致 |
