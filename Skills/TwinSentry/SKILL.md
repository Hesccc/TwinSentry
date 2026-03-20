---
name: twin-sentry
description: TwinSentry 安全告警分析系统接口工具。用于获取告警、提交分析结论、处置记录，以及与 TwinSentry API 交互。
metadata:
  openclaw:
    requires:
      bins: [python3, pip]
    install:
      - id: pip
        kind: pip
        package: requests
        label: Install Python requests library
---

# TwinSentry Skill - 安全告警分析系统

本 Skill 提供与 TwinSentry 安全告警分析系统的集成能力。

## 功能

### 1. 分析 Agent (Analysis Agent)
从 TwinSentry 获取待分析告警，并提交分析结论和富化数据。

**主要方法：**
- `fetch_task()` - 获取一条待分析告警（原子性）
- `submit_result(alert_id, analysis_log)` - 提交分析结论
- `run_once(analyze_func)` - 完整的过程

### 2. 处置 Agent (Disposition Agent)
获取已分析的告警并执行处置动作。

**主要方法：**
- `fetch_task()` - 获取一条待处置告警
- `submit_result(alert_id, action_log)` - 提交处置记录
- `run_once(dispose_func)` - 完整的过程

## 使用方法

### 配置环境变量或修改脚本中的配置

在 `references/analysis_agent_skill.py` 和 `references/disposition_agent_skill.py` 顶部修改配置：

```python
TWINSENTRY_BASE_URL = "http://your-twinsentry-server:5000"  # TwinSentry 服务器地址
ANALYSIS_AGENT_KEY = "your-api-key"  # 分析 Agent API Key
DISPOSITION_AGENT_KEY = "your-api-key"  # 处置 Agent API Key
```

### 分析告警报表示例

```python
import sys
sys.path.insert(0, '/root/.openclaw/workspace-main/skills/twin-sentry/references')
from analysis_agent_skill import TwinSentryAnalysisSkill

skill = TwinSentryAnalysisSkill()

# 获取待分析告警
task = skill.fetch_task()
if task:
    print(f"告警 ID: {task['id']}")
    print(f"标题: {task['title']}")
    print(f"优先级: {task['priority']}")
    print(f"内容: {task['text_lines']}")
    
    # 提交分析结论
    skill.submit_result(
        alert_id=task['id'],
        analysis_log="来源 IP 命中威胁情报，建议立即封禁。",
        enrichment_data={"threat_score": 95, "source_ip": "1.2.3.4"}
    )
```

### 处置告警报表示例

```python
import sys
sys.path.insert(0, '/root/.openclaw/workspace-main/skills/twin-sentry/references')
from disposition_agent_skill import TwinSentryDispositionSkill

skill = TwinSentryDispositionSkill()

# 获取待处置告警
task = skill.fetch_task()
if task:
    print(f"告警 ID: {task['id']}")
    print(f"分析结论: {task['analysis_log']}")
    print(f"富化数据: {task['enrichment_data']}")
    
    # 提交处置记录
    skill.submit_result(
        alert_id=task['id'],
        action_log="1. 已在 WAF 封禁来源 IP\n2. 已终止恶意进程\n3. 已创建工单"
    )
```

## 完整工作流示例

```python
import sys
sys.path.insert(0, '/root/.openclaw/workspace-main/skills/twin-sentry/references')
from analysis_agent_skill import TwinSentryAnalysisSkill
from disposition_agent_skill import TwinSentryDispositionSkill

# 分析 Agent
analysis_skill = TwinSentryAnalysisSkill()

def my_analyze(alert):
    """分析函数 - 可集成 LLM 进行智能分析"""
    title = alert['title']
    text_lines = alert['text_lines']
    
    # 这里可以调用 LLM 进行分析
    # result = llm.analyze(title, text_lines)
    
    return {
        "analysis_log": f"分析完成：{title} 需进一步核查",
        "enrichment_data": {"analyzed_by": "openclaw"}
    }

# 处理一条告警
analysis_skill.run_once(my_analyze)

# 处置 Agent
disposition_skill = TwinSentryDispositionSkill()

def my_dispose(alert):
    """处置函数 - 执行实际的安全操作"""
    analysis = alert['analysis_log']
    
    # 这里可以调用安全工具 API
    # waf.block_ip(enrichment['source_ip'])
    
    return {
        "action_log": f"根据分析：{analysis}\n已执行自动封禁"
    }

# 处理一条告警
disposition_skill.run_once(my_dispose)
```

## 告警数据结构

### fetch_task() 返回的告警对象

```python
{
    "id": 123,                    # 告警 ID
    "title": "SSH 暴力破解检测",   # 告警标题
    "priority": "high",           # 优先级: high/medium/low
    "raw_text": "...",           # 原始文本
    "text_lines": [...],         # 按行拆分的告警内容
    "analysis_log": "...",        # 分析结论（仅处置 Agent）
    "enrichment_data": {...}      # 富化数据（仅处置 Agent）
}
```

## 注意事项

1. **API Key 管理**：确保 API Key 安全存储，建议使用环境变量
2. **网络连接**：确保能够访问 TwinSentry 服务器
3. **幂等性**：fetch_task 使用 SKIP LOCKED，同一告警不会被多个 Agent 并发获取
4. **超时设置**：默认超时 30 秒，可根据需要调整
5. **日志记录**：脚本使用 Python logging 模块，建议配置日志级别

## 测试

直接运行脚本进行演示模式：

```bash
cd /root/.openclaw/workspace-main/skills/twin-sentry/references
python3 analysis_agent_skill.py
python3 disposition_agent_skill.py
```

## 集成到 LangChain

参考 `references/langchain_wrapper.py` 了解如何将 TwinSentry 技能包装为 LangChain BaseTool。

## 集成到 Dify

使用 `references/dify_tool.yaml` 导入到 Dify 或其他支持 OpenAPI 规范的框架。

## 相关文档

1. **API Key 管理**：在请求头中使用 `X-Agent-Key`
2. **连接地址**：确保使用了正确的 `/api/agent/` 前缀
3. **网络连接**：确保能够访问 TwinSentry 服务器
