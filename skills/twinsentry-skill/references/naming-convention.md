# 命名与编码规范 (Naming Convention)

在为 TwinSentry 编写扩展智能体（Agent）或将自研大模（LLM）脚手架系统接入到平台中时，请务必遵循以下核心的命名与架构规范，以保证与系统的高度一致性和兼容性。

## 1. 脚本与工程文件命名
- **Agent 执行脚本主体**：推荐统一使用下划线蛇形命名（Snake Case），并以明确的 `_agent_skill.py` 结尾。
    - ✅ `analysis_agent_skill.py`
    - ✅ `action_agent_skill.py`

## 2. 系统环境变量 (Environment Variables)
所有供外部读取的网络地址和授权签名**必须**通过 `.env` 动态挂载获取，严禁在公开散发的代码中进行硬编码（Hardcode）。
推荐必须声明的标准环境变量键名（在部署或分发的 `.env` 中）：
- `TWINSENTRY_BASE_URL`：中心控制台服务的 HTTP(S) 地址（例如 `http://127.0.0.1:5000`）。
- `ANALYSIS_AGENT_KEY`：专用于分析型任务借口鉴权的全局 Key。
- `ACTION_AGENT_KEY`：专用于处置/动作型下发接口指令的全局 Key。

## 3. UI 展示与富文本约定 (Markdown)
TwinSentry 的 Web 智能分析弹层已经原生接入了 Markdown 支持模块。
- **推荐标记**：推荐使用 `**加粗**` 标红重要的 IP 地址和域名，也可以使用代码块 `` ` `` 或块状引用的方式输出复杂 SQL 语句。列表任务请规范使用 `- [x]` checkbox 语法。
- **避免标签**：请不要在 Agent 响应回传的报告中混入危险的原生 HTML 标签（如 `<script>`, `<iframe>` ），这会被前端自带的安全逻辑清洗并导致渲染破损。

## 4. 富化数据标准 (Enrichment Data)
在回调 `submit_result` 时如果携带了 `enrichment_data` 参数，请务必保证其序列化前的对象为**合法的字典格式 (Dict)**，便于在数据库中保存为 JSON 串。
推荐尽量携带如下结构范式的字段，作为通用的机器读取标识：
```json
{
  "analyzed_by": "Your_Model_Name_Or_Version",
  "threat_score": 90,
  "confidence": "high",
  "action_required": true
}
```
