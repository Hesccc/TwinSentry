# TwinSentry Agent Skills

本目录包含可供 AI Agent 直接调用的 TwinSentry 接口技能包（Tools/Skills）。
这里的代码封装了如何从 TwinSentry 拉取告警、以及如何将处置与分析结果提交回 TwinSentry 的方法。

## 目录结构

- `analysis_agent_skill.py`: **分析 Agent 技能包**。封装了拉取和提交分析结论的逻辑。
- `disposition_agent_skill.py`: **处置 Agent 技能包**。封装了获取和提交处置记录的逻辑。
- `langchain_wrapper.py`: （新增）**LangChain 包装器示例**。展示如何将技能包装为 LangChain `BaseTool` 供 LLM 调用。
- `dify_tool.yaml`: （新增）**Dify Plugin API YAML 规范示例**。用于导入到 Dify 或其他支持 OpenAPI 规范的框架。

## 快速使用说明

1. **环境配置**：
   在需要集成的环境中通过 pip 安装依赖（若无）：
   ```bash
   pip install requests
   ```
2. **填写凭据（如果直接使用原生 Python 脚本）**：
   在 `analysis_agent_skill.py` / `disposition_agent_skill.py` 顶部填入您的 TwinSentry 地址和 API Key。
3. **独立运行演示模式**：
   您可以直接运行脚本体验模拟的交互流程：
   ```bash
   python analysis_agent_skill.py
   python disposition_agent_skill.py
   ```

## 集成到您的 AI Agent 框架

如果您使用的是现代 AI Agent 框架（如 LangChain 或 AutoGPT），请参考随附的 `langchain_wrapper.py` 建立工具类。
您可以基于其中的 `run_once()` 与 `fetch_task()` 灵活组合出适合您业务逻辑节点的 Prompt 工作流。
